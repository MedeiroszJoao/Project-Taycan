"""UNAPPROVED Stage 4 observation-layer CANDIDATE, not recovered original.

Operates only on permitted noise-free Stage 3 observed-channel rows. No latent truth,
labels, severities, physics/auxiliary seeds or time-indexed nuisance values enter
published channels. The external auxiliary trace is a *separate* physical input
proposal and MUST be physically coupled before any Stage 4 episode is scored.

Innovations use a Gaussian Random(seed_observer) stream. SOC initial group biases
consume the registered post-RPM/torque-bias XorShift nuisance state. Auxiliary
innovations consume an independent Random(seed_aux) stream, exclusively via
``auxiliary_trace_candidate``. Neither replaces the historical observation layer.
"""
from __future__ import annotations

import math
import random
import json
from pathlib import Path
from typing import Mapping, Sequence

# Source-of-truth observed-ID whitelist comes from the byte-verified Stage 3
# signal contract. Disallow accidental label/seed/hidden-state leakage.
CONTRACT_PATH = Path(__file__).resolve().parents[1] / "simulator/taycan_sim/signal_contract.json"
APPROVED_OBD_IDS = frozenset(json.loads(CONTRACT_PATH.read_text(encoding="utf-8"))["approved_ids"])

RPM_CHANNELS = ("TAYCAN_EM_RPM_1", "TAYCAN_EM_RPM_2", "TAYCAN_ENG_MOTOR_RPM")
TORQUE_CHANNELS = ("TAYCAN_EM_TORQ_1", "TAYCAN_EM_TORQ_2")
GROUP_SOC_CHANNELS = tuple(f"TAYCAN_HVBAT_MOD{m}_C{g}_SOC" for m in range(1, 29) for g in range(1, 7))
GROUP_V_CHANNELS = tuple(f"TAYCAN_HVBAT_MOD{m}_C{g}_V" for m in range(1, 29) for g in range(1, 7))
MODULE_T_CHANNELS = tuple(f"TAYCAN_HVBAT_MOD{m}_T{j}" for m in range(1, 29) for j in range(1, 4))
CURRENT = ("TAYCAN_BMS_I", "TAYCAN_HVBAT_CURRENT")
AH_CHARGE, AH_DISCHARGE = "TAYCAN_HVBAT_TOT_AH_CHRG", "TAYCAN_HVBAT_TOT_AH_DCHRG"
KWH_CHARGE, KWH_DISCHARGE = "TAYCAN_HVBAT_TOT_KWH_CHRG", "TAYCAN_HVBAT_TOT_KWH_DCHRG"


class XorShift32:
    """Match Stage 4 manifest generator's xorshift32 uniform stream."""
    def __init__(self, seed: int):
        if not (0 <= seed < 2**32):
            raise ValueError("seed out of uint32")
        self.state = seed or 0x6D2B79F5

    def uniform(self) -> float:
        x = self.state
        x ^= x << 13 & 0xFFFFFFFF
        x ^= x >> 17
        x ^= x << 5 & 0xFFFFFFFF
        self.state = x & 0xFFFFFFFF
        return self.state / 4294967296.0

    def gauss(self) -> float:
        # Box-Muller with an explicit, stable draw order. Avoid ln(0).
        u1 = max(self.uniform(), 2**-32)
        u2 = self.uniform()
        return math.sqrt(-2.0 * math.log(u1)) * math.cos(2 * math.pi * u2)


def exact_ou_transition(phi_per_s: float, sigma_per_sqrt_s: float, dt_s: float) -> tuple[float, float]:
    """Exact sampled OU: dX=ln(phi)*X dt + sigma dW, for constant parameters."""
    if not (math.isfinite(phi_per_s) and 0 < phi_per_s <= 1):
        raise ValueError("phi must be finite in (0,1]")
    if not (math.isfinite(sigma_per_sqrt_s) and sigma_per_sqrt_s >= 0):
        raise ValueError("sigma must be finite nonnegative")
    if not (math.isfinite(dt_s) and dt_s > 0):
        raise ValueError("dt must be finite positive")
    log_phi = math.log(phi_per_s)
    a = math.exp(log_phi * dt_s)
    var_seconds = dt_s if log_phi == 0 else math.expm1(2.0 * log_phi * dt_s) / (2.0 * log_phi)
    return a, sigma_per_sqrt_s * math.sqrt(var_seconds)


