# Stage 4B — prospective TUM real-CAN energy-accounting diagnostic, research-only

**Registered 2026-10-24 before this specific quantitative energy analysis.** Source: TUM Rosenberger/Lienkamp CC BY 4.0, `10.14459/2025mp1774217.001`, 92 recordings, one BASE RWD 93.4 kWh; target 4S AWD 79.2 kWh. The earlier all-92 coverage audit was already inspected; this is a *subsequent exploration*, NOT untouched confirmatory validation.

## Sample selection and estimands

Select precisely **12 recordings** by SHA-256 ascending hash of the provider's relative CSV path from the public 92-entry archive manifest. This policy is determined before looking at numeric outcomes of selected files; published sampling frame had been observed. Sample is **one vehicle**, not 12 independent vehicles.

Evaluate **only directly measurable shared physical identities and consistency**, no class labels, no fault detection or model-A calibration. Read-only source rsync, SHA256 each CSV; immediately delete raw files after processing. Preserve only per-recording summary and reproducibility.

1. (P_e(t)=V(t)I(t)), under both signed conventions until external evidence confirms current orientation. For consecutive valid adjacent samples, integrate (E_e=\sum [V_i I_i+V_{i+1}I_{i+1}] \Delta t/(2\cdot3.6\times10^6)) in kWh, (Q=\sum (I_i+I_{i+1})\Delta t/(2\cdot3600)) in Ah.
2. (P_m(t)=\tau(t)\cdot 2\pi\cdot\mathrm{rpm}(t)/60) W; report signed integrated mechanical energy, **do not equate single CAN motor signal to all-drive-motor traction output** and do not assume front and rear motor same.
3. Use only nonmissing/finite pairs and strictly increasing `time`, maximum allowed gap **1.0s**; report rejected pair counts by reason. Report nonfinite, SOC outside [0,100], non-positive voltage and implausible `V>1500` separate from missingness (do not silently clip).
4. For SOC observation, use 600-second disjoint windows (anchored at local t=0), with at least 80% valid current pair-time coverage and at least **1.0 percentage point** absolute observed SOC change. Report windows' signed coulombs and observed SOC change. Do not fit nominal cell or pack capacity to hidden simulator truth. A per-window `effective_Ah_abs = 100*abs(Q_Ah)/abs(delta_soc_pp)` is purely diagnostic and subject to SOC display quantization and currents' sign convention. Report both `corr(I-integral,∆SOC)` and anti-correlation; do not select sign to maximize apparent fit.
5. Preserve missingness structure and sample counts, no imputation. **Neither 10Hz rows nor windows within a session are independent physical-vehicle replicates**; no fine-grained p-value claims. Descriptive cross-session summaries are clustered at recording ID and remain same-car context.
6. Declare any motor-electric conversion efficiency comparison ineligible unless CAN definitions, motor count and load paths are independently established. Compare *dimensions* and sign physically but do not calculate an apparent "efficiency" from incompatible signals.
7. Results only **B4 external telemetry consistency**; independent PyBaMM B freeze remains required separately. No Stage4 frozen train/validation/test rows accessed.

Gates: valid CSVs and source hashes; report all 12 including failures; repeatable selection and numeric results; units as documented or provisional. Fail gracefully (explicit missingness), never patch bad data silently. Zero protected test access. Files `scripts/stage4b_tum_energy_probe.py` and generated `results/tmp/stage4b/tum_12_energy_probe.json` in CI artifact, not raw CSVs.

**Important:** physical pack capacity inferred using `93.4kWh / 723V ≈129.18Ah` is a **rough dimensional comparison only**: the published energy could be gross vs usable, pack voltage varies with SOC, and SOC CAN may be display-scaled. No exact capacity equality acceptance gate.
