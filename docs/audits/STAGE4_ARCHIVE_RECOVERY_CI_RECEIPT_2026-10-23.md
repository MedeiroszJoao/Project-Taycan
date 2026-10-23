# Stage 4 archive recovery: test and provenance receipt (2026-10-23)

## Verified technical results

- GitHub repo: `MedeiroszJoao/Project-Taycan` (public).
- Work branch: `research/stage4-archive-recovery-2026-10-23`.
- Main and approved Stage 3 physics model: **not changed**.
- Recovery utility and synthetic tests committed.
- Standard GitHub-hosted Linux runner; no paid DigitalOcean machine was created.
- GitHub Actions [run 39931760561](https://github.com/MedeiroszJoao/Project-Taycan/actions/runs/39931760561) concluded `success`.
- Verified logs: **10/10 unit tests OK**. Categories: five recovery tests, two F14/F28 counter tests, three sealed manifest/whitelist tests.
- Sealed files verified in CI: SHA-256 preregistration, amendment, manifest, freeze.json. Manifest validation: 2,232 unique episode IDs, split constraints, hypotheses, seeds and profile constraints enforced by runner `load_manifest()`.
- Later [run 39932114576](https://github.com/MedeiroszJoao/Project-Taycan/actions/runs/39932114576) concluded `success` after documentation changes. The unit-test suite was unchanged.

## Archive recovery (not yet ZIP-content verification)

Project file service reported copying five existing generated archives:
- `taycan_etapa3_codigo_testes.zip` (33,253 bytes, earlier)
- `taycan_etapa3_codigo_testes_final.zip` (49,271 bytes, later)
- `taycan_etapa4_codigo_dados.zip` (86,017 bytes, earlier)
- `taycan_etapa4_codigo_dados_later.zip` (86,017 bytes, later)
- `taycan_etapa4_dados_reais_e_codigo.zip` (203,907 bytes)

**Precise limitation:** no `zipfile` inspection or SHA-256 verification of any embedded `model.py` or `observation_layer.py` took place because the local execution session remained inaccessible. Do not conflate ZIP materialization with internal extraction or byte identity.

## Open execution gates

1. Run checksum-gated archive recovery utility against the **later** Stage 3 ZIP first, inspect the actual ZIP members and save the receipt.
2. Reconcile any differing `observation_layer.py` versions. Do not invent an SHA-256.
3. Import the exact Stage 3 API; implement backend adapter without changing physics or sealed experiment files.
4. Re-run Stage 3 original tests and verify H00/BMS_I F14/F28 against the actual model.
5. Perform M01/I01 energy matching (within preregistered tolerance), charge calibration, 12-episode smoke and only then full 2,232 episodes.
6. External-cell validation remains a separate requirement; not started by these CI runs.

## Status classification

- `CODE_AND_SYNTHETIC_TESTS: PASS`
- `MANIFEST_SEAL_VALIDATION: PASS`
- `ORIGINAL_MODEL_SOURCE_HASH: NOT VERIFIED`
- `ORIGINAL_OBSERVATION_LAYER: NOT VERIFIED`
- `SMOKE_AND_PHYSICAL_BACKEND: NOT EXECUTED`
- `STAGE4: UNAPPROVED`

These statuses supersede any impression that the Stage 4 scientific experiment has been completed.
