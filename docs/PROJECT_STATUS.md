# Project Taycan — research status

Scope: probabilistic fault diagnosis for the 2022 Porsche Taycan 4S with standard 79.2 kWh Performance Battery (28 modules, 336 cells).

## Approval gates

| Stage | Status |
| --- | --- |
| 1 — Observability catalog | Approved; artifacts not yet imported to this repository |
| 2 — Fault taxonomy and signal matrix | Approved; artifacts not yet imported |
| 3 — Physical simulator and tests | Approved; source not yet imported |
| 4 — Synthetic and external battery datasets | Delivered for audit; formal approval pending |
| 5–8 | Not authorized to start |

The Stage 3 `taycan_sim/model.py` approved SHA-256 is:
`af4e576cf824d30ee6aa9b2fd1f2c18d576fd269027df67c43c5e7647266ff4e`.

Do not replace approved files, alter frozen assumptions, or advance a stage without an explicit stage approval.

NASA and Oxford datasets provide external cell-level evidence, **not** Taycan-specific pack/motor/inverter validation. The repository currently contains a scaffold only.

## Safety and evidentiary caveats

This research software must not be used as a certified diagnostic tool or as authority for high-voltage repair, vehicle operation, or safety-critical release decisions.
Keep real and synthetic measurements clearly distinguished. Record file provenance, source date, variant, license, units, and SHA-256 in `data/manifests/` or `docs/sources/`.
