# B2 development diagnosis — 2026-10-26

Status: NOT APPROVED. Development diagnostics only. No final blind files read.

Source: 20240314_1C_Test (MCCC).mat, SHA256 1b4484914764b7f819cab2e43639a770c2ee890488aa3e7142034f7bf3c2ad37.
The protocol was written before the three simulations. Existing frozen artifacts were not changed.

SPMe mesh40, first eligible 1800s charge window at recording time 21734s, initial SOC 0.0798311 inferred from precharge BMS voltage. Frozen electrochemistry and observation adapter.

| Effective capacity Ah | RMSE mV | Maximum mV | Coverage |
|---|---:|---:|---:|
|61.259778569358865|64.493|110.155|1|
|66|58.400|129.844|1|
|72|71.399|152.143|1|

All three fail the registered 50mV RMSE threshold. Capacity rescaling changes both SOC progression and normalized current/polarization, so it is not a pure SOC intervention. These runs do not identify capacity.

Additional exploratory checks on the same development session:
- Quiet interval 379–3981s: 3603 samples; last five BMS samples average 4.171667 V/cell.
- Quiet interval 16182–21738s: 5557 samples; last five average 3.151667 V/cell.
- Quiet interval 26468–27589s: 1122 samples; last five average 4.166667 V/cell.
- Trapezoidal AVL current integral, divided by two parallel cells: -55.919594 Ah from 3981 to 16182s; +55.683101 Ah from 21738 to 26468s.
- Frozen OCV at 30C gives 4.146254 V at SOC=1 and 2.422732 V at SOC=0. Inverting the 4.171667V endpoint with brentq on [0,1] failed because endpoints do not bracket it.

Interpretation: resting high-voltage endpoint is incompatible with the endpoint mapping used for initialization. This is not proof that OCV explains the entire MCCC residual: thermal state, residual relaxation and BMS acquisition bias remain possible contributions. Full charge/discharge capacities here are operational-window capacities, not independently measured total thermodynamic capacity.

Next discriminating work: extract relaxed development anchors and coulomb intervals across the development sessions; evaluate voltage/SOC mapping and measurement bias jointly, using an explicitly restricted model. Recheck cell-level regression and pulse response before freezing any replacement. Previously exposed validation sessions cannot become blind again. Final blind release requires a completed frozen pipeline and applicable registered protocol.

## Follow-up research and implementation

Extracted eight >=600s quiet intervals across all six development files; tail means use 60 seconds. Finite rest is not assumed to prove equilibrium. Seven BMS tails have zero observed range, so sub-quantization fitted slopes are not evidence of physical zero drift. The 1C postcharge tail still changes by 1.667mV/cell.

The first 1C high rest gives +25.412990mV relative to frozen OCV(1,T). Two prospective development-only probes apply this constant positive-electrode correction and re-invert initial SOC against the same precharge BMS voltage:

| Capacity Ah | Corrected RMSE mV | Max mV | Coverage |
|---|---:|---:|---:|
|61.259778569358865|71.543|125.935|1|
|66|57.009|120.782|1|

Neither passes. Thus endpoint matching alone does not resolve the sustained-charge residual. No replacement candidate is approved or released to final blind data.

Wolfram symbolic computation returned zero for `((a*z0+b)+q/(Q/a)-b)/a-(z0+q/Q)` under a>0,Q>0. If z'=a*z+b, Q'=Q/a and U'(z')=U((z'-b)/a), terminal equilibrium voltage is invariant. This is a restricted equilibrium-model identifiability argument, not a proof of nonidentifiability of the entire electrochemical model. Independent SOC boundaries or restricted OCV families are necessary before interpreting capacity estimates physically.

Acumen was consulted for E66/PyBaMM updates; it returned general EV industry facts, none directly useful for calibration. No such facts were incorporated into model parameters. Primary-source follow-up:
- https://battery.mcmaster.ca/research/datasets-and-algorithms/ identifies the E66 dataset.
- https://docs.pybamm.org/en/v26.4.1/_modules/pybamm/models/full_battery_models/lithium_ion/electrode_soh.html documents initial stoichiometry dependence on OCP and voltage limits.
Local PyBaMM version is 26.4.2; its installed initialization wrapper was inspected. No dependency upgrade was performed.

Five new extractor tests passed by direct function execution: duration boundary, short rest rejection, clock gap rejection, NaN split, and current threshold. `pytest` was unavailable; no full-suite pass is claimed. Source/result files and protocols are retained alongside the parent freezes.

Next: use existing cell GITT relaxed anchors to constrain a restricted nonlinear OCV map, while explicitly accounting for finite relaxation and cell-to-module measurement differences. Sparse module endpoints alone cannot identify a general OCV curve. The failed endpoint and capacity probes must remain in the research history.
