# Demo script

A 3-minute live demo of the Services Bottleneck Predictor, followed by answers to likely questions. Every time, number and sentence below is what the live app shows today on https://bottleneck-predictor.vercel.app/. If the engine, the demo days or the results change, re-check them.

## The story in one line

A supervisor sees a full waiting room too late. We warn them about 30 minutes earlier, say why, and name the staff move that prevents it.

## Before you present

Do this 10 minutes before your slot.

1. Open the link in a fresh private window on the presenting laptop. Set browser zoom so the whole action card is visible without scrolling.
2. Walk through the full click path below once, from start to finish. This loads every screen you will show, so the replay runs at full speed when it counts.
3. Press **Reset**, select **Doctor called away**, and leave the clock at 08:00 with speed on **Fast**.
4. Have the backup video open in another tab, and the app running locally (`npm run dev`) as a second fallback.
5. Agree who drives the screen and who speaks. One person doing both is fine; rehearse it twice with a timer.

## The 3-minute script

Replay controls used: the four **Demo day** buttons, **Play / Pause**, the **5 min** step button, and **Apply move** on the card. To stop on an exact time, play on Fast, pause a little early, then use **5 min** to step forward.

### 1. Problem and user (0:00 to 0:20)

**Do:** nothing. The screen shows "Doctor called away" at 08:00, "No action needed".

**Say:**
> "In an outpatient clinic, staff are assigned to stations in the morning, but the bottleneck moves during the day. The shift supervisor only notices when the waiting room is already full, and a queue that builds in twenty minutes takes hours to clear. Our tool tells that supervisor which station will overload next, why, and which staff move prevents it. Here is one morning, replayed."

### 2. Detect (0:20 to 0:50)

**Do:** press **Play**. Pause when the clock passes about 10:30. Press **5 min** until the card appears at **11:00**.

**Screen at 10:55:** "No action needed yet. Keeping an eye on Consultation."

**Screen at 11:00:** Consultation shows a 10-minute wait, "Rising to 20 min by 11:30", status **Will breach**, 55% chance, "3 of 4 doctors".

**Say:**
> "For three hours the screen says no action needed. At 10:55 it starts watching consultation but does not raise an alarm. Five minutes later it does. Look at the wait: ten minutes. Nobody in the waiting room would call this a problem yet. The tool says consultation will pass the thirty-minute limit by 11:35."

### 3. Categorize and explain (0:50 to 1:20)

**Do:** read the card aloud, then open **Why?**

**Card:** "Open the reserve room with the on-call doctor." / "Consultation is likely to pass the 30-minute limit by 11:35 (55% chance). Cause: staffing gap. 3 of 4 doctors are on duty. About 27 patients will be affected." / "Act within 35 min".

**Why? bars:** Staffing gap 21 min, Demand surge 2 min, Slow processing 0 min.

**Say:**
> "It does not only predict. It names the cause: a staffing gap, three of four doctors on duty, a doctor was called to the ward. It gets there by re-running the next hour three times, each time putting one thing back to normal: arrivals, staffing, service speed. Restoring the doctor removes twenty-one minutes of the wait. A surge would explain two. So the answer is staff, not volume."

### 4. Recommend and act (1:20 to 1:55)

**Do:** point at **Expected effect**, press **Apply move**, then press **5 min** once. Stop there.

**Expected effect:** "Opening the reserve room for an hour cuts the consultation wait by about 21 minutes, saving about 3 patient-hours of waiting across the clinic in that hour. No other station is expected to pass the limit in the next hour."

**Screen at 11:05 after Apply:** "No action needed". Consultation is back to **OK** with 4 of 4 doctors. The **Moves applied** panel reads "Patients waiting over 30 min today: 22% without this move, 1% with it".

**Say:**
> "The recommendation is one move the clinic is allowed to make, with what it gains and what it costs: twenty-one minutes off the consultation wait, about three patient-hours of waiting saved in the next hour. It only suggests moves staff are qualified for: it never sends a doctor or a radiographer to another station. I apply it. Five minutes later consultation is back to OK. And here is the whole day: without this move, twenty-two percent of patients wait over thirty minutes. With it, one percent."

### 5. Prioritize (1:55 to 2:20)

**Do:** select **Holiday rush**. Press **Play**, pause near 10:30, step with **5 min** to **10:50**. Point at **Also watching**. Step once more to **10:55**. Do not press Apply on this day.

**Screen at 10:50:** card is Registration, "Open a third registration desk with the float clerk", cause demand surge, "Arrivals are about 2 times the usual level for this hour". Under it: "Ranked first of 2: 41 patients affected, 50% chance, about 4 minutes over the limit." **Also watching (1):** Consultation, "May pass the limit in about 45 min", Demand surge.

**Screen at 10:55:** the two swap. The card is now Consultation, "Open the reserve room with the on-call doctor", "Ranked first of 2: 36 patients affected, 55% chance, about 5 minutes over the limit."; Registration moves to Also watching.

**Say:**
> "A different morning: a walk-in rush, arrivals at double the usual level. Now two stations are at risk. The tool shows one action, ranks the rest below it, and says why on the card: forty-one patients affected, a fifty percent chance, four minutes over the limit. The ranking is those three numbers multiplied together, times a weight for the station. Five minutes later the order flips: the rush has moved on from registration to consultation, and the card moves with it. This is the bottleneck moving, which is what a fixed roster cannot follow."

### 6. False alarms (2:20 to 2:35)

**Do:** select **Ordinary busy day** and press **Play**. Let it run while you speak.

**Screen:** "No action needed" all day. It shows "No action needed yet" briefly at 11:05 and 11:30, and never raises an alert.

