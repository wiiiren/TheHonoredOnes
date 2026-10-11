# Demo script

A 3-minute live demo of the Services Bottleneck Predictor, followed by answers to likely questions. It is built to answer the brief's core question: does the model help someone make a better decision, and can you prove it? Every time, number and sentence below is what the live app shows today on https://bottleneck-predictor.vercel.app/. If the engine, the demo days or the results change, re-check them.

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

**Timing.** The spoken lines total about 425 words, which is roughly 2:50 at a normal speaking pace. That leaves about 10 seconds for clicks and pauses, which is very little: plan to use the first cut under "If you are running long" unless rehearsal comes in under three minutes. Start each line while the replay is still running; do not wait for it in silence.

### 1. Problem and user (0:00 to 0:25)

**Do:** nothing. The screen shows "Doctor called away" at 08:00, "No action needed".

**Say:**
> "We are TheHonoredOnes, and this is the Services Bottleneck Predictor. In a hospital outpatient clinic the bottleneck moves all day: registration, then consultation, then pharmacy. The supervisor sees it only when the waiting room is full, and by then it takes hours to clear. We warn them about thirty minutes earlier, say why, and name the staff move that prevents it."

### 2. Detect (0:25 to 0:55)

**Do:** press **Play** and start speaking. Pause when the clock passes about 10:30. Press **5 min** until the card appears at **11:00**.

**Screen at 10:55:** "No action needed yet. Keeping an eye on Consultation."

**Screen at 11:00:** Consultation shows a 10-minute wait, "Rising to 20 min by 11:30", status **Will breach**, 55% chance, "3 of 4 doctors".

**Say:**
> "Here is one morning, replayed. For three hours the screen stays quiet. At eleven it raises an alert, while the wait at consultation is only ten minutes and nobody in the waiting room sees a problem. The tool has simulated the next hour thirty times, using a model that has learned the arrival pattern, and expects consultation to pass the thirty-minute limit by 11:35."

### 3. Categorize and explain (0:55 to 1:18)

**Do:** point at the cause on the card, then open **Why?**

**Card:** "Open the reserve room with the on-call doctor." / "Consultation is likely to pass the 30-minute limit by 11:35 (55% chance). Cause: staffing gap. 3 of 4 doctors are on duty. About 27 patients will be affected." / "Act within 35 min".

**Why? bars:** Staffing gap 21 min, Demand surge 2 min, Slow processing 0 min.

**Say:**
> "The tool also names the kind of problem: a staffing gap, with only three of four doctors on duty. It works this out by re-running the next hour with arrivals, staffing and service speed each put back to normal. Restoring the fourth doctor removes twenty-one minutes of the wait, so the problem is staffing, not patient numbers."

### 4. Recommend and act (1:18 to 1:46)

**Do:** point at **Expected effect**, press **Apply move**, then press **5 min** once. Stop there.

**Expected effect:** "Opening the reserve room for an hour cuts the consultation wait by about 21 minutes, saving about 3 patient-hours of waiting across the clinic in that hour. No other station is expected to pass the limit in the next hour."

**Screen at 11:05 after Apply:** "No action needed". Consultation is back to **OK** with 4 of 4 doctors. The **Moves applied** panel reads "Patients waiting over 30 min today: 22% without this move, 1% with it".

**Say:**
> "It recommends one move the clinic is allowed to make and states its effect: twenty-one minutes off the wait and about three patient-hours saved in the next hour. It never sends a doctor or a radiographer to another station. I apply it, and five minutes later consultation is back to OK. Across the whole day, patients waiting over thirty minutes fall from twenty-two percent to one."

### 5. Prioritize (1:46 to 2:14)

**Do:** select **Holiday rush**, press **Play** and start speaking. Pause near 10:30, step with **5 min** to **10:50**. Point at the "Ranked first" line and at **Also watching**. Step once more to **10:55**. Do not press Apply on this day.

