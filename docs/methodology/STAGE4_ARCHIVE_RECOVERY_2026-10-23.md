# Stage 4 — Source recovery (unapproved, non-destructive)

Date: 2026-10-23. This is an **archive recovery procedure**, NOT a reconstructed physical simulator and NOT a completed Stage 4 experiment.

## Original archive references

Previously generated in the project and recovered as raw files by the conversation file service:

| Original archive | Recovered size (bytes) | Role |
|---|---:|---|
| taycan_etapa3_codigo_testes.zip (earlier copy) | 33253 | Initial Stage 3 archive; **do not assume final frozen model** |
| taycan_etapa3_codigo_testes_final.zip (later copy) | 49271 | Later Stage 3 archive; primary candidate for the approved frozen model |
| taycan_etapa4_codigo_dados.zip | 86017 | Earlier Stage 4 observation / synthetic data layer |
| taycan_etapa4_codigo_dados_later.zip | 86017 | Later generated Stage 4 archive; bytes not yet compared |
| taycan_etapa4_dados_reais_e_codigo.zip | 203907 | Later Stage 4 code and externally oriented package |

The file-service recovery provided these working-copy paths:
- /mnt/data/recovered/taycan_etapa3_codigo_testes.zip
- /mnt/data/recovered/taycan_etapa3_codigo_testes_final.zip
- /mnt/data/recovered/taycan_etapa4_codigo_dados.zip
- /mnt/data/recovered/taycan_etapa4_codigo_dados_later.zip
- /mnt/data/recovered/taycan_etapa4_dados_reais_e_codigo.zip

**Important:** The file service reported successfully placing the archive bytes at these paths; an executable Python/container session was unavailable at the time, so contents and archive checksums were **not** yet independently audited. Archive names and sizes are not evidence that either source is present inside.

## Frozen hashes (do not change)

- Stage 3 `taycan_sim/model.py` SHA-256: `af4e576cf824d30ee6aa9b2fd1f2c18d576fd269027df67c43c5e7647266ff4e`
- Stage 4 `freeze.json` SHA-256: `5822c3e43e6f4634c7ca60d0aabb6f38afe5cecece99883833ee1c4d12dc5df8`
- The original `freeze.json` **is** stored at `experiments/stage_04_data_validation/freeze.json` in GitHub.
- No trusted checksum is currently assigned to `observation_layer.py`. Recover it with complete archive provenance and compare alternative copies byte-for-byte.

## Procedure

After the Python environment becomes available, from repository root:

```bash
python3 scripts/recover_frozen_stage3_from_archives.py \
  --stage3-zip /mnt/data/recovered/taycan_etapa3_codigo_testes_final.zip \
  --stage4-zip /mnt/data/recovered/taycan_etapa4_codigo_dados_later.zip \
  --stage4-zip /mnt/data/recovered/taycan_etapa4_dados_reais_e_codigo.zip
```

Without `--write`, this inventories files, compares SHA-256, and emits a JSON receipt. It **does not** modify files. If both sources are found and verified, rerun with `--write` to copy the exact source bytes into **isolated** `recovery/stage4_verified/` and generate `recovery_receipt.json`. Never commit a replacement `model.py` into the approved Stage 3 paths without hash equality.

Run the separate synthetic tests:

```bash
python3 -m unittest discover -s tests/unit -p 'test_stage4_archive_recovery.py' -v
python3 -m unittest discover -s tests/unit -p 'test_stage4_counter_alignment.py' -v
```

Then compare/import original dependencies and implement a minimal Stage 4 backend adapter against the **real recovered API**, not an invented signature. Check the adapter's counter timing, per-channel biases and split/seed isolation. Full 2,232-episode execution remains **blocked** until smoke tests and M01/I01 energy-calibration receipt pass. Do not advance to Stage 5 without the literal Stage 4 approval.

## Fail-safe alternatives

A. If the approved `model.py` hash occurs in one ZIP, recover that exact file and use it without modification.

B. If none matches, record `BLOQUEIO: MODEL_FROZEN_HASH_NOT_FOUND` and prepare a **separate, explicitly labelled candidate reconstruction** for review. A reconstructed file cannot claim the old SHA-256, cannot replace the Stage 3 approved model, and would require an explicit Stage 3 revision/re-freeze before becoming authoritative.

No paid infrastructure, storage, compute, or credentials are required by this plan.

**Version integrity warning:** the earliest Stage 3 archive was reportedly generated with fewer tests than the later approved stage. Its size (33,253 bytes) differs from the later 49,271-byte archive, which is now the primary source candidate. The approved model is identified by SHA-256 alone; neither filename nor filesize proves validity. Do not choose the earliest archive just because it was found first.
