"""Everything between the engine and the screen.

The app uses only the six functions in engine/api.py. This module calls them
(cached, since every call is deterministic) and turns the results into small
display-ready dataclasses, which api/index.py sends to the browser as JSON.
"""

import dataclasses
import json
import logging
import sys
from functools import lru_cache
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from engine import api  # noqa: E402

from . import wording as w  # noqa: E402

log = logging.getLogger(__name__)

with open(ROOT / "config.yaml", encoding="utf-8") as f:
    CFG = yaml.safe_load(f)

OPEN, CLOSE = w.minutes_of(CFG["open"]), w.minutes_of(CFG["close"])
TICK = CFG.get("tick_min", 5)
LIMIT = CFG["wait_limit_min"]
CLEAR_AT = CFG["alert"]["clear_at"]
MOVES = {m["id"]: m for m in CFG["allowed_moves"]}
MOVE_MIN = CFG.get("action_duration_min", 60)
DATA_MISSING = "Demo data could not be loaded. Choose another day or press Reset."
USES_MOCK = getattr(api.get_state, "__module__", "") == "engine.mock"

# Picker name -> (scenario tag, icon). Day ids come from data/demo_days.json.
DAY_META = {
    "Ordinary busy day": ("Normal day", "calendar-days"),
    "Doctor called away": ("Staffing gap", "user-x"),
    "Holiday rush": ("Demand surge", "users"),
    "Records system slow": ("Slow processing", "hourglass"),
}
DEFAULT_DEMO_DAYS = {"Ordinary busy day": 0, "Doctor called away": 1,
                     "Holiday rush": 2, "Records system slow": 3}
SPEEDS = {"Slow": 1.0, "Normal": 0.5, "Fast": 0.2}  # seconds per 5-minute tick


def _load_demo_days():
    """data/demo_days.json maps picker names to day ids; either
    {"Name": day} or [{"name": ..., "day": ...}]."""
    path = ROOT / "data" / "demo_days.json"
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
        if isinstance(raw, list):
            raw = {d["name"]: d["day"] for d in raw}
        return {str(k): int(v) for k, v in raw.items()} or DEFAULT_DEMO_DAYS
    except Exception:  # noqa: BLE001 - fall back to the default days
        log.exception("could not read %s", path)
        return DEFAULT_DEMO_DAYS


def _load_results():
    path = ROOT / "eval" / "results.json"
    if not path.exists():
        return None
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:  # noqa: BLE001
        log.exception("could not read %s", path)
        return None


DEMO_DAYS = _load_demo_days()
RESULTS = _load_results()
FIRST_DAY = "Doctor called away" if "Doctor called away" in DEMO_DAYS else next(iter(DEMO_DAYS))


# ---------- cached engine calls ----------

@lru_cache(maxsize=4096)
def _view(day, clock, actions):
    state = api.get_state(day, clock, actions)
    return state, api.forecast(state), api.alerts(state)


@lru_cache(maxsize=4096)
def _recommend(day, clock, actions, station):
    return api.recommend(api.get_state(day, clock, actions), station)


@lru_cache(maxsize=512)
def _outcome(day, actions):
    return api.day_outcome(day, actions)


# ---------- display models ----------

@dataclasses.dataclass
class DayOption:
    name: str = ""
    tag: str = ""
    icon: str = "calendar-days"


@dataclasses.dataclass
class StationView:
    key: str = ""
    name: str = ""
    wait_now: int = 0
    trend: str = ""
    trend_dir: str = "flat"     # up | down | flat
    status: str = "ok"          # ok | watch | breach | over
    status_word: str = "OK"
    chance: int = 0             # chance of passing the limit within the hour, nearest 5%
    staff: str = ""
    waiting: int = 0
    fill: int = 0               # wait now as a share of the limit, for the meter
    focus: bool = False


@dataclasses.dataclass
class CauseBar:
    label: str = ""
    minutes: int = 0
    width: int = 0
    top: bool = False


@dataclasses.dataclass
class WhatIf:
    label: str = ""
    saved: int = 0
    added: int = 0
    after: str = ""