**Say:**
> "An alarm that cries wolf gets ignored. On an ordinary busy day the tool watches the peak and stays quiet. It only raises an alert after two checks in a row agree."

### 7. Proof (2:35 to 3:00)

**Do:** scroll to **Why trust this?**

**Tiles:** "30 min" median warning. "0.7" false alarms per day. "5 of 5" right cause. "10%" less total patient waiting.

**Say:**
> "We tested on twenty simulated clinic days the model never saw. Median warning: thirty minutes before the limit. Less than one false alarm a day. The right cause every time it raised an alert. And against a good supervisor who reacts once a queue is already over the limit, with the same staff and the same moves, following the tool cut total patient waiting by ten percent. To be clear about what is real: the arrival pattern comes from a public hospital log of nineteen thousand visits. Staffing, service times and the results are simulated. A pilot needs one thing from a hospital: a timestamped export from its queue system."

## If something goes wrong

| Problem | What to do |
| --- | --- |
| You paused late on "Doctor called away" (11:05 to 11:15) | Carry on. The card is the same with a higher chance. After Apply the day still ends at 1%, but the next step shows "Move in progress: Keep the reserve room open" rather than "No action needed". Say: "the move is running; the tool tells you to keep it in place." |
| You overshot on "Holiday rush" | Press **Reset** and replay, or describe the swap from the 10:55 screen alone. |
| The replay is slow or stalls | Keep talking over it. If it does not recover in 10 seconds, switch to the local app or the backup video. |
| "The clinic engine is not responding" | Press **Try again** once, then switch to the backup. |

## What not to click

These are real behaviours of the current build that distract from the story.

- **Do not press Apply on "Holiday rush".** Applying only the first move there makes the whole-day line read 16% to 28%: the third desk pushes the rush into consultation faster. Following every recommendation through the day brings it to 2%, but that takes five moves and more time than you have.
- **Do not keep playing "Doctor called away" past 11:10 after Apply.** The card then shows a 95% chance and "expect about 53 minutes", though the wait stays under 30.
- **Do not play "Holiday rush" past 11:20.** Later cards name "slow processing" at pharmacy on a surge day.
- **Do not open "What if?"** on the 11:00 card. One line reads "Saves -5 min".
- **Do not open "Data and assumptions"** unless asked. Its first line rounds the over-30 share to "1% with the tool and 1% reacting"; the unrounded figures are 0.7% and 1.0%.

## Optional extra, if you are asked for a third cause

Select **Records system slow**, play to **10:55**. The card reads "Cause: slow processing. Each patient is taking 16 minutes against the usual 10", and recommends opening the reserve room. Pressing Apply there takes the day from 8% of patients over 30 minutes to 0%.

## Likely questions

**What is real and what is simulated?**
The arrival pattern by hour and weekday, and the share of patients sent to laboratory and imaging, are measured from the public HospitalOPD log (19,214 visits on 156 days). Service times, staff numbers, the pharmacy share and the five allowed moves are assumptions. Every result is from simulated days.

**Why simulate at all?**
A real log cannot answer "what if we had moved someone", and it has no labels for the cause. A simulator can do both.

**How does the forecast work?**
It simulates the next 60 minutes from the current queues 30 times. The share of runs over 30 minutes is the chance of a breach. A gradient-boosted model, trained on 60 simulated days, forecasts arrivals so a surge is picked up from recent arrivals.

**Is it better than a simple guess?**
Sixty minutes ahead the average error is 1.6 minutes, against 2.5 for "the wait stays the same" and 2.3 for the usual wait at that time of day. When a station is busy the error is 9.9 minutes: well ahead of "stays the same" (16.5) and level with the time-of-day average (9.8).

**How many problems does it miss?**
Of 17 breaches on the test days, it flagged 9 before the limit was passed, 5 only once the wait was over it, and missed 3.

**How do you keep false alarms down?**
An alert needs a 30% chance or more on two checks in a row, and clears below 20%. That rule halves false alarms, from 1.4 to 0.7 a day. The thresholds were chosen on 10 separate tuning days with a budget of one false alarm a day.

**How often is the cause right?**
On all 5 scenario test days that raised an alert. On the other 5 scenario days it raised no alert.

**Does it hold up on messy data?**
With noisy inputs (queue counts, arrivals and service times all perturbed) it flagged the same 9 of 17 breaches early and named the right cause on 6 of 6 days, but false alarms rose to 1.7 a day. On 12 days with two causes at once, which it never trained on, it flagged 15 of 22 breaches early.

**What is the measurable impact?**
Three policies on the same 20 days with the same staff and moves. Total waiting: 426 hours with a fixed roster, 367 for a supervisor who reacts after the limit is passed, 329 following the tool. The tool beat reacting on 9 days, matched it on 11 and lost on none. Share of patients waiting over 30 minutes: 5.2%, 1.0% and 0.7%. That is about 1.9 waiting hours saved a day against reacting, or roughly 580 a year assuming 300 clinic days.

**How is priority decided?**
Chance of a breach, times patients affected, times expected minutes over the limit, times a station weight (consultation 1.5, pharmacy 1.2, the others 1.0). The weights are our judgment.

**Are the staff moves realistic?**
They are assumptions: move a registration clerk to pharmacy, send the float nurse to laboratory sample-taking, open the reserve room with the on-call doctor, open a third registration desk with a float clerk, and fast-track repeat prescriptions. A hospital would replace this list with its own. The tool only picks from the list.

**What are the limits?**
Patients never leave the queue in the simulation, a moved staff member works at full speed at once, and half the test days carry an injected disruption, so a real clinic's mix of good and bad days will differ.

**What would a pilot need?**
A timestamped event-log export from the hospital's queue or records system, and its own list of allowed staff moves.
