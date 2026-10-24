# Stage 4B E66 — amendment: isolated numerical batches after runner shutdown

2026-10-24. **Retrospective; no changes to any historical validation threshold, physical parameter or fitting set.** GitHub Actions attempts [40126799460](https://github.com/MedeiroszJoao/Project-Taycan/actions/runs/40126799460) and [40127753939](https://github.com/MedeiroszJoao/Project-Taycan/actions/runs/40127753939) were interrupted by runner shutdown during the multi-solve mesh/Jacobian job, without a completed diagnostic artifact. These are infrastructure limitations, NOT scientific evidence of pass/fail.

The independently authenticated **posthoc** reconstruction [40126047070](https://github.com/MedeiroszJoao/Project-Taycan/actions/runs/40126047070) already established the first two mesh points and solver-tolerance-only effects, reproducibly on one previously observed LG E66 1C record. It is NOT the absent original Work freeze.

To prevent loss of all results when the runner shuts down, partition the already-fixed numerical experiments into independent jobs, each with its own output file:
- `SPMe_80`: meshes **20,40,80**, each at IDAKLU rtol 1e-8 and atol 1e-9; require all three full 1C time domains, compare 20→40 and 40→80, plus per-mesh RMSE vs already inspected 1C experimental voltage.
- `DFN_80`: identical procedure on DFN.
- `JAC`: for **both original FIT curves only**, evaluate absolute finite-difference Jacobian (delta 0.001 V offset, 0.001 V slope, 0.001 ohm contact), compute singular values/numerical rank; no fit, no evaluation output used to tune parameters.
- Mesh **160** remains a recorded component of the earlier [2026-10-24 mesh protocol](STAGE4B_E66_POSTHOC_MESH_JACOBIAN_2026-10-24.md), to be handled *separately* only if supported by environment. **Do not imply that 80-point results establish 80→160 convergence.**

Every batch must independently verify (1) publisher LG E66 cell ZIP 152,124,241 bytes and MD5 `734d8c3c262d7dcbd4eaf1b6b366e079`, (2) sha256 of new deterministic wrapper, (3) all four original **POSTHOC** receipts as archived from run 40126047070, (4) source code SHA. The **original Work receipts remain unavailable and cannot be replaced**.

Write output incrementally after every solve, with partial-progress metadata. If runner dies, report missing cases; never count a partial batch as complete. Job artifacts contain only summary JSON, not original source data, and must never be named `GENERATOR_B_FREEZE.json`.

The original 1C criterion remains FAIL (SPMe RMSE 84.829mV; DFN 86.536mV). Additional discretization convergence cannot overturn the original empirical failure. No protected historical Stage4 tests or virgin E66 module validation/blind files.
