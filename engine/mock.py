"""Hour-1 fakes: every contract function returning hard-coded values in the agreed shape.

The numbers are illustrative (they follow the worked example in DESIGN.md). The real
functions in the other engine modules return exactly these keys; tests/test_contract.py
enforces that.
"""

STATIONS = ("registration", "consultation", "laboratory", "imaging", "pharmacy")
CAUSES = ("demand_surge", "staffing_gap", "slow_processing")


def _clock(clock):
    if isinstance(clock, str):
        h, m = clock.split(":")
        return int(h) * 60 + int(m)
    return int(clock)


def get_state(day, clock, actions=()):
    def st(waiting, in_service, staff_on, wait, arr, svc, done):
        return {"waiting": waiting, "in_service": in_service, "staff_on": staff_on,
                "wait_now_min": wait, "arrivals_30m": arr, "service_min_30m": svc,
                "completed_30m": done}

    return {
        "day": day,
        "clock": _clock(clock),               # minutes since midnight
        "weekday": 0,                         # 0 = Monday
        "actions": tuple(actions),            # applied so far, each (action_id, start_minute)
        "recent_arrivals": {15: 6, 30: 11, 60: 21},   # clinic arrivals at registration
        "stations": {
            "registration": st(3, 2, 2, 6.0, 11, 4.1, 12),
            "consultation": st(7, 3, 3, 23.3, 10, 10.4, 8),
            "laboratory": st(1, 1, 1, 6.0, 3, 6.2, 3),
            "imaging": st(1, 1, 1, 12.0, 2, 11.5, 2),
            "pharmacy": st(4, 2, 2, 14.0, 7, 7.3, 6),
        },
    }


def forecast(state):
    def h(p50, p90, prob):
        return {"wait_p50": p50, "wait_p90": p90, "breach_prob": prob}

    return {
        "registration": {15: h(6.0, 10.0, 0.0), 30: h(6.0, 12.0, 0.0), 60: h(4.0, 10.0, 0.0)},
        "consultation": {15: h(30.0, 36.7, 0.47), 30: h(36.7, 46.7, 0.73), 60: h(41.0, 53.3, 0.8)},
        "laboratory": {15: h(6.0, 12.0, 0.0), 30: h(6.0, 18.0, 0.03), 60: h(6.0, 18.0, 0.07)},
        "imaging": {15: h(12.0, 24.0, 0.03), 30: h(12.0, 24.0, 0.07), 60: h(12.0, 36.0, 0.13)},
        "pharmacy": {15: h(14.0, 21.0, 0.03), 30: h(17.5, 28.0, 0.13), 60: h(24.5, 35.0, 0.43)},
    }


def diagnose(state, station):
    return {
        "cause": "staffing_gap",   # or demand_surge | slow_processing | mixed | peak_load
        "contributions": {"demand_surge": 2.1, "staffing_gap": 17.4, "slow_processing": 0.6},
    }


def recommend(state, station):
    if station != "consultation":
        return []   # the "no allowed move helps" case
    return [
        {"action_id": "open_reserve_room",
         "label": "Open the reserve room with the on-call doctor",
         "wait_saved_min": 12.3, "donor_station": None, "donor_wait_added_min": 0.0,
         "total_wait_saved_patient_min": 164.0,
         "bottleneck_after": "pharmacy", "bottleneck_after_min": 40},
        {"action_id": "nurse_to_lab",
         "label": "Send the float nurse to laboratory sample-taking",
         "wait_saved_min": 0.0, "donor_station": None, "donor_wait_added_min": 0.0,
         "total_wait_saved_patient_min": 6.0,
         "bottleneck_after": "consultation", "bottleneck_after_min": 20},
    ]   # best first; may be empty


def alerts(state):
    return [
        {"station": "consultation", "breach_prob": 0.8, "minutes_to_breach": 20,
         "patients_affected": 18, "priority": 237.6,
         "cause": "staffing_gap",
         "contributions": {"demand_surge": 2.1, "staffing_gap": 17.4, "slow_processing": 0.6},
         "top_action": recommend(state, "consultation")[0],
         "facts": {"staff_on": 3, "staff_roster": 4, "staff_type": "doctors",
                   "arrival_ratio": 1.1, "service_min_now": 10.4, "service_min_usual": 10.0,
                   "wait_now_min": 23.3, "wait_expected_min": 41.0, "minutes_over_limit": 11.0}},
        {"station": "pharmacy", "breach_prob": 0.43, "minutes_to_breach": 50,
         "patients_affected": 14, "priority": 21.7,
         "cause": "demand_surge",
         "contributions": {"demand_surge": 6.8, "staffing_gap": 0.0, "slow_processing": 0.9},
         "top_action": None,
         "facts": {"staff_on": 2, "staff_roster": 2, "staff_type": "pharmacists",
                   "arrival_ratio": 1.7, "service_min_now": 7.3, "service_min_usual": 7.0,
                   "wait_now_min": 14.0, "wait_expected_min": 24.5, "minutes_over_limit": 1.5}},
    ]   # highest priority first; empty when calm


def day_outcome(day, actions=()):
    return {"patients": 116, "share_over_30": 0.12 if actions else 0.31,
            "total_wait_hours": 21.5 if actions else 38.0}