@dataclasses.dataclass
class ActionCard:
    station: str = ""
    station_name: str = ""
    label: str = "Do this now"  # "Move in progress" while an applied move is running here
    title: str = ""
    tone: str = "urgent"        # urgent | warn
    deadline: str = ""
    chance: int = 0
    what: str = ""
    why_head: str = ""
    why_rest: str = ""
    affected: str = ""
    rank: str = ""              # why this alert is ranked where it is; empty when it is the only one
    helps: bool = False
    action_id: str = ""
    action_label: str = ""
    effect: str = ""
    no_move_title: str = "No move helps"
    no_move: str = ""
    causes: list[CauseBar] = dataclasses.field(default_factory=list)
    causes_note: str = ""
    what_ifs: list[WhatIf] = dataclasses.field(default_factory=list)


@dataclasses.dataclass
class Watching:
    station: str = ""
    name: str = ""
    when: str = ""
    cause: str = ""
    tone: str = "watch"         # watch | breach


@dataclasses.dataclass
class Applied:
    label: str = ""
    at: str = ""


@dataclasses.dataclass
class Outcome:
    without_pct: int = 0
    with_pct: int = 0
    without_label: str = ""
    with_label: str = ""


@dataclasses.dataclass
class Metric:
    value: str = ""
    caption: str = ""


@dataclasses.dataclass
class Screen:
    """One full render of the screen for a (day, clock, actions)."""
    mode: str = "calm"          # calm | watch | alert | closed | error
    stations: list[StationView] = dataclasses.field(default_factory=list)
    card: ActionCard = dataclasses.field(default_factory=ActionCard)
    note_title: str = ""
    note_body: str = ""
    watching: list[Watching] = dataclasses.field(default_factory=list)
    outcome: Outcome = dataclasses.field(default_factory=Outcome)
    show_outcome: bool = False


DAY_OPTIONS = [DayOption(n, *DAY_META.get(n, ("Demo day", "calendar-days"))) for n in DEMO_DAYS]
METRICS = [Metric(v, c) for v, c in w.trust_metrics(RESULTS)] if RESULTS else []
NOTES = w.trust_notes(RESULTS) if RESULTS else []
ASSUMPTIONS = list((RESULTS or {}).get("assumptions") or [])


# ---------- building a screen ----------

def _status(station, state, fc, alert_by_station):
    if w.whole(state["stations"][station]["wait_now_min"]) > LIMIT:
        return "over"
    if station in alert_by_station:
        return "breach"
    f = fc[station]
    if max(f[30]["breach_prob"], f[60]["breach_prob"]) >= CLEAR_AT:
        return "watch"
    return "ok"


def _station_view(station, state, fc, status, focus):
    s = state["stations"][station]
    f = fc[station]
    now, later = w.whole(s["wait_now_min"]), w.whole(f[30]["wait_p50"])
    trend, direction = w.trend(now, later, state["clock"])
    roster = CFG["stations"][station]["staff"]
    on = s["staff_on"]
    prob = max(f[30]["breach_prob"], f[60]["breach_prob"])
    return StationView(
        key=station, name=w.name(station), wait_now=now, trend=trend, trend_dir=direction,
        status=status, status_word=w.STATUS_WORD[status],
        chance=w.chance_pct(prob) if prob > 0 else 0,
        staff=f"{on} of {roster} {w.staff_noun(station, roster)}",
        waiting=int(s["waiting"]), fill=min(100, round(now / LIMIT * 100)) if LIMIT else 0,
        focus=station == focus,
    )


def _cause_bars(alert):
    contrib = alert.get("contributions") or {}
    keys = ("demand_surge", "staffing_gap", "slow_processing")
    minutes = {k: max(0, w.whole(contrib.get(k, 0))) for k in keys}
    top = max(minutes.values())
    return [CauseBar(label=w.CAUSE_NAMES[k].capitalize(), minutes=minutes[k],
                     width=round(minutes[k] / top * 100) if top else 0,
                     top=bool(top) and minutes[k] == top)
            for k in keys]


def _running_move(state, station):
    """(action_id, start) of the latest applied move still running at this station, or None."""
    clock = state["clock"]
    running = [(start, action_id) for action_id, start in state.get("actions", ())
               if start <= clock < start + MOVE_MIN
               and station in (MOVES.get(action_id, {}).get("to"),
                               MOVES.get(action_id, {}).get("station"))]
    if not running:
        return None
    start, action_id = max(running)
    return action_id, start


