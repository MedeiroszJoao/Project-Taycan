# Project Taycan — research status

Scope: probabilistic fault diagnosis for the 2022 Porsche Taycan 4S with standard 79.2 kWh Performance Battery (28 modules, 336 cells).

## Approval gates

| Stage | Status |
| --- | --- |
| 1 — Observability catalog | Approved; artifacts not yet imported to this repository |
| 2 — Fault taxonomy and signal matrix | Approved; artifacts not yet imported |
| 3 — Physical simulator and tests | Approved; original `model.py`, required package files, and 28 original unit tests now imported unchanged |
| 4 — Synthetic and external battery datasets | **4A internally completed for research-only synthetic infrastructure (2026-10-23); 4B scientific validity still OPEN; original official 2232-episode campaign NOT RUN** |
| 5–8 | Not authorized to start |

The Stage 3 `taycan_sim/model.py` approved SHA-256 is:
`af4e576cf824d30ee6aa9b2fd1f2c18d576fd269027df67c43c5e7647266ff4e`.

Do not replace approved files, alter frozen assumptions, or advance a stage without an explicit stage approval.

NASA and Oxford datasets provide external cell-level evidence, **not** Taycan-specific pack/motor/inverter validation. The repository now includes the exact recovered Stage 3 simulator under `src/simulator/taycan_sim/` and the original tests under `tests/unit/test_stage3_simulator.py`. The **historical Stage 4 full campaign** remains unexecuted because its original observer is not recovered and the original hash-bound runner is not to be bypassed. **Separately**, research-only Stage 4A synthetic infrastructure passed 104/104 tests and a successor 12×6h smoke using original TRAIN-manifest rows, with zero reserved test access; its internal noncommercial completion receipt is at `docs/decisions/STAGE4A_INTERNAL_RESEARCH_COMPLETION_RECEIPT_2026-10-23.md`. The corrected candidate physics/observer is a new, explicitly separate research implementation, NOT part of the historically approved frozen Stage3 model. Stage4B physical validity and external validation remain open.

## Safety and evidentiary caveats

This research software must not be used as a certified diagnostic tool or as authority for high-voltage repair, vehicle operation, or safety-critical release decisions.
Keep real and synthetic measurements clearly distinguished. Record file provenance, source date, variant, license, units, and SHA-256 in `data/manifests/` or `docs/sources/`.
