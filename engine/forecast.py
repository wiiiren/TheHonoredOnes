"""Arrival model, forecast() and the alert rule.

forecast(state) runs the clinic forward 60 minutes, 30 times, from what is observable in
`state`. diagnose() and recommend() call the same projection with one thing changed and
the same random draws, so differences between runs are the change and not luck.

    python -m engine.forecast train    # fit the arrival model -> models/arrivals.joblib
"""
from __future__ import annotations

import math
import sys
from collections import OrderedDict
from functools import lru_cache

import numpy as np

from . import sim
from .sim import IMG, LAB, STATIONS, Clinic, params

MODEL_PATH = sim.ROOT / "models" / "arrivals.joblib"
FEATURES = ["bucket", "ratio_15", "ratio_30", "ratio_60", "z_15", "z_30", "z_60"]
BUCKET_MIN = 15
N_BUCKETS = 4
HORIZON = BUCKET_MIN * N_BUCKETS      # 60 minutes
FORECAST_DRAWS = 128                  # service draws per station per run


# --------------------------------------------------------------------------- arrival model

@lru_cache(maxsize=8)
def _usual_cum(weekday):
    """Cumulative usual arrivals by minute of day, padded so any window can be summed."""
    usual = params().usual(weekday)
    return np.concatenate([[0.0], np.cumsum(usual), np.full(240, usual.sum())])


def usual_between(weekday, lo, hi) -> float:
    cum = _usual_cum(weekday)
    return float(cum[max(hi, 0)] - cum[max(lo, 0)])


def feature_rows(clock, weekday, a15, a30, a60):
    """One row per 15-minute bucket ahead, plus the usual arrivals in that bucket.

    Time of day and weekday enter through the usual level; the features describe how far
    recent arrivals are from it (as a ratio and in standard deviations), which is what
    reveals a surge."""
    recent = []
    for arrived, window in ((a15, 15), (a30, 30), (a60, 60)):
        usual = usual_between(weekday, clock - window, clock)
        recent.append(((arrived + 1) / (usual + 1), (arrived - usual) / math.sqrt(usual + 1)))
    rows, usual = [], []
    for b in range(N_BUCKETS):
        lo = clock + b * BUCKET_MIN
        usual.append(usual_between(weekday, lo, lo + BUCKET_MIN))
        rows.append([b] + [r[0] for r in recent] + [r[1] for r in recent])
    return rows, usual


def training_table(days):
    """Features, targets and usual levels: one row per 5-minute tick and bucket."""
    P = params()
    X, y, base = [], [], []
    for day in days:
        r = sim.day_run(day)
        weekday = r.spec["weekday"]
        per_min = np.zeros(1440 + HORIZON)
        n = min(len(r.reg_per_min), 1440 - P.open)
        per_min[P.open:P.open + n] = r.reg_per_min[:n]
        cum = np.concatenate([[0.0], np.cumsum(per_min)])
        for clock in range(P.open, P.close, P.tick):
            a15, a30, a60 = (cum[clock] - cum[clock - w] for w in (15, 30, 60))
            rows, usual = feature_rows(clock, weekday, a15, a30, a60)
            for b, row in enumerate(rows):
                if usual[b] <= 0:        # bucket is after closing: no arrivals by rule
                    continue
                lo = clock + b * BUCKET_MIN
                X.append(row)
                y.append(cum[lo + BUCKET_MIN] - cum[lo])
                base.append(usual[b])
    return np.array(X, dtype=float), np.array(y, dtype=float), np.array(base, dtype=float)


def train(save=True):
    """Fit the gradient-boosted arrival forecaster on the training days.

    The model learns a multiplier on the usual level: the target is arrivals / usual,
    weighted by usual, which is a Poisson model with the usual level as exposure."""
    from sklearn.ensemble import HistGradientBoostingRegressor
    X, y, base = training_table(sim.day_ids("train"))
    model = HistGradientBoostingRegressor(loss="poisson", max_iter=100, learning_rate=0.05,
                                          max_depth=2, min_samples_leaf=40,
                                          l2_regularization=1.0, early_stopping=False,
                                          random_state=0)
    model.fit(X, y / base, sample_weight=base)
    if save:
        import joblib
        import sklearn
        MODEL_PATH.parent.mkdir(exist_ok=True)
        joblib.dump({"model": model, "features": FEATURES, "sklearn": sklearn.__version__,
                     "rows": int(len(y)), "data_mode": params().data_mode}, MODEL_PATH)
    return model


