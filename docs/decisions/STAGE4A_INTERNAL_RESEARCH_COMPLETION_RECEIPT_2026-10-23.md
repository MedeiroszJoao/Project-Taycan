# Stage 4A — internal research-only completion receipt

**Decision date:** 2026-10-23.
**Outcome:** **4A RESEARCH INFRASTRUCTURE INTERNALLY ACCEPTED (NON-COMMERCIAL)**.
**Scope:** reproducible, numerically gated **synthetic** scenario generation and original-TRAIN-manifest compatibility. **NOT** Porsche real-vehicle validation, not Stage 4B completion, not authorization to score the frozen validation or reserved test episodes, not an external homologation.

## Authorization and provenance

The owner explicitly accepted on 2026-10-23 the proportionate, internal non-commercial scientific approval pathway in the conversational record (“Ok, anote e prossigamos”). The exact acceptance and limitations are documented in `docs/decisions/STAGE4A_INTERNAL_NONCOMMERCIAL_ACCEPTANCE_2026-10-23.md`.

Version-qualified Python 3.11 CI run:
**[40032193170](https://github.com/MedeiroszJoao/Project-Taycan/actions/runs/40032193170)**, commit `390144a23bc2bceb380381bf8a951fae4ac41c4b`. Checks:

| Gate | Executed result |
|---|---|
| All unit tests on qualified successor | **104/104 PASS** |
| Original TRAIN manifesto compatibility, one selected six-hour row per H00/B01–B09/M01/I01 | **12/12 PASS, zero failures** |
| All 28 observed features under nominal sensor coverage | **28/28 each** |
| Individual simulated branch SOC, all 12 series | **42.432455–62.241852%**, inside preregistered 30–80% candidate QC window |
| DC-bus algebra residual | max **1.0186341e-10 W** against **1e-5 W** threshold |
| Exact fixed-parameter 1RC local energy identity | max **1.8891555e-12 J/step** against **1e-4 J/step** threshold |
| Validation / test episodes simulated | **0 / 0** |
| Original Stage 3 source and frozen prereg/manifests changed | **NO**; recorded SHA-256 guards verify unchanged |
| Training smoke receipt | `stage4a-successor-train-smoke12-attestation` GitHub Actions artifact; source and feature vector hashes archived |

### Attested SOURCE SHA-256 from independent GitHub runner

- Historical Stage3 model: `af4e576cf824d30ee6aa9b2fd1f2c18d576fd269027df67c43c5e7647266ff4e`.
- Original freeze: `5822c3e43e6f4634c7ca60d0aabb6f38afe5cecece99883833ee1c4d12dc5df8`.
- Frozen 2232-row manifest: `1894681c771335e5ecb06f8fa421c11aaf8806c5f5ebab3182035e44d28b86f0`.
- Original prereg: `1c3c50149e50bceb3f14b8a334b248c225cdc8478128cf88952051ea0bce1b21`.
- Frozen amendment: `18c5c8f104f2909a1f23a594eafd8e26a77a1ea4f80e285e0e1396b5a1da29ba`.
- Candidate research-only gated physics: `43972371b3014bd81ef4176cc396f27b855691bb8c6aa7ec743458e5b64b1310`.
- Candidate **reconstructed and corrected** observer: `f330dea792f54607a86bd5476e4f2846fc5c5393e194f15b5dd98b5214ee7869`.
- Six-hour duty: `51ea794b3d82cf0a14fc901485c65af9420249cce134c3098ce2365724f8ade6`.
- Original 28-feature extractor: `2c71b9b5d6ca7fa310ec95d258407c2fb7d0956a0cc4c58084ad7b1d25395ccf`.
- Train-only successor smoke runner: `66c350807b6db455690779fe81c3ae611a6a8abe9a57d81d483309db6de7787f`.
- Acceptance document: `5557f1421305c11ff8edb0678991b3e8a670677a6c556fa96f01c2ba5b3a2f99`.
- Prospective train smoke specification: `e65ed9e1cd2d0b6beadcf304eab4003f81364ef7974b18cfa1379228f417fd85`.

Calibration preceding qualification:
[40027130137](https://github.com/MedeiroszJoao/Project-Taycan/actions/runs/40027130137) used a separate development reference waveform and prospective brackets; nominal charge = **47.79296875 kW** and shifted charge = **31.5625 kW**; I01 severity is mapped to energy-equivalent M01 loss based on assumed activity-gated fault function. **Energy matching is not physical/observational class identity.**

The previous independent *development-only* 12×6h candidate smoke (corrected observation version) also passed [40028102083](https://github.com/MedeiroszJoao/Project-Taycan/actions/runs/40028102083). The later train-only CI improves the evidence by exercising 12 actual frozen TRAIN nuisance/seed records.

## Explicit claims excluded

1. **No entire first-law energy conservation**: only DC algebra and fixed-parameter RC local identity are checked. Temperature- and aging-dependent chemical/capacitance work, reversible heat, and side reactions are not fully closed or independently measured.
2. **No recovered original observer**: `observation_layer_4a_candidate.py` is a new documented implementation; the original Stage4 `observation_layer.py` remains unavailable with verified provenance.
3. **No known-real I01 idle behavior**: inverter fault excess is modeled as zero when torque or RPM are zero. The model is conditional and not OEM-calibrated.
4. **No sensor robustness assurance**: absence of any required sensor can mask F15–F17; the 2916-scenario exploratory Pilot2 used an older observer layer and cannot independently validate corrected-observer performance.
5. **No true diagnostic performance/AUC/power claim**, no PyBaMM independent generator B, no TUM/LG E66 whole-vehicle validation, no full 2232 official scoring and **no test-set access**.

## Next steps, not blockers to internal 4A sign-off

- **Stage 4B:** independent battery-generator / external data validity and detectability under sensor degradation.
- A separate **campaign execution authorization** is needed before processing all 2232 frozen cases, including 360 validation and 1152 reserved test. The original historical hash-gated runner must stay untouched; any full successor runner uses new release/protocol namespace, strict split isolation, and separate results.
- Keep the PR in DRAFT until reviewed; no scientific change is merged into `main` by this receipt alone.

**Final categorization:** **COMPLETED: Stage4A engineering infrastructure for non-commercial synthetic research.** **NOT COMPLETED:** broader Stage4 scientific validity (Stage4B), original full campaign, Bayesian inference.
