# Project Taycan — Stage 3/4 candidate integration audit (2026-10-23)

**Classification: EXPERIMENTAL / NONSCORING / NOT FORMALLY APPROVED.**

## Frozen basis

The approved Stage 3 `src/simulator/taycan_sim/model.py` is retained byte for byte:

`SHA-256 af4e576cf824d30ee6aa9b2fd1f2c18d576fd269027df67c43c5e7647266ff4e`

The sealed Stage 4 `freeze.json` is likewise unchanged (`SHA-256 5822c3e43e6f4634c7ca60d0aabb6f38afe5cecece99883833ee1c4d12dc5df8`). The runner still requires the **original** approved model hash. **Do not disguise the model candidate as that frozen model or disable the runner hash gate.**

The actual historical Stage 4 `observation_layer.py` has not been recovered. The new `src/observation/observation_layer_candidate.py` is a **new synthetic implementation**, not a recovered original or a validated equivalent.

## Physical problem reproduced

In the frozen model the inverter loss uses `P_mech*(1/eta-1)` and gearbox loss uses `P_mech*gearbox_loss_fraction`. For a negative torque at positive RPM, both terms become negative, creating a non-dissipative power accounting artifact. The supplied candidate switches to nonnegative bidirectional losses, accepts signed torque sequences, a DC-side external power source, and a separately sampled nonnegative stochastic auxiliary load sequence. It uses explicit signed power balance:

`P_battery_DC = P_mechanical + P_motor_loss + P_inverter_loss + P_gear_loss + P_auxiliary - P_external_DC`.

This is a *toy bidirectional driveline model*: it has no mechanical wheel/road state, charger state machine, AC charging hardware efficiency, battery pack HV safeguards, derating, taper, torque demand saturation or pack thermal verification. In particular, a DC injection while torque is nonzero is an artificial boundary stress test, **not evidence that a Taycan can charge while driving**. The proof of conservation refers to its algebraic power boundary, **not validated whole-vehicle thermodynamics**.

## Observation candidate contract

- Input: only noise-disabled, approved OBD channel rows from `taycan_sim` or `candidate_sim`, **never** hidden `truth` rows.
- Fail-closed approved-ID whitelist sourced from the approved Stage 3 signal contract. Unknown channels, labels or latent truth keys are rejected.
- Four pseudorandom streams in the *combined exploratory pipeline*: `physics` for physical model initialization, `observer` for white measurement/AR(1) innovations, `aux` for auxiliary stochastic electric load, and `nuisance` for registered nuisance scale/bias selection. `make_observation_config` from the existing runner produces the nuisance draws; the candidate consumes the post-bias xorshift state for persistent group-SOC biases. The streams are independently seeded.
- RPM and torque: registered per-channel persistent offsets plus white noise, held fixed through the episode.
- SOC groups: registered persistent Gaussian group bias plus a **candidate** exact sampled continuous-time OU model using phi per second, with measured SOC constrained to 0–100%; the clipping count is disclosed.
- Current acquisition: shared mode uses identical BMS/HVBAT current readings; independent mode uses separate white innovations.
- Counter source: `BMS_I` or `HVBAT_CURRENT` only; `truth` forbidden. Coulomb and energy totals use the chosen observed current and observed voltage, preserving sample-0 baseline semantics for F14/F28.
- Experimental auxiliary trace: AR(1)/OU-driven DC load explicitly clipped to [0, `aux_cap_W`]; injected into the candidate's DC power demand **before** physical current and SOC integration. The cap interpretation and clipping are **assumptions needing prospective approval**.
- Voltage/temperature noise amplitudes currently use Stage 3 nominal assumptions; voltage/temperature correlation, asynchronous timestamps, missing samples, quantization and delays are **not yet implemented** in this candidate. This is not complete Stage 4 observational equivalence.

## Reproduced results

All checks run locally with the recovered original and sealed Stage 4 parameters:

- Stage 3 original: **28/28** unit tests passed.
- Stage 4 runner/manifest unit tests (separate existing test suite): **10/10** passed.
- Earlier unmodified boundary candidate: **6/6** passed.
- Combined local workspace with updated physical and observation candidates, Stage 3 tests and compatible Stage 4 tests: **52/52** passed, including **19** new candidate tests. This count should be interpreted as local test cases, not official episodes.
- Exploratory candidate coupling: one TRAIN-manifest-configured H00 and one B06 probe, each `120 × 5 s` steps; custom signed torque trace. Neither is a registered six-hour NOMINAL/SHIFTED run. Each produced all 28 feature names and 28 masks, with no missing feature in these probes; power-balance residual < `5e-11 W` and no negative dissipative inverter/gearbox loss. F14/F28 are near zero under counter source `BMS_I`, with nonzero differences under independent `HVBAT_CURRENT` acquisition.
- Additional end-to-end non-scoring sweep: all **12** hypotheses run with unique TRAIN-manifest seeds, each 120 steps at dt=5s and the same declared custom torque waveform (not a frozen 6-hour driving profile). Every case produced 28 named features and 28 masks; **0 total missing features**, **0 steps with negative inverter/gear dissipation**, maximum instantaneous DC balance residual **6.55e-11 W**. This is an integration-coverage check, **not** the registered Stage 4 smoke.
- **0** official six-hour Stage 4 smoke experiments scored; **0** of 2,232 official episodes scored.

To reproduce local tests with Python 3.10+:

```bash
PYTHONPATH=src/simulator:src:. python -m unittest discover -s tests/unit -p 'test_*.py' -v
python scripts/probe_candidate_pipeline.py
python scripts/probe_candidate_12_hypotheses.py
```

The probe generates `results/candidate_pipeline_probe.json` (synthetic, **NOT** held-out evaluation). Do not optimize nuisance parameters based on its output.

## Non-negotiable gates before scoring

1. Decide whether the new physics model should be formally revised and refrozen. If yes, create a prospectively approved new preregistration with a **new** model hash; do not rewrite or backdate sealed original experiments.
2. Locate the actual observation layer or formally approve this replacement **after** checking correlated acquisition, missingness, timing, quantization, SOC drift, and parameter interpretation.
3. Develop an explicit backend for the revised protocol and validate 5-second sampling and F14/F28 counters. The current sealed runner cannot legitimately run this candidate against the old model hash.
4. Audit admissible loading/charging schedules; enforce SOC, current, voltage, temperature and operating-mode limits; independently test step-size sensitivity and energy closure.
5. Then, and only with approval, calibrate training-only H00 charge inputs, complete 12 M01/I01 energy mappings, run the 12-episode smoke, execute 2,232 episodes, audit all output and assess external datasets. No Stage 5 training yet.

**The candidate branch is a proposal. Merge into approved scientific sources only after a documented approval gate.**
