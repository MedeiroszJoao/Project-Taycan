# Stage 4 — Independent energy inventory gate (unapproved)

**2026-10-23. Candidate only. Do not merge into frozen source or count as registered episodes.**

## Added audit

`scripts/audit_stage4_energy_inventory.py` computes two **counterfactual static parameter-change terms** without using the simulator's own output-energy identity:

1. **Effective capacity decreasing with age** under held SOC, reference 25°C, and the candidate's assumed linear open-circuit voltage:
   `E_chem(z,a)=168*2*3600*Q_cell*(1-alpha*a)*(U_low*z + U_span*z*z/2)`.
   Over six hours at default `aging_rate_per_s=1e-8`, `z=0.60` held, `a=0.15` to `a=0.150216`, the model's accounting inventory declines by **4,171.513109 J**, without an explicit degradation-energy or side-reaction ledger.
2. **RC equivalent capacitance** is implicit: `C(a)=tau/(R1_0*(1+beta*a))`. Holding polarization `V_p=0.15 V` for an *illustrative* parameter change, the total 336-branch storage jump is **-63.163210 J**, beyond the exact fixed-R/C per-step identity. This is **not** predicted energy loss in any six-hour run with physically evolving `V_p`.

**Important:** these terms CANNOT simply be inserted into the thermal dissipation ledger. Capacity fade is a constitutive/side-reaction process, while variable capacitance requires its own constitutive work/energy law. Claimed whole-cell conservation remains **UNRESOLVED**. Do not treat the 4.17 kJ as observed temperature rise or as Taycan-specific degradation. If aging is intentionally a prescribed parametric drift, disable it for an explicitly frozen-parameter numerical conservation experiment and disclose the missing constitutive accounting.

For the RC branch, the source candidate implements
`dv/dt=I/C-v/(R C)`, `E=0.5*C*v^2` **within constant-coefficient steps**. Under time-varying `C(t)`, the state equation requires a choice of controlled-current capacitor law: `I=V/R+d(CV)/dt` if it is a literal variable capacitor, or the original `dv/dt` as a phenomenological ECM. Neither choice permits silently treating all parameter dependence as ordinary Joule heat.

## Primary sources / transfer cautions

- Bernardi, Pawlikowski, Newman (1985): https://doi.org/10.1149/1.2113792
- Li et al. (2019), passive physics-derived equivalent circuits: https://doi.org/10.1016/j.electacta.2018.12.167
- Porsche Taycan battery documentation: 28 modules, 336 cells, standard 79.2 kWh. https://newsroom.porsche.com/en_AU/2021/products/technical-feature-the-porsche-taycan-23670.html
- Porsche published pack topology is `168s2p`. For uniform 12-cell modules it implies `6s2p` in each of 28 modules. The Borealis E66 metadata says `6p2s`; its topology claim must be reconciled against instrumentation/wiring, and not silently mapped to this 4S pack. https://borealisdata.ca/dataset.xhtml?persistentId=doi:10.5683/SP3/7JP3NM

## Technical reproduction

```bash
PYTHONPATH=src/simulator:src:. python scripts/audit_stage4_energy_inventory.py
PYTHONPATH=src/simulator:src:. python -m unittest discover -s tests/unit -p 'test_*.py' -v
```

The separate GitHub Actions workflow `.github/workflows/stage4-research-candidate.yml` runs the full unit suite and this read-only analysis on the research branch. **A workflow being configured is not a claim of successful execution.** No official smoke, calibration receipt or 2,232-episode scoring is authorized.
