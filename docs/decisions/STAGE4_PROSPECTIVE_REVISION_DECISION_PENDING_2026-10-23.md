# Stage 4: prospective physical and observational revision — DECISION PENDING

**Status: DRAFT / NOT APPROVED / NOT AN AMENDMENT TO THE HISTORICAL FREEZE.** Created 2026-10-23 for expert and owner review. It grants no permission to score episodes, modify the frozen model, repurpose holdouts, or start Stage 5.

## Immutable reference

- Stage 3 frozen `src/simulator/taycan_sim/model.py`: SHA-256 `af4e576cf824d30ee6aa9b2fd1f2c18d576fd269027df67c43c5e7647266ff4e`.
- Stage 4 sealed `freeze.json`: SHA-256 `5822c3e43e6f4634c7ca60d0aabb6f38afe5cecece99883833ee1c4d12dc5df8`.
- Stage 4 manifest: 2,232 entries (720 TRAIN, 360 VALIDATION, 1,152 TEST); do not rewrite IDs, splits, seeds or labels.
- Original historical `observation_layer.py` recovery reported elsewhere but its exact bytes and provenance have **not** been verified and it is NOT committed. The candidate is **not** a recovered original.

## Mandatory decisions BEFORE any new Stage 4 frozen campaign

1. **Physical constitutive closure.** Choose whether `aging_rate_per_s` is to be frozen at zero during energy-conservation tests or whether the model introduces and validates an explicit degradation/side-reaction ledger. The six-hour static, 60% SOC counterfactual with current defaults changes approximate OCV-integrated chemical inventory by `-4171.513109 J` purely due to capacity loss; no corresponding physical destination is currently modeled.
2. **Variable RC capacitance.** Select and test a time-varying capacitor constitutive law and its work exchange, or hold `R1,C1` fixed in the conservation experiment. The exact RC energy identity in the candidate assumes constant coefficients *within* each step. The 336-branch fixed-`V_p=0.15 V` six-hour parameter-change counterfactual gives `-63.163210 J`, a bookkeeping jump not represented by fixed-step `Q_R1`.
3. **I01 operating-state fault definition.** Current candidate injects `+1600 W*severity_I` during cruise, acceleration, regeneration, **rest and charge**. The parked intervals occupy 40% of the duty cycle. Therefore 40% of the current energy-matched I01 fault energy is attributed to parked conditions. If the extra loss were motor-operation gated, matched I01 severity would scale by **5/3**. Do not select either assumption merely because it improves feature discriminability.
4. **Duty and charger physics.** Explicitly freeze the five 12-minute blocks/hour waveform (currently assumed torque 42, 82, -50 Nm base cases, not real-world calibrated), realistic motor speeds, parking/charge modes, accepted versus requested battery DC power, current, terminal voltage, thermal, SOC and taper limits. The original sealed charge calibration [0,120] kW endpoints may violate physically strict constraints. The development-only 47.8046875 kW / 31.5625 kW values were derived from narrowed post-pilot brackets and **may not be represented as precommitted calibration**.
5. **Observation, external domain and feature data.** Verify original observation source or formally label new substitute; test four RNG streams and sensor covariance, quantization, delays, missingness, F14/F28 timing and counter sources without truth leakage. Resolve lab module 6p2s/6s2p documentation, TUM RWD 93.4 kWh vs target 4S AWD 79.2 kWh, and preserve NASA/Oxford holdout exposure/quarantine. Validate against external measurements only where variant/domain compatible.

## Reproducible evidence, not approval

- New independent static energy inventory and tests: `docs/audits/STAGE4_INDEPENDENT_ENERGY_INVENTORY_2026-10-23.md` and `scripts/audit_stage4_energy_inventory.py`.
- I01 activity-dependent energy-mapping sensitivity and tests: `docs/audits/STAGE4_M01_I01_MODE_SENSITIVITY_2026-10-23.md` and `scripts/audit_stage4_m01_i01_modes.py`.
- CI: GitHub Actions Python 3.11 **82/82** tests PASS (the test suite checks code behavior and detects unresolved physics limitations; it does not validate the vehicle). See PR #2 / workflow runs.
- Previous 12/12 M01/I01 analytic maps are exactly matched in the candidate's chosen loss model **by construction**. This does not give a validated equivalent inverter failure or official calibration receipt.
- Existing 2× six-hour experiments are non-scoring H00 development runs, not registered smoke tests. **Official episodes completed: zero.**

## Proposed prospective acceptance checks (NOT approved or frozen)

A review must choose and numerically fix: (i) state-dependent constitutive equations, units, and energy ledger; (ii) valid SOC/current/voltage/temperature domains and handling of inadmissible inputs; (iii) quantitative dt-convergence tolerances set without looking at heldout results; (iv) all fault-specific activity gates and physical loss parameter ranges; (v) observation RNG/noise and counter contracts; (vi) independent calibration seeds/bracket rules, no validation/test fitting; (vii) external data usage and holdout policy.

Only after explicit authorization: create a **new** versioned protocol, preregistered manifest linkage to the unchanged historical splits, and new SHA-256 for accepted candidate sources. The old `freeze.json` and 2,232-row manifest must not be silently changed or reused as evidence that the revised model was historically frozen. Then re-run training-only calibration, complete authorized energy matching, full-length 12-episode smoke, the campaign, and independent audit.

## Evidence policy

- A zero DC algebra residual is not global electrochemical-thermal conservation.
- A test suite passing does not prove material calibration or external validation.
- Synthetic outcomes must never be used to certify real Taycan operation, high-voltage safety or maintenance decisions.
- Stages 5–8 are not authorized.