def _validate_config(c: Mapping) -> None:
    if c.get("counter_source") not in CURRENT and c.get("counter_source") not in ("BMS_I", "HVBAT_CURRENT"):
        raise ValueError("counter_source must be BMS_I or HVBAT_CURRENT; truth forbidden")
    if c.get("acquisition_mode") not in ("independent", "shared"):
        raise ValueError("acquisition_mode must be independent or shared")
    if c.get("diff_motor_t_mapping") not in ("winding_proxy", "uninformative"):
        raise ValueError("diff motor mapping invalid")
    for channel in RPM_CHANNELS:
        if channel not in c["rpm_persistent_bias_by_channel_rpm"]:
            raise ValueError(f"missing RPM bias for {channel}")
    for channel in TORQUE_CHANNELS:
        if channel not in c["torque_persistent_bias_by_channel_Nm"]:
            raise ValueError(f"missing torque bias for {channel}")
    for field in ("rpm_white_sigma_rpm", "torque_white_sigma_Nm", "soc_group_bias_sd_pp", "soc_innovation_pp_sqrt_s"):
        if not (math.isfinite(float(c[field])) and float(c[field]) >= 0):
            raise ValueError(f"invalid {field}")
    for field in ("observer", "aux", "nuisance", "physics"):
        seed = c["seeds"][field]
        if type(seed) is not int or not 0 <= seed < 2**32:
            raise ValueError(f"invalid {field} seed")
    if len(set(c["seeds"].values())) != 4:
        raise ValueError("four RNG streams must be distinct")
    for b in (*c["rpm_persistent_bias_by_channel_rpm"].values(), *c["torque_persistent_bias_by_channel_Nm"].values()):
        if not math.isfinite(float(b)):
            raise ValueError("nonfinite bias")
    exact_ou_transition(float(c["soc_phi_per_s"]), float(c["soc_innovation_pp_sqrt_s"]), 1)


