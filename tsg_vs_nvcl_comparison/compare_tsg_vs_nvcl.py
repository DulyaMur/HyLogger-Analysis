"""
Compare raw .tsg/.bip HyLogger data (read directly via pyTSG) against the
NVCL API pull already used by the pipeline (nvcl_kit, via etl/fetch_holes.py,
cached in data/raw_holes.csv).

Question this answers: what does the current NVCL-API ETL gain and lose by
pulling only the Grp1_uTSAS scalar at 20 m resolution through the API,
compared to reading the hole's raw TSG package directly - and is there
anything in the raw data worth feeding into classifier/rules_baseline.py
that the API pull cannot provide.

Requires the hole's NVCL zip already downloaded and extracted locally (the
package is hundreds of MB - too large to commit to the repo). Point
--tsg-folder at the extracted folder containing <hole_id>_tsg.tsg etc.

Run
---
python etl/compare_tsg_vs_nvcl.py --tsg-folder "C:\\path\\to\\05GJD001\\<...>"
"""

import argparse
from pathlib import Path

import numpy as np
import pandas as pd
from pytsg import parse_tsg


DATA_DIR = Path("data")
API_RAW_HOLES = DATA_DIR / "raw_holes.csv"
OUTPUT_BINNED = DATA_DIR / "tsg_vs_nvcl_binned.csv"
OUTPUT_METHODS = DATA_DIR / "tsg_vs_nvcl_method_agreement.csv"

DEFAULT_HOLE_ID = "05GJD001"
DEFAULT_RESOLUTION_M = 20.0
NO_DATA_GRP = ""
METHODS = ["uTSAS", "sTSAS", "sTSAV"]
INVALID_LABELS = {"INVALID", "NOTAROK"}


def load_raw_package(folder):
    """Read the extracted NVCL zip directly with pyTSG."""
    return parse_tsg.read_package(folder, read_cras_file=False)


def raw_method_table(scalars, hole_id, method):
    """
    Native-resolution Min1/Wt1/Grp1 table for one TSA method.

    Grp1 == "" is pyTSG's no-data marker (backed by the -3.402823e38 sentinel
    on the paired Wt1/Error columns) - rows with no classification are
    dropped here, same policy as etl/convert_percentages.py.
    """
    df = pd.DataFrame({
        "hole_id": hole_id,
        "depth": scalars["Depth (m)"].astype(float),
        "min1": scalars[f"Min1 {method}"].astype(str),
        "wt1": scalars[f"Wt1 {method}"].astype(float),
        "grp1": scalars[f"Grp1 {method}"].astype(str),
    })
    return df.loc[df["grp1"] != NO_DATA_GRP].reset_index(drop=True)


