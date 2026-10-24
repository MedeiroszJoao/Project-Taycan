# Stage4B E66 post-freeze 1C failure — diagnostic audit without refitting

2026-10-24. Research protocol already published on branch, `results/e66_calibration/PROSPECTIVE.json`. Work's interrupted execution **reported**, but its local binary/JSON calibration artifacts have **not yet been committed or independently verified here**, that E66 Chen-derived SPMe/DFN achieved ≈46mV RMSE on the 0.5C evaluation record, ≈85–87mV on 1C, with numerical refinement 1C FAIL. Treat these **reported values** as provisional until the original Work `FIT_RESULT.json`, `GENERATOR_B_FREEZE.json`, `EVALUATION.json` and full logs are available with hashes. Do not recalculate fit or alter frozen fitted parameters based on these evaluation outcomes.

## Existing preregistered criteria, in source

- External terminal-voltage voltage RMSE <=0.05 V, maximum abs error <=0.15V, coverage >=0.95.
- Mesh/solver-refinement maximum absolute voltage change <=0.005 V. Failure at 1C is a binding criterion, separate from empirical RMSE.
- Single **one-cell** E66, 25°C, two fitting protocols C/20+C/3, evaluation 0.5C+1C; evaluation is *prospective no-fit transfer*, **NOT pristine virgin blind** if previously inspected.
- The effective model is Chen2020 (LG M50) with E66 current/capacity normalization and bounded voltage-shape OCP+contact corrections; not electrode-resolved E66 chemistry.

## Adversarial code audit

1. `scripts/fit_e66_generator_b.py:simulate()` computes two different numerical configurations in `evaluate()`: `mesh=20, rtol=1e-6, atol=1e-7` vs `mesh=40, rtol=1e-8, atol=1e-9`. The reported difference is **JOINT space/time+solver sensitivity**; cannot diagnose a uniquely spatial mesh error or uniquely time tolerance error. An independent factorial numerical audit would vary mesh and tolerances separately, **using same frozen physical parameters**, and would be labeled `post-hoc numerical diagnostics`, not a replacement of the originally failed gate.
2. The comparison currently uses only `t <= t_refined[-1]` for `numerical_refinement_max_V`. If the finer run terminates early, the difficult tail is omitted. **Fail closed on full coverage of both independent grids** and report both terminations, n-points, time-to-cutoff, common-overlap fraction and max/RMS gap; never produce a pass from common-prefix agreement alone.
3. The `simulate()` interpolation grid ends at min(requested final time, actual solver time), so a high 1C RMSE on the preceding domain must not be confused with the cutoff. Always compare the intended 1C time span and report existing voltage range, time coverage and signed residual across early/middle/late segments.
4. `Contact resistance [Ohm]` is defined for the normalized 5Ah surrogate current, not automatically the E66 terminal current. The factor q/5 must be declared when converting resistance and energy to 65Ah cell physical units; never add a second scale during diagnostics.
5. OCP corrections `a+b*(sto-.5)` are effective voltage response terms; do not infer electrode thermodynamics from fitted values. Check outside fitting stoichiometry range and positivity/monotonicity on actually traversed domain without retuning.
6. Physical interpretation of relative-error signs or charge/discharge capacity must be checked against measured current conventions; the cell `segment()` uses `i=-Current` for discharge. The recovered **module** AVL/BMS sign anticorrelation cannot itself determine the sign of the cell dataset, which uses separate instrument channels.
7. No electrochemical test on another cell, no rigorous thermal prediction, no 4S vehicle fault identification can be inferred from this evaluation. Those are later, distinct gates.

## Bounded next step

**First** place the Work-generated freeze, fit, evaluation receipts (small JSON, no raw measurements or prior fixture substitutions) and full solver logs in a dedicated provenance folder on the experimental branch, preserving their exact bytes and hashes. **Then** run `scripts/audit_e66_frozen_receipts.py` (read-only receipt auditor), which verifies frozen-source hashes, model/parameter invariance, externally evaluated files, published thresholds and incomplete/refinement cases. Do not rerun optimization.

Only after receipt verification may a **separate** retrospective factorial numerical test compare mesh and tolerance changes at 1C under the frozen same model, explicitly as numerical diagnosis and not an overwritten PASS of the originally failed gate.

**Status: generator-B fitted development candidate as reported, BUT NOT INDEPENDENTLY VERIFIED OR SCIENTIFICALLY APPROVED; 1C out-of-fit domain FAIL reported.**
