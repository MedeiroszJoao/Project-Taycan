# Stage4B LG E66 MATLAB MCOS decoder — prospective library amendment

Date 2026-10-24. `mat-io==0.4.0` run [40075795890](https://github.com/MedeiroszJoao/Project-Taycan/actions/runs/40075795890) failed to decode an actual MATLAB MCOS table: `ValueError: no field of name _Class`; no numeric output was accepted. All blind and validation files remain unaccessed numerically.

**Before any re-run**, change only independent Python reader version to **`mat-io==1.0.1`**, released 2026-10-10 with Python 3.11 Linux wheel, source PyPI JSON https://pypi.org/pypi/mat-io/json. Hold constant: same source ZIP hash/MD5, single preregistered 1C development MCCC file, data interpretation, metrics and acceptance criteria. This is a documented post-failure package *compatibility probe* only, not a claim of independent research replication or preregistered version comparison.

If the newer reader also fails, stop with fail-closed receipt. Do not infer numeric results from serialized opaque reference tokens, invent data or access validation / blind files to troubleshoot.
