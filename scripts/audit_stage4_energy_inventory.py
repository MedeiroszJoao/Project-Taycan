"""Independent Stage 4 energy-inventory audit. Research-only; no Stage 4 scoring.

Computes the change in an idealized chemical-energy inventory when the
candidate's capacity and polarization capacitance vary with its age state.
A nonzero change is a *missing constitutive accounting term*, not a measured
thermal loss. Fixed SOC and fixed polarization voltage are diagnostic
counterfactuals; they are NOT a physical six-hour vehicle trajectory.

Only Python stdlib; no hidden truth or held-out datasets are accessed.
"""
from __future__ import annotations

import json
import math
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src" / "simulator"))
from candidate_sim import model_energy_consistent as physical  # noqa: E402


def chemical_inventory_joules(
    z: float, age: float, config: physical.ModelConfig
) -> float:
    """OCV-integrated toy chemical inventory at reference T=25 C.

    E = N_groups*N_branches*(3600 Q_cell)*(1-alpha age)
        * integral_0^z (U0 + Uspan*s) ds.
    No reversible entropy, temperature, concentration or side-reaction term.
    """
    if not (math.isfinite(z) and 0.0 <= z <= 1.0):
        raise ValueError("SOC must be finite in [0,1]")
    if not (math.isfinite(age) and 0.0 <= age <= 1.0):
        raise ValueError("age must be finite in [0,1]")
    q_ah = config.capacity_ah_cell * (1.0 - config.age_capacity_loss * age)
    if q_ah <= 0.0:
        raise ValueError("capacity must be positive")
    integral_ocv = config.ocv_low_v * z + 0.5 * config.ocv_span_v * z * z
    return (
        physical.N_GROUPS * physical.BRANCHES
        * (3600.0 * q_ah) * integral_ocv
    )


def rc_capacitance_farads(age: float, config: physical.ModelConfig) -> float:
    """Capacitance implied by the model's constant tau and age-dependent R1."""
    if not math.isfinite(age) or age < 0 or age > 1:
        raise ValueError("invalid age")
    resistance = config.r1_ohm_cell * (1.0 + config.age_resistance_gain * age)
    return config.rc_tau_s / resistance


def parameter_jump_joules(
    polarization_voltage: float,
    age_before: float,
    age_after: float,
    config: physical.ModelConfig,
) -> float:
    """Energy step when C changes with V held fixed.

    Sign and magnitude follow Delta E = 1/2 V^2 (C_after-C_before)
    per cell-branch. A physically changing capacitor may exchange work;
    this is NOT necessarily Joule heat, and no process law is assumed.
    """
    if not math.isfinite(polarization_voltage):
        raise ValueError("polarization voltage must be finite")
    return (
        0.5 * physical.N_GROUPS * physical.BRANCHES
        * polarization_voltage ** 2
        * (
            rc_capacitance_farads(age_after, config)
            - rc_capacitance_farads(age_before, config)
        )
    )


def audit_default_six_hours() -> dict:
    p = physical.ModelConfig()
    duration_s = 6 * 3600
    initial_age = p.aging_index
    final_age = min(1.0, initial_age + p.aging_rate_per_s * duration_s)
    soc_counterfactual = 0.6
    pol_counterfactual_v = 0.15
    e0 = chemical_inventory_joules(soc_counterfactual, initial_age, p)
    e1 = chemical_inventory_joules(soc_counterfactual, final_age, p)
    qdelta = e1 - e0
    c0 = rc_capacitance_farads(initial_age, p)
    c1 = rc_capacitance_farads(final_age, p)
    rc_jump = parameter_jump_joules(
        pol_counterfactual_v, initial_age, final_age, p
    )
    # These geometric equalities follow the 168s2p candidate, not independent
    # validation of the individual 2022 Taycan electrical characteristics.
    if (
        physical.N_MODULES * physical.GROUPS_PER_MODULE
        != physical.N_GROUPS
        or physical.BRANCHES != 2
        or physical.N_GROUPS != 168
    ):
        raise AssertionError("unexpected candidate pack geometry")

    return {
        "classification": "ADVERSARIAL_STATIC_INVENTORY_AUDIT_NOT_STAGE4_EPISODE",
        "evidence": "derived from candidate parameters, not measured",
        "model": "src/simulator/candidate_sim/model_energy_consistent.py",
        "duration_s": duration_s,
        "assumed_fixed_SOC": soc_counterfactual,
        "assumed_fixed_temperature_C": 25.0,
        "initial_age": initial_age,
        "final_age": final_age,
        "initial_chemical_inventory_J": e0,
        "final_chemical_inventory_J": e1,
        "aging_capacity_inventory_delta_J": qdelta,
        "assumed_fixed_polarization_voltage_V": pol_counterfactual_v,
        "initial_rc_capacitance_F": c0,
        "final_rc_capacitance_F": c1,
        "rc_parameter_inventory_jump_J": rc_jump,
        "cell_topology": {
            "series": physical.N_GROUPS,
            "parallel": physical.BRANCHES,
            "modules": physical.N_MODULES,
            "groups_in_series_per_module": physical.GROUPS_PER_MODULE,
            "total_cells": physical.N_GROUPS * physical.BRANCHES,
        },
        "scientific_limitations": [
            "Not a trajectory; holding SOC and polarization fixed is diagnostic.",
            "Chemical inventory integrates the assumed linear OCV at 25 C only.",
            "Changing effective capacity requires a loss or side-reaction law.",
            "Changing capacitance requires constitutive work/energy accounting.",
            "Do not add both terms to heat without a derived physical mechanism.",
            "Neither DC-bus closure nor RC fixed-step closure settles these gaps.",
        ],
        "approval": "NONE; Stage 4 official experiments remain unauthorized",
    }


def main() -> None:
    print(json.dumps(audit_default_six_hours(), indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
