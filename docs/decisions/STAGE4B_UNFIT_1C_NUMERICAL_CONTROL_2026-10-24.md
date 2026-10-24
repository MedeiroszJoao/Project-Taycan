# Stage 4B — isolated 1C numerical control (not recovered E66 freeze)

**2026-10-24. Registered before running this new numerical control.** This is **retrospective with respect to the observed E66 1C failure** and fully separate from the Work-local original frozen result. Work-reported 0.5C ≈46mV and 1C ≈85–87mV are **not independently attested** because their original `FIT_RESULT.json`, `GENERATOR_B_FREEZE.json`, `EVALUATION.json` and logs have not been recovered. No attempt is authorized to reconstruct these missing documents by fitting after evaluating 1C.

## Pure PyBaMM numerical-control question

Does **unfitted** PyBaMM Chen2020 (LG M50), under a standard constant-current 1C discharge and the same numerical settings as the prior E66 runner, exhibit >5mV changes solely from mesh/tolerance selection?

- Models: SPMe and DFN (both thermal=isothermal, contact resistance enabled), PyBaMM **26.4.2**, Python 3.11, IDAKLU.
- Real cell input: **NONE**. No E66 MATLAB, no module or TUM CAN, no Project Taycan custom 1RC, no historical Stage4 split. Results cannot be compared to Taycan cell voltage observations or transferred to a 4S pack.
- Parameter set **Chen2020, unadjusted**; initial SOC 0.8, ambient+initial temperature 298.15K, discharge current 5A, contact resistance 0.001ohm, run 1200s with 241 nominal 5-second output points.
- Exact fixed grid, 2 models × 4 numerical configurations:
  - A: mesh20, rtol1e-6, atol1e-7;
  - B: mesh40, rtol1e-6, atol1e-7;
  - C: mesh20, rtol1e-8, atol1e-9;
  - D: mesh40, rtol1e-8, atol1e-9.
- Exact five pairwise comparisons for each model: A/B, A/C, A/D, B/D, C/D. Report maximum absolute V gap, RMS V gap, all terminations, timestamps, local full-horizon flag, and judge numerical stability under **5mV** difference only when both reached full 1200s and all 241 common samples exist.
- This 5mV threshold echoes the previously registered E66 refinement gate but is a **diagnostic decision criterion, not proof of E66 accuracy**. Do not apply observed control PASS/FAIL to overturn original 1C E66 failure. Do not adjust numerical inputs after seeing outcomes. A solver cutoff, exception, missing runs or skipped comparisons makes the experiment INCOMPLETE; retain the raw failure context in JSON.
- Source/version, model assumptions, exact binary/derived software versions, end-of-run voltage and full numeric comparison JSON must be archived.

This control tests only whether the **software and generic cell equations** show obvious numerical sensitivity at a matching nominal C-rate. If small, it still does not rule out failures due to the original E66 fitting, concentrations, stoichiometric subdomains, current trace, or initialization. If large, it motivates a numerical follow-up in the original frozen E66 setting when receipts become available.

**Frozen E66 source never edited**; original observations/data reserved and original reported E66 1C FAIL preserved. Actual repair remains blocked until original receipts are published or their loss is formally registered and a distinct prospective campaign is designed.
