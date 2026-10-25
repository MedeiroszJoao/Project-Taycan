"""Post-hoc E66 residual analysis, only two previously exposed cell sessions.
No solver runs, parameter fitting, blind files or raw third-party exports.
"""
from __future__ import annotations
import argparse,hashlib,inspect,json,os,sys
from pathlib import Path
os.environ['PYBAMM_DISABLE_TELEMETRY']='true'
import numpy as np
from scipy.integrate import cumulative_trapezoid
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from scripts.fit_e66_generator_b import get_inputs
OUT=ROOT/'results/e66_causal_audit/residuals'
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def dump(p,obj):p.write_text(json.dumps(obj,indent=2,allow_nan=False)+'\n')
def basic(e):
    e=np.asarray(e);mse=float(np.mean(e*e));bias=float(np.mean(e))
    return dict(n_time_samples=len(e),bias_mV=1000*bias,RMSE_mV=1000*np.sqrt(mse),centered_RMSE_mV=1000*float(np.sqrt(np.mean((e-bias)**2))),bias_fraction_MSE=bias*bias/mse if mse else None,max_abs_error_mV=1000*float(np.max(abs(e))))
def corr(x,y):
    return float(np.corrcoef(x,y)[0,1]) if np.std(x)>1e-12 and np.std(y)>1e-12 else None

def analyze(item,d):
    trajectory=item['trajectory'];t=np.array([r['time_s'] for r in trajectory]);e=np.array([r['model_V']-r['measured_V'] for r in trajectory])
    if d['source_sha256']!=item['experimental']['source_sha256']:raise ValueError('authorized source hash mismatch')
    predicted_meas=np.interp(t,d['t'],d['v']);receipt_meas=np.array([r['measured_V'] for r in trajectory])
    discrepancy=float(np.max(abs(predicted_meas-receipt_meas)))
    if discrepancy>1e-10:raise ValueError('receipt measurement interpolation mismatch')
    qraw=cumulative_trapezoid(d['i'],d['t'],initial=0)/3600;q=np.interp(t,d['t'],qraw);relative=q/q[-1]
    current=np.interp(t,d['t'],d['i']);temp=np.interp(t,d['t'],d['T']);cols={'time_s':t,'discharged_Ah':q,'relative_discharged_capacity':relative,'current_A':current,'temperature_C':temp}
    summary=basic(e)
    if abs(summary['RMSE_mV']/1000-item['voltage_RMSE_V'])>1e-12:raise ValueError('receipt metric mismatch')
    stats={}
    for k,x in cols.items():
      slope=float(np.polyfit(x,e,1)[0]) if np.std(x)>1e-12 else None
      stats[k]=dict(residual_correlation=corr(x,e),linear_descriptive_slope_V_per_unit=slope,range=[float(min(x)),float(max(x))],sd=float(np.std(x)))
    bins=[]
    for lo in np.linspace(0,.9,10):
      mask=(relative>=lo)&(relative<(lo+.1) if lo<.89 else relative<=1.0000001)
      # Only ten aggregate bins are publishable. No raw input/model trace exported.
      ids=np.flatnonzero(mask)
      if not len(ids):continue
      bins.append(dict(relative_capacity_bin=[float(lo),float(lo+.1)],time_mean_s=float(np.mean(t[ids])),Ah_mean=float(np.mean(q[ids])),relative_Ah_mean=float(np.mean(relative[ids])),current_mean_A=float(np.mean(current[ids])),temperature_change_mean_C=float(np.mean(temp[ids]-temp[0])),**basic(e[ids]),residual_min_mV=float(min(e[ids])*1000),residual_max_mV=float(max(e[ids])*1000)))
    thirds={str(i+1):basic(e[ids]) for i,ids in enumerate(np.array_split(np.arange(len(e)),3))}
    endpoints={name:basic(e[mask]) for name,mask in [('first_10pct',relative<=.1),('middle_80pct',(relative>.1)&(relative<.9)),('last_10pct',relative>=.9)]}
    # Descriptive projections diagnose confounding, NEVER update physical model.
    z=np.stack([relative,temp,current],axis=1);sd=np.std(z,axis=0);valid=sd>1e-12;zz=(z[:,valid]-np.mean(z[:,valid],axis=0))/sd[valid];X=np.column_stack([np.ones(len(e)),zz]);b=np.linalg.lstsq(X,e,rcond=None)[0];res=e-X@b
    descriptive=dict(columns=['intercept']+[k for k,v in zip(['relative_Ah','temperature','current'],valid) if v],standardized_slopes_V=b.tolist(),condition=float(np.linalg.cond(X)),rank=int(np.linalg.matrix_rank(X)),in_sample_centered_R2=1-float(np.mean(res**2)/np.var(e)) if np.var(e)>0 else None,causal_interpretation='FORBIDDEN: one trajectory, autocorrelation, progress/temperature confounding; no fitted prediction exported')
    return dict(model=item['model'],file=item['file'],source_sha256=d['source_sha256'],independent_sessions=1,measured_receipt_interpolation_max_V=discrepancy,metrics=summary,thirds=thirds,endpoint_regions=endpoints,associations=stats,predictor_correlations={a+' vs '+b:corr(cols[a],cols[b]) for a,b in [('time_s','discharged_Ah'),('relative_discharged_capacity','temperature_C'),('relative_discharged_capacity','current_A'),('temperature_C','current_A')]},descriptive_joint_regression=descriptive,bins=bins,notes=['500 time samples are NOT 500 independent validation units','Centered RMSE subtracts known posthoc mean residual algebraically; not corrected predictive performance','No confidence interval for between-cell accuracy: only one cell/two discharge sessions available'])

