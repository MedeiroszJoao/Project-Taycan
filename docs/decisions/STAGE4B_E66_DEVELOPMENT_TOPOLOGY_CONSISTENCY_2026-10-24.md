# Stage4B LG E66 module 6-file development-only topology & instrument consistency probe

Date 2026-10-24. This is **exploratory** because the first `20240314_1C_Test (MCCC).mat` FIT file was already inspected numerically (published before this document, run 40075907122). Remaining five fit files have not been numerically assessed; split stays immutable: six FIT, two VALIDATION, four BLIND.

First FIT source showed `mat-io==1.0.1` successfully decoding 27,590 numeric samples: AVL module V 17.85–25.44, BMS module V 18.11–25.14, CellVoltage 2.79–4.19 V, CellID 0..5, AVL I -41.88..132.78A, BMS I -131..39.2A. Dataset description says “6p2s”, whereas readme's 2C=264A and cell 66Ah imply two parallel strings and six groups in series under conventional notation; this is an **observed topology discrepancy** requiring confirmation. Do not silently rewrite the official source wording. The target 4S architecture in Stage3 is an **independently declared** design assumption; 28 modules ×6 series groups×2 parallels×66Ah×3.7V ≈82.0512kWh only demonstrates dimensional plausibility, not independent validation of the nominal pack or usable energy.

## Fixed analysis of SIX FIT files ONLY

For every file in precommitted FIT partition:
- verify same 5.5MB official ZIP MD5/SHA256, parse table with `mat-io==1.0.1`, create independent hashes for source members.
- use documented `AVL_Voltage.ACT_U`, `BMS_Voltage.Pack_Summed_Voltage`, `AVL_Current.ACT_I`, `BMS_Current.Pack_Current`, `CellVoltage.CellVoltage`, `CellID.CellId`, `RecordingTime.RecordingTime`, and auxiliary/thermal channels where available.
- report per-series valid counts, finite extrema and missingness. For aligned rows, report **median of per-row AVL module V / individual cell V**, and fraction with ratio 4.5–7.5; such pairs may have sensor timing skew. Do not infer pack serial count if fewer than 100 aligned valid samples.
- report Pearson current correlation `AVL I` vs `BMS I` with at least 100 aligned valid points and no assumed polarity; report opposite/identical current conventions if evidence supports.
- report observed unique `CellId` values; 0..5 is not proof of physical wiring without instrumentation diagram.
- no fitting of PyBaMM, no validation or blind file payloads parsed. Partial coverage and failures explicit.
- Report descriptive topology support per FILE and count by experimental protocol, **not six independent modules**.

No attempt to estimate true cell capacity, electrochemical parameters or fault separability from these six files in this step. A/B transfer and Stage4B completion remain blocked on model-B parameterization and independent experimental evaluation. 
