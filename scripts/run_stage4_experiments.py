#!/usr/bin/env python3
"""Fail-closed Stage 4 runner. Code-only addition; this script does not run at commit time.

The frozen physical model and observation layer are intentionally loaded through a local
backend adapter because those executable artifacts are not currently in this repository.
See docs/methodology/STAGE4_RUNNER_CONTRACT.md for the exact contract.
"""
from __future__ import annotations

import argparse
import csv
import gzip
import hashlib
import importlib.util
import io
import json
import math
import os
import subprocess
import sys
import tempfile
import time
from pathlib import Path

if str(Path(__file__).resolve().parents[1]) not in sys.path:
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from typing import Any, Iterable

ROOT = Path(__file__).resolve().parents[1]
STAGE4 = ROOT / "experiments" / "stage_04_data_validation"
PREREG_PATH = STAGE4 / "REVISION_PREREG_ADDENDUM.json"
AMENDMENT_PATH = STAGE4 / "STAGE4_APPEND_ONLY_AMENDMENT.json"
MANIFEST_PATH = STAGE4 / "STAGE4_EPISODE_MANIFEST.csv"

EXPECTED = {
    "prereg_sha256": "1c3c50149e50bceb3f14b8a334b248c225cdc8478128cf88952051ea0bce1b21",
    "prereg_git_blob_sha1": "acbf92a36fadb4f7e0a5c9e2d30e80186d4ce19c",
    "amendment_sha256": "18c5c8f104f2909a1f23a594eafd8e26a77a1ea4f80e285e0e1396b5a1da29ba",
    "amendment_git_blob_sha1": "07124a8d0c854a66de77dbe6f0991e9014df991f",
    "manifest_sha256": "1894681c771335e5ecb06f8fa421c11aaf8806c5f5ebab3182035e44d28b86f0",
    "manifest_git_blob_sha1": "af91c16f2b234e1f3f964ae73d6ea27c72f1aad4",
    "model_py_sha256": "af4e576cf824d30ee6aa9b2fd1f2c18d576fd269027df67c43c5e7647266ff4e",
    "freeze_sha256": "5822c3e43e6f4634c7ca60d0aabb6f38afe5cecece99883833ee1c4d12dc5df8",
}
HYPOTHESES = ["H00", "B01", "B02", "B03", "B04", "B05", "B06", "B07", "B08", "B09", "M01", "I01"]
SPLITS = ("train", "validation", "test")
STREAMS = ("physics", "observer", "aux", "nuisance")
PROFILES = ("NOMINAL_6H", "SHIFT_REGEN_COLD_6H")
SOC_WINDOW = (30.0, 80.0)
SOC_INITIAL = 60.0
DURATION_S = 21600
DT_S = 5
BISECTION_MIN = 8
BISECTION_MAX = 12
BISECTION_BRACKET_KW = (0.0, 120.0)
SOC_FINAL_TOLERANCE_PP = 0.5
REGULARIZER = 1e-9  # Recorded for provenance; singular OLS fits are NA, never silently regularized.

FEATURES = [
    ("F01", "mean_R33_W"),
    ("F02", "sd_R33_W"),
    ("F03", "beta_tau2_W_per_Nm2"),
    ("F04", "beta_omega_W_per_rad_s"),
    ("F05", "sd_regressed_R33_W"),
    ("F06", "mean_current_diff_A"),
    ("F07", "sd_current_diff_A"),
    ("F08", "mean_module_pair_voltage_spread_V"),
    ("F09", "p95_module_pair_voltage_spread_V"),
    ("F10", "mean_pack_group_voltage_consistency_V"),
    ("F11", "sd_pack_group_voltage_consistency_V"),
    ("F12", "mean_BMS_SOC_pct"),
    ("F13", "SOC_slope_pct_per_hour"),
    ("F14", "net_Ah_counter_minus_BMS_integral_Ah"),
    ("F15", "mean_thermal_spread_C"),
    ("F16", "p95_thermal_spread_C"),
    ("F17", "max_internal_module_T_spread_C"),
    ("F18", "mean_DIFF_MOTOR_T_C"),
    ("F19", "slope_DIFF_MOTOR_T_C_per_hour"),
    ("F20", "integrated_observed_HV_kWh"),
    ("F21", "negative_DC_power_fraction"),
    ("F22", "mean_min_isolation_kohm"),
    ("F23", "min_isolation_kohm"),
    ("F24", "time_mean_sum_torque_squared"),
    ("F25", "time_mean_sum_abs_angular_speed"),
    ("F26", "beta_tau_W_per_Nm"),
    ("F27", "beta_tauomega_dimensionless"),
    ("F28", "net_kWh_counter_minus_BMS_DC_integral_kWh"),
]
FEATURE_NAMES = [f"{code}_{name}" for code, name in FEATURES]
MASK_NAMES = [f"mask_{code}" for code, _ in FEATURES]

RPM_BIAS_CHANNELS = ("TAYCAN_EM_RPM_1", "TAYCAN_EM_RPM_2", "TAYCAN_ENG_MOTOR_RPM")
FEATURE_RPM_CHANNELS = ("TAYCAN_EM_RPM_1", "TAYCAN_EM_RPM_2")
TORQUE_CHANNELS = ("TAYCAN_EM_TORQ_1", "TAYCAN_EM_TORQ_2")
ISOLATION_CHANNELS = (
    "TAYCAN_HV_ISO_POS_SYS", "TAYCAN_HV_ISO_NEG_SYS",
    "TAYCAN_HVBAT_ISO_POS", "TAYCAN_HVBAT_ISO_NEG",
)
AH_COUNTERS = ("TAYCAN_HVBAT_TOT_AH_DCHRG", "TAYCAN_HVBAT_TOT_AH_CHRG")
KWH_COUNTERS = ("TAYCAN_HVBAT_TOT_KWH_DCHRG", "TAYCAN_HVBAT_TOT_KWH_CHRG")
BASE_OBSERVED_CHANNELS = {
    "TAYCAN_HVBAT_VOLT", "TAYCAN_BMS_I", "TAYCAN_HVBAT_CURRENT",
    "TAYCAN_BMS_SOC", "TAYCAN_HVBAT_SOC_DISP", "TAYCAN_DIFF_MOTOR_T",
    *FEATURE_RPM_CHANNELS, *TORQUE_CHANNELS, *ISOLATION_CHANNELS, *AH_COUNTERS, *KWH_COUNTERS,
}
GROUP_VOLTAGE_CHANNELS = tuple(
    f"TAYCAN_HVBAT_MOD{module}_C{group}_V"
    for module in range(1, 29) for group in range(1, 7)
)
MODULE_TEMP_CHANNELS = tuple(
    f"TAYCAN_HVBAT_MOD{module}_T{sensor}"
    for module in range(1, 29) for sensor in range(1, 4)
)
OBSERVED_CHANNEL_WHITELIST = sorted(BASE_OBSERVED_CHANNELS | set(GROUP_VOLTAGE_CHANNELS) | set(MODULE_TEMP_CHANNELS))

DRAW_SPEC = [
    ("rpm_white_sigma", "rpm_white_sigma_range_rpm"),
    ("rpm_bias_halfwidth", "rpm_bias_halfwidth_range_rpm"),
    ("torque_white_sigma", "torque_white_sigma_range_Nm"),
    ("torque_bias_halfwidth", "torque_bias_halfwidth_range_Nm"),
    ("soc_group_bias_sd", "soc_group_bias_sd_range_pp"),
    ("soc_innovation", "soc_innovation_range_pp_sqrt_s"),
    ("aux_phi", "aux_phi_range_per_second"),
    ("aux_white_sigma", "aux_white_range_W_sqrt_s"),
    ("aux_cap", "aux_cap_range_W"),
]


class GateError(RuntimeError):
    pass


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def sha256_file(path: Path) -> str:
    return sha256_bytes(path.read_bytes())


def git_blob_sha1(data: bytes) -> str:
    header = b"blob " + str(len(data)).encode("ascii") + b"\0"
    return hashlib.sha1(header + data).hexdigest()


