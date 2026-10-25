"""Post-hoc fixed-coefficient absolute-step local sensitivity on C20/C3 ONLY.
No parameter optimization, no original freeze claim, no module/1C numeric access.
"""
from __future__ import annotations
import argparse,hashlib,json,os,platform,subprocess,sys,tempfile,time
from pathlib import Path
os.environ['PYBAMM_DISABLE_TELEMETRY']='true'
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from scripts.fit_e66_generator_b import get_inputs,simulate

def digest(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def dump(p,x):Path(p).write_text(json.dumps(x,indent=2,allow_nan=False)+'\n')
def svd_report(matrix):
 import numpy as np
 norms=np.linalg.norm(matrix,axis=0)
 scaled=matrix/np.where(norms>0,norms,1.)
 s=np.linalg.svd(matrix,compute_uv=False);sn=np.linalg.svd(scaled,compute_uv=False)
 return {'column_norms':norms.tolist(),'singular_values_raw':s.tolist(),'singular_values_unit_column':sn.tolist(),
 'rank_default':int(np.linalg.matrix_rank(matrix)),'rank_unit_column_threshold_1e_3':int(np.sum(sn>sn[0]*1e-3)),
 'rank_unit_column_threshold_1e_6':int(np.sum(sn>sn[0]*1e-6)),
 'condition_unit_column':float(sn[0]/sn[-1]) if sn[-1]>0 else None,
 'column_cosine_matrix':(scaled.T@scaled).tolist()}

def worker(args):
 import numpy as np,pybamm
 if pybamm.__version__!='26.4.2':raise RuntimeError('PyBaMM26.4.2 required')
 fit=json.loads((args.receipts/'FIT_RESULT.json').read_text());spec=json.loads((ROOT/'results/e66_calibration/PROSPECTIVE.json').read_text())
 d=get_inputs(args.archive,[spec['fit'][args.worker]])[0]
 expected=fit['fit_sources'][args.worker]
 if d['source_sha256']!=expected['source_sha256']:raise ValueError('fit member bytes drift')
 x=np.asarray(fit['parameters'],float)
 if args.param>=0:x[args.param]+=args.delta
 t,v,term=simulate(d,x,fit['effective_capacity_Ah'],mesh=40,fit=True)
 if len(t)!=150 or abs(t[-1]-.9*d['t'][-1])>1e-5:raise ValueError('incomplete fit horizon')
 if not np.all(np.isfinite(v)):raise ValueError('nonfinite output')
 # Transient synthetic predictions only; not stored in committed aggregate results.
 np.savez(args.worker_output,t=t,v=v,current_normalized=np.interp(t,d['t'],d['i'])/(fit['effective_capacity_Ah']/5.))
 print(term)

def run(args):
 import numpy as np,pybamm
 out=args.output;out.mkdir(parents=True,exist_ok=True)
 fit_path=args.receipts/'FIT_RESULT.json';fit=json.loads(fit_path.read_text())
 spec=json.loads((ROOT/'results/e66_calibration/PROSPECTIVE.json').read_text())
 if pybamm.__version__!='26.4.2':raise RuntimeError('version drift')
 allowed=get_inputs(args.archive,spec['fit'])
 if len(allowed)!=2 or any(d['source_sha256']!=e['source_sha256'] for d,e in zip(allowed,fit['fit_sources'])):raise ValueError('authorized member provenance drift')
 prospective={'classification':'POSTHOC_CAUSAL_NUMERICAL_AUDIT_NOT_REFIT','hypothesis':'rank2 caused by vanishing relative R perturbation at zero boundary',
 'falsification':'absolute R derivative null or rank deficiency persists under stable steps',
 'source_sha256':digest(__file__),'fitter_sha256':digest(ROOT/'scripts/fit_e66_generator_b.py'),'fit_receipt_sha256':digest(fit_path),
 'archive_sha256':digest(args.archive),'fit_member_sha256':[d['source_sha256'] for d in allowed],
 'fixed_parameters':fit['parameters'],'q_Ah':fit['effective_capacity_Ah'],'absolute_steps':[.001,.0001],
 'scheme':'forward absolute differences, physical units V,V,ohm; R one-sided feasible at lowerbound',
 'mesh':40,'rtol':1e-8,'atol':1e-9,'points_per_curve':150,'fit_duration_fraction':.9,
 'rank_thresholds_relative':[1e-3,1e-6],'stability_max_relative_frobenius':.01,
 'contact_derivative_analytic':'dV/dR=-I_model for imposed current and isothermal contact loss',
 'analytic_contact_max_error_V_per_ohm':.01,
 'timeout_seconds_per_solve':args.timeout,'planned_jobs':14,'sequential_jobs':True,
 'no_refit':True,'evaluation_1C_used':False,'no_structural_identifiability_claim':True,
 'python':platform.python_version(),'pybamm':pybamm.__version__}
 prospect=out/'PROSPECTIVE.json'
 if prospect.exists() and json.loads(prospect.read_text())!=prospective:raise ValueError('existing prospective mismatch')
 dump(prospect,prospective)
 jobs=[(d,-1,0.) for d in range(2)]+[(d,p,delta) for delta in [.001,.0001] for d in range(2) for p in range(3)]
 logs=[];arrays={};start=time.monotonic()
 with tempfile.TemporaryDirectory(prefix='e66_jacobian_') as temporary:
  for index,(d,p,delta) in enumerate(jobs):
   path=Path(temporary)/f'{index}.npz';started=time.monotonic()
   command=[sys.executable,str(Path(__file__).resolve()),'--archive',str(args.archive),'--receipts',str(args.receipts),'--worker',str(d),'--param',str(p),'--delta',str(delta),'--worker-output',str(path)]
   log={'dataset_index':d,'parameter_index':p,'absolute_delta':delta}
   try:
    result=subprocess.run(command,capture_output=True,text=True,timeout=args.timeout)
    if result.returncode:raise RuntimeError(result.stderr[-1600:])
    with np.load(path) as data:arrays[(d,p,delta)]={k:data[k].copy() for k in data.files}
    log.update(status='COMPLETED',termination=result.stdout.strip())
   except Exception as exc:log.update(status='FAILED',error=type(exc).__name__+': '+str(exc))
   log['seconds']=time.monotonic()-started;logs.append(log);dump(out/'JOBS.json',logs)
   print(index+1,log['status'],round(log['seconds'],2),flush=True)
 reports=[];matrices={}
 for delta in [.001,.0001]:
  try:
   mats=[];expected=[]
   for d in range(2):
    base=arrays[(d,-1,0.)];columns=[]
    for p in range(3):
     changed=arrays[(d,p,delta)]
     if not np.array_equal(base['t'],changed['t']):raise ValueError('timegrid drift')
     columns.append((changed['v']-base['v'])/delta)
    mats.append(np.column_stack(columns));expected.append(-base['current_normalized'])
   matrix=np.vstack(mats);matrices[delta]=matrix
   np.savetxt(out/f'jacobian_absolute_{delta}.csv',matrix,delimiter=',',header='dV_doffset,dV_dslope,dV_dR',comments='')
   reports.append({'absolute_delta':delta,'status':'COMPLETE','summary':svd_report(matrix),
    'contact_analytic_max_abs_error_V_per_ohm':float(np.max(abs(matrix[:,2]-np.concatenate(expected)))),
    'contact_derivative_range':list(map(float,[matrix[:,2].min(),matrix[:,2].max()]))})
  except Exception as exc:reports.append({'absolute_delta':delta,'status':'INCOMPLETE','error':str(exc)})
 stability=None
 if len(matrices)==2:stability=float(np.linalg.norm(matrices[.001]-matrices[.0001])/np.linalg.norm(matrices[.001]))
 report={'classification':'RESULTADO_EXPLORATORIO_POSTHOC','reports':reports,'step_relative_frobenius_difference':stability,
 'stable_under_predeclared_1percent':bool(stability is not None and stability<=.01),'source_optimizer_rank':fit['jacobian_rank'],
 'source_relative_contact_step_ohm':fit['parameters'][2]*1e-3,'new_absolute_steps_ohm':[.001,.0001],
 'computed_jobs':sum(x['status']=='COMPLETED' for x in logs),'planned_jobs':14,'seconds':time.monotonic()-start,
 'structural_identifiability_proven':False,'onecell_iid_confidence_intervals':False,'no_refit':True,'no_evaluation_data_used':True,
 'prospective_sha256':digest(prospect)}
 dump(out/'RESULT.json',report);print(json.dumps(report,indent=2));return report

if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--archive',type=Path,default=ROOT.parent/'project_sources/09-doi-10.5683-sp3-7jp3nm.zip');p.add_argument('--receipts',type=Path,default=ROOT/'results/tmp/e66_causal/receipts/e66_calibration');p.add_argument('--output',type=Path,default=ROOT/'results/e66_causal_audit/jacobian');p.add_argument('--timeout',type=int,default=120);p.add_argument('--worker',type=int,default=-1);p.add_argument('--param',type=int,default=-1);p.add_argument('--delta',type=float,default=0);p.add_argument('--worker-output',type=Path)
 a=p.parse_args();worker(a) if a.worker>=0 else run(a)
