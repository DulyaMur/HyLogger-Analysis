"""
Classifier threshold sensitivity analysis
=========================================

Individual analysis by Dulya Murage (24910402), CITS5553 (GSWA HyLogger).

The Group 6 rule-based classifier uses one fixed set of *placeholder* thresholds
and leaves 89.9% of intervals Unclassified, and rule R3 (Waste rock) never fires.
Those two facts raise an obvious question the group report flags as future work:

    How sensitive are the labels to the thresholds we picked, and WHY does R3
    never fire?

This script answers that empirically. It re-implements the five first-match-wins
rules with *configurable* thresholds, then:

  1. reproduces the baseline result as a sanity check;
  2. breaks the Unclassified pile into its real causes (error gate vs no rule
     matched vs too little data) - something the baseline lumps together;
  3. sweeps each threshold one at a time and records how the label counts move;
  4. diagnoses R3 by looking at the DARK-MICA distribution and finding the
     threshold at which Waste would start to fire.

Input : data/mineral_percentages.csv  (276 intervals x 14 minerals, Final Mask == 1)
Output : outputs/*.csv (sweep tables), outputs/*.png (plots), console report.

Run:  python threshold_sensitivity.py
"""

from pathlib import Path

import numpy as np
import pandas as pd
import matplotlib
matplotlib.use("Agg")  # write files, no display needed
import matplotlib.pyplot as plt

HERE = Path(__file__).resolve().parent
DATA = HERE / "data" / "mineral_percentages.csv"
OUT = HERE / "outputs"
OUT.mkdir(exist_ok=True)

# Baseline placeholder thresholds, copied verbatim from
# classifier/rules_baseline.py in the team repo.
BASELINE = dict(
    MIN_SCAN_COUNT=20,
    WHITE_MICA_ALTERED=40,
    CHLORITE_ALTERED=25,
    CHLORITE_ORE=15,
    CARBONATE_ORE=15,
    WASTE_COMBINED=55,          # DARK-MICA threshold for R3
    WHITE_MICA_WASTE_MAX=15,
    CARBONATE_WASTE_MAX=15,
    EXPECTED_MAX_ERROR=307,
)

LABELS = ["Possible ore zone", "Altered zone", "Waste rock", "Unclassified"]


def classify(row, p):
    """
    The same five rules as the baseline, in the same order (first match wins),
    but driven by the threshold dict ``p`` so we can vary it.

    Returns (label, rule). Note: unlike the baseline, we give the error-gate
    failure its own rule tag ("R5_error_gate") so we can separate it from a
    genuine no-rule-matched ("R5_no_match").
    """
    total = row.get("total_n", 0)
    if not np.isfinite(total) or total < p["MIN_SCAN_COUNT"]:
        return "Unclassified", "R4_low_data"

    error = pd.to_numeric(row.get("Error", np.nan), errors="coerce")
    if not np.isfinite(error) or not 0 <= error <= p["EXPECTED_MAX_ERROR"]:
        return "Unclassified", "R5_error_gate"

    wm = row.get("WHITE-MICA", 0)
    ch = row.get("CHLORITE", 0)
    ca = row.get("CARBONATE", 0)
    dm = row.get("DARK-MICA", 0)

    if wm >= p["WHITE_MICA_ALTERED"] and ch >= p["CHLORITE_ALTERED"]:
        return "Altered zone", "R1_phyllic"
    if ca >= p["CARBONATE_ORE"] and ch >= p["CHLORITE_ORE"]:
        return "Possible ore zone", "R2_ore"
    if dm >= p["WASTE_COMBINED"] and wm < p["WHITE_MICA_WASTE_MAX"] and ca < p["CARBONATE_WASTE_MAX"]:
        return "Waste rock", "R3_waste"
    return "Unclassified", "R5_no_match"


def run(df, p):
    """Classify every interval under threshold set ``p``; return a labelled copy."""
    out = df.apply(lambda r: classify(r, p), axis=1, result_type="expand")
    out.columns = ["label", "rule"]
    return df.assign(label=out["label"], rule=out["rule"])


def counts(labelled):
    """Label counts as a dict, always covering all four labels."""
    vc = labelled["label"].value_counts()
    return {lab: int(vc.get(lab, 0)) for lab in LABELS}


