# Stage 4 source recovery audit — 2026-10-23

> **Historical snapshot, superseded in part by [Stage 3 source import](STAGE3_SOURCE_IMPORT_2026-10-23.md):** On 2026-10-23 the original Stage 3 `model.py` was subsequently recovered byte-for-byte, its SHA-256 verified, its 28 tests passed, and its package imported into `src/simulator/taycan_sim/`. The original Stage 4 `observation_layer.py` is **still missing**, and Stage 4 is **not approved**. Statements below describe the earlier recovery attempt and have not been silently rewritten.

## Status

**ORIGINAL ARCHIVES LOCATED AND MATERIALIZED; ORIGINAL PYTHON MEMBERS NOT YET EXTRACTED; STAGE 4 UNAPPROVED.** Do not claim original `model.py` or `observation_layer.py` recovered until the bytes have been read and checked.

This is a provenance/engineering audit, **not** a physical-model run or external validation.

## Evidence found

- Project attachment: `taycan_etapa3_codigo_testes.zip`, materialized as `/mnt/data/recovered_taycan/taycan_etapa3_codigo_testes.zip` (33,253 bytes reported by the project Files system).
- Project attachment: `taycan_etapa4_codigo_dados.zip`, materialized as `/mnt/data/recovered_taycan/taycan_etapa4_codigo_dados.zip` (86,017 bytes reported by the project Files system).
- The original ZIP bytes were stored in the conversation's container artifact surface, **not committed to this GitHub repository**. Their ZIP SHA-256 values have not yet been calculated.
- Container shell, private Python and user-visible Python runtime all returned `ClientError`, preventing extraction and a native test run. Do not interpret that as lost ZIP bytes.
- GitHub repository `main` contains Stage 4's `freeze.json` and sealed preregistration, amendment, 2,232-row manifest, runner and tests; it lacks the frozen Stage 3 `taycan_sim/model.py` and executable `observation_layer.py`. A check of known candidate historical GitHub paths returned no commits, and the releases list was empty.
- DigitalOcean's attached account has no existing droplets. No paid infrastructure was created.
- Exa's result for Taycan model sources pointed at other projects (MATLAB/Simulink MPC), **not** the original Python source. Importing that code would violate provenance/frozen-model rules.

## Frozen checksums

- Stage 3 `taycan_sim/model.py` SHA-256: `af4e576cf824d30ee6aa9b2fd1f2c18d576fd269027df67c43c5e7647266ff4e`.
- Stage 4 `freeze.json` SHA-256: `5822c3e43e6f4634c7ca60d0aabb6f38afe5cecece99883833ee1c4d12dc5df8`.

There is **no established original SHA-256 of `observation_layer.py`**. Its recovered bytes must be preserved, archived with a newly measured hash, reviewed for original provenance, and tested with the frozen model. A hash measured only now is not retroactively an approved frozen hash.

## Fail-closed recovery mechanism added

`scripts/recover_stage3_stage4_sources.py`:

- Reads archive members through `zipfile`, validating each member's ZIP CRC.
- Requires `model.py` in the Stage 3 archive and refuses every candidate whose byte-level SHA differs from the frozen checksum.
- Requires a unique `observation_layer.py` in the Stage 4 archive; refuses conflicting copies.
- Checks the repository Stage 4 `freeze.json` against the frozen SHA; compares any embedded Stage 4 copy.
- Refuses overwriting already-present Python files with different bytes.
- Writes a deterministic `recovery_receipt.json`, including ZIP/source SHA-256, source member paths and non-approval status.
- Does not change or regenerate the physical model and does not run the 2,232-episode experiment.

Six synthetic regression scenarios are defined in `tests/unit/test_recover_stage3_stage4_sources.py` for successful repeatable recovery, conflicting layers, tampered models, missing layers, tampered freeze and refusal to overwrite. **These tests have not run.**

## Exact commands for any available Python 3.10+ workspace

From the repository root, with the two original ZIP archives available locally:

```bash
python -m unittest discover -s tests/unit -p 'test_recover_stage3_stage4_sources.py'

python scripts/recover_stage3_stage4_sources.py \
  --stage3-zip /PATH/TO/taycan_etapa3_codigo_testes.zip \
  --stage4-zip /PATH/TO/taycan_etapa4_codigo_dados.zip \
  --freeze experiments/stage_04_data_validation/freeze.json \
  --output recovered-stage4
```

Verify the output receipt, the imported source code and the Stage 3 frozen tests. Only then write/test the Stage 4 backend adapter; execute the F14/F28 counter-alignment tests, calibrate M01/I01, run the 12-episode smoke, and finally seek approval to execute the sealed 2,232-episode manifest.

## Failure paths

1. **ZIP member found but hash fails:** do not use it as the Stage 3 original. Inspect other preserved copies, GitHub historical branches and original archived exports; report a hard integrity block if all differ.
2. **Original archive truly lacks required source:** preserve evidence and stage a separately labeled candidate reconstruction in a distinct location/branch, subject to an explicit `REVISAR ETAPA 3` instruction before replacing the frozen model. Never forge the original checksum or claim equivalence based on descriptions.

No Stage 5 work is authorized by this recovery audit.
