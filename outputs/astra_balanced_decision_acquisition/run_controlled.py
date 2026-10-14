"""Frozen, resumable sequential comparisons. Run: freeze | checks | run | collect."""
import runtime as rt
import sys
import time
import numpy as np
from balanced_method import decisions,select_risk,select_variance,select_margin
from worlds import WORLDS,SEEDS,ARMS,make_world,PaidOracle,evaluate


def run():
    rt.verify()
    checks=rt.load(rt.ROOT/'INDEPENDENT_CHECKS.json')
    if checks.get('manifest_sha256')!=rt.sha(rt.ROOT/'MANIFEST.json'):raise RuntimeError('Reference gate manifest mismatch')
    if not checks['acceptance_pass']:raise RuntimeError('Independent checks not accepted')
    for world in WORLDS:
        for seed in SEEDS:
            rt.wait_slot();w=make_world(world,seed)
            rt.save(rt.ROOT/'worlds'/f'{world}_{seed}.json',w)
            for arm in ARMS:
                oracle=PaidOracle(w['y_pool'],w['z_pool']);paid=[];ys=[];zs=[]
                for j in w['startup']:
                    y,z=oracle.reveal(j);paid.append(int(j));ys.append(y);zs.append(z)
                for budget in range(6,11):
                    key=f'{world}_{seed}_{arm}_B{budget}';dest=rt.ROOT/'records'/f'{key}.json'
                    if dest.exists():
                        rec=rt.load(dest)
                        if rec['paid_ids']!=paid:raise RuntimeError('Cached path mismatch')
                    else:
                        rt.wait_slot();t=time.monotonic()
                        try:
                            model=rt.charged_fit(key,w['X_pool'],w['X_pool'][paid],ys,zs)
                            # Chooser decision inputs NEVER include evaluator features/outcomes.
                            dec=decisions(model,w['X_pool'],np.empty((0,4)),seed=91000+seed+budget*101)
                            test=decisions(model,w['X_pool'],w['X_test'],seed=91000+seed+budget*101)
                            p=model.predict_proba(w['X_test']);nr=len(w['X_pool'])
                            interval=model.probability_interval(w['X_test'])
                            rules={'PBR':test['decision'][nr:],'cutoff_0.5':p>=.5,
                                   'paid_fraction':p>=np.mean(ys),'posterior_mean_pi':p>=test['pi_mean']}
                            metrics={rule:evaluate(w['y_test'],p,d,w['eta_test'],interval,w['region_test']) for rule,d in rules.items()}
                            rec={'key':key,'world':world,'seed':seed,'arm':arm,'budget':budget,
                                 'paid_ids':paid.copy(),'paid_y':ys.copy(),'paid_z':zs.copy(),'status':'ok',
                                 'metrics':metrics,'p_test':p,'decisions_test':rules,'probability_interval_test':interval,
                                 'decision_numerics':dec,'test_decision_numerics':test,
                                 'paid_fraction':float(np.mean(ys)),'reference_pi_mean':dec['pi_mean'],
                                 'EVALUATOR_true_reference_pi':float(w['eta_pool'].mean()),
                                 'EVALUATOR_true_test_pi':float(w['eta_test'].mean()),
                                 'model_diagnostics':model.diagnostics,'selected':None,'query':None}
                            if not dec['numerically_accepted'] or not test['numerically_accepted']:
                                rec['status']='DECISION_NUMERICAL_STOP'
                            elif budget<10:
                                rt.wait_slot();cand=[j for j in range(nr) if j not in paid]
                                if arm=='balanced_risk':q=select_risk(model,cand,seed=20000+seed+budget*101,
                                    response_availability=w['response_availability'],decision_risk=dec['risk'])
                                elif arm=='probability_variance':q=select_variance(model,cand,w['response_availability'])
                                else:q=select_margin(dec,cand)
                                rec['query']=q;rec['selected']=q['selected']
                                if q['status']!='accepted':rec['status']=q['status']
                            rec['seconds']=time.monotonic()-t
                        except Exception as ex:
                            rec={'key':key,'world':world,'seed':seed,'arm':arm,'budget':budget,
                                 'paid_ids':paid.copy(),'status':'FAILED','error':repr(ex),'selected':None,'seconds':time.monotonic()-t}
                        rt.save(dest,rec)
                        print(f"{key}: {rec['status']} ({rec['seconds']:.1f}s)",flush=True)
                    if rec['status']!='ok':break
                    if budget<10:
                        j=int(rec['selected']);y,z=oracle.reveal(j);paid.append(j);ys.append(y);zs.append(z)
    collect()