def _action_card(alert, state, fc, recs):
    clock = state["clock"]
    station = alert["station"]
    action = alert.get("top_action")
    helps = w.action_helps(action)
    head, rest = w.split_cause(w.why_sentence(alert, state, CFG))
    others = [r for r in recs if helps and r["action_id"] != action["action_id"]]
    # An applied move is already working here and nothing more helps: say so, rather
    # than telling the supervisor that no move helps.
    running = None if helps else _running_move(state, station)
    if running:
        label, title = "Move in progress", w.ACTION_KEEP.get(running[0], "Keep the applied move in place.")
        deadline = f"Running until {w.hhmm(running[1] + MOVE_MIN)}"
        no_move_title = "Already applied"
        no_move = w.running_sentence(alert, fc, running[1], running[1] + MOVE_MIN)
    else:
        label, title = "Do this now", (action["label"] + ".") if helps else "Warn waiting patients."
        deadline = w.deadline(alert)
        no_move_title = "No move helps"
        no_move = "" if helps else w.no_move_sentence(alert, fc)
    return ActionCard(
        station=station, station_name=w.name(station),
        label=label, title=title,
        tone="urgent" if helps else "warn",
        deadline=deadline,
        chance=w.chance_pct(alert["breach_prob"]),
        what=w.what_sentence(alert, clock, LIMIT),
        why_head=head, why_rest=rest,
        affected=w.affected_sentence(alert) if alert.get("cause") != "peak_load" else "",
        helps=helps,
        action_id=action["action_id"] if helps else "",
        action_label=action["label"] if helps else "",
        effect=w.effect_sentence(action, station, fc, CFG) if helps else "",
        no_move_title=no_move_title, no_move=no_move,
        causes=_cause_bars(alert),
        causes_note=w.bars_sentence(alert),
        what_ifs=[WhatIf(label=r["label"], saved=w.whole(r["wait_saved_min"]),
                         added=w.whole(r["donor_wait_added_min"]) if r.get("donor_station") else 0,
                         after=w.name(r.get("bottleneck_after")) or "None")
                  for r in others],
    )


def _outcome_view(day, actions):
    without, with_ = _outcome(day, ()), _outcome(day, actions)
    one = len(actions) == 1
    return Outcome(without_pct=w.pct(without["share_over_30"]), with_pct=w.pct(with_["share_over_30"]),
                   without_label="without this move" if one else "without these moves",
                   with_label="with it" if one else "with them")


def build(day, clock, actions, selected=""):
    """The whole screen for one moment of the replay. Raises on engine errors."""
    state, fc, alert_list = _view(day, clock, actions)
    alert_by_station = {a["station"]: a for a in alert_list}
    focus = alert_by_station.get(selected) or (alert_list[0] if alert_list else None)
    focus_station = focus["station"] if focus else ""
    statuses = {s: _status(s, state, fc, alert_by_station) for s in w.STATIONS}
    screen = Screen(stations=[_station_view(s, state, fc, statuses[s], focus_station)
                              for s in w.STATIONS])

    if actions:
        screen.outcome = _outcome_view(day, actions)
        screen.show_outcome = True

    if clock >= CLOSE:
        final = _outcome(day, actions)
        screen.mode = "closed"
        screen.note_title = "Clinic closed"
        screen.note_body = (f"Patients who waited over {LIMIT} minutes today: "
                            f"{w.pct(final['share_over_30'])}% of {final['patients']}.")
        return screen

    if focus is not None:
        screen.mode = "alert"
        screen.card = _action_card(focus, state, fc, _recommend(day, clock, actions, focus_station))
        if len(alert_list) > 1:
            screen.card.rank = w.rank_sentence(focus, alert_list.index(focus), len(alert_list))
    else:
        watching = [s for s in w.STATIONS if statuses[s] == "watch"]
        if watching:
            screen.mode = "watch"
            screen.note_title = "No action needed yet"
            screen.note_body = f"Keeping an eye on {' and '.join(w.name(s) for s in watching)}."
        else:
            screen.mode = "calm"
            screen.note_title = "No action needed"
            screen.note_body = (f"All stations are expected to stay under {LIMIT} minutes "
                                f"for the next hour.")

    screen.watching = [
        Watching(station=a["station"], name=w.name(a["station"]), when=w.watching_when(a),
                 cause=w.CAUSE_NAMES.get(a.get("cause"), "").capitalize(),
                 tone="breach" if statuses[a["station"]] in ("breach", "over") else "watch")
        for a in alert_list if a["station"] != focus_station
    ]
    return screen
