# Product Requirements Document: Services Bottleneck Predictor

**Prototype use case:** Hospital outpatient services
**Hackathon track:** Track 1, Predictive Model
**Status:** Draft v1, 10 October 2026
**Related docs:** [TRD.md](TRD.md) (how it is built), [DESIGN.md](DESIGN.md) (what the screen looks like and says)

---

## 1. Summary

The Services Bottleneck Predictor tells an outpatient shift supervisor which station will overload in the next 15 to 60 minutes, why, and which staff move prevents it.

One-line pitch: *"We tell the outpatient supervisor which station will overload next, why, and which staff move prevents it."*

## 2. Problem

Outpatient departments assign staff to stations at the start of the day, but the bottleneck moves during it. Registration clears, consultation fills, pharmacy piles up late. The supervisor sees the problem only when the waiting room is already full.

Three properties make this expensive:

| Property | What it means |
| --- | --- |
| Queues are nonlinear | A station looks fine at 80% busy and fails at 95%. In the simplest queue model the average wait is almost five times longer. |
| Backlogs clear slowly | A backlog that builds in 20 minutes can take hours to clear, so acting 30 minutes late costs far more than acting 30 minutes early. |
| The loss is hidden | A patient who leaves without medication is not recorded as a queue failure. |

### What the failure costs

- Patients leave before being seen or before collecting medication.
- Care is delayed for ill and elderly patients who wait for hours.
- Staff work overtime when the clinic overruns.
- Consultations are rushed to clear the backlog.
- Complaints rise and staff burn out.

### Definition of failure used in this product

- **Breach:** the estimated wait at a station passes 30 minutes.
- **Headline measures:** share of patients who wait over 30 minutes at any station, and total patient waiting hours per day.

## 3. Users

| | Description |
| --- | --- |
| **Primary user** | Outpatient shift supervisor or nurse manager. Decides where staff work during the day. Not a data specialist. |
| **Decision supported** | Which staff member to move, to which station, in the next hour. |
| **Beneficiaries** | Patients (shorter waits), station staff (fewer overloads), hospital management (less overtime). |
| **Demo audience** | Hackathon judges. They must understand the screen in under 10 seconds. |

### Core user story

> As a shift supervisor, I want to be told before a station overloads, what is causing it, and what I can do about it, so that I can move staff while it is still cheap to fix.

## 4. Goals and non-goals

### Goals

1. Warn of a breach before it happens, with enough lead time to act.
2. Name the cause of each predicted breach in plain language.
3. Rank simultaneous problems so the supervisor knows which to handle first.
4. Recommend one concrete, allowed staff move and show its expected effect, including the cost elsewhere.
5. Stay quiet when nothing needs doing.
6. Prove, on held-out test days, that following the tool beats reacting after the fact.

### Non-goals

Following the organisers' advice, the prototype deliberately excludes:

- **Login**, accounts and user roles. The link opens straight into the demo.
- **A whole product.** No database, live data feed, settings screen, admin tools, notifications or integrations.
- **A dashboard.** No grid of charts and gauges. The screen leads with one recommended action.
- A second use case. Other service settings are mentioned in the pitch only.
- An LLM. Explanations are sentence templates filled with model numbers.
- Clinical decisions of any kind. The tool recommends staffing moves, not patient care.

## 5. The four-stage workflow

Every requirement below maps to one of the four stages in the hackathon brief, plus the recommendation step.

| Stage | Question answered | What the user sees |
| --- | --- | --- |
| **Detect** | Which station will breach, and when? | Each station's wait now and expected wait; a "will breach" status |
| **Categorize** | What kind of problem is it? | A cause label: demand surge, staffing gap, slow processing, peak load, or mixed |
| **Prioritize** | Which problem first? | One "Do this now" card; the rest ranked under "Also watching" |
| **Explain** | Why should I believe it? | Three plain sentences, plus cause bars on request |
| **Recommend** | What should I do? | One allowed staff move, its gain, its cost, and the next bottleneck |

## 6. Functional requirements

Priority: **M** = must have for the demo, **S** = should have, **C** = could have (first to cut).

### Detect

