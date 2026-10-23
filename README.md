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

## Historical Stage 1 and Stage 2 primary reports

- [Stage 1 — Original 546-signal observability catalog](experiments/stage_01_observability/taycan_etapa1_observabilidade.md). OBDb source attribution and CC BY-SA 4.0 license remain in this original report.
- [Stage 2 — Original fault taxonomy and family-level diagnostic matrix](experiments/stage_02_fault_taxonomy/taycan_etapa2_relatorio.md).
- [Restoration provenance and remaining materials](docs/audits/STAGE1_STAGE2_SOURCE_IMPORT_2026-10-23.md).

The original 6,552-row signal-expanded Stage 2 matrix (7.4 MB JSON and original XLSX) and the Stage 1 auxiliary JSON are not yet part of the repository. **Do not claim their import, or full third-party reproduction of the matrix, before the exact source bytes are versioned.**
