# Stage 4B — independent PyBaMM generator-B preliminary model registration (before runs)

**Date:** 2026-10-24. **Status:** prospective *solver-only qualification*; **NOT** the final calibrated `GENERATOR_B_FREEZE` for A-versus-B comparisons.

**Independence principle:** PyBaMM SPMe and DFN are electrochemical models based on porous-electrode physics, not mathematical rewrites of Project Taycan simulator A's Thévenin/1RC circuit. B does not reuse simulator A physics, observation functions, 28-feature extractor or source calibrations.

## Fixed numerical protocol before first executed pilot

- Python `3.11`, PyBaMM pinned **`26.4.2`**; PyBaMM's `Chen2020` parameter set used as published **LG M50 NMC811/graphite-like cell context**, **not** Porsche LG E66 calibration, not a documented Taycan cell match.
- Models: `pybamm.lithium_ion.SPMe(options={"thermal":"lumped"})` as PRIMARY, `pybamm.lithium_ion.DFN(options={"thermal":"lumped"})` as solver/construction SENSITIVITY. Use independently provided PyBaMM parameter values, not hand-coded equivalent circuits.
- Fixed deterministic experiment: **Discharge at 0.5C for 20 minutes**, **Rest for 10 minutes**, **Charge at 0.2C for 20 minutes**, `period="30 seconds"`, initial SOC **0.6**, IDAKLU solver. No target fitting. These are solver qualification inputs, not measured TUM driving current.
- Record model output names, voltage, current, cell temperature and solver time/value arrays; validate finite values; avoid invented terminal-voltage cutoffs and assume no target-vehicle voltage.
- Verify A) electrochemical current sign across discharge/rest/charge; B) physically plausible single-cell voltage domain `[2.5,4.3]` V (illustrative generic bounds; separately flag any model event/termination); C) heat/temperature finite, K>0; D) reproducibility with a second *identical run* at fixed version; E) SPMe/DFN output-distance descriptions without interpreting the distance as error relative to real Porsche data.
- Log exact `pybamm.__version__`, Python version, configuration, parameter key fingerprint, script SHA and solver status in JSON artifact.
- If package API changes or a step fails, preserve explicit failure and stop. Any adjustments require prospective documented append-only amendment before re-running; cannot claim results from a failed run.
- No vehicle fault hypotheses (B09/M01/I01 etc) artificially imposed; no 4A/5 scorings or protected holdout access.

## Do NOT promote prematurely

This experiment only establishes that an **independent physical-cell generator exists and executes**. Actual Stage4B generator-B freeze still requires suitable cell parameter provenance and/or calibration to an identified dataset, heldouts and a justified observed-channel mapping. All A/B performance comparisons are PROHIBITED until that later freeze is signed.

Source: PyBaMM model comparison tutorial https://docs.pybamm.org/en/v26.4.2/source/examples/notebooks/models/compare-lithium-ion.html ; Chen2020 parameterization originally developed for an LG M50 cell, not established as Taycan LG E66. No commercial costs authorized.
