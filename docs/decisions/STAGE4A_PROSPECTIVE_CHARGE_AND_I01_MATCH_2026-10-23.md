# Stage4A candidate charge / I01 activity matching — prospective development addendum
Date: 2026-10-23. This method is fixed by the code commit **before** the dedicated calibration CI evaluation.

**This is a second, unsealed development calibration**, explicitly distinct from the historical sealed [0,120] kW search and from the earlier post-pilot charging search. It does not retroactively repair or re-label the historical preregistration. It is *not* a license to score the 2,232 official episodes or train Stage5.

## Calibration setup
- Physics: model_4a_activity_gated; observer not used during training-only H00 charge boundary search.
- Six-hour profile with five 12-min blocks/hour: drive, accelerate, regenerate, rest, charge; charge applied only parked, 5 s step, 4,320 steps.
- Nominal profile prospectively restricted to [40, 55] kW; shifted profile [24, 40] kW. These bounds were informed by previous **development** runs; DO NOT call their selection blind.
- Entirely new SHA256-derived calibration-specific physics and auxiliary seeds, checked for collisions against historical manifesto, Pilot1, Pilot2 and 12-case candidate smoke. Auxiliary waveform is a fixed 700+200sin(t/190) W deterministic common random profile (no stochastic auxiliary innovations); therefore this evaluates a single assumed nuisance trajectory, not robustness.
- Constant initial mean and branch SOC=60%; 30–80% **branch** SOC acceptance over the full trajectory; both endpoints must be valid and bracket the target final SOC.
- 8–12 midpoint bisections, finish with final mean SOC difference at most 0.5 pp and in-window trajectory. If endpoints or intermediate trajectories violate constraints, abort and do not silently move the brackets. Record **all** endpoint and midpoint traces.

## Revised M01/I01 matching
- Fault law: added motor copper loss `K*(motor_loss_fault_multiplier-1)*severity_M * torque²`, and added inverter loss `1600W * severity_I` **only when abs(torque)>0 and abs(rpm)>0** (traction or regeneration), with no extra I01 fault term in stationary rest/charge.
- Match by integrated **injected** loss over the frozen 6h profile, not by independently tuning observed class separability. Active-duty time is analytically 12,960s for the assumed profile.
- 2 profiles × 2 DIFF meanings × 3 M01 severities (0.25/0.5/1) = 12 prescribed entries. If I01 severity would exceed 1, label infeasible rather than clamping. Matched M01/I01 energy *does not* imply joint observational equivalence.
- For severity_M=1, verify with independent actual 6h H00, M01, I01 simulations per profile that direct incremental motor and inverter fault loss integrals match within 1e-5% relative. Source and seeds fixed before CI; no validation/test tuning.
- CI artifacts capture charge power, full bisection traces, mapping and full-horizon loss mismatch.

**Limitations:** No realistic charger current/voltage taper, no verified Taycan inverter off-state dissipation, thermal global first-law closure unresolved, one assumed nuisance waveform, no motor/inverter experimental data. Model B / external evidence remains Stage4B. The original run_stage4_experiments.py hash gate MUST NOT be bypassed. A versioned replacement frozen methodology and approval are required before any scored campaign.

Source: `scripts/calibrate_stage4a_activity_gated_dev.py`. Reproduction: `PYTHONPATH=src/simulator:src:. python scripts/calibrate_stage4a_activity_gated_dev.py --profile NOMINAL_6H`; repeat with SHIFT_REGEN_COLD_6H.
