"""Post-hoc domain check; preserve the original voltage-only gates."""
import json
import sys
from pathlib import Path
import numpy as np
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from scripts import transfer_e66_to_dev_module as m

def main():
    rows = json.loads((m.OUT / 'EVALUATION.json').read_text())['results']
    out = []
    for name in sorted({r['name'] for r in rows if r['status'] == 'COMPLETED'}):
        t, current, measured, meta = m.window(name)
        charge = np.r_[0, np.cumsum((current[1:] + current[:-1]) * np.diff(t) / 7200)]
        soc = meta['initial_SOC_from_pre_voltage'] - charge / 61.259778569358865
        for r in [r for r in rows if r['name'] == name]:
            error = np.asarray(r['model_mean_cell_V']) - np.interp(r['model_times_s'], t, measured)
            rmse = float(np.sqrt(np.mean(error**2)))
            if abs(rmse - r['RMSE_mean_cell_V']) > 1e-10:
                raise ValueError('metric disagreement')
            domain = min(soc) >= 0 and max(soc) <= 1
            out.append({'name': name, 'model': r['model'], 'RMSE_V': rmse,
                        'original_voltage_only_gate': r['gate'], 'SOC_proxy_range': [float(min(soc)), float(max(soc))],
                        'posthoc_domain_gate': 'PASS' if domain else 'FAIL',
                        'combined_interpretation': 'PASS_LIMITED' if domain and r['gate'] == 'PASS' else 'FAIL'})
    m.c.dump(m.OUT / 'DOMAIN_AUDIT.json', {'posthoc': True, 'original_results_unchanged': True,
                                        'results': out, 'ineligible': [r for r in rows if r['status'] != 'COMPLETED']})

if __name__ == '__main__':
    main()
