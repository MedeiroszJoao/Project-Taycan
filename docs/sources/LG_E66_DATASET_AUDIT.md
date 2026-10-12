# Source audit: McMaster LG E66 Taycan cell/module dataset

**Scope:** provenance and preliminary read-only archive inspection. This does **not** revise Stage 4, fit the simulator, or authorize Stage 5.

## Primary source and attribution

Uwalaka, L., Yao, Q., Duque, J., and Kollmeyer, P. J. (2024). *Fast Charging and Characterization Dataset for Porsche Taycan LG E66 Battery Cell and Module*. Borealis Data Repository. DOI: https://doi.org/10.5683/SP3/7JP3NM

Both original README files explicitly declare **CC BY 4.0**. Attribution and license notice are required for redistribution and adaptations.

## Integrity and content

| Check | Observation |
|---|---|
| Uploaded ZIP | `doi-10.5683-sp3-7jp3nm.zip` |
| Size | **157,829,116 bytes** |
| SHA-256 | `d569bb98ec52ed6b0e151e3269154063dcc4b8a13ab05b30ac7bb3fa94cfd20b` |
| Outer / nested archives | All passed ZIP CRC |
| Cell archive | 63 MATLAB MAT files + HPPC explanatory DOCX |
| Module archive | 12 MATLAB MAT files |
| Other | 2 original READMEs + 3-page instrumentation PDF + source MANIFEST.TXT |

## First-party experimental facts

- **Cell:** one **65 Ah nominal LG E66 NMC** cell removed from a Taycan module; temperatures **−20, −10, 0, 10, 25 and 40 °C**; tests include C/20, C/3, HPPC, GITT, OCV, 0.5C, 1C and 15 driving-cycle sequences per temperature.
- **Module:** one 12-cell Taycan module under controlled chamber at **30 °C** with charging tests and losses. Test rig includes **AVL tester and Orion BMS measurements**, cell voltages/IDs, numerous temperature sensors, coolant inlet/outlet and cooling-plate measurements.
- **Electrical topology:** the experiment's own **`3-Taycan Module Instrumentation.pdf` page 3** explicitly says **`6s2p`**. This resolves the ambiguity in the Borealis web page's abbreviated topology description.
- **Cooling rig:** coolant **50/50 water–glycol**; approximately **1.75 L/min** total flow, split between two parallel cooling plates. This describes the **test bench**, not a factory vehicle flow-rate specification.

## Verified sample data (not calibration)

| MATLAB file | Inspection result |
|---|---|
| `.../25degC/..._C20Dis.mat` | 2,997 entries; discharged-current sign negative; minimum recorded Ah counter −61.3141 Ah |
| `.../25degC/..._HPPC.mat` | 403,514 entries; current −390.0219 to +195.0002 A; voltage 2.7995–4.2006 V; pulse logging ~0.1 s |
| `.../Drive Cycles/25degC/...mat` | 858,862 entries; 6 missing-current message rows. Filter nonphysical `MSG` before modeling. |
| Module fast-charge MAT | 30 logical variable names present, but stored as MATLAB `MCOS table` opaque objects that are **not directly decoded** into arrays by standard SciPy `loadmat`. |

These numbers describe **particular observed files**, not validated Taycan pack parameters or a full-sample quality audit.

## Critical limitations and next steps

1. The experiment identifies materials as taken from a Porsche Taycan, but does not by itself prove equivalence to a **2022 Taycan 4S 79.2 kWh standard Performance Battery**. The single-cell/sample-module study cannot establish production variability.
2. Preserve original filenames, units, timestamps, and test sessions. Check time sampling, status transitions and missing messages.
3. Cell discharge current is negative in observed data; explicit sign conversion is required before comparison with the approved simulated conventions.
4. Resolve the MAT `MCOS table` decoding or obtain an author-supplied numerical export before quantitative module-model comparisons.
5. Any new calibration, fitting, split design, or adjustment to the Stage 3 frozen physical simulator requires an authorized stage revision.

**Approved Stage 3 model checksum remains** `af4e576cf824d30ee6aa9b2fd1f2c18d576fd269027df67c43c5e7647266ff4e`.

**Repository handling:** source ZIP and first-party PDF were **not committed**; this file contains only attribution and audit metadata. The repository's visibility was public when this research catalog was prepared.
