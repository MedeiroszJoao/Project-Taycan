"""Development-only sensitivity of M01/I01 energy matching to inverter state.

The existing candidate adds I01 extra inverter loss at every timestep,
including parked rest/charge. This counterfactual audit compares that rule
with a gated rule that adds extra loss only with a motor operating.
Neither policy is physically validated for the target Taycan; this script
does NOT modify the simulator, issue calibration receipts, or read holdouts.
"""
from __future__ import annotations

import json
import math
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src" / "simulator"))
from candidate_sim import model_energy_consistent as physical  # noqa: E402
from scripts.duty_cycle_candidate import build_duty_inputs  # noqa: E402


def inspect_profile(profile: str, m01_severity: float = 1.0) -> dict:
    if not (math.isfinite(m01_severity) and 0 < m01_severity <= 1):
        raise ValueError("invalid target M01 severity")
    trace = build_duty_inputs(
        dt_s=5.0, charge_power_kw=0.0, profile_id=profile
    )
    p = physical.ModelConfig()
    dt = trace.dt_s
    active = [
        (abs(tau) > 1e-12 or abs(rpm) > 1e-12)
        for tau, rpm in zip(trace.torque_nm, trace.rpm)
    ]
    if len(active) != len(trace.mode):
        raise AssertionError("duty trace lengths disagree")
    stationary_modes = {"rest", "charge"}
    if any(
        active[i] == (trace.mode[i] in stationary_modes)
        for i in range(len(active))
    ):
        raise AssertionError("operating-mode definition is inconsistent")
    active_duration_s = sum(active) * dt
    stationary_duration_s = (len(active) - sum(active)) * dt
    duration_s = len(active) * dt

    # The time-integrated fault injection is purely algebraic in this
    # experimental model; temperature and SOC do not enter its definition.
    motor_extra_j = (
        p.motor_copper_coeff_w_per_nm2
        * (p.motor_loss_fault_multiplier - 1)
        * m01_severity
        * sum(tau * tau * dt for tau in trace.torque_nm)
    )
    full_inverter_energy_j = p.inverter_fault_extra_W * duration_s
    gated_inverter_energy_j = p.inverter_fault_extra_W * active_duration_s
    if gated_inverter_energy_j <= 0:
        raise ValueError("no operating time in candidate waveform")
    original_i01_severity = motor_extra_j / full_inverter_energy_j
    gated_i01_severity = motor_extra_j / gated_inverter_energy_j
    if original_i01_severity > 1 or gated_i01_severity > 1:
        raise ValueError("energy matching severity is infeasible for candidate")
    idle_energy_j = original_i01_severity * p.inverter_fault_extra_W * stationary_duration_s
    return {
        "profile": profile,
        "M01_severity": m01_severity,
        "mode_duration_s": {
            key: trace.mode.count(key) * dt
            for key in ("cruise","acceleration","regeneration","rest","charge")
        },
        "active_duration_s": active_duration_s,
        "stationary_duration_s": stationary_duration_s,
        "inverter_fault_extra_power_W": p.inverter_fault_extra_W,
        "M01_injected_extra_energy_J": motor_extra_j,
        "I01_full_injection_energy_at_severity_1_J": full_inverter_energy_j,
        "I01_gated_energy_at_severity_1_J": gated_inverter_energy_j,
        "I01_matched_severity_always_on": original_i01_severity,
        "I01_matched_severity_activity_gated": gated_i01_severity,
        "current_I01_stationary_extra_energy_at_match_J": idle_energy_j,
        "stationary_fraction_of_I01_matched_loss": idle_energy_j / motor_extra_j,
        "classification": "NONSCORING_ALTERNATIVE_ASSUMPTIONS_NOT_CALIBRATED",
        "warning": (
            "The inverter may have standby losses, but the 1600 W constant "
            "fault power has not been physically justified for parked states. "
            "Do not replace official 12-point matching with these alternatives."
        ),
    }


def audit() -> dict:
    profiles = [
        inspect_profile("NOMINAL_6H"),
        inspect_profile("SHIFT_REGEN_COLD_6H"),
    ]
    return {
        "status": "OPEN_MODEL_DISCREPANCY_NOT_STAGE4_APPROVAL",
        "profiles": profiles,
        "held_out_data_used": False,
        "official_receipt_generated": False,
    }


if __name__ == "__main__":
    print(json.dumps(audit(), indent=2, sort_keys=True))
