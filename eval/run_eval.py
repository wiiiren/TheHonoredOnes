"""Regenerates every number in the "Why trust this?" section.

    python eval/run_eval.py            # all runs -> eval/results.json
    python eval/run_eval.py --quick    # runs 2 and 5 only (the two that must exist)

Runs 1 to 5 use only the 20 held-out test days. Nothing here tunes anything: alert
thresholds are chosen by eval/tune_alerts.py on the 10 tuning days.
"""
from __future__ import annotations

import json
import sys
import time
from copy import deepcopy
from datetime import datetime, timezone
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from engine import api, sim  # noqa: E402
from engine.forecast import (alert_settings, arrival_rates, breach_probs, project,  # noqa: E402
                             step_alert)
from engine.recommend import IDLE, advance, episode_cause  # noqa: E402
from engine.sim import CAUSES, STATIONS  # noqa: E402

P = sim.params()
TICKS = list(range(P.open, P.close, P.tick))
NS = len(STATIONS)
CLINIC_DAYS_PER_YEAR = 300      # assumption for the impact figure: Monday to Saturday


# --------------------------------------------------------------------------- views of a day

def noisy(state, rng):
    """What the engine would see through an imperfect feed: queue counts off by up to 2,
    recent arrivals miscounted by up to 10%, service times off by up to 20%. The day
    itself is unchanged; only the observation is."""
    s = deepcopy(state)
    for st in s["stations"].values():
        st["waiting"] = max(0, st["waiting"] + int(rng.integers(-2, 3)))
        st["arrivals_30m"] = max(0, int(round(st["arrivals_30m"] * rng.uniform(0.9, 1.1))))
        st["service_min_30m"] = round(st["service_min_30m"] * float(rng.uniform(0.8, 1.2)), 1)
    s["recent_arrivals"] = {w: max(0, int(round(v * rng.uniform(0.9, 1.1))))
                            for w, v in s["recent_arrivals"].items()}
    return sim.refresh_waits(s)


def observe(day, clock, noise):
    state = api.get_state(day, clock)
    if noise:
        state = noisy(state, np.random.default_rng([20261011, int(day), int(clock)]))
    return state


def truth(day) -> np.ndarray:
    """[tick, station] true wait estimate on the day with nobody moved."""
    r = sim.day_run(day)
    idx = np.minimum(np.array(TICKS + [P.close + k * P.tick for k in range(13)]) - P.open, r.minutes)
    return r.true_wait[idx]


