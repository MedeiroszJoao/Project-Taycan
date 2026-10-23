# Stage 3 source import and provenance — 2026-10-23

## Result

**RECOVERED EXACT APPROVED MODEL — COMMITTED UNCHANGED.**
This import records source recovery, not approval of a new physics model or Stage 4.

- Approved archive member: `taycan_etapa3/taycan_sim/model.py`.
- Original archive: `taycan_etapa3_codigo_testes_final.zip`; archive SHA-256 `a2c47cb29bea4db57cfd20ffe8f4e22b98fc5b3b5dfc3e3ef6d27d28cc81eaaa`.
- `model.py` SHA-256 **`af4e576cf824d30ee6aa9b2fd1f2c18d576fd269027df67c43c5e7647266ff4e`**, exactly equal to the approved Stage 3 hash in `docs/PROJECT_STATUS.md` and the Stage 4 `freeze.json`.
- Original `model.py` Git blob SHA-1: `21f2f74f372ef7dbbc802bcdb92714309f9eacf0` (checks the Git upload preserves the original bytes).
- Other recovered, byte-preserved members: `taycan_sim/__init__.py`, `taycan_sim/__main__.py`, `taycan_sim/signal_contract.json`, and `tests/test_simulator.py`.
- Stage 3 source package: `src/simulator/taycan_sim/`.
- Original test source: `tests/unit/test_stage3_simulator.py` (path renamed, **contents unchanged**).
- Re-executed original tests locally: **28/28 PASS** under Python 3.13. These test internal simulation behavior and contract consistency, not Taycan-real-world validity.

## Reproduction

From the repository root (Linux/macOS):

```bash
PYTHONPATH=src/simulator python -m unittest discover -s tests/unit -p 'test_stage3_simulator.py' -v
PYTHONPATH=src/simulator python -m taycan_sim --fault H00 --steps 180
sha256sum src/simulator/taycan_sim/model.py
```

PowerShell:

```powershell
$env:PYTHONPATH = "src/simulator"
python -m unittest discover -s tests/unit -p "test_stage3_simulator.py" -v
python -m taycan_sim --fault H00 --steps 180
(Get-FileHash "src/simulator/taycan_sim/model.py" -Algorithm SHA256).Hash
```

## Scientific and safety constraints

1. The recovered source is unchanged. **Do not modify or replace it** to introduce charging input, negative-torque/regeneration fixes or time-varying torque without a separately authorized model revision and documented new hash.
2. The experimental physics extension evaluated on 2026-10-23 is **not** imported into the approved package.
3. Original `observation_layer.py` remains **NOT RECOVERED**. Stage 4 smoke/full runs, the sealed 2,232-episode study and Stage 5 inference are **not authorized or claimed** by this import.
4. The model's physical parameters are assumptions and not calibrated for a real 2022 Taycan; this software is not a certified diagnostic device.
