# TUM Taycan Real-World CAN Dataset — intake status

**Current status:** source verified; user ZIP received; **byte-level and sample-data inspection pending** because the analysis runtime could not access its mounted filesystem on 2026-10-12. Do not interpret source metadata as verification of the uploaded ZIP contents.

## Original dataset
- **Authors:** Nico Rosenberger and Markus Lienkamp, Technical University of Munich (TUM).
- **Title:** *CAN Data of a Porsche Taycan during Real-world Driving Scenarios*.
- **DOI:** https://doi.org/10.14459/2025mp1774217.001
- **Canonical landing page:** https://mediatum.ub.tum.de/1774217
- **Publication:** 2025-05-26.
- **License per repository:** CC BY 4.0 — cite authors, dataset, DOI and changes.
- **Source's stated scope:** 92 measured driving records; **93 published files / 408 MB**. Signals may include pack voltage, current, SOC, battery temperatures, motor RPM and torque, and vehicle states; individual recordings vary by purpose.
- **Acquisition method:** periodic requests for ECU status via CAN. Actual sampling rates and missingness **must be examined in individual files**, not assumed.

## Vehicle/transfer-domain caveats
The associated article by Rosenberger et al. (World Electric Vehicle Journal 2025, 16, 296) studies a **rear-wheel-drive, April 2022 Porsche Taycan with 93.4 kWh Performance Battery Plus**. It is **not** the Project-Taycan target: **2022 4S, AWD, 79.2 kWh standard Performance Battery**. This difference affects battery module count, energy and drive unit count and may affect measured signal semantics. No source claim establishes equivalence or direct quantitative validation for the target configuration.

## User upload
- Supplied in conversation as `m1774217_001.zip`.
- File service metadata reports **427,200,572 bytes**.
- **NOT VERIFIED:** SHA-256, ZIP CRC integrity, number of entries, file structure, headers, signal units, per-session duration, measurement intervals, missing data and value ranges.
- A scientific audit cannot be marked complete based on the filename or the source website alone.

## Controlled next step
Run `scripts/audit_tum_realworld_zip.ps1` **locally, read-only** on the user's original file. The tool emits ZIP inventory, selected text headers and SHA-256 without extracting, training, fitting, publishing original data, or touching frozen simulation code. The metadata is supplementary; quantitative checks and test-set partitioning require a subsequent controlled importer and authorization.

> Scientific stage gates: Stages 1–3 approved; Stage 4 awaits explicit formal approval/revision; Stage 5 unauthorized. This document does not revise any stage.
