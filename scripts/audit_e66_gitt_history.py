"""Independent post-hoc 25C GITT history audit; no fitting, no blind access."""
import io,json,hashlib,zipfile
from pathlib import Path
import numpy as np
from scipy.io import loadmat
ROOT=Path(__file__).resolve().parents[1]
NAME='Cell Data/Characterization/25degC/Part 1 (Full Char - C_20Dis at 25degC)/07-30-23_06.21 31974_GITT.mat'
def main():
 with zipfile.ZipFile(ROOT.parent/'project_sources/09-doi-10.5683-sp3-7jp3nm.zip') as z:
  with zipfile.ZipFile(io.BytesIO(z.read('1-Cell Data.zip'))) as q:blob=q.read(NAME)
 assert hashlib.sha256(blob).hexdigest()=='be164172c96a3c86594791459240b9f6e9205e1af05bb3abd7a685df4de4da9a'
 m=loadmat(io.BytesIO(blob),simplify_cells=True)['meas']
 t,i,v,T=[np.asarray(x,float) for x in [m['Time'],-m['Current'],m['Voltage'],m['Battery_Temp_degC']]]
 assert all(np.all(np.isfinite(x)) for x in [t,i,v,T]) and np.all(np.diff(t)>=0)
 dup=np.flatnonzero(np.diff(t)==0);conf=t[dup[np.logical_or.reduce([x[dup]!=x[dup+1] for x in [i,v,T]])]]
 first=np.r_[True,np.diff(t)>0];last=np.r_[np.diff(t)>0,True];tf=t[first]
 def integ(cur):return np.r_[0,np.cumsum((cur[1:]+cur[:-1])*.5*np.diff(tf)/3600)]
 q=integ(i[first]);ql=integ(i[last]);t,i,v,T=[x[first] for x in [t,i,v,T]]
 edges=np.diff(np.r_[False,abs(i)<=1,False].astype(int));rows=[]
 for s,e in zip(np.flatnonzero(edges==1),np.flatnonzero(edges==-1)):
  if t[e-1]-t[s]<600 or np.any((conf>=t[s])&(conf<=t[e-1])):continue
  soc=1-q[e-1]/61.259778569358865
  if not 0<=soc<=1:continue
  tail=(t>=t[e-1]-60)&(t<=t[e-1]);earlier=(t>=t[e-1]-660)&(t<=t[e-1]-600)
  rows.append(dict(time_s=float(t[e-1]),soc=float(soc),V=float(v[tail].mean()),T_C=float(T[tail].mean()),rest_s=float(t[e-1]-t[s]),last_10min_change_mV=float((v[tail].mean()-v[earlier].mean())*1000) if earlier.any() else None,tail_slope_mV_min=float(np.polyfit(t[tail]-t[tail][0],v[tail],1)[0]*60000),tail_span_mV=float(np.ptp(v[tail])*1000)))
 pairs=[]
 for j,r in enumerate(rows):
  for o in rows[j+1:]:
   if abs(r['soc']-o['soc'])<1e-4:
    pairs.append(dict(soc=r['soc'],delta_soc=o['soc']-r['soc'],gap_mV=(o['V']-r['V'])*1000,delta_T_C=o['T_C']-r['T_C'],earlier_last10min_change_mV=r['last_10min_change_mV'],later_last10min_change_mV=o['last_10min_change_mV']))
 out=dict(source=NAME,sha256=hashlib.sha256(blob).hexdigest(),status='POSTHOC_DIAGNOSTIC_NOT_VALIDATION',duplicate_rows=len(dup),conflicting_timestamps=len(conf),first_last_charge_max_gap_Ah=float(np.max(abs(q-ql))),anchors=rows,pairs=pairs,limitations=['SOC is conditional on assumed capacity and initial SOC','Finite rest is not equilibrium proof','History dependence is not uniquely attributable to hysteresis','Only 25C GITT payload opened'])
 (ROOT/'results/e66_gitt_history_audit/RESULTS.json').write_text(json.dumps(out,indent=2)+'\n')
 print(json.dumps({k:v for k,v in out.items() if k!='anchors'},indent=2))
if __name__=='__main__':main()
