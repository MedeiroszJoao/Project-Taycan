"""Publish only derived error metrics and parameter profiles, no measured curves."""
import json
from pathlib import Path
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
ROOT=Path(__file__).resolve().parents[1];OUT=ROOT/'results/e66_kinetic_calibration'
f=json.loads((OUT/'FIT_RESULT.json').read_text());ev=json.loads((OUT/'EVALUATION.json').read_text())['results'];audit=json.loads((OUT/'INDEPENDENT_AUDIT.json').read_text())
fig,ax=plt.subplots(1,3,figsize=(15,4.5),layout='constrained')
p=f['profiles'];x=[r['k'] for r in p]
for i in range(3):ax[0].plot(x,[1000*np.sqrt(r['per_pulse_MSE'][i]) for r in p],'.-',label=f'Pulso {i+1}')
ax[0].axvline(f['k'],c='black',ls='--',label=f"Ajuste: {f['k']:.3f}");ax[0].set(xlabel='Multiplicador conjunto de cinética',ylabel='RMSE durante carga (mV)',title='Perfil condicional HPPC');ax[0].legend(fontsize=8)
for model,color,offset in [('SPMe','#176b8a',-.18),('DFN','#d17935',.18)]:
 vals=[]
 for i in range(2):
  r=next(r for r in ev if r['dataset']=='DISCHARGE' and r['index']==i and r['model']==model);vals.append(r.get('RMSE_V',float('nan'))*1000)
 ax[1].bar(np.arange(2)+offset,vals,.35,label=model,color=color)
ax[1].axhline(50,c='red',ls='--',label='Limite RMSE');ax[1].set(xticks=[0,1],xticklabels=['0,5C','1C'],ylabel='RMSE absoluto (mV)',title='Transferência não cega');ax[1].legend(fontsize=8)
for model,color,offset in [('SPMe','#176b8a',-.18),('DFN','#d17935',.18)]:
 vals=[]
 for i in range(6):
  r=next(r for r in ev if r['dataset']=='GITT' and r['index']==i and r['model']==model and r['mesh']==40);vals.append(r.get('RMSE_V',float('nan'))*1000)
 ax[2].bar(np.arange(6)+offset,vals,.35,label=model,color=color)
ax[2].axhline(50,c='red',ls='--');ax[2].set(xticks=np.arange(6),xticklabels=np.arange(1,7),xlabel='Segmento da mesma célula',ylabel='RMSE relativo (mV)',title='GITT: tensão relativa ao repouso')
for a in ax:a.spines[['top','right']].set_visible(False);a.grid(axis='y',alpha=.15)
fig.suptitle('E66 • candidato eletroquímico efetivo • não representa validação diagnóstica do veículo',fontsize=12)
fig.savefig(OUT/'KINETIC_AUDIT.png',dpi=160);fig.savefig(OUT/'KINETIC_AUDIT.svg')
