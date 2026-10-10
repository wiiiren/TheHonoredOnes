"""recommend() and alerts().

Recommendations re-run the forecast once per allowed move, with the same random draws and
the move applied for the next 60 minutes. Every move is tested, not only those aimed at
the alerting station.
"""
from __future__ import annotations

from collections import OrderedDict
from copy import deepcopy

import numpy as np

from . import sim
from .diagnose import diagnose, label, priority
from .forecast import (alert_settings, breach_probs, expected_staff, fingerprint, project,
                       step_alert, usual_between)
from .sim import CAUSES, STATIONS, params


def available_moves(state) -> list:
    """Allowed moves that could start now: not already in force, and never one that
    would take a station's last staff member."""
    P = params()
    in_force = sim.active_actions(state["actions"], state["clock"], P)
    out = []
    for move in P.cfg["allowed_moves"]:
        if move["id"] in in_force:
            continue
        donor = move.get("from")
        if donor in STATIONS and state["stations"][donor]["staff_on"] < 2:
            continue
        out.append(move)
    return out


def recommend(state, station):
    """Allowed moves worth making for `station`, best first; may be empty.

    Each item: action_id, label, wait_saved_min (cut in the station's 60-minute wait),
    donor_station and donor_wait_added_min (None and 0.0 when the staff member comes from
    the float pool), total_wait_saved_patient_min (net patient-minutes of waiting saved
    across all stations over the hour), bottleneck_after (station most likely to pass the
    limit once the move is made, or None if none is at watch level) and
    bottleneck_after_min (minutes until it does).

    A move is kept only if it saves waiting overall and its donor station stays
    comfortable (wait under recommend.donor_max_wait_min all hour in 9 runs out of 10).
    Moves that cut this station's wait by at least recommend.min_gain_min come first,
    ordered by waiting saved across the clinic; if there are none the list is empty: no
    allowed move helps.
    """
    P = params()
    rules = P.cfg["recommend"]
    _, clear_at, _ = alert_settings(P)      # watch level
    si = STATIONS.index(station)
    base = project(state)
    base_prob = base.cum_breach()[-1]
    out = []
    for move in available_moves(state):
        alt = project(state, move=move["id"])
        after = alt.cum_breach()[-1]
        donor = move.get("from") if move.get("from") in STATIONS else None
        added = 0.0
        if donor:
            di = STATIONS.index(donor)
            added = float(np.mean(alt.W[:, -1, di] - base.W[:, -1, di]))
            # The donor must stay comfortable: in 9 runs out of 10 its wait stays under
            # donor_max_wait_min for the whole hour with the move made.
            if np.percentile(alt.W[:, :, di].max(axis=1), 90) > rules["donor_max_wait_min"]:
                continue
        total = float(np.mean(base.area.sum(axis=1) - alt.area.sum(axis=1)))
        if total < rules["min_total_saved_patient_min"]:
            continue                          # does not save waiting overall
        worst = int(np.argmax(after))
        watch = after[worst] >= clear_at
        out.append({
            "action_id": move["id"],
            "label": move["label"],
            "wait_saved_min": round(float(np.mean(base.W[:, -1, si] - alt.W[:, -1, si])), 1),
            "donor_station": donor,
            "donor_wait_added_min": round(max(added, 0.0), 1),
            "total_wait_saved_patient_min": round(total, 0),
            "bottleneck_after": STATIONS[worst] if watch else None,
            "bottleneck_after_min": alt.minutes_to_breach(worst) if watch else None,
        })
    # Best first: moves that really help this station, by waiting saved across the clinic.
    helps = [m for m in out if m["wait_saved_min"] >= rules["min_gain_min"]]
    if not helps:
        return []
    rest = [m for m in out if m["wait_saved_min"] < rules["min_gain_min"]]
    by_total = lambda m: (m["total_wait_saved_patient_min"], m["wait_saved_min"])  # noqa: E731
    return sorted(helps, key=by_total, reverse=True) + sorted(rest, key=by_total, reverse=True)


# Per station: (alert raised?, ticks at or above raise_at, ticks below clear_at,
#               ticks in this alert episode, contribution sums over the episode)
IDLE = (False, 0, 0, 0, (0.0,) * len(CAUSES))
_HISTORY: dict = {}
_ALERTS: OrderedDict = OrderedDict()