# ---------------------------------------------------------------------------
# 1. Baseline reproduction + why-unclassified breakdown
# ---------------------------------------------------------------------------
def baseline_report(df):
    labelled = run(df, BASELINE)
    c = counts(labelled)
    n = len(df)
    print("=" * 64)
    print("BASELINE REPRODUCTION  (should match the group report)")
    print("=" * 64)
    for lab in LABELS:
        print(f"  {lab:20s}: {c[lab]:4d}  ({c[lab] / n * 100:5.1f}%)")
    print(f"  {'TOTAL':20s}: {n:4d}")
    print(f"\n  Unclassified rate: {c['Unclassified'] / n * 100:.1f}%   (report says 89.9%)")

    print("\n  Why are intervals Unclassified? (baseline lumps these together)")
    rules = labelled["rule"].value_counts()
    for r in ("R5_no_match", "R5_error_gate", "R4_low_data"):
        print(f"    {r:16s}: {int(rules.get(r, 0)):4d}")
    print("  -> 'no rule matched' vs 'failed the Error gate' are different problems.")
    labelled.to_csv(OUT / "baseline_labelled.csv", index=False)
    return labelled


# ---------------------------------------------------------------------------
# 2. One-at-a-time threshold sweeps
# ---------------------------------------------------------------------------
def sweep(df, key, values):
    """Vary one threshold across ``values`` (others at baseline); record counts."""
    rows = []
    for v in values:
        p = dict(BASELINE, **{key: v})
        c = counts(run(df, p))
        c[key] = v
        rows.append(c)
    res = pd.DataFrame(rows)[[key] + LABELS]
    res.to_csv(OUT / f"sweep_{key}.csv", index=False)
    return res


def plot_sweep(res, key, baseline_value, title):
    plt.figure(figsize=(7, 4.2))
    for lab in LABELS:
        plt.plot(res[key], res[lab], marker="o", ms=3, label=lab)
    plt.axvline(baseline_value, color="grey", ls="--", lw=1, label=f"baseline = {baseline_value}")
    plt.xlabel(f"{key} threshold (%)" if "ERROR" not in key else f"{key} (Error units)")
    plt.ylabel("intervals")
    plt.title(title)
    plt.legend(fontsize=8)
    plt.tight_layout()
    plt.savefig(OUT / f"sweep_{key}.png", dpi=130)
    plt.close()


def all_sweeps(df):
    print("\n" + "=" * 64)
    print("THRESHOLD SWEEPS  (one threshold varied, others held at baseline)")
    print("=" * 64)
    specs = [
        ("WHITE_MICA_ALTERED", range(20, 61, 2), "R1: white-mica threshold vs labels"),
        ("CHLORITE_ALTERED", range(10, 41, 2), "R1: chlorite threshold vs labels"),
        ("CHLORITE_ORE", range(5, 31, 1), "R2: chlorite-ore threshold vs labels"),
        ("CARBONATE_ORE", range(5, 31, 1), "R2: carbonate-ore threshold vs labels"),
        ("WASTE_COMBINED", range(10, 61, 2), "R3: dark-mica (waste) threshold vs labels"),
        ("EXPECTED_MAX_ERROR", range(100, 601, 25), "Error gate vs labels (coverage control)"),
    ]
    for key, values, title in specs:
        values = list(values)
        res = sweep(df, key, values)
        plot_sweep(res, key, BASELINE[key], title)
        # console: show the two extreme ends and the baseline row
        base_row = res[res[key] == BASELINE[key]]
        lo, hi = res.iloc[0], res.iloc[-1]
        print(f"\n  {key}:  range {values[0]}..{values[-1]}  (baseline {BASELINE[key]})")
        print(f"    at {int(lo[key]):>4}: ore={lo['Possible ore zone']:>3}  "
              f"alt={lo['Altered zone']:>3}  waste={lo['Waste rock']:>3}  uncl={lo['Unclassified']:>3}")
        if not base_row.empty:
            b = base_row.iloc[0]
            print(f"    at {int(b[key]):>4}: ore={b['Possible ore zone']:>3}  "
                  f"alt={b['Altered zone']:>3}  waste={b['Waste rock']:>3}  uncl={b['Unclassified']:>3}  <- baseline")
        print(f"    at {int(hi[key]):>4}: ore={hi['Possible ore zone']:>3}  "
              f"alt={hi['Altered zone']:>3}  waste={hi['Waste rock']:>3}  uncl={hi['Unclassified']:>3}")


