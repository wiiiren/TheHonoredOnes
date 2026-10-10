"""Sentence templates (DESIGN.md section 5) and number formatting.

Every sentence is filled only with numbers from the engine. Writing rules:
whole numbers, "chance" not "probability", no model terms, three sentences at
most above the Apply button, always say what happens next.
"""

STATIONS = ["registration", "consultation", "laboratory", "imaging", "pharmacy"]

CAUSE_NAMES = {
    "demand_surge": "demand surge",
    "staffing_gap": "staffing gap",
    "slow_processing": "slow processing",
    "mixed": "mixed causes",
    "peak_load": "normal peak",
}

# (singular, plural) for the staff at each station.
STAFF_NOUN = {
    "registration": ("clerk", "clerks"),
    "consultation": ("doctor", "doctors"),
    "laboratory": ("technician", "technicians"),
    "imaging": ("radiographer", "radiographers"),
    "pharmacy": ("pharmacist", "pharmacists"),
}

# Each allowed move as a gerund, for "{Action} for an hour cuts ...".
ACTION_GERUND = {
    "clerk_to_pharmacy": "Moving a registration clerk to the pharmacy counter",
    "nurse_to_lab": "Sending the float nurse to laboratory sample-taking",
    "open_reserve_room": "Opening the reserve room",
    "open_third_desk": "Opening a third registration desk",
    "fast_track_pharmacy": "Fast-tracking repeat prescriptions",
}

# Each allowed move as an instruction to keep it going, for the card while it is running.
ACTION_KEEP = {
    "clerk_to_pharmacy": "Keep the clerk at the pharmacy counter.",
    "nurse_to_lab": "Keep the float nurse on laboratory sample-taking.",
    "open_reserve_room": "Keep the reserve room open.",
    "open_third_desk": "Keep the third registration desk open.",
    "fast_track_pharmacy": "Keep fast-tracking repeat prescriptions.",
}

STATUS_WORD = {"ok": "OK", "watch": "Watch", "breach": "Will breach", "over": "Over limit"}


# ---------- number formatting ----------

def hhmm(minutes):
    minutes = int(round(minutes))
    return f"{minutes // 60:02d}:{minutes % 60:02d}"


def minutes_of(hhmm_text):
    h, m = hhmm_text.split(":")
    return int(h) * 60 + int(m)


def whole(x):
    return int(round(float(x)))


def chance_pct(p):
    """Chance to the nearest 5%, kept between 5 and 95: never claims certainty."""
    return min(95, max(5, int(round(float(p) * 20) * 5)))


def chance(p):
    c = int(round(float(p) * 20) * 5)
    return "over 95% chance" if c > 95 else f"{max(c, 5)}% chance"


def pct(share):
    """Share of patients as a whole percentage; accepts 0-1 or 0-100."""
    share = float(share)
    return whole(share * 100 if share <= 1 else share)


def name(station):
    return station.capitalize() if station else ""


def staff_noun(station, n):
    singular, plural = STAFF_NOUN.get(station, ("member of staff", "staff"))
    return singular if n == 1 else plural


# ---------- sentences ----------

def deadline(alert):
    m = alert.get("minutes_to_breach")
    if m is None:
        return "Act within the hour"
    if m <= 0:
        return "Act now"
    return f"Act within {whole(m)} min"


def what_sentence(alert, clock, limit):
    st_name = name(alert["station"])
    c = chance(alert["breach_prob"])
    m = alert.get("minutes_to_breach")
    if m is None:
        return f"{st_name} is likely to pass the {limit}-minute limit within the hour ({c})."
    if m <= 0:
        return (f"{st_name} has already passed the {limit}-minute limit and is likely "
                f"to stay over it ({c}).")
    return f"{st_name} is likely to pass the {limit}-minute limit by {hhmm(clock + m)} ({c})."


def _top_two(contributions):
    ranked = sorted(contributions.items(), key=lambda kv: kv[1], reverse=True)
    return [CAUSE_NAMES.get(k, k) for k, _ in ranked[:2]]


