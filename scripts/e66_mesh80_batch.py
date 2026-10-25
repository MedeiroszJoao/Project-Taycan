"""Bounded POST-HOC E66 1C mesh40/80 diagnostic, unchanged fitted physics.

Each solve runs in its own process, timeout120s, checkpoint before next solve.
Only model-generated curves and scalar residual metrics may leave scratch.
"""
from __future__ import annotations
import argparse,hashlib,json,os,platform,subprocess,sys,time
from importlib.metadata import version
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
os.environ['PYBAMM_DISABLE_TELEMETRY']='true'
from scripts.diagnose_e66_1c_frozen_numerics import verify_original_receipts,simulate_fixed,predictive_metrics,_voltage
from scripts.fit_e66_generator_b import get_inputs
OUT=ROOT/'results/e66_causal_audit/mesh80'
RECEIPTS=ROOT/'results/tmp/e66_causal/receipts/e66_calibration'
ORIGIN=ROOT/'results/tmp/e66_causal/receipts/tmp/stage4b/posthoc_reconstruction/POSTHOC_PROVENANCE.json'
FACTORIAL=ORIGIN.parent/'POSTHOC_1C_NUMERICAL_FACTORIAL.json'
ARCHIVE=ROOT/'results/tmp/e66_causal/research_wrapper.zip'
CASES=[(model,mesh) for model in ('SPMe','DFN') for mesh in (40,80)]
TOL={'rtol':1e-8,'atol':1e-9}
LIMIT_SECONDS=120

def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def dump(p,v):
    p=Path(p);p.parent.mkdir(parents=True,exist_ok=True)
    temp=p.with_suffix(p.suffix+'.partial');temp.write_text(json.dumps(v,indent=2,allow_nan=False)+'\n');temp.replace(p)
def environment():return {'python':platform.python_version(),**{k:version(k) for k in ('pybamm','pybammsolvers','numpy','scipy','casadi')}}

def verify():
    spec,fit,freeze,ev,name,paths=verify_original_receipts(RECEIPTS,ARCHIVE)
    origin=json.loads(ORIGIN.read_text())
    if origin['classification']!='POSTHOC_RECONSTRUCTED_AFTER_1C_OUTCOMES_KNOWN':raise ValueError('unlabeled posthoc provenance')
    for name2 in ('FIT_RESULT.json','GENERATOR_B_FREEZE.json','EVALUATION.json'):
        if sha(RECEIPTS/name2)!=origin['reconstruction_receipt_sha256'][name2]:raise ValueError('posthoc receipt hash mismatch')
    if environment()['pybamm']!='26.4.2':raise ValueError('requires PyBaMM26.4.2')
    return spec,fit,freeze,ev,name,paths

