# Stage4B SPMe-vs-DFN parameter sensitivity: prospectively fixed protocol

Date: 2026-10-24. This document is recorded before observing the sensitivity-grid outputs. This is not an A-versus-B test and not an empirical calibration or final GENERATOR_B_FREEZE.

**Source:** independent PyBaMM 26.4.2, Chen2020 nominal **LG M50** cell parameters (not LG E66, not 2022 Taycan 4S 79.2kWh), Python 3.11, IDAKLU.

**Grid (18 independent deterministic solves):**
- Model variant: SPMe (primary), DFN (sensitivity). Both `options={"thermal":"lumped"}`.
- Ambient and initial absolute temperature: exactly {288.15, 298.15, 308.15} K. Both `Ambient temperature [K]` and `Initial temperature [K]` updated consistently.
- Discharge rate: exactly {0.25C, 0.5C, 1.0C}; positive discharge and 20-minute duration.
- 10-minute rest, 20-minute charge at 0.2C; initial SOC=60%, output period 30s.
- Solver: PyBaMM IDAKLU; retain default tolerances, record exact model/source/parameter identifiers.
- Stability: fully executed duration 3000 s or explicit failure/termination; monotone finite time; finite cell terminal voltage, cell temperature and current; nominal model voltage 2.5–4.3V and temperature 200–380K are intentionally broad generic screening bounds, **not Taycan OEM ranges**.
- Comparisons: calculate RMS and maximum absolute SPMe-minus-DFN `Voltage [V]` and `Volume-averaged cell temperature [K]` aligned by interpolation to a uniform 30s grid. Also report per-case extrema and cell charge/discharge.
- Comparison units: *per-cell* V/K, not 800V pack measurements. No arbitrary 168s2p extrapolation or inference about pack heat transfer.
- A case that terminates early, changes current sign, has missing output, incompatible parameter set or nonfinite output is a **FAIL**, with diagnostic retained; no silent deletion or post-result parameter tuning.
- No source from Project Taycan simulator A, 28-feature layer, labels, or protected train/validation/test datasets is permitted.
- The script reports differences as **model-form uncertainty proxies**, not calibrated prediction errors, independent third-party validations, or diagnostic fault identification.
- Work on experimentally anchored model-B parameterization and holdout partitions continues separately. Future cell datasets must identify chemistry/geometry and cannot automatically be called Porsche battery measurements.

Implementation: `scripts/run_stage4b_pybamm_sensitivity_grid.py`. Store exact code hash and version with 18 outputs and 9 pairwise comparisons.
