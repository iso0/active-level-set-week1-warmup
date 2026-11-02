"""Cached-result reporting, no fit or new scientific comparison selection."""
from control import ROOT,read,atomic,sha,now
from resources import Slot

def main():
    with Slot() as slot:
        import csv,json,statistics,math
        from collections import defaultdict
        import numpy as np
        import matplotlib;matplotlib.use('Agg');import matplotlib.pyplot as plt
        audit=read(ROOT/'results/finishing/AUDIT.json');assert audit['status']=='PASS'
        a=read(ROOT/'results/analysis_test_v1/ANALYSIS.json');dev=read(ROOT/'results/analysis_dev_v1/ANALYSIS.json')
        out=ROOT/'results/completion';out.mkdir(exist_ok=True)
        def rows(path):return list(csv.DictReader((ROOT/path).open(encoding='utf8')))
        ds=rows('results/finishing/MODEL_DIAGNOSTICS.csv');hits=rows('results/finishing/HIT_DIAGNOSTICS.csv')
        per=rows('results/analysis_test_v1/PER_WORLD_PATH_MODEL.csv')
        costs=[];target=[]
        units=[read(p) for p in sorted((ROOT/'results').glob('unit__test_v1_*')) if not p.name.endswith('cached_analysis.json')]
        borrowed=statistics.mean(sum(r['fits'].get('joint',{}).get('cpu_seconds',0) for r in unit['records']) for unit in units)
        for row in a['overall']:
            extra=borrowed if row['arm'] in ('strong_extra','fixed_extra') else 0
            costs.append({'arm':row['arm'],'paid_budget':24,'reported_fit_predict_cpu_per_path':row['cpu_seconds'],
                          'borrowed_joint_fit_cpu':extra,'dependency_accounted_cpu_per_path':row['cpu_seconds']+extra,
                          'includes_query_path_construction':False})
            for t in ['0.90','0.93','0.95']:
                selected=[p for p in per if p['arm']==row['arm']]
                att=[p for p in selected if p['attained_'+t]=='True']
                target.append({'arm':row['arm'],'target':t,'paths':288,'attained':row['attained_'+t],
                    'censored_at24':288-row['attained_'+t],'restricted_burden_25':row['burden_'+t],
                    'mean_confirmed_among_attainers_ONLY':statistics.mean(float(p['confirmed_budget_'+t]) for p in att) if att else None,
                    'kept_at24':sum(p['kept_at24_'+t]=='True' for p in selected)})
        def writecsv(path,rr):
            with path.open('w',encoding='utf8',newline='') as h:
                wr=csv.DictWriter(h,rr[0].keys());wr.writeheader();wr.writerows(rr)
        writecsv(out/'COMPUTE_COST.csv',costs);writecsv(out/'TARGET_ATTAINMENT.csv',target)
        diag=[]
        for fam in sorted({r['family'] for r in ds}):
            rr=[r for r in ds if r['family']==fam and r['budget']=='24'];hh=[r for r in hits if r['family']==fam]
            dd={'family':fam,'paths':len(rr)}
            for k in ['log_noise_change','log_amplitude_change','log_length_rms_change','null_weight_fixed','null_weight_joint','location_entropy','weighted_lambda','weighted_beta_variance']:
                dd['mean_'+k]=statistics.mean(float(r[k]) for r in rr)
            for k in ['first_geometric','first_geometric_latent_positive','first_geometric_observed_positive','first_geometric_signed_target','first_geometric_observed_signed_target']:
                dd[k+'_observed_paths']=sum(bool(r[k]) for r in hh)
            dd['geometric_hits_le1_paths']=sum(int(r['count_geometric'])<=1 for r in hh)
            dd['signed_target_hits_le1_paths']=sum(int(r['count_signed_target'])<=1 for r in hh)
            dd['mean_geometric_hits']=statistics.mean(int(r['count_geometric']) for r in hh)
            dd['mean_signed_target_hits']=statistics.mean(int(r['count_signed_target']) for r in hh)
            diag.append(dd)
        writecsv(out/'FAMILY_DIAGNOSTICS_B24.csv',diag)
        concentration={}
        for ctrl in ('strong_extra','fixed_extra','joint_trace'):
            vv=[r['delta'] for r in a['screen']['local_ba_vs_'+ctrl]['per_world']]
            concentration[ctrl]={'worlds':len(vv),'positive':sum(x>1e-12 for x in vv),'negative':sum(x< -1e-12 for x in vv),
                 'ties':sum(abs(x)<=1e-12 for x in vv),'median':statistics.median(vv),'min':min(vv),'max':max(vv),
                 'mean_without_largest_POSTHOC':(sum(vv)-max(vv))/(len(vv)-1)}
        # Family-specific all-path table and transparent fixed-budget curves.
        lines=['# Same-target query burden and measured CPU','',
          'All startup, discovery and second confirmation queries are charged. Targets require two consecutive evaluations of one learner at B8,10,...24. Nonattainers are censored at24; burden25 is a prespecified penalized score, not an observed success time. Paths are dependent within144 worlds. No new acquisition was run.','',
          '|Model|BA .90 reached /288|.93|.95|Burden .90 / .93 / .95|Fit+predict CPU/path (s)|Full dependency CPU/path (s)|',
          '|---|---:|---:|---:|---|---:|---:|']
        for row,c in zip(a['overall'],costs):
            lines.append(f"|{row['arm']}|{row['attained_0.90']}|{row['attained_0.93']}|{row['attained_0.95']}|{row['burden_0.90']:.4f} / {row['burden_0.93']:.4f} / {row['burden_0.95']:.4f}|{row['cpu_seconds']:.4f}|{c['dependency_accounted_cpu_per_path']:.4f}|")
        lines+=['','The extra-null controls receive the joint optimum as a paid-data-only start. Reported arm CPU excludes producing that borrowed start; the last column adds it. They are stronger diagnostic controls, not equally cheap deployable pipelines. Joint costs include its null fit and joint optimization. Path generation is shared and accounted separately, not charged selectively to an arm.','',
          '|Joint minus control|Target|Mean restricted-burden difference|Pointwise paired-world 95% interval|',
          '|---|---|---:|---|']
        for ctrl in ('strong_extra','fixed_extra'):
            for t in ['0.90','0.93','0.95']:
                d=a['comparisons']['joint__minus__'+ctrl]['all']['burden_'+t]
                lines.append(f"|{ctrl}|{t}|{d['mean']:+.5f}|[{d['pointwise95'][0]:+.5f}, {d['pointwise95'][1]:+.5f}]|")
        lines+=['',f"Actual TEST execution: {a['total_execution_cpu_seconds']:.3f}s combined replay CPU plus {a['path_generation_cpu_seconds']:.3f}s path-construction CPU; peak {a['peak_rss_bytes']/2**20:.2f}MiB. Summed replay wall {a['total_execution_wall_seconds']:.3f}s is not campaign elapsed time because jobs ran in parallel. DEV replay CPU {dev['total_execution_cpu_seconds']:.3f}s. No physical simulator time was measured.",
          '', 'There is a small descriptive .93 burden improvement versus fixed_extra (-.073 queries), but not a consistent improvement across all targets or versus extra-strong. This does not establish acquisition efficiency or meaningful simulator savings. Attainer-only averages in CSV are selected-subset descriptions and must not replace censored comparisons.']
        (out/'SAME_TARGET_COST.md').write_text('\n'.join(lines)+'\n',encoding='utf8')
        rr=rows('results/analysis_test_v1/PER_BUDGET_METRICS.csv')
        fig,axes=plt.subplots(3,4,figsize=(15,9),sharex=True,sharey=True)
        for ax,fam in zip(axes.flat,sorted({r['family'] for r in rr})):
            for arm in ('strong_extra','fixed_extra','joint'):
                means=[statistics.mean(float(r['ba']) for r in rr if r['family']==fam and r['arm']==arm and int(r['budget'])==b) for b in range(8,25,2)]
                ax.plot(range(8,25,2),means,'o-',ms=3,label=arm)
            ax.axhline(.9,color='gray',lw=.7,ls=':');ax.set_title(fam.replace('_',' '),fontsize=10);ax.set_xlabel('paid observations');ax.set_ylabel('mean BA')
        h,l=axes.flat[0].get_legend_handles_labels();fig.legend(h,l,loc='upper center',ncol=3)
        fig.suptitle('Independent TEST: every family retained; two dependent paths per world',y=1)
        fig.tight_layout(rect=[0,0,1,.94]);fig.savefig(out/'LEARNING_CURVES.png',dpi=150);fig.savefig(out/'LEARNING_CURVES.pdf');plt.close(fig)
        result={'utc':now().isoformat(),'status':'COMPLETE','scope':'Post-TEST descriptive cached diagnostics; no new fits or gate changes',
                'world_effect_concentration':concentration,'family_diagnostics':diag,'costs':costs,'target_attainment':target,
                'test_analysis_sha256':sha(ROOT/'results/analysis_test_v1/ANALYSIS.json'),'audit_sha256':sha(ROOT/'results/finishing/AUDIT.json')}
        atomic(out/'COMPLETION_SUMMARY.json',result)
        print(json.dumps({'status':'COMPLETE','concentration':concentration,'borrowed_cpu_per_path':borrowed}))

if __name__=='__main__':main()