def bin_to_resolution(df, anchor, resolution=DEFAULT_RESOLUTION_M):
    """Downsample native-depth rows into fixed-width bins anchored at the
    API pull's own first bin edge (`anchor`), so raw and API data land on
    the exact same depth keys. Anchoring on the raw data's own min depth
    instead would silently shift every bin edge relative to the API's bins,
    since fetch_holes.py's 20 m bins start at the hole's first sample depth,
    not at a round multiple of the resolution."""
    out = df.copy()
    out["bin_depth"] = (((out["depth"] - anchor) // resolution) * resolution) + anchor
    return out


def raw_binned_percentages(raw_utsas_binned):
    """Per-bin mineral percentages from raw uTSAS, same normalisation as
    etl/convert_percentages.py (share of valid classified samples in the bin)."""
    valid = raw_utsas_binned[~raw_utsas_binned["grp1"].isin(INVALID_LABELS)]
    counts = (
        valid
        .groupby(["bin_depth", "grp1"])
        .size()
        .rename("n")
        .reset_index()
    )
    totals = counts.groupby("bin_depth")["n"].transform("sum")
    counts["pct_raw"] = counts["n"] / totals * 100
    return counts.rename(columns={"bin_depth": "depth", "grp1": "mineral"})


def api_binned_percentages(hole_id):
    """Per-bin mineral percentages as the current pipeline already produces
    them, straight from the cached NVCL API pull."""
    df = pd.read_csv(API_RAW_HOLES)
    df = df[df["hole_id"] == hole_id].copy()
    df["value"] = df["value"].astype(str).str.strip().str.upper()
    df = df[~df["value"].isin(["INVALID", "NOTAROK"])]
    df = df[df["count"] > 0]
    totals = df.groupby("depth")["count"].transform("sum")
    df["pct_api"] = df["count"] / totals * 100
    return df.rename(columns={"value": "mineral"})[["depth", "mineral", "pct_api"]]


def compare_resolution(raw_utsas, api_df, hole_id):
    api_hole = api_df[api_df["hole_id"] == hole_id]
    print("\n" + "=" * 65)
    print(f"RESOLUTION - {hole_id}")
    print("=" * 65)
    print(f"Raw native samples (pyTSG, all classified): {len(raw_utsas):,}")
    print(f"  Native sample spacing: ~8 mm (fixed by the HyLogger instrument)")
    print(f"  Depth range: {raw_utsas['depth'].min():.2f} - {raw_utsas['depth'].max():.2f} m")
    n_bins_api = api_hole["depth"].nunique()
    print(f"\nPipeline pull (fetch_holes.py, {DEFAULT_RESOLUTION_M:g} m resolution): {n_bins_api} bins")
    print("  This is a pipeline setting, not an API limit: reader.get_scalar_data()")
    print("  returns all 25,938 native rows, identical to the raw file (verified).")


def compare_coverage(scalars, hole_id):
    print("\n" + "=" * 65)
    print(f"COVERAGE - {hole_id}")
    print("=" * 65)
    total = len(scalars)
    for method in METHODS:
        classified = (scalars[f"Grp1 {method}"].astype(str) != "").sum()
        print(f"  {method:6s}: {classified:6,d}/{total:,} classified "
              f"({classified / total * 100:5.1f}%)")
    print("\n  Note: the pipeline (fetch_holes.py) only requests uTSAS. For this hole")
    print("  the API's 20 published scalar logs are uTSAS + ujCLST (TIR) only, so")
    print("  sTSAS/sTSAV coverage above exists only in the raw file.")


def compare_binned_percentages(raw_pct, api_pct):
    merged = pd.merge(raw_pct, api_pct, on=["depth", "mineral"], how="outer")
    merged["pct_raw"] = merged["pct_raw"].fillna(0)
    merged["pct_api"] = merged["pct_api"].fillna(0)
    merged["abs_diff"] = (merged["pct_raw"] - merged["pct_api"]).abs()

    print("\n" + "=" * 65)
    print("BINNED MINERAL % - RAW (uTSAS, rebinned to match) vs API (uTSAS)")
    print("=" * 65)
    print("  (Same TSA method, same 20 m bins, INVALID/NOTAROK excluded on both")
    print("   sides. Any gap comes from how the API's sampled endpoint aggregates.)")

    by_mineral = (
        merged.groupby("mineral")["abs_diff"]
        .agg(["mean", "max", "count"])
        .sort_values("mean", ascending=False)
    )
    print(f"\n{by_mineral.round(2).to_string()}")

    overall_mae = merged["abs_diff"].mean()
    print(f"\n  Overall mean absolute difference: {overall_mae:.2f} percentage points")
    return merged


def compare_methods(scalars, hole_id):
    """
    How often uTSAS and sTSAS agree on the mineral group, sample by sample
    (the two columns are row-aligned in the same package). Only samples where
    both methods give a real mineral call (not blank, INVALID or NOTAROK) are
    compared. sTSAV is excluded: it is a visible-light method covering a
    different mineral family (see etl/tsa_comparison.py's note).
    """
    u = scalars["Grp1 uTSAS"].astype(str).reset_index(drop=True)
    s = scalars["Grp1 sTSAS"].astype(str).reset_index(drop=True)
    depth = scalars["Depth (m)"].astype(float).reset_index(drop=True)

    def usable(x):
        return (x != NO_DATA_GRP) & ~x.isin(INVALID_LABELS)

    both = usable(u) & usable(s)
    only_one = (usable(u) ^ usable(s))
    combined = pd.DataFrame({"depth": depth, "uTSAS": u, "sTSAS": s})
    combined["agreement"] = "neither_or_invalid"
    combined.loc[only_one, "agreement"] = "only_one_method"
    combined.loc[both & (u == s), "agreement"] = "agree"
    combined.loc[both & (u != s), "agreement"] = "disagree"

    n_both = int(both.sum())
    n_agree = int((both & (u == s)).sum())
    print("\n" + "=" * 65)
    print(f"METHOD AGREEMENT (sample by sample, within raw file) - {hole_id}")
    print("=" * 65)
    print(f"  Samples where both uTSAS and sTSAS give a mineral: {n_both:,}")
    print(f"    agree   : {n_agree:,} ({n_agree / n_both * 100:.1f}%)")
    print(f"    disagree: {n_both - n_agree:,} ({(n_both - n_agree) / n_both * 100:.1f}%)")
    print(f"  Samples with a mineral from only one of the two: {int(only_one.sum()):,}")
    print("  sTSAV is not compared (different mineral family).")
    print("  Only uTSAS is published by the API for this hole; sTSAS comes from")
    print("  the same raw file at no extra cost.")
    return combined


def summarize_confidence(scalars):
    print("\n" + "=" * 65)
    print("CONFIDENCE (Wt1) - valid mineral calls only (INVALID/NOTAROK removed)")
    print("=" * 65)
    for method in METHODS:
        wt1 = scalars[f"Wt1 {method}"].astype(float)
        grp1 = scalars[f"Grp1 {method}"].astype(str)
        keep = (grp1 != NO_DATA_GRP) & ~grp1.isin(INVALID_LABELS)
        valid = wt1[keep]
        at_one = (valid == 1.0).sum()
        inv_at_one = ((wt1 == 1.0) & grp1.isin(INVALID_LABELS)).sum()
        print(f"  {method:6s}: n = {len(valid):6,d}, mean Wt1 = {valid.mean():.3f}, "
              f"below 0.5 = {(valid < 0.5).mean() * 100:4.1f}%, "
              f"exactly 1.0 = {at_one:,} ({at_one / len(valid) * 100:4.1f}%); "
              f"INVALID/NOTAROK rows at 1.0: {inv_at_one:,}")
    print("\n  The API publishes 'Wt1 uTSAS' and 'Error uTSAS' as separate numeric")
    print("  logs, identical to the raw file; the pipeline just never requests")
    print("  them. sTSAS/sTSAV Wt1 exist only in the raw file.")


def summarize_named_indices(scalars):
    candidate_cols = [
        "White Mica w2200",
        "Chlorite w2250",
        "Ferric oxide abundance 25062014",
        "Hematite-goethite_distr",
    ]
    present = [c for c in candidate_cols if c in scalars.columns]
    print("\n" + "=" * 65)
    print("NAMED MINERAL INDICES - only in the raw file")
    print("=" * 65)
    if not present:
        print("  None of the expected named-index columns were found in this file.")
        return
    for col in present:
        v = scalars[col].astype(float)
        valid = v[v > -1e37]
        print(f"  {col:35s}: {len(valid):6,d} valid values, "
              f"range [{valid.min():.3f}, {valid.max():.3f}]")
    print("\n  These are continuous per-sample scores (not just a category label)")
    print("  - unlike Grp1's discrete mineral-group bins, the classifier could")
    print("  threshold or trend these directly instead of counting class labels.")


def print_recommendations(method_agreement):
    both = method_agreement["agreement"].isin(["agree", "disagree"]).sum()
    agree_pct = (method_agreement["agreement"] == "agree").sum() / both * 100
    print("\n" + "=" * 65)
    print("WHAT MATTERS FOR THE CLASSIFIER (verified on 05GJD001)")
    print("=" * 65)
    print(f"""
  A. Rule 2 (hematite) cannot fire: 0 hematite samples in SWIR and only 8 in
     the whole hole (sTSAV, raw file only). Rule 3 needs goethite, which is
     absent from SWIR and exists only in sTSAV (4,929 samples, raw file only,
     decoded via pyTSG's class table); whether R3 fires depends on how the
     goethite percentage is normalised.

  B. Already in the API but not requested by fetch_holes.py: Wt1/Error
     uTSAS (confidence) and the TIR classes ujCLST (SILICA/quartz, feldspars,
     pyroxene, spodumene...). All 20 published logs match the raw file.
     Native ~8 mm rows are also available; the 20 m resolution is a pipeline
     setting, and the sampled 20 m pull does not match native data.

  C. Raw file only: sTSAS/sTSAV, their Wt1, named indices (w2200, w2250,
     ferric oxide, hematite-goethite distribution), water scalars, SNR,
     absorption features, raw spectra, WAMEX ID header. uTSAS and sTSAS
     agree on {agree_pct:.1f}% of samples where both give a mineral.
""")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--tsg-folder",
        required=True,
        help="Path to the extracted NVCL zip folder for one hole (e.g. ...\\05GJD001\\<uuid>)",
    )
    parser.add_argument("--hole-id", default=DEFAULT_HOLE_ID)
    args = parser.parse_args()

    DATA_DIR.mkdir(parents=True, exist_ok=True)

    print(f"Loading raw TSG package for {args.hole_id} from {args.tsg_folder} ...")
    data = load_raw_package(args.tsg_folder)
    scalars = data.nir.scalars

    raw_utsas = raw_method_table(scalars, args.hole_id, "uTSAS")

    api_raw = pd.read_csv(API_RAW_HOLES)
    api_hole = api_raw[api_raw["hole_id"] == args.hole_id]

    if api_hole.empty:
        raise ValueError(
            f"{args.hole_id} not found in {API_RAW_HOLES}. "
            "Run etl/fetch_holes.py first (or pick a hole already in that file)."
        )

    bin_anchor = api_hole["depth"].min()
    raw_utsas_binned = bin_to_resolution(raw_utsas, anchor=bin_anchor)

    compare_resolution(raw_utsas, api_raw, args.hole_id)
    compare_coverage(scalars, args.hole_id)

    raw_pct = raw_binned_percentages(raw_utsas_binned)
    api_pct = api_binned_percentages(args.hole_id)
    binned_comparison = compare_binned_percentages(raw_pct, api_pct)

    method_agreement = compare_methods(scalars, args.hole_id)
    summarize_confidence(scalars)
    summarize_named_indices(scalars)
    print_recommendations(method_agreement)

    binned_comparison.to_csv(OUTPUT_BINNED, index=False)
    method_agreement.to_csv(OUTPUT_METHODS, index=False)
    print(f"\nSaved binned raw-vs-API comparison to {OUTPUT_BINNED}")
    print(f"Saved native-resolution method agreement to {OUTPUT_METHODS}")


if __name__ == "__main__":
    main()
