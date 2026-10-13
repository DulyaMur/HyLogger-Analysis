# Findings — threshold sensitivity

> The numbers below are what `threshold_sensitivity.py` produces on the 276-interval
> dataset. **Run it yourself first and confirm you get the same values**, then write
> the interpretation in your own words in the "→ My reading" lines (that part is the
> point — it's what shows you understand it).

## 1. Baseline reproduced (sanity check)
Matches the group report exactly: Possible ore zone **22**, Altered zone **6**,
Waste rock **0**, Unclassified **248** → **89.9%** unclassified.

## 2. What the Unclassified pile is really made of
The baseline reports these 248 as one bucket. Split by actual cause:

| Cause | Intervals |
|---|---|
| No rule matched (R5) | 178 |
| Failed the Error quality gate | **69** |
| Too few scans (R4) | 1 |

So **~28% of the unclassified intervals (69 / 248) are a data-quality problem, not
a rule problem** — they never even reach the mineral rules.

→ My reading: _(why does this matter for how GSWA should act on the thresholds?)_

## 3. Threshold sensitivity (one knob at a time)
Most sensitive knob is **carbonate-ore (R2)**:

| CARBONATE_ORE | Possible ore zone | Unclassified |
|---|---|---|
| 5% | 59 | 211 |
| 15% (baseline) | 22 | 248 |
| 30% | 8 | 262 |

Altered (R1) is driven mostly by the **white-mica** threshold (14 → 6 → 0 as it goes
20 → 40 → 60). The **Error gate** strongly controls coverage on its own (at a gate of
100 only 7 intervals get any label; at 600, ~36 do). Full tables/plots in `outputs/`.

→ My reading: _(which thresholds would you prioritise asking GSWA to validate, and why?)_

## 4. Why R3 (Waste rock) never fires
Two independent causes, both needed to explain the zero:

1. **Dark-mica is almost always low** — mean 3.9%, 95th percentile 21.9%, and only
   **3** of 276 intervals reach the 55% waste threshold at all.
2. **The few candidates fail the Error gate.** Of the intervals meeting R3's full
   mineral logic at baseline (dark-mica≥55, white-mica<15, carbonate<15), **2**
   qualify — but **both fail the Error gate**, so they're marked Unclassified before
   R3 is ever tested. Actual Waste fires: **0**.

Even lowering the dark-mica threshold keeps a large gap between "meets R3 conditions"
and "actually labelled Waste" (e.g. at dark-mica≥10%: 15 meet the conditions, only 6
survive the gate). See `outputs/r3_diagnosis.csv` and `outputs/r3_dark_mica_hist.png`.

→ My reading: _(is R3 a bad rule, or a rule starved by the data + the Error gate? what
would you change?)_

## 5. So what (for the group project)
→ My reading: _(2–3 sentences: what does this add to the group report's "future work",
and what is the single most useful thing GSWA could do with it?)_
