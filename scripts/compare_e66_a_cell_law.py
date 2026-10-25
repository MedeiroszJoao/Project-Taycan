"""Restricted constitutive-law audit of A, not full vehicle replay."""
import sys,json,hashlib
from pathlib import Path
import numpy as np
ROOT=Path(__file__).resolve().parents[1];sys.path[:0]=[str(ROOT),str(ROOT/'src/simulator')]
from taycan_sim.model import ModelConfig
from scripts.e66_pulse_discrimination import extract
OUT=ROOT/'results/e66_kinetic_calibration'
def predict(t,I,duration,T,age,p):
 r_age=1+p.age_resistance_gain*age;q=p.capacity_ah_cell*(1-p.age_capacity_loss*age)
 r0=p.r0_ohm_cell*r_age*max(.5,1+p.resistance_cold_coeff_per_K*(p.resistance_reference_C-T));r1=p.r1_ohm_cell*r_age
 elapsed=np.minimum(t,duration);ocv_delta=-p.ocv_span_v*I*elapsed/(3600*q)
 polarization=I*r1*(1-np.exp(-elapsed/p.rc_tau_s))*np.exp(-np.maximum(t-duration,0)/p.rc_tau_s)
 return ocv_delta-polarization-I*r0*(t<duration)
def main():
 rows=[];p=ModelConfig()
 for ds in ['HPPC','GITT']:
  for f,t,actual in extract(ds)[0]:
   for age in [0,.15]:
    v=predict(t,f['current_A'],f['duration_s'],f['initial_T_C'],age,p);e=v-actual
    rows.append({'dataset':ds,'index':f['index'],'age':age,'relative_RMSE_V':float(np.sqrt(np.mean(e*e))),'relative_max_error_V':float(np.max(abs(e))),'bias_V':float(e.mean()),'model_V':v.tolist(),'model_times_s':t.tolist()})
 out={'scope':'analytic constant-current single-cell reduction of A 1RC constitutive law; isothermal homogeneous cell; NOT A full backend or features validation','assumptions':'zero initial polarization, linear OCV, measured initial temperature, two declared age levels; no parameter fit; no vehicle energy/thermal replay','source_sha256':hashlib.sha256((ROOT/'src/simulator/taycan_sim/model.py').read_bytes()).hexdigest(),'results':rows}
 (OUT/'A_CELL_LAW.json').write_text(json.dumps(out,indent=2)+'\n')
if __name__=='__main__':main()
