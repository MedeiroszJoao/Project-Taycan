# Stage4B genuine Porsche Taycan LG E66 module raw-data inventory — prospective

Date: 2026-10-24. Primary source: Uwalaka, Yao, Duque, Kollmeyer (McMaster), Borealis Dataverse doi:10.5683/SP3/7JP3NM, published 2024-10-10, CC BY 4.0.

**Independently documented from public dataset BEFORE executing this archive inventory:**

- `4-Module Data.zip`, public Dataverse file ID **837535**, reported size **5,501,501 bytes** and checksum **MD5 619eb01774c04696e399d106639a342c**.
- `2-Readme - Module.txt`, file 837534, source description from authors. Experiments use **one recovered Taycan module of twelve LG E66 cells, 6 parallel × 2 series**. Ambient thermal chamber **30°C** ±1°C, coolant plate set **30°C**. Charging MCCC at **0.5, 1, 1.5, 2 C** and vehicle fast-charge power profile; additional 0.7/1.2/1.5C constant-power-loss cycling. Terminal voltage/current from AVL/Orion; module cell voltages and thermal sensors, actual full-pack calibration not granted.
- `1-Cell Data.zip`, file ID 837532, >152MB, not downloaded in the initial lightweight audit. This artifact is relevant for later PyBaMM cell-level calibration.
- `3-Taycan Module Instrumentation.pdf`, 837536, 236,837 B, provides thermocouple locations; analysis requires independently interpreting that source before treating temperatures as colocated.

**FIRST EXPERIMENT**: download ONLY file 837535 (<6 MB) over HTTPS official Dataverse API, stream to temporary local CI disk, verify exact byte size and MD5, record independent SHA-256. Zip-directory listing (filename, uncompressed/compressed size, metadata flags, CRC) ONLY. Reject malformed ZIP, path traversal, duplicate names, encrypted members, zip bombs (ratio >1000). Probe MATLAB file variable names, shapes, MATLAB format only if supported by installed readers; **do not train or fit**. Delete raw temp bytes and publish ONLY structural metadata. Archive full test stdout and JSON receipts.

**Integrity:** official checksum failures fail closed. No replacement of approved Stage3/4A physics; no original Stage4 2232 row accesses and no PGM training. **This is independent actual Porsche E66 *module*-level evidence**, not validation of hypothetical 4S pack architecture. A module is 6p2s and cannot be silently mapped to simulator A's assumed arrangement of 28 modules each represented differently.

Scientific next step only after data reading: define **experiment-level heldouts** (e.g. reserve selected C-rate and/or charging protocol as BLIND BEFORE parameter fitting), temperature/voltage/current mapping, and stop conditions. Fix these then a new calibrated PyBaMM model B freeze may be proposed. Do not overwrite existing Chen2020 LG M50 solver qualification with E66 parameters that have not been identified.
