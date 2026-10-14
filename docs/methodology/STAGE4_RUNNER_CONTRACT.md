# Stage 4 runner: backend contract and execution gates

**Status:** runner source committed; no simulation, calibration, smoke test, or episode was executed by this commit.

## Why a backend adapter is required

The repository contains the sealed Stage 4 preregistration, append-only amendment, and 2,232-row episode manifest. It does **not** currently contain the frozen Stage 3 taycan_sim/model.py, freeze.json, or the executable observation layer. The runner therefore accepts paths to those local artifacts and a backend adapter. It fails closed if any SHA-256 differs or if the adapter cannot attest that counter timing was checked.

The runner itself does not modify the frozen model or either sealed JSON file. It uses only Python standard-library modules and requires Python 3.10 or newer.

## Backend interface

Pass --backend-file PATH to a local Python file that exports:

- MODEL_SHA256 = "af4e576cf824d30ee6aa9b2fd1f2c18d576fd269027df67c43c5e7647266ff4e"
- COUNTER_TIMING_VERIFIED = True only after verifying the Stage 3 forward-Euler timing/indexing for the Ah and kWh counters.
- run_episode(context: dict) -> dict.

run_episode must import and use the exact context["artifacts"]["model_py_path"] after confirming its hash. It must return a dictionary with:

- observed_rows: list of time-step dictionaries keyed by the exact OBDb channel IDs. Each row may also include time_s and dt_s.
- audit: an audit dictionary described below.

The adapter is responsible for invoking the existing Stage 3 physical model and observation layer; it must not implement a replacement physical model. It must pass the four frozen seeds to distinct streams: seed_physics, seed_observer, seed_aux, and seed_nuisance. The continuous nuisance scales are taken directly from the manifest. Persistent RPM/torque biases are already supplied as per-channel Uniform(-halfwidth,+halfwidth) values in context["observation_config"]. The SOC-bias RNG state is supplied as soc_bias_rng_seed_after_channel_biases; white measurement innovations use seed_observer, and the stochastic auxiliary load uses seed_aux.

For context["phase"] == "episode", the adapter must apply the row's acquisition_mode, counter_source, and diff_motor_t_mapping. counter_source="truth" is forbidden. TAYCAN_ENG_MOTOR_RPM receives an independent sensor bias/noise in the observation layer if the frozen layer supports it, but it is not added to the sealed feature whitelist.

For context["phase"] == "charge_calibration", the hypothesis is H00 and sensor measurement noise is disabled; the auxiliary-load process remains active. Return the physical SOC trajectory only in audit, not in observed_rows. The runner uses that trajectory solely for charge calibration and QC.

### Required audit fields

Every call must include:

- model_sha256: exact frozen model SHA-256.
- counter_timing_verified: true.
- profile_id, dt_s, charge_power_kw_applied.
- seeds_applied: dictionary identical to context["seeds"].
- traction_torque_scale_applied and regeneration_torque_scale_applied.
- soc_true_percent: one finite value per simulated time step, for audit/QC only.
- soc_time_s: finite time values aligned one-to-one with soc_true_percent.
- soc_initial_percent: configured initial SOC, exactly 60% within numerical tolerance.
- ambient_shift_applied: Boolean. If false for SHIFT_REGEN_COLD_6H, the runner records ambient_shift_not_modeled=true; it does not pretend the thermal shift was applied.
- For scored episodes, also fault_injection_applied, injected_severity_applied, acquisition_mode_applied, counter_source_applied, and diff_motor_t_mapping_applied.

For SHIFT_REGEN_COLD_6H, the adapter must scale each driver torque **before loss calculations**: negative torque (regeneration) ×1.5; positive torque (traction) ×0.85; zero remains zero. The runner contains the canonical scalar helper scale_signed_torque(torque_nm, profile_id) and the adapter may import it from scripts.run_stage4_experiments. Set the temperature target to 10 °C through the existing coolant_C or init_module_C field if available. If neither field is supported, return ambient_shift_applied=false; do not silently change the frozen model.

The adapter must not add latent truth, injected fault values, severity, labels, nuisance parameters, or seeds to observed channel rows. The runner projects rows onto the pre-registered observed-channel whitelist before feature extraction.

