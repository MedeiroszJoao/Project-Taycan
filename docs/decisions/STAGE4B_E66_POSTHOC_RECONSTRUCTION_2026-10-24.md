# Stage 4B — auditable E66 post-hoc reconstruction (NOT original Work freeze)

**2026-10-24 — research-only retrospective experiment recorded BEFORE starting this reconstruction.**

The original Work `FIT_RESULT.json`, `GENERATOR_B_FREEZE.json`, `EVALUATION.json` and solver logs were not recovered from the GitHub branches, available CI runs or attached indexed files. Original Work verbal results reported ≈46mV (0.5C) and 85–87mV (1C), plus a numerical refinement failure at 1C. **Do not fabricate Work artifacts, assume identical results, claim untouched evaluation, or declare the original 1C PASS.**

### New specifically labeled reconstruction

Run the **committed original Python implementation** `scripts/fit_e66_generator_b.py` unchanged, but using a verified copy of the *publisher's original* 152,124,241-byte `1-Cell Data.zip` from Borealis file ID 837532 (MD5 `734d8c3c262d7dcbd4eaf1b6b366e079`, DOI `10.5683/SP3/7JP3NM`). This was the subfile Work's source read inside its uploaded outer ZIP. Its source outer archive SHA256 (`d569bb98ec52ed6b0e151e3269154063dcc4b8a13ab05b30ac7bb3fa94cfd20b`) **is not presently reconstructable**, so never claim that SHA or byte-identity to its uploaded `doi-...zip`.

1. Download, independently verify published size+MD5 and compute SHA256; do not retain or distribute raw data.
2. Construct an ephemeral outer ZIP containing the EXACT publisher inner ZIP unchanged at `1-Cell Data.zip`; stream SHA256 of this newly assembled wrapper. This wrapper's hash will DIFFER from Work's original uploaded outer ZIP even though its inner original data hash is independently verified.
3. Copy `results/e66_calibration/PROSPECTIVE.json` **inside the temporary CI checkout only** and replace *only* `source_archive_SHA256` with the new wrapper SHA. Archive hashes of both original protocol and this new, explicitly post-hoc modified source-container reference. Original repository protocol must remain unchanged.
4. Under pinned PyBaMM `26.4.2` (Python 3.11; record complete dependent versions), execute original source `fit` using ONLY its two predesignated 25°C FIT cell records (C/20 and C/3), then execute original `evaluate` on its *already revealed* two 25°C EVAL recordings (0.5C, 1C). No unrelated cell temperature, module 2-file validation or 4-file blind data, and absolutely NO 1,152 historical Stage4 tests may be opened.
5. Save resulting `FIT_RESULT`, `GENERATOR_B_FREEZE` and `EVALUATION` under an artifact path that clearly labels them `POSTHOC_RECONSTRUCTED_AFTER_1C_RESULTS_KNOWN`, and **NEVER commit them to canonical `results/e66_calibration` as if Work generated them**. A freeze's internal `before_evaluation=True` records only the re-run's *within-run* procedural order; it is **NOT independent chronological evidence** of the original Work pre-result freeze.
6. Run only the registered 1C mesh×tolerance factorial on the RECONSTRUCTED fitted physical parameters. Test all four configurations A=20,1e-6/1e-7; B=40,same tolerance; C=20,1e-8/1e-9; D=40,tighter, for SPMe and DFN. Require baseline re-run to reproduce **the reconstructed** evaluation trajectory, full-horizon eligibility, source hashes and unchanged parameters. Any solver error, premature cutoff or missing receipt is FAIL/INCONCLUSIVE.
7. This is **POST-HOC DIAGNOSTIC ONLY**, with no genuine independent heldout evidence or physical validation beyond already revealed experimental records. Original negative 1C results and previous non-pass remain archived exactly as known. If this reconstruction suggests better fit, it still cannot retroactively change the original gate, and cannot license a complete Stage4B signoff.

Deliver provenance JSON with original source/protocol SHA, official inner ZIP SHA/MD5, recomposed wrapper SHA, recomputed fit/freeze/eval SHA and scientific comparisons, all in a temporary GitHub Actions artifact. Source input and large binaries must not be uploaded to artifacts or Git.

**Important numerical caveat:** Original `simulate(mesh)` switches rtol/atol simultaneously. The 2×2 factorial is explicitly retrospective and is meant to disambiguate these changes only. Physical model adjustments, if indicated, must be proposed as a new independently versioned model and tested on a prospectively locked previously unseen experimental record.

**COST LIMIT:** no paid service or cloud subscription; free GitHub Actions only, with capped run timeout and reporting even if blocked.