def collect():
    rows=[rt.load(f) for f in sorted((rt.ROOT/'records').glob('*.json'))]
    worlds=[rt.load(f) for f in sorted((rt.ROOT/'worlds').glob('*.json'))]
    paths=[];contrasts=[]
    for name in WORLDS:
        for seed in SEEDS:
            by={}
            for arm in ARMS:
                records=sorted([r for r in rows if r['world']==name and r['seed']==seed and r['arm']==arm],key=lambda r:r['budget'])
                complete=len(records)==5 and all(r['status']=='ok' for r in records)
                result={'world':name,'seed':seed,'arm':arm,'complete':complete,'n_records':len(records),
                        'path':records[-1]['paid_ids'] if records else [],'stop':None if complete else (records[-1]['status'] if records else 'NOT_RUN')}
                if complete:
                    vals={m:[r['metrics']['PBR'][m] for r in records] for m in ('BA','declared_batch_loss','sensitivity','specificity','brier','log_loss','region_error','region_positive_recall','region_negative_recall')}
                    result['AULC']={m:float(np.trapezoid(v,dx=1)/4) if all(x is not None for x in v) else None for m,v in vals.items()}
                    result['B10']=records[-1]['metrics']['PBR'];by[arm]=result
                paths.append(result)
            for control in ARMS[1:]:
                a,b=by.get(ARMS[0]),by.get(control)
                rec={'world':name,'seed':seed,'contrast':f'{ARMS[0]} - {control}','complete':a is not None and b is not None}
                if rec['complete']:
                    rec['AULC']={m:None if a['AULC'][m] is None or b['AULC'][m] is None else a['AULC'][m]-b['AULC'][m] for m in a['AULC']}
                    rec['B10']={m:None if a['B10'][m] is None or b['B10'][m] is None else a['B10'][m]-b['B10'][m] for m in a['AULC']}
                    rec['paths_diverged']=a['path']!=b['path']
                    rec['first_divergence_budget']=next((i+1 for i,(x,y) in enumerate(zip(a['path'],b['path'])) if x!=y),None)
                contrasts.append(rec)
    status='COMPLETE' if len(paths)==84 and all(p['complete'] for p in paths) else 'INCOMPLETE_WITH_PRESERVED_STOPS'
    out={'status':status,'manifest':rt.load(rt.ROOT/'MANIFEST.json'),'accounting':rt.counts(),
         'numerical_checks':rt.load(rt.ROOT/'INDEPENDENT_CHECKS.json'),'worlds':worlds,
         'per_checkpoint':rows,'paths':paths,'paired_contrasts':contrasts,
         'limitations':['Prospective IID-batch risk is a training-reference proxy, not exact fixed-test-label BA.','Constructed groups evaluator only.',
                        'Synthetic comparisons do not establish SPH superiority or query savings.','C3 spent; C4 and real-data Stage A not run.']}
    rt.save(rt.ROOT/'CONTROLLED_RESULTS.json',out)
    print(status,rt.counts(),flush=True)


if __name__=='__main__':
    action=sys.argv[1] if len(sys.argv)>1 else 'freeze'
    if action=='freeze':print(rt.freeze()['frozen_utc'])
    elif action=='checks':
        import independent_checks
        independent_checks.run()
    elif action=='run':run()
    elif action=='collect':collect()
    else:raise SystemExit(action)
