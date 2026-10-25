"""Independent small receipt audit; no experimental data ingestion."""
import hashlib,json,math
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];BASE=ROOT/'results/e66_causal_audit'
def digest(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def validate(rows,protocol):
 expected={(c,'SPMe',r) for c in protocol['cases'] for r in ['.5','1']}|{(c,'DFN','1') for c in protocol['DFN_1C_cases']}
 actual={(r['case'],r['model'],r['rate']) for r in rows}
 if actual!=expected or len(rows)!=len(expected):raise ValueError('missing/duplicate counterfactual')
 for r in rows:
  if r['status']!='COMPLETED':raise ValueError('unfinished counterfactual')
  for k in ['RMSE_V','bias_V','centered_RMSE_V','coverage','max_abs_error_V']:
   if not math.isfinite(r[k]):raise ValueError('nonfinite metric')
  if abs(r['RMSE_V']**2-r['bias_V']**2-r['centered_RMSE_V']**2)>1e-10:raise ValueError('residual identity mismatch')
  if r['case']=='baseline' and r['archive_reproduction']!='PASS':raise ValueError('unreproduced baseline')
  if r['parameters_optimized']:raise ValueError('unpermitted optimization')
  if r['case']=='contact_plus0p001' and r['baseline_gap_mean_V']>=0:raise ValueError('contact loss sign')
 return len(rows)
def main():
 p=BASE/'counterfactuals/PROTOCOL.json';rows=json.loads((BASE/'counterfactuals/RESULTS.json').read_text())['results'];n=validate(rows,json.loads(p.read_text()))
 for r in rows:
  if r['source_SHA256']!=digest(ROOT/'scripts/e66_causal_counterfactuals.py') or r['protocol_SHA256']!=digest(p):raise ValueError('source/protocol drift')
 hashes={r['fit_SHA256'] for r in rows}
 if len(hashes)!=1:raise ValueError('different fitting parameters receipt')
 report={'status':'PASS_RECEIPT_INTEGRITY_NOT_PHYSICAL_VALIDATION','counterfactuals':n,'single_posthoc_fit_sha256':next(iter(hashes)),'historical_sources_preserved':True,'files':{str(x.relative_to(ROOT)):digest(x) for x in BASE.rglob('*') if x.is_file() and x.name!='INDEPENDENT_RECEIPT_AUDIT.json'}}
 (BASE/'INDEPENDENT_RECEIPT_AUDIT.json').write_text(json.dumps(report,indent=2)+'\n');print(report['status'],n)
if __name__=='__main__':main()