# ---------------------------------------------------------------------------
# 3. Why does R3 (Waste rock) never fire?
# ---------------------------------------------------------------------------
def r3_diagnosis(df):
    print("\n" + "=" * 64)
    print("R3 (WASTE ROCK) DIAGNOSIS")
    print("=" * 64)
    dm = df["DARK-MICA"]
    print(f"  DARK-MICA across 276 intervals: max={dm.max():.1f}%  "
          f"mean={dm.mean():.1f}%  95th pct={dm.quantile(0.95):.1f}%")

    # Helper: does this interval reach R3 at all? R3 is only tested if the
    # interval passes the low-data check AND the Error gate, and is NOT already
    # taken by R1 or R2. But R3 itself requires white-mica<15 and carbonate<15,
    # which already rule out R1 (needs wm>=40) and R2 (needs carbonate>=15) -
    # so the ONLY things that can intercept an R3 candidate are the low-data
    # check and the Error gate, both of which run first.
    passes_data = np.isfinite(df["total_n"]) & (df["total_n"] >= BASELINE["MIN_SCAN_COUNT"])
    err = pd.to_numeric(df["Error"], errors="coerce")
    passes_gate = np.isfinite(err) & (err >= 0) & (err <= BASELINE["EXPECTED_MAX_ERROR"])
    reaches_r3 = passes_data & passes_gate

    cond_wm = df["WHITE-MICA"] < BASELINE["WHITE_MICA_WASTE_MAX"]
    cond_ca = df["CARBONATE"] < BASELINE["CARBONATE_WASTE_MAX"]

    print("\n  Two separate things kill R3. Counting both:")
    print(f"  {'dark-mica':>10} | meet R3 mineral conds | of those, pass Error gate -> ACTUAL Waste")
    rows = []
    for t in range(60, 9, -5):
        cond_dm = df["DARK-MICA"] >= t
        meet = cond_dm & cond_wm & cond_ca           # satisfy R3's mineral logic
        actual = meet & reaches_r3                    # also survive the earlier gates
        rows.append({"dark_mica_threshold": t,
                     "meet_r3_mineral_conditions": int(meet.sum()),
                     "also_pass_error_gate_actual_waste": int(actual.sum())})
        print(f"  {t:>8}%  |          {int(meet.sum()):>3}          |                 {int(actual.sum()):>3}")
    pd.DataFrame(rows).to_csv(OUT / "r3_diagnosis.csv", index=False)

    meet_base = (df["DARK-MICA"] >= BASELINE["WASTE_COMBINED"]) & cond_wm & cond_ca
    actual_base = int((meet_base & reaches_r3).sum())
    print(f"\n  At the baseline (dark-mica>=55): {int(meet_base.sum())} intervals meet R3's mineral")
    print(f"  conditions, but {int(meet_base.sum()) - actual_base} of them FAIL the Error gate, so R3")
    print(f"  actually fires {actual_base} times -> Waste rock stays empty.")
    print("  => R3 is starved by TWO things: dark-mica rarely reaching 55%, AND the")
    print("     few candidates that do, failing the Error quality gate first.")

    # Histogram of dark-mica with the baseline threshold marked.
    plt.figure(figsize=(7, 4.2))
    plt.hist(dm, bins=30, color="#C45BA0", edgecolor="white")
    plt.axvline(55, color="black", ls="--", lw=1.2, label="baseline R3 threshold = 55%")
    plt.xlabel("DARK-MICA (% of valid scans in interval)")
    plt.ylabel("intervals")
    plt.title("Why R3 never fires: dark-mica rarely reaches the waste threshold")
    plt.legend(fontsize=8)
    plt.tight_layout()
    plt.savefig(OUT / "r3_dark_mica_hist.png", dpi=130)
    plt.close()


def main():
    if not DATA.exists():
        raise SystemExit(f"Missing {DATA}. Copy mineral_percentages.csv into data/ first.")
    df = pd.read_csv(DATA)
    assert df["Final Mask"].eq(1).all(), "Data must be Final-Mask filtered already."
    print(f"Loaded {len(df)} intervals across {df['hole_id'].nunique()} holes.\n")

    baseline_report(df)
    all_sweeps(df)
    r3_diagnosis(df)

    print("\nDone. Tables and plots written to:", OUT)


if __name__ == "__main__":
    main()
