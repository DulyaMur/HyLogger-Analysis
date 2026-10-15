# HyLogger - Analysis 

Individual exploratory and comparison work I did for the **GSWA HyLogger Industry Adoption**
capstone (CITS5553, Group 6). This is the underlying data-analysis groundwork that fed into the
shared team project - the hands-on investigation of the raw HyLogger data and the NVCL API,
kept separate here because this is underlying work I did to understand and guide project.

- **Team project (shared repo):** https://github.com/RVSHANDILYA/GSWA-hylogger-Industry-Adoption
- **Data source:** GSWA HyLogger scans, open-file via the National Virtual Core Library (NVCL).
- **Hole used throughout:** `05GJD001`.

## How this relates to the group project
This individual work both **guided** and **deepened** the shared project:

- The **EDA** (`eda/`) and the **TSG-vs-NVCL comparison** (`tsg_vs_nvcl_comparison/`) were done *during* the project to understand the raw data and the NVCL API before modelling. They shaped team decisions: standardising on the uTSAS SWIR method, and recognising that oxide minerals (hematite/goethite) are a SWIR blind spot needing TIR data, which became the classifier's "sensor limits" and ore-proxy reasoning in the group report.
- The **threshold sensitivity study** (`threshold_sensitivity/`) is a *follow-up* analysis done after the build, to understand the classifier's behaviour (why 89.9% of intervals are Unclassified, why rule R3 never fires) and to inform the report's future-work recommendations.

## What's here

### `eda/` - first-look exploratory data analysis
Reading a raw HyLogger `.tsg` package directly with [pyTSG](https://github.com/Geological-Survey-of-Western-Australia/pytsg)
to understand what the data actually contains before any modelling.
- `read_hole.py` — loads the extracted NVCL package for `05GJD001`, inspects the NIR/SWIR and
  TIR spectra shapes and the per-sample metadata/scalars, and plots the first spectra and
  mineral-vs-depth.
- `nir_spectra_preview.png`, `mineral_vs_depth.png`, `strip_log_mockup.png` — outputs.

### `tsg_vs_nvcl_comparison/` - raw TSG vs NVCL-API comparison
A focused study of **what the pipeline's NVCL-API pull gains and loses** versus reading the raw
`.tsg` package directly, and whether anything in the raw data is worth feeding into the classifier.
- `compare_tsg_vs_nvcl.py` — compares the raw pyTSG data (native resolution, all TSA methods)
  against the API pull (`Grp1_uTSAS` at 20 m), and quantifies method agreement.
- `data/tsg_vs_nvcl_binned.csv`, `data/tsg_vs_nvcl_method_agreement.csv` — outputs.
- `docs/tsg_vs_nvcl_comparison.pdf` — write-up of the findings.

**Key findings** (see the PDF for detail): the NVCL API is lossless for what it publishes (all
native rows, plus Wt1/Error and TIR), so the limitation is the *pipeline*, not the API — the team
ETL requests only `Grp1_uTSAS` at 20 m and ignores Wt1/Error/TIR. The raw `.tsg` file is still
needed for sTSAS/sTSAV, named indices (e.g. ferric oxide, hematite–goethite), raw spectra and the
embedded WAMEX ID.

### `threshold_sensitivity/` - classifier threshold sensitivity analysis
A follow-up study answering two open questions from the group report's future work:
how sensitive the labels are to the placeholder thresholds, and **why rule R3 (Waste
rock) never fires**. Sweeps each threshold across the full 276-interval dataset and
diagnoses R3. Key result: R3 is starved by two independent things, dark-mica rarely
reaching the waste threshold and the few candidates failing the Error quality gate
first. See `threshold_sensitivity/FINDINGS.md`.

### `reports/` - my worked analyses
- `Hylogger_Industry_Adoption_Data_Analysis.pdf` - preliminary end-to-end analysis of hole 05GJD001.

## Running the code
The scripts expect the hole's NVCL package **downloaded and extracted locally** (hundreds of MB —
deliberately **not** committed; see `.gitignore`). Point the scripts at the extracted folder:

```bash
pip install pytsg pandas numpy matplotlib
python eda/read_hole.py
python tsg_vs_nvcl_comparison/compare_tsg_vs_nvcl.py --tsg-folder "C:\path\to\05GJD001\<...>"
```

## Notes
- The HyLogger data is GSWA **open-file** data served through NVCL. The original project
  correspondence (marked OFFICIAL) is **not** included here — only my own analysis, code and
  reports derived from the open data.
- Local repository; not published.
