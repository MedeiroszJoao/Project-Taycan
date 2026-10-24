# Stage4B TUM BMS SOC quantization sensitivity — POST-HOC adversarial

Date: 2026-10-24. This analysis was initiated **AFTER** seeing the TUM 12-recording result (84 of 84 eligible windows had concordant current-integral/SOC trend; 12 session-median effective capacities 95.99–131.66 Ah). It is a **retrospective robustness analysis**, not prespecified confirmatory science.

Even if all observed `hv_soc` values appear integer, the actual CAN internal scaling or update rules are not yet independently established. Test a hypothetical worst-case **1.0 percentage-point nearest-integer SOC quantization**, under which an observed endpoint has error within ±0.5pp and a two-endpoint difference has an uncertainty of ±1.0pp.

For any integrated signed coulombs `Q_Ah` and measured magnitude `d=abs(ΔSOC_pp)`, naive effective capacity `100*abs(Q_Ah)/d`. With ±1pp uncertainty in the reported SOC difference, a conditional, **not probabilistic confidence interval** for capacity is:
- lower = `100*abs(Q_Ah)/(d+1)`
- upper = `100*abs(Q_Ah)/(d-1)` when d>1; else unbounded.
These bounds are conditional on the simple quantization-error model and on *exact* integrated current. They do not account for BMS SOC filtering, sample delay, integrator drift or genuine usable-vs-gross SOC definitions.

Run over the existing 12-session JSON **without downloading 427 MB CAN again**. Report how many eligible windows have unbounded upper capacity, and conservative multiplicative sensitivity by |∆SOC|. Include per-recording medians only as descriptive dependent observations. Never claim 84 independent samples or Taycan pack capacity identification. The sign concordance itself may be algorithmically coupled if BMS SOC is current-integrated. Study changes in battery voltage/current physically using independent channels before external calibration.

Input: archived `stage4b-tum12-external-energy-report` from GitHub Actions #40074088298. Output: quantization sensitivity report, with input SHA256 and script hash, no raw telemetry. 
