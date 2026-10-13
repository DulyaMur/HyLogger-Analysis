# Classifier threshold sensitivity analysis

Individual analysis by **Dulya Murage (24910402)**, CITS5553 (GSWA HyLogger).

## Why
The Group 6 rule-based classifier uses one fixed set of *placeholder* thresholds,
leaves **89.9%** of intervals Unclassified, and rule **R3 (Waste rock) never fires**.
The group report lists two open questions as future work:

> *"Change each threshold in turn to see how the labels move, and find out why R3 never fires."*

This is my follow-up analysis that answers both, on the full 276-interval dataset
(20 holes), without needing to re-run the ETL.

## What it does
`threshold_sensitivity.py`:
1. **Reproduces the baseline** as a sanity check (must match the report: 22 ore,
   6 altered, 0 waste, 248 unclassified).
2. **Breaks the Unclassified pile into its real causes** — the baseline reports
   one "R5_no_match" bucket, but it actually mixes *no rule matched* with
   *failed the Error quality gate*. Separating them is informative.
3. **Sweeps each threshold** one at a time (others held at baseline) and records
   how the four label counts respond.
4. **Diagnoses R3** — distinguishes intervals that *meet R3's mineral conditions*
   from those that *actually reach R3* in the first-match-wins pipeline, and
   names what intercepts the rest.

## How to run
```bash
pip install pandas numpy matplotlib
python threshold_sensitivity.py
```
Reads `data/mineral_percentages.csv` (copied from the team repo; all intervals
are Final-Mask filtered). Writes tables and plots to `outputs/`.

## Outputs
| File | What it is |
|---|---|
| `outputs/baseline_labelled.csv` | every interval with its baseline label and the rule that fired |
| `outputs/sweep_<THRESHOLD>.csv` / `.png` | label counts as that one threshold varies |
| `outputs/r3_diagnosis.csv` | R3 candidates vs actual Waste fires, by dark-mica threshold |
| `outputs/r3_dark_mica_hist.png` | distribution of DARK-MICA with the R3 threshold marked |

## Findings
See **FINDINGS.md** for the results and interpretation.

## Relation to the team work
The five rules and baseline thresholds are reproduced from
`classifier/rules_baseline.py` in the team repo
(github.com/RVSHANDILYA/GSWA-hylogger-Industry-Adoption). This analysis does not
change the classifier; it probes its behaviour.
