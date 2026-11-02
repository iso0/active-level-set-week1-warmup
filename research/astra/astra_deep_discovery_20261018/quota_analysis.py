"""Fixed-share descriptive analysis; no fitting or scientific selection."""
import os
for key in ('OMP_NUM_THREADS','OPENBLAS_NUM_THREADS','MKL_NUM_THREADS','NUMEXPR_NUM_THREADS'):
    os.environ[key]='1'
import csv
import gzip
import json
from collections import defaultdict
from coordination import HERE,Slot,now
import ledger

with Slot():
    import numpy as np
    from threadpoolctl import threadpool_limits
    with threadpool_limits(1):
        all_results={}
        for phase in ('EXTRADEV','EXTRATEST'):
            rows=[];invariants=[];index={};pairs=defaultdict(list)
            for path in sorted((HERE/'results'/phase).glob('quota__*.json.gz')):
                with gzip.open(path,'rt',encoding='utf-8') as f:r=json.load(f)
                s=r['unit'];events=r['events'];local=r['local_queries']
                expected=(s['budget']-len(r['startup']))//2
                if local!=expected or any(e['reason'].startswith('local')!=(i%2==1) for i,e in enumerate(events)):
                    invariants.append(s['id'])
                e={**s,**r['metrics'][-1],**{k:r[k] for k in
                   ('target_event','target_confirmed_budget','restricted_query_burden','local_queries','triggers','cpu_seconds','wall_seconds','selection_seconds','peak_process_working_set_bytes')}}
                rows.append(e);index[(s['family'],s['seed'],s['selector'])]=(e,r)
            with ledger.database() as c:
                unfinished=[dict(r) for r in c.execute("SELECT id,status,error FROM units WHERE phase=? AND status!='COMPLETE'",(phase,))]
            for family,seed,arm in index:
                if arm!='quota_surprise':continue
                other=index.get((family,seed,'quota_no_surprise'))
                if not other:continue
                (a,ar),(b,br)=index[(family,seed,arm)],other
                if ar['evaluator']['hash']!=br['evaluator']['hash'] or ar['paid_ids'][:8]!=br['paid_ids'][:8]:
                    invariants.append(a['id']+' unmatched world/startup')
                pairs[family].append((a,b))
            rng=np.random.default_rng(20261018);effects=[]
            for metric in ('error','boundary_error','island_recall','recall_positive','recall_negative','brier','log_loss','restricted_query_burden'):
                values={f:np.array([a[metric]-b[metric] for a,b in rr if a.get(metric) is not None and b.get(metric) is not None]) for f,rr in pairs.items()}
                values={f:v for f,v in values.items() if len(v)}
                if not values:continue
                point=float(np.mean([v.mean() for v in values.values()]))
                boot=sum(v[rng.integers(len(v),size=(10000,len(v)))].mean(1) for v in values.values())/len(values)
                effects.append({'metric':metric,'surprise_minus_no_surprise':point,'ci95':np.quantile(boot,[.025,.975]).tolist(),
                    'families':len(values),'pairs':sum(len(v) for v in values.values()),'descriptive_only':True})
            dst=HERE/'results'/'analysis'/('quota__'+phase);dst.mkdir(parents=True,exist_ok=True)
            if rows:
                fields=list(dict.fromkeys(k for r in rows for k in r))
                with (dst/'per_seed_endpoints.csv').open('w',newline='',encoding='utf-8') as f:
                    w=csv.DictWriter(f,fields);w.writeheader();w.writerows(rows)
            result={'phase':phase,'utc':now().isoformat(),'completed':len(rows),'unfinished':unfinished,
                'path_or_quota_errors':invariants,'effects':effects,'joint_target_unchanged':True,
                'interpretation':'surprise-informed anchor choice at exactly equal local/global expenditure; not an independent new test population',
                'families':{f:{'pairs':len(rr),'attainment_surprise':float(np.mean([a['target_event'] for a,b in rr])),
                             'attainment_no_surprise':float(np.mean([b['target_event'] for a,b in rr]))} for f,rr in pairs.items()}}
            ledger.atomic_json(dst/'RESULTS.json',result);all_results[phase]=result
        ledger.atomic_json(HERE/'results'/'QUOTA_CONTROL_RESULTS.json',all_results)
        print('Fixed-share control analysis saved; no threshold or model chosen')