def register():
    spec,fit,freeze,ev,name,paths=verify()
    protocol={'classification':'POSTHOC_CAUSAL_NUMERICAL_DIAGNOSTIC_NOT_NEW_VALIDATION','date':'2026-10-25',
        'hypothesis':'H6 mesh truncation materially explains exposed1C voltage error',
        'refutation_criterion':'full-horizon mesh40to80 maxvoltage gap<=5mV plus empiricalRMSE>50mV and maxerror>150mV weakens mesh truncation as dominant cause at tested resolution; no claim asymptotic convergence',
        'allowed_source':name,'fixed_parameters':fit['parameters'],'fixed_effective_capacity_Ah':fit['effective_capacity_Ah'],
        'variations':{'mesh_points_per_spatial_coordinate':[40,80],'models':['SPMe','DFN'],'solver_tolerances':TOL},
        'conditions_fixed':'same correctedChen2020, SOCinitialization order, constantinitialmeasuredtemperature, scaledexperimentalcurrent, cutoffs2.5/4.5V',
        'cost_bound':{'jobs':4,'timeout_per_process_seconds':LIMIT_SECONDS,'max_child_wall_seconds':4*LIMIT_SECONDS,'threads':1,'checkpoint':'atomic JSON immediately after eachcompletedsolve or timeout','mesh160':'not scheduled'},
        'numerical_criteria':{'comparison_points':500,'minimum_coverage':.95,'must_also_complete_full_horizon':True,'max_abs_mesh_voltage_difference_V':.005},
        'original_empirical_criteria_preserved':{'RMSE_V':.05,'max_absolute_V':.15,'minimum_coverage':.95},
        'posthoc_receipts':{n:sha(p) for n,p in paths.items()},'origin_sha256':sha(ORIGIN),'wrapper_sha256':sha(ARCHIVE),
        'source_sha256':{p:sha(ROOT/p) for p in ('scripts/e66_mesh80_batch.py','scripts/fit_e66_generator_b.py','scripts/diagnose_e66_1c_frozen_numerics.py')},
        'environment':environment(),'archived_environment':freeze.get('environment'),
        'limits':['Physicalparametersnotrefit','1Cpreviouslyexposed;notblind','No protectedmodule orStage4testdata','No rawmeasuredcurvespublished','Python/NumPy/SciPydriftrecorded;comparemesh40againstarchivedtighttolbaseline','No80to160resultimplied','No parameterprecision or physicalvalidity inferred fromnumericalconvergence']}
    path=OUT/'PROSPECTIVE.json'
    if path.exists() and json.loads(path.read_text())!=protocol:raise ValueError('existing prospective protocol differs')
    dump(path,protocol);return protocol

def worker(model,mesh):
    import numpy as np
    protocol=json.loads((OUT/'PROSPECTIVE.json').read_text())
    for p,h in protocol['source_sha256'].items():
        if sha(ROOT/p)!=h:raise ValueError('post-registration source drift')
    _,fit,_,_,name,_=verify();data=get_inputs(ARCHIVE,[name])[0]
    begin=time.monotonic();record=simulate_fixed(data,fit,model,{'mesh':mesh,**TOL});summary=record['summary']
    grid=np.linspace(0,summary['target_duration_s'],500);grid=grid[grid<=summary['achieved_duration_s']+1e-8]
    volts=_voltage(record['sol'],grid);metrics=predictive_metrics(record,data)
    item={'status':'COMPLETED','classification':'POSTHOC_NUMERICAL_DIAGNOSTIC','model':model,'mesh':mesh,
        'summary':summary,'predictive_scalar_metrics':metrics,'worker_wall_s':time.monotonic()-begin,
        'model_only_curve':[{'time_s':float(t),'model_V':float(v)} for t,v in zip(grid,volts)],
        'source_cell_sha256':data['source_sha256'],'protocol_sha256':sha(OUT/'PROSPECTIVE.json'),
        'original_empirical_gate':'PASS' if metrics['rmse_V']<=.05 and metrics['max_abs_V']<=.15 and summary['coverage_fraction']>=.95 else 'FAIL',
        'raw_measured_curve_published':False}
    dump(OUT/f'{model}_{mesh}.json',item)

def compare(a,b):
    import numpy as np
    if a['status']!='COMPLETED' or b['status']!='COMPLETED':return {'gate':'INCONCLUSIVO','reason':'incomplete or interrupted solve'}
    aa=a['model_only_curve'];bb=b['model_only_curve'];n=min(len(aa),len(bb))
    t1=np.array([v['time_s'] for v in aa[:n]]);t2=np.array([v['time_s'] for v in bb[:n]])
    if n<2 or not np.allclose(t1,t2,rtol=0,atol=1e-8):raise ValueError('nonmatching comparison grid')
    gap=np.array([v['model_V'] for v in aa[:n]])-np.array([v['model_V'] for v in bb[:n]])
    full=all(r['summary']['complete_full_horizon'] and r['summary']['coverage_fraction']>=.95 for r in (a,b))
    maxgap=float(np.max(abs(gap)))
    return {'gate':('PASS' if maxgap<=.005 else 'FAIL') if full else 'INCONCLUSIVO','full_horizon_both':full,'points':n,
        'max_abs_mesh_difference_V':maxgap,'RMS_mesh_difference_V':float(np.sqrt(np.mean(gap**2))),
        'mean_mesh40_minus_mesh80_V':float(np.mean(gap)),'mesh40_empirical_gate':a['original_empirical_gate'],'mesh80_empirical_gate':b['original_empirical_gate'],
        'interpretation':'numericalgateonly; empiricalfailureunchangedifFAIL;notasymptoticconvergence'}

