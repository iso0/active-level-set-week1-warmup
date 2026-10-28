"""One cached-result analysis; acquires an Astra slot before numerical imports."""
import argparse
import hashlib
import json
from pathlib import Path
from control import ROOT,atomic,event,lock,now,read,sha
from queue_store import Queue
from resources import Slot

def main():
    output=ROOT/'results/analysis_dev_v1';output.mkdir(parents=True,exist_ok=True)
    with lock(ROOT/'runtime/analysis_dev_v1.lck',wait=0):
        if (output/'ANALYSIS.json').exists():
            print('Cached analysis already complete; no repeat');return
        q=Queue(ROOT)
        with q.connect() as c:units=[dict(x) for x in c.execute("SELECT * FROM units WHERE phase='DEV_V1'")]
        assert len(units)==64 and all(u['status'] in ('COMPLETE','FAILED') for u in units),'DEV_NOT_TERMINAL'
        with Slot() as slot:
            import numpy as np
            import matplotlib
            matplotlib.use('Agg')
            import matplotlib.pyplot as plt
            import csv
            from research_v1.worker import metrics
            from research_v1.worlds import maximin
            manifest=read(ROOT/'FROZEN_DEV_V1.json');assert all(sha(ROOT/p)==h for p,h in manifest['source_hashes'].items())
            arms=manifest['arms'];families=list(dict.fromkeys(w['family'] for w in manifest['worlds']))
            results=[];integrity=[];failures=[];unit_files={};metric_names=['ba','positive_recall','negative_recall','error','regional_error','outside_error','log_loss','brier','rmse']
            for u in units:
                slot.check()
                if u['status']!='COMPLETE':failures.append({'id':u['id'],'status':u['status'],'error':u['error']});continue
                r=read(ROOT/u['result']);assert sha(ROOT/u['result'])==u['result_sha'];unit_files[u['id']]=u['result_sha']
                directory=ROOT/'results/dev_v1'/u['id']
                with np.load(directory/'world.npz') as saved:w={k:saved[k] for k in saved.files}
                records=r['records'];assert [a['budget'] for a in records]==list(range(8,25,2))
                assert len(set(r['paid']))==len(r['paid'])==24 and len(r['queries'])==16
                for row in records:
                    assert row['paid_ids']==r['paid'][:row['budget']]
                    assert sha(ROOT/row['predictions_file'])==row['predictions_sha256']
                    with np.load(ROOT/row['predictions_file']) as pred:
                        for arm in arms:
                            actual=metrics(pred[arm+'_probability'][256:],pred[arm+'_mean'][256:],w)
                            for key,value in actual.items():
                                if value is None:assert row['arms'][arm]['metrics'][key] is None
                                else:assert abs(row['arms'][arm]['metrics'][key]-value)<1e-12
                            assert np.min(pred[arm+'_variance'])>0
                for query in r['queries']:
                    b=query['budget_before'];before={k:v for k,v in query.items() if k not in ('observed','innovation_z','posterior_hash')}
                    data={'paid':r['paid'][:b],'observations':r['observations'][:b],'theta':query['theta_before'],'query':before}
                    assert hashlib.sha256(json.dumps(data,sort_keys=True).encode()).hexdigest()==query['posterior_hash']
                    assert query['paid_ids_before']==r['paid'][:b] and query['query_id']==r['paid'][b]
                    assert query['observed']==r['observations'][b]
                    s2=query['latent_variance_before']+query['noise_variance_before'];assert s2>0
                    assert abs((query['observed']-query['mean_before'])/np.sqrt(s2)-query['innovation_z'])<1e-12
                    disk=read(directory/f'prequery_B{b:02d}.json');assert disk=={**before,'posterior_hash':query['posterior_hash']}
                    if r['path']=='maximin':assert maximin(w['x'][:256],r['paid'][:b])==query['query_id']
                    elif b%2==0:
                        row=next(z for z in records if z['budget']==b)
                        with np.load(ROOT/row['predictions_file']) as a:
                            score=-np.abs(a['strong_probability'][:256]-.5);score[np.array(r['paid'][:b])]=-np.inf
                            assert int(np.argmax(score))==query['query_id']
                hits=[i+1 for i,j in enumerate(r['paid']) if w['region'][j]]
                for arm in arms:
                    rows=[z['arms'][arm]['metrics'] for z in records]
                    summary={'id':r['id'],'family':r['family'],'seed':r['seed'],'path':r['path'],'arm':arm,
                        'first_region_hit':hits[0] if hits else None,'paid_region_hits':len(hits),'cpu_seconds_joint_four_models':r['cpu_seconds'],
                        'wall_seconds_joint_four_models':r['wall_seconds'],'peak_rss_bytes':r['peak_rss_bytes']}
                    for key in metric_names:
                        yy=[z[key] for z in rows]
                        summary[key+'_aulc']=float(np.trapezoid(yy,dx=2)/16) if all(y is not None for y in yy) else None
                        summary[key+'_b24']=yy[-1]
                    for target in (.90,.93,.95):
                        good=[z['ba'] is not None and z['ba']>=target for z in rows]
                        confirms=[records[j+1]['budget'] for j in range(len(good)-1) if good[j] and good[j+1]]
                        summary[f'attain_{target:.2f}']=confirms[0] if confirms else None
                        summary[f'burden_{target:.2f}']=confirms[0] if confirms else 25
                    last=records[-1]['arms'][arm]['diagnostics'];summary['null_weight_b24']=last['null_weight'];summary['noise_sd_b24']=float(np.exp(last['theta'][-1]))
                    d=np.array(last['component_logdet']);z=np.array(last['component_quadratic']);weights=np.array(last['weights'])
                    summary['evidence_fit_gain_b24']=float(weights@(.5*(z[0]-z)))
                    summary['evidence_logdet_penalty_b24']=float(weights@(.5*(d-d[0])))
                    summary['latent_trace_extra_b24']=float(.36*np.dot(weights[1:],last['gate_reference_trace'])) if arm in ('gated','trace_match') else (0 if arm=='strong' else float(.36*(1-weights[0])))
                    if hits:
                        post=[z for z in records if z['budget']>=max(8,hits[0])]
                        summary['post_hit_regional_error_mean']=float(np.mean([z['arms'][arm]['metrics']['regional_error'] for z in post]))
                    else:summary['post_hit_regional_error_mean']=None
                    results.append(summary)
                integrity.append({'id':u['id'],'status':'PASS','budgets':9,'prequery_hashes':16,'scope':'All cached metrics and paths; margin rankings at even budgets, odd ranking not reconstructible from scalar receipt.'})
            fields=list(results[0]) if results else []
            with (output/'PER_WORLD_PATH_MODEL.csv').open('w',newline='',encoding='utf-8') as h:
                writer=csv.DictWriter(h,fieldnames=fields);writer.writeheader();writer.writerows(results)
            index={(r['family'],r['seed'],r['path'],r['arm']):r for r in results}
            rng=np.random.default_rng(716204)
            def contrast(arm,control,key,path=None,group=None):
                groups=[]
                for family in group or families:
                    deltas=[]
                    for w in manifest['worlds']:
                        if w['family']!=family:continue
                        ps=[path] if path else manifest['paths'];values=[]
                        for panel in ps:
                            a=index.get((family,w['seed'],panel,arm));b=index.get((family,w['seed'],panel,control))
                            if a and b and a[key] is not None and b[key] is not None:values.append(a[key]-b[key])
                        if len(values)==len(ps):deltas.append(float(np.mean(values)))
                    if deltas:groups.append(np.asarray(deltas))
                if not groups:return {'mean':None,'worlds':0,'interval':None}
                boot=np.mean([np.mean(rng.choice(g,(2000,len(g)),replace=True),axis=1) for g in groups],axis=0)
                return {'mean':float(np.mean([g.mean() for g in groups])),'worlds':sum(map(len,groups)),
                        'interval':np.quantile(boot,[.025,.975]).tolist(),'families_with_data':len(groups)}
            contrasts={}
            for panel in [None,*manifest['paths']]:
                label=panel or 'world_average_of_both_paths';contrasts[label]={}
                for arm,ctrl in [('compact','strong'),('gated','strong'),('trace_match','strong'),('gated','trace_match')]:
                    contrasts[label][arm+'__minus__'+ctrl]={key:contrast(arm,ctrl,key,panel) for key in ['ba_aulc','positive_recall_aulc','negative_recall_aulc','regional_error_aulc','log_loss_aulc','error_aulc','burden_0.90','burden_0.93','burden_0.95']}
            local=['local_shift','small_island','rotated_local'];controls=['smooth','heteroskedastic','outliers','correlated_corruption']
            screen={'local_ba_gated_minus_strong':contrast('gated','strong','ba_aulc',group=local),
                    'local_ba_gated_minus_trace':contrast('gated','trace_match','ba_aulc',group=local),
                    'local_error_gated_minus_strong':contrast('gated','strong','regional_error_aulc',group=local),
                    'control_ba_gated_minus_strong':contrast('gated','strong','ba_aulc',group=controls)}
            vals=[screen[k]['mean'] for k in screen]
            screen['passed']=not failures and all(v is not None for v in vals) and vals[0]>=.005 and vals[1]>=.005 and vals[2]<0 and vals[3]>-.01
            screen['interpretation']='Prospective DEV expansion screen, not a confirmatory scientific win.'
            family_table=[]
            for family in families:
                for arm in arms:
                    rr=[r for r in results if r['family']==family and r['arm']==arm]
                    row={'family':family,'arm':arm,'world_paths':len(rr)}
                    for key in ['ba_aulc','positive_recall_aulc','negative_recall_aulc','log_loss_aulc','regional_error_aulc','null_weight_b24','noise_sd_b24','paid_region_hits','latent_trace_extra_b24']:
                        valid=[r[key] for r in rr if r[key] is not None];row[key]=float(np.mean(valid)) if valid else None;row[key+'_defined']=len(valid)
                    for target in (.90,.93,.95):row[f'attainment_{target:.2f}']=sum(r[f'attain_{target:.2f}'] is not None for r in rr)
                    family_table.append(row)
            # Scientific figure: all families retained; pilot uncertainty is descriptive.
            fig,axes=plt.subplots(2,2,figsize=(11,8));colors={'strong':'#31383e','compact':'#d48436','gated':'#147d92','trace_match':'#a45b92'}
            for ax,key,title in zip(axes.flat,['ba_aulc','regional_error_aulc','log_loss_aulc','null_weight_b24'],['Early balanced accuracy','Regional sign error','Log loss','Baseline posterior weight at B24']):
                for j,arm in enumerate(arms):
                    vv=[next(r[key] for r in family_table if r['family']==f and r['arm']==arm) for f in families]
                    ax.plot(np.arange(len(families))+.07*(j-1.5),vv,'o-',label=arm,color=colors[arm],markersize=4,lw=.9)
                ax.set_title(title);ax.set_xticks(range(len(families)),[f.replace('_','\n') for f in families],fontsize=7);ax.grid(alpha=.2)
            axes[0,0].legend(fontsize=8);fig.suptitle('DEV v1: same paid paths; 32 worlds, two dependent path panels',fontsize=12)
            fig.tight_layout();fig.savefig(output/'ALL_FAMILIES.png',dpi=150);plt.close(fig)
            info={'status':'COMPLETE_WITH_FAILURES' if failures else 'COMPLETE','utc':now().isoformat(),
                  'manifest_sha256':sha(ROOT/'FROZEN_DEV_V1.json'),'analysis_code_sha256':sha(ROOT/'analyse_dev.py'),
                  'unit_result_hashes':unit_files,'completed_units':len(integrity),'scheduled_units':64,'failures':failures,
                  'contrasts':contrasts,'screen':screen,'families':family_table,'queue':q.summary(),
                  'uncertainty':'Pointwise whole-world stratified bootstrap; four worlds per fixed family; no multiplicity guarantee.',
                  'limits':'Joint four-model timings only; matched-path attainment is not an acquisition saving; scalar odd-budget prequery receipts do not establish full ranking.'}
            atomic(output/'INTEGRITY.json',{'status':'PASS' if not failures else 'PASS_AVAILABLE_WITH_FAILURES','units':integrity,'failures':failures})
            atomic(output/'ANALYSIS.json',info)
            event('DEV_V1_ANALYSIS_COMPLETE',screen_passed=screen['passed'],completed=len(integrity),failed=len(failures))
            print(json.dumps({'screen':screen,'completed':len(integrity),'failed':len(failures)}))

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--threads',type=int,choices=[1],required=True);p.parse_args();main()
