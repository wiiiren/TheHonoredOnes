"""HTTP API for the web app. Deployed as a Vercel Python function; run locally
with `npm run dev` (uvicorn on port 8000, proxied by Next.js).

The engine is deterministic for (day, clock, actions), so the API is stateless:
the browser holds the replay clock and the applied moves and sends them on
every request.

GET /api/py/health   liveness
GET /api/py/meta     clinic hours, demo days, evidence from eval/results.json
GET /api/py/screen   the whole screen for one moment of a replay
"""

import dataclasses
import logging
import re
import sys
from pathlib import Path

from fastapi import FastAPI, HTTPException, Query
from fastapi.responses import JSONResponse

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from presenter import view  # noqa: E402

log = logging.getLogger("api")

app = FastAPI(
    title="Services Bottleneck Predictor API",
    docs_url="/api/py/docs",
    openapi_url="/api/py/openapi.json",
)

ALLOWED_MOVES = {m["id"] for m in view.CFG["allowed_moves"]}
MAX_ACTIONS = 24
ACTION_RE = re.compile(r"^([a-z_]+)@(\d{3,4})$")
CACHE_FOREVER = {"Cache-Control": "public, max-age=3600, s-maxage=86400"}


def _parse_actions(text: str, clock: int) -> tuple[tuple[str, int], ...]:
    """'open_reserve_room@665,clerk_to_pharmacy@700' -> (('open_reserve_room', 665), ...)."""
    if not text:
        return ()
    out = []
    for part in text.split(","):
        m = ACTION_RE.match(part.strip())
        if not m or m.group(1) not in ALLOWED_MOVES:
            raise HTTPException(400, f"Unknown move: {part.strip()[:40]}")
        at = int(m.group(2))
        if not view.OPEN <= at <= min(clock, view.CLOSE):
            raise HTTPException(400, "A move must start between opening and the current time.")
        out.append((m.group(1), at))
    if len(out) > MAX_ACTIONS:
        raise HTTPException(400, f"At most {MAX_ACTIONS} moves per day.")
    return tuple(sorted(set(out), key=lambda a: (a[1], a[0])))


@app.get("/api/py/health")
def health():
    return {"ok": True, "engine": "mock" if view.USES_MOCK else "live"}


@app.get("/api/py/meta")
def meta():
    body = {
        "open": view.OPEN,
        "close": view.CLOSE,
        "tick": view.TICK,
        "limit": view.LIMIT,
        "defaultDay": view.FIRST_DAY,
        "days": [dataclasses.asdict(d) for d in view.DAY_OPTIONS],
        "metrics": [dataclasses.asdict(m) for m in view.METRICS],
        "notes": view.NOTES,
        "assumptions": view.ASSUMPTIONS,
        "testDays": (view.RESULTS or {}).get("test_days"),
        "usesMock": view.USES_MOCK,
    }
    return JSONResponse(body, headers=CACHE_FOREVER)


@app.get("/api/py/screen")
def screen(
    day: str = Query(..., max_length=80),
    clock: int = Query(...),
    actions: str = Query("", max_length=1000),
    selected: str = Query("", max_length=40),
):
    if day not in view.DEMO_DAYS:
        raise HTTPException(400, "Unknown demo day.")
    if not view.OPEN <= clock <= view.CLOSE or (clock - view.OPEN) % view.TICK:
        raise HTTPException(400, "Clock must be a replay step between opening and closing.")
    moves = _parse_actions(actions, clock)
    try:
        result = view.build(view.DEMO_DAYS[day], clock, moves, selected)
    except Exception:  # noqa: BLE001 - never leak a stack trace to the browser
        log.exception("engine failed for %s at %s with %s", day, clock, moves)
        raise HTTPException(500, view.DATA_MISSING) from None
    # Same inputs always give the same screen, so the CDN may keep it.
    return JSONResponse(dataclasses.asdict(result), headers=CACHE_FOREVER)
