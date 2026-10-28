"""Cached analysis of the single v2 discriminator, with whole-world contrasts."""
import argparse
import json
from control import ROOT,atomic,event,lock,now,read,sha
from queue_store import Queue
from resources import Slot

def main():
    output=ROOT/'results/analysis_dev_v2';output.mkdir(parents=True,exist_ok=True)
    with lock(ROOT/'runtime/analysis_dev_v2.lck',wait=0):
        if (output/'ANALYSIS.json').exists():print('Already complete; no repeat');return
        q=Queue(ROOT)
        with q.connect() as c:units=[dict(x) for x in c.execute("SELECT * FROM units WHERE phase='DEV_V2'")]
        assert len(units)==64 and all(u['status'] in ('COMPLETE','FAILED') for u in units),'V2_NOT_TERMINAL'
        with Slot() as slot:
            import numpy as np
            import csv
            import matplotlib
            matplotlib.use('Agg')
            import matplotlib.pyplot as plt
            from research_v1.worker import metrics
            manifest=read(ROOT/'FROZEN_DEV_V2.json');assert all(sha(ROOT/p)==h for p,h in manifest['source_hashes'].items())
            families=list(dict.fromkeys(w['family'] for w in manifest['worlds']));arms=manifest['arms']
            rows=[];failures=[];integrity=[];curves={};costs=[]
            for u in units:
                slot.check()
                if u['status']!='COMPLETE':failures.append({'id':u['id'],'error':u['error']});continue
                assert sha(ROOT/u['result'])==u['result_sha'];r=read(ROOT/u['result'])
                pp=ROOT/'results'/('unit__'+r['parent_id']+'.json');assert sha(pp)==r['parent_sha256']==manifest['parents'][r['parent_id']]
                parent=read(pp);assert r['paid']==parent['paid']
                with np.load(ROOT/'results/dev_v1'/r['parent_id']/'world.npz') as s:w={k:s[k] for k in s.files}
                assert [z['budget'] for z in r['records']]==list(range(8,25,2))
                for record,old in zip(r['records'],parent['records']):
                    assert record['paid_ids']==old['paid_ids'] and sha(ROOT/record['predictions_file'])==record['predictions_sha256']
                    assert record['parent_predictions_sha256']==old['predictions_sha256']
                    with np.load(ROOT/record['predictions_file']) as p,np.load(ROOT/old['predictions_file']) as orig:
                        for arm in ('strong','gated'):
                            for key in ('mean','variance','probability'):assert np.array_equal(p[arm+'_'+key],orig[arm+'_'+key])
                        for arm in arms:
                            actual=metrics(p[arm+'_probability'][256:],p[arm+'_mean'][256:],w)
                            for key,value in actual.items():
                                target=record['arms'][arm]['metrics'][key]
                                assert value==target if value is None else abs(value-target)<1e-12
                hits=[j+1 for j,i in enumerate(r['paid']) if w['region'][i]]
                for arm in arms:
                    mm=[z['arms'][arm]['metrics'] for z in r['records']];dd=r['records'][-1]['arms'][arm]['diagnostics']
                    row={'family':r['family'],'seed':r['seed'],'path':r['path'],'arm':arm,'unit':r['id'],
                         'first_region_hit':hits[0] if hits else None,'paid_region_hits':len(hits),'null_weight_b24':dd['null_weight']}
                    for key in ('ba','positive_recall','negative_recall','error','regional_error','outside_error','log_loss','brier','rmse'):
                        values=[z[key] for z in mm];row[key+'_aulc']=float(np.trapezoid(values,dx=2)/16) if all(v is not None for v in values) else None
                        row[key+'_b24']=values[-1]
                    for target in (.90,.93,.95):
                        good=[z['ba'] is not None and z['ba']>=target for z in mm]
                        passed=[10+2*j for j in range(8) if good[j] and good[j+1]]
                        row[f'attain_{target:.2f}']=passed[0] if passed else None;row[f'burden_{target:.2f}']=passed[0] if passed else 25
                    post=[z for z in r['records'] if hits and z['budget']>=max(8,hits[0])]
                    row['post_hit_regional_error_mean']=float(np.mean([z['arms'][arm]['metrics']['regional_error'] for z in post])) if post else None
                    rows.append(row);curves[(r['family'],r['seed'],r['path'],arm)]=[z['ba'] for z in mm]
                costs.append({'id':r['id'],'incremental_cpu_seconds':r['cpu_seconds'],'incremental_wall_seconds':r['wall_seconds'],
                              'peak_rss_bytes':r['peak_rss_bytes'],'new_queries':0,'new_background_optimizations':0,
                              'dense_factorizations':sum(z['actual_operations']['dense_factorizations'] for z in r['records']),
                              'rankone_updates':sum(z['actual_operations']['rankone_updates'] for z in r['records'])})
                integrity.append({'id':r['id'],'status':'PASS','parent_path_hash_verified':True,'cached_controls_byte_identical':True,'predictions_recomputed_metrics':True})
            with (output/'PER_WORLD_PATH_MODEL.csv').open('w',encoding='utf-8',newline='') as h:
                writer=csv.DictWriter(h,fieldnames=list(rows[0]));writer.writeheader();writer.writerows(rows)
            index={(r['family'],r['seed'],r['path'],r['arm']):r for r in rows};rng=np.random.default_rng(716204)
            def contrast(arm,control,key,path=None,group=None,hit_only=False):
                blocks=[]
                for f in group or families:
                    changes=[]
                    for w in manifest['worlds']:
                        if w['family']!=f:continue
                        values=[];panels=[path] if path else manifest['paths']
                        for panel in panels:
                            a=index.get((f,w['seed'],panel,arm));b=index.get((f,w['seed'],panel,control))
                            if a and b and a[key] is not None and b[key] is not None and (not hit_only or a['first_region_hit'] is not None):values.append(a[key]-b[key])
                        if len(values)==len(panels):changes.append(float(np.mean(values)))
                    if changes:blocks.append(np.array(changes))
                if not blocks:return {'mean':None,'interval':None,'worlds':0}
                boot=np.mean([rng.choice(g,(2000,len(g)),replace=True).mean(1) for g in blocks],axis=0)
                return {'mean':float(np.mean([g.mean() for g in blocks])),'interval':np.quantile(boot,[.025,.975]).tolist(),
                        'worlds':sum(map(len,blocks)),'families_with_data':len(blocks)}
            contrasts={}
            for panel in (None,*manifest['paths']):
                cc={}
                for arm,ctrl in [('coherent','strong'),('coherent','gated'),('coherent_trace','strong'),('coherent','coherent_trace')]:
                    cc[arm+'__minus__'+ctrl]={key:contrast(arm,ctrl,key,panel) for key in ('ba_aulc','positive_recall_aulc','negative_recall_aulc','regional_error_aulc','log_loss_aulc','error_aulc','burden_0.90','burden_0.93','burden_0.95')}
                    cc[arm+'__minus__'+ctrl]['conditional_post_hit_error']=contrast(arm,ctrl,'post_hit_regional_error_mean',panel,hit_only=True)
                contrasts[panel or 'world_average_of_both_paths']=cc
            local=['local_shift','small_island','rotated_local'];controls=['smooth','heteroskedastic','outliers','correlated_corruption']
            screen={'local_ba_coherent_minus_strong':contrast('coherent','strong','ba_aulc',group=local),
                    'local_ba_coherent_minus_trace':contrast('coherent','coherent_trace','ba_aulc',group=local),
                    'local_error_coherent_minus_strong':contrast('coherent','strong','regional_error_aulc',group=local),
                    'control_ba_coherent_minus_strong':contrast('coherent','strong','ba_aulc',group=controls)}
            vals=[screen[k]['mean'] for k in screen];screen['passed']=not failures and all(v is not None for v in vals) and vals[0]>=.005 and vals[1]>=.005 and vals[2]<0 and vals[3]>-.01
            table=[]
            for f in families:
                for arm in arms:
                    rr=[r for r in rows if r['family']==f and r['arm']==arm];a={'family':f,'arm':arm,'world_paths':len(rr)}
                    for key in ('ba_aulc','positive_recall_aulc','negative_recall_aulc','regional_error_aulc','log_loss_aulc','null_weight_b24','paid_region_hits'):
                        vv=[r[key] for r in rr if r[key] is not None];a[key]=float(np.mean(vv)) if vv else None;a[key+'_defined']=len(vv)
                    for t in (.90,.93,.95):a[f'attainment_{t:.2f}']=sum(r[f'attain_{t:.2f}'] is not None for r in rr)
                    table.append(a)
            colors={'strong':'#31383e','gated':'#147d92','coherent':'#bb5d30','coherent_trace':'#9460a1'}
            fig,axes=plt.subplots(2,4,figsize=(14,6),sharex=True)
            for ax,f in zip(axes.flat,families):
                for arm in arms:
                    values=[v for k,v in curves.items() if k[0]==f and k[3]==arm]
                    ax.plot(manifest['budgets'],np.mean(values,axis=0),label=arm,color=colors[arm])
                ax.set_title(f.replace('_',' '),fontsize=10);ax.set_ylim(.45,1.01);ax.set_xlabel('Paid queries');ax.grid(alpha=.2)
            axes[0,0].legend(fontsize=7);axes[0,0].set_ylabel('Balanced accuracy');axes[1,0].set_ylabel('Balanced accuracy')
            fig.suptitle('DEV v2: same inspected worlds and paid paths; four worlds per family',fontsize=12);fig.tight_layout();fig.savefig(output/'LEARNING_CURVES.png',dpi=150);plt.close(fig)
            # Deterministic visualization subjects: first small-island world, both
            # original paths. Public-input projection; it is not a 2D boundary.
            seed=next(w['seed'] for w in manifest['worlds'] if w['family']=='small_island')
            fig,axes=plt.subplots(1,2,figsize=(10,4))
            for ax,panel in zip(axes,manifest['paths']):
                pid=f'dev_v1_small_island_{seed}_{panel}';parent=read(ROOT/'results'/('unit__'+pid+'.json'))
                with np.load(ROOT/'results/dev_v1'/pid/'world.npz') as w:
                    x=w['x'];labels=w['labels'];paid=np.array(parent['paid'])
                    ax.scatter(x[256:,0],x[256:,1],c=labels[256:],cmap='coolwarm',s=6,alpha=.3,vmin=0,vmax=1)
                    ax.plot(x[paid,0],x[paid,1],'-o',color='#252e35',ms=3,lw=.7)
                    for b,i in enumerate(paid):ax.annotate(str(b+1),(x[i,0],x[i,1]),fontsize=6)
                ax.set_title(panel);ax.set_xlabel('x1');ax.set_ylabel('x2')
            fig.suptitle('Actual shared query paths: 4D world projected onto x1,x2; colors = latent labels',fontsize=10)
            fig.tight_layout();fig.savefig(output/'QUERY_REPLAY_PROJECTION.png',dpi=160);plt.close(fig)
            result={'status':'COMPLETE_WITH_FAILURES' if failures else 'COMPLETE','utc':now().isoformat(),
                    'manifest_sha256':sha(ROOT/'FROZEN_DEV_V2.json'),'analysis_code_sha256':sha(ROOT/'analyse_v2.py'),
                    'completed_units':len(integrity),'scheduled_units':64,'failures':failures,'contrasts':contrasts,
                    'screen':screen,'families':table,'costs':costs,'queue':q.summary(),
                    'scope':'DEV on previously inspected worlds; both paths averaged within world; pointwise descriptive bootstrap.',
                    'limits':'No new acquisition paths or independent TEST; incremental v2 CPU is not standalone whole-learner CPU.'}
            atomic(output/'INTEGRITY.json',{'status':'PASS' if not failures else 'PASS_AVAILABLE_WITH_FAILURES','units':integrity,'failures':failures})
            atomic(output/'ANALYSIS.json',result);event('DEV_V2_ANALYSIS_COMPLETE',screen_passed=screen['passed'],completed=len(integrity),failed=len(failures))
            print(json.dumps({'screen':screen,'complete':len(integrity),'failed':len(failures)}))

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--threads',type=int,choices=[1],required=True);p.parse_args();main()