def why_sentence(alert, state, cfg):
    station = alert["station"]
    cause = alert.get("cause")
    s = state["stations"][station]
    roster = cfg["stations"][station]["staff"]
    if cause == "staffing_gap":
        on = s["staff_on"]
        return f"Cause: staffing gap. {on} of {roster} {staff_noun(station, roster)} are on duty."
    if cause == "demand_surge":
        # Clinic arrivals in the last 30 minutes against the engine's usual level for this
        # time and weekday (calibrated, so not the assumed rates in config.yaml).
        ratio = (alert.get("facts") or {}).get("arrival_ratio") or 0
        if ratio >= 1.95:
            fact = f"Arrivals are about {whole(ratio)} times the usual level for this hour."
        elif ratio >= 1.05:
            fact = f"Arrivals are about {whole((ratio - 1) * 100)}% above the usual level for this hour."
        else:
            fact = "More patients than usual are reaching this station."
        return f"Cause: demand surge. {fact}"
    if cause == "slow_processing":
        now = whole(s["service_min_30m"])
        usual = whole(cfg["stations"][station]["service_min"])
        if now > usual:
            fact = f"Each patient is taking {now} minutes against the usual {usual}."
        else:
            fact = "Each patient is taking longer than usual."
        return f"Cause: slow processing. {fact}"
    if cause == "mixed":
        a, b = _top_two(alert.get("contributions", {}))
        return f"Causes: {a} and {b}, in roughly equal parts."
    if cause == "peak_load":
        return (f"Nothing unusual has happened; the normal peak is more than "
                f"{roster} {staff_noun(station, roster)} can clear.")
    return ""


def split_cause(sentence):
    """('Cause: staffing gap.', '3 of 4 doctors are on duty.') so the lead-in can be bold."""
    for lead in ("Cause:", "Causes:"):
        if sentence.startswith(lead):
            head, _, rest = sentence.partition(". ")
            return (head + ".", rest) if rest else (sentence, "")
    return "", sentence


def affected_sentence(alert):
    return f"About {whole(alert['patients_affected'])} patients will be affected."


def action_helps(action):
    return bool(action) and whole(action["wait_saved_min"]) >= 1


def effect_sentence(action, station, fc, cfg):
    gerund = ACTION_GERUND.get(action["action_id"], action["label"].rstrip("."))
    parts = [f"{gerund} for an hour cuts the {station} wait by about "
             f"{whole(action['wait_saved_min'])} minutes."]
    donor = action.get("donor_station")
    if donor:
        added = whole(action["donor_wait_added_min"])
        if added >= 1:
            parts.append(f"It adds about {added} minutes at {donor}.")
        else:
            parts.append(f"It adds no noticeable wait at {donor}.")
    parts.append(next_sentence(action.get("bottleneck_after"), station, fc, cfg))
    return " ".join(parts)


def next_sentence(after, station, fc, cfg):
    clear_at = cfg["alert"]["clear_at"]
    if not after or fc.get(after, {}).get(60, {}).get("breach_prob", 0) < clear_at:
        return "No other station is expected to pass the limit in the next hour."
    if after == station:
        return f"{name(station)} stays the busiest station."
    return f"{name(after)} then becomes the busiest station."


def no_move_sentence(alert, fc):
    f = fc[alert["station"]]
    wait = max(f[30]["wait_p50"], f[60]["wait_p50"])
    return (f"No allowed staff move reduces the wait. "
            f"Tell waiting patients to expect about {whole(wait)} minutes.")


def running_sentence(alert, fc, started, until):
    f = fc[alert["station"]]
    wait = max(f[30]["wait_p50"], f[60]["wait_p50"])
    return (f"Applied at {hhmm(started)} and running until {hhmm(until)}. No further allowed "
            f"move reduces the wait. Tell waiting patients to expect about {whole(wait)} minutes.")


def bars_sentence(alert):
    cause = alert.get("cause")
    if cause == "peak_load":
        return "No single cause stands out; this is the normal peak."
    if cause == "mixed":
        a, b = _top_two(alert.get("contributions", {}))
        return f"The expected wait comes from the {a} and the {b} in roughly equal parts."
    return f"Most of the expected wait comes from the {CAUSE_NAMES.get(cause, cause)}."


