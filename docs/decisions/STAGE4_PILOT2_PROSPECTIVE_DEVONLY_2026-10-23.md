# Stage 4 — Pilot 2 prospective DEVELOPMENT-ONLY specification
2026-10-23. This document and its paired source commit precede any Pilot 2 generation in this research branch.

**This is not a rewrite of the Stage 4 freeze, not an official Stage 5 inference exercise, and not permission to open holdouts.**

### Prospective factorial design

- 11 fault types x severities [0.10, 0.25, 0.50, 0.75, 1.00] x three degradation levels x 16 distinct seeds = 2640 fault episodes.
- H00, with severity exactly zero, uses five **quota strata**, three degradation levels and 16 independent episodes = 240 controls.
- 2880 ten-minute sessions, 120 steps at dt=5 s, using the explicitly assumed prior sinusoidal torque waveform.
- 36 six-hour sessions: [H00,B02,B04,B07,M01,I01] x three levels x [NOMINAL_6H,SHIFT_REGEN_COLD_6H], 4320 steps at dt=5 s, physical charge only in parked blocks. M01 0.5; the I01 six-hour contrast uses energy-matched severity **conditional on the unvalidated always-on inverter injection law**. These are not registered Stage 4 episodes.
- Physically unapproved model_energy_consistent and unapproved observation_layer_candidate remain labeled as candidates.
- All 5 RNG streams (physics, observer, auxiliary, nuisance, measurement degradation) are namespace-derived, unique and disjoint from the 8928 frozen seeds and 768 Pilot 1 development seeds.
- Chunked execution: six sharded jobs, one output JSONL each, with all attempted episodes and explicit error records. No samples, features or labels from reserved official evaluation are opened.

### Sensor degradation: ASSUMED hypotheses, NOT measured Taycan specifications

| Axis | Nominal | Realistic assumed | Severe assumed |
|---|---:|---:|---:|
| Temperature quantization | none | 0.1 C | 0.5 C |
| Voltage quantization | none | 0.005 V | 0.02 V |
| Current quantization | none | 0.2 A | 1 A |
| Torque quantization | none | 0.5 Nm | 2 Nm |
| RPM quantization | none | 2 rpm | 10 rpm |
| SOC quantization | none | 0.1 pp | 0.5 pp |
| Ah counter quantization | none | 0.01 Ah | 0.1 Ah |
| kWh counter quantization | none | 0.001 kWh | 0.01 kWh |
| Module temperature channels permanently disabled | 0 | 2 | 20 |
| Extra delayed observed channels | 0 | 3 | 15 |
| Delay (steps) | 0 | 1 | 4 |
| Channels with one dropout burst | 0 | 2 | 12 |
| Consecutive dropout samples / affected channel | 0 | 2 | 6 |

Sensor selection, delay and dropout start are determined by a fresh independent seed. Missing values stay missing. Stage 4's current feature extraction invalidates a feature if required samples are absent, therefore **valid-feature fraction and failure rate are primary outcomes** alongside separability. Never discard invalid episodes without reporting counts.

### Statistics frozen before inspection

- 12 hypotheses -> 66 unordered comparisons, five severity quota strata, three observer levels, 28 feature values and matching masks.
- Each feature: count of valid independent sessions, univariate Fisher (mean difference squared / sum of sample variances), symmetric Gaussian marginal KL proxy when variances positive; NA if fewer than 8 independent valid sessions or zero variance.
- 95% session-bootstrap percentile intervals, 200 fixed RNG-resamples, for Fisher; complete unabridged tables, not merely maximum-feature values. Report availability separately and include an explicit reason for unestimable metrics.
- Explore missingness, particularly full-series mask invalidation; do not interpret low sample availability as evidence of good or bad classification.
- With only 16 sessions in a cell, a 5% FPR/80% power **minimum detectable severity is not established**. No supervised model is trained in this run, no AUC claim or posterior, no feature selection based on official test data.
- M01/I01 raw severity contrasts are NOT energy-balanced; six-hour I01 contrast is matched by the candidate's deterministic loss function only and does not validate its physics.
- No vehicle identity in historical manifest; repeat index alone is not evidence of seed leakage. This experiment also does not measure vehicle-to-vehicle longitudinal generalization.
- A separate PyBaMM generator B is tracked in issue #3 and must be independently implemented/frozen before any transfer test. Do not claim an independent generator B is complete.

### Immutable reference
Stage 3 original model SHA256 af4e576cf824d30ee6aa9b2fd1f2c18d576fd269027df67c43c5e7647266ff4e; freeze.json SHA256 5822c3e43e6f4634c7ca60d0aabb6f38afe5cecece99883833ee1c4d12dc5df8. The original 2232 rows (720 train, 360 validation, 1152 reserved test) and all approved features/runner code are untouched.

### Reproducibility caveats
This report specifies research hypotheticals. CI success demonstrates that this synthetic pipeline executed, **not** real-world Porsche accuracy, safety, diagnostic identifiability or calibrated instrument specifications.