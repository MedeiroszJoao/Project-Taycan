"""Post-evaluation metric audit. No fitting; gates come from the frozen protocol."""
import json
import sys
from pathlib import Path
import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from scripts import validate_e66_reserved_module_sessions as v


def main():
    v.guards()
    receipt = json.loads((v.OUT / 'EVALUATION.json').read_text())
    if receipt['freeze_sha256'] != v.m.c.sha(v.OUT / 'VALIDATION_FREEZE.json'):
        raise ValueError('evaluation freeze mismatch')
    rows = receipt['results']
    expected = {(i, k, 40) for i in range(2) for k in ['SPMe', 'DFN']} | {(i, 'SPMe', 80) for i in range(2)}
    keys = [(r['index'], r['model'], r['mesh']) for r in rows]
    if len(keys) != len(expected) or set(keys) != expected:
        raise ValueError('missing or duplicate cases')
    criteria = json.loads((v.OUT / 'PROTOCOL.json').read_text())['primary_criteria']
    checks, refinement = [], []
    for i in range(2):
        t, current, measured, _, meta = v.window(i)
        charge = np.r_[0, np.cumsum((current[:-1] + current[1:]) * np.diff(t) / 7200)]
        soc = meta['initial_SOC'] + charge / (2 * 61.259778569358865)
        for r in [r for r in rows if r['index'] == i]:
            if r['status'] != 'COMPLETED':
                raise ValueError('incomplete numerical evaluation')
            times = np.asarray(r['model_times_s'])
            prediction = np.asarray(r['predicted_AVL_module_V'])
            if not np.all(np.isfinite(prediction)) or np.any(np.diff(times) <= 0):
                raise ValueError('invalid prediction')
            error = (prediction - np.interp(times, t, measured)) / 6
            rmse, maximum = float(np.sqrt(np.mean(error**2))), float(np.max(abs(error)))
            for key, value in [('AVL_RMSE_V_per_mean_cell', rmse), ('AVL_max_error_V_per_mean_cell', maximum)]:
                if abs(r[key] - value) > 1e-10:
                    raise ValueError('metric disagreement')
            if not np.allclose(r['coulomb_SOC_range'], [min(soc), max(soc)], atol=1e-10, rtol=0):
                raise ValueError('SOC accounting disagreement')
            passed = (rmse <= criteria['AVL_RMSE_V_per_mean_cell'] and maximum <= criteria['AVL_max_error_V_per_mean_cell']
                      and r['coverage'] >= criteria['coverage_min'] and min(soc) >= 0 and max(soc) <= 1)
            if ('PASS' if passed else 'FAIL') != r['gate']:
                raise ValueError('gate disagreement')
            checks.append({'index': i, 'model': r['model'], 'mesh': r['mesh'], 'RMSE_mV_per_mean_cell': rmse * 1000,
                           'maximum_mV_per_mean_cell': maximum * 1000, 'gate': r['gate'],
                           'secondary_sensor_bias_plus_minus_5mV_worst_RMSE_mV': max(float(np.sqrt(np.mean((error + b)**2))) * 1000 for b in [-.005, .005])})
        pair = {r['mesh']: r for r in rows if r['index'] == i and r['model'] == 'SPMe'}
        low, high = pair[40], pair[80]
        gap = float(np.max(abs(np.asarray(low['predicted_AVL_module_V']) - np.interp(low['model_times_s'], high['model_times_s'], high['predicted_AVL_module_V']))) / 6)
        refinement.append({'index': i, 'maximum_gap_V_per_mean_cell': gap, 'gate': 'PASS' if gap <= criteria['mesh40_80_max_gap_V_per_mean_cell'] else 'FAIL'})
    decision = 'PASS_LIMITED' if all(r['gate'] == 'PASS' for r in checks + refinement) else 'FAIL'
    v.m.c.dump(v.OUT / 'INDEPENDENT_VERDICT.json', {
        'decision': decision, 'scope': 'two held-out sessions, same module, selected 300-second electrical windows',
        'audit_type': 'independent metric recomputation, same implementation/runtime; not an independent laboratory',
        'preregistration_commit': 'fbf19bffb0622710a9e6817a6d9c059bebb0a5f8',
        'evaluation_sha256': v.m.c.sha(v.OUT / 'EVALUATION.json'), 'checks': checks, 'refinement': refinement,
        'validation_files_numeric_access': 2, 'final_blind_files_numeric_access': 0, 'historical_reserved_access': 0,
        'no_parameter_retuning': True, 'thermal_prediction_validated': False, 'vehicle_diagnostics_validated': False,
        'formal_stage_approval': 'not issued', 'whole_stage4B': 'NOT_VALIDATED_FULL_SCOPE'})
    print(decision)


if __name__ == '__main__':
    main()
