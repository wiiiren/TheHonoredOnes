"""The web API: input checks and the replay story on a demo day.

Run from the repository root: python -m pytest tests/
"""
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from fastapi.testclient import TestClient  # noqa: E402

from api.index import app  # noqa: E402
from presenter import view, wording  # noqa: E402

client = TestClient(app)
DAY = "Doctor called away"


def screen(**params):
    return client.get("/api/py/screen", params={"day": DAY, **params})


def test_health_and_meta():
    assert client.get("/api/py/health").json()["ok"] is True
    meta = client.get("/api/py/meta").json()
    assert meta["open"] == view.OPEN and meta["close"] == view.CLOSE
    assert [d["name"] for d in meta["days"]] == list(view.DEMO_DAYS)
    assert meta["defaultDay"] in view.DEMO_DAYS


def test_rejects_bad_input():
    assert client.get("/api/py/screen", params={"day": "Nope", "clock": view.OPEN}).status_code == 400
    assert screen(clock=view.OPEN + 1).status_code == 400
    assert screen(clock=view.CLOSE + view.TICK).status_code == 400
    assert screen(clock=600, actions="delete_everything@600").status_code == 400
    assert screen(clock=600, actions="open_reserve_room@700").status_code == 400


def test_every_step_of_every_demo_day_renders():
    for day in view.DEMO_DAYS:
        for clock in range(view.OPEN, view.CLOSE + 1, view.TICK * 6):
            r = client.get("/api/py/screen", params={"day": day, "clock": clock})
            assert r.status_code == 200, (day, clock, r.text)
            body = r.json()
            assert len(body["stations"]) == 5
            assert body["mode"] in ("calm", "watch", "alert", "closed")


def test_surge_sentence_uses_the_engine_ratio():
    state = {"clock": 690, "stations": {"registration": {"staff_on": 2, "arrivals_30m": 16,
                                                         "service_min_30m": 4.0}}}

    def why(ratio):
        alert = {"station": "registration", "cause": "demand_surge",
                 "facts": {"arrival_ratio": ratio}}
        return wording.why_sentence(alert, state, view.CFG)

    assert "about 60% above" in why(1.6)
    assert "about 2 times" in why(2.1)
    assert "More patients than usual" in why(1.0)


def test_apply_changes_the_day():
    first = None
    for clock in range(view.OPEN, view.CLOSE, view.TICK):
        body = screen(clock=clock).json()
        if body["mode"] == "alert" and body["card"]["helps"]:
            first = (clock, body["card"]["action_id"])
            break
    assert first, "the demo day never recommends a move"
    clock, action = first
    after = screen(clock=clock + view.TICK, actions=f"{action}@{clock}").json()
    assert after["show_outcome"] is True
    assert after["outcome"]["with_pct"] <= after["outcome"]["without_pct"]
    closed = screen(clock=view.CLOSE, actions=f"{action}@{clock}").json()
    assert closed["mode"] == "closed"


def test_card_explains_its_rank_only_when_alerts_compete():
    ranked = alone = 0
    for day in view.DEMO_DAYS:
        for clock in range(view.OPEN, view.CLOSE, view.TICK):
            body = client.get("/api/py/screen", params={"day": day, "clock": clock}).json()
            if body["mode"] != "alert":
                continue
            rank = body["card"]["rank"]
            if body["watching"]:
                ranked += 1
                assert rank.startswith(f"Ranked first of {len(body['watching']) + 1}: "), rank
            else:
                alone += 1
                assert rank == ""
    assert ranked and alone


def test_effect_states_waiting_saved_across_the_clinic():
    action = {"action_id": "open_reserve_room", "label": "Open the reserve room",
              "wait_saved_min": 21.0, "donor_station": None, "donor_wait_added_min": 0.0,
              "total_wait_saved_patient_min": 290.0, "bottleneck_after": None}
    fc = {s: {60: {"breach_prob": 0.0}} for s in wording.STATIONS}
    sentence = wording.effect_sentence(action, "consultation", fc, view.CFG)
    assert "saving about 5 patient-hours of waiting across the clinic in that hour." in sentence
    assert wording.saved_phrase(40) == "40 patient-minutes"
    assert wording.saved_phrase(0) == ""


def test_wording_never_shows_impossible_numbers():
    assert wording.staff_label("registration", 3, 2) == "3 clerks, 1 extra"
    assert wording.staff_label("consultation", 3, 4) == "3 of 4 doctors"
    assert wording.what_if_effect(-5.2) == "Adds 5 min here"
    assert wording.what_if_effect(4.6) == "Saves 5 min"
    assert wording.what_if_effect(0.2) == "No change here"
    note = wording.trust_notes({"policy": {"tool": {"share_over_30": 0.0068},
                                           "reactive": {"share_over_30": 0.0102}}})[0]
    assert "from 1.0% to 0.7%" in note


def test_card_acknowledges_a_running_move():
    first = None
    for clock in range(view.OPEN, view.CLOSE, view.TICK):
        card = screen(clock=clock).json()["card"]
        if card["helps"]:
            first = (clock, card["action_id"], card["station"])
            break
    assert first, "the demo day never recommends a move"
    start, action, station = first
    seen = 0
    for clock in range(start + view.TICK, start + view.MOVE_MIN, view.TICK):
        body = screen(clock=clock, actions=f"{action}@{start}").json()
        card = body["card"]
        if body["mode"] != "alert" or card["station"] != station or card["helps"]:
            continue
        seen += 1
        assert card["label"] == "Move in progress"
        assert card["title"] == wording.ACTION_KEEP[action]
        assert card["title"] != "Warn waiting patients."
    assert seen, "the alert never stayed raised while the move was running"
