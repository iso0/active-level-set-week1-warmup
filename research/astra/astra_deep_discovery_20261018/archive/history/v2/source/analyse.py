"""Paired controlled-results analysis; acquires a numerical slot, never refits."""
import os
for k in ('OMP_NUM_THREADS','OPENBLAS_NUM_THREADS','MKL_NUM_THREADS','NUMEXPR_NUM_THREADS'):
    os.environ[k]='1'
import argparse
import csv
import gzip
import hashlib
import json
from collections import defaultdict
from pathlib import Path
from coordination import HERE,Slot,now
import ledger


def read_rows(phase,prefix):
    result=[]
    for file in sorted((HERE/'results'/phase).glob(prefix+'*.json.gz')):
        with gzip.open(file,'rt',encoding='utf-8') as f:
            row=json.load(f)
        row['_file']=str(file.relative_to(HERE))
        result.append(row)
    return result


def analyse(phase,prefix):
    with Slot() as slot:
        import numpy as np
        from threadpoolctl import threadpool_limits
        with threadpool_limits(1):
            rows=read_rows(phase,prefix)
            if not rows:
                raise RuntimeError('no completed outcomes')
            with ledger.database() as c:
                expected=[dict(r) for r in c.execute('SELECT id,status FROM units WHERE phase=? AND id LIKE ?',
                    (phase,prefix+'%'))]
            incomplete=[r for r in expected if r['status']!='COMPLETE']
            dst=HERE/'results'/'analysis'/f'{prefix}{phase}'
            dst.mkdir(parents=True,exist_ok=True)
            endpoint=[]; curves=[]; path_errors=[]; world_groups=defaultdict(list)
            for row in rows:
                s=row['unit']; key=(s['family'],s['seed'])
                world_groups[key].append(row)
                e={k:s[k] for k in ('id','phase','family','seed','model','selector','budget')}
                e.update(row['metrics'][-1])
                for k in ('error_AULC','target_event','target_confirmed_budget','restricted_query_burden',
                          'local_queries','triggers','near_ties','fit_seconds','selection_seconds',
                          'evaluation_seconds','wall_seconds','cpu_seconds','peak_process_working_set_bytes'):
                    e[k]=row[k]
                endpoint.append(e)
                curves += [{**{k:s[k] for k in ('id','family','seed','model','selector')},**m} for m in row['metrics']]
                paid=row['paid_ids'];events=row['events'];n0=len(row['startup'])
                issues=[]
                if len(set(paid))!=len(paid) or len(paid)!=s['budget']: issues.append('duplicate/missing paid ID')
                if len(events)!=len(paid)-n0: issues.append('event count')
                if [r['paid_id'] for r in row['startup']]!=paid[:n0]: issues.append('startup')
                for k,event in enumerate(events):
                    if event['paid_id']!=paid[n0+k] or event['paid_before']!=n0+k: issues.append('time order')
                    if len(event['prequery_hash'])!=64 or len(event['model_hash'])!=64: issues.append('posterior provenance')
                    if event['cost']!=1: issues.append('paid cost')
                    if event['variance_kind']!='latent plus separate observation noise': issues.append('variance convention')
                hit=None
                for previous,current in zip(row['metrics'][:-1],row['metrics'][1:]):
                    if previous['target_met'] and current['target_met']:
                        hit=current['budget'];break
                if hit!=row['target_confirmed_budget']: issues.append('target did not charge confirmation')
                if issues:path_errors.append({'id':s['id'],'issues':sorted(set(issues))})
            for key,group in world_groups.items():
                if len({r['evaluator']['hash'] for r in group})!=1 or len({tuple(r['paid_ids'][:len(r['startup'])]) for r in group})!=1:
                    path_errors.append({'world':key,'issues':['unmatched world/startup']})
            def write_csv(name,data):
                fields=list(dict.fromkeys(k for row in data for k in row))
                with (dst/name).open('w',newline='',encoding='utf-8') as f:
                    w=csv.DictWriter(f,fields);w.writeheader();w.writerows(data)
            write_csv('per_seed_endpoints.csv',endpoint)
            write_csv('all_learning_curve_readouts.csv',curves)
            buckets=defaultdict(list)
            for e in endpoint:buckets[(e['family'],e['model'],e['selector'])].append(e)
            summaries=[]
            metrics=('error','boundary_error','island_recall','recall_positive','recall_negative','BA',
                     'brier','log_loss','MAE','RMSE','coverage90','aux_RMSE','reported_channel_RMSE',
                     'error_AULC','target_event','restricted_query_burden','local_queries','triggers',
                     'positive_paid_count','paid_island_count','wall_seconds','selection_seconds','cpu_seconds',
                     'peak_process_working_set_bytes')
            for (f,m,a),group in sorted(buckets.items()):
                summary={'family':f,'model':m,'selector':a,'n':len(group)}
                for metric in metrics:
                    v=[r[metric] for r in group if r.get(metric) is not None]
                    summary[metric]=float(np.mean(v)) if v else None
                    summary[metric+'_defined_n']=len(v)
                summaries.append(summary)
            write_csv('family_summary.csv',summaries)
            index={(e['family'],e['seed'],e['model'],e['selector']):e for e in endpoint}
            pairs=[('H1_same_model_local_effect',('mixture','regional'),('mixture','sur_global')),
                   ('H2_same_selector_model_effect',('mixture','regional'),('simple','regional')),
                   ('H3_boundary_gate',('structure','boundary_regional'),('structure','sur_global')),
                   ('H4_structural_representation',('structure','boundary_regional'),('simple','boundary_regional')),
                   ('boundary_gate_original_model',('mixture','boundary_regional'),('mixture','sur_global')),
                   ('boundary_loss_vs_blind',('structure','boundary_regional'),('structure','boundary_blind')),
                   ('boundary_vs_ungated',('structure','boundary_regional'),('structure','ungated_local')),
                   ('matched_maximin_model',('structure','maximin'),('simple','maximin')),
                   ('matched_random_model',('structure','random'),('simple','random')),
                   ('structure_vs_mixture_same_gate',('structure','boundary_regional'),('mixture','boundary_regional')),
                   ('paired_vs_primary_structure',('structure','sur_global'),('structure','sur_primary')),
                   ('local_loss_vs_blind',('mixture','regional'),('mixture','blind_local')),
                   ('surprise_vs_ungated',('mixture','regional'),('mixture','ungated_local')),
                   ('SUR_vs_VTL',('mixture','sur_global'),('mixture','vtl')),
                   ('paired_vs_primary',('mixture','sur_global'),('mixture','sur_primary'))]
            rng=np.random.default_rng(20261018)
            contrasts=[]
            for name,a,b in pairs:
                groups=defaultdict(list)
                for (family,seed),members in world_groups.items():
                    ar=index.get((family,seed,*a));br=index.get((family,seed,*b))
                    if ar and br:groups[family].append((ar,br))
                if not groups:continue
                def paired(metric):
                    return {f:np.array([ar[metric]-br[metric] for ar,br in g if ar.get(metric) is not None and br.get(metric) is not None],float)
                            for f,g in groups.items()}
                for metric in ('error','error_AULC','boundary_error','island_recall','brier','log_loss','restricted_query_burden'):
                    values={f:v for f,v in paired(metric).items() if len(v)}
                    if not values:continue
                    point=float(np.mean([v.mean() for v in values.values()]))
                    boot=sum(v[rng.integers(len(v),size=(10000,len(v)))].mean(1) for v in values.values())/len(values)
                    ci=np.quantile(boot,[.025,.975]).tolist()
                    item={'contrast':name,'A':a,'B':b,'metric':metric,'A_minus_B':point,'ci95':ci,
                          'families':len(values),'pairs':sum(map(len,values.values())),
                          'scope':'development descriptive' if phase=='DEV' else 'frozen synthetic distribution',
                          'primary':name.startswith(('H1_','H2_','H3_','H4_')) and metric=='error'}
                    if item['primary']:
                        signs=sum((rng.integers(0,2,size=(10000,len(v)))*2-1)@v/len(v) for v in values.values())/len(values)
                        item['randomization_p_two_sided']=float((1+np.sum(abs(signs)>=abs(point)-1e-15))/10001)
                    if metric=='restricted_query_burden':
                        aa=float(np.mean([np.mean([ar['target_event'] for ar,br in g]) for g in groups.values()]))
                        bb=float(np.mean([np.mean([br['target_event'] for ar,br in g]) for g in groups.values()]))
                        item.update({'attainment_A':aa,'attainment_B':bb,
                                     'query_savings_established':bool(not incomplete and phase=='TEST' and aa>=.8 and bb>=.8 and ci[1]<0)})
                    contrasts.append(item)
            primary=sorted([r for r in contrasts if r['primary']],key=lambda r:r['randomization_p_two_sided'])
            previous=0.
            for j,r in enumerate(primary):
                adjusted=min(1.,max(previous,(len(primary)-j)*r['randomization_p_two_sided']))
                r['holm_p']=adjusted;previous=adjusted
                r['confirmatory_pass']=bool(phase=='TEST' and not incomplete and adjusted<.05 and r['ci95'][1]<0)
            result={'phase':phase,'prefix':prefix,'utc':now().isoformat(),'complete':not incomplete,
                'expected_units':len(expected),'completed_outcomes':len(rows),'incomplete':incomplete,
                'path_audit_errors':path_errors,'path_audit_scope':'every saved paid sequence, startup, world identity, timestamps, hash presence and target-confirmation rule; deterministic numerical replay tested separately',
                'contrasts':contrasts,'families':summaries,'actual_controlled_outcomes':True,
                'no_SPH_or_external_confirmation':True,
                'source_hash':hashlib.sha256(Path(__file__).read_bytes()).hexdigest()}
            ledger.atomic_json(dst/'CONTROLLED_RESULTS.json',result)
            ledger.event(None,None,'ANALYSIS_COMPLETE',{'phase':phase,'prefix':prefix,'n':len(rows),'complete':not incomplete,
                         'source_sha256':result['source_hash'],'path_errors':len(path_errors)})
            summary=['# Controlled '+phase+' results','',f"Completed {len(rows)}/{len(expected)} units; incomplete={len(incomplete)}.",
                     f"Path invariant errors: {len(path_errors)}. No SPH or independent physical-data claim.",'',
                     '| Contrast | Final error A−B | Paired 95% interval | n |','|---|---:|---:|---:|']
            summary += [f"| {r['contrast']} | {r['A_minus_B']:+.5f} | [{r['ci95'][0]:+.5f}, {r['ci95'][1]:+.5f}] | {r['pairs']} |" for r in contrasts if r['metric']=='error']
            summary += ['', 'Negative error differences favor A. '+('DEV is development evidence, not the independent TEST result.' if phase=='DEV' else 'TEST uses the frozen independent synthetic realizations.'),
                        'Query savings require the separately frozen attainment/censor rule; inspect CONTROLLED_RESULTS.json.',
                        'Family tables retain all worlds, including nulls and corrupted monitors. Undefined conditional metrics stay N/A.']
            (dst/'SUMMARY.md').write_text('\n'.join(summary)+'\n',encoding='utf-8')
            print('\n'.join(summary))
            return result


if __name__=='__main__':
    p=argparse.ArgumentParser()
    p.add_argument('--phase',choices=['DEV','TEST'],required=True)
    p.add_argument('--prefix',required=True)
    p.add_argument('--threads',type=int,choices=[1],required=True)
    args=p.parse_args()
    analyse(args.phase,args.prefix)