def trend(now, later, clock):
    """(sentence, direction) for the next 30 minutes at one station."""
    if abs(later - now) < 5:
        return "Steady for 30 min", "flat"
    if later > now:
        return f"Rising to {later} min by {hhmm(clock + 30)}", "up"
    return f"Falling to {later} min by {hhmm(clock + 30)}", "down"


def watching_when(alert):
    m = alert.get("minutes_to_breach")
    if m is None:
        return "May pass the limit within the hour"
    if m <= 0:
        return "Already past the limit"
    return f"May pass the limit in about {whole(m)} min"


# ---------- evidence (eval/results.json) ----------

AGAINST = "a supervisor who reacts only after the limit is passed"


def trust_metrics(r):
    """Headline numbers for 'Why trust this?'. Each is (value, caption); a metric
    is left out until its number exists."""
    out = []
    al = r.get("alerts") or {}
    if al.get("median_warning_min") is not None:
        out.append((f"{whole(al['median_warning_min'])} min",
                    "Median warning before a station passed the limit."))
    fa = al.get("false_alarms_per_day")
    if fa is not None:
        fa = float(fa)
        if fa == 0:
            out.append(("0", "False alarms on the test days."))
        else:
            caption = "False alarms per day on the test days."
            no_rule = al.get("false_alarms_per_day_no_rule")
            if no_rule is not None and float(no_rule) > fa:
                caption += (f" Raising an alert only after two checks in a row brings it down "
                            f"from {float(no_rule):.1f}.")
            out.append((f"{fa:.1f}", caption))
    cause = r.get("cause") or {}
    confusion = cause.get("confusion") or {}
    if confusion and all(isinstance(v, dict) for v in confusion.values()):
        # Days with no alert are a missed warning, not a wrong cause; count them apart.
        alerted = sum(n for row in confusion.values() for k, n in row.items() if k != "no_alert")
        missed = sum(row.get("no_alert", 0) for row in confusion.values())
        right = sum(row.get(true, 0) for true, row in confusion.items())
        if alerted:
            caption = "Right cause named on test days where it raised an alert."
            if missed:
                caption += f" On {missed} more it raised no alert."
            out.append((f"{right} of {alerted}", caption))
    elif cause.get("accuracy") is not None:
        out.append((f"{pct(cause['accuracy'])}%", "Right cause named on test cases."))
    pol = r.get("policy") or {}
    tool_h = (pol.get("tool") or {}).get("total_wait_hours")
    react_h = (pol.get("reactive") or {}).get("total_wait_hours")
    if tool_h is not None and react_h:
        cut = whole((react_h - tool_h) / react_h * 100)
        if cut > 0:
            out.append((f"{cut}%", f"Less total patient waiting than {AGAINST} "
                                   f"({whole(react_h)} to {whole(tool_h)} hours over the test days)."))
    return out


def trust_notes(r):
    """Fine print: the share-over-30 comparison, what is real, what is simulated, assumptions."""
    notes = []
    pol = r.get("policy") or {}
    tool = (pol.get("tool") or {}).get("share_over_30")
    reactive = (pol.get("reactive") or {}).get("share_over_30")
    if tool is not None and reactive is not None:
        t, rv = pct(tool), pct(reactive)
        if t < rv:
            notes.append(f"Following the top action cut patients waiting over 30 minutes from "
                         f"{rv}% to {t}%, against {AGAINST}.")
        elif t == rv:
            notes.append(f"The share of patients waiting over 30 minutes was about the same: "
                         f"{t}% with the tool and {rv}% reacting.")
        else:
            notes.append(f"Patients waiting over 30 minutes: {t}% with the tool, {rv}% reacting.")
    calibration_note = (r.get("calibration") or {}).get("note")
    if r.get("data_mode") == "calibrated" and calibration_note:
        notes.append(f"What is real: {calibration_note[0].lower()}{calibration_note[1:]}")
    elif r.get("data_mode") == "calibrated":
        notes.append("What is real: the arrival pattern and pathway shares are calibrated "
                     "on a public outpatient event log.")
    else:
        notes.append("What is assumed: arrival pattern, service times and staff numbers are "
                     "stated assumptions, not measured from a real clinic.")
    days = r.get("test_days") or 20
    notes.append(f"What is simulated: results are from {days} simulated test days "
                 f"not used to build the model.")
    return notes
