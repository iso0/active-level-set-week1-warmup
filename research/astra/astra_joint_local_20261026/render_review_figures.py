"""Presentation-only repair from cached values; no scientific computation rerun."""
from control import ROOT,read,atomic,sha,now
from resources import Slot
with Slot():
    import csv,statistics
    import matplotlib;matplotlib.use('Agg');import matplotlib.pyplot as plt
    out=ROOT/'results/completion'
    rr=list(csv.DictReader((ROOT/'results/analysis_test_v1/PER_BUDGET_METRICS.csv').open(encoding='utf8')))
    families=sorted({r['family'] for r in rr})
    fig,axes=plt.subplots(3,4,figsize=(16,10),sharex=True,sharey=True)
    for ax,fam in zip(axes.flat,families):
        for arm in ('strong_extra','fixed_extra','joint'):
            yy=[statistics.mean(float(r['ba']) for r in rr if r['family']==fam and r['arm']==arm and int(r['budget'])==b) for b in range(8,25,2)]
            ax.plot(range(8,25,2),yy,'o-',ms=3,label=arm)
        ax.axhline(.9,color='gray',lw=.7,ls=':');ax.set_title(fam.replace('_',' '),fontsize=10);ax.set_xlabel('paid observations');ax.set_ylabel('mean BA')
    h,l=axes.flat[0].get_legend_handles_labels();fig.legend(h,l,loc='upper center',bbox_to_anchor=(.5,.945),ncol=3)
    fig.suptitle('Independent TEST: every family retained; two dependent paths per world',y=.985)
    fig.subplots_adjust(top=.86,bottom=.07,left=.055,right=.985,wspace=.23,hspace=.38)
    for ext in ('png','pdf'):fig.savefig(out/('LEARNING_CURVES_REVIEWED.'+ext),dpi=150)
    plt.close(fig)
    fig,axes=plt.subplots(3,4,figsize=(16,10),sharex=True)
    for ax,fam in zip(axes.flat,families):
        directory=next(p for p in sorted((ROOT/'data/test_v1').glob('test_v1_'+fam+'_*_strong_margin')) if p.name.split('_')[-3].endswith('000'))
        parent=read(directory/'parent.json');rr=parent['queries']
        ax.errorbar([r['budget_before'] for r in rr],[r['mean_before'] for r in rr],
            yerr=[2*r['latent_variance_before']**.5 for r in rr],fmt='o',ms=3,label='saved prequery mean +/- 2 latent SD')
        ax.scatter([r['budget_before'] for r in rr],[r['observed'] for r in rr],s=12,color='black',label='subsequent noisy observation')
        ax.axhline(0,color='gray',lw=.7);ax.set_title(fam.replace('_',' '),fontsize=10);ax.set_xlabel('paid budget before query')
    h,l=axes.flat[0].get_legend_handles_labels();fig.legend(h,l,loc='upper center',bbox_to_anchor=(.5,.945),ncol=2)
    fig.suptitle('First replicate per family: all 192 prequery moments independently verified',y=.985)
    fig.subplots_adjust(top=.86,bottom=.07,left=.055,right=.985,wspace=.27,hspace=.38)
    for ext in ('png','pdf'):fig.savefig(out/('PREQUERY_REPLAY_REVIEWED.'+ext),dpi=150)
    plt.close(fig)
    atomic(ROOT/'evidence/FIGURE_RENDER_REPAIR.json',{'utc':now().isoformat(),
        'reason':'Initial completion figures had title/legend overlap at top. Original artifacts and frozen source preserved.',
        'scope':'Presentation-only regeneration from existing tables and saved prequery moments; no model or reference rerun.',
        'reviewed_outputs':['results/completion/LEARNING_CURVES_REVIEWED.png','results/completion/PREQUERY_REPLAY_REVIEWED.png']})
    print('Re-rendered cached figures; visual review still required')
