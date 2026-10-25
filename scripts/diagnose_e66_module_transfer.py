import sys,json
from pathlib import Path
import numpy as np
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from scripts import transfer_e66_to_dev_module as m
rows=[]
for name in sorted(m.DEV):
 d=m.read(name);t=d['RecordingTime'];I=d['AVL_Current'];a=int(np.flatnonzero(abs(I)>10)[0]);T=float(np.nanmean([d[k][:max(a,1)] for k in m.THERM if k in d]));V=float(np.mean(d['AVL_Voltage'][max(a-5,0):max(a,1)])/6);qpos=np.r_[0,np.cumsum((np.maximum(I[1:],0)+np.maximum(I[:-1],0))*.5*np.diff(t)/3600)];qneg=np.r_[0,np.cumsum((np.minimum(I[1:],0)+np.minimum(I[:-1],0))*.5*np.diff(t)/3600)];ch=d['AhAccu_Charge']-d['AhAccu_Charge'][0];dc=d['AhAccu_Discharge']-d['AhAccu_Discharge'][0]
 row={'name':name,'initial_active_row':a,'initial_mean_cell_V':V,'T_for_domain_check_C':T,'OCV_domain_V':[m.ocv(s,T) for s in [0,.05,.95,1]],'charge_counter_delta_Ah':float(ch[-1]),'discharge_counter_delta_Ah':float(dc[-1]),'integrated_positive_AVL_Ah':float(qpos[-1]),'integrated_negative_AVL_Ah':float(qneg[-1]),'charge_correlation':float(np.corrcoef(qpos,ch)[0,1]) if np.std(ch)>0 else None,'discharge_correlation':float(np.corrcoef(qneg,dc)[0,1]) if np.std(dc)>0 else None,'net_correlation':float(np.corrcoef(qpos+qneg,ch+dc)[0,1]),'terminal_padding_removed':d['terminal_padding_removed']};rows.append(row)
m.c.dump(m.OUT/'TRANSFER_DIAGNOSTIC.json',{'scope':'post-QC-failure diagnosis; no model fits, no prediction success claims','results':rows});print(json.dumps(rows,indent=2))
