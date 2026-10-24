# E66 Stage 4B — evidence-verified recovery, 1C failure and numerical-causality boundary

**Date:** 2026-10-24. **Status:** retrospective scientific verification COMPLETE within available evidence; scientific Stage4B APPROVAL **NOT GRANTED**. Research-only. This is not the original Work result attestation or a real Taycan 4S pack calibration.

## Three different provenance levels — do not conflate

**A. Work-original historical frozen receipts — UNRECOVERED.** `FIT_RESULT.json`, `GENERATOR_B_FREEZE.json`, `EVALUATION.json` originally computed in Work are **not** on the available experimental GitHub branch, GitHub Actions artifacts or accessible Project/Library file index. Their pre-result chronology cannot be independently reconstructed from later reported metrics or new timestamps. The existing GitHub `results/e66_calibration/PROSPECTIVE.json` is authentic preregistered protocol/source, but by itself does not prove the contents of the missing Work model freeze.

**B. Verifiable new post-hoc reconstruction — PASS as reproduction, NOT historical original.** The separately registered [#40126047070](https://github.com/MedeiroszJoao/Project-Taycan/actions/runs/40126047070) retrieved the publisher's E66 cell ZIP, verified the independent **152,124,241-byte, MD5 `734d8c3c262d7dcbd4eaf1b6b366e079`, SHA256 `fc65efb69fe196952b430443b0e3c8df0ff789076f91ecebe3f8e10d86937e65`** source. It used the historically committed `scripts/fit_e66_generator_b.py` unchanged and only the two original FIT 25°C curves; the outer wrapper was newly created with a *different SHA256*. Because 1C results were already known, the new fit, its internal freeze, and evaluation are **retrospective**; they do not become blind or validate the original Work pre-result freeze. No new physical settings were chosen based on 1C within the reproduction.

**C. Independent archived 500-point evaluation checks — PASS on provenance/numeric consistency, FAIL on 1C scientific gate.** The new lightweight [#40128391055](https://github.com/MedeiroszJoao/Project-Taycan/actions/runs/40128391055), artifact `stage4b-posthoc-trace-rmse-integrity-not-original-work`, downloaded only previously archived small *posthoc* receipts, not the raw cell ZIP. `scripts/audit_e66_frozen_receipts.py` recomputed RMSE, bias, maximum abs error, and coverage using **all 500 archived voltage observations per experiment/model**, and independently confirmed source, temporary prereg, fit, freeze and evaluation hashes. **All four stored trajectory statistics recompute exactly within declared 1e-8 numerical tolerances**; `receipt_integrity=PASS`, `gate_counts={PASS:2,FAIL:2}`, `all_eval_pass=false`, `independent_chronology_proven=false`. Five adversarial tests newly confirm that corrupted error metrics, missing traces, false coverage and nonmonotone timestamps fail closed; full E66-specific [#40127919098](https://github.com/MedeiroszJoao/Project-Taycan/actions/runs/40127919098) **17/17 PASS**. Generic Stage 3/4 CI [#40127919103](https://github.com/MedeiroszJoao/Project-Taycan/actions/runs/40127919103): 131 tests, **124 PASS + 7 intentional skips** for scientific dependencies absent from stdlib jobs.

## Quantitative POST-HOC empirical 25°C terminal-voltage comparison (same ONE cell)

| Exposed protocol | SPMe RMSE (mV) | DFN RMSE (mV) | RMSE threshold | Original prospectively declared outcome applied to new replay |
|---|---:|---:|---:|---|
| 0.5C | **46.2521** | **46.3387** | ≤50 mV | Both empirical + original coupled-numeric PASS |
| 1C | **84.8291** | **86.5355** | ≤50 mV | Both empirical + original coupled-numeric FAIL |

At 1C, signed bias is **−81.6774 mV SPMe**, **−83.6747 mV DFN**. Max absolute errors are **155.0535 and 151.8999 mV**, both exceeding the original **150mV** maximum threshold. These negative signed biases account for most of the total RMSE but **do not identify a unique physical error mechanism**. Both solvers reached 100% of the 1C evaluation time, so this failure cannot be attributed merely to early termination.

## Retrospective causal NUMERICAL disaggregation: what the data prove

The original `simulate(mesh=20)` uses IDAKLU rtol/atol `1e-6/1e-7`; changing to mesh40 simultaneously tightened to `1e-8/1e-9`, confounding mesh with tolerance. The fixed-parameter factorial [#40126047070](https://github.com/MedeiroszJoao/Project-Taycan/actions/runs/40126047070) separated the two factors on **the already observed 1C record**, with complete common horizons and zero parameter optimization.

| 1C case | SPMe error RMS (mV) | DFN error RMS (mV) |
|---|---:|---:|
| A — mesh20, loose IDAKLU | 84.8291 | 86.5355 |
| B — mesh40, SAME loose IDAKLU | **85.1132** | **87.0468** |
| C — mesh20, tight IDAKLU only | 84.8303 | 86.5399 |
| D — mesh40 + tight IDAKLU | 85.1113 | 87.0517 |

- Maximum pointwise A→B (mesh alone) voltage gap: **8.3519mV SPMe, 8.5889mV DFN**, above the preregistered 5mV *numerical consistency* tolerance. Its RMS over the 500 points is **0.6421mV and 0.7626mV**, respectively.
- Maximum pointwise A→C (solver tolerance alone): **0.00850mV SPMe, 0.0157mV DFN**, orders of magnitude smaller. **On these tested meshes**, spatial discretization explains nearly all the 5mV refinement inconsistency; this does **not prove full mesh convergence**.
- With fixed experimental reference, the reverse triangle inequality yields an exact model-agnostic lower bound on mesh40 prediction RMSE: `RMSE_B ≥ RMSE_A − RMS(V_B−V_A)`. Thus `RMSE_B ≥ 84.1870mV SPMe` and `≥85.7729mV DFN`, both still decisively above 50mV. Direct numerical RMSE_B confirms the failure. This shows correcting the **specific observed mesh20→40 difference alone** cannot rescue accuracy; it is not a theorem about all possible finer meshes or alternative physics.

**Extended mesh 20/40/80/160 and absolute-difference FIT Jacobian:** NOT COMPLETED. Attempts [#40126799460](https://github.com/MedeiroszJoao/Project-Taycan/actions/runs/40126799460), [#40127753939](https://github.com/MedeiroszJoao/Project-Taycan/actions/runs/40127753939) and [#40127706137](https://github.com/MedeiroszJoao/Project-Taycan/actions/runs/40127706137) were interrupted by GitHub runner shutdown while executing the combined diagnostic, despite successfully rechecking the source and receipts. **No trustworthy completed 80→160 gap, convergence or independent Jacobian rank can be claimed**. The original optimizer's reported rank 2/3 and zero-like fitted contact resistance may be a *relative finite-difference step / bound artifact*; no structural non-identifiability theorem may be asserted without the separate absolute-step test. A revised checkpointed small-batch research plan is registered at `docs/decisions/STAGE4B_E66_MESH_BATCH_AMENDMENT_2026-10-24.md`, but batch execution is **not yet evidenced** and not necessary to preserve the already-proven 1C scientific FAIL.

## Scientific gates and program safety

- **PASS:** real publisher-source MD5/SHA; re-running original code transparently as new posthoc reproduction; source/receipt hash chain and recomputed 4×500-point numerical metrics; two 0.5C outcomes; isolation of observed solver-tolerance vs mesh20→40 effects; CI regression suites.
- **FAIL:** one-cell 1C terminal-voltage accuracy under both SPMe/DFN and numerical mesh20→40 consistency under preregistered 5mV threshold. Both negative results preserved.
- **BLOCKED:** original Work freeze provenance; full 80→160 convergence + absolute-step Jacobian due CI runner shutdown; accepted physically anchored E66 chemistry/geometry and global 4B signoff.
- **NOT ATTEMPTED:** claim of real 4S pack prediction or actual diagnostic class accuracy, module blind/validation outcome unseal, Stage4 official 2232-episode campaign, Stage5 training.

**Research decision:** retain the failed candidate and its original scientific gate. If additional computing can be allocated, split model/mesh/Jacobian analysis into independently checkpointed no-cost jobs with identical frozen parameters. Future model improvements must be versioned as a **new prospective hypothesis** evaluated against a genuinely still-sealed external protocol, and must not relabel the 1C observed data as new holdout.

No merge to main, no paid compute, no new source physics changes or protected historical validation/test access.
