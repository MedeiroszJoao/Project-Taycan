# Stage4B: posthoc E66 mesh convergence and FIT Jacobian scale audit

Recorded **2026-10-24**, after observing the reconstructed source fit and the original negative 1C result. This is **RETROSPECTIVE CAUSAL DIAGNOSTIC**, not validation, refitting, approval, or redefinition of the original Stage4B frozen 1C numerical/empirical criteria.

The independent [POSTHOC reconstruction run #40126047070](https://github.com/MedeiroszJoao/Project-Taycan/actions/runs/40126047070) downloaded and verified Borealis `1-Cell Data.zip` (MD5 `734d8c3c262d7dcbd4eaf1b6b366e079`, 152,124,241 bytes), re-executed the historically committed **unchanged** `scripts/fit_e66_generator_b.py` on only original two FIT cell records (25°C C20 + C3), and then reproduced the original two already-viewed 0.5C and 1C evaluations. It generates **new post-hoc** receipts with source, fit and evaluation hash-chain PASS; it DOES NOT recover the original Work output or turn an already-viewed 1C evaluation into blind evidence.

Observed posthoc 1C: SPMe RMSE 0.0848291077V, DFN 0.0865355101V (both FAIL versus 0.05V); max bias -0.08168V and -0.08367V. 20→40 mesh change at fixed loose tolerance: maximum 8.3519mV / 8.5889mV; only solver tolerance change at fixed mesh20 0.0085mV / 0.0157mV. All 500 points overlap; full time horizon reached. **These results fix the next prospective diagnostic measurements but not the fitted physics.**

## Diagnostic 1 — extended convergence at fixed tight tolerances

- Read the already archived **post-hoc** freeze/eval/fit receipts and verify sha256 against previous POSTHOC_PROVENANCE and restored publisher archive SHA. Every physical parameter unchanged.
- Only already-exposed **1C cell** record; no other cell temperatures, E66 module validation files, blind module files or original 1,152 Stage4 reserved tests.
- Same PyBaMM 26.4.2, original Chen2020 effective model mapping; vary **spatial meshes 20, 40, 80 and 160**, holding IDAKLU **rtol=1e-8, atol=1e-9** constant. Both SPMe and DFN, 8 complete solves.
- Prespecified pairs: **20→40, 40→80, 80→160**, at 500 common output times, 1C full duration ≈3279.7s. Compute max absolute difference and RMS difference (volts), both horizon coverages, and *strict* numeric convergence PASS only if both complete full horizon, finite 500 points and max gap <=0.005V. If a model fails at mesh160, report the failure and do not infer convergence.
- Report per-solve experimental voltage error RMSE, bias, maximum error separately. These errors are retrospective on previously observed data, not new heldout evidence. Do not reclassify the original 1C FAIL even if meshes 40→80 or 80→160 converge.

## Diagnostic 2 — source optimizer Jacobian near zero contact resistance

- The post-hoc fit gave offset ~-0.040210V, OCP slope ~-0.039859V and effective contact R≈2.64e-16ohm (at positivity bound); its reported numerical Jacobian singular values are [17.3305, 2.58428, 0] and rank **2/3**.
- **Do NOT infer global structural nonidentifiability from that rank**: source `scipy.optimize.least_squares(...,diff_step=1e-3)` uses relative perturbation, which can collapse near a near-zero resistance parameter, so Jacobian=0 may be a finite-difference scaling/bound artifact.
- Independently compute forward differences on **only the original FIT curves** (C20, C3). Fix mesh=40, original frozen solver tolerance associated with 40, original model and initial state. For each of three physical parameters, perturb by an **absolute** step declared now: ΔOCP_offset=0.001V, ΔOCP_slope=0.001V, Δcontact_R=0.001ohm. Form stacked 300×3 voltage sensitivity matrix, report full singular spectrum/rank and nonzero finite-difference column norms. If rank becomes 3, the old rank2 did not demonstrate structural nonidentifiability; if rank remains 2, further independent parameter scaling/evidence is needed. Do not fit any parameters or claim electrode-geometry identification.
- Source physical limitations remain: Chen2020 LG M50 is a surrogate for Taycan LG E66, single cell unit, no independent thermal validation, no completed 4B external validation.

## Security, reproducibility, protection and status

- Download the public 152MB source file from the publisher again and verify MD5/SHA256; NEVER distribute the raw cell source in GitHub Actions artifacts.
- Retrieve only small **post-hoc reconstructed** receipts from prior CI artifact [12573407008](https://github.com/MedeiroszJoao/Project-Taycan/actions/runs/40126047070/artifacts/12573407008), NOT the original Work receipts. Exact contents + hash-chain checks are required; fail closed on mismatch.
- Write only aggregated numerical diagnostics with source hashes, no train/test leaking or new fit.
- Independent scientific conclusion remains **original E66 1C FAIL**; this analysis differentiates numerical discretization and optimizer derivative artifacts.
- Require no infrastructure purchase/paid service. Use separate branch, PR draft, keep original source `scripts/fit_e66_generator_b.py` and historical Stage3/4A/freeze unchanged.
