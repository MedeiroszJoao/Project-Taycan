# Stage4B — runner interruption and unchanged mesh/Jacobian retry

**2026-10-24.** GitHub [Actions #40126799460](https://github.com/MedeiroszJoao/Project-Taycan/actions/runs/40126799460) completed the original source download/verification and prior *post-hoc reconstructed* freeze receipt recovery, then launched the prespecified extended mesh (20/40/80/160) plus fixed-absolute-step 3-parameter FIT Jacobian analysis. At approximately 19:49 UTC the runner logged: `The runner has received a shutdown signal` and `The operation was canceled`. No scientific diagnostic result JSON artifact survived. **State: INFRASTRUCTURE INTERRUPTED; neither experimental FAIL nor PASS.**

Scientific evidence that remains secure from the [earlier completed run #40126047070](https://github.com/MedeiroszJoao/Project-Taycan/actions/runs/40126047070):
- Independent Borealis cell ZIP publisher checksum PASS; prior Work fit source run unchanged, outputs explicitly `POSTHOC_RECONSTRUCTED_AFTER_1C_OUTCOMES_KNOWN`.
- Reconstructed 0.5C: SPMe RMSE 46.252mV, DFN 46.339mV — originally declared threshold PASS within the new reconstruction.
- Reconstructed 1C: SPMe RMSE 84.829mV, DFN 86.536mV — original predeclared 50mV threshold FAIL. Negative mean bias approximately −81.68mV and −83.67mV across full 1C record.
- Within reconstructed 1C, mesh 20→40 produced maximum voltage discrepancy 8.352/8.589mV; tolerance-only 20 mesh maximum 0.0085/0.0157mV (SPMe/DFN). All runs full horizon, 500 points, baseline reproduces reconstructed (NOT original Work) trajectory exactly.
- The optimizer reported numerical rank 2/3 with `effective_M50_contact_R_ohm` near its zero boundary, but **global structural non-identifiability is not established**; source numerical relative Jacobian `diff_step` could mask that contact derivative near zero.

**Retry decision:** one isolated rerun of failed job #120969866001, identical commit/protocol, no change to fitted physics or prespecified comparisons. Other heavy, repeatable historical workflows are converted to manual-only so documentation commits do not redundantly re-download TUM/E66. If the same runner shutdown recurs, report the failure and use *smaller independently specified* numerical batches (separate model and grid) **without changing any scientific thresholds or original 1C conclusion**. Do not declare success from an incomplete run.

Original Work source output freeze/fit/evaluation JSON remain irretrievable as original files; the artifact from #40126047070 is **a new explicitly post-hoc recreation**, even though its numerical outputs match Work's earlier verbal summary. No 1,152 protected historical Stage4 tests opened, no 4B overall approval and no legitimate Taycan E66 chemistry-identification claim.
