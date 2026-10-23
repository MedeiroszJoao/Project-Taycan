# Stage 4 — M01/I01 operating-mode adversarial audit

**Non-scoring developmental evidence, 2026-10-23.** The research candidate currently implements `p_inv_loss += 1600 W * severity_I` in **every step**, even with `rpm = torque = 0` during `rest` and `charge`; in contrast, `M01` additional copper losses are proportional to `torque**2`.

In the six-hour research-only duty cycle, 12-minute blocks repeat each hour: 3 active blocks + 2 stationary blocks, hence the duration split is **12,960 s active and 8,640 s stationary**. At fixed matching energy the I01 candidate attributes exactly **40%** of its fault energy to those parked blocks, which has not been justified by direct inverter measurements.

With `E_M = k_copper*(multipler-1)*severity_M * ∫torque(t)^2 dt` and `P_I = 1600*severity_I`:

- **Always-on candidate:** `severity_I = E_M / (1600 * 21,600)`.
- **Activity-gated alternative (counterfactual only):** `severity_I = E_M / (1600 * 12,960)`.
- Gated/always-on severity ratio: **5/3**. For nominal `severity_M=1`, `0.059297892` becomes approximately `0.098829820`. For cold+regen `0.063862109` becomes approximately `0.106436848`.

This is not a choice between two experimentally validated inverter fault models. Standby dissipation may occur under some hardware failure states; it requires a **declared operating-state model and measured or defensible standby-power prior**. The core issue is nonidentifiability of the energy-based mapping under an unfrozen model assumption. The existing **12/12 mathematically matched candidate cases remain conditional** on the always-on rule; DO NOT reuse them as Stage 4 calibration receipts.

Reproduce:

```bash
PYTHONPATH=src/simulator:src:. python scripts/audit_stage4_m01_i01_modes.py
PYTHONPATH=src/simulator:src:. python -m unittest discover -s tests/unit -p 'test_*.py' -v
```

References: <https://newsroom.porsche.com/en_AU/2021/products/technical-feature-the-porsche-taycan-23670.html> describes pulse-controlled inverter operation in traction and regeneration, but does **not** establish constant 1.6 kW failure loss while parked. Do not claim production-Taycan idle fault power is zero either.

Approval remains **BLOCKED**; original Stage 3 `model.py`, `freeze.json`, 2,232-row manifest and all held-out data remain untouched.
