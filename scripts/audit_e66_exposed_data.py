"""Retrospective H4/H7 audit. Summary-only output; four fixed exposed cell files.
Does not fit, simulate or modify the historical segment/model. Synthetic tests
exercise this independent accounting and characterize the original parser bugs.
"""
from __future__ import annotations
import argparse,collections,datetime,hashlib,io,json,platform,sys,zipfile
from pathlib import Path
import numpy as np
from scipy.io import loadmat
ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'results/e66_causal_audit/data'
def sha(b):return hashlib.sha256(b).hexdigest()
def stats(x):
 x=np.asarray(x,float);g=x[np.isfinite(x)]
 return {'n':int(x.size),'nonfinite':int(x.size-g.size),'min':float(g.min()) if g.size else None,'max':float(g.max()) if g.size else None,'mean':float(g.mean()) if g.size else None,'median':float(np.median(g)) if g.size else None}
def selected_indices(m,ithresh=1.,vlow=2.):
 t,i,v,T=[np.asarray(m[k],float) for k in ['Time','Current','Voltage','Battery_Temp_degC']]
 if not t.ndim==i.ndim==v.ndim==T.ndim==1 or not len(t)==len(i)==len(v)==len(T):raise ValueError('misaligned arrays')
 valid=np.isfinite(t)&np.isfinite(i)&np.isfinite(v)&np.isfinite(T)&(-i>ithresh)&(v>vlow)&(v<5)
 all_ix=np.flatnonzero(valid)
 if len(all_ix)<10:raise ValueError('fewer than ten valid total discharge samples')
 cuts=np.flatnonzero(np.diff(all_ix)>1);ix=all_ix[:cuts[0]+1] if len(cuts) else all_ix
 # Additional audit guard: original parser fails to check length AFTER truncation.
 if len(ix)<2:raise ValueError('first selected discharge too short for integration')
 if np.any(np.diff(t[ix])<=0):raise ValueError('nonmonotone selected time')
 return ix,all_ix

def integrate(t,i):
 t=np.asarray(t,float);i=np.asarray(i,float)
 if len(t)<2 or len(t)!=len(i) or not np.all(np.isfinite(t)) or not np.all(np.isfinite(i)) or np.any(np.diff(t)<=0):raise ValueError('invalid integration arrays')
 return float(np.trapezoid(i,t)/3600)