def parameter_audit():
    import pybamm
    from pybamm.input.parameters.lithium_ion import Chen2020
    p=pybamm.ParameterValues('Chen2020');entries={}
    patterns=['thickness','radius','height','width','porosity','diffusivity','exchange-current','conductivity','active material','Nominal cell','Maximum concentration','Initial concentration']
    for k in p.keys():
      if not any(s in k for s in patterns):continue
      v=p[k]
      if callable(v):entries[k]=dict(kind='inherited_function',name=v.__name__,source_sha256=hashlib.sha256(inspect.getsource(v).encode()).hexdigest())
      elif isinstance(v,(float,int,str)):entries[k]=dict(kind='inherited_value',value=v)
    return dict(pybamm_version=pybamm.__version__,parameter_source_sha256=sha(Chen2020.__file__),base='LG M50, not E66',entries=entries,
      fitted_physical_curve_parameters=['Positive OCP additive offset','Positive OCP linear stoichiometry correction','Contact resistance'],
      extra_overrides=['initial stoichiometries(SOC=1) using uncorrected OCP','ambient and initial T','voltage cutoffs','current normalized by measured C20 capacity/5Ah'],
      temperature_dependency={'negative_solid_diffusivity':'constant3.3e-14 m2/s','positive_solid_diffusivity':'constant4e-15 m2/s','electrolyte_diffusivity':'Nyman2008 concentration-dependent, T argument unused','electrolyte_conductivity':'Nyman2008 concentration-dependent, T argument unused','exchange_current_density':'Arrhenius temperature dependence retained for both electrodes'},
      interpretation='Current normalization preserves nominal relative discharge rate in a virtual5Ah M50; it does not identify E66 electrode geometry, kinetics, transport, active surface or stoichiometric windows.')