@lru_cache(maxsize=1)
def _model():
    """The saved model, or one trained on the spot if the file is missing or was written
    by a different library version or under a different data mode."""
    try:
        import joblib
        import sklearn
        saved = joblib.load(MODEL_PATH)
        if (saved["features"] == FEATURES and saved["sklearn"] == sklearn.__version__
                and saved.get("data_mode") == params().data_mode):
            return saved["model"]
    except Exception:
        pass
    return train(save=False)


@lru_cache(maxsize=4096)
def arrival_rates(clock, weekday, a15, a30, a60, source="model") -> tuple:
    """Expected arrivals per minute at registration for each of the next 60 minutes."""
    P = params()
    rows, usual = feature_rows(clock, weekday, a15, a30, a60)
    if source in ("usual", "no_model"):
        counts = usual
    else:
        multiplier = _model().predict(np.array(rows, dtype=float))
        # Guard against extrapolation: stay within a factor of 3 of the usual level.
        counts = [min(max(float(m), 1 / 3.0), 3.0) * u for m, u in zip(multiplier, usual)]
    rates = []
    for b in range(N_BUCKETS):
        lo = clock + b * BUCKET_MIN
        open_min = max(0, min(lo + BUCKET_MIN, P.close) - max(lo, P.open))
        per_min = counts[b] / open_min if open_min else 0.0
        rates.extend(per_min if P.open <= m < P.close else 0.0 for m in range(lo, lo + BUCKET_MIN))
    return tuple(rates)


# --------------------------------------------------------------------------- projection

class Projection:
    """Result of the forward runs. W[r, k, s]: wait estimate in run r at 5*(k+1) minutes
    ahead at station s. area[r, s]: patient-minutes spent waiting over the hour.
    joined[r, s]: patients who joined the station's queue over the hour."""
    __slots__ = ("W", "area", "joined", "now", "_cum")

    def __init__(self, W, area, joined, now):
        self.W, self.area, self.joined, self.now = W, area, joined, now
        self._cum = None

    def cum_breach(self) -> np.ndarray:
        """[k, s]: share of runs that have passed the limit by step k (or are over it now)."""
        if self._cum is None:
            limit = params().limit
            over = np.maximum.accumulate(self.W > limit, axis=1) | (self.now > limit)
            self._cum = over.mean(axis=0)
        return self._cum

    def prob(self, si) -> float:
        """Chance the station passes the limit within the hour."""
        return float(self.cum_breach()[-1, si])

    def minutes_to_breach(self, si) -> int:
        """Minutes until the station passes the limit, in 5-minute steps: the median over
        the runs that do pass it. 0 if it is over now; the full hour if no run passes."""
        if self.now[si] > params().limit:
            return 0
        cum = self.cum_breach()[:, si]
        step = params().tick
        if cum[-1] <= 0:
            return int(len(cum) * step)
        return int((np.nonzero(cum >= cum[-1] / 2)[0][0] + 1) * step)


def fingerprint(state) -> tuple:
    return (state["day"], state["clock"], state["weekday"], tuple(state["actions"]),
            tuple(sorted(state["recent_arrivals"].items())),
            tuple(tuple(state["stations"][s][k] for k in sorted(state["stations"][s]))
                  for s in STATIONS))


_DRAWS: OrderedDict = OrderedDict()
_PROJ: OrderedDict = OrderedDict()


def _draws(day, clock, runs):
    key = (day, clock, runs)
    if key not in _DRAWS:
        rng = np.random.default_rng([params().cfg["forecast"]["seed"], int(day), int(clock)])
        _DRAWS[key] = {
            "arr": rng.random((runs, HORIZON)),
            "z": rng.standard_normal((runs, len(STATIONS), FORECAST_DRAWS)).tolist(),
            "ru": rng.random((runs, FORECAST_DRAWS, 2)).tolist(),
            "z0": rng.standard_normal((runs, len(STATIONS), 16)).tolist(),
            "u0": rng.random((runs, len(STATIONS), 16)).tolist(),
            "uq": rng.random((runs, 2, 64, 2)).tolist(),
        }
        while len(_DRAWS) > 8:
            _DRAWS.popitem(last=False)
    return _DRAWS[key]


def expected_staff(state, P=None) -> list:
    """The roster as changed by applied actions that are in force now."""
    P = P or params()
    staff = [[r] for r in P.roster]
    scale = [[1.0] for _ in STATIONS]
    for action_id in sim.active_actions(state["actions"], state["clock"], P):
        sim.apply_move(P.moves[action_id], staff, scale, 0, 1)
    return [s[0] for s in staff]