**Screen at 10:50:** card is Registration, "Open a third registration desk with the float clerk", cause demand surge, "Arrivals are about 2 times the usual level for this hour". Under it: "Ranked first of 2: 41 patients affected, 50% chance, about 4 minutes over the limit." **Also watching (1):** Consultation, "May pass the limit in about 45 min", Demand surge.

**Screen at 10:55:** the two swap. The card is now Consultation, "Open the reserve room with the on-call doctor", "Ranked first of 2: 36 patients affected, 55% chance, about 5 minutes over the limit."; Registration moves to Also watching.

**Say:**
> "A different morning: a walk-in rush at double the usual arrivals, with two stations at risk at once. The tool shows one action, ranks the other below it, and gives the reason: forty-one patients affected, a fifty percent chance, four minutes over the limit. Five minutes later the order flips, as the rush moves from registration to consultation. A fixed roster cannot follow that."

### 6. False alarms (2:14 to 2:26)

**Do:** select **Ordinary busy day** and press **Play**. Let it run while you speak.

**Screen:** "No action needed" all day. It shows "No action needed yet" briefly at 11:05 and 11:30, and never raises an alert.

**Say:**
> "An alarm that cries wolf gets ignored. On an ordinary busy day the tool watches the peak and stays quiet, because an alert needs two checks in a row."

### 7. Proof and close (2:26 to 3:00)

**Do:** scroll to **Why trust this?** and point at the tiles as you name them.

**Tiles:** "30 min" median warning. "0.7" false alarms per day. "5 of 5" right cause. "10%" less total patient waiting.

**Say:**
> "We tested it on twenty simulated days the model never saw. The median warning was thirty minutes, with under one false alarm a day. Arrival patterns come from a real hospital log; staffing and results are simulated. So does it help someone make a better decision? Against a good supervisor who reacts once a queue is over the limit, it cut total waiting by ten percent and was never worse on any day. The same approach fits any service with queues: banks, government counters, airports."

### If you are running long

Cut in this order. Each cut is a whole sentence, so nothing is left half-said.

1. Beat 7: "The same approach fits any service with queues: banks, government counters, airports." (about 5 seconds)
2. Beat 5: "A fixed roster cannot follow that." (2 seconds)
3. Beat 4: "It never moves a doctor or a radiographer to another station." (4 seconds)
4. Beat 1: "We are TheHonoredOnes, and this is the Services Bottleneck Predictor." if you are introduced by name (4 seconds)

Never cut the question and answer in beat 7. It is the judges' own core question.

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

## Optional extra, if you are asked for a third cause

Select **Records system slow**, play to **10:55**. The card reads "Cause: slow processing. Each patient is taking 16 minutes against the usual 10", and recommends opening the reserve room. Pressing Apply there takes the day from 8% of patients over 30 minutes to 0%.

## Likely questions

**What is real and what is simulated?**
Two things are measured from real data, the public HospitalOPD log of 19,214 visits on 156 days: how arrivals vary by hour and weekday, and the share of patients sent to the laboratory and to imaging. Everything else is an assumption: service times, staff numbers, the pharmacy share and the five allowed moves. All of our results come from simulated days.

**Why simulate at all?**
A real log shows what happened, not what would have happened if a supervisor had moved someone. It also does not record why a queue built up. A simulator lets us test both.

**How does the forecast work?**
Every five minutes it takes the queues as they are now and plays the next 60 minutes forward 30 times. The share of those runs in which the wait passes 30 minutes is the chance of a breach: 15 runs out of 30 means 50%. A gradient-boosted model, trained on 60 simulated days, supplies the expected arrivals, so a surge shows up as soon as recent arrivals run above normal.

**Is it better than a simple guess?**
On average, yes. Looking 60 minutes ahead, its average error is 1.6 minutes. Guessing "the wait will stay as it is now" is off by 2.5 minutes, and guessing "the usual wait for this time of day" is off by 2.3. When a station is busy all three errors are larger: 9.9 minutes for the tool, 16.5 for "stays as it is" and 9.8 for the time-of-day guess. So in busy periods it clearly beats the first guess and is level with the second.