def read_json(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except Exception as exc:
        raise GateError(f"JSON inválido ou inacessível: {path}: {exc}") from exc
    if not isinstance(value, dict):
        raise GateError(f"Esperava objeto JSON: {path}")
    return value


def atomic_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temp = path.with_suffix(path.suffix + ".tmp")
    temp.write_text(json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    os.replace(temp, path)


def atomic_csv(path: Path, fieldnames: list[str], rows: Iterable[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temp = path.with_suffix(path.suffix + ".tmp")
    with temp.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames, extrasaction="raise", lineterminator="\n")
        writer.writeheader()
        for row in rows:
            writer.writerow({key: csv_value(row.get(key)) for key in fieldnames})
    os.replace(temp, path)


def csv_value(value: Any) -> Any:
    if value is None:
        return ""
    if isinstance(value, bool):
        return "true" if value else "false"
    if isinstance(value, float):
        if not math.isfinite(value):
            return ""
        return format(value, ".12g")
    return value


def first_existing(candidates: list[Path]) -> Path | None:
    return next((path.resolve() for path in candidates if path.is_file()), None)


def resolve_external_paths(args: argparse.Namespace) -> tuple[Path, Path, Path]:
    model = Path(args.model_py).expanduser().resolve() if args.model_py else first_existing([
        ROOT / "external_data/stage3/taycan_sim/model.py",
        ROOT / "taycan_etapa3/taycan_sim/model.py",
        ROOT / "taycan_etapa4/taycan_sim/model.py",
    ])
    freeze = Path(args.freeze_json).expanduser().resolve() if args.freeze_json else first_existing([
        ROOT / "external_data/stage4/freeze.json",
        ROOT / "taycan_etapa3/freeze.json",
        ROOT / "taycan_etapa4/freeze.json",
    ])
    backend = Path(args.backend_file).expanduser().resolve() if args.backend_file else None
    missing = []
    if model is None:
        missing.append("--model-py (arquivo frozen Stage 3 model.py)")
    if freeze is None:
        missing.append("--freeze-json (freeze.json original da Etapa 4)")
    if backend is None or not backend.is_file():
        missing.append("--backend-file (adapter local conforme docs/methodology/STAGE4_RUNNER_CONTRACT.md)")
    if missing:
        raise GateError("BLOQUEIO: faltam artefatos executáveis: " + "; ".join(missing))
    return model, freeze, backend


def load_and_verify_inputs(model_path: Path, freeze_path: Path, backend_path: Path) -> dict[str, Any]:
    for path in (PREREG_PATH, AMENDMENT_PATH, MANIFEST_PATH, model_path, freeze_path, backend_path):
        if not path.is_file():
            raise GateError(f"BLOQUEIO: arquivo obrigatório ausente: {path}")

    prereg_bytes = PREREG_PATH.read_bytes()
    amendment_bytes = AMENDMENT_PATH.read_bytes()
    manifest_bytes = MANIFEST_PATH.read_bytes()
    model_hash = sha256_file(model_path)
    freeze_hash = sha256_file(freeze_path)

    checks = {
        "prereg_sha256": sha256_bytes(prereg_bytes),
        "prereg_git_blob_sha1": git_blob_sha1(prereg_bytes),
        "amendment_sha256": sha256_bytes(amendment_bytes),
        "amendment_git_blob_sha1": git_blob_sha1(amendment_bytes),
        "manifest_sha256": sha256_bytes(manifest_bytes),
        "manifest_git_blob_sha1": git_blob_sha1(manifest_bytes),
        "model_py_sha256": model_hash,
        "freeze_sha256": freeze_hash,
    }
    for key, expected in EXPECTED.items():
        if checks.get(key) != expected:
            raise GateError(f"FAIL-STOP: {key} divergente; esperado={expected}; encontrado={checks.get(key)}")

    prereg = json.loads(prereg_bytes.decode("utf-8"))
    amendment = json.loads(amendment_bytes.decode("utf-8"))
    if prereg.get("parent_stage4_freeze_sha256") != EXPECTED["freeze_sha256"]:
        raise GateError("FAIL-STOP: parent_stage4_freeze_sha256 não confere com o freeze congelado.")
    if prereg.get("frozen_stage3_model_sha256") != EXPECTED["model_py_sha256"]:
        raise GateError("FAIL-STOP: hash do model.py no pré-registro diverge.")
    parent = amendment.get("parent", {})
    if parent.get("sha256") != EXPECTED["prereg_sha256"] or parent.get("git_blob") != EXPECTED["prereg_git_blob_sha1"]:
        raise GateError("FAIL-STOP: parent do adendo não corresponde ao pré-registro selado.")
    if parent.get("model_py_sha256") != EXPECTED["model_py_sha256"] or parent.get("freeze_sha256") != EXPECTED["freeze_sha256"]:
        raise GateError("FAIL-STOP: parent do adendo não corresponde ao model.py/freeze congelados.")

    backend_hash = sha256_file(backend_path)
    runner_hash = sha256_file(Path(__file__).resolve())
    return {
        "prereg_sha256": checks["prereg_sha256"],
        "prereg_git_blob_sha1": checks["prereg_git_blob_sha1"],
        "amendment_sha256": checks["amendment_sha256"],
        "amendment_git_blob_sha1": checks["amendment_git_blob_sha1"],
        "manifest_sha256": checks["manifest_sha256"],
        "manifest_git_blob_sha1": checks["manifest_git_blob_sha1"],
        "model_py_sha256": model_hash,
        "freeze_sha256": freeze_hash,
        "backend_sha256": backend_hash,
        "runner_sha256": runner_hash,
        "model_py_path": str(model_path),
        "freeze_json_path": str(freeze_path),
        "backend_file_path": str(backend_path),
        "prereg_path": str(PREREG_PATH),
        "amendment_path": str(AMENDMENT_PATH),
        "manifest_path": str(MANIFEST_PATH),
    }


def load_manifest() -> tuple[list[dict[str, str]], dict[str, Any], dict[str, Any]]:
    prereg = read_json(PREREG_PATH)
    amendment = read_json(AMENDMENT_PATH)
    with MANIFEST_PATH.open("r", encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle)
        rows = list(reader)
        columns = reader.fieldnames or []
    expected_columns = amendment["manifest"]["required_manifest_columns"]
    if columns != expected_columns:
        raise GateError(f"FAIL-STOP: colunas do manifesto divergentes: {columns!r}")
    if len(rows) != 2232:
        raise GateError(f"FAIL-STOP: manifesto deveria conter 2232 linhas; contém {len(rows)}.")
    if len({r["episode_id"] for r in rows}) != 2232:
        raise GateError("FAIL-STOP: episode_id duplicado.")
    counts = {split: sum(r["split"] == split for r in rows) for split in SPLITS}
    if counts != {"train": 720, "validation": 360, "test": 1152}:
        raise GateError(f"FAIL-STOP: contagens de split divergentes: {counts}")

    all_seeds: set[int] = set()
    split_seeds: dict[str, set[int]] = {split: set() for split in SPLITS}
    for row in rows:
        if row["hypothesis"] not in HYPOTHESES:
            raise GateError(f"Hipótese não registrada: {row['hypothesis']}")
        if row["counter_source"] not in ("BMS_I", "HVBAT_CURRENT"):
            raise GateError(f"counter_source não permitido: {row['counter_source']}")
        if row["profile"] not in PROFILES:
            raise GateError(f"perfil não registrado: {row['profile']}")
        if int(row["duration_s"]) != DURATION_S or float(row["dt_s"]) != DT_S:
            raise GateError(f"Duração/dt divergente no episódio {row['episode_id']}")
        if row["split"] != "test" and row["profile"] != "NOMINAL_6H":
            raise GateError(f"Perfil deslocado fora do teste: {row['episode_id']}")
        for stream in STREAMS:
            seed = int(row[f"seed_{stream}"])
            if not 0 <= seed <= 0xFFFFFFFF:
                raise GateError(f"Seed fora de uint32: {row['episode_id']} {stream}")
            if seed in all_seeds:
                raise GateError(f"FAIL-STOP: colisão de seed: {seed}")
            all_seeds.add(seed)
            split_seeds[row["split"]].add(seed)
    for i, left in enumerate(SPLITS):
        for right in SPLITS[i + 1:]:
            if split_seeds[left] & split_seeds[right]:
                raise GateError(f"FAIL-STOP: seeds compartilhadas entre {left} e {right}")
    test_profile_counts = {
        profile: sum(r["split"] == "test" and r["profile"] == profile for r in rows)
        for profile in PROFILES
    }
    if test_profile_counts != {"NOMINAL_6H": 576, "SHIFT_REGEN_COLD_6H": 576}:
        raise GateError(f"FAIL-STOP: distribuição de teste por perfil divergente: {test_profile_counts}")
    phis = {float(r["soc_phi_per_s"]) for r in rows}
    expected_phis = set(float(x) for x in prereg["split_policy"]["parameters_assumed"]["soc_phi_grid_per_second"])
    if phis != expected_phis or max(phis) < 0.9995:
        raise GateError(f"FAIL-STOP: grade de phi divergente: {sorted(phis)}")
    return rows, prereg, amendment


class XorShift32:
    def __init__(self, seed: int):
        self.state = (int(seed) & 0xFFFFFFFF) or 0x6D2B79F5

    def uniform(self) -> float:
        x = self.state
        x ^= (x << 13) & 0xFFFFFFFF
        x ^= (x >> 17) & 0xFFFFFFFF
        x ^= (x << 5) & 0xFFFFFFFF
        self.state = x & 0xFFFFFFFF
        return self.state / 4294967296.0


def make_observation_config(row: dict[str, str], prereg: dict[str, Any], seeds: dict[str, int] | None = None,
                           verify_draws: bool = True, sensors_enabled: bool = True) -> dict[str, Any]:
    seed_map = seeds or {stream: int(row[f"seed_{stream}"]) for stream in STREAMS}
    rng = XorShift32(seed_map["nuisance"])
    ranges = prereg["split_policy"]["parameters_assumed"]
    for column, range_key in DRAW_SPEC:
        drawn = ranges[range_key][0] + (ranges[range_key][1] - ranges[range_key][0]) * rng.uniform()
        if verify_draws and abs(drawn - float(row[column])) > 1.1e-8:
            raise GateError(f"FAIL-STOP: nuisance draw não reproduz manifesto: {row['episode_id']} {column}")

    rpm_half = float(row["rpm_bias_halfwidth"])
    torque_half = float(row["torque_bias_halfwidth"])
    rpm_biases = {channel: (2.0 * rng.uniform() - 1.0) * rpm_half for channel in RPM_BIAS_CHANNELS}
    torque_biases = {channel: (2.0 * rng.uniform() - 1.0) * torque_half for channel in TORQUE_CHANNELS}
    soc_bias_seed = rng.state
    return {
        "sensor_noise_enabled": sensors_enabled,
        "rpm_white_sigma_rpm": float(row["rpm_white_sigma"]),
        "rpm_bias_halfwidth_rpm": rpm_half,
        "rpm_persistent_bias_by_channel_rpm": rpm_biases,
        "torque_white_sigma_Nm": float(row["torque_white_sigma"]),
        "torque_bias_halfwidth_Nm": torque_half,
        "torque_persistent_bias_by_channel_Nm": torque_biases,
        "soc_group_bias_sd_pp": float(row["soc_group_bias_sd"]),
        "soc_innovation_pp_sqrt_s": float(row["soc_innovation"]),
        "soc_phi_per_s": float(row["soc_phi_per_s"]),
        "soc_bias_rng_seed_after_channel_biases": soc_bias_seed,
        "aux_phi_per_s": float(row["aux_phi"]),
        "aux_white_sigma_W_sqrt_s": float(row["aux_white_sigma"]),
        "aux_cap_W": float(row["aux_cap"]),
        "acquisition_mode": row["acquisition_mode"],
        "counter_source": row["counter_source"],
        "diff_motor_t_mapping": row["diff_motor_t_mapping"],
        "seeds": {key: int(value) for key, value in seed_map.items()},
        "truth_ablation_allowed": False,
        "persistent_bias_sampling": "Uniform(-halfwidth,+halfwidth), per channel and episode, from nuisance xorshift stream after the nine registered scale draws",
        "white_noise_rng": "seed_observer",
        "auxiliary_rng": "seed_aux",
        "physics_rng": "seed_physics",
    }


def profile_spec(profile_id: str) -> dict[str, Any]:
    if profile_id == "NOMINAL_6H":
        return {
            "id": profile_id, "duration_s": DURATION_S, "dt_s": DT_S, "ambient_target_C": 25.0,
            "traction_torque_scale": 1.0, "regeneration_torque_scale": 1.0,
            "ambient_parameter_candidates": ["coolant_C", "init_module_C"],
            "ambient_shift_not_modeled_allowed": False,
        }
    if profile_id == "SHIFT_REGEN_COLD_6H":
        return {
            "id": profile_id, "duration_s": DURATION_S, "dt_s": DT_S, "ambient_target_C": 10.0,
            "traction_torque_scale": 0.85, "regeneration_torque_scale": 1.5,
            "torque_sign_convention": "negative=regeneration; positive=traction",
            "ambient_parameter_candidates": ["coolant_C", "init_module_C"],
            "ambient_shift_not_modeled_allowed": True,
        }
    raise GateError(f"Perfil desconhecido: {profile_id}")


def scale_signed_torque(torque_nm: float, profile_id: str) -> float:
    """Backend helper: call on each driver torque before model loss calculations."""
    torque = float(torque_nm)
    if profile_id == "SHIFT_REGEN_COLD_6H":
        return torque * (1.5 if torque < 0 else 0.85 if torque > 0 else 1.0)
    if profile_id == "NOMINAL_6H":
        return torque
    raise GateError(f"Perfil desconhecido: {profile_id}")


def load_backend(path: Path):
    spec = importlib.util.spec_from_file_location("taycan_stage4_backend_adapter", path)
    if spec is None or spec.loader is None:
        raise GateError(f"Não foi possível carregar backend adapter: {path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    if not callable(getattr(module, "run_episode", None)):
        raise GateError("Backend deve exportar run_episode(context: dict) -> dict.")
    if getattr(module, "COUNTER_TIMING_VERIFIED", False) is not True:
        raise GateError("BLOQUEIO: backend não declara COUNTER_TIMING_VERIFIED=True; F14/F28 não podem ser usados.")
    if getattr(module, "MODEL_SHA256", None) != EXPECTED["model_py_sha256"]:
        raise GateError("BLOQUEIO: backend não declara o SHA-256 exato do model.py congelado.")
    return module


def finite_number(value: Any) -> float | None:
    if value is None or isinstance(value, bool):
        return None
    try:
        number = float(value)
    except (TypeError, ValueError):
        return None
    return number if math.isfinite(number) else None


def mean(values: list[float]) -> float | None:
    return sum(values) / len(values) if values else None


def sample_sd(values: list[float]) -> float | None:
    if len(values) < 2:
        return None
    avg = mean(values)
    return math.sqrt(sum((x - avg) ** 2 for x in values) / (len(values) - 1))


def quantile_linear(values: list[float], probability: float) -> float | None:
    ordered = sorted(values)
    if not ordered:
        return None
    if len(ordered) == 1:
        return ordered[0]
    pos = (len(ordered) - 1) * probability
    low = int(math.floor(pos))
    high = int(math.ceil(pos))
    if low == high:
        return ordered[low]
    weight = pos - low
    return ordered[low] * (1.0 - weight) + ordered[high] * weight


def slope_ols(x: list[float], y: list[float]) -> float | None:
    pairs = [(a, b) for a, b in zip(x, y) if math.isfinite(a) and math.isfinite(b)]
    if len(pairs) < 2:
        return None
    mx = mean([p[0] for p in pairs])
    my = mean([p[1] for p in pairs])
    den = sum((a - mx) ** 2 for a, _ in pairs)
    if den <= 0:
        return None
    return sum((a - mx) * (b - my) for a, b in pairs) / den


def dot(a: list[float], b: list[float]) -> float:
    return sum(x * y for x, y in zip(a, b))


def inverse_square(matrix: list[list[float]]) -> list[list[float]] | None:
    n = len(matrix)
    aug = [list(map(float, row)) + [1.0 if i == j else 0.0 for j in range(n)] for i, row in enumerate(matrix)]
    scale = max((abs(x) for row in matrix for x in row), default=1.0)
    tol = max(scale * 1e-13, 1e-15)
    for col in range(n):
        pivot = max(range(col, n), key=lambda r: abs(aug[r][col]))
        if abs(aug[pivot][col]) <= tol:
            return None
        aug[col], aug[pivot] = aug[pivot], aug[col]
        divisor = aug[col][col]
        aug[col] = [x / divisor for x in aug[col]]
        for r in range(n):
            if r == col:
                continue
            factor = aug[r][col]
            aug[r] = [x - factor * y for x, y in zip(aug[r], aug[col])]
    return [row[n:] for row in aug]


def ols_fixed_basis(x_rows: list[list[float]], y: list[float]) -> dict[str, Any]:
    """OLS on [1, sum(tau), sum(tau^2), sum(omega), sum(tau*omega)].
    Columns are scaled for numerical stability; rank-deficient coefficients remain NA.
    """
    if len(x_rows) != len(y) or len(y) < 5:
        return {"rank": 0, "beta": None, "residual_sd": None, "condition": None}
    width = 5
    scales = [math.sqrt(sum(row[j] ** 2 for row in x_rows) / len(x_rows)) for j in range(width)]
    if any(not math.isfinite(s) or s <= 0 for s in scales):
        return {"rank": 0, "beta": None, "residual_sd": None, "condition": None}
    columns = [[row[j] / scales[j] for row in x_rows] for j in range(width)]
    qcols: list[list[float]] = []
    rmat = [[0.0] * width for _ in range(width)]
    threshold = math.sqrt(len(y)) * 1e-10
    rank = 0
    for j in range(width):
        v = columns[j][:]
        for i, q in enumerate(qcols):
            coeff = dot(q, v)
            rmat[i][j] = coeff
            v = [vv - coeff * qq for vv, qq in zip(v, q)]
        norm = math.sqrt(dot(v, v))
        if norm <= threshold:
            break
        rmat[j][j] = norm
        qcols.append([vv / norm for vv in v])
        rank += 1
    if rank != width:
        return {"rank": rank, "beta": None, "residual_sd": None, "condition": None}
    rhs = [dot(qcols[j], y) for j in range(width)]
    beta_scaled = [0.0] * width
    for i in range(width - 1, -1, -1):
        remainder = rhs[i] - sum(rmat[i][j] * beta_scaled[j] for j in range(i + 1, width))
        beta_scaled[i] = remainder / rmat[i][i]
    beta = [beta_scaled[j] / scales[j] for j in range(width)]
    fitted = [sum(beta[j] * row[j] for j in range(width)) for row in x_rows]
    residuals = [actual - fit for actual, fit in zip(y, fitted)]
    residual_sd = sample_sd(residuals)
    # Infinity-norm condition estimate of the scaled design's R factor.
    inv_r = inverse_square(rmat)
    if inv_r is None:
        condition = None
    else:
        norm_r = max(sum(abs(x) for x in row) for row in rmat)
        norm_inv = max(sum(abs(x) for x in row) for row in inv_r)
        condition = norm_r * norm_inv
    return {"rank": rank, "beta": beta, "residual_sd": residual_sd, "condition": condition}


def observed_series(rows: list[dict[str, Any]], channel: str) -> tuple[list[float | None], bool]:
    values = [finite_number(row.get(channel)) for row in rows]
    return values, any(value is None for value in values)


def feature_matrix(episode_id: str, rows: list[dict[str, Any]], dt_s: float,
                   counter_timing_verified: bool) -> tuple[dict[str, Any], dict[str, Any]]:
    """Feature extraction receives observed rows only; audit/truth is not an argument."""
    if not rows:
        raise GateError(f"Episódio sem amostras observadas: {episode_id}")
    times_s = []
    for index, row in enumerate(rows):
        times_s.append(finite_number(row.get("time_s")) if finite_number(row.get("time_s")) is not None else index * dt_s)
    times_h = [t / 3600.0 for t in times_s]
    feature_values: dict[str, float | None] = {name: None for name in FEATURE_NAMES}
    masks: dict[str, int] = {f"mask_{code}": 1 for code, _ in FEATURES}
    diagnostics: dict[str, Any] = {"n_steps": len(rows), "dt_s": dt_s}

    def put(code: str, name: str, value: float | None, incomplete: bool = False) -> None:
        feature_values[f"{code}_{name}"] = value if value is not None and math.isfinite(value) else None
        masks[f"mask_{code}"] = 0 if value is not None and math.isfinite(value) and not incomplete else 1

    v, miss_v = observed_series(rows, "TAYCAN_HVBAT_VOLT")
    bms_i, miss_bms_i = observed_series(rows, "TAYCAN_BMS_I")
    hv_i, miss_hv_i = observed_series(rows, "TAYCAN_HVBAT_CURRENT")
    bms_soc, miss_soc = observed_series(rows, "TAYCAN_BMS_SOC")
    diff_temp, miss_diff_temp = observed_series(rows, "TAYCAN_DIFF_MOTOR_T")
    torques = [observed_series(rows, channel) for channel in TORQUE_CHANNELS]
    rpms = [observed_series(rows, channel) for channel in ("TAYCAN_EM_RPM_1", "TAYCAN_EM_RPM_2")]
    r33: list[float | None] = []
    x_design: list[list[float]] = []
    r33_y: list[float] = []
    r33_incomplete = False
    torque_incomplete = False
    rpm_incomplete = False
    sum_tau_sq_series: list[float] = []
    sum_abs_omega_series: list[float] = []
    for i in range(len(rows)):
        tau_values = [torques[0][0][i], torques[1][0][i]]
        rpm_values = [rpms[0][0][i], rpms[1][0][i]]
        if any(value is None for value in tau_values):
            torque_incomplete = True
        else:
            tau1, tau2 = [float(x) for x in tau_values]
            sum_tau_sq_series.append(tau1 * tau1 + tau2 * tau2)
        if any(value is None for value in rpm_values):
            rpm_incomplete = True
        else:
            rpm1, rpm2 = [float(x) for x in rpm_values]
            sum_abs_omega_series.append(abs(2 * math.pi * rpm1 / 60.0) + abs(2 * math.pi * rpm2 / 60.0))
        torque_rpm = [*tau_values, *rpm_values]
        if any(value is None for value in torque_rpm):
            sum_tau = sum_tau_sq = sum_omega = sum_tau_omega = None
        else:
            tau1, tau2, rpm1, rpm2 = [float(x) for x in torque_rpm]
            omega1, omega2 = 2 * math.pi * rpm1 / 60.0, 2 * math.pi * rpm2 / 60.0
            sum_tau = tau1 + tau2
            sum_omega = omega1 + omega2
            sum_tau_sq = tau1 * tau1 + tau2 * tau2
            sum_tau_omega = tau1 * omega1 + tau2 * omega2
        if v[i] is None or bms_i[i] is None or any(value is None for value in torque_rpm):
            r33.append(None)
            r33_incomplete = True
            continue
        voltage, current = float(v[i]), float(bms_i[i])
        residual = voltage * current - sum_tau_omega
        r33.append(residual)
        r33_y.append(residual)
        x_design.append([1.0, sum_tau, sum_tau_sq, sum_omega, sum_tau_omega])
    r33_valid = [x for x in r33 if x is not None]
    put("F01", "mean_R33_W", mean(r33_valid), r33_incomplete)
    put("F02", "sd_R33_W", sample_sd(r33_valid), r33_incomplete)
    fit = ols_fixed_basis(x_design, r33_y)
    diagnostics["r33_regression_rank"] = fit["rank"]
    diagnostics["r33_condition_number_inf_estimate_scaled_design"] = fit["condition"]
    diagnostics["r33_regression_n"] = len(r33_y)
    diagnostics["r33_regularizer_declared_but_not_applied_to_rank_deficient_OLS"] = REGULARIZER
    if fit["beta"] is not None:
        beta = fit["beta"]
        put("F03", "beta_tau2_W_per_Nm2", beta[2], r33_incomplete)
        put("F04", "beta_omega_W_per_rad_s", beta[3], r33_incomplete)
        put("F05", "sd_regressed_R33_W", fit["residual_sd"], r33_incomplete)
        put("F26", "beta_tau_W_per_Nm", beta[1], r33_incomplete)
        put("F27", "beta_tauomega_dimensionless", beta[4], r33_incomplete)
    else:
        for code, name in (("F03", "beta_tau2_W_per_Nm2"), ("F04", "beta_omega_W_per_rad_s"),
                           ("F05", "sd_regressed_R33_W"), ("F26", "beta_tau_W_per_Nm"),
                           ("F27", "beta_tauomega_dimensionless")):
            put(code, name, None, True)

    current_diff = [a - b for a, b in zip(bms_i, hv_i) if a is not None and b is not None]
    put("F06", "mean_current_diff_A", mean(current_diff), miss_bms_i or miss_hv_i)
    put("F07", "sd_current_diff_A", sample_sd(current_diff), miss_bms_i or miss_hv_i)
    spread_by_time: list[float] = []
    pack_consistency: list[float] = []
    group_voltage_incomplete = False
    for i in range(len(rows)):
        group_values = [finite_number(rows[i].get(channel)) for channel in GROUP_VOLTAGE_CHANNELS]
        if any(x is None for x in group_values) or v[i] is None:
            group_voltage_incomplete = True
            continue
        values = [float(x) for x in group_values]
        spread_by_time.append(max(values) - min(values))
        pack_consistency.append(float(v[i]) - sum(values))
    put("F08", "mean_module_pair_voltage_spread_V", mean(spread_by_time), group_voltage_incomplete)
    put("F09", "p95_module_pair_voltage_spread_V", quantile_linear(spread_by_time, 0.95), group_voltage_incomplete)
    put("F10", "mean_pack_group_voltage_consistency_V", mean(pack_consistency), group_voltage_incomplete)
    put("F11", "sd_pack_group_voltage_consistency_V", sample_sd(pack_consistency), group_voltage_incomplete)
    put("F12", "mean_BMS_SOC_pct", mean([x for x in bms_soc if x is not None]), miss_soc)
    soc_pairs = [(times_h[i], x) for i, x in enumerate(bms_soc) if x is not None]
    put("F13", "SOC_slope_pct_per_hour", slope_ols([x for x, _ in soc_pairs], [y for _, y in soc_pairs]), miss_soc)

    ah_dis, miss_ah_dis = observed_series(rows, AH_COUNTERS[0])
    ah_chg, miss_ah_chg = observed_series(rows, AH_COUNTERS[1])
    ah_value = None
    ah_invalid = miss_ah_dis or miss_ah_chg or miss_bms_i or not counter_timing_verified
    if not ah_invalid and len(rows) >= 2:
        delta_dis, delta_chg = ah_dis[-1] - ah_dis[0], ah_chg[-1] - ah_chg[0]
        if delta_dis < -1e-8 or delta_chg < -1e-8:
            ah_invalid = True
        else:
            integral_ah = sum(float(bms_i[i]) * (finite_number(rows[i].get("dt_s")) or dt_s) / 3600.0 for i in range(len(rows)))
            ah_value = delta_dis - delta_chg - integral_ah
    put("F14", "net_Ah_counter_minus_BMS_integral_Ah", ah_value, ah_invalid)

    module_thermal_spreads: list[float] = []
    within_module_spreads: list[float] = []
    temp_incomplete = False
    for i in range(len(rows)):
        module_means = []
        module_spreads = []
        for module in range(1, 29):
            vals = [finite_number(rows[i].get(f"TAYCAN_HVBAT_MOD{module}_T{sensor}")) for sensor in range(1, 4)]
            if any(x is None for x in vals):
                temp_incomplete = True
                continue
            fvals = [float(x) for x in vals]
            module_means.append(mean(fvals))
            module_spreads.append(max(fvals) - min(fvals))
        if len(module_means) == 28:
            module_thermal_spreads.append(max(module_means) - min(module_means))
        if module_spreads:
            within_module_spreads.append(max(module_spreads))
        if len(module_means) != 28 or len(module_spreads) != 28:
            temp_incomplete = True
    put("F15", "mean_thermal_spread_C", mean(module_thermal_spreads), temp_incomplete)
    put("F16", "p95_thermal_spread_C", quantile_linear(module_thermal_spreads, 0.95), temp_incomplete)
    temp_structural_missing = any(all(finite_number(row.get(channel)) is None for row in rows)
                                  for channel in MODULE_TEMP_CHANNELS)
    f17_value = max(within_module_spreads) if within_module_spreads and not temp_structural_missing else None
    put("F17", "max_internal_module_T_spread_C", f17_value, temp_incomplete)
    put("F18", "mean_DIFF_MOTOR_T_C", mean([x for x in diff_temp if x is not None]), miss_diff_temp)
    diff_pairs = [(times_h[i], x) for i, x in enumerate(diff_temp) if x is not None]
    put("F19", "slope_DIFF_MOTOR_T_C_per_hour", slope_ols([x for x, _ in diff_pairs], [y for _, y in diff_pairs]), miss_diff_temp)

    power = [float(vv) * float(ii) if vv is not None and ii is not None else None for vv, ii in zip(v, bms_i)]
    p20 = None
    p20_incomplete = False
    integral = 0.0
    n_intervals = 0
    for i in range(len(power) - 1):
        dt = times_s[i + 1] - times_s[i]
        if power[i] is None or power[i + 1] is None or dt <= 0:
            p20_incomplete = True
            continue
        integral += (float(power[i]) + float(power[i + 1])) * 0.5 * dt / 3600000.0
        n_intervals += 1
    if n_intervals:
        p20 = integral
    put("F20", "integrated_observed_HV_kWh", p20, p20_incomplete or miss_v or miss_bms_i)
    valid_power = [x for x in power if x is not None]
    put("F21", "negative_DC_power_fraction",
        (sum(x < 0 for x in valid_power) / len(valid_power)) if valid_power else None,
        len(valid_power) != len(power))

    isolation_min: list[float] = []
    isolation_incomplete = False
    for row in rows:
        vals = [finite_number(row.get(channel)) for channel in ISOLATION_CHANNELS]
        if any(x is None for x in vals):
            isolation_incomplete = True
            continue
        isolation_min.append(min(float(x) for x in vals))
    put("F22", "mean_min_isolation_kohm", mean(isolation_min), isolation_incomplete)
    put("F23", "min_isolation_kohm", min(isolation_min) if isolation_min else None, isolation_incomplete)
    put("F24", "time_mean_sum_torque_squared", mean(sum_tau_sq_series), torque_incomplete)
    put("F25", "time_mean_sum_abs_angular_speed", mean(sum_abs_omega_series), rpm_incomplete)

    kwh_dis, miss_kwh_dis = observed_series(rows, KWH_COUNTERS[0])
    kwh_chg, miss_kwh_chg = observed_series(rows, KWH_COUNTERS[1])
    kwh_value = None
    kwh_invalid = miss_kwh_dis or miss_kwh_chg or miss_v or miss_bms_i or not counter_timing_verified
    if not kwh_invalid and len(rows) >= 2:
        delta_dis, delta_chg = kwh_dis[-1] - kwh_dis[0], kwh_chg[-1] - kwh_chg[0]
        if delta_dis < -1e-8 or delta_chg < -1e-8:
            kwh_invalid = True
        else:
            integral_kwh = sum(float(v[i]) * float(bms_i[i]) * (finite_number(rows[i].get("dt_s")) or dt_s) / 3600000.0
                               for i in range(len(rows)))
            kwh_value = delta_dis - delta_chg - integral_kwh
    put("F28", "net_kWh_counter_minus_BMS_DC_integral_kWh", kwh_value, kwh_invalid)

    feature_row = {"episode_id": episode_id, **feature_values, **masks}
    return feature_row, diagnostics


def load_backend_result(context: dict[str, Any]) -> dict[str, Any]:
    backend_path = Path(context["artifacts"]["backend_file_path"])
    backend = load_backend(backend_path)
    started = time.perf_counter()
    result = backend.run_episode(context)
    runtime = time.perf_counter() - started
    if not isinstance(result, dict) or not isinstance(result.get("audit"), dict):
        raise GateError("Backend retornou formato inválido: esperado dict com audit.")
    audit = result["audit"]
    if audit.get("model_sha256") != EXPECTED["model_py_sha256"]:
        raise GateError("FAIL-STOP: backend executou modelo cujo hash não é o congelado.")
    if audit.get("counter_timing_verified") is not True:
        raise GateError("FAIL-STOP: timing dos contadores Ah/kWh não foi verificado pelo backend.")
    if not isinstance(audit.get("ambient_shift_applied"), bool):
        raise GateError("FAIL-STOP: backend deve declarar ambient_shift_applied como Boolean.")
    if audit.get("profile_id") != context["profile"]["id"]:
        raise GateError("FAIL-STOP: backend aplicou perfil diferente do solicitado.")
    applied_dt = finite_number(audit.get("dt_s"))
    if applied_dt is None or abs(applied_dt - float(context["profile"]["dt_s"])) > 1e-12:
        raise GateError("FAIL-STOP: dt ausente ou divergente do manifesto.")
    applied_charge = finite_number(audit.get("charge_power_kw_applied"))
    if applied_charge is None or abs(applied_charge - float(context["charge_power_kw"])) > 1e-8:
        raise GateError("FAIL-STOP: potência de carga ausente ou divergente da calibração congelada.")
    if audit.get("seeds_applied") != context["seeds"]:
        raise GateError("FAIL-STOP: seeds aplicadas pelo backend divergem do contexto.")
    profile_id = context["profile"]["id"]
    expected_traction = 0.85 if profile_id == "SHIFT_REGEN_COLD_6H" else 1.0
    expected_regen = 1.5 if profile_id == "SHIFT_REGEN_COLD_6H" else 1.0
    applied_traction = finite_number(audit.get("traction_torque_scale_applied"))
    applied_regen = finite_number(audit.get("regeneration_torque_scale_applied"))
    if applied_traction is None or abs(applied_traction - expected_traction) > 1e-12:
        raise GateError("FAIL-STOP: escala de torque de tração ausente ou divergente.")
    if applied_regen is None or abs(applied_regen - expected_regen) > 1e-12:
        raise GateError("FAIL-STOP: escala de regeneração ausente ou divergente.")
    if context["phase"] == "episode":
        for key, expected in (("acquisition_mode_applied", context["observation_config"]["acquisition_mode"]),
                              ("counter_source_applied", context["observation_config"]["counter_source"]),
                              ("diff_motor_t_mapping_applied", context["observation_config"]["diff_motor_t_mapping"])):
            if audit.get(key) != expected:
                raise GateError(f"FAIL-STOP: {key} ausente/divergente: esperado={expected!r}, obtido={audit.get(key)!r}")
        hypothesis = context["episode"]["hypothesis"]
        if hypothesis != "H00" and audit.get("fault_injection_applied") is not True:
            raise GateError(f"FAIL-STOP: falha {hypothesis} não foi confirmada como injetada.")
        if hypothesis == "H00" and audit.get("fault_injection_applied") not in (False, None):
            raise GateError("FAIL-STOP: H00 reportou injeção de falha.")
        expected_injected = finite_number(context["episode"].get("injected_severity"))
        if expected_injected is None:
            expected_injected = 0.0 if hypothesis == "H00" else float(context["episode"]["severity"])
        applied_injected = finite_number(audit.get("injected_severity_applied"))
        if applied_injected is None or abs(applied_injected - expected_injected) > 1e-9:
            raise GateError(f"FAIL-STOP: severidade injetada diverge: esperado={expected_injected}, obtido={applied_injected}")
        if not isinstance(result.get("observed_rows"), list) or not result["observed_rows"]:
            raise GateError("Backend não retornou série observada para o episódio.")
    return {"result": result, "runtime_s": runtime}


def soc_summary(audit: dict[str, Any]) -> dict[str, Any]:
    soc = [finite_number(x) for x in audit.get("soc_true_percent", [])]
    valid = [float(x) for x in soc if x is not None]
    if not valid or len(valid) != len(soc):
        raise GateError("Backend não retornou uma trajetória SOC verdadeira completa e finita.")
    initial = finite_number(audit.get("soc_initial_percent"))
    if initial is None or abs(initial - SOC_INITIAL) > 1e-6:
        raise GateError(f"SOC inicial configurado diverge do pré-registro: {initial} != {SOC_INITIAL}")
    times = audit.get("soc_time_s")
    if not isinstance(times, list) or len(times) != len(soc) or any(finite_number(t) is None for t in times):
        raise GateError("Backend deve retornar soc_time_s finito e alinhado com soc_true_percent.")
    return {
        "soc_true_min_pct": min(valid),
        "soc_true_max_pct": max(valid),
        "soc_true_final_pct": valid[-1],
        "soc_true_initial_pct": initial,
        "soc_true_final_residual_pp": valid[-1] - initial,
        "soc_true_window_violation": min(valid) < SOC_WINDOW[0] or max(valid) > SOC_WINDOW[1],
        "soc_true_samples": len(valid),
    }


def write_soc_trajectory(path: Path, rows: list[dict[str, Any]], audit: dict[str, Any], dt_s: float) -> None:
    truth = [finite_number(x) for x in audit.get("soc_true_percent", [])]
    if len(truth) != len(rows):
        raise GateError(f"Trajetória SOC verdadeira não alinhada: {len(truth)} != {len(rows)}")
    observed = [finite_number(row.get("TAYCAN_BMS_SOC")) for row in rows]
    path.parent.mkdir(parents=True, exist_ok=True)
    temp = path.with_suffix(path.suffix + ".tmp")
    with temp.open("wb") as raw:
        with gzip.GzipFile(filename="", mode="wb", fileobj=raw, mtime=0) as zipped:
            with io.TextIOWrapper(zipped, encoding="utf-8", newline="") as text_handle:
                writer = csv.writer(text_handle, lineterminator="\n")
                writer.writerow(["time_s", "SOC_true_percent_for_audit_only", "SOC_observed_BMS_SOC_percent"])
                for i, (truth_value, observed_value) in enumerate(zip(truth, observed)):
                    time_value = finite_number(rows[i].get("time_s"))
                    if time_value is None:
                        time_value = i * dt_s
                    writer.writerow([format(time_value, ".8f"),
                                     "" if truth_value is None else format(truth_value, ".8f"),
                                     "" if observed_value is None else format(observed_value, ".8f")])
    os.replace(temp, path)


def atomic_single_row_csv(path: Path, row: dict[str, Any], columns: list[str]) -> None:
    atomic_csv(path, columns, [row])


def run_worker(context_path: Path) -> int:
    context = read_json(context_path)
    artifacts = context["artifacts"]
    model_path = Path(artifacts["model_py_path"])
    freeze_path = Path(artifacts["freeze_json_path"])
    backend_path = Path(artifacts["backend_file_path"])
    current_hashes = load_and_verify_inputs(model_path, freeze_path, backend_path)
    for key, value in artifacts.items():
        if key in current_hashes:
            if current_hashes.get(key) != value:
                raise GateError(f"FAIL-STOP: hash de entrada mudou no worker: {key}")
        elif key == "m01_i01_energy_match_receipt_sha256":
            receipt_path = Path(context.get("energy_match_receipt_path", ""))
            if not receipt_path.is_file() or sha256_file(receipt_path) != value:
                raise GateError("FAIL-STOP: recibo de pareamento energético M01/I01 ausente ou alterado.")
            current_hashes[key] = value
        elif key.endswith("_sha256") or key.endswith("_git_blob_sha1"):
            raise GateError(f"FAIL-STOP: hash de entrada sem verificação disponível: {key}")
    outcome = load_backend_result(context)
    result, runtime = outcome["result"], outcome["runtime_s"]
    audit = result["audit"]
    worker_result_path = Path(context["worker_result_path"])
    common = {
        "job_id": context["job_id"],
        "phase": context["phase"],
        "profile_id": context["profile"]["id"],
        "charge_power_kw": context["charge_power_kw"],
        "runtime_s": runtime,
        "input_hashes": current_hashes,
        "audit": {k: v for k, v in audit.items() if k not in ("soc_true_percent", "soc_time_s")},
    }
    if context["phase"] == "charge_calibration":
        summary = soc_summary(audit)
        trajectory_path = Path(context["run_dir"]) / "soc_trajectories" / f"{context['job_id']}.csv.gz"
        trajectory_path.parent.mkdir(parents=True, exist_ok=True)
        temp = trajectory_path.with_suffix(trajectory_path.suffix + ".tmp")
        truth = [finite_number(x) for x in audit.get("soc_true_percent", [])]
        with temp.open("wb") as raw:
            with gzip.GzipFile(filename="", mode="wb", fileobj=raw, mtime=0) as zipped:
                with io.TextIOWrapper(zipped, encoding="utf-8", newline="") as text_handle:
                    writer = csv.writer(text_handle, lineterminator="\n")
                    writer.writerow(["time_s", "SOC_true_percent_for_audit_only"])
                    soc_times = [finite_number(x) for x in audit.get("soc_time_s", [])]
                    if len(soc_times) != len(truth) or any(x is None for x in soc_times):
                        raise GateError("Trajetória de calibração sem soc_time_s finito/alinhado.")
                    for time_value, value in zip(soc_times, truth):
                        writer.writerow([format(float(time_value), ".8f"),
                                         "" if value is None else format(value, ".8f")])
        os.replace(temp, trajectory_path)
        atomic_json(worker_result_path, {**common, **summary,
                                         "soc_trajectory_gz": str(trajectory_path),
                                         "soc_trajectory_gz_sha256": sha256_file(trajectory_path)})
        return 0

    episode = context["episode"]
    rows = result["observed_rows"]
    # Feature input is explicitly projected onto the registered observed-channel whitelist.
    projected = []
    for row in rows:
        if not isinstance(row, dict):
            raise GateError("Linha observada não é um objeto.")
        out = {key: row.get(key) for key in OBSERVED_CHANNEL_WHITELIST if key in row}
        for timing_key in ("time_s", "dt_s"):
            if timing_key in row:
                out[timing_key] = row[timing_key]
        projected.append(out)
    audit_times = [finite_number(x) for x in audit.get("soc_time_s", [])]
    if len(audit_times) != len(projected) or any(x is None for x in audit_times):
        raise GateError("FAIL-STOP: grade temporal SOC não está alinhada à série observada.")
    for i, projected_row in enumerate(projected):
        observed_time = finite_number(projected_row.get("time_s"))
        if observed_time is not None and abs(observed_time - float(audit_times[i])) > 1e-6:
            raise GateError(f"FAIL-STOP: time_s observado diverge da grade física no índice {i}.")
        projected_row["time_s"] = float(audit_times[i])
        if finite_number(projected_row.get("dt_s")) is None:
            projected_row["dt_s"] = float(episode["dt_s"])
    features, diagnostics = feature_matrix(episode["episode_id"], projected, float(episode["dt_s"]),
                                           counter_timing_verified=True)
    soc = soc_summary(audit)
    obs_soc = [finite_number(row.get("TAYCAN_BMS_SOC")) for row in projected]
    obs_soc_valid = [float(x) for x in obs_soc if x is not None]
    obs_min = min(obs_soc_valid) if obs_soc_valid else None
    obs_max = max(obs_soc_valid) if obs_soc_valid else None
    metadata = {
        "episode_id": episode["episode_id"],
        "hypothesis": episode["hypothesis"],
        "split": episode["split"],
        "severity": episode["severity"],
        "injected_severity": finite_number(episode.get("injected_severity")),
        "energy_match_status": episode.get("energy_match_status", "NOT_APPLICABLE"),
        "energy_match_mismatch_pct": finite_number(episode.get("energy_match_mismatch_pct")),
        "energy_match_delta_E_motor_J": finite_number(episode.get("delta_E_motor_J")),
        "energy_match_delta_E_inverter_J": finite_number(episode.get("delta_E_inverter_J")),
        "energy_match_receipt_sha256": context.get("energy_match_receipt_sha256", ""),
        "severity_quota": episode["severity_quota"],
        "replicate": episode["replicate"],
        "block": episode["block"],
        "profile": episode["profile"],
        "duration_s": int(episode["duration_s"]),
        "dt_s": float(episode["dt_s"]),
        "acquisition_mode": episode["acquisition_mode"],
        "counter_source": episode["counter_source"],
        "diff_motor_t_mapping": episode["diff_motor_t_mapping"],
        "soc_phi_per_s": float(episode["soc_phi_per_s"]),
        "rpm_white_sigma": float(episode["rpm_white_sigma"]),
        "rpm_bias_halfwidth": float(episode["rpm_bias_halfwidth"]),
        "torque_white_sigma": float(episode["torque_white_sigma"]),
        "torque_bias_halfwidth": float(episode["torque_bias_halfwidth"]),
        "soc_group_bias_sd": float(episode["soc_group_bias_sd"]),
        "soc_innovation": float(episode["soc_innovation"]),
        "aux_phi": float(episode["aux_phi"]),
        "aux_white_sigma": float(episode["aux_white_sigma"]),
        "aux_cap": float(episode["aux_cap"]),
        **{f"seed_{stream}": int(episode[f"seed_{stream}"]) for stream in STREAMS},
        "charge_power_fixed_kW": float(context["charge_power_kw"]),
        "runtime_s": runtime,
        "n_steps": len(projected),
        **soc,
        "soc_observed_min_pct": obs_min,
        "soc_observed_max_pct": obs_max,
        "soc_observed_window_violation": (obs_min is not None and obs_min < SOC_WINDOW[0]) or
                                         (obs_max is not None and obs_max > SOC_WINDOW[1]),
        "ambient_shift_not_modeled": episode["profile"] == "SHIFT_REGEN_COLD_6H" and
                                     audit.get("ambient_shift_applied") is not True,
        "ambient_shift_applied": audit.get("ambient_shift_applied") is True,
        "counter_timing_verified": audit.get("counter_timing_verified") is True,
        "r33_regression_rank": diagnostics["r33_regression_rank"],
        "r33_condition_number_inf_estimate_scaled_design": diagnostics["r33_condition_number_inf_estimate_scaled_design"],
        "r33_regression_n": diagnostics["r33_regression_n"],
        "feature_diagnostics_json": json.dumps(diagnostics, sort_keys=True),
        "input_hashes_json": json.dumps(current_hashes, sort_keys=True),
        "audit_flags_json": json.dumps({k: v for k, v in audit.items() if k not in ("soc_true_percent", "soc_time_s")}, sort_keys=True),
    }
    run_dir = Path(context["run_dir"])
    feature_path = run_dir / "episode_features" / f"{episode['episode_id']}.csv"
    metadata_path = run_dir / "episode_metadata" / f"{episode['episode_id']}.json"
    trajectory_path = run_dir / "soc_trajectories" / f"{episode['episode_id']}.csv.gz"
    log_path = run_dir / "logs" / f"{episode['episode_id']}.json"
    atomic_single_row_csv(feature_path, features, ["episode_id", *FEATURE_NAMES, *MASK_NAMES])
    atomic_json(metadata_path, metadata)
    write_soc_trajectory(trajectory_path, projected, audit, float(episode["dt_s"]))
    run_log = {
        "status": "EPISODE_COMPLETE", "episode_id": episode["episode_id"],
        "input_hashes": current_hashes, "runtime_s": runtime,
        "feature_csv_sha256": sha256_file(feature_path),
        "metadata_json_sha256": sha256_file(metadata_path),
        "soc_trajectory_gz_sha256": sha256_file(trajectory_path),
        "audit_flags": {k: v for k, v in audit.items() if k not in ("soc_true_percent", "soc_time_s")},
    }
    atomic_json(log_path, run_log)
    done = {
        "status": "EPISODE_COMPLETE",
        "episode_id": episode["episode_id"],
        "input_hashes": current_hashes,
        "feature_csv_sha256": sha256_file(feature_path),
        "metadata_json_sha256": sha256_file(metadata_path),
        "soc_trajectory_gz_sha256": sha256_file(trajectory_path),
        "run_log_sha256": sha256_file(log_path),
        "runtime_s": runtime,
    }
    done_path = run_dir / "done" / f"{episode['episode_id']}.json"
    atomic_json(done_path, done)
    atomic_json(worker_result_path, {"job_id": context["job_id"], "status": "EPISODE_COMPLETE",
                                     "episode_id": episode["episode_id"], "runtime_s": runtime,
                                     "done_receipt": str(done_path), "input_hashes": current_hashes})
    return 0


def calibration_seeds(profile_id: str, manifest_seeds: set[int]) -> dict[str, int]:
    """Fixed, independent calibration namespace; shared across bisection points for common random numbers."""
    seeds = {}
    for stream in STREAMS:
        text = f"TAYCAN4R|CALIBRATION|{profile_id}|{stream}"
        seeds[stream] = int(hashlib.sha256(text.encode("utf-8")).hexdigest()[:8], 16)
    if len(set(seeds.values())) != len(STREAMS):
        raise GateError(f"FAIL-STOP: colisão interna de seeds de calibração: {profile_id}")
    collision = set(seeds.values()) & manifest_seeds
    if collision:
        raise GateError(f"FAIL-STOP: seed de calibração colide com manifesto: {sorted(collision)}")
    return seeds


def run_subprocess_job(context: dict[str, Any], output_root: Path) -> dict[str, Any]:
    temp_dir = output_root / "worker_contexts"
    temp_dir.mkdir(parents=True, exist_ok=True)
    job_id = context["job_id"]
    context_path = temp_dir / f"{job_id}.json"
    result_path = output_root / "worker_results" / f"{job_id}.json"
    context["worker_result_path"] = str(result_path)
    atomic_json(context_path, context)
    command = [sys.executable, str(Path(__file__).resolve()), "--worker-context", str(context_path)]
    completed = subprocess.run(command, text=True, capture_output=True)
    if completed.returncode != 0:
        log_path = output_root / "logs" / f"{job_id}.failure.json"
        atomic_json(log_path, {"job_id": job_id, "returncode": completed.returncode,
                               "stdout": completed.stdout, "stderr": completed.stderr,
                               "context_sha256": sha256_file(context_path),
                               "input_hashes": context["artifacts"]})
        raise GateError(f"Worker falhou ({job_id}, código {completed.returncode}). Log: {log_path}\n"
                        f"STDERR:\n{completed.stderr[-4000:]}")
    if not result_path.is_file():
        raise GateError(f"Worker terminou sem recibo: {result_path}")
    return read_json(result_path)


def base_context(episode: dict[str, str], phase: str, profile_id: str, charge_kw: float,
                 artifacts: dict[str, Any], prereg: dict[str, Any], seeds: dict[str, int],
                 run_dir: Path, verify_manifest_draws: bool = True) -> dict[str, Any]:
    obs = make_observation_config(episode, prereg, seeds=seeds, verify_draws=verify_manifest_draws,
                                  sensors_enabled=(phase == "episode"))
    if phase == "charge_calibration":
        obs["sensor_noise_enabled"] = False
        obs["auxiliary_process_enabled"] = True
        obs["truth_ablation_allowed"] = False
    else:
        obs["sensor_noise_enabled"] = True
        obs["auxiliary_process_enabled"] = True
    return {
        "job_id": "",
        "phase": phase,
        "episode": episode,
        "profile": profile_spec(profile_id),
        "charge_power_kw": float(charge_kw),
        "seeds": {key: int(value) for key, value in seeds.items()},
        "observation_config": obs,
        "observed_channel_whitelist": OBSERVED_CHANNEL_WHITELIST,
        "artifacts": artifacts,
        "run_dir": str(run_dir),
        "calibration_policy": {
            "training_only_hypothesis": "H00",
            "soc_initial_percent": SOC_INITIAL,
            "soc_window_percent": list(SOC_WINDOW),
            "charging_boundary": "negative battery-side DC power before electrical balance; no OBC subsystem",
        },
    }


def load_cached_calibration(path: Path, artifacts: dict[str, Any]) -> dict[str, Any] | None:
    if not path.is_file():
        return None
    receipt = read_json(path)
    if receipt.get("input_hashes") != artifacts or receipt.get("status") != "CHARGE_CALIBRATION_CONVERGED":
        raise GateError("BLOQUEIO: recibo de calibração existente não corresponde aos hashes atuais; não sobrescrever.")
    profiles = receipt.get("profiles", {})
    if set(profiles) != set(PROFILES):
        raise GateError("BLOQUEIO: recibo de calibração não contém exatamente os dois perfis.")
    for profile_id, values in profiles.items():
        residual = finite_number(values.get("final_soc_residual_pp"))
        soc_min = finite_number(values.get("soc_true_min_pct"))
        soc_max = finite_number(values.get("soc_true_max_pct"))
        if residual is None or abs(residual) > SOC_FINAL_TOLERANCE_PP or soc_min is None or soc_max is None or soc_min < SOC_WINDOW[0] or soc_max > SOC_WINDOW[1]:
            raise GateError(f"BLOQUEIO: recibo de calibração não satisfaz o critério em {profile_id}.")
    return receipt


def calibrate_profiles(rows: list[dict[str, str]], prereg: dict[str, Any], artifacts: dict[str, Any],
                       backend_path: Path, output_root: Path) -> dict[str, Any]:
    receipt_path = output_root / "calibration" / "charge_calibration_receipt.json"
    cached = load_cached_calibration(receipt_path, artifacts)
    if cached:
        return cached

    train_h00 = next((row for row in rows if row["hypothesis"] == "H00" and row["split"] == "train"), None)
    if train_h00 is None:
        raise GateError("BLOQUEIO: manifesto sem H00 de treino para calibração.")
    manifest_seeds = {int(row[f"seed_{stream}"]) for row in rows for stream in STREAMS}
    trace_all = {}
    fixed = {}
    used_calibration_seeds: set[int] = set()
    for profile_id in PROFILES:
        seeds = calibration_seeds(profile_id, manifest_seeds)
        if used_calibration_seeds.intersection(seeds.values()):
            raise GateError("FAIL-STOP: colisão de seed entre perfis de calibração.")
        used_calibration_seeds.update(seeds.values())
        profile_trace = []
        cache_dir = output_root / "calibration" / "runs"
        cache_dir.mkdir(parents=True, exist_ok=True)

        def evaluate(power_kw: float, label: str) -> dict[str, Any]:
            job_id = f"CAL_{profile_id}_{label}_{power_kw:.9f}".replace(".", "p")
            cache_path = cache_dir / f"{job_id}.json"
            if cache_path.is_file():
                cached_run = read_json(cache_path)
                if cached_run.get("input_hashes") != artifacts or cached_run.get("seeds") != seeds or \
                   abs(float(cached_run.get("charge_power_kw", math.nan)) - power_kw) > 1e-10:
                    raise GateError(f"BLOQUEIO: log de calibração incompatível: {cache_path}")
                return cached_run
            context = base_context(train_h00, "charge_calibration", profile_id, power_kw, artifacts,
                                   prereg, seeds, output_root / "calibration", verify_manifest_draws=False)
            context["job_id"] = job_id
            context["calibration_reference"] = {
                "hypothesis": "H00", "source_split": "train", "manifest_episode_id": train_h00["episode_id"],
                "seed_policy": "SHA256('TAYCAN4R|CALIBRATION|<profile>|<stream>') first 8 hex as uint32",
                "same_seeds_across_bisection_points": True,
            }
            result = run_subprocess_job(context, output_root)
            record = {**result, "input_hashes": artifacts, "seeds": seeds, "charge_power_kw": power_kw,
                      "profile_id": profile_id, "evaluation_label": label}
            atomic_json(cache_path, record)
            return record

        low, high = BISECTION_BRACKET_KW
        low_eval = evaluate(low, "bracket_low")
        high_eval = evaluate(high, "bracket_high")
        low_res = float(low_eval["soc_true_final_residual_pp"])
        high_res = float(high_eval["soc_true_final_residual_pp"])
        profile_trace.extend([low_eval, high_eval])
        if low_res > 0 or high_res < 0 or low_res * high_res > 0:
            trace_all[profile_id] = {"status": "BRACKET_FAILURE", "trace": profile_trace}
            atomic_json(output_root / "calibration" / "charge_calibration_trace.json", trace_all)
            raise GateError(f"BLOQUEIO: bissecção sem bracket de raiz para {profile_id}; residuals={low_res, high_res}")
        converged = None
        for iteration in range(1, BISECTION_MAX + 1):
            midpoint = (low + high) / 2.0
            ev = evaluate(midpoint, f"iter_{iteration:02d}")
            ev["iteration"] = iteration
            profile_trace.append(ev)
            within = (float(ev["soc_true_min_pct"]) >= SOC_WINDOW[0] and
                      float(ev["soc_true_max_pct"]) <= SOC_WINDOW[1])
            residual = float(ev["soc_true_final_residual_pp"])
            if iteration >= BISECTION_MIN and abs(residual) <= SOC_FINAL_TOLERANCE_PP and within:
                converged = ev
                break
            if residual < 0:
                low = midpoint
            else:
                high = midpoint
        trace_all[profile_id] = {
            "status": "CONVERGED" if converged else "NONCONVERGENCE",
            "bracket_initial_kW": [BISECTION_BRACKET_KW[0], BISECTION_BRACKET_KW[1]],
            "iterations": len([x for x in profile_trace if x.get("iteration")]),
            "trace": profile_trace,
            "selected": converged,
        }
        atomic_json(output_root / "calibration" / "charge_calibration_trace.json", trace_all)
        if converged is None:
            raise GateError(f"BLOQUEIO: calibração de carga não convergiu em até {BISECTION_MAX} iterações para {profile_id}.")
        fixed[profile_id] = {
            "charge_power_fixed_kW": float(converged["charge_power_kw"]),
            "final_soc_residual_pp": float(converged["soc_true_final_residual_pp"]),
            "soc_true_min_pct": float(converged["soc_true_min_pct"]),
            "soc_true_max_pct": float(converged["soc_true_max_pct"]),
            "iterations": int(converged["iteration"]),
            "integrated_Pdc_kWh": converged.get("audit", {}).get("integrated_Pdc_kWh"),
            "charge_energy_kWh": converged.get("audit", {}).get("charge_energy_kWh"),
            "numerical_balance_error": converged.get("audit", {}).get("numerical_balance_error"),
            "calibration_seed_streams": seeds,
            "reference_episode_id": train_h00["episode_id"],
            "profile_id": profile_id,
        }
    receipt = {
        "status": "CHARGE_CALIBRATION_CONVERGED",
        "input_hashes": artifacts,
        "profiles": fixed,
        "trace_path": str(output_root / "calibration" / "charge_calibration_trace.json"),
        "calibration_seed_policy": "SHA256('TAYCAN4R|CALIBRATION|<profile>|<stream>') first 8 hex as uint32; unique versus all 8928 manifest seeds; common random numbers across bisection points",
        "created_utc_note": "No timestamp is used as a seed or input; receipt is created only by an explicit local run.",
    }
    atomic_json(receipt_path, receipt)
    return receipt


def load_m01_i01_energy_receipt(output_root: Path, artifacts: dict[str, Any],
                                   rows: list[dict[str, str]]) -> tuple[Path, dict[str, Any], dict[tuple[str, str, float], dict[str, Any]]]:
    path = output_root / "calibration" / "M01_I01_ENERGY_MATCH_RECEIPT.json"
    if not path.is_file():
        raise GateError(
            "BLOQUEIO PRÉ-TESTE: falta calibration/M01_I01_ENERGY_MATCH_RECEIPT.json. "
            "O pré-registro exige pareamento energético M01×I01 por perfil e mapeamento "
            "da severidade I01 antes de qualquer episódio de teste."
        )
    receipt = read_json(path)
    if receipt.get("status") != "M01_I01_ENERGY_MATCH_COMPLETE":
        raise GateError("BLOQUEIO: recibo M01/I01 não declara M01_I01_ENERGY_MATCH_COMPLETE.")
    if receipt.get("input_hashes") != artifacts:
        raise GateError("BLOQUEIO: recibo M01/I01 foi calculado com hashes diferentes.")
    if receipt.get("calibration_split") != "independent_calibration_only" or        receipt.get("uses_validation_outcomes") is not False or receipt.get("uses_test_outcomes") is not False:
        raise GateError("BLOQUEIO: calibração M01/I01 não comprova isolamento de validação/teste.")
    manifest_seeds = {int(row[f"seed_{stream}"]) for row in rows for stream in STREAMS}
    calibration_seeds = receipt.get("calibration_seed_values")
    if not isinstance(calibration_seeds, list) or not calibration_seeds:
        raise GateError("BLOQUEIO: recibo M01/I01 não lista as seeds de calibração.")
    calibration_seeds = [int(x) for x in calibration_seeds]
    if len(set(calibration_seeds)) != len(calibration_seeds) or set(calibration_seeds) & manifest_seeds:
        raise GateError("BLOQUEIO: seeds de calibração M01/I01 duplicadas ou colidindo com o manifesto.")
    entries = receipt.get("mapping")
    if not isinstance(entries, list) or len(entries) != 12:
        raise GateError("BLOQUEIO: mapping M01/I01 deve conter 12 combinações (2 perfis × 2 DIFF × 3 severidades).")
    mapping: dict[tuple[str, str, float], dict[str, Any]] = {}
    for entry in entries:
        profile = entry.get("profile_id")
        diff_mode = entry.get("diff_motor_t_mapping")
        severity = finite_number(entry.get("m01_severity"))
        i01_severity = finite_number(entry.get("i01_severity_used"))
        mismatch = finite_number(entry.get("mismatch_pct"))
        motor_j = finite_number(entry.get("delta_E_motor_J"))
        inverter_j = finite_number(entry.get("delta_E_inverter_J"))
        status = entry.get("match_status")
        if profile not in PROFILES or diff_mode not in ("winding_proxy", "uninformative") or severity not in (0.25, 0.5, 1.0):
            raise GateError(f"BLOQUEIO: chave de mapeamento M01/I01 inválida: {entry}")
        if i01_severity is None or not 0.0 <= i01_severity <= 1.0 or mismatch is None or mismatch < 0:
            raise GateError(f"BLOQUEIO: severidade I01 ou mismatch inválido: {entry}")
        if motor_j is None or motor_j <= 0 or inverter_j is None or inverter_j < 0:
            raise GateError(f"BLOQUEIO: energias dissipadas ausentes/não positivas: {entry}")
        computed_mismatch = abs(inverter_j - motor_j) / motor_j * 100.0
        if abs(computed_mismatch - mismatch) > 0.05:
            raise GateError(f"BLOQUEIO: mismatch_pct não confere com as energias registradas: {entry}")
        if status not in ("MATCHED", "INFEASIBLE"):
            raise GateError(f"BLOQUEIO: match_status inválido: {status}")
        if status == "MATCHED" and mismatch > 1.0:
            raise GateError(f"BLOQUEIO: status MATCHED com mismatch >1%: {entry}")
        if status == "INFEASIBLE" and mismatch <= 1.0:
            raise GateError(f"BLOQUEIO: status INFEASIBLE apesar de mismatch <=1%: {entry}")
        key = (profile, diff_mode, float(severity))
        if key in mapping:
            raise GateError(f"BLOQUEIO: chave M01/I01 duplicada: {key}")
        mapping[key] = entry
    expected_keys = {
        (profile, diff_mode, severity)
        for profile in PROFILES
        for diff_mode in ("winding_proxy", "uninformative")
        for severity in (0.25, 0.5, 1.0)
    }
    if set(mapping) != expected_keys:
        raise GateError("BLOQUEIO: o recibo M01/I01 não cobre todas as combinações pré-registradas.")
    return path, receipt, mapping


def output_paths(run_dir: Path, episode_id: str) -> tuple[Path, Path, Path, Path]:
    return (
        run_dir / "episode_features" / f"{episode_id}.csv",
        run_dir / "episode_metadata" / f"{episode_id}.json",
        run_dir / "soc_trajectories" / f"{episode_id}.csv.gz",
        run_dir / "done" / f"{episode_id}.json",
    )


def completed_episode_valid(run_dir: Path, episode_id: str, artifacts: dict[str, Any]) -> bool:
    feature_path, metadata_path, trajectory_path, done_path = output_paths(run_dir, episode_id)
    if not done_path.is_file():
        return False
    done = read_json(done_path)
    if done.get("status") != "EPISODE_COMPLETE" or done.get("input_hashes") != artifacts:
        raise GateError(f"BLOQUEIO: recibo de episódio incompatível: {done_path}")
    log_path = run_dir / "logs" / f"{episode_id}.json"
    for path, key in ((feature_path, "feature_csv_sha256"), (metadata_path, "metadata_json_sha256"),
                      (trajectory_path, "soc_trajectory_gz_sha256"), (log_path, "run_log_sha256")):
        if not path.is_file() or sha256_file(path) != done.get(key):
            raise GateError(f"BLOQUEIO: artefato de episódio corrompido/incompleto: {path}")
    return True


def run_episode_row(row: dict[str, str], prereg: dict[str, Any], artifacts: dict[str, Any],
                    charge_receipt: dict[str, Any], backend_path: Path, run_dir: Path,
                    energy_mapping: dict[tuple[str, str, float], dict[str, Any]] | None = None,
                    energy_receipt_path: Path | None = None) -> dict[str, Any]:
    episode_id = row["episode_id"]
    if completed_episode_valid(run_dir, episode_id, artifacts):
        return {"episode_id": episode_id, "status": "SKIPPED_VERIFIED", "runtime_s": 0.0}
    seeds = {stream: int(row[f"seed_{stream}"]) for stream in STREAMS}
    episode_for_backend: dict[str, Any] = dict(row)
    episode_for_backend["injected_severity"] = 0.0 if row["hypothesis"] == "H00" else float(row["severity"])
    episode_for_backend["energy_match_status"] = "NOT_APPLICABLE"
    if row["hypothesis"] == "M01":
        episode_for_backend["energy_match_status"] = "REFERENCE_M01"
    if row["hypothesis"] == "I01":
        if energy_mapping is None:
            episode_for_backend["energy_match_status"] = "UNMATCHED_SMOKE_NOT_SCORED"
        else:
            key = (row["profile"], row["diff_motor_t_mapping"], float(row["severity"]))
            if key not in energy_mapping:
                raise GateError(f"BLOQUEIO: sem mapeamento energético para {episode_id}: {key}")
            match = energy_mapping[key]
            episode_for_backend["injected_severity"] = float(match["i01_severity_used"])
            episode_for_backend["energy_match_status"] = match["match_status"]
            episode_for_backend["energy_match_mismatch_pct"] = float(match["mismatch_pct"])
            episode_for_backend["delta_E_motor_J"] = float(match["delta_E_motor_J"])
            episode_for_backend["delta_E_inverter_J"] = float(match["delta_E_inverter_J"])
    context = base_context(row, "episode", row["profile"],
                           charge_receipt["profiles"][row["profile"]]["charge_power_fixed_kW"],
                           artifacts, prereg, seeds, run_dir)
    context["job_id"] = episode_id
    context["episode"] = episode_for_backend
    if energy_receipt_path is not None:
        context["energy_match_receipt_path"] = str(energy_receipt_path)
        context["energy_match_receipt_sha256"] = sha256_file(energy_receipt_path)
    context["persistent_biases_note"] = "Biases uniformes por canal/episódio são explicitamente passados em observation_config."
    result = run_subprocess_job(context, run_dir)
    if result.get("status") != "EPISODE_COMPLETE" or result.get("episode_id") != episode_id:
        raise GateError(f"Worker não concluiu episódio: {episode_id}")
    return {"episode_id": episode_id, "status": "EXECUTED", "runtime_s": float(result["runtime_s"])}


def rebuild_aggregate_tables(rows: list[dict[str, str]], run_dir: Path, artifacts: dict[str, Any]) -> None:
    features = []
    metadata = []
    for row in rows:
        episode_id = row["episode_id"]
        if not completed_episode_valid(run_dir, episode_id, artifacts):
            continue
        feature_path, metadata_path, _, _ = output_paths(run_dir, episode_id)
        with feature_path.open("r", encoding="utf-8", newline="") as handle:
            values = list(csv.DictReader(handle))
        if len(values) != 1:
            raise GateError(f"Matriz por episódio deve conter exatamente uma linha: {feature_path}")
        features.append(values[0])
        metadata.append(read_json(metadata_path))
    atomic_csv(run_dir / "tables" / "stage4_feature_matrix.csv",
               ["episode_id", *FEATURE_NAMES, *MASK_NAMES], features)
    metadata_columns = [
        "episode_id", "hypothesis", "split", "severity", "injected_severity", "energy_match_status",
        "energy_match_mismatch_pct", "energy_match_delta_E_motor_J", "energy_match_delta_E_inverter_J",
        "energy_match_receipt_sha256", "severity_quota", "replicate", "block", "profile",
        "duration_s", "dt_s", "acquisition_mode", "counter_source", "diff_motor_t_mapping", "soc_phi_per_s",
        "rpm_white_sigma", "rpm_bias_halfwidth", "torque_white_sigma", "torque_bias_halfwidth",
        "soc_group_bias_sd", "soc_innovation", "aux_phi", "aux_white_sigma", "aux_cap",
        *(f"seed_{stream}" for stream in STREAMS), "charge_power_fixed_kW", "runtime_s", "n_steps",
        "soc_true_min_pct", "soc_true_max_pct", "soc_true_final_pct", "soc_true_initial_pct",
        "soc_true_final_residual_pp", "soc_true_window_violation", "soc_true_samples", "soc_observed_min_pct", "soc_observed_max_pct",
        "soc_observed_window_violation", "ambient_shift_not_modeled", "ambient_shift_applied",
        "counter_timing_verified", "r33_regression_rank", "r33_condition_number_inf_estimate_scaled_design",
        "r33_regression_n", "feature_diagnostics_json", "input_hashes_json", "audit_flags_json",
    ]
    atomic_csv(run_dir / "tables" / "stage4_evaluation_metadata.csv", metadata_columns, metadata)


def run_mode(args: argparse.Namespace) -> None:
    model_path, freeze_path, backend_path = resolve_external_paths(args)
    artifacts = load_and_verify_inputs(model_path, freeze_path, backend_path)
    backend = load_backend(backend_path)  # Contract gate before calibration or episode launch.
    rows, prereg, amendment = load_manifest()
    output_root = Path(args.output_dir).expanduser().resolve() if args.output_dir else ROOT / "results/tmp/stage4_run"
    output_root.mkdir(parents=True, exist_ok=True)

    if args.mode == "smoke":
        charge_receipt = calibrate_profiles(rows, prereg, artifacts, backend_path, output_root)
        # One training row per hypothesis, chosen by manifest order; smoke outputs are not scored data.
        smoke_rows = []
        for hypothesis in HYPOTHESES:
            candidate = next((r for r in rows if r["hypothesis"] == hypothesis and r["split"] == "train"), None)
            if candidate is None:
                raise GateError(f"Sem episódio de treino para smoke: {hypothesis}")
            smoke_rows.append(candidate)
        index = {row["episode_id"]: i for i, row in enumerate(rows)}
        smoke_rows.sort(key=lambda r: index[r["episode_id"]])
        smoke_dir = output_root / "smoke"
        executed = []
        for row in smoke_rows:
            executed.append(run_episode_row(row, prereg, artifacts, charge_receipt, backend_path, smoke_dir))
        rebuild_aggregate_tables(smoke_rows, smoke_dir, artifacts)
        if len(executed) != 12:
            raise GateError(f"Smoke deveria executar 12 episódios, retornou {len(executed)}")
        smoke_receipt = {
            "status": "SMOKE_PASSED",
            "n_episodes": 12,
            "selected_hypotheses": HYPOTHESES,
            "selection_rule": "first manifest-order TRAIN episode for each of the 12 hypotheses; separate smoke output, not included in scored full output",
            "input_hashes": artifacts,
            "charge_calibration_receipt_sha256": sha256_file(output_root / "calibration/charge_calibration_receipt.json"),
            "episode_statuses": executed,
            "feature_matrix_sha256": sha256_file(smoke_dir / "tables/stage4_feature_matrix.csv"),
            "evaluation_metadata_sha256": sha256_file(smoke_dir / "tables/stage4_evaluation_metadata.csv"),
        }
        atomic_json(smoke_dir / "SMOKE_RECEIPT.json", smoke_receipt)
        print(json.dumps({"status": "SMOKE_PASSED", "episodes": 12,
                          "calibration_receipt": str(output_root / "calibration/charge_calibration_receipt.json"),
                          "smoke_receipt": str(smoke_dir / "SMOKE_RECEIPT.json")}, ensure_ascii=False, indent=2))
        return

    if args.mode == "full":
        calibration_path = output_root / "calibration" / "charge_calibration_receipt.json"
        charge_receipt = load_cached_calibration(calibration_path, artifacts)
        if charge_receipt is None:
            raise GateError("BLOQUEIO: execute --mode smoke primeiro; calibração de ambos os perfis ainda não existe.")
        smoke_receipt_path = output_root / "smoke" / "SMOKE_RECEIPT.json"
        if not smoke_receipt_path.is_file():
            raise GateError("BLOQUEIO: smoke de 12 episódios ainda não foi aprovado.")
        smoke = read_json(smoke_receipt_path)
        if smoke.get("status") != "SMOKE_PASSED" or smoke.get("n_episodes") != 12 or smoke.get("input_hashes") != artifacts:
            raise GateError("BLOQUEIO: recibo smoke ausente, inválido ou feito com hashes diferentes.")
        if smoke.get("charge_calibration_receipt_sha256") != sha256_file(calibration_path):
            raise GateError("BLOQUEIO: calibração mudou depois do smoke.")
        smoke_rows = [next(r for r in rows if r["hypothesis"] == h and r["split"] == "train") for h in HYPOTHESES]
        smoke_dir = output_root / "smoke"
        for smoke_row in smoke_rows:
            if not completed_episode_valid(smoke_dir, smoke_row["episode_id"], artifacts):
                raise GateError(f"BLOQUEIO: artefato smoke ausente/inválido: {smoke_row['episode_id']}")
        if sha256_file(smoke_dir / "tables/stage4_feature_matrix.csv") != smoke.get("feature_matrix_sha256"):
            raise GateError("BLOQUEIO: matriz smoke diverge do recibo.")
        if sha256_file(smoke_dir / "tables/stage4_evaluation_metadata.csv") != smoke.get("evaluation_metadata_sha256"):
            raise GateError("BLOQUEIO: metadata smoke diverge do recibo.")
        energy_receipt_path, energy_receipt, energy_mapping = load_m01_i01_energy_receipt(output_root, artifacts, rows)
        energy_receipt_hash = sha256_file(energy_receipt_path)
        full_artifacts = {**artifacts, "m01_i01_energy_match_receipt_sha256": energy_receipt_hash}
        full_dir = output_root / "full"
        summary = []
        for row in rows:  # Strict manifest order. Each physical episode is a subprocess.
            summary.append(run_episode_row(row, prereg, full_artifacts, charge_receipt, backend_path, full_dir,
                                           energy_mapping=energy_mapping, energy_receipt_path=energy_receipt_path))
        rebuild_aggregate_tables(rows, full_dir, full_artifacts)
        complete = sum(completed_episode_valid(full_dir, row["episode_id"], full_artifacts) for row in rows)
        if complete != 2232:
            raise GateError(f"Execução completa incompleta: {complete}/2232 episódios.")
        full_receipt = {
            "status": "ALL_2232_EPISODES_COMPLETE",
            "n_episodes": complete,
            "input_hashes": full_artifacts,
            "charge_calibration_receipt_sha256": sha256_file(calibration_path),
            "smoke_receipt_sha256": sha256_file(smoke_receipt_path),
            "m01_i01_energy_match_receipt_sha256": energy_receipt_hash,
            "feature_matrix_sha256": sha256_file(full_dir / "tables/stage4_feature_matrix.csv"),
            "evaluation_metadata_sha256": sha256_file(full_dir / "tables/stage4_evaluation_metadata.csv"),
            "runtime_records": summary,
        }
        atomic_json(full_dir / "STAGE4_RUN_RECEIPT.json", full_receipt)
        print(json.dumps({"status": full_receipt["status"], "episodes": complete,
                          "receipt": str(full_dir / "STAGE4_RUN_RECEIPT.json")}, ensure_ascii=False, indent=2))
        return
    raise GateError(f"Modo desconhecido: {args.mode}")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Runner fail-closed da Etapa 4 do Project Taycan.")
    parser.add_argument("--mode", choices=("smoke", "full"), default="smoke",
                        help="smoke calibra os dois perfis e roda 12 episódios; full exige smoke aprovado.")
    parser.add_argument("--model-py", default=os.environ.get("TAYCAN_MODEL_PY"))
    parser.add_argument("--freeze-json", default=os.environ.get("TAYCAN_FREEZE_JSON"))
    parser.add_argument("--backend-file", default=os.environ.get("TAYCAN_STAGE4_BACKEND"))
    parser.add_argument("--output-dir", default=os.environ.get("TAYCAN_STAGE4_OUTPUT"))
    parser.add_argument("--worker-context", help=argparse.SUPPRESS)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    try:
        if args.worker_context:
            return run_worker(Path(args.worker_context).resolve())
        run_mode(args)
        return 0
    except GateError as exc:
        print(f"BLOQUEIO ETAPA 4: {exc}", file=sys.stderr)
        return 2
    except Exception as exc:
        print(f"ERRO NÃO CLASSIFICADO: {type(exc).__name__}: {exc}", file=sys.stderr)
        raise


if __name__ == "__main__":
    raise SystemExit(main())