def demand_excess(state, P=None) -> list:
    """Patients per station who are waiting only because recent arrivals ran above usual.

    Zero unless clinic arrivals over the last 30 or 60 minutes are clearly above the usual
    level (z-score at least demand_min_z). The clinic-wide excess is then traced down the
    pathway: a station's share of it is how far its own joins in the last 30 minutes run
    above what usual arrivals would have sent it.
    """
    P = P or params()
    clock, weekday, recent = state["clock"], state["weekday"], state["recent_arrivals"]
    surplus, z = 0.0, 0.0
    for window in (30, 60):
        usual = usual_between(weekday, clock - window, clock)
        z = max(z, (recent[window] - usual) / math.sqrt(usual + 1))
        surplus = max(surplus, recent[window] - usual)
    out = [0] * len(STATIONS)
    if z < P.demand_min_z:
        return out
    lag = [0.0, P.service_min[0], P.service_min[0] + P.service_min[1],
           P.service_min[0] + P.service_min[1], P.service_min[0] + P.service_min[1]]
    for si, name in enumerate(STATIONS):
        st = state["stations"][name]
        back = int(round(lag[si]))
        usual = P.share[name] * usual_between(weekday, clock - 30 - back, clock - back)
        take = int(round(min(st["waiting"], max(st["arrivals_30m"] - usual, 0.0), surplus)))
        out[si] = max(take, 0)
        surplus -= out[si]
    return out


def _series(state, P, staff_mode, speed_mode, move):
    """Staff and service scale for each of the next 60 minutes."""
    clock, actions = state["clock"], state["actions"]
    H = HORIZON
    if staff_mode == "roster":
        staff = [[r] * H for r in expected_staff(state, P)]
    else:
        staff = [[int(state["stations"][s]["staff_on"])] * H for s in STATIONS]
    scale = []
    for name in STATIONS:
        unexplained, total = sim.station_speed(state, name, P)
        scale.append([total / unexplained if speed_mode == "normal" else total] * H)
    # Applied actions end 60 minutes after they start: undo them from then on.
    for action_id, spans in sim.action_windows(actions, P).items():
        mv = P.moves[action_id]
        for lo, hi in spans:
            if not (lo <= clock < hi) or hi - clock >= H:
                continue
            for i in range(hi - clock, H):
                if "service_scale" in mv:
                    scale[STATIONS.index(mv["station"])][i] /= mv["service_scale"]
                else:
                    to = STATIONS.index(mv["to"])
                    if staff[to][i] > 1:
                        staff[to][i] -= 1
                        if mv["from"] in STATIONS:
                            staff[STATIONS.index(mv["from"])][i] += 1
    if move is not None:
        sim.apply_move(P.moves[move], staff, scale, 0, H)
    return staff, scale


def _build(state, P, d, r, speeds):
    """A clinic consistent with the observed counts. What cannot be observed (how long
    each service has left, where each waiting patient goes next) is drawn per run."""
    clock = state["clock"]
    c = Clinic(clock)
    stretch = 1 + P.cv ** 2          # a service caught in progress is longer than average
    for si, name in enumerate(STATIONS):
        st = state["stations"][name]

        def patient(j):
            if si == LAB:
                u = d["uq"][r][0][j % 64]
                return (-1, clock, 1 if u[0] < P.p_img_given_lab else 0, 1 if u[1] < P.p_pharm else 0)
            if si == IMG:
                return (-1, clock, 0, 1 if d["uq"][r][1][j % 64][1] < P.p_pharm else 0)
            return (-1, clock, 0, 0)

        waiting = max(int(st["waiting"]), 0)
        serving = max(int(st["in_service"]), 0)
        for j in range(waiting):
            c.q[si].append(patient(j))
        for j in range(serving):
            full = math.exp(P.mu[si] + P.sigma * d["z0"][r][si][j % 16]) * speeds[si]
            left = full * d["u0"][r][si][j % 16] * stretch
            c.busy[si].append((clock + max(1, int(left + 0.5)), patient(waiting + j), 0))
    return c