| ID | Requirement | Priority | Acceptance criterion |
| --- | --- | --- | --- |
| FR-1 | Show the current estimated wait for each of the five stations | M | Values update every 5-minute tick of the replay |
| FR-2 | Forecast the wait per station at 30 and 60 minutes ahead | M | Forecast shown beside the current wait |
| FR-3 | Forecast at 15 minutes ahead | C | Same as FR-2 |
| FR-4 | Compute a breach probability per station | M | Value between 0 and 1 from repeated forward simulation |
| FR-5 | Raise an alert only when breach probability is high on two consecutive ticks; clear it only after two low ticks | M | A single noisy tick never raises or clears an alert |

### Categorize

| ID | Requirement | Priority | Acceptance criterion |
| --- | --- | --- | --- |
| FR-6 | Label each alert with one cause: demand surge, staffing gap, slow processing | M | Each scenario type shows the correct label on its demo day |
| FR-7 | Label `mixed` when two causes contribute almost equally | S | Returned when the second contribution is at least 80% of the first |
| FR-8 | Label `peak_load` when nothing is abnormal and the roster is simply too thin | S | Returned when every contribution is under 3 minutes |
| FR-9 | Report how many minutes of wait each cause explains | M | Three values available for the "Why?" view |

### Prioritize

| ID | Requirement | Priority | Acceptance criterion |
| --- | --- | --- | --- |
| FR-10 | Score each alert by breach probability, patients affected, expected minutes over the limit, and station weight | M | Alerts returned sorted by score |
| FR-11 | Show the top alert as the single "Do this now" card | M | Exactly one card is prominent |
| FR-12 | List remaining alerts in rank order | M | One line each, highest first |
| FR-13 | Show a deadline to act for each alert | M | "Act within N minutes" |

### Explain

| ID | Requirement | Priority | Acceptance criterion |
| --- | --- | --- | --- |
| FR-14 | Explain each alert in at most three plain sentences built from model numbers | M | No model terms; whole numbers; readable aloud |
| FR-15 | Show cause contributions as three bars on request | M | Hidden until "Why?" is selected |
| FR-16 | Show evidence of reliability on request | M | "Why trust this?" section lists evaluation results and assumptions |

### Recommend

| ID | Requirement | Priority | Acceptance criterion |
| --- | --- | --- | --- |
| FR-17 | Recommend one staff move from a configured list of allowed moves | M | Never recommends moving a doctor or radiographer to another station |
| FR-18 | State the gain at the target station, the cost at the donor station, and the next bottleneck | M | All three appear in the action line |
| FR-19 | Let the user apply the move and see the replay change course | M | Station waits after Apply differ from the no-action replay |
| FR-20 | Show the day's outcome with and without the applied action | M | One line: share of patients waiting over 30 minutes, both cases |
| FR-21 | List alternative moves with their effects | C | Hidden until "What if?" is selected |
| FR-22 | Say so when no allowed move helps | S | Card states this and suggests informing patients |

### Demo

| ID | Requirement | Priority | Acceptance criterion |
| --- | --- | --- | --- |
| FR-23 | Replay a stored day with play, pause, speed and reset | M | Runs 08:00 to 16:00 without error |
| FR-24 | Offer four named demo days: ordinary busy day, doctor called away, holiday rush, records system slow | M | Each selectable by name |
| FR-25 | Show "No action needed" when there are no alerts | M | Visible for most of the ordinary busy day |

## 7. Non-functional requirements

| ID | Requirement | Target |
| --- | --- | --- |
| NFR-1 | Access | Public link, no login, opens directly into the demo |
| NFR-2 | Responsiveness | Each replay tick renders in under 2 seconds on the deployed app |
| NFR-3 | False alarms | Within a stated budget of one per day on tuning days |
| NFR-4 | Robustness | Results reported under a noisy view of the clinic and on unseen two-cause days |
| NFR-5 | Reproducibility | One command regenerates every reported number from a clean clone |
| NFR-6 | Plain language | A non-expert can state the recommended action and its reason after reading the card once |
| NFR-7 | Honesty | The app and pitch state which numbers come from real data and which from simulation |
| NFR-8 | Resilience | A missing file produces a plain message, never a stack trace |
| NFR-9 | Accessibility | Status is never shown by colour alone |

## 8. Success measures

