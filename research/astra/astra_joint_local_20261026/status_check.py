"""Read-only verification plus compact own-state receipt, no numerical imports."""
import json,psutil
from control import ROOT,read,atomic,sha,now,event,validate
from queue_store import Queue
from resources import alive
c=validate();f=read(ROOT/'FROZEN_DEV_V1.json')
assert all(sha(ROOT/p)==v for p,v in f['source_hashes'].items())
if (ROOT/'FROZEN_TEST_V1.json').exists():
    assert all(sha(ROOT/p)==v for p,v in read(ROOT/'FROZEN_TEST_V1.json')['source_hashes'].items())
assert all(sha(ROOT/r['copy'])==r['sha256'] for r in read(ROOT/'source_snapshot/PREVIOUS_MANIFEST.json'))
assert all(sha(ROOT/r['copy'])==r['sha256'] for r in read(ROOT/'source_snapshot/GITHUB_MANIFEST.json')['files'])
q=Queue(ROOT);summary=q.summary();shared=read(__import__('pathlib').Path(c['shared_runtime'])/'astra_state.json')
workers=[]
for j in shared['jobs']:
    live=alive(j['pid'],j['created']);row={**j,'live_identity_verified':live}
    if live:
        p=psutil.Process(j['pid']);row['os_threads']=p.num_threads();row['rss_bytes']=p.memory_info().rss
        row['blas_environment']={k:p.environ().get(k) for k in ['OPENBLAS_NUM_THREADS','MKL_NUM_THREADS','OMP_NUM_THREADS']}
    workers.append(row)
result={'utc':now().isoformat(),'campaign_id':ROOT.name,'task_and_frozen_hashes':'PASS','source_snapshot_hashes':'PASS',
        'deadline_utc':c['deadline_utc'],'queue':summary,'workers':workers,'own_max_workers':c['own_max_workers']}
atomic(ROOT/'runtime/HEARTBEAT.json',result)
s=read(ROOT/'STATE.json');s.update(updated_utc=now().isoformat(),queue_counts=summary['counts'],verified_own_workers=sum(w['live_identity_verified'] for w in workers));atomic(ROOT/'STATE.json',s)
event('COMPACT_STATUS',counts=summary['counts'],workers=len(workers),hashes='PASS')
print(json.dumps(result))
