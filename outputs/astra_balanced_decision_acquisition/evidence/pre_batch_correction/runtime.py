"""Read-only host queue, immutable manifests, fit accounting and local caches."""
import os
for _key in ('OMP_NUM_THREADS','OPENBLAS_NUM_THREADS','MKL_NUM_THREADS','NUMEXPR_NUM_THREADS','VECLIB_MAXIMUM_THREADS'):
    os.environ[_key]='1'
import datetime as dt
import hashlib
import json
from pathlib import Path
import subprocess
import time

ROOT=Path(__file__).resolve().parent


def stamp():return dt.datetime.now(dt.timezone.utc).isoformat()
def sha(path):return hashlib.sha256(Path(path).read_bytes()).hexdigest()
def clean(obj):
    if isinstance(obj,dict):return {str(k):clean(v) for k,v in obj.items()}
    if isinstance(obj,(tuple,list)):return [clean(v) for v in obj]
    if hasattr(obj,'tolist'):return clean(obj.tolist())
    if isinstance(obj,float) and (obj!=obj or abs(obj)==float('inf')):return None
    return obj
def save(path,obj):
    path=Path(path);path.parent.mkdir(parents=True,exist_ok=True)
    tmp=path.with_suffix(path.suffix+'.tmp');tmp.write_text(json.dumps(clean(obj),indent=1,allow_nan=False),encoding='utf-8');tmp.replace(path)
def load(path):return json.loads(Path(path).read_text(encoding='utf-8'))


def append(obj):
    with (ROOT/'ledger.jsonl').open('a',encoding='utf-8') as f:f.write(json.dumps(clean({'utc':stamp(),**obj}),allow_nan=False)+'\n')


def host_snapshot():
    cmd="Get-CimInstance Win32_Process | Where-Object { $_.Name -match '^(python|pythonw|julia|Rscript)\\.exe$' } | Select-Object ProcessId,ParentProcessId,Name,CommandLine | ConvertTo-Json -Compress"
    r=subprocess.run(['powershell','-NoProfile','-Command',cmd],capture_output=True,text=True,check=True)
    rows=json.loads(r.stdout) if r.stdout.strip() else []
    if isinstance(rows,dict):rows=[rows]
    own={os.getpid(),os.getppid()};changed=True
    while changed:
        changed=False
        for row in rows:
            if row['ProcessId'] in own and row['ParentProcessId'] not in own:
                own.add(row['ParentProcessId']);changed=True
    parents={r['ParentProcessId'] for r in rows}
    leaves=[r for r in rows if r['ProcessId'] not in own and r['ProcessId'] not in parents]
    # Unknown foreign numerical workers count conservatively as one or >=4 if
    # no explicit 1-thread schedule is visible. Never change affinity or priority.
    slots=0
    for r in leaves:
        command=r.get('CommandLine') or ''
        slots+=1 if '--threads 1' in command else 4
    return {'utc':stamp(),'host':os.environ.get('COMPUTERNAME'),'foreign_leaves':leaves,'foreign_slots':slots,'own_threads':1}


def wait_slot():
    while True:
        state=host_snapshot();save(ROOT/'HOST_QUEUE.json',state)
        if state['foreign_slots']<=3:return state
        print('Queued: all four shared numerical threads occupied.',flush=True)
        time.sleep(30)


SOURCES=('balanced_method.py','worlds.py','runtime.py','run_controlled.py','independent_checks.py','joint_model_v2.py','v1_reference.py','PROSPECTIVE_SELECTION.md')