Results are filled in from `eval/results.json` after the evaluation runs. No figure is claimed before it is measured.

| Measure | How it is measured | Target |
| --- | --- | --- |
| Forecast accuracy | Average wait error at 30 and 60 minutes, against two simple baselines | Better than both baselines at 60 minutes |
| Warning time | Median minutes between alert and breach | Long enough to act: at least 15 minutes |
| False alarms | Alerts with no breach within 60 minutes, per day | At most one per day |
| Cause accuracy | Share of scenario days labelled with the true cause | Reported as measured |
| Robustness | The three measures above under noise and on two-cause days | Reported as measured, with the drop stated |
| **Decision impact** | Share of patients waiting over 30 minutes under three policies on 20 held-out days | Tool-guided beats reactive |

The headline claim is the last row. The comparison that matters is tool-guided against **reactive** (move staff once a queue has already passed the limit), because beating "do nothing" proves little.

## 9. Scope of the prototype

| In scope | Out of scope |
| --- | --- |
| One outpatient department with five stations | Multiple departments or hospitals |
| Replay of simulated days | Live data connection |
| Simulator calibrated on a public event log where possible | Claims about a specific real hospital |
| Five allowed staff moves | Rostering, shift planning, leave management |
| One screen | Mobile layout, multiple pages, settings |
| English | Other languages |

## 10. Data and assumptions

| Item | Detail |
| --- | --- |
| Real data | HospitalOPD event log (Mendeley Data): 62,422 event records, April 2024 to April 2026, start and completion times across five outpatient activities. Used to calibrate arrival shape, service times and pathway shares, subject to a data check. |
| Simulated data | 90 simulated clinic days with known causes. Used for training, tuning, testing, what-ifs and the policy comparison. |
| Why both | A real log cannot answer "what if we had moved someone", and has no cause labels. A simulator alone is not grounded. |
| Staff numbers | Assumed unless the real log records staff. |
| Allowed moves | Assumed; to be confirmed with someone who works in a clinic if possible. |
| Wait limit | 30 minutes, configurable. |
| Station weights | A judgment call, stated in the pitch. |

All assumptions live in `config.yaml` and are listed in the README.

## 11. Risks

| Risk | Effect | Mitigation |
| --- | --- | --- |
| The real dataset is unusable or its licence is unclear | No real-data calibration | Fall back to stated assumptions; build is otherwise identical |
| Judges discount simulated results | Weaker proof | Calibrate on real data, show the calibration check, be explicit about what is simulated |
| Cause labels cannot be verified on real data | Categorize looks unproven | Verify on injected scenarios with known causes; report accuracy |
| The forecast does not beat the baselines | Detect looks weak | Report honestly; lead with alert quality and decision impact |
| The screen drifts into a dashboard | Goes against organisers' advice | Rule: no chart visible until something is clicked |
| The live link fails during judging | No demo | Open early; keep a recorded backup video |

## 12. Traceability to the hackathon brief

| Brief requirement | Covered by |
| --- | --- |
| Detect | FR-1 to FR-5 |
| Categorize | FR-6 to FR-9 |
| Prioritize | FR-10 to FR-13 |
| Explain | FR-14 to FR-16 |
| Solve a specific, real-world problem | Section 2 |
| Clearly identify the user | Section 3 |
| Support decision-making, not just prediction | FR-17 to FR-22 |
| Perform robustly on noisy or unfamiliar data | NFR-4 |
| Minimize false alarms | FR-5, FR-25, NFR-3 |
| Clearly communicate recommendations and reasoning | FR-14, FR-18 |
| Demonstrate measurable impact through realistic assumptions | Section 8, Section 10 |
| Core judging question: better decision, and proof | Decision impact measure in Section 8 |

## 13. Open questions

- Does the HospitalOPD log include a staff or resource column, and what is its licence?
- Are the five allowed moves realistic for a real outpatient department?
- What false-alarm budget would a real supervisor accept?
- Should a moved clerk count as a full extra pair of hands at pharmacy, or less?

## 14. Beyond the prototype

The same engine applies to any multi-station service by changing the configuration: university service counters, government offices, bank branches. A pilot needs one thing from the organisation: a timestamped event-log export from its queue or records system.
