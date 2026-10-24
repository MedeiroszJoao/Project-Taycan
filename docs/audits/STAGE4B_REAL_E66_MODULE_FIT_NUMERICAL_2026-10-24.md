# Stage 4B — empirical Taycan LG E66 module: measured topology and sensor polarity

**Date:** 2026-10-24. **Status:** exploratory empirical physical-structure and instrument-consistency evidence. Not Model-B freeze; not A/B generalization, diagnostic validity or completion of Stage4B.

## Independent public experiment and integrity

Primary source: [Uwalaka, Yao, Duque & Kollmeyer, 2024, Borealis](https://borealisdata.ca/dataset.xhtml?persistentId=doi:10.5683/SP3/7JP3NM) (DOI 10.5683/SP3/7JP3NM, CC BY 4.0), LG E66 battery cell and recovered Porsche Taycan module. `4-Module Data.zip` Dataverse file 837535; verified **5,501,501 bytes**, MD5 **619eb01774c04696e399d106639a342c**, SHA256 **a5628a9d56d2e097158620346c3f69b5ff5c6269bb2770f643e91f397abcac7e**, all ZIP member CRC PASS, **12** MATLAB level-5 experimental files. [Provenance run 40075085474](https://github.com/MedeiroszJoao/Project-Taycan/actions/runs/40075085474).

**Experimental partition prospectively filed prior to any numeric reads**: six development-fit files, two validation files, four blind holdout files. See [split decision](../decisions/STAGE4B_E66_MODULE_SPLIT_TOPOLOGY_GATE_2026-10-24.md). No numeric validation or blind reads, no Stage4 1152 reserved test reads. Six development datasets came from **the same module** and should not be treated as six independent vehicles/modules.

### Reader and failure history

Initial SciPy 1.14.1 `scipy.io.loadmat` returned `MatlabOpaque` for each `meas.*` MATLAB MCOS table and yielded no valid numeric results. Third-party open-source `mat-io==0.4.0` failed with `ValueError: no field of name _Class`, [failed run 40075795890](https://github.com/MedeiroszJoao/Project-Taycan/actions/runs/40075795890). Newer `mat-io==1.0.1` (documented version change prior to rerun) successfully returned named pandas DataFrames, [run 40075907122](https://github.com/MedeiroszJoao/Project-Taycan/actions/runs/40075907122). Do not mislabel failed earlier readers as physical signals.

## Executed six-file development FIT analysis

Prospective follow-on analysis (one file already numerically inspected, five additional files not yet numerically inspected) registered in [fit-only physical protocol](../decisions/STAGE4B_E66_DEVELOPMENT_TOPOLOGY_CONSISTENCY_2026-10-24.md). Source: `scripts/stage4b_e66_dev_module_physical_qc.py`. **[All six complete in run 40076125617](https://github.com/MedeiroszJoao/Project-Taycan/actions/runs/40076125617)**. Artifact `stage4b-e66-six-development-module-physical-qc`.

| FIT experimental file | Paired numeric samples | Median AVL module V / reported cell V | Pearson corr(AVL I, BMS I) |
|---|---:|---:|---:|
| 0.7C loss | 7,730 | 5.97917 | -0.985126 |
| 1C loss | 8,678 | 5.95373 | -0.981866 |
| 1C MCCC | 27,590 | 5.95556 | -0.999774 |
| 0.5C MCCC part 1 | 3,358 | 5.96882 | -0.999246 |
| 0.5C MCCC part 2 | 25,082 | 5.94937 | -0.999628 |
| 1.2C loss | 24,780 | 5.96306 | -0.985873 |

All six reported **100%** of aligned positive module-to-cell voltage ratios between **4.5 and 7.5** (a broad, predeclared sanity window); `CellID` observed 0..5 in first tested dataset. The raw source README's '2C = 264 A' implies reference module capacity 132 Ah. Taken with E66 cell nameplate around 66Ah, the data support **six electrical groups in series and two nominally parallel cells per group (convention 6s2p)**; the official dataset description alternatively says '6p2s'. This inconsistency must be explicitly flagged and resolved using the 236,837 B `3-Taycan Module Instrumentation.pdf` source and/or wiring evidence **before freezing pack mapping**. The voltage evidence supports electrical grouping but is not alone a mechanical / OEM wiring certificate.

The AVL and Orion BMS **current columns have nearly opposite signed dynamics** in every FIT experiment. Inverting signs is warranted before physical energy comparisons *only after* matching actual measurement conventions and time alignment. Large negative correlations alone do not prove calibration/absolute accuracy; offsets, synchronisation and instrument metrology remain to be checked.

## Physical meaning, limits, consequences

- **Empirical support gained**: real Taycan LG E66 module scale; battery terminal voltage ~six series groups; strong current-sign inversion between independent acquisition paths; per-experiment raw sample availability; independent source version and checksums.
- **Wolfram dimensional crosscheck**: 28 × 6 series × 2 parallel × hypothetical 66 Ah × 3.7 V nominal cell = **82.0512 kWh**, *illustrative gross theoretical energy*, not the 79.2kWh OEM usable/baseline battery. This must not be used as observed experimental pack energy or a calibration target.
- **Not established**: internal chemistry/electrode-specific parameters, thermophysical pack response, module heat exchange beyond lab coolant plate at 30°C, health/aging faults, OCV/R0 functions or reliable stage4 failure discrimination. Laboratory module is not necessarily identical to every pack/market/version of target 2022 Taycan 4S.
- PyBaMM earlier independent SPMe/DFN solver/grid used `Chen2020` LG M50 cell, **not** E66; prior simulations stay valid as *solver capability*, not E66 empirical validation. Stage4B `GENERATOR_B_FREEZE` is **still NOT signed**.
- Stage3 historic simulator SHA and Stage4A correction/runner remain unchanged, as do Stage4 freeze, 2232 manifest and 1152 reserved test episodes. No whole-data A/B evaluation.

### Next auditable scientific steps

(1) Independently inspect instrumentation diagram and correct 6s2p vs '6p2s' identification. (2) Verify actual AVL vs BMS current sign conventions, voltage offsets, sample delay and instrument uncertainty in six FIT data, preserving records and outliers. (3) Define terminal-voltage, input current, thermal-boundary and initial SOC matching to genuine E66 *cell* data; only then fit physically identifiable parameters and freeze B before testing validation and blind partitions. (4) Treat TUM one-car RWD driving evidence and E66 module lab as **distinct external domains**; do not merge into pseudo-independent sample pool.

**Conclusion: strong independent experimental evidence for module voltage grouping and sensor polarity, but no right to infer model A accuracy or E66-calibrated generator B yet.**
