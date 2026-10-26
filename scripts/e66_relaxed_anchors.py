"""Development-only rested anchors; never equate finite rest with equilibrium."""
import json
import numpy as np
from scripts import e66_module_observation_adapter as a
m=a.m
OUT=m.ROOT/'results/e66_b2_development'
def intervals(t,current,min_duration=600):
 quiet=np.isfinite(current)&(abs(current)<=1)
 edges=np.diff(np.r_[False,quiet,False].astype(int))
 return [(int(s),int(e)) for s,e in zip(np.flatnonzero(edges==1),np.flatnonzero(edges==-1)) if t[e-1]-t[s]>=min_duration and np.max(np.diff(t[s:e]))<=2]
def main():
 rows=[]
 for name in sorted(m.DEV):
  a.FILES=[name];d=a.data(0);t=d['RecordingTime'];I=d['AVL_Current'];q=np.r_[0,np.cumsum((I[1:]+I[:-1])*np.diff(t)/14400)]
  anchors=[]
  for s,e in intervals(t,I):
   tail=(t>=t[e-1]-60)&(t<=t[e-1]);v=d['BMS_Voltage'][tail]/6
   anchors.append(dict(start_s=float(t[s]),end_s=float(t[e-1]),duration_s=float(t[e-1]-t[s]),cell_net_Ah=float(q[e-1]),BMS_tail_V=float(v.mean()),AVL_tail_V=float(d['AVL_Voltage'][tail].mean()/6),BMS_tail_drift_mV_per_min=float(np.polyfit(t[tail]-t[tail][0],v,1)[0]*60000),temperature_C=float(np.mean([d[k][tail] for k in m.THERM])),tail_span_mV=float(np.ptp(v)*1000)))
  rows.append(dict(name=name,source_sha256=d['source_sha256'],anchors=anchors));print(name,len(anchors),flush=True)
 (OUT/'RELAXED_ANCHORS.json').write_text(json.dumps(dict(development_only=True,min_rest_s=600,tail_s=60,not_equilibrium_proof=True,results=rows),indent=2)+'\n')
if __name__=='__main__':main()