def project(state, arrivals="model", staff="state", speed="state", move=None) -> Projection:
    """Run the clinic forward 60 minutes `forecast.runs` times.

    arrivals  "model" (learned forecaster), "usual" (usual level for the time of day,
              and without the patients already waiting because of a surge) or "no_model"
              (usual level, queues untouched: the evaluation's test of what the model adds)
    staff     "state" (who is on duty now) or "roster" (the planned roster)
    speed     "state" (recent service speed) or "normal" (the usual service time)
    move      an allowed move id applied for the whole hour, or None
    """
    key = (fingerprint(state), arrivals, staff, speed, move)
    if key in _PROJ:
        _PROJ.move_to_end(key)
        return _PROJ[key]
    P = params()
    runs = int(P.cfg["forecast"]["runs"])
    clock = state["clock"]
    d = _draws(state["day"], clock, runs)
    ra = state["recent_arrivals"]
    rates = np.array(arrival_rates(clock, state["weekday"], ra[15], ra[30], ra[60], arrivals))
    arr = sim.poisson_from_uniform(d["arr"], rates).tolist()
    staff_s, scale_s = _series(state, P, staff, speed, move)
    speeds = [s[0] for s in scale_s]
    seen = state
    if arrivals == "usual":
        excess = demand_excess(state, P)
        if any(excess):
            seen = dict(state, stations={
                name: dict(state["stations"][name],
                           waiting=state["stations"][name]["waiting"] - excess[si])
                for si, name in enumerate(STATIONS)})
    step = P.tick
    K = HORIZON // step
    factor = np.array([[P.service_min[si] * scale_s[si][step * (k + 1) - 1]
                        / max(staff_s[si][step * (k + 1) - 1], 1)
                        for si in range(len(STATIONS))] for k in range(K)])
    Q = np.zeros((runs, K, len(STATIONS)))
    area = np.zeros((runs, len(STATIONS)))
    joined = np.zeros((runs, len(STATIONS)))
    for r in range(runs):
        c = _build(seen, P, d, r, speeds)
        samples, a, j = [], [0] * 5, [0] * 5
        sim.run(c, HORIZON, arr[r], staff_s, scale_s, d["z"][r], d["ru"][r], P,
                step=step, samples=samples, area=a, joined=j)
        Q[r] = samples
        area[r] = a
        joined[r] = j
    # "Over the limit now" is a fact about the present, whatever the run changes.
    now = np.array([P.wait(state["stations"][s]["waiting"], state["stations"][s]["staff_on"],
                           si, sim.station_speed(state, s, P)[1])
                    for si, s in enumerate(STATIONS)])
    proj = Projection(Q * factor, area, joined, now)
    _PROJ[key] = proj
    while len(_PROJ) > 2500:
        _PROJ.popitem(last=False)
    return proj


def forecast(state):
    """{station: {15|30|60: {"wait_p50", "wait_p90", "breach_prob"}}}.

    wait_p50 and wait_p90 are the median and 90th-percentile wait estimate at that many
    minutes ahead. breach_prob is the share of runs in which the station has passed the
    limit by then (so it never falls as the horizon grows).
    """
    P = params()
    proj = project(state)
    cum = proj.cum_breach()
    out = {}
    for si, name in enumerate(STATIONS):
        out[name] = {}
        for h in P.cfg["forecast"]["horizons_min"]:
            k = h // P.tick - 1
            w = proj.W[:, k, si]
            out[name][int(h)] = {"wait_p50": round(float(np.median(w)), 1),
                                 "wait_p90": round(float(np.percentile(w, 90)), 1),
                                 "breach_prob": round(float(cum[k, si]), 3)}
    return out


# --------------------------------------------------------------------------- alert rule

def alert_settings(P=None) -> tuple:
    a = (P or params()).cfg["alert"]
    return float(a["raise_at"]), float(a["clear_at"]), int(a["ticks"])


def step_alert(prev, prob, settings):
    """One tick of the alert rule for one station.

    prev = (active, ticks at or above raise_at, ticks below clear_at). An alert is raised
    after `ticks` consecutive checks at or above raise_at and cleared after `ticks`
    consecutive checks below clear_at, so one noisy check never raises or clears it.
    """
    raise_at, clear_at, ticks = settings
    active, hi, lo = prev
    hi = hi + 1 if prob >= raise_at else 0
    lo = lo + 1 if prob < clear_at else 0
    if not active and hi >= ticks:
        active = True
    elif active and lo >= ticks:
        active = False
    return (active, hi, lo)


def breach_probs(state) -> list:
    """Chance per station of passing the limit within the hour."""
    proj = project(state)
    return [proj.prob(si) for si in range(len(STATIONS))]


if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "train":
        import time
        t0 = time.perf_counter()
        train()
        print(f"trained the arrival model in {time.perf_counter() - t0:.1f}s -> {MODEL_PATH}")
    else:
        print(__doc__)
