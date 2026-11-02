"""Small deterministic checks, never a scientific benchmark result."""
import pickle
import numpy as np
from coordination import HERE,now
import ledger
from model import MixtureGP
from worlds import World
from quota_policy import QuotaPolicy


def run(slot,unit,attempt):
    world=World('smooth',171734,pool_size=48,eval_size=32,ref_size=16,startup=4)
    checks=[]
    for arm in ('quota_surprise','quota_no_surprise'):
        paths=[]
        for resume in (False,True):
            paid=list(world.startup);obs=[list(world.pay(i).values) for i in paid]
            policy=QuotaPolicy(world.x,paid,arm,713019)
            for k in range(6):
                slot.check();model=MixtureGP('structure',1)
                ledger.reserve('reference',len(model.components),unit,attempt)
                model.fit(world.x[paid],obs,paid)
                snap=model.snapshot(world.x,world.ref_x)
                before=snap.digest();choice=policy.ask(snap)
                observation=world.pay(choice['paid_id']);event=policy.tell(observation)
                if before!=snap.digest() or before!=event['prequery_hash']:
                    raise AssertionError('pre-query snapshot changed')
                paid.append(observation.paid_id);obs.append(list(observation.values))
                if k==2 and resume:
                    paid,obs,policy=pickle.loads(pickle.dumps((paid,obs,policy),protocol=5))
            paths.append((paid,policy.events))
        if paths[0]!=paths[1]:raise AssertionError('quota checkpoint replay differs')
        events=paths[0][1]
        if any(e['reason'].startswith('local')!=(i%2==1) for i,e in enumerate(events)):
            raise AssertionError('fixed quota slot mismatch')
        if any(e.get('local_candidate_count')!=12 for e in events if e['reason'].startswith('local')):
            raise AssertionError('twelve unpaid candidates required')
        checks.append({'arm':arm,'checkpoint_replay':'exact','local_queries':3,'global_queries':3,
                       'unique_paid':len(set(paths[0][0]))==10,'prequery_immutable':True})
    result={'status':'PASS','utc':now().isoformat(),'checks':checks,'reference_fits':24,'component_solves':288,
            'scope':'software/numerical fixture; not a scientific-world success'}
    ledger.atomic_json(HERE/'results'/'references'/'QUOTA_CHECKS.json',result)
    return result
