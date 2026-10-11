# Services Bottleneck Predictor

**Tells an outpatient shift supervisor which station will overload next, why, and which staff move prevents it.**

Prototype use case: hospital outpatient services. Built for Track 1 (Predictive Model).

**Live demo:** [bottleneck-predictor.vercel.app](https://bottleneck-predictor.vercel.app/) · **Docs:** [PRD](docs/PRD.md) · [TRD](docs/TRD.md) · [Design](docs/DESIGN.md)

---

## Contents

- [The problem](#the-problem)
- [What it does](#what-it-does)
- [Quick start](#quick-start)
- [Using the demo](#using-the-demo)
- [How it works](#how-it-works)
- [Repository layout](#repository-layout)
- [Data](#data)
- [Evaluation](#evaluation)
- [Assumptions and limits](#assumptions-and-limits)
- [Team](#team)

## The problem

Outpatient staff are assigned to stations at the start of the day, but the bottleneck moves during it: registration clears, consultation fills, pharmacy piles up late. The supervisor sees it only when the waiting room is full, and a backlog that builds in 20 minutes takes hours to clear.

The cost is patients leaving without medication, delayed care, staff overtime and rushed consultations.

## What it does

| Stage | Question | On screen |
| --- | --- | --- |
| **Detect** | Which station will pass a 30-minute wait, and when? | Wait now and expected wait for each station |
| **Categorize** | What kind of problem is it? | Demand surge, staffing gap, slow processing, peak load or mixed |
| **Prioritize** | Which problem first? | One "Do this now" card; the rest ranked below |
| **Explain** | Why believe it? | Three plain sentences; cause bars on request |
| **Recommend** | What should I do? | One allowed staff move, its gain, its cost and the next bottleneck |

It is one screen with no login. It is deliberately not a dashboard: the screen leads with an action, and stays quiet when nothing needs doing.

## Quick start

Requires Python 3.11 or later and Node.js 20 or later.

```bash
git clone https://github.com/wiiiren/TheHonoredOnes.git
cd TheHonoredOnes
pip install -r requirements-dev.txt
npm install
npm run dev
```

Then open http://localhost:3000. `npm run dev` starts the Next.js front end and the Python API (uvicorn on port 8000) together; the front end proxies `/api/py/*` to the API.

Run commands from the repository root.

| Task | Command |
| --- | --- |
| Run the app | `npm run dev` |
| Build the front end | `npm run build` (also `npm run lint`, `npm run typecheck`) |
| Regenerate all results | `python eval/run_eval.py` |
| Check the engine and the API | `python -m pytest tests/` |
| Check a prepared CSV | `python engine/calibrate.py check data/raw/HospitalOPD-noname.csv` |
| Rebuild calibration from the real log | `python engine/calibrate.py` |

### Deploy

The app deploys to [Vercel](https://vercel.com) as one project: the Next.js front end, plus `api/index.py` as a Python function that runs the engine. `requirements.txt` lists only what the function needs.

- **From the command line:** `npx vercel login`, then `npx vercel --prod` from the repository root.
- **From GitHub:** import the repository at vercel.com/new and keep the detected Next.js settings. Every push to the production branch redeploys.

Open the public link in a private window to confirm it loads with no login. Tag each working checkpoint (`git tag checkpoint-1 && git push --tags`), and redeploy the last tag if a push breaks the live link.

## Using the demo

1. Pick a day: **Ordinary busy day**, **Doctor called away**, **Holiday rush** or **Records system slow**.
2. Press **Play**. The clinic replays in 5-minute steps from 08:00 to 16:00.
3. When a card appears, read the action and its cause. Open **Why?** for the cause breakdown or **What if?** for other moves.
4. Press **Apply** to make the move. The replay changes course and shows the day's outcome with and without it.
5. Open **Why trust this?** for the evaluation results and assumptions.

## How it works

One forward simulator of the clinic is used three ways:

| Use | Method |
| --- | --- |
| Forecast | Simulate the next 60 minutes from the current state, 30 times. The share of runs over the limit is the chance of a breach. |
| Cause | Repeat with one driver reset to normal (arrivals, staff, or service speed). The reset that removes the most wait is the cause. |
| Recommendation | Repeat with each allowed staff move applied. Keep the move that saves the most waiting overall. |

A gradient-boosted model forecasts arrivals so that surges are picked up early. An alert is raised only when the chance of a breach is high on two consecutive checks, which keeps false alarms down.

Full detail is in the [TRD](docs/TRD.md).

## Repository layout

```text
config.yaml        every tunable value: stations, staff, limits, allowed moves
engine/            simulator, forecast, cause, recommendation
  api.py           the six functions the app uses
  mock.py          stand-in outputs in the same shapes, used until each real function lands
api/index.py       the web API (FastAPI): /api/py/meta and /api/py/screen; a Vercel Python function
presenter/         turns engine results into what the screen shows
  view.py          the only caller of engine/api.py: cached calls turned into display models
  wording.py       sentence templates and number formatting
src/               the Next.js front end (App Router, Tailwind CSS, shadcn/ui)
  app/             layout, page, theme
  components/dashboard/  header, replay controls, patient flow, action card, side cards, evidence
  components/ui/   shadcn/ui components
  hooks/use-replay.ts    replay clock, play loop, applied moves
  lib/             API client, types
vercel.json        Python function settings for deployment
data/              day specs, calibration, demo days
models/            trained arrival forecaster
eval/              evaluation script and results.json
tests/             engine contract, engine and API tests
docs/              PRD, TRD, design
```

## Data

| Source | Used for |
| --- | --- |
| [HospitalOPD event log](https://data.mendeley.com/datasets/j2hd2239dr/1) (Mendeley Data, DOI 10.17632/j2hd2239dr.1, CC BY 4.0) | Calibrating the arrival pattern by hour and weekday, and the laboratory and imaging shares |
| Simulated clinic days | Training, tuning, testing, what-ifs and the policy comparison |

A real log cannot answer "what if we had moved someone" and has no cause labels, so results come from simulated days: 60 to train, 10 to tune, 20 held out for testing.

Put the raw CSV at `data/raw/HospitalOPD-noname.csv`, or pass its path to the command. The `data/raw/` folder is ignored by git; do not commit raw event logs.

```bash
python engine/calibrate.py check data/raw/HospitalOPD-noname.csv
python engine/calibrate.py data/raw/HospitalOPD-noname.csv
```

Calibration writes only derived summary numbers to `data/calibration.json`. The engine uses that file automatically when `calibration.use` is `true` in `config.yaml`.

**This build is calibrated on the real log.** The log holds 62,422 event records (49,912 visits). Calibration uses 19,214 visits on 156 days, Monday to Saturday, 08:00 to 16:00, from 2025-09-01 to 2026-03-01, with timestamps shifted from UTC to UTC+5.

- **Measured from the log:** arrivals per hour, weekday pattern, and the share of patients sent to laboratory (13%) and imaging (12%).
- **Assumed, not measured:** service times, the pharmacy share and staff numbers. The log has no usable service durations, records pharmacy for under 1% of visits, and identifies only doctors.
- **Scaled:** real arrivals are multiplied by 0.75 so the assumed four-doctor clinic is 92% busy in the peak hour of an average weekday.

The raw file is not in this repository because it names individual doctors. Only the summary numbers in `data/calibration.json` are committed.

## Evaluation

`python eval/run_eval.py` writes `eval/results.json`. All results use the 20 held-out days.

| Run | Question | Result |
| --- | --- | --- |
| Forecast accuracy | Is the forecast better than two simple baselines? | Average error 60 minutes ahead is 1.6 minutes, against 2.5 for "the wait stays the same" and 2.3 for the usual wait at that time of day. When a station is busy (a wait of 10 minutes or more) the error is 9.9 minutes: well under "stays the same" (16.5) and level with the time-of-day average (9.8). |
| Alert quality | Are alerts early and rarely wrong? | Of 17 breaches, 9 were flagged before the limit was passed (median warning 30 minutes), 5 only once over it, and 3 were missed. There were 0.7 false alarms a day, against 1.4 without the two-checks-in-a-row rule. |
| What the learned model adds | Does the arrival model earn its place? | Replacing it with "arrivals stay at the usual level" leaves the average wait error unchanged (1.6 minutes either way). With the model, one more breach is flagged early (9 of 17 against 8) and one fewer is missed (3 against 4). During a surge the error in forecast arrivals falls from 8.8 to 7.8 patients an hour, on the 3 surge test days. Most of the predictive power comes from the simulation. |
| Cause accuracy | Is the named cause the true one? | Right on all 5 scenario days that raised an alert. The other 5 scenario days raised no alert. |
| Robustness | Does it hold up on noisy inputs and unseen two-cause days? | With noisy inputs it still flagged 9 of 17 breaches early and named the right cause on 6 of 6 days, but false alarms rose to 1.7 a day. On 12 unseen two-cause days it flagged 15 of 22 breaches early; on the 10 days with an alert it named one of the two true causes on 9 and "mixed" on 1. |
| Decision impact | Does following the tool beat a supervisor who reacts after the limit is passed? | Total waiting was 329 hours with the tool, 367 reacting and 426 with a fixed roster, across 2,066 patients. The tool beat reacting on 9 days, matched it on 11 and lost on none, using 21 staff moves against 16. The share of patients waiting over 30 minutes was 0.7% with the tool, 1.0% reacting and 5.2% with a fixed roster. |

Against a reacting supervisor that is 1.9 waiting hours saved a day, or about 580 hours a year assuming 300 clinic days. Half the test days carry an injected disruption, so a real clinic's mix of good and bad days will differ.

## Assumptions and limits

- Results are from simulated days, not a live clinic.
- Staff numbers and the five allowed moves are assumptions set in `config.yaml`.
- A moved staff member is assumed to work at full speed immediately.
- Patients do not abandon the queue in the simulation.
- The tool recommends staffing moves only. It makes no clinical decisions.

A pilot would need one thing from a hospital: a timestamped event-log export from its queue or records system.

## Team

**TheHonoredOnes**

| Role | Name | Area |
| --- | --- | --- |
| Frontend | Yap Yu Hang | App and delivery |
| Backend | Tan Wei Ren | Engine and evaluation |

## Acknowledgements

Batool, Komal; Mehmood, Arshad; Zafar, Saad (2026), "HospitalOPD", Mendeley Data, V1, doi: 10.17632/j2hd2239dr.1. Licensed under CC BY 4.0.