def freeze():
    dest=ROOT/'MANIFEST.json'
    if dest.exists():return verify()
    obj={'frozen_utc':stamp(),'anchor':'2b22c13df41ee0179d5999ff07a98c0aa36814ca',
         'worlds':['informative','redundant','harmful','rare_negatives','locally_mixed','selected_fraction','missing_depth'],
         'seeds':[5101,5102,5103,5104],'arms':['balanced_risk','probability_variance','balanced_margin'],
         'budgets':[6,7,8,9,10],'pool_size':24,'test_size':96,
         'target':'population balanced error under uniform fixed candidate-feature distribution; training-only proxy for held-out BA',
         'planned_main_fit_requests':420,'validation_fit_limit':24,'top_level_ceiling':600,
         'component_solve_ceiling':1500,'nominal_main_solves':1260,'nominal_validation_solves':72,'fallback_reserve':168,
         'reference_groups_ceiling':30,'reference_states_ceiling':12000000,
         'source_sha256':{f:sha(ROOT/f) for f in SOURCES},
         'evidence_sha256':{str(f.relative_to(ROOT)):sha(f) for f in (ROOT/'evidence').iterdir() if f.is_file()},
         'v2_original_hashes':{f:sha(ROOT.parent/'astra_joint_model_v2'/f) for f in ('joint_model_v2.py','v1_reference.py','CONTROLLED_RESULTS.json','SELECTION_RECORD_V2.json')},
         'expected_directions':'See PROSPECTIVE_SELECTION.md; no numeric superiority forecast',
         'stop_rules':'Numerical ladder ceilings; no seed replacement; missing endpoints null; no savings endpoint'}
    save(dest,obj);append({'event':'FREEZE','manifest_sha256':sha(dest)});return obj


def verify():
    obj=load(ROOT/'MANIFEST.json')
    for name,expected in obj['source_sha256'].items():
        if sha(ROOT/name)!=expected:raise RuntimeError(f'Frozen source changed: {name}')
    for name,expected in obj['v2_original_hashes'].items():
        if sha(ROOT.parent/'astra_joint_model_v2'/name)!=expected:raise RuntimeError(f'Original V2 changed: {name}')
    return obj


def counts():
    rows=[json.loads(s) for s in (ROOT/'ledger.jsonl').read_text(encoding='utf-8').splitlines()] if (ROOT/'ledger.jsonl').exists() else []
    starts=[r for r in rows if r['event']=='FIT_START'];ends=[r for r in rows if r['event']=='FIT_END']
    pending=set(r['key'] for r in starts)-set(r['key'] for r in ends)
    return {'top_level_requests':len(starts),'component_solves':sum(r.get('component_solves',0) for r in ends),
            'pending':sorted(pending),'failed_fits':sum(r.get('status')!='ok' for r in ends),
            'validation_requests':sum(r.get('validation',False) for r in starts)}


def charged_fit(key,xref,xpaid,y,z,validation=False):
    import pickle
    from joint_model_v2 import JointModelV2
    from worlds import config
    verify();cache=ROOT/'checkpoints'/f'{key}.pkl';record=ROOT/'fit_records'/f'{key}.json'
    if record.exists():
        old=load(record)
        if old['status']!='ok':raise RuntimeError(f'Preserved failed fit {key}')
        if sha(cache)!=old['checkpoint_sha256']:raise RuntimeError('Corrupt checkpoint')
        return pickle.loads(cache.read_bytes())
    c=counts()
    if key in c['pending']:raise RuntimeError(f'Unresolved interrupted fit {key}; audit, never silently rerun')
    if c['top_level_requests']>=600 or c['component_solves']+6>1500:raise RuntimeError('Fit budget exhausted')
    if validation and c['validation_requests']>=24:raise RuntimeError('Validation fit budget exhausted')
    state=wait_slot();append({'event':'FIT_START','key':key,'validation':validation,'host':state})
    model=JointModelV2(xref,config());start=time.monotonic()
    try:
        model.fit(xpaid,y,z)
        cache.parent.mkdir(exist_ok=True);cache.write_bytes(pickle.dumps(model))
        rec={'event':'FIT_END','key':key,'status':'ok','component_solves':model.solve_count,
             'seconds':time.monotonic()-start,'diagnostics':model.diagnostics,'checkpoint_sha256':sha(cache)}
        save(record,rec);append(rec);return model
    except Exception as ex:
        rec={'event':'FIT_END','key':key,'status':'failed','error':repr(ex),
             'component_solves':getattr(model,'solve_count',0),'seconds':time.monotonic()-start}
        save(record,rec);append(rec);raise