def baseline_check(record,archived):
    old=archived['models'][record['model']]['cases']['D_BOTH_ORIGINAL_COMPARATOR']
    metric=record['predictive_scalar_metrics'];deltas={k:metric[k]-old['predictive'][k] for k in ('rmse_V','bias_V','max_abs_V')}
    return {'metric_differences_from_archived_mesh40_tighttol_V':deltas,'within_0_1mV_all_scalar_metrics':all(abs(v)<=.0001 for v in deltas.values()),'limitation':'archivedmesh40fullcurveunavailable; scalarsnotbytewiseorpointwiseequality'}

def run():
    protocol=register();receipts=[]
    for model,mesh in CASES:
        output=OUT/f'{model}_{mesh}.json'
        if output.exists():
            record=json.loads(output.read_text())
            if record.get('protocol_sha256')!=sha(OUT/'PROSPECTIVE.json'):raise ValueError('checkpoint protocol mismatch')
        else:
            start=time.monotonic();env=dict(os.environ,OPENBLAS_NUM_THREADS='1',OMP_NUM_THREADS='1',MKL_NUM_THREADS='1',PYBAMM_DISABLE_TELEMETRY='true')
            with (OUT/f'{model}_{mesh}.log').open('w') as log:
                try:
                    proc=subprocess.run([sys.executable,str(Path(__file__).resolve()),'worker','--model',model,'--mesh',str(mesh)],cwd=ROOT,env=env,stdout=log,stderr=subprocess.STDOUT,timeout=LIMIT_SECONDS)
                    if proc.returncode or not output.exists():raise RuntimeError('workerexit'+str(proc.returncode))
                    record=json.loads(output.read_text())
                except (subprocess.TimeoutExpired,RuntimeError) as exc:
                    record={'status':'TIMEOUT' if isinstance(exc,subprocess.TimeoutExpired) else 'FAILED','model':model,'mesh':mesh,'error':str(exc),'elapsed_s':time.monotonic()-start,'protocol_sha256':sha(OUT/'PROSPECTIVE.json')};dump(output,record)
        receipts.append({'model':model,'mesh':mesh,'status':record['status'],'output_sha256':sha(output)})
        dump(OUT/'progress.json',{'completed_attempts':receipts,'planned':len(CASES)})
        print(json.dumps(receipts[-1]),flush=True)
    report={'classification':'POSTHOC_CAUSAL_DIAGNOSTIC','environment':environment(),'original_1C_empirical_failure_preserved':True,'mesh160':'NOT_EXECUTED','models':{},'protocol_sha256':sha(OUT/'PROSPECTIVE.json')}
    archived=json.loads(FACTORIAL.read_text())
    for model in ('SPMe','DFN'):
        a=json.loads((OUT/f'{model}_40.json').read_text());b=json.loads((OUT/f'{model}_80.json').read_text())
        report['models'][model]={'comparison':compare(a,b),'mesh40_archived_check':baseline_check(a,archived) if a['status']=='COMPLETED' else None,
            'cases':[{k:v for k,v in r.items() if k!='model_only_curve'} for r in (a,b)]}
    dump(OUT/'SUMMARY.json',report);print(json.dumps(report,indent=2),flush=True)

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('mode',choices=['run','worker']);p.add_argument('--model',choices=['SPMe','DFN']);p.add_argument('--mesh',type=int,choices=[40,80]);a=p.parse_args()
    if a.mode=='worker':worker(a.model,a.mesh)
    else:run()
