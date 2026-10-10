"""diagnose() and the priority score.

Cause-finding re-runs the forecast three times with the same random draws, each time
resetting one driver across the whole clinic. The wait that reset removes at the target
station is that cause's contribution.
"""
from __future__ import annotations

import numpy as np

from .forecast import project
from .sim import CAUSES, STATIONS, params

RERUNS = {
    "demand_surge": {"arrivals": "usual"},     # arrivals at the usual level for the time of day
    "staffing_gap": {"staff": "roster"},       # staff back to the roster
    "slow_processing": {"speed": "normal"},    # service time back to the usual
}


def label(contributions, P=None) -> str:
    """Largest contribution wins; near-ties are mixed; nothing abnormal is peak_load."""
    d = (P or params()).cfg["diagnose"]
    ranked = sorted(contributions.items(), key=lambda kv: kv[1], reverse=True)
    (first, top), (_, second) = ranked[0], ranked[1]
    if top < d["min_contribution_min"]:
        return "peak_load"      # the roster is simply too thin for the normal peak
    if second >= d["mixed_ratio"] * top:
        return "mixed"
    return first


def diagnose(state, station):
    """{"cause", "contributions": {cause: minutes of wait removed}} for one station.

    cause is demand_surge, staffing_gap, slow_processing, mixed or peak_load.
    A contribution is the station's 60-minute wait in the forecast minus the same wait
    when that one driver is reset to normal, averaged over paired runs.
    """
    si = STATIONS.index(station)
    base = project(state).W[:, -1, si]
    contributions = {}
    for cause in CAUSES:
        rerun = project(state, **RERUNS[cause]).W[:, -1, si]
        contributions[cause] = round(max(float(np.mean(base - rerun)), 0.0), 1)
    return {"cause": label(contributions), "contributions": contributions}


def priority(proj, state, station) -> tuple:
    """(priority, patients_affected, minutes_over_limit) for a station.

    priority = chance of passing the limit x patients affected x expected minutes over the
    limit x station weight. It only orders alerts and is never shown as a number; the
    card shows the terms behind it.
    """
    P = params()
    si = STATIONS.index(station)
    patients = state["stations"][station]["waiting"] + float(proj.joined[:, si].mean())
    over = float(np.maximum(proj.W[:, :, si].max(axis=1) - P.limit, 0.0).mean())
    return proj.prob(si) * patients * over * P.weight[si], int(round(patients)), over
