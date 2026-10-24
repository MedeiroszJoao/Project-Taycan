# Taycan Stage 4 — Adversarial Energy and Six-Hour Duty-Cycle Candidate Audit

**Date:** 2026-10-23. **Status:** `EXPLORATORY / UNAPPROVED / NO OFFICIAL EPISODES SCORED`.

## Provenance and immutable source

- Frozen approved original: `src/simulator/taycan_sim/model.py`, SHA-256 `af4e576cf824d30ee6aa9b2fd1f2c18d576fd269027df67c43c5e7647266ff4e` — **not changed**.
- Prior experimental bidirectional candidate: SHA-256 `9dbc84f67bbf02b32068cb915bd15efbe7298959d420c38bf14d92c7a5e696b0` — **not changed**.
- Newly proposed strict-energy candidate: `src/simulator/candidate_sim/model_energy_consistent.py`, SHA-256 `d4e399755aee9fe9c1b3e2dc3de16a3a48361ebc12270c3f4db3801003c7e4db`.
- Stage 4 original `freeze.json` SHA-256 `5822c3e43e6f4634c7ca60d0aabb6f38afe5cecece99883833ee1c4d12dc5df8` — **not changed**.
- Historical original `observation_layer.py`: still **not byte-verified in this workspace**. The prior observation candidate remains a substitute, not historical original.
- All tests: **70/70 passed locally**, including the original tests, 14 energy/duty tests and 4 analytic matching tests (10 exact-RC and SOC boundary tests plus 4 duty-profile/charge-mode tests). Test names are retained in source.

## Mathematical derivation: RC work is not synonymous with resistive heat

The Thevenin branch in the model follows `dV_p/dt = -(V_p - I R1)/tau` with `tau = R1*C1`; discharge current is positive. Over one step `[0, h]`, assuming constant branch current `I`, `R1`, and `C1`, define `b=I*R1`, `a=V0-b`:

```
V_p(t) = b + a * exp(-t/tau)
V1 = b + a*exp(-h/tau)
E_cap = (C1/2) * V_p**2
Q_R1 = (b**2*h + 2*b*a*tau*(1-exp(-h/tau))
            + a**2*(tau/2)*(1-exp(-2*h/tau))) / R1
W_in = I * (b*h + a*tau*(1-exp(-h/tau)))
W_in = Q_R1 + (E_cap_end-E_cap_start)
```

The old code adds `I * V_p(end)` to module *heat rate*, which is **neither** the exact average `I*V_p(t)` nor the irreversible heat `V_p(t)**2/R1`. The new candidate uses `Q_R1/h` for heat, logs capacitor storage and input work separately, and checks the per-step identity.

**Falsification example:** at `V0=0.15 V`, `I=0 A`, `R1=0.00025 Ω`, `tau=75 s`, `h=5 s`, the exact resistor dissipation is **421.290048 J**, supplied by a **-421.290048 J** capacitor-energy decrease, despite **zero** input electrical work. An `I*V_p` heat model predicts zero thermal dissipation here and is incorrect.

2,500 signed randomized analytic tests passed; the 900-second 168s2p model probes gave maximum absolute step-wise RC identity residuals around `1e-12 J` at dt 1/2.5/5/10 s. This is **internal numerical consistency**, not whole-cell measured thermal validity.

**Known limitations:** Constant current and coefficients inside each step; no correction for capacitor constitutive energy when `R1/C1` vary *between* steps, no entropic/reversible heat, no dynamic current sharing within a timestep, no module heat-flow calibration. The DC power balance checks only algebraic closure, not total electrochemical energy conservation.

## Physical SOC policy

The prior simulator silently used `SOC=max(0.001,min(0.999,SOC_trial))`; the new candidate fails closed if any branch update, including B04 leakage, would exit physical `[0,1]`. This is an **admissibility guard, not a charge-control implementation**. It must not be confused with realistic current/voltage/taper limits or thermal derating. A 180 kW charging stress with initial SOC 98.5% raised `SOC_BOUNDARY_VIOLATION step=0 group=147 branch=1 mechanism=terminal proposed_SOC=1.00033475596 current_A=-174.831859`. It is not a Porsche charging threshold.

## Explicit temporal interface and operating-state rule

New experimental inputs `rpm_trace_rpm`, `torque_trace_nm`, `external_charge_trace_W` permit 4320×5s, six-hour simulations. The external charge trace is **valid only with rpm=0 and torque=0**; contradictory driving/charging commands raise `CHARGE_MODE_CONFLICT`. The schedule is five repeated 12-minute blocks per hour, six times: `cruise`, `acceleration`, `regeneration`, `rest`, `charge`. The 12-minute blocks match the preregistration *lengths*, but **the numeric 42/82/-50 Nm duty waveforms and RPM profiles were assumed after preregistration** — not an official frozen input. Over six hours there are exactly six of each block (72 minutes of each mode).

## Six-hour DEVELOPMENT-ONLY H00 root searches

Initial **configured** SOC 60%, seed 505, fixed non-noisy synthetic H00; **no validation/test episodes**. Eight binary iterations per profile, using narrow brackets chosen **after earlier exploratory pilot results**, so **not the sealed 0–120 kW bisection** and **not an official calibration receipt**. Battery-side DC power is delivered during charge blocks only (1.2 h total).

