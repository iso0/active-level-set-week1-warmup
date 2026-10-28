"""Stdlib-only report tables and full queue ledger from immutable results."""
import csv
import json
import statistics
from control import ROOT,atomic,now,read,sha
from queue_store import Queue

def mean(values):
    v=[x for x in values if x is not None];return statistics.mean(v) if v else None

def main():
    a1=read(ROOT/'results/analysis_dev_v1/ANALYSIS.json');a2=read(ROOT/'results/analysis_dev_v2/ANALYSIS.json')
    assert a1['completed_units']==a2['completed_units']==64 and not a1['screen']['passed'] and not a2['screen']['passed']
    final=read(ROOT/'evidence/FINAL_NUMERICAL_AND_HANDOFF_CHECKS.json');assert final['status']=='PASS'
    data=[]
    for ver in ('v1','v2'):
        with (ROOT/f'results/analysis_dev_{ver}/PER_WORLD_PATH_MODEL.csv').open(encoding='utf-8',newline='') as f:
            for r in csv.DictReader(f):
                if ver=='v2' and r['arm'] in ('strong','gated'):continue
                for k,v in list(r.items()):
                    if k not in ('id','unit','family','path','arm'):r[k]=float(v) if v else None
                data.append(r)
    arms=['strong','compact','gated','trace_match','coherent','coherent_trace'];paths=['maximin','strong_margin']
    table=['# Same-target query and computation accounting','',
           'The two shared query policies were fixed. These are predictor attainments on those paths, **not demonstrated acquisition savings**. Each panel has32 worlds. Confirmation requires two consecutive grid budgets; unattained cases retain burden25 and censoring at24. Counts are individual learners, not a threshold on an averaged learning curve.','',
           '| Shared path | Predictor | BA-AULC | Positive recall | Negative recall | BA≥.90 count; burden | BA≥.93 count; burden | BA≥.95 count; burden |',
           '|---|---|---:|---:|---:|---:|---:|---:|']
    summary=[]
    for panel in paths:
        for arm in arms:
            rr=[r for r in data if r['path']==panel and r['arm']==arm]
            row={'path':panel,'arm':arm,'n':len(rr),'ba_aulc':mean(r['ba_aulc'] for r in rr),
                 'positive_recall':mean(r['positive_recall_aulc'] for r in rr),'negative_recall':mean(r['negative_recall_aulc'] for r in rr)}
            cells=[]
            for t in ('.90','.93','.95'):
                key='0'+t;count=sum(r['attain_'+key] is not None for r in rr);burden=mean(r['burden_'+key] for r in rr)
                row['attained_'+key]=count;row['censored_'+key]=len(rr)-count;row['restricted_burden_'+key]=burden
                row['held_at_b24_'+key]=sum(r['ba_b24'] is not None and r['ba_b24']>=float(key) for r in rr)
                cells.append(f'{count}/{len(rr)}; {burden:.3f}')
            summary.append(row)
            table.append(f"| {panel} | {arm} | {row['ba_aulc']:.4f} | {row['positive_recall']:.4f} | {row['negative_recall']:.4f} | "+' | '.join(cells)+' |')
    original=[read(p) for p in (ROOT/'results').glob('unit__dev_v1_*.json') if 'reference' not in p.stem]
    cost={'v1_total_cpu_seconds':sum(r['cpu_seconds'] for r in original),'v1_mean_cpu_seconds':mean(r['cpu_seconds'] for r in original),
          'v1_peak_rss_bytes':max(r['peak_rss_bytes'] for r in original),'v2_incremental_cpu_seconds':sum(r['incremental_cpu_seconds'] for r in a2['costs']),
          'v2_mean_incremental_cpu_seconds':mean(r['incremental_cpu_seconds'] for r in a2['costs']),
          'v2_peak_rss_bytes':max(r['peak_rss_bytes'] for r in a2['costs']),
          'v2_dense_factorizations':sum(r['dense_factorizations'] for r in a2['costs']),
          'v2_rankone_updates':sum(r['rankone_updates'] for r in a2['costs']),
          'v1_component_solves_actual':sum(r['used_counts']['component_solves'] for r in original),
          'optimizer_evaluations_actual':sum(r['used_counts']['optimizer_evaluations'] for r in original),
          'optimizer_refreshes':sum(len(r['model']['optimizer']) for r in original),
          'chosen_optimizer_failures':sum(not o['chosen_success'] for r in original for o in r['model']['optimizer']),
          'individual_optimizer_start_failures':sum(o['starts']-o['successes'] for r in original for o in r['model']['optimizer'])}
    table += ['', 'All64 v1 paths jointly evaluated four models: total measured model/prediction CPU '+f"{cost['v1_total_cpu_seconds']:.3f}s, mean {cost['v1_mean_cpu_seconds']:.3f}s/path, peak RSS {cost['v1_peak_rss_bytes']/2**20:.1f}MiB.",
              'V2 reused fitted backgrounds and paths: incremental prediction CPU '+f"{cost['v2_incremental_cpu_seconds']:.3f}s total, {cost['v2_mean_incremental_cpu_seconds']:.3f}s/path, peak RSS {cost['v2_peak_rss_bytes']/2**20:.1f}MiB.",
              'These timings exclude imports, world construction, supervision and some serialization. V1 joint timing is not a per-arm timing; v2 incremental timing is not full learner cost. No physical simulation duration was measured.', '',
              f"V1: {cost['v1_component_solves_actual']:,} component solves and {cost['optimizer_evaluations_actual']:,} optimizer evaluations. V2: {cost['v2_dense_factorizations']:,} dense factorizations plus {cost['v2_rankone_updates']:,} rank-one updates. All {cost['optimizer_refreshes']} selected optimizer results reported success; {cost['individual_optimizer_start_failures']} individual starts did not. Success is not proof of global optimality."]
    table += ['', '## Search accounting','',
              'Geometric footprint hits were the frozen conditional subgroup. They are not necessarily positive-regime detections. The following extra diagnostic distinguishes latent-positive and noisy-observed-positive hits inside that footprint; no membership was given to a selector. All pre-hit queries were charged.', '',
              '| Family | Shared path | Worlds with footprint hit | With latent-positive footprint hit | With observed-positive footprint hit |', '|---|---|---:|---:|---:|']
    for family in ('local_shift','small_island','rotated_local'):
        for panel in paths:
            rr=[r for r in final['search_diagnostics'] if r['family']==family and r['path']==panel]
            table.append(f'| {family} | {panel} | '+ ' | '.join(f"{sum(r[k] is not None for r in rr)}/{len(rr)}" for k in ('first_footprint_hit','first_latent_positive_in_footprint','first_observed_positive_in_footprint'))+' |')
    (ROOT/'SAME_TARGET_QUERY_COST.md').write_text('\n'.join(table)+'\n',encoding='utf-8')
    atomic(ROOT/'SAME_TARGET_QUERY_COST.json',{'utc':now().isoformat(),'per_path_predictor':summary,'cost':cost,'search':final['search_diagnostics']})
    fam=['# All families retained','', 'Means of both path panels; four independent worlds per family. Two path panels are not eight independent replicates. BA and both recalls are B8–B24 AULC.','', '| Family | Predictor | BA | Positive recall | Negative recall | Local error | Log loss |', '|---|---|---:|---:|---:|---:|---:|']
    for f in dict.fromkeys(r['family'] for r in data):
        for arm in arms:
            rr=[r for r in data if r['family']==f and r['arm']==arm]
            vals=[mean(r[k] for r in rr) for k in ('ba_aulc','positive_recall_aulc','negative_recall_aulc','regional_error_aulc','log_loss_aulc')]
            fam.append('| '+f+' | '+arm+' | '+' | '.join('undefined' if v is None else f'{v:.4f}' for v in vals)+' |')
    (ROOT/'ALL_FAMILIES.md').write_text('\n'.join(fam)+'\n',encoding='utf-8')
    q=Queue(ROOT)
    with q.connect() as c:
        ledger={name:[dict(r) for r in c.execute('SELECT * FROM '+name)] for name in ('units','attempts','reservations')}
    atomic(ROOT/'evidence/FINAL_ATTEMPT_LEDGER.json',ledger)
    result={'scientific_status':'COMPLETE_BOTH_DEV_SCREENS_FAILED','independent_worlds':32,'actual_query_paths':64,
            'v2_same_path_prediction_replays':64,'failed_scientific_units':0,'independent_test_executed':False,'new_selector_executed':False,
            'v1':a1['screen'],'v2':a2['screen'],'cost':cost,'queue':q.summary(),'last_analysis_utc':now().isoformat(),
            'artifacts':{'design':'docs/MODEL_DESIGN_V1.md','v2':'docs/DEV_V2_PROTOCOL.md','all_results':'results/',
                         'query_cost':'SAME_TARGET_QUERY_COST.md','family_tables':'ALL_FAMILIES.md','handoff':'handoff/README.md',
                         'automatic_resume':'AUTO_RESUME_RECEIPT.json','attempt_ledger':'evidence/FINAL_ATTEMPT_LEDGER.json'}}
    atomic(ROOT/'CONTROLLED_RESULTS.json',result)
    print(json.dumps({'cost':cost,'query_table_rows':len(summary),'science':result['scientific_status']}))

if __name__=='__main__':main()
