# Stage 4 revision — Wolfram analytical checks (not simulation)

**Status:** algebra/numerical verification only. No physical scenario was rerun, no observed R33 sample was produced, and no Bayesian/ML fitting was conducted. The approved Stage 3 `model.py` is unchanged (`af4e576cf824d30ee6aa9b2fd1f2c18d576fd269027df67c43c5e7647266ff4e`).

## A. R33 observation-error propagation

The frozen Stage 2 relation R33 is
`R33 = V_HV*I_HV - sum_j( torque_j * (2*pi/60) * rpm_j )`.
This is not a direct inverter-fault discriminator: traction, motor, inverter, mechanical and auxiliary power losses all appear within the energy balance.

For independent zero-mean white torque and RPM noise `sigma_tau=1.5 N*m`, `sigma_rpm=12 rpm`, `sigma_V=0.001 V` and `sigma_I=0.06 A`, conditional on true values and persistent biases set to zero,

```
Var(R33 measurement error) =
  (V^2*sigma_I^2 + I^2*sigma_V^2 + sigma_I^2*sigma_V^2)
  +(2*pi/60)^2 sum_j[torque_j^2*sigma_rpm^2
     +rpm_j^2*sigma_tau^2
     +sigma_tau^2*sigma_rpm^2].
```

At an **illustrative operating point**, **not a Stage 4 run**, each of two powertrain channels has torque 80 N*m and 3150 rpm, with HV 650 V, 50 A:

```wolfram
N[Sqrt[2 (2 Pi/60)^2 (80^2 12^2+3150^2 1.5^2+1.5^2 12^2)
       +650^2 0.06^2+50^2 0.001^2+0.06^2 0.001^2],9]
```
Output: `715.1201345072374` **W standard deviation (noise only)**.

With independent episode-level biases uniform in `[-1,1] N*m` and `[-12,12] rpm`, the across-episode standard deviation of bias-induced shift is `281.5663211484724 W`; combined marginal standard deviation is `768.554747550709 W`. The conservative magnitude bound for the shift in the mean residual at that point is `863.3096612064752 W`.

These are **conditional analytic numbers** based on assumed independent errors and **cannot** replace measured mean, SD, bias ablation, or empirical M01/I01 separability after rerunning the simulations. Persistent biases shift mean per episode; their marginal average across symmetric simulated episodes is zero.

## B. AR(1) SOC drift

Assumed `epsilon_t = phi epsilon_(t-1) + noise` with per-second innovation standard deviation `0.035 percentage point`.
Stationary SD `0.035/sqrt(1-phi^2)`, half-life `ln(1/2)/ln(phi)`.

| phi | stationary SD (pp) | half-life (s) | exact 10 s innovation multiplier |
| --- | ---: | ---: | ---: |
| 0.97 | 0.1439707622 | 22.7566 | 2.77835 |
| 0.995 | 0.3504383220 | 138.2826 | 3.09239 |
| 0.9995 | 1.1069355567 | 1385.9478 | 3.15518 |
| 0.9999 | 2.4749356083 | 6931.1252 | 3.16086 |

At `dt>1s`, the innovation scale preserving stationary variance is `sqrt((1-phi^(2dt))/(1-phi^2))`, not generically `sqrt(dt)`. The original approximation changes stationary variance appreciably at phi 0.97 and dt 10s.

## C. Balanced six-hour long-horizon protocol (PRE-REG, not an observed trajectory)

- Initial SOC 60%, acceptable [30,80]% and nominal usable energy **ASSUMED** 70 kWh, sensitivity [65,75] kWh. Must verify model internal Ah/SOC versus kWh balance; cannot equate 79.2 kWh gross directly with usable energy.
- Five 12-minute blocks per 60-minute cycle. The previously used constant 7 kW charge block is **not assumed sufficient**.
- Calibrate a **single battery-side DC charge boundary** using only the H00 training reference. Hold that schedule fixed across faults, mappings, and test episodes.
- Illustrative only: 11.8 kWh pre-charge consumption in 48 minutes requires 59.0 kW battery-side charging for 12 minutes to close energy balance; if 90% grid-to-battery efficiency were assumed, this corresponds to 65.5556 kW upstream. SOC nadir under a simplified fixed 70 kWh usable-energy assumption would be 43.1429%. No charger/OBC model is implied.
- **Only measured synthetic simulator trajectories** can pass/fail the 30–80% window and energy closure; record SOC(t), min/max, input/output kWh and residual.

## D. M01/I01 energy matching

Approved assumed coefficients include `k_Cu=0.033 W/(N*m)^2`, `motor_loss_fault_multiplier=2.0`, and `inverter_fault_extra_W=1600 W` (Stage 3 parameter registry). Determine the **actual** extra loss for each hypothesis from the frozen physical simulator over the identical training-only profile. Match `integral(Delta P_M dt)` to `integral(Delta P_I dt)`, never raw numeric severity alone. Both DIFF mappings must be evaluated, and any unmatched severity must be explicitly marked.

**Toy algebra only:** one hypothetical motor alternating equally between torque 80 and 190 N*m has mean torque²=21250 (N*m)². At motor severity 0.5, a linear coefficient-multiplication interpretation gives mean extra loss 350.625 W, equal to an inverter extra-loss severity 350.625/1600 = **0.219140625**. This is **not** an executable-model matched-pair estimate and does not cover two axles or dynamic feedback.

## E. Oxford, LG E66 and held-out data

- Oxford: user-reported 22 mean-temperature exceptions and four `OCV duration >100000 s` exceptions remain **pending full CSV regeneration**. Explicit flags and exclusion policy are preregistered in `REVISION_PREREG_ADDENDUM.json`; do not silently remove any row. The `q` value near 745 for a 740 mAh cell suggests **mAh** (INFERENCE).
- Oxford Cell7 and Cell8 remain virgin numerical holdouts. NASA B0018 is **CONTAMINATED**, and not a blind test. `holdout_quarantine` and B0018 were absent from the currently published Project-Taycan Git tree and targeted code search on the default branch; no universal claim is made about every historical/private repository.
- LG E66 metadata only: 63 MAT cell files and 12 MAT module files, recorded without opening additional numeric series. The original README says nominal 65 Ah; the McMaster research catalogue [labels it 60 Ah](https://battery.mcmaster.ca/research/). Independent [Batemo](https://www.batemo.com/products/batemo-cell-explorer/lg-chem-e66a/) identifies 65.0 Ah nominal for an LG E66A extracted from a 2020 Taycan. **Cell identity/year, 60 vs 65 Ah and transfer to a MY2022 4S remain unresolved; no silent normalization.**

## Runtime blocker / status

**BLOQUEIO:** local execution kernel unavailable, with repeated ClientError, so Stage 4 Python scenario reruns, full Oxford flagged file creation, and model-specific R33 empirical statistics **have not been executed**. Acceptable exits: (A) resume file/container execution and run the unchanged frozen Stage 3 code through the revised Stage 4 wrapper, or (B) execute the exact reproducible Stage 4 package in the user's Windows environment and ingest execution logs; do not fabricate numerical outputs.

This document is a post-review analytical/preregistration addendum, **not** an approval of Stage 4 or Stage 5.