def transform_observed_rows(noiseless_observed: Sequence[Mapping[str, float]], c: Mapping,
                            dt_s: float) -> tuple[list[dict[str, float]], dict]:
    """Add hypothetical measurement imperfections to noise-free *observed* rows.

    The caller must supply sensor_noise=False output from the physical model;
    otherwise white noise would be double counted. This function cannot assert
    provenance of arbitrary input measurements. It never accepts latent truth.
    """
    _validate_config(c)
    if not noiseless_observed:
        raise ValueError("empty observations")
    if not math.isfinite(dt_s) or dt_s <= 0:
        raise ValueError("invalid dt_s")
    mandatory = (*RPM_CHANNELS, *TORQUE_CHANNELS, *GROUP_SOC_CHANNELS, *GROUP_V_CHANNELS,
                 *CURRENT, "TAYCAN_BMS_SOC", "TAYCAN_HVBAT_VOLT")
    observer = random.Random(c["seeds"]["observer"])
    nuisance = XorShift32(int(c["soc_bias_rng_seed_after_channel_biases"]))
    initial_bias = [nuisance.gauss() * c["soc_group_bias_sd_pp"] for _ in GROUP_SOC_CHANNELS]
    soc_x = [0.0] * len(GROUP_SOC_CHANNELS)
    a_soc, sd_soc = exact_ou_transition(c["soc_phi_per_s"], c["soc_innovation_pp_sqrt_s"], dt_s)
    noise_enabled = bool(c["sensor_noise_enabled"])
    ah_chg = ah_dis = kwh_chg = kwh_dis = 0.0
    observed = []
    clipping = 0
    voltage_sigma = float(c.get("voltage_white_sigma_V", 0.001))
    current_sigma = float(c.get("current_white_sigma_A", 0.06))
    temp_sigma = float(c.get("temperature_white_sigma_C", 0.04))
    if min(voltage_sigma,current_sigma,temp_sigma) < 0 or not all(map(math.isfinite,(voltage_sigma,current_sigma,temp_sigma))):
        raise ValueError("invalid physical sensor noise")
    for i, baseline in enumerate(noiseless_observed):
        if any(k not in baseline for k in mandatory):
            raise ValueError("input is missing mandatory OBD sensor channels")
        if any(not math.isfinite(float(v)) for v in baseline.values()):
            raise ValueError("nonfinite observed-channel input")
        forbidden = set(baseline).difference(APPROVED_OBD_IDS)
        if forbidden:
            raise ValueError(f"non-OBD/latent channel(s) in observations: {sorted(forbidden)!r}")
        row = dict(baseline)
        if noise_enabled:
            for ch in GROUP_V_CHANNELS:
                row[ch] += observer.gauss(0.0, voltage_sigma)
            for ch in MODULE_T_CHANNELS:
                if ch in row:
                    row[ch] += observer.gauss(0.0, temp_sigma)
            row["TAYCAN_HVBAT_VOLT"] += observer.gauss(0.0, voltage_sigma)
            if c["acquisition_mode"] == "shared":
                # Channel pairing shares exactly the same acquisition, not two white draws.
                shared = row[CURRENT[0]] + observer.gauss(0.0, current_sigma)
                row[CURRENT[0]] = row[CURRENT[1]] = shared
                total_v = sum(row[ch] for ch in GROUP_V_CHANNELS)
                row["TAYCAN_BMS_CELL_V_SUM"] = row["TAYCAN_HVBAT_CELL_SUM_V"] = total_v
            else:
                for ch in CURRENT:
                    row[ch] += observer.gauss(0.0, current_sigma)
                row["TAYCAN_BMS_CELL_V_SUM"] += observer.gauss(0.0, voltage_sigma)
                row["TAYCAN_HVBAT_CELL_SUM_V"] += observer.gauss(0.0, voltage_sigma)
            for ch in RPM_CHANNELS:
                row[ch] += c["rpm_persistent_bias_by_channel_rpm"][ch] + observer.gauss(0.0, c["rpm_white_sigma_rpm"])
            for ch in TORQUE_CHANNELS:
                row[ch] += c["torque_persistent_bias_by_channel_Nm"][ch] + observer.gauss(0.0, c["torque_white_sigma_Nm"])
            # Feature whitelist omits ENG_MOTOR_RPM but it is a physical OBD channel.
            for j, ch in enumerate(GROUP_SOC_CHANNELS):
                soc_x[j] = a_soc * soc_x[j] + sd_soc * observer.gauss(0.0, 1.0)
                v = row[ch] + initial_bias[j] + soc_x[j]
                if v < 0 or v > 100:
                    clipping += 1
                row[ch] = max(0.0, min(100.0, v))
            # Reconstruct the BMS group-SOC estimator from permitted measured groups;
            # preserve the Stage 3 baseline's BMS-vs-group proxy offset.
            offset = baseline["TAYCAN_BMS_SOC"] - sum(baseline[ch] for ch in GROUP_SOC_CHANNELS) / len(GROUP_SOC_CHANNELS)
            row["TAYCAN_BMS_SOC"] = max(0.0, min(100.0,
                sum(row[ch] for ch in GROUP_SOC_CHANNELS) / len(GROUP_SOC_CHANNELS) + offset))
        selected = "TAYCAN_BMS_I" if c["counter_source"] == "BMS_I" else "TAYCAN_HVBAT_CURRENT"
        d_ah = row[selected] * dt_s / 3600.0
        d_kwh = row[selected] * row["TAYCAN_HVBAT_VOLT"] * dt_s / 3600000.0
        ah_dis += max(0, d_ah)
        ah_chg += max(0, -d_ah)
        kwh_dis += max(0, d_kwh)
        kwh_chg += max(0, -d_kwh)
        row[AH_CHARGE], row[AH_DISCHARGE] = ah_chg, ah_dis
        row[KWH_CHARGE], row[KWH_DISCHARGE] = kwh_chg, kwh_dis
        row["time_s"] = float(i) * dt_s
        row["dt_s"] = dt_s
        observed.append(row)
    return observed, {"status": "CANDIDATE_NOT_ORIGINAL", "noise_enabled": noise_enabled,
                      "soc_clipped_group_samples": clipping, "num_steps": len(observed),
                      "model_input_requirement": "sensor_noise=False; observed OBD rows only",
                      "auxiliary_energy_coupling": "NOT_IMPLEMENTED; do not score official episodes"}


def auxiliary_trace_candidate(c: Mapping, dt_s: float, steps: int, *, nominal_W: float = 1900.0) -> list[float]:
    """Nonnegative bounded stochastic DC load, to inject into candidate physics."""
    _validate_config(c)
    if not isinstance(steps,int) or steps < 1 or not math.isfinite(nominal_W):
        raise ValueError("invalid trace arguments")
    a, sd = exact_ou_transition(c["aux_phi_per_s"], c["aux_white_sigma_W_sqrt_s"], dt_s)
    cap = float(c["aux_cap_W"])
    if not math.isfinite(cap) or cap <= 0:
        raise ValueError("invalid auxiliary cap")
    rng = random.Random(c["seeds"]["aux"])
    x = 0.0
    values = []
    for _ in range(steps):
        x = max(-cap, min(cap, a * x + sd * rng.gauss(0, 1)))
        # This is a cap on actual DC auxiliary demand, not on the AR1 residual.
        # Clipping makes the simulated load nonnegative and <= aux_cap_W.
        values.append(min(cap, max(0.0, nominal_W + x)))
    return values
