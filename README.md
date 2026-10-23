# Project-Taycan

Research on probabilistic diagnosis of a 2022 Porsche Taycan 4S using synthetic physics, observed vehicle signals and external battery-cell evidence.

## Stage 3 — original recovered simulator

The **byte-exact approved** Stage 3 simulator is at [`src/simulator/taycan_sim/model.py`](src/simulator/taycan_sim/model.py), with the required `signal_contract.json`, Python package files and original [28 tests](tests/unit/test_stage3_simulator.py).

Approved model SHA-256: `af4e576cf824d30ee6aa9b2fd1f2c18d576fd269027df67c43c5e7647266ff4e`.

Run tests from the repository root:

```bash
PYTHONPATH=src/simulator python -m unittest discover -s tests/unit -p 'test_stage3_simulator.py' -v
PYTHONPATH=src/simulator python -m taycan_sim --fault H00 --steps 180
```

On PowerShell set `$env:PYTHONPATH = "src/simulator"` first, then run the same `python` commands.

See [source recovery and provenance](docs/audits/STAGE3_SOURCE_IMPORT_2026-10-23.md) and [project status](docs/PROJECT_STATUS.md).

**Stage 4 remains blocked:** original `observation_layer.py` not recovered; no sealed episodes were scored and no formal Stage 4 approval has been issued. Experimental charging/regeneration modifications are **not** incorporated into this frozen source.

**Safety:** The simulator is research software, not a validated vehicle diagnostic or high-voltage safety tool.
