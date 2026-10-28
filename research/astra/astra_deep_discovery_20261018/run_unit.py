"""One coordinated numerical worker, repeatedly claiming durable units."""
import os
for _key in ('OMP_NUM_THREADS','OPENBLAS_NUM_THREADS','MKL_NUM_THREADS','NUMEXPR_NUM_THREADS',
             'VECLIB_MAXIMUM_THREADS','BLIS_NUM_THREADS'):
    os.environ[_key] = '1'
import argparse
import gzip
import hashlib
import json
import pickle
import sys
import time
import traceback
from pathlib import Path
import psutil
from coordination import HERE, Slot, AllocationWait, now, within_deadline
import ledger


def verify_source(manifest):
    for name, expected in manifest['source_hashes'].items():
        if hashlib.sha256((HERE/name).read_bytes()).hexdigest() != expected:
            raise RuntimeError('frozen source changed: '+name)


def save_checkpoint(path, state):
    tmp = path.with_suffix('.tmp')
    with tmp.open('wb') as f:
        pickle.dump(state,f,protocol=5)
        f.flush(); os.fsync(f.fileno())
    os.replace(tmp,path)


def read_checkpoint(path):
    # Locally generated trusted artifact only; never unpickle downloaded content.
    with path.open('rb') as f:
        return pickle.load(f)


def trajectory(spec, attempt, slot, manifest):
    import numpy as np
    from model import MixtureGP
    from policy import Policy
    from worlds import World
    wid = spec['id']
    folder = HERE/'results'/spec['phase']
    folder.mkdir(parents=True,exist_ok=True)
    ckdir = HERE/'runtime'/'checkpoints'
    ckdir.mkdir(exist_ok=True)
    ck = ckdir/(wid+'.pickle')
    world = World(spec['family'],spec['seed'],**manifest['world_sizes'])
    if ck.exists():
        state = read_checkpoint(ck)
        if state['manifest_hash'] != spec['manifest_hash'] or state['world_hash'] != world.hash:
            raise RuntimeError('checkpoint source/world mismatch')
    else:
        paid = list(world.startup)
        state = {'manifest_hash':spec['manifest_hash'],'world_hash':world.hash,
            'paid':paid, 'observations':[list(world.pay(i).values) for i in paid],
            'policy':Policy(world.x,paid,spec['selector'],spec['policy_seed']),
            'metrics':[], 'fit_seconds':0.,'selection_seconds':0.,'evaluation_seconds':0.,
            'wall_seconds':0.,'cpu_seconds':0.,'target_time':None,'peak_rss':0,
            'started_utc':now().isoformat(),'startup_observations':[world.pay(i).__dict__ for i in paid]}
        save_checkpoint(ck,state)
    policy = state['policy']
    start_wall,start_cpu = time.perf_counter(),time.process_time()
    prior_wall,prior_cpu = state['wall_seconds'],state['cpu_seconds']
    # Checkpoint always holds a complete paid prefix, with no pending oracle call.
    while True:
        slot.check()
        model = MixtureGP(spec['model'],world.channels)
        ledger.reserve('controlled',len(model.components),wid,attempt)
        t=time.perf_counter()
        model.fit(world.x[state['paid']],state['observations'],state['paid'])
        state['fit_seconds'] += time.perf_counter()-t
        b=len(state['paid'])
        if (b % 4 == 0 or b == spec['budget']) and not any(m['budget']==b for m in state['metrics']):
            t=time.perf_counter()
            metrics=world.evaluate(model,state['paid'])
            metrics['budget']=b
            state['metrics'].append(metrics)
            state['evaluation_seconds'] += time.perf_counter()-t
            if len(state['metrics'])>=2 and metrics['target_met'] and state['metrics'][-2]['target_met'] and state['target_time'] is None:
                state['target_time']=b
        if b >= spec['budget']:
            break
        within_deadline()
        t=time.perf_counter()
        # These selectors use candidate moments only. One reference is retained
        # for the common snapshot contract; it cannot affect their decisions.
        cheap = spec['selector'] in ('random','maximin','maxvar','straddle','margin',
                                    'multiscale_tree','ca_smart_adapt')
        posterior=model.snapshot(world.x,world.ref_x[:1] if cheap else world.ref_x)
        choice=policy.ask(posterior)
        state['selection_seconds'] += time.perf_counter()-t
        observation=world.pay(choice['paid_id'])
        policy.tell(observation)
        state['paid'].append(observation.paid_id)
        state['observations'].append(list(observation.values))
        state['wall_seconds']=prior_wall+time.perf_counter()-start_wall
        state['cpu_seconds']=prior_cpu+time.process_time()-start_cpu
        memory=psutil.Process().memory_info()
        state['peak_rss']=max(state['peak_rss'],getattr(memory,'peak_wset',memory.rss))
        save_checkpoint(ck,state)
    state['wall_seconds']=prior_wall+time.perf_counter()-start_wall
    state['cpu_seconds']=prior_cpu+time.process_time()-start_cpu
    memory=psutil.Process().memory_info()
    state['peak_rss']=max(state['peak_rss'],getattr(memory,'peak_wset',memory.rss))
    save_checkpoint(ck,state)
    metrics=state['metrics']
    outcome={'unit':spec,'attempt_completed':attempt,'status':'COMPLETE',
        'source_manifest_hash':spec['manifest_hash'],'evaluator':world.evaluator_provenance(),
        'startup':state['startup_observations'],'paid_ids':state['paid'],'events':policy.events,
        'metrics':metrics,'target_event':state['target_time'] is not None,
        'target_confirmed_budget':state['target_time'],
        'restricted_query_burden':state['target_time'] or spec['budget'],
        'censor_budget':spec['budget'],
        'error_AULC':float(np.trapezoid([m['error'] for m in metrics],[m['budget'] for m in metrics])/(spec['budget']-len(world.startup))),
        'local_queries':sum(e['reason'].startswith('local') for e in policy.events),
        'triggers':sum(e['triggered'] for e in policy.events),
        'near_ties':sum(e['near_tie'] for e in policy.events),
        'fit_seconds':state['fit_seconds'],'selection_seconds':state['selection_seconds'],
        'evaluation_seconds':state['evaluation_seconds'],'wall_seconds':state['wall_seconds'],
        'cpu_seconds':state['cpu_seconds'],'peak_process_working_set_bytes':state['peak_rss'],
        'memory_scope':'OS lifetime process peak; worker may have run earlier units',
        'started_utc':state['started_utc'],'completed_utc':now().isoformat()}
    raw=json.dumps(outcome,allow_nan=False).encode()
    target=folder/(wid+'.json.gz')
    tmp=target.with_suffix('.tmp')
    with tmp.open('wb') as f:
        f.write(gzip.compress(raw,mtime=0))
    os.replace(tmp,target)
    return {'path':str(target.relative_to(HERE)),'sha256':hashlib.sha256(target.read_bytes()).hexdigest(),
            'paid_count':b,'wall_seconds':state['wall_seconds']}