def advance(prev, state, settings=None) -> list:
    """Move every station's alert one tick forward to `state`.

    Applies the raise/clear rule, and while an alert stays raised adds this tick's cause
    contributions to the episode's running total. The cause on the card comes from that
    total, so it does not flip from tick to tick or change once the disruption ends but
    its backlog remains.
    """
    settings = settings or alert_settings()
    probs = breach_probs(state)
    out = []
    for si, name in enumerate(STATIONS):
        active, hi, lo, ticks, sums = prev[si]
        was_active = active
        active, hi, lo = step_alert((active, hi, lo), probs[si], settings)
        if not active:
            out.append((False, hi, lo, 0, IDLE[4]))
            continue
        found = diagnose(state, name)["contributions"]
        if not was_active:
            ticks, sums = 0, IDLE[4]
        out.append((True, hi, lo, ticks + 1,
                    tuple(total + found[c] for total, c in zip(sums, CAUSES))))
    return out


def episode_cause(tracked) -> dict:
    """{"cause", "contributions"} for one station's tracked alert: the average
    contribution of each cause over the ticks the alert has been raised."""
    ticks, sums = tracked[3], tracked[4]
    contributions = {c: round(total / max(ticks, 1), 1) for c, total in zip(CAUSES, sums)}
    return {"cause": label(contributions), "contributions": contributions}


def track(state) -> list:
    """Alert tracking for every station at `state`, replaying the rule from opening time.

    Earlier ticks come from get_state() on the same day and actions and are cached, so
    during a replay each tick costs one new forecast.
    """
    P = params()
    settings = alert_settings(P)
    day, clock, actions = state["day"], state["clock"], state["actions"]

    def key(t):
        return (day, t, sim.norm_actions(actions, upto=t), settings)

    todo = []
    t = clock - P.tick
    while t >= P.open and key(t) not in _HISTORY:
        todo.append(t)
        t -= P.tick
    prev = _HISTORY[key(t)] if t >= P.open else [IDLE] * len(STATIONS)
    for t in reversed(todo):
        prev = advance(prev, sim.get_state(day, t, actions), settings)
        _HISTORY[key(t)] = prev
    if len(_HISTORY) > 20000:
        _HISTORY.clear()
    return advance(prev, state, settings)


def alerts(state):
    """Raised alerts, highest priority first; empty when calm.

    Each item: station, breach_prob (chance of passing the limit within the hour),
    minutes_to_breach, patients_affected, priority, cause and contributions (averaged over
    the time this alert has been raised, so they are stable), top_action (the first item
    of recommend() or None) and facts (the numbers the card sentences need).
    """
    key = (fingerprint(state), alert_settings())
    if key in _ALERTS:
        return deepcopy(_ALERTS[key])
    P = params()
    tracked = track(state)
    proj = project(state)
    roster = expected_staff(state, P)
    clock, weekday = state["clock"], state["weekday"]
    usual_30 = usual_between(weekday, clock - 30, clock)
    ratio = state["recent_arrivals"][30] / usual_30 if usual_30 > 0 else 1.0
    out = []
    for si, name in enumerate(STATIONS):
        if not tracked[si][0]:
            continue
        st = state["stations"][name]
        cause = episode_cause(tracked[si])
        moves = recommend(state, name)
        score, patients, over = priority(proj, state, name)
        explained = sim.action_scale(state["actions"], si, clock, clock + 1, P)
        out.append({
            "station": name,
            "breach_prob": round(proj.prob(si), 3),
            "minutes_to_breach": proj.minutes_to_breach(si),
            "patients_affected": patients,
            "priority": round(score, 2),
            "cause": cause["cause"],
            "contributions": cause["contributions"],
            "top_action": moves[0] if moves else None,
            "facts": {
                "staff_on": st["staff_on"],
                "staff_roster": roster[si],
                "staff_type": P.cfg["stations"][name]["staff_label"],
                "arrival_ratio": round(ratio, 1),
                "service_min_now": st["service_min_30m"],
                "service_min_usual": round(P.service_min[si] * explained, 1),
                "wait_now_min": st["wait_now_min"],
                "wait_expected_min": round(float(np.median(proj.W[:, -1, si])), 1),
                "minutes_over_limit": round(over, 1),
            },
        })
    out.sort(key=lambda a: (a["priority"], a["breach_prob"]), reverse=True)
    _ALERTS[key] = out
    while len(_ALERTS) > 2500:
        _ALERTS.popitem(last=False)
    return deepcopy(out)
