"""Summarize fixed candidates; quarantine long-pulse recovery normalization."""
import json
from pathlib import Path
import numpy as np
ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'results/e66_pulse_discrimination'
def summarize(h,g):
 rows=h['results']; coarse=[r for r in rows if r['mesh']==20]
 names=sorted({r['candidate'] for r in coarse});stats={}
 for c in names:
  rr=[r for r in coarse if r['candidate']==c]
  stats[c]={k:float(np.median([r[k] for r in rr])) for k in ['RMSE_deltaV_V','RMSE_loaded_V','RMSE_rest_V']}
 base=stats['baseline_posthoc']['RMSE_loaded_V']
 for c in names:stats[c]['median_loaded_improvement_fraction']=1-stats[c]['RMSE_loaded_V']/base
 wins=sum(min((r for r in coarse if r['pulse']['index']==i),key=lambda r:r['RMSE_loaded_V'])['candidate']=='kinetics_both_x2' for i in {r['pulse']['index'] for r in coarse})
 gaps={}
 for r in rows:
  if r['mesh']!=40:continue
  a=next(a for a in coarse if a['candidate']==r['candidate'] and a['pulse']['index']==r['pulse']['index'])
  if a['model_times_s']!=r['model_times_s']:raise ValueError('mesh alignment')
  gaps[r['candidate']]=float(np.max(np.abs(np.array(a['model_deltas'])-r['model_deltas'])))
 gitt=[{'index':p['index'],'rebound_1_to_300s_V':p['relaxation_deltaV_after_s']['300']-p['relaxation_deltaV_after_s']['1'],'recovery_fraction_60s_valid':False} for p in g['pulses']]
 return {'scope':'mechanism discrimination, not fitted E66 generator or external diagnostic validation','candidate_statistics':stats,'kinetics_loaded_wins':wins,'eligible_HPPC_pulses':len(coarse)//len(names),'independent_cells':1,'mesh20_to40_max_gap_V':gaps,'mesh_gate_5mV_pass':all(x<=.005 for x in gaps.values()),'conditional_preference':'kinetics_both_x2' if wins/(len(coarse)//len(names))>=.75 and stats['kinetics_both_x2']['median_loaded_improvement_fraction']>=.2 else 'INCONCLUSIVE','GITT':gitt,'GITT_metric_quarantine':'Ignore recovery_fraction_60s in GITT_EMPIRICAL.json: denominator is 10s drop, not end-of-long-pulse drop; it is not a physical recovery fraction. Retained original output for audit. Rebound uses two post-pulse voltages and is descriptive only.','inference_limits':['three SOC windows from one cell/session are correlated','relative-voltage anchoring removes OCV offset','both electrode kinetics scaled jointly, not individually identified','GITT has no simulated prediction in this audit','prior 1C validation failure remains; no generator promotion']}
if __name__=='__main__':
 out=summarize(json.loads((OUT/'HPPC_RESULTS.json').read_text()),json.loads((OUT/'GITT_EMPIRICAL.json').read_text()))
 (OUT/'SUMMARY.json').write_text(json.dumps(out,indent=2,allow_nan=False)+'\n')
 print(json.dumps(out,indent=2))
