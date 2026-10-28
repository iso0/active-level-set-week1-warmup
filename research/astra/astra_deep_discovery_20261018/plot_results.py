"""Frozen-family summaries; no additional GP fitting or favorable-case choice."""
import os
for k in ('OMP_NUM_THREADS','OPENBLAS_NUM_THREADS','MKL_NUM_THREADS','NUMEXPR_NUM_THREADS'):
    os.environ[k]='1'
import argparse
import json
from collections import defaultdict
from coordination import HERE,Slot
import ledger
from analyse import read_rows


def main(phase,prefix):
    with Slot():
        import numpy as np
        import matplotlib
        matplotlib.use('Agg')
        import matplotlib.pyplot as plt
        from threadpoolctl import threadpool_limits
        with threadpool_limits(1):
            rows=read_rows(phase,prefix)
            dst=HERE/'results'/'analysis'/f'{prefix}{phase}'
            data=json.loads((dst/'CONTROLLED_RESULTS.json').read_text())
            families=list(dict.fromkeys(r['unit']['family'] for r in rows))
            arms=[('simple','random'),('simple','regional'),('mixture','sur_global'),('mixture','regional')]
            if prefix=='v2__':
                arms=[('simple','random'),('simple','boundary_regional'),('structure','sur_global'),('structure','boundary_regional')]
            colors=['#888888','#c45a37','#1c75a3','#7045a0']
            grouped=defaultdict(list)
            for row in rows:
                s=row['unit'];grouped[(s['family'],s['model'],s['selector'])].append(row)
            plt.rcParams.update({'font.size':9,'axes.spines.top':False,'axes.spines.right':False})
            for metric,label in [('error','Uniform level-set error'),('boundary_error','Error in |f| ≤ 0.10'),
                                 ('island_recall','Island recall (evaluator only)')]:
                fs=families if metric!='island_recall' else [f for f in families if f.startswith('island')]
                cols=3 if len(fs)>4 else 2
                fig,axes=plt.subplots(int(np.ceil(len(fs)/cols)),cols,figsize=(12,3*np.ceil(len(fs)/cols)),squeeze=False)
                for ax,f in zip(axes.flat,fs):
                    for (m,a),color in zip(arms,colors):
                        group=grouped[(f,m,a)]
                        if not group:continue
                        bs=[e['budget'] for e in group[0]['metrics']]
                        yy=np.array([[e.get(metric,np.nan) if e.get(metric) is not None else np.nan for e in r['metrics']] for r in group])
                        if not np.isfinite(yy).any():continue
                        mu=np.nanmean(yy,axis=0)
                        ax.plot(bs,mu,color=color,label=m+'/'+a)
                        if len(group)>1:
                            se=np.nanstd(yy,axis=0,ddof=1)/np.sqrt(np.sum(np.isfinite(yy),axis=0))
                            ax.fill_between(bs,np.maximum(0,mu-1.96*se),np.minimum(1,mu+1.96*se),color=color,alpha=.12)
                    ax.set_title(f);ax.set_xlabel('Paid simulations');ax.set_ylabel(label);ax.set_ylim(0,1)
                for ax in list(axes.flat)[len(fs):]:ax.set_visible(False)
                handles,labels=axes.flat[0].get_legend_handles_labels()
                fig.legend(handles,labels,loc='lower center',ncol=2)
                fig.suptitle(f'{phase}: {label} — all registered families; mean ± 1.96 SE (descriptive)',y=.997)
                fig.tight_layout(rect=(0,.045,1,.98));fig.savefig(dst/(metric+'_curves.png'),dpi=160);plt.close(fig)
            summaries=data['families']
            fig,axes=plt.subplots(1,2,figsize=(13,6))
            for offset,((m,a),color) in enumerate(zip(arms,colors)):
                chosen=[next((r for r in summaries if r['family']==f and r['model']==m and r['selector']==a),None) for f in families]
                xx=np.arange(len(families))+(offset-1.5)*.17
                axes[0].barh(xx,[r['target_event'] if r else 0 for r in chosen],height=.15,color=color,label=m+'/'+a)
                axes[1].plot([r['restricted_query_burden'] if r else np.nan for r in chosen],xx,'o',color=color)
            for ax in axes:ax.set_yticks(np.arange(len(families)),families)
            axes[0].set_xlim(0,1);axes[0].set_xlabel('Fraction confirming joint target twice')
            axes[1].set_xlabel('Restricted query burden (censored at actual horizon)')
            axes[0].legend(fontsize=7,loc='best');fig.tight_layout();fig.savefig(dst/'attainment_and_query_burden.png',dpi=160);plt.close(fig)
            ledger.event(None,None,'SUMMARY_FIGURES',{'phase':phase,'prefix':prefix,'directory':str(dst.relative_to(HERE)),
                'fits':0,'source':'plot_results.py'})
            print(dst)


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--phase',choices=['DEV','TEST'],required=True)
    p.add_argument('--prefix',required=True);p.add_argument('--threads',choices=[1],type=int,required=True)
    a=p.parse_args();main(a.phase,a.prefix)