| Metric | NOMINAL_6H | SHIFT_REGEN_COLD_6H |
|---|---:|---:|
| Development-only selected charge power (kW) | 47.8046875 | 31.5625000 |
| Configured initial SOC (%) | 60 | 60 |
| Final mean hidden SOC (%) | 60.001978 | 60.044270 |
| Final SOC residual (percentage points) | 0.001978 | 0.044270 |
| Trajectory min/max mean SOC (%) | 45.1477 / 60.0344 | 47.2653 / 60.0443 |
| Trajectory min/max branch SOC (%) | 43.9681 / 61.7782 | 46.0872 / 61.7873 |
| Integrated ideal external DC energy (kWh) | 57.36563 | 37.87500 |
| Max per-step RC identity residual (J) | 1.408e-12 | 8.811e-13 |
| Max DC power algebra residual (W) | 5.093e-11 | 4.002e-11 |

A previous 6h fixed-DC-power pilot must **not** be compared at face value to this schedule: 6 hours of charging versus 1.2 hours differ by factor five in duration. No target-real-world claim is made about these power levels.

## Protocol incompatibility / mandatory formal decision

The sealed registration requires bisection in **[0, 120] kW** on H00, including checking feasibility and complete SOC history. Under physically strict state bounds the endpoints can fail (undercharge/overcharge). The present exploratory search narrowed the brackets after inspecting pilot outputs; it cannot replace the original sealed calibration without a **prospective, explicitly authorized amendment**. The original Stage 4 runner's source-hash gate must **not** be bypassed. Publish a new registered candidate hash, numeric waveform, SOC boundary policy, charge-profile support, operational modes, consistent noise parameters, calibration procedure, and independent M01/I01 matched-energy method **before scored episodes**. Keep original manifest and holdout partitions immutable; do not fit Stage 5 models.

## External validation evidence is still limited

TUM 92/92 files passed source SHA-512 verification previously, but published Taycan vehicle is RWD/93.4 kWh, not target AWD/79.2 kWh. Borealis first-party dataset description calls the 12-cell module `6p2s`, while the original instrumentation PDF audit calls it `6s2p`; resolve this notation conflict from electrical wiring before claiming any module-level topology. No external root-mean-square voltage or thermal error was estimated in this run. Historical observation layer recovery described by Claude remains unconfirmed here because the original ZIP bytes were not accessible.

## Literature / primary references

- Bernardi, Pawlikowski & Newman, *A General Energy Balance for Battery Systems*, J. Electrochem. Soc. (1985): https://doi.org/10.1149/1.2113792
- Thevenin 0.2 documentation (Thevenin ECM state equations): https://thevenin.readthedocs.io/stable/user_guide/model_description.html
- Published Borealis cell/module data: https://borealisdata.ca/dataset.xhtml?persistentId=doi:10.5683/SP3/7JP3NM
- TUM external dataset: https://doi.org/10.14459/2025mp1774217.001

## Subsequent developmental M01-to-I01 energy mapping (not official)

The assumed candidate injection equations are exceptionally simple: additional M01 motor copper loss is ΔP_M = `k_copper * torque(t)^2 * (fault_multiplier-1) * severity_M`, whereas extra I01 inverter loss is ΔP_I = `1600 W * severity_I` throughout the six-hour episode. Therefore,

```
severity_I = severity_M * k_copper * (fault_multiplier-1)
             * sum(torque_t**2*dt) / (1600*sum(dt))
```

This is an algebraic identity for the **assumed injection functions**; it does not establish physical equivalence of fault mechanisms, thermal pathways, terminal current trajectories or measured signatures. DIFF-motor-temperature measurement mode has no effect on the physical injection functions, therefore both DIFF mappings receive the same energy match in each profile.

For `k_copper=.033 W/Nm²`, inverter extra loss at severity one `1600 W` and the assumed torque waveform, ratios of inverter severity to motor severity are **0.059297892** (nominal) and **0.063862109** (shifted). The resulting **12/12** predescribed grid combinations are analytically MATCHED (two profiles × two DIFF modes × three motor-severity values), with severities within `[0,1]`.

Independent 6-hour simulation cross-check, using only synthetic H00/M01/I01 inputs (no held-out data):

| Profile | ΔE_motor (MJ) | ΔE_inverter (MJ) | Difference (%) | M01 final SOC (%) | I01 final SOC (%) |
|---|---:|---:|---:|---:|---:|
| NOMINAL_6H | 2.049335 | 2.049335 | 0.000e+00 | 59.27387 | 59.28098 |
| SHIFT_REGEN_COLD_6H | 2.207074 | 2.207074 | 2.110e-14 | 59.26588 | 59.26788 |

**Critical distinctions:**
- These equalities are expected by construction; interpreting zero mismatch as independent validation would be an **OVERCLAIM**.
- Matching loss energy does not match observed R33 residual distributions, current, OCV errors, temperature or all operating constraints. Note that M01/I01 still have slightly different final SOC in the table.
- `results/m01_i01_energy_match_development_only.json` is **not** the sealed runner's `M01_I01_ENERGY_MATCH_RECEIPT.json`: seed/authorization/input hash/split requirements are not met, and the waveform and physics candidate are not approved.
- Following this addition the local unit test suite has **70/70 tests PASS**, including four additional analytic-matching and mode invariance tests. This supersedes the earlier count of 66 and the initial 52.

## Next gate

(1) Audit new candidate on 5-second time boundary across fault families under amended protocol; (2) reconcile historical observation-layer implementation and its provenance; (3) verify full electrothermal energy accounting, charge-control constraints and public-data domain; (4) prepare prospective protocol amendment for user decision; (5) only after authorization: official training-only H00 calibration, M01/I01 energy matching, smoke, full campaign and external metrics.