## Commands (PowerShell)

First restore the exact Stage 3/4 executable artifacts locally, then supply the adapter path. Example paths below are placeholders; use the actual paths on the machine:

~~~powershell
python scripts/run_stage4_experiments.py --mode smoke --model-py "C:\path\to\taycan_etapa4\taycan_sim\model.py" --freeze-json "C:\path\to\taycan_etapa4\freeze.json" --backend-file "C:\path\to\stage4_backend_adapter.py"
~~~

Only after the smoke run succeeds:

~~~powershell
python scripts/run_stage4_experiments.py --mode full --model-py "C:\path\to\taycan_etapa4\taycan_sim\model.py" --freeze-json "C:\path\to\taycan_etapa4\freeze.json" --backend-file "C:\path\to\stage4_backend_adapter.py"
~~~

Use the same output directory for both commands. By default, generated data go under results/tmp/stage4_run/, which is ignored by Git. The runner requires the successful 12-episode smoke receipt and the matching calibration receipt before --mode full can begin.

## Execution and output policy

- Hash guards run in the parent process and again inside every worker process.
- Charge power is calibrated separately for NOMINAL_6H and SHIFT_REGEN_COLD_6H using H00 training-only references, common random numbers across bisection points, 8–12 iterations, and a strict final-SOC residual/window check. Nonconvergence blocks all episode execution.
- Calibration seeds use the deterministic namespace TAYCAN4R|CALIBRATION|<profile>|<stream>, checked for collisions against all 8,928 manifest seeds and across the two profiles. The exact seeds are recorded in the calibration receipt.
- Smoke selects the first TRAIN row for each of the 12 hypotheses in manifest order. Smoke outputs are separate and are never counted in the 2,232 scored episodes.
- Full execution traverses the manifest in its original order. One episode is run per subprocess. Completed episode artifacts are skipped only when the done receipt and SHA-256 hashes of the feature CSV, metadata JSON, SOC trajectory, and run log all verify.
- stage4_feature_matrix.csv contains only episode ID, 28 numerical features, and 28 fixed missingness masks. stage4_evaluation_metadata.csv contains labels, split, severity, nuisance/structural fields, seeds, QC flags, regression diagnostics, and runtime. Truth SOC is written only to compressed audit trajectories and metadata; it never enters feature extraction.
- A nonfinite/missing required channel produces NA plus a missingness mask. Singular five-term R33 regression coefficients are NA with rank diagnostics; the runner does not silently ridge-fit them.
- No model fitting, validation-based parameter retuning, test-based retuning, or Stage 5 operation occurs here.

## Additional pre-test gate: M01 × I01 energy matching

The sealed preregistration requires a profile-specific, DIFF-mode-specific M01-to-I01 energy mapping before any full-manifest run. The runner does not invent a matching algorithm and does not create this calibration receipt. Until a separate calibration procedure produces and reviews the file below, full mode stops before launching any full episode:

results/tmp/stage4_run/calibration/M01_I01_ENERGY_MATCH_RECEIPT.json

The receipt must have status M01_I01_ENERGY_MATCH_COMPLETE, input_hashes equal to the five frozen input hashes plus the runner/backend hashes used during calibration, calibration_split equal to independent_calibration_only, uses_validation_outcomes=false, uses_test_outcomes=false, a unique calibration_seed_values list disjoint from all manifest seeds, and 12 mapping entries covering both profiles × both DIFF mappings × severities 0.25, 0.5, and 1.0. Each entry records profile_id, diff_motor_t_mapping, m01_severity, i01_severity_used, delta_E_motor_J, delta_E_inverter_J, mismatch_pct, and match_status (MATCHED or INFEASIBLE). MATCHED requires mismatch ≤1%; INFEASIBLE records the best feasible I01 severity and a mismatch >1%. The runner verifies the arithmetic and applies i01_severity_used to I01 episodes while preserving the manifest severity as the target/reference level.

This is a deliberate fail-closed gate, not a claim that the mapping calibration exists or has run.

## Current limitation

The runner source is committed, but no execution result is implied. Until the frozen model, original freeze file, and a backend adapter satisfying this contract are restored and verified, the correct status is **BLOCKED / NOT EXECUTED**.