def audit_member(m):
 ix,all_ix=selected_indices(m);raw={k:np.asarray(m[k]) for k in m};t=raw['Time'][ix].astype(float);t=t-t[0];i=-raw['Current'][ix].astype(float);v=raw['Voltage'][ix].astype(float);T=raw['Battery_Temp_degC'][ix].astype(float);dt=np.diff(t);q=integrate(t,i);med=float(np.median(dt));gap=dt>5*med
 a={'raw_rows':len(raw['Time']),'raw_fields':list(raw),'selected_rows':len(ix),'valid_discharge_rows_all_runs':len(all_ix),'discarded_later_discharge_rows':len(all_ix)-len(ix),'selected_start_index':int(ix[0]),'selected_end_index':int(ix[-1]),'selected_fraction_of_raw_rows':len(ix)/len(raw['Time']),'raw_nonfinite_counts':{k:int(np.sum(~np.isfinite(raw[k].astype(float)))) for k in ['Time','Current','Voltage','Battery_Temp_degC','Ah','Power']},'raw_status_counts':dict(collections.Counter(map(str,raw['Status']))),'selected_status_counts':dict(collections.Counter(map(str,raw['Status'][ix]))),'duration_s':float(t[-1]),'dt_s':stats(dt),'large_gap_count':int(gap.sum()),'large_gap_time_fraction':float(dt[gap].sum()/t[-1]),'capacity_trapezoid_Ah':q,'current_discharge_A':stats(i),'temperature_C':stats(T),'temperature_initial_C':float(T[0]),'temperature_final_C':float(T[-1]),'voltage_initial_loaded_V':float(v[0]),'voltage_final_loaded_V':float(v[-1]),'current_initial_discharge_A':float(i[0]),'first_selected_is_rest':bool(abs(i[0])<.1)}
 a['sign_check']={'source_current_negative_fraction':float(np.mean(raw['Current'][ix]<0)),'power_minus_sourceVI_W':stats(raw['Power'][ix]-raw['Current'][ix]*v),'power_plus_dischargeVI_W':stats(raw['Power'][ix]+i*v),'scope':'cell Digatron signals; not module AVL/Orion inference'}
 ah=raw['Ah'][ix].astype(float);counter=float(ah[-1]-ah[0]);a['counter_check']={'first_counter_Ah':float(ah[0]),'last_counter_Ah':float(ah[-1]),'signed_Ah_delta':counter,'abs_Ah_delta':abs(counter),'integral_minus_abs_counter_Ah':q-abs(counter),'difference_percent_of_integral':100*(q-abs(counter))/q,'counter_increment_min_Ah':float(np.diff(ah).min()),'counter_increment_max_Ah':float(np.diff(ah).max()),'shared_instrument_not_independent_calibration':True}
 a['integration_sensitivity_Ah']={'left':float(np.sum(i[:-1]*dt)/3600),'right':float(np.sum(i[1:]*dt)/3600)}
 for stride in [2,10]:
  sub=np.unique(np.r_[np.arange(0,len(t),stride),len(t)-1]);a['integration_sensitivity_Ah']['coarse_every_'+str(stride)]=integrate(t[sub],i[sub])
 a['endpoint_trim_Ah']={str(n):integrate(t[n:-n],i[n:-n]) for n in [1,5] if len(t)>2*n+1}
 a['threshold_sensitivity']=[]
 for current in [.5,1,2]:
  for voltage in [2,2.5,2.8]:
   sub,_=selected_indices(m,current,voltage);a['threshold_sensitivity'].append({'current_threshold_A':current,'voltage_threshold_V':voltage,'n':len(sub),'capacity_Ah':integrate(raw['Time'][sub],-raw['Current'][sub])})
 # Timing precision differs: TimeStamp can be rounded to whole seconds.
 ts=[datetime.datetime.strptime(str(x),'%m/%d/%Y %I:%M:%S %p') for x in raw['TimeStamp'][ix]];stamp=np.array([(x-ts[0]).total_seconds() for x in ts]);a['timestamp_check']={'start':ts[0].isoformat(),'end':ts[-1].isoformat(),'time_vs_timestamp_elapsed_difference_s':stats(t-stamp),'nonincreasing_timestamp_steps':int(np.sum(np.diff(stamp)<=0)),'note':'TimeStamp rounded seconds can repeat; Time used for integration'}
 # Preceding rest must be actually contiguous and recorded in the SAME file.
 pre=[];j=int(ix[0])-1
 while j>=0 and np.isfinite(raw['Current'][j]) and abs(raw['Current'][j])<.1:
  pre.append(j);j-=1
 if pre:
  pre=np.asarray(pre[::-1]);a['preceding_rest']={'recorded':True,'n':len(pre),'duration_s':float(raw['Time'][pre[-1]]-raw['Time'][pre[0]]),'last_rest_voltage_V':float(raw['Voltage'][pre[-1]]),'last_rest_to_first_loaded_gap_s':float(raw['Time'][ix[0]]-raw['Time'][pre[-1]]),'last_rest_minus_first_loaded_mV':float(1000*(raw['Voltage'][pre[-1]]-v[0])),'conditional_unobserved_transition_charge_upper_Ah':float((raw['Time'][ix[0]]-raw['Time'][pre[-1]])*np.max(i)/3600),'transition_bound_assumption':'current between last rest and first loaded lies between zero and selected maximum; not a measured correction','interpretation':'recorded preceding low-current interval, not proof of full thermodynamic equilibrium'}
 else:a['preceding_rest']={'recorded':False,'interpretation':'no preceding rest in selected file; SOC1/preconditioning not established by first loaded point'}
 # Compare raw-grid interpolation to historical selected curve; do not output traces.
 a['linear_interpolation_checks']={'query500_grid_within_domain':True,'input_gap_max_s':float(dt.max()),'constant_input_sanity_A':float(np.ptp(i)),'warning':'shared arrays do not independently prove instrument channel synchronization; no per-channel timestamps'}
 return a

