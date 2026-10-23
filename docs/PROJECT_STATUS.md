# Project Taycan — research status

Scope: probabilistic fault diagnosis for the 2022 Porsche Taycan 4S with standard 79.2 kWh Performance Battery (28 modules, 336 cells).

## Approval gates

| Stage | Status |
| --- | --- |
| 1 — Observability catalog | Historically approved; complete 546-signal Markdown catalog imported; accompanying JSON still pending |
| 2 — Fault taxonomy and signal matrix | Historically approved; original Markdown taxonomy/report imported; 6,552-row expanded JSON/XLSX matrix still pending |
| 3 — Physical simulator and tests | Approved; original `model.py`, required package files, and 28 original unit tests now imported unchanged |
| 4 — Synthetic and external battery datasets | Delivered for audit; formal approval pending |
| 5–8 | Not authorized to start |

The Stage 3 `taycan_sim/model.py` approved SHA-256 is:
`af4e576cf824d30ee6aa9b2fd1f2c18d576fd269027df67c43c5e7647266ff4e`.

Do not replace approved files, alter frozen assumptions, or advance a stage without an explicit stage approval.

NASA and Oxford datasets provide external cell-level evidence, **not** Taycan-specific pack/motor/inverter validation. The repository now includes the exact recovered Stage 3 simulator under `src/simulator/taycan_sim/` and the original tests under `tests/unit/test_stage3_simulator.py`. Stage 4 remains blocked on the original observation layer, backend integration, and formal validation. The experimental Stage 4 boundary-condition extension is not part of the approved frozen model.

## Safety and evidentiary caveats

This research software must not be used as a certified diagnostic tool or as authority for high-voltage repair, vehicle operation, or safety-critical release decisions.
Keep real and synthetic measurements clearly distinguished. Record file provenance, source date, variant, license, units, and SHA-256 in `data/manifests/` or `docs/sources/`.