**How many problems does it miss?**
There were 17 breaches on the test days. It flagged 9 before the wait passed the limit, flagged 5 only after the wait was already over it, and missed 3 completely.

**Where is the AI, and what does the learned model add?**
There are two parts. The first is a gradient-boosted model, trained on 60 simulated days, that forecasts arrivals by comparing recent arrivals with the usual level. The second is a simulator that plays the next hour forward 30 times from the live queues. Most of the predictive power comes from the simulator. We tested this by swapping the learned model for a simple assumption, "arrivals stay at the usual level", on the same 20 test days. The average wait error did not change: 1.6 minutes either way. With the model, the tool flagged one more breach early (9 of 17 instead of 8) and missed one fewer (3 instead of 4). During a surge, the model's forecast of arrivals was off by 7.8 patients an hour instead of 8.8, measured on the 3 surge test days. These figures are in `eval/results.json` under `model_value`.

**How many alerts are false alarms?**
Half of them. On the 20 test days it raised 28 alerts, and 14 were followed by a real breach within the hour. The other 14 were false alarms, which is 0.7 a day.

**How do you keep false alarms down?**
The tool raises an alert only when the chance of a breach is 30% or more on two checks in a row, five minutes apart. It clears the alert after two checks in a row below 20%. Requiring the second check halves false alarms, from 1.4 a day to 0.7. We chose these thresholds on 10 separate tuning days, allowing ourselves at most one false alarm a day.

**How often is the cause right?**
Every time it raised an alert. Of the 10 test days with an injected problem, 5 raised an alert and all 5 named the right cause. The other 5 raised no alert at all.

**Does it hold up on messy data?**
Mostly, at the cost of more false alarms. We made the inputs noisy by distorting the queue counts, the arrival counts and the service times. It still flagged the same 9 of 17 breaches early and named the right cause on 6 of 6 days, but false alarms rose from 0.7 to 1.7 a day. We also tried 12 days with two problems at once, which it never saw in training. There it flagged 15 of 22 breaches early.

**What is the measurable impact?**
We ran the same 20 days three ways, with the same staff and the same allowed moves each time. With a fixed roster, patients waited 426 hours in total. With a supervisor who reacts after a wait has passed the limit, 367 hours. Following the tool, 329 hours. Day by day, the tool beat the reacting supervisor on 9 days, matched them on 11 and never did worse. The share of patients waiting over 30 minutes was 5.2% with a fixed roster, 1.0% reacting and 0.7% with the tool. Against reacting, that is about 1.9 waiting hours saved a day, or roughly 580 a year if the clinic opens 300 days.

**How is priority decided?**
Each alert gets a score: the chance of a breach, times the patients affected, times the expected minutes over the limit, times a weight for the station. Consultation is weighted 1.5, pharmacy 1.2 and the others 1.0. Those weights are our own judgment.

**Are the staff moves realistic?**
They are our assumptions. There are five: move a registration clerk to pharmacy, send the float nurse to laboratory sample-taking, open the reserve room with the on-call doctor, open a third registration desk with a float clerk, and fast-track repeat prescriptions. A hospital would replace this list with its own, and the tool only ever picks from the list.

**What are the limits?**
Three main ones. In the simulation, patients never give up and leave the queue. A staff member who is moved works at full speed straight away. And half the test days have a problem injected, so a real clinic, with a different mix of good and bad days, would see different numbers.

**What would a pilot need?**
Two things from the hospital: a timestamped event-log export from its queue or records system, and its own list of allowed staff moves.

**Could this work outside a hospital?**
The approach would, for any service with stations and queues. Stations, staffing, service times and allowed moves are all settings in one file. The route people take between stations is built into the simulator for a clinic, so that part would need adapting for another sector.