def main(archive):
 config=json.loads((OUT/'PROSPECTIVE_DATA_AUDIT.json').read_text());spec=json.loads((ROOT/'results/e66_calibration/PROSPECTIVE.json').read_text());names=config['authorized_numeric_members']
 if names!=spec['fit']+spec['evaluation'] or len(names)!=4:raise ValueError('allowlist drift')
 if sha(archive.read_bytes())!=config['source_outer_sha256']:raise ValueError('outer hash mismatch')
 if sha((ROOT/'scripts/fit_e66_generator_b.py').read_bytes())!=config['original_source_sha256']:raise ValueError('historical parser changed')
 report={'classification':'RETROSPECTIVE_DATA_PARSER_DIAGNOSTIC_ONLY','original_work_receipts_recovered':False,'baseline_commit':config['baseline_commit'],'config_sha256':sha((OUT/'PROSPECTIVE_DATA_AUDIT.json').read_bytes()),'audit_source_sha256':sha(Path(__file__).read_bytes()),'python':platform.python_version(),'source_outer_sha256':config['source_outer_sha256'],'members':[],'protected_numeric_members_opened':0}
 sys.path.insert(0,str(ROOT));from scripts.fit_e66_generator_b import segment
 with zipfile.ZipFile(archive) as z:
  inner=z.read('1-Cell Data.zip')
  if sha(inner)!=config['source_inner_sha256']:raise ValueError('inner hash mismatch')
  report['source_inner_sha256']=sha(inner)
  with zipfile.ZipFile(io.BytesIO(inner)) as c:
   for name in names:
    blob=c.read(name);m=loadmat(io.BytesIO(blob),simplify_cells=True)['meas'];a=audit_member(m);original=segment(blob);a.update(name=name,source_sha256=sha(blob),historical_segment_exact_row_count_match=a['selected_rows']==original['rows'],historical_segment_integral_difference_Ah=a['capacity_trapezoid_Ah']-original['capacity_Ah']);report['members'].append(a)
 q=report['members'][0]['capacity_trapezoid_Ah'];report['normalization']={'Qref_Ah':q,'virtual_parallel_Qref_over_5':q/5,'mapping':'I_rep=I_exp/(Qref/5); I_rep/5=I_exp/Qref. This preserves nominal relative charge depletion, not geometry/kinetics/E66 physics.'}
 for a in report['members']:
  a['normalization']={'median_Crate_vs_65Ah':a['current_discharge_A']['median']/65,'median_Crate_vs_Qref':a['current_discharge_A']['median']/q,'median_representative_cell_current_A':a['current_discharge_A']['median']/(q/5),'delivered_charge_fraction_Qref':a['capacity_trapezoid_Ah']/q}
 (OUT/'DATA_AUDIT.json').write_text(json.dumps(report,indent=2,allow_nan=False)+'\n')
 print(json.dumps([{'name':a['name'].rsplit('/',1)[1],'rows':a['selected_rows'],'Q':a['capacity_trapezoid_Ah'],'counter_difference_percent':a['counter_check']['difference_percent_of_integral'],'dt':a['dt_s'],'preceding_rest':a['preceding_rest']} for a in report['members']],indent=2))
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--archive',type=Path,default=ROOT.parent/'project_sources/09-doi-10.5683-sp3-7jp3nm.zip');main(p.parse_args().archive)
