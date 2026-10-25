# Reproduction without relying on expiring CI artifacts

The input_receipts directory contains the exact post-hoc FIT_RESULT and historical PROSPECTIVE consumed by this campaign, plus its reconstruction provenance. These are not restored pre-exposure originals. No raw measured trajectories are included.

Install the exact versions in GENERATOR_B_FREEZE.json. Place the licensed original DOI ZIP at `../project_sources/09-doi-10.5683-sp3-7jp3nm.zip` relative to this repository; its SHA256 must equal the freeze. The historical PROSPECTIVE has an older wrapper hash; the current runner verifies the actual attached source archive against its own freeze.

Restore the expected receipt paths:

```bash
mkdir -p results/tmp/e66_causal/receipts/e66_calibration
cp results/e66_kinetic_calibration/input_receipts/FIT_RESULT.json results/tmp/e66_causal/receipts/e66_calibration/FIT_RESULT.json
cp results/e66_kinetic_calibration/input_receipts/PROSPECTIVE.json results/tmp/e66_causal/receipts/e66_calibration/PROSPECTIVE.json
```

Re-run evaluation in a disposable checkout: remove only `results/e66_kinetic_calibration/job_*.json` in that disposable checkout to avoid reusing the checkpoints, then run:

```bash
python scripts/calibrate_e66_kinetics.py evaluate
python scripts/check_e66_fit_regression.py
python scripts/stress_e66_frozen_kinetics.py
python scripts/check_e66_lithium_inventory.py
python scripts/audit_e66_kinetic_results.py
PYTHONPATH=src/simulator:src:. python -m unittest discover -s tests/unit -v
```

Do not overwrite the published freeze or retune after seeing evaluation failures. To replicate optimization, use another disposable copy containing the protocol but no fit/freeze/job outputs. The runner records a new receipt. Bitwise solver trajectories may vary across platforms; hashes protect configuration, not a promise of cross-platform floating-point identity.

F14/F28 from the vehicle protocol cannot be externally validated by synthesizing electrical counters from the same laboratory current/voltage. That would create an algebraic control, not an independent acquisition test. They remain outside this cell campaign.