def main():
    ap=argparse.ArgumentParser();ap.add_argument('--receipts',type=Path,default=ROOT/'results/tmp/e66_causal/receipts/e66_calibration');ap.add_argument('--archive',type=Path,default=ROOT.parent/'project_sources/09-doi-10.5683-sp3-7jp3nm.zip');a=ap.parse_args()
    OUT.mkdir(parents=True,exist_ok=True);evaluation=a.receipts/'EVALUATION.json';ev=json.loads(evaluation.read_text());spec=json.loads((ROOT/'results/e66_calibration/PROSPECTIVE.json').read_text())
    if set(r['file'] for r in ev['results'])!=set(spec['evaluation']):raise ValueError('nonauthorized evaluation file')
    plan=dict(classification='POSTHOC_CAUSAL_DIAGNOSTIC_AFTER_1C_REVEALED',source_sha256=sha(__file__),evaluation_sha256=sha(evaluation),authorized_files=spec['evaluation'],fixed='existing500point predictions only; no fit/re-simulation',hypotheses=['H2 inherited parameter mismatch','H3 constant/current/progress-dependent residual','H5 temperature association not causality'],falsifiers=['Nearzero centered error would support pure-offset description; material centered residual refutes exact constant explanation','If residual/current curve differs by rate, a single pureohmic correction is insufficient','High correlations among progress and temperature prevent causal attribution'],metrics='biasfractionMSE, centeredRMSE, thirds, firstlast10%, correlations, descriptive standardized regression,10bins',independent_n='one cell,2sessions,2models of same measurements',no_iid_CI=True,cost='no solver, <1minute expected',protected_data_access=0,raw_export=False)
    planpath=OUT/'ANALYSIS_PLAN.json'
    if planpath.exists() and json.loads(planpath.read_text())!=plan:raise ValueError('plan/source drift')
    if not planpath.exists():dump(planpath,plan)
    data={d['name']:d for d in get_inputs(a.archive,spec['evaluation'])}
    rows=[analyze(r,data[r['file']]) for r in ev['results']]
    bymodel=[]
    for model in ('SPMe','DFN'):
      rr=[r for r in rows if r['model']==model];low=next(r for r in rr if '0p5C' in r['file']);high=next(r for r in rr if '_1C' in r['file'])
      i0=low['associations']['current_A']['range'];i1=high['associations']['current_A']['range']
      b0=low['metrics']['bias_mV'];b1=high['metrics']['bias_mV']
      equivalent=[r['metrics']['bias_mV']/1000/np.mean([b['current_mean_A'] for b in r['bins']]) for r in (low,high)]
      bymodel.append(dict(model=model,delta_bias_mV=b1-b0,bias_ratio_1C_to_05C=b1/b0,bias_divided_by_physical_current_ohm=equivalent,note='Equivalent residual/current is a descriptive quotient, not contact resistance identification. Two rates on one cell do not identify linear ohmic vs kinetic vs OCV causes.'))
    report=dict(classification='POSTHOC_RESIDUAL_DIAGNOSTIC_NOT_REFIT_OR_NEW_VALIDATION',plan_sha256=sha(planpath),evaluation_sha256=sha(evaluation),rows=rows,cross_rate=bymodel,parameter_audit=parameter_audit())
    dump(OUT/'RESIDUAL_ANALYSIS.json',report)
    import matplotlib;matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    fig,axes=plt.subplots(1,3,figsize=(14,4.2));styles={'SPMe':'-','DFN':'--'}
    for r in rows:
      bins=r['bins'];rate='0.5C' if '0p5C' in r['file'] else '1C';color='tab:blue' if rate=='0.5C' else 'tab:red';label=rate+' '+r['model']
      for ax,key in zip(axes,['time_mean_s','relative_Ah_mean','temperature_change_mean_C']):ax.plot([b[key] for b in bins],[b['bias_mV'] for b in bins],styles[r['model']],color=color,marker='o',markersize=3,label=label)
    for ax,xlabel in zip(axes,['Elapsed time (s)','Relative discharged capacity','Measured temperature change (°C)']):ax.set_xlabel(xlabel);ax.axhline(0,color='black',linewidth=.7);ax.grid(alpha=.2)
    axes[0].set_ylabel('Model − measurement, mean residual (mV)');axes[2].legend(fontsize=8)
    fig.suptitle('POST-HOC E66 residuals: 10 capacity-bin means / session; not independent replicates')
    fig.tight_layout();fig.savefig(OUT/'residual_aggregates.png',dpi=180);plt.close(fig)
    dump(OUT/'RECEIPT.json',{'analysis_sha256':sha(OUT/'RESIDUAL_ANALYSIS.json'),'figure_sha256':sha(OUT/'residual_aggregates.png'),'models':2,'sessions':2,'cells':1,'no_new_solver_runs':True,'new_physical_fit':False,'blind_files_read':0})
    print(json.dumps([dict(model=r['model'],file=Path(r['file']).name,**r['metrics']) for r in rows],indent=2))
if __name__=='__main__':main()
