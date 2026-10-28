"""Read-only development mechanism diagnostics. No GP fits or hidden TEST data."""
import gzip
import json
import statistics
from collections import defaultdict
from coordination import HERE, Slot, now
import ledger

with Slot():
    groups = defaultdict(list)
    for path in sorted((HERE/'results'/'DEV').glob('v1_1__*.json.gz')):
        with gzip.open(path, 'rt', encoding='utf-8') as f:
            row = json.load(f)
        if row['unit']['selector'] == 'regional':
            groups[(row['unit']['family'], row['unit']['model'])].append(row)
    result=[]
    for (family, model), rows in groups.items():
        events=[e for r in rows for e in r['events'] if 'raw_z' in e]
        result.append({'family':family,'model':model,'trajectories':len(rows),
            'prequential_observations':len(events),
            'max_absolute_z':max(abs(e['raw_z']) for e in events),
            'median_absolute_z':statistics.median(abs(e['raw_z']) for e in events),
            'sign_disagreements':sum(e['mean'][0]*e['values'][0]<0 for e in events),
            'triggers':sum(r['triggers'] for r in rows),
            'local_queries':sum(r['local_queries'] for r in rows),
            'first_island_hit_trajectories':sum(r['metrics'][-1]['first_island_query'] is not None for r in rows),
            'final_island_recalls':[r['metrics'][-1]['island_recall'] for r in rows],
            'latent_interval_coverage90':[r['metrics'][-1]['coverage90'] for r in rows]})
    ledger.atomic_json(HERE/'results'/'DEV_MECHANISM_DIAGNOSIS.json',
        {'utc':now().isoformat(),'rows':result,'GP_fits':0,'scope':'post-hoc v1.1 development diagnosis'})
    for r in result:
        if r['model']=='mixture':
            print(r['family'], 'max|z|',round(r['max_absolute_z'],3),'sign disagreements',r['sign_disagreements'],
                  'island hit trajectories',r['first_island_hit_trajectories'])