def allowed_phases():
    mf=json.loads(ledger.manifest_path().read_text())
    with ledger.database() as c:
        row=c.execute('SELECT status FROM units WHERE id=?',(mf.get('reference_unit_id','000_REFERENCE_v1'),)).fetchone()
    if not row or row['status']!='COMPLETE':
        return ['REFERENCE']
    phases=['DEV']
    if (HERE/'TEST_RELEASE.json').exists():
        release=json.loads((HERE/'TEST_RELEASE.json').read_text())
        if release.get('manifest_hash')==hashlib.sha256(ledger.manifest_path().read_bytes()).hexdigest():
            phases.append('TEST')
    return phases


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--work',action='store_true',required=True)
    parser.add_argument('--threads',type=int,choices=[1],required=True)
    parser.parse_args()
    manifest=json.loads(ledger.manifest_path().read_text())
    verify_source(manifest)
    try:
        with Slot() as slot:
            # Numerical imports strictly after shared-record registration.
            from threadpoolctl import threadpool_limits,threadpool_info
            import numpy, scipy
            with threadpool_limits(limits=1):
                info=threadpool_info()
                if any(p['num_threads']!=1 for p in info):
                    raise RuntimeError('BLAS thread contract failed')
                ledger.event(None,None,'WORKER_START',{'slot':slot.record,'resources':slot.initial_snapshot,'libraries':info})
                while True:
                    slot.check()
                    job=ledger.claim(allowed_phases(),psutil.Process().create_time())
                    if job is None:
                        return
                    spec,attempt=job
                    try:
                        if spec['phase']=='REFERENCE':
                            import numerical_checks
                            result=numerical_checks.run(slot,spec['id'],attempt)
                        else:
                            result=trajectory(spec,attempt,slot,manifest)
                        ledger.event(spec['id'],attempt,'UNIT_RESULT',result)
                        ledger.finish(spec['id'],attempt,'COMPLETE')
                    except AllocationWait as exc:
                        ledger.finish(spec['id'],attempt,'PENDING',str(exc)); return
                    except TimeoutError as exc:
                        ledger.finish(spec['id'],attempt,'CENSORED_DEADLINE',str(exc)); return
                    except Exception:
                        detail=traceback.format_exc()
                        ledger.finish(spec['id'],attempt,'FAILED',detail)
                        ledger.atomic_json(HERE/'results'/'failures'/(spec['id']+'__'+attempt+'.json'),
                                           {'spec':spec,'attempt':attempt,'traceback':detail,'utc':now().isoformat()})
                        print(detail,flush=True)
                        # Numerical failures remain closed until a prospective repair.
                        if spec['phase']=='REFERENCE':
                            return
    except (AllocationWait,TimeoutError) as exc:
        print(str(exc),flush=True)


if __name__=='__main__':
    main()
