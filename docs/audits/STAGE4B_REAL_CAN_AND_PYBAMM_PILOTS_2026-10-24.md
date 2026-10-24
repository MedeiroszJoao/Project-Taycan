# Stage 4B — executed external CAN energy probe and independent-cell solver audit

**Date:** 2026-10-24. **Verdict:** two new quantitative research exercises completed, **no overall Stage4B approval**. No original 4A model, original Stage3, manifest or reserved test outcomes modified/accessed.

## A. All-92 REAL TUM CAN recording inventory and measurement QC

TUM dataset Rosenberger/Lienkamp, `10.14459/2025mp1774217.001`, CC BY 4.0. This is **base Porsche Taycan RWD 93.4 kWh**; target Project Taycan is **Taycan 4S AWD 79.2 kWh**. [92-session run #40072082604](https://github.com/MedeiroszJoao/Project-Taycan/actions/runs/40072082604) actually downloaded and audited all 92 public individual CSV recordings from official mediaTUM rsync (no user ZIP reupload necessary). 4,661,270 sample rows spanning 466,117.8 cumulative seconds, zero failures. Current HV 99.9997% row coverage, SOC 99.5787%, voltage HV 72.2174%, motor torque 99.4110%, average battery temp 22.1784%; gearbox speed 0%. This is one vehicle, **not 92 independent vehicle units**. No external fault labels.

## B. Prespecified 12-recording real current/SOC/power probe

[Run #40074088298](https://github.com/MedeiroszJoao/Project-Taycan/actions/runs/40074088298); [prospective protocol](../decisions/STAGE4B_TUM_ENERGY_PROBE_PROSPECTIVE_2026-10-24.md). 12 recordings selected by ascending SHA256(relative provider CSV path) before inspecting their *numeric* results. All 12 parsed, 0 errors, 615,460 time rows, 10 recordings with simultaneously usable V/I pairs. 84 nonoverlapping 10-minute windows met a precommitted rule: >=80% valid current-time coverage and >=1 percentage-point endpoint SOC change. **84/84** showed SOC change concordant in sign with the signed integrated current, implying positive current is charging at CAN level in those windows. This is conditional on the observed BMS representation, not laboratory validation of energy chemistry.

The **12 per-recording medians** of naive Coulomb-counting-effective-capacity diagnostics span **95.986–131.656 Ah**, median between recordings **114.9985 Ah**. These ARE NOT physical cell/pack usable capacity estimates because SOC display may be quantized, algorithmically current-integrated, delayed, filtered, and one vehicle generated all recordings. The 93.4kWh is energy, Ah conversion also needs a justified voltage basis. Do not fit A or B to these Ah values. A single CAN motor's torque/RPM mechanical power is not whole-vehicle powertrain efficiency.

An explicit POST-HOC adversarial quantization analysis used the **existing archived small JSON only**, no repeat of original 427MB dataset: [run #40074689527](https://github.com/MedeiroszJoao/Project-Taycan/actions/runs/40074689527), [methodology](../decisions/STAGE4B_TUM_SOC_QUANTIZATION_RETROSPECTIVE_2026-10-24.md). If each SOC endpoint might be quantized ±0.5pp, the observed ∆SOC is uncertain by ±1pp. For observed d=abs(∆SOC)>1pp and measured Q, conditional capacity lower bound =100|Q|/(d+1), upper=100|Q|/(d−1); for d≤1 the upper bound is infinite. **12/84** eligible windows fall into that unbounded-upper class. This is a hypothetical worst-case range, NOT a CI, and actual CAN SOC resolution remains to be verified independently. The 84 windows may not provide independent information because BMS SOC may itself be estimated partly by integrating CAN current.

### What this does and does not establish

- **PASS:** public TUM data accessible; file provenance and hashes; CAN format and missingness; coherent current/SOC sign and energy dimensional processing; non-identifiability of exact capacity from short/quantized SOC windows.
- **INCONCLUSIVE:** actual usable pack capacity and physical powertrain efficiency; chemical energy first-law closure; external predictive accuracy of simulator A.
- **NOT DONE:** real diagnostic performance for B01–I01, and full target Taycan 4S validation.

## C. Independent physical battery cell generator B (PyBaMM)

[Precommitted solver-only protocol](../decisions/STAGE4B_PYBAMM_SOLVER_QUALIFICATION_2026-10-24.md). [Run #40074225160](https://github.com/MedeiroszJoao/Project-Taycan/actions/runs/40074225160): PyBaMM **26.4.2**, Python 3.11, electrochemical **SPMe and DFN**, `Chen2020` parameter set intended for **LG M50** (not Taycan LG E66), `thermal=lumped`, IDAKLU, initial SOC 0.6, 20-min 0.5C discharge / 10-min rest / 20-min 0.2C charge. **Both models PASS**, 3,000s full protocol. SPMe Vmin=3.577950V, Vmax=3.813057V, Tmax=301.00982K. DFN Vmin=3.578337V, Vmax=3.812462V, Tmax=300.974385K. Deterministic independent SPMe rerun exactly matched stored source trajectory SHA256.

Prospectively registered **18-solve rate×temperature model-form test** [run #40074502464](https://github.com/MedeiroszJoao/Project-Taycan/actions/runs/40074502464), [protocol](../decisions/STAGE4B_PYBAMM_SENSITIVITY_PREREG_2026-10-24.md): model {SPMe,DFN}, discharge {0.25C,0.5C,1C}, initial+ambient {288.15K,298.15K,308.15K}, 20-minute discharge, 10-minute rest, 20-minute 0.2C charge. **18/18 complete, no errors**, nine matched pairs. Paired voltage RMS differences (in millivolts):

| Temp \ Rate | 0.25C | 0.5C | 1.0C |
|---|---:|---:|---:|
| 15°C | 0.383 | 0.622 | 1.774 |
| 25°C | 0.455 | 0.731 | 1.935 |
| 35°C | 0.590 | 0.934 | 2.309 |

Maximum instantaneous paired voltage discrepancy 5.3477mV; maximum instantaneous paired temperature discrepancy 0.1813K. Differences increase in this test grid with rate and temperature. This characterizes **same-parameter model-form sensitivity**, not an error against a real cell; SPMe and DFN are not separately empirically calibrated and are not independent validations of one another. The independent relationship of B is to the custom 1RC simulator **A**.

### Generator B gates

- **PASS**: third-party electrochemical physical-cell solver genuinely executes with pinned PyBaMM version, deterministic inputs, documented independent code, provenance, SPMe/DFN convergence through all requested profiles.
- **OPEN**: correct LG E66/Taycan cell parameter provenance; public cell experimental fit/holdout splits; prospectively signed **`GENERATOR_B_FREEZE`**; physically shared observation-channel mapping, independent battery-vs-vehicle data reconciliation, quantitative A×B transfer comparisons and OOD.
- **OUT OF SCOPE FOR CELL-ONLY B**: full motor/inverter/isolation B09/M01/I01 claims. SPMe/DFN not a complete Taycan OBD system.

## Engineering handoff

PR [#2](https://github.com/MedeiroszJoao/Project-Taycan/pull/2) remains draft. Independent source files:
`scripts/stage4b_tum_energy_probe.py`;
`scripts/stage4b_soc_quantization_adversarial.py`;
`scripts/run_stage4b_pybamm_independent_cell.py`;
`scripts/run_stage4b_pybamm_sensitivity_grid.py`;
`scripts/audit_stage4b_tum_can_full.py`.
Source logs and JSON artifacts are linked in the four runs. All narrow research actions are now **workflow_dispatch/manual-only** to avoid redundant expensive downloads/installations every time the PR changes.

**Scientific verdict:** Stage4B advanced materially in independent modeling and exposure of data observability and inferential limitations; external diagnostic accuracy remains entirely unproven. Do not authorize Stage5 or the original reserved 1,152 tests from these results. 
