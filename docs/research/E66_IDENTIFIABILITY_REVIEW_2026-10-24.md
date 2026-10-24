# E66 calibration — independent prospective identifiability review

Review date 2026-10-24; baseline `e48f3366c92b9425263d93c00155729571bcdb01`. This review read Git documents, official packaged README and ZIP-directory metadata only. No cell MAT numeric payload, module validation/holdout numeric payload, or historical Stage4 reserved episode was opened. No physical model was modified.

## Evidence and design boundary

The packaged `0-Readme - Cell.txt` identifies **one 65 Ah LG E66 NMC cell, still within a recovered Taycan module**, tested across −20, −10, 0, 10, 25 and 40°C. It does not identify electrode-specific NMC composition, negative-electrode chemistry, porosity, particle radius, electrolyte transport, electrode thickness, active fractions or heat-transfer geometry. The cell cannot be counted as six independent cells merely because six temperatures were tested. Temperature tests occurred sequentially; temperature and calendar/test history are confounded.

Primary provenance: Uwalaka, Yao, Duque and Kollmeyer, *Fast Charging and Characterization Dataset for Porsche Taycan LG E66 Battery Cell and Module*, [Borealis DOI 10.5683/SP3/7JP3NM](https://doi.org/10.5683/SP3/7JP3NM), CC BY 4.0. Local packaged README SHA-256 `2b700b53b45d531b5077fc08c2b22fdede20ed2e3fa5f83ea442335cec5a31f1`; inner cell ZIP, 152124241 bytes, SHA-256 `fc65efb69fe196952b430443b0e3c8df0ff789076f91ecebe3f8e10d86937e65`. These are observed local identities; independent publisher checksum comparison is separate.

Current Git documents freeze **module** development/validation/blind groups. They do not automatically define a cell-data partition. Freeze an exact cell filename allowlist, roles, subsegments and checksums **before numeric reading**. Keep all drive cycles as an uninspected generalization group until calibration is frozen; select calibration characterization families in advance. A practical bounded scope is 25°C C/20 and HPPC for identification, one preselected C/3 or 0.5C file for model selection, and untouched 1C plus drive cycles for final evaluation. If adjacent characterization has already been inspected elsewhere, disclose exposure and call later evaluation prospective within this run, not pristine blind validation.

The README warns that the first 25°C capacity C/20 test was accidentally done at 25°C; a repeat at **40°C after the characterization** supplies the reference used by the authors. Predeclare whether nominal 65Ah, first measured 25°C capacity or the repeated 40°C reference defines SOC, and show the others as sensitivity. Do not select whichever makes validation favorable. C/20/GITT finite-rest curves are approximate equilibrium evidence, not electrode-resolved OCP. Drive-cycle `Status` distinguishes protocols and charge/recovery; counters reset between steps. Segment by action and monotonic time, preserve reset/discontinuity records, and do not concatenate blindly.

## What a Chen-derived SPMe calibration can establish

`Chen2020` originates in a **5 Ah LG M50 cylindrical cell**, whose NMC811/graphite-SiOx chemistry and internal properties are not established for E66. See [Chen et al., JES 2020, DOI 10.1149/1945-7111/ab9050](https://doi.org/10.1149/1945-7111/ab9050). Retaining that electrochemistry while fitting E66 terminal data yields an **effective Chen-derived E66-response surrogate**, not a recovered E66 electrode parameterization.

Changing `Nominal cell capacity [A.h]` from 5 to65 alone changes C-rate bookkeeping but does not consistently rescale physical active-material inventory or current density. Two defensible exploratory conventions are:

1. An explicit effective parallel/area multiplier near65/5=13, applied consistently to current density and inventory, with declared hypothetical geometry. Verify charge balance at the actual65A terminal current, not merely nominal C-rate labels.
2. Solve a normalized 5Ah representative cell with measured E66 current divided by a frozen effective scale; present terminal current, capacity and energy mapping explicitly. An electrical surrogate under prescribed temperature is defensible; scaling its cylindrical heat-transfer surface to an E66 pouch/module is not automatically defensible.

Do not mix both conventions and double-scale current. When fitting an external series resistance, use E66 terminal current with E66-equivalent resistance; if the resistance is specified on the representative cell, divide by the same parallel scale for the terminal mapping. State positive-discharge sign and check it against charging/discharging energy, not just correlation.

## Recommended bounded fit, frozen before optimization

Start with no more than **three global effective parameters**, plus explicitly bounded initial-state nuisance terms:

| Parameter | Exploratory bound recommendation | Interpretation / caution |
|---|---|---|
| Effective capacity/current scale | equivalent50–80Ah, positive; reference65Ah | Broad numerical search bound, not E66 manufacturer tolerance. Check measured calibration capacity before finalizing the prospectively declared physical interpretation. |
| Added terminal contact resistance | 0–5mΩ on E66 current convention | Effective series correction; cannot uniquely distinguish tabs, instrument offset, electrolyte and kinetic error. Negative values would compensate model error and are disallowed. |
| One common solid-diffusion multiplier | 0.1–10 times fixed Chen values, optimize log-scale | Effective response time; do not simultaneously fit independent radii and diffusivities. |
| Initial SOC per independent protocol | Prefer measured charge/rest rule; optional bounded correction ±0.03 | Nuisance, not independently measured SOC. Never tune per evaluation trajectory against its full voltage outcome. |

These numerical bounds are recommendations, **not an approved final parameter freeze**. If source metadata/independent pilot reasoning justifies different bounds, amend before optimization; log bound hits and rejected solver trajectories. Fix electrode OCP and stoichiometry at first, but explicitly test their misspecification: a persistent voltage-shape residual is evidence against Chen chemistry transfer, not an invitation to fit unrestricted OCP functions. Avoid fitting both a free voltage offset and initial SOC without assessing their correlation.

Use integrated-time or equal-segment weighting; HPPC0.1s samples must not dominate C/2060s samples solely by count. Charge/rest/pulse segments should each contribute declared weight. Optimize only training voltages at predeclared times; include termination coverage in the objective so early voltage-cutoff trajectories cannot obtain low error by dropping difficult samples. Report solver failure counts, final time, aligned coverage, RMSE, bias and maximum absolute error separately.

A thermal fit should be separate and limited. Case temperature at cell midpoint is not volume-average/core temperature. Because the cell remained in the module, unknown neighboring-cell/contact/chamber coupling prevents treating an isolated cylindrical lumped boundary as measured E66 physics. Prescribed measured temperature can support an electrical-only validation **conditional on observed temperature**; it cannot count as a thermal prediction. Do not jointly fit heat capacity, area, convection coefficient and entropic coefficient from one surface trace.

## Identifiability and acceptance checks

1. Run at least three fixed starting points within identical bounds. Compare achieved loss and parameter vectors, not optimizer success flags alone.
2. Calculate finite-difference sensitivities using dimensionless/log-scaled parameters at the fit, singular values/rank and normalized column correlations. Scale-dependent raw Jacobian condition numbers alone are misleading.
3. Profile each fit parameter or perform a small declared grid around it while reoptimizing others. Flat/boundary profiles imply weak identifiability even when RMSE is low.
4. Use block/protocol uncertainty or sensitivity envelopes. Thousands of samples from one cell do not furnish thousands of independent experimental replicates; pointwise iid bootstrap confidence intervals are inappropriate.
5. Compare frozen uncalibrated baseline and calibrated surrogate on the **same** untouched conditions; preserve negative results and coverage. Parameter selection using validation turns that set into development and requires a separate untouched evaluation group.
6. Freeze source code, versions, exact mapped parameters/functions, solver tolerances, initial-state procedure, temperature treatment, metrics and partition hashes before evaluation. A model JSON with only fitted scalar values is insufficient.
7. Do not transfer electrical parameter-fit success to B01–B09 fault mechanism identification, pack topology, module thermal behavior or whole-vehicle diagnostic validity. Evaluate only supported observables and scenarios.

The caution is supported by primary identifiability research: [Bizeray et al., Identifiability and parameter estimation of the single particle lithium-ion battery model](https://arxiv.org/abs/1702.02471) describes conditions involving known OCP gradients and lumped kinetics; [Aitio et al., SPMe parameter identifiability](https://people.maths.ox.ac.uk/chapman/battery/publication/aitio2020/) distinguishes sensitivity and parameter uncertainty. This review does not perform Bayesian inference or authorize Stage5.

**Prospective verdict:** bounded, externally driven terminal-voltage calibration is feasible as an explicitly effective surrogate. Unique E66 electrochemical parameter recovery, population generalization and independently validated thermal/pack physics are not established by these measurements or a low fitting RMSE.

## Review of root's actual prospective design (same date, before evaluation)

The later `results/e66_calibration/PROSPECTIVE.json` chooses a narrower two-protocol calibration: 25°C C/20 and C/3; evaluation at25°C 0.5C and1C, explicitly possibly previously exposed and not blind. It excludes the40°C repeated capacity file. Capacity derives from C/20 integration; effective parallel factorQfit/5 normalizes actual current. InitialSOC1 and original Chen full-charge stoichiometries are fixed assumptions. Thermal prediction is explicitly excluded. These decisions are coherent as a conditional experiment, with initialSOC and fixed-temperature error retained as limitations.

The actual fitted quantities differ from the recommendation above: positive-electrode OCP additive constant(±0.3V), linear stoichiometry correction(±1V coefficient), and effective-M50 contact resistance(0–0.1Ω). This is a bounded empirical voltage-shape correction, not E66 half-cell thermodynamic identification. Preserve the full corrected OCP function and stoichiometry range in the freeze; inspect its slope/domain for unphysical reversals or extrapolation. A successful fit would not identify which electrode caused voltage differences. OCP offset, OCP slope, initialSOC and resistance can compensate one another; fixed initialSOC removes one fit dimension but does not eliminate model misspecification.

The specified 150 uniform-time points from the first90% of each training discharge give equal protocol weighting and an explicit domain; do not silently score only solver-surviving evaluation prefixes. The gates50mV RMSE,150mV maximum error,95% time coverage and5mV numerical refinement are prospective engineering criteria, not a known Porsche tolerance or metrology-derived acceptance limit. Evaluation must retain full intended horizon, solver events and failed cases. A FAIL is a scientifically valid bounded conclusion; no post-evaluation retuning is authorized by this review.