def watch(day, noise=False, settings=None, cause=True, arrivals="model"):
    """Replay a day tick by tick as the engine sees it.

    Returns probs [tick, station], p50 forecasts {30|60: [tick, station]}, the observed
    wait now [tick, station], raised flags [tick, station] and, per alert raise,
    (tick index, station index, cause shown when it was first raised).

    arrivals="no_model" forecasts with arrivals at the usual level instead of the learned
    model; causes are not worked out in that case."""
    settings = settings or alert_settings()
    cause = cause and arrivals == "model"
    n = len(TICKS)
    probs = np.zeros((n, NS))
    seen = np.zeros((n, NS))
    p50 = {30: np.zeros((n, NS)), 60: np.zeros((n, NS))}
    raised = np.zeros((n, NS), dtype=bool)
    raises = []
    prev = [IDLE] * NS
    for i, clock in enumerate(TICKS):
        state = observe(day, clock, noise)
        proj = project(state, arrivals=arrivals)
        probs[i] = breach_probs(state) if arrivals == "model" else [proj.prob(si) for si in range(NS)]
        seen[i] = [state["stations"][s]["wait_now_min"] for s in STATIONS]
        for h in p50:
            p50[h][i] = np.median(proj.W[:, h // P.tick - 1, :], axis=0)
        if cause:
            now = advance(prev, state, settings)
        else:
            now = [step_alert(prev[si][:3], probs[i, si], settings) + IDLE[3:] for si in range(NS)]
        for si in range(NS):
            raised[i, si] = now[si][0]
            if now[si][0] and not prev[si][0]:
                raises.append((i, si, episode_cause(now[si])["cause"] if cause else None))
        prev = now
    return {"probs": probs, "p50": p50, "seen": seen, "raised": raised, "raises": raises}


def rule(probs, settings) -> np.ndarray:
    """Raised flags [tick, station] from a probability series under given settings."""
    raised = np.zeros(probs.shape, dtype=bool)
    for si in range(probs.shape[1]):
        prev = IDLE[:3]
        for i in range(probs.shape[0]):
            prev = step_alert(prev, probs[i, si], settings)
            raised[i, si] = prev[0]
    return raised


# --------------------------------------------------------------------------- run 2: alerts

def episodes(breach) -> list:
    """Breach episodes at one station as (first tick, last tick); gaps of up to two ticks
    are the same episode."""
    out = []
    for i in np.nonzero(breach)[0]:
        if out and i - out[-1][1] <= 3:
            out[-1][1] = i
        else:
            out.append([i, i])
    return out


def alert_quality(days, raised_by_day) -> dict:
    """Score alerts against true breaches.

    An alert is real if the station is over the limit when it is raised or passes it
    within 60 minutes; otherwise it is a false alarm. A breach is caught if an alert was
    already raised at least one tick before it began; the warning time is how long before.
    """
    horizon = 60 // P.tick
    alerts = real = caught = late = total = 0
    warnings = []
    for day in days:
        over = truth(day)[:len(TICKS) + horizon] > P.limit
        raised = raised_by_day[day]
        for si in range(NS):
            r = raised[:, si]
            starts = [i for i in range(len(r)) if r[i] and (i == 0 or not r[i - 1])]
            for i in starts:
                alerts += 1
                real += bool(over[i:i + horizon + 1, si].any())
            for first, last in episodes(over[:len(TICKS), si]):
                total += 1
                if first > 0 and r[first - 1]:
                    start = first - 1
                    while start > 0 and r[start - 1]:
                        start -= 1
                    caught += 1
                    warnings.append(min((first - start) * P.tick, 60))
                elif r[first:last + 1].any():
                    late += 1
    n = len(days)
    return {
        "days": n,
        "alerts": alerts,
        "breaches": total,
        "precision": round(real / alerts, 3) if alerts else None,
        "recall": round(caught / total, 3) if total else None,
        "breaches_caught_early": caught,
        "breaches_flagged_only_once_over": late,
        "breaches_missed": total - caught - late,
        "median_warning_min": float(np.median(warnings)) if warnings else None,
        "false_alarms": alerts - real,
        "false_alarms_per_day": round((alerts - real) / n, 2),
    }


def run_alerts(days, views) -> dict:
    settings = alert_settings()
    with_rule = alert_quality(days, {d: views[d]["raised"] for d in days})
    no_rule = alert_quality(days, {d: rule(views[d]["probs"], settings[:2] + (1,)) for d in days})
    with_rule["false_alarms_per_day_no_rule"] = no_rule["false_alarms_per_day"]
    with_rule["no_rule"] = {k: no_rule[k] for k in ("alerts", "precision", "recall",
                                                    "median_warning_min", "false_alarms_per_day")}
    with_rule["settings"] = {"raise_at": settings[0], "clear_at": settings[1], "ticks": settings[2]}
    return with_rule


# --------------------------------------------------------------------------- run 1: forecast

def time_of_day_average() -> np.ndarray:
    """[tick, station] average true wait at each time of day over the training days."""
    return np.mean([truth(d) for d in sim.day_ids("train")], axis=0)


def run_forecast(days, views, baseline) -> dict:
    """Mean absolute error of the wait estimate 30 and 60 minutes ahead, in minutes, for
    the model and two baselines. `busy` keeps only moments when the station's wait is, or
    turns out to be, at least 10 minutes: most of the day every method is right that
    nothing is happening."""
    out = {}
    groups = {"normal": [d for d in days if sim.day_spec(d)["scenario"] == "normal"],
              "scenario": [d for d in days if sim.day_spec(d)["scenario"] != "normal"],
              "all": list(days)}
    for h in (30, 60):
        k = h // P.tick
        out[str(h)] = {}
        for group, members in groups.items():
            err = {"model": [], "persistence": [], "time_of_day": []}
            busy = []
            for d in members:
                actual = truth(d)[k:k + len(TICKS)]
                v = views[d]
                err["model"].append(np.abs(v["p50"][h] - actual))
                err["persistence"].append(np.abs(v["seen"] - actual))
                err["time_of_day"].append(np.abs(baseline[k:k + len(TICKS)] - actual))
                busy.append((actual >= 10) | (v["seen"] >= 10))
            if not members:
                continue
            busy = np.concatenate(busy)
            cell = {name: round(float(np.concatenate(e).mean()), 2) for name, e in err.items()}
            cell["busy"] = {name: round(float(np.concatenate(e)[busy].mean()), 2)
                            for name, e in err.items()} if busy.any() else None
            cell["busy_share"] = round(float(busy.mean()), 3)
            out[str(h)][group] = cell
        out[str(h)].update(out[str(h)]["all"])      # TRD shape: forecast["30"]["model"]
    return out


# --------------------------------------------------------------------------- run 3: cause

def run_cause(days, views) -> dict:
    """For each scenario day, the cause on the card when the first alert linked to the
    scenario is raised: at the disrupted station (any station for a demand surge), from
    the start of the disruption until 60 minutes after it ends."""
    labels = list(CAUSES) + ["mixed", "peak_load", "no_alert"]
    confusion = {}
    right = shown = 0
    for d in days:
        spec = sim.day_spec(d)
        events = spec["events"]
        if not events:
            continue
        true = [e["type"] for e in events]
        lo = min(sim.to_min(e["start"]) for e in events)
        hi = max(sim.to_min(e["start"]) + e["duration"] for e in events) + 60
        where = None
        if "demand_surge" not in true:
            where = {STATIONS.index(e["station"]) for e in events}
        got = "no_alert"
        for i, si, cause in views[d]["raises"]:
            if lo <= TICKS[i] <= hi and (where is None or si in where):
                got = cause
                break
        key = "+".join(true)
        confusion.setdefault(key, {name: 0 for name in labels})[got] += 1
        if got != "no_alert":
            shown += 1
            right += got in true or (len(true) > 1 and got == "mixed")
    return {"scenario_days": sum(sum(row.values()) for row in confusion.values()),
            "days_with_alert": shown, "correct": right,
            "accuracy": round(right / shown, 3) if shown else None,
            "confusion": confusion}


# --------------------------------------------------------------------------- run 5: policies

def targets(move) -> str:
    return move.get("to") or move.get("station")


def reactive_step(state):
    """A supervisor without the tool: once a station's wait has passed the limit, send an
    available move to the station with the longest wait. They do not take a clerk from a
    registration desk that is itself more than half way to the limit."""
    in_force = sim.active_actions(state["actions"], state["clock"])
    over = sorted(((st["wait_now_min"], name) for name, st in state["stations"].items()
                   if st["wait_now_min"] > P.limit), reverse=True)
    for _, name in over:
        for move in P.cfg["allowed_moves"]:
            if targets(move) != name or move["id"] in in_force:
                continue
            donor = move.get("from")
            if donor in STATIONS:
                d = state["stations"][donor]
                if d["staff_on"] < 2 or d["wait_now_min"] > P.limit / 2:
                    continue
            return move["id"]
    return None


def tool_step(state):
    """Apply the top action of the highest-priority alert that has one."""
    for alert in api.alerts(state):
        if alert["top_action"]:
            return alert["top_action"]["action_id"]
    return None


def run_policy(days, step) -> dict:
    patients = over = hours = moves = 0.0
    per_day = {}
    for d in days:
        actions = ()
        if step is not None:
            for clock in TICKS:
                move = step(api.get_state(d, clock, actions))
                if move:
                    actions += ((move, clock),)
        o = api.day_outcome(d, actions)
        per_day[d] = {"share_over_30": o["share_over_30"], "total_wait_hours": o["total_wait_hours"],
                      "moves": len(actions)}
        patients += o["patients"]
        over += o["share_over_30"] * o["patients"]
        hours += o["total_wait_hours"]
        moves += len(actions)
    return {"share_over_30": round(over / patients, 4), "total_wait_hours": round(hours, 1),
            "wait_hours_per_day": round(hours / len(days), 2), "moves": int(moves),
            "moves_per_day": round(moves / len(days), 2), "patients": int(patients),
            "per_day": per_day}


def run_policies(days) -> dict:
    out = {"fixed": run_policy(days, None), "reactive": run_policy(days, reactive_step),
           "tool": run_policy(days, tool_step)}
    better = sum(out["tool"]["per_day"][d]["total_wait_hours"] < out["reactive"]["per_day"][d]["total_wait_hours"] - 1e-9 for d in days)
    worse = sum(out["tool"]["per_day"][d]["total_wait_hours"] > out["reactive"]["per_day"][d]["total_wait_hours"] + 1e-9 for d in days)
    out["tool_vs_reactive"] = {"days_tool_better": int(better), "days_tool_worse": int(worse),
                               "days_equal": len(days) - int(better) - int(worse)}
    for policy in ("fixed", "reactive", "tool"):
        out[policy].pop("per_day")
    return out


# --------------------------------------------------------------------------- run 0: calibration

def run_calibration() -> dict:
    """Simulated normal days against the real log. Only what the log can support."""
    cal = P.calibration
    if not cal:
        return {}
    normal = [d for d in sim.day_ids() if sim.day_spec(d)["scenario"] == "normal"]
    runs = [sim.day_run(d) for d in normal]
    hours = range(P.open // 60, P.close // 60)
    factor = np.mean([P.weekday_factor[r.spec["weekday"]] for r in runs])
    arrivals = {str(h): {
        "real_per_hour": cal["real"]["arrivals_per_hour"][str(h)],
        "real_scaled_per_hour": round(cal["arrivals_per_hour"][str(h)] * float(factor), 2),
        "sim_per_hour": round(float(np.mean([r.reg_per_min[h * 60 - P.open:(h + 1) * 60 - P.open].sum()
                                             for r in runs])), 2)} for h in hours}
    shares = {}
    for name in ("laboratory", "imaging"):
        si = STATIONS.index(name)
        shares[name] = {"real": cal["share"][name], "sim": round(float(np.mean(
            [len({row[0] for row in r.rows if row[1] == si}) / r.outcome["patients"] for r in runs])), 4)}
    to_doctor = np.concatenate([[row[3] - reg[row[0]] for row in r.rows if row[1] == 1]
                                for r in runs
                                for reg in [{row[0]: row[2] for row in r.rows if row[1] == 0}]])
    stations = {name: {"real_service_min": None,
                       "sim_service_min": round(float(np.mean(
                           [row[4] - row[3] for r in runs for row in r.rows if row[1] == si])), 2),
                       "config_service_min": P.service_min[si]}
                for si, name in enumerate(STATIONS)}
    return {
        "note": ("Arrival pattern and laboratory and imaging shares are measured from the "
                 "real log. Service times, pharmacy share and staff numbers are assumptions: "
                 "the log does not record them usably."),
        "normal_days_simulated": len(runs),
        "arrival_scale_factor": cal["arrival_scale_factor"],
        "arrivals": arrivals,
        "shares": shares,
        **stations,
        "wait_to_doctor": {
            "real_median_min": cal["real"]["wait_to_doctor"]["median_min"],
            "real_share_over_30": cal["real"]["wait_to_doctor"]["share_over_30"],
            "sim_median_min": float(np.median(to_doctor)),
            "sim_share_over_30": round(float((to_doctor > P.limit).mean()), 3),
            "note": ("Not a calibration target. The simulated clinic is sized so normal days "
                     "are calm; the real clinic's waits are far longer."),
        },
        "consult_cycle_proxy_min": cal["real"]["consult_cycle_proxy_min"],
    }


# --------------------------------------------------------------------------- main

def assumptions() -> list:
    cal = P.calibration
    out = [
        "Results are from simulated clinic days, not a live clinic.",
        f"Staff numbers are assumed: {', '.join(f'{P.roster[i]} at {s}' for i, s in enumerate(STATIONS))}.",
        f"Average service times are assumed: {', '.join(f'{s} {P.service_min[i]:g} min' for i, s in enumerate(STATIONS))}.",
        f"{P.share['pharmacy']:.0%} of patients are assumed to visit the pharmacy.",
        "The five allowed moves are assumed, and a moved staff member works at full speed at once.",
        "Each move lasts 60 minutes. The float nurse, float clerk and on-call doctor are assumed available.",
        "Patients do not leave the queue, so the cost of leaving without care is not measured.",
        f"A breach is the wait estimate (patients waiting x current service time / staff) passing {P.limit:g} minutes.",
        "Disruptions are injected in the busy part of the day (starting 09:30 to 11:30).",
        "The reactive supervisor moves staff only after a wait has passed the limit, and does not "
        "take a clerk from a registration desk that is more than half way to the limit.",
        f"Station weights used only to rank alerts: {dict(zip(STATIONS, P.weight))}.",
    ]
    if cal:
        out.insert(1, (
            "Arrival pattern by hour and weekday, and the laboratory and imaging shares, are measured "
            f"from the HospitalOPD log ({cal['method']['visits_used']} visits on {cal['method']['days_used']} "
            f"days, {cal['method']['window'][0]} to {cal['method']['window'][1]}, timestamps shifted "
            f"from UTC to UTC+{cal['method']['utc_offset_hours']})."))
        out.insert(2, (
            f"Real arrivals are scaled by {cal['arrival_scale_factor']} so that the assumed "
            f"{P.roster[1]}-doctor clinic is {P.cfg['calibration']['target_peak_util']:.0%} busy in the "
            "peak hour of an average weekday."))
    else:
        out.insert(1, "No real-data calibration: arrivals and patient shares are the assumptions in config.yaml.")
    return out


# --------------------------------------------------------------------------- model value

def arrivals_error(days, source) -> dict:
    """Mean absolute error of registration arrivals forecast for the next hour, in
    patients: over every tick, and over the ticks while an injected surge is under way."""
    every, in_surge = [], []
    for d in days:
        r = sim.day_run(d)
        per_min = np.zeros(1440 + 60)
        n = min(len(r.reg_per_min), 1440 - P.open)
        per_min[P.open:P.open + n] = r.reg_per_min[:n]
        cum = np.concatenate([[0.0], np.cumsum(per_min)])
        surges = []
        for ev in sim.day_spec(d).get("events", []):
            if ev["type"] == "demand_surge":
                h, m = ev["start"].split(":")
                start = int(h) * 60 + int(m)
                surges.append((start + 15, start + ev["duration"]))
        for clock in TICKS:
            ra = api.get_state(d, clock)["recent_arrivals"]
            predicted = sum(arrival_rates(clock, sim.day_spec(d)["weekday"], ra[15], ra[30], ra[60], source))
            err = abs(predicted - (cum[clock + 60] - cum[clock]))
            every.append(err)
            if any(lo <= clock <= hi for lo, hi in surges):
                in_surge.append(err)
    return {"all": round(float(np.mean(every)), 2),
            "in_surge": round(float(np.mean(in_surge)), 2) if in_surge else None,
            "surge_ticks": len(in_surge)}


def run_model_value(days, views, baseline) -> dict:
    """What the learned arrival model adds: the same forecast and alert rule with the model
    replaced by 'arrivals stay at the usual level for this time of day'."""
    without = {d: watch(d, arrivals="no_model") for d in days}
    out = {"note": ("Same test days, same simulator and alert rule. 'without_model' forecasts "
                    "arrivals at the usual level for the time of day and weekday.")}
    for name, v, source in (("with_model", views, "model"), ("without_model", without, "no_model")):
        alerts = run_alerts(days, v)
        fc = run_forecast(days, v, baseline)["60"]
        arr = arrivals_error(days, source)
        out[name] = {
            "breaches_caught_early": alerts["breaches_caught_early"],
            "breaches_flagged_only_once_over": alerts["breaches_flagged_only_once_over"],
            "breaches_missed": alerts["breaches_missed"],
            "false_alarms_per_day": alerts["false_alarms_per_day"],
            "median_warning_min": alerts["median_warning_min"],
            "wait_error_60_min": fc["model"],
            "wait_error_60_min_busy": fc["busy"]["model"],
            "arrivals_error_next_hour": arr["all"],
            "arrivals_error_next_hour_in_surge": arr["in_surge"],
        }
    out["breaches"] = run_alerts(days, views)["breaches"]
    out["surge_test_days"] = sum(sim.day_spec(d)["scenario"] == "demand_surge" for d in days)
    return out


def main(quick=False):
    t0 = time.perf_counter()
    test = sim.day_ids("test")
    two = sim.day_ids("two_cause")
    results = {
        "generated_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "data_mode": P.data_mode,
        "test_days": len(test),
        "wait_limit_min": P.limit,
    }

    print("replaying test days ...")
    views = {d: watch(d, cause=not quick) for d in test}
    results["alerts"] = run_alerts(test, views)
    print("  alerts:", {k: results["alerts"][k] for k in ("precision", "recall", "median_warning_min",
                                                          "false_alarms_per_day", "false_alarms_per_day_no_rule")})
    if not quick:
        results["calibration"] = run_calibration()
        baseline = time_of_day_average()
        results["forecast"] = run_forecast(test, views, baseline)
        print("  forecast 60 min:", {k: results["forecast"]["60"][k] for k in ("model", "persistence", "time_of_day")})
        results["cause"] = run_cause(test, views)
        print("  cause:", results["cause"]["correct"], "of", results["cause"]["days_with_alert"])
        results["model_value"] = run_model_value(test, views, baseline)
        print("  with the model:   ", results["model_value"]["with_model"])
        print("  without the model:", results["model_value"]["without_model"])

        print("robustness: noisy view ...")
        noisy_views = {d: watch(d, noise=True) for d in test}
        print("robustness: two-cause days ...")
        two_views = {d: watch(d) for d in two}
        results["robustness"] = {
            "noisy": {"forecast": run_forecast(test, noisy_views, baseline),
                      "alerts": run_alerts(test, noisy_views),
                      "cause": run_cause(test, noisy_views)},
            "two_cause": {"days": len(two),
                          "forecast": run_forecast(two, two_views, baseline),
                          "alerts": run_alerts(two, two_views),
                          "cause": run_cause(two, two_views)},
        }
        print("  noisy alerts:", {k: results["robustness"]["noisy"]["alerts"][k] for k in ("precision", "recall", "median_warning_min", "false_alarms_per_day")})

    print("policies ...")
    results["policy"] = run_policies(test)
    pol = results["policy"]
    for name in ("fixed", "reactive", "tool"):
        print(f"  {name:9s}", {k: pol[name][k] for k in ("share_over_30", "total_wait_hours", "moves")})
    saved = pol["reactive"]["wait_hours_per_day"] - pol["tool"]["wait_hours_per_day"]
    results["impact"] = {
        "wait_hours_saved_per_day_vs_reactive": round(saved, 2),
        "wait_hours_saved_per_day_vs_fixed": round(pol["fixed"]["wait_hours_per_day"] - pol["tool"]["wait_hours_per_day"], 2),
        "clinic_days_per_year_assumed": CLINIC_DAYS_PER_YEAR,
        "wait_hours_saved_per_year_vs_reactive": round(saved * CLINIC_DAYS_PER_YEAR),
        "note": ("Per-day figures are averages over the 20 test days, half of which carry an "
                 "injected disruption; a real clinic's mix of good and bad days will differ."),
    }
    results["assumptions"] = assumptions()
    results["runtime_seconds"] = round(time.perf_counter() - t0, 1)
    out = ROOT / "eval" / "results.json"
    out.write_text(json.dumps(results, indent=2) + "\n", encoding="utf-8")
    print(f"wrote {out} in {results['runtime_seconds']}s")


if __name__ == "__main__":
    main(quick="--quick" in sys.argv)
