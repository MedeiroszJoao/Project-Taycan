import json
from pathlib import Path
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
ROOT=Path(__file__).resolve().parents[1];OUT=ROOT/'results/e66_ocp_recalibration';rows=json.loads((OUT/'INDEPENDENT_AUDIT.json').read_text())['results']
fig,axs=plt.subplots(1,2,figsize=(10,4.4),layout='constrained')
labels=['C/20*','C/3*','0,5C','1C']
for model,color,shift in [('SPMe','#236e85',-.18),('DFN','#c97c31',.18)]:
 x=[];rm=[];mx=[]
 for r in rows:
  if r['model']!=model or r['dataset'] not in ['TRAIN','DISCHARGE']:continue
  x.append(r['index']+(2 if r['dataset']=='DISCHARGE' else 0));rm.append(r['RMSE_V']*1000);mx.append(r['max_error_V']*1000)
 for ax,vals in zip(axs,[rm,mx]):ax.bar(np.array(x)+shift,vals,.35,label=model,color=color)
for ax,limit,title in zip(axs,[50,150],['Erro quadrático médio','Erro absoluto máximo']):
 ax.axhline(limit,color='#b13a37',ls='--',label=f'Limite: {limit} mV');ax.set(xticks=np.arange(4),xticklabels=labels,ylabel='mV por célula',title=title);ax.spines[['top','right']].set_visible(False);ax.grid(axis='y',alpha=.15);ax.legend(fontsize=8)
fig.suptitle('Qualificação elétrica restrita • E66 a aproximadamente 25°C',fontsize=12)
fig.supxlabel('* Desenvolvimento. 0,5C/1C: transferência não cega. Não demonstra diagnóstico do veículo.',fontsize=9)
fig.savefig(OUT/'FINAL_VOLTAGE_GATES.svg');fig.savefig(OUT/'FINAL_VOLTAGE_GATES.png',dpi=160)
