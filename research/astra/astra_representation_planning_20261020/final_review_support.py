"""Cached-result review and presentation only; no model fits or new inference."""
import argparse
import csv
import gzip
import hashlib
import json
import os
from pathlib import Path
import statistics
import time
import traceback
import psutil
from coordination import ROOT, Slot, now
from ledger import add_units, claim, finish, atomic_json, sha256, connection


def rows(name):
    with (ROOT/'results/analysis'/name).open(newline='', encoding='utf8') as h:
        return list(csv.DictReader(h))


def mean(values):
    return statistics.mean(values) if values else None


def run():
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    start = time.process_time()
    manifest = json.loads((ROOT/'FROZEN_TEST_V1.json').read_text())
    for name, digest in manifest['source_hashes'].items():
        assert sha256(ROOT/name) == digest
    endpoints = rows('per_world_endpoints.csv')
    readouts = rows('per_world_readouts.csv')
    world_rows = rows('world_provenance.csv')
    costs = rows('same_target_query_cost.csv')
    primary = json.loads((ROOT/'results/analysis/PRIMARY_CONTRASTS.json').read_text())
    family = json.loads((ROOT/'results/analysis/FAMILY_SUMMARIES.json').read_text())
    integrity = json.loads((ROOT/'results/audits/PATH_INTEGRITY.json').read_text())
    replay = json.loads((ROOT/'results/audits/NUMERICAL_REPLAY.json').read_text())
    search = json.loads((ROOT/'results/SEARCH_CONTROLS.json').read_text())
    result_index = json.loads((ROOT/'results/analysis/ANALYSIS_STATUS.json').read_text())['result_files']
    paths, totals = {}, {}
    opt = dict(refits=0, chosen_unsuccessful=0, starts=0, unsuccessful_starts=0)
    for item in result_index:
        raw = (ROOT/item['path']).read_bytes()
        assert hashlib.sha256(raw).hexdigest() == item['sha256']
        r = json.loads(gzip.decompress(raw)); u = r['unit']
        paths[u['panel'],u['world_id'],u['model']+'__'+u['selector']] = r['paid_ids']
        for k,v in r['counters'].items(): totals[k] = totals.get(k,0)+v
        for o in r.get('optimizer_log',[]):
            opt['refits'] += 1
            opt['chosen_unsuccessful'] += not o['chosen_success']
            opt['starts'] += o['starts']
            opt['unsuccessful_starts'] += o['starts']-o['successes']
    path_pairs=[]
    for panel in ['prefix','e2e']:
        pairs=[('local__h1','existing__h1'),('local__h2','existing__h2'),
               ('existing__h2','existing__h1'),('local__h2','local__h1')]
        if panel=='prefix': pairs += [('existing__mixture_h1','existing__h1'),('local__mixture_h1','local__h1')]
        for a,b in pairs:
            for group in ['all','island_small','island_large']:
                ws=[w for w in world_rows if group=='all' or w['family']==group]
                ps=[(paths.get((panel,w['world_id'],a)),paths.get((panel,w['world_id'],b))) for w in ws]
                ps=[(x,y) for x,y in ps if x is not None and y is not None]
                path_pairs.append(dict(panel=panel,left=a,right=b,group=group,n=len(ps),
                                       identical_paid_sequence=sum(x==y for x,y in ps)))
    weights=[]
    for f in manifest['family_counts']:
        for b in [32,48]:
            rs=[r for r in readouts if r['panel']=='prefix' and r['family']==f and r['arm']=='local__h1' and int(r['budget'])==b]
            x=[float(r['local_posterior_weight']) for r in rs]
            weights.append(dict(family=f,budget=b,n=len(x),mean=mean(x),median=statistics.median(x),max=max(x)))
    hits=[]
    for f in ['island_small','island_large']:
        for a in sorted({r['arm'] for r in endpoints if r['panel']=='e2e'}):
            rs=[r for r in endpoints if r['panel']=='e2e' and r['family']==f and r['arm']==a]
            comp=[r for r in rs if r['complete']=='True']
            hits.append(dict(family=f,arm=a,scheduled=len(rs),complete=len(comp),
                             first_hit=sum(bool(r['first_hit']) for r in comp),third_hit=sum(bool(r['third_hit']) for r in comp)))
        for a in ['random','maximin']:
            rs=[r for r in search['paths'] if r['family']==f and r['selector']==a]
            hits.append(dict(family=f,arm=a+'_search_only',scheduled=len(rs),complete=len(rs),
                             first_hit=sum(r['first_valid_hit'] is not None for r in rs),
                             third_hit=sum(r['third_valid_hit'] is not None for r in rs)))
    numerical=[]
    for kind in ['h2','mixture_h1']:
        ss=[r for r in replay['states'] if r['source_unit'].endswith('__'+kind)]
        ds=[v for r in ss for order in r.get('diagnostics',{}).values() for v in order]
        numerical.append(dict(kind=kind,n=len(ss),
            maximum_cached_difference=max(r['cached_vs_highest_max_abs'] for r in ss),
            maximum_refinement_difference=max(r['refinement_max_abs'] for r in ss),
            different_tie_broken_winner=sum(r['selected']!=r['refined_winner_with_ordinary_tie'] for r in ss),
            maximum_selected_refined_score_gap=max(r['selected_refined_score_gap'] for r in ss),
            max_mass_error=max((abs(d['mass']-1) for d in ds),default=None),
            effective_node_range=[min((d['quadrature_effective_nodes'] for d in ds),default=None),max((d['quadrature_effective_nodes'] for d in ds),default=None)]))
    facts=dict(utc=now().isoformat(),source_sha256=sha256(Path(__file__)),
               scope='Post hoc descriptive review of immutable cached results; no new fits, inference or candidate selection.',
               completed_test_actual_counters=totals,ard_optimizer=opt,path_pairs=path_pairs,
               local_weights=weights,search_counts=hits,numerical_replays=numerical,
               numerical_groups=integrity['numeric_groups'])
    atomic_json(ROOT/'results/audits/FINAL_REVIEW_FACTS.json',facts)

    # Tables format already computed quantities; no new bootstrap or target.
    lines=['# Same target, paid-query burden and measured computation','',
           'All means and attainment percentages weight the eleven families equally. Counts are raw completed paths; these are different denominators. Failed paths are separate, never assigned B48 success or censoring. No arm reaches the registered 80% overall attainment requirement for a query-saving claim.','',
           '| Panel / model / rule | Complete / planned | Attained; complete censored | Weighted attainment | Restricted queries | Decision CPU s | Total CPU s | Peak MiB |',
           '|---|---:|---:|---:|---:|---:|---:|---:|']
    for r in costs:
        if r['group']!='equal_family':continue
        lines.append(f"| {r['panel']} / {r['arm']} | {r['complete_n']}/{r['expected_n']} | {r['attained_n']}; {r['censored_complete_n']} | {100*float(r['attainment_fraction']):.2f}% | {float(r['restricted_paid_query_burden']):.3f} | {float(r['mean_decision_cpu']):.3f} | {float(r['mean_total_cpu']):.3f} | {int(r['max_peak_memory_bytes'])/1048576:.1f} |")
    lines += ['', 'Prefix means B32 feature-only paid startup continued to B48; e2e means B8 to B48. The target needs two consecutive four-query readouts. All complete paths buy 48 queries even after attainment. Restricted burden is min(T,48), not demonstrated savings. CPU excludes world generation/import/supervisor time; interrupted pre-checkpoint CPU may be under-recorded. Peak memory is worker process lifetime. No physical runtime was measured.','', 'Source: results/analysis/same_target_query_cost.csv; its pointwise intervals and all per-family rows remain authoritative.']
    (ROOT/'SAME_TARGET_QUERY_COST.md').write_text('\n'.join(lines)+'\n',encoding='utf8')
    lines=['# All families: common-prefix B48 evidence','',
           'Descriptive family means. E/H1 = preserved fixed mixture; L/H2 = local mixture and bounded two-step rule; ARD/S = learned ARD and full-pool straddle. Changes in both model and selector are complete-system comparisons. N/A is preserved. Full eight-arm metrics, pointwise uncertainty and denominators are in family_metrics.csv.','',
           '| Family | Arm | Global error | Boundary error | Positive recall | Negative recall | Island recall | Brier | Log loss |',
           '|---|---|---:|---:|---:|---:|---:|---:|---:|']
    for f in manifest['family_counts']:
        for a in ['existing__h1','local__h2','ard__straddle']:
            r=next(r for r in family if (r['panel'],r['group'],r['arm'])==('prefix',f,a))
            vs=[r['metrics'][k]['estimate'] for k in ['error','boundary_error','recall_positive','recall_negative','island_recall','brier','log_loss']]
            lines.append('| '+f+' | '+a+' | '+' | '.join('N/A' if v is None else f'{v:.5f}' for v in vs)+' |')
    (ROOT/'ALL_FAMILIES_REVIEW.md').write_text('\n'.join(lines)+'\n',encoding='utf8')

    out=ROOT/'figures/reviewed';out.mkdir(exist_ok=True)
    plt.rcParams.update({'font.size':10,'axes.spines.top':False,'axes.spines.right':False,'savefig.dpi':170})
    images=[]
    def save(fig,name,caption):
        for ext in ['png','pdf']:fig.savefig(out/(name+'.'+ext),bbox_inches='tight')
        plt.close(fig)
        images.append(dict(name=name,png=(out/(name+'.png')).relative_to(ROOT).as_posix(),
                           pdf=(out/(name+'.pdf')).relative_to(ROOT).as_posix(),
                           png_sha256=sha256(out/(name+'.png')),pdf_sha256=sha256(out/(name+'.pdf')),caption=caption))
    order=['error__R','error__H','error__I','island_error__R','island_error__H','island_error__I']
    fig,ax=plt.subplots(figsize=(10,5.6)); labels=[]
    for j,key in enumerate(order):
        r=primary['contrasts'][key];lo,hi=r['ci95_simultaneous'];e=r['estimate']
        ax.errorbar(e,j,xerr=[[e-lo],[hi-e]],fmt='D' if r['degenerate'] else 'o',color='#777777' if r['degenerate'] else '#3b6fb6',capsize=4)
        labels.append(('Conditional island error' if key.startswith('island') else 'Global sign error')+' / '+key.split('__')[1]+(' (degenerate)' if r['degenerate'] else ''))
    ax.set_yticks(range(6),labels);ax.invert_yaxis();ax.axvline(0,color='black',lw=1)
    ax.set_xlabel('Paired loss contrast; R/H < 0 favors the new factor; I is effect modification')
    ax.set_title('B48 complete-world contrasts: no clean primary pass\nApproximate simultaneous 95% intervals; missing-outcome bounds are in the table')
    ax.grid(axis='x',alpha=.2);fig.tight_layout()
    save(fig,'primary_mechanism_contrasts','334 complete factorial worlds; conditional islands 6 small and 26 large. Two zero-width degenerate intervals do not establish equivalence. Three terminal TEST failures disable a clean primary pass; sensitivity bounds are separate, not confidence intervals.')
    colors={'existing__h1':'#3b6fb6','existing__h2':'#0e355e','local__h1':'#db8b24','local__h2':'#8c4716','ard__straddle':'#20826a'}
    fig,axs=plt.subplots(1,2,figsize=(13,5))
    for ax,f in zip(axs,['island_small','island_large']):
        for a,col in colors.items():
            rs=[r for r in endpoints if r['panel']=='e2e' and r['family']==f and r['arm']==a and r['complete']=='True']
            ts=[int(r['first_hit']) if r['first_hit'] else 49 for r in rs]
            ax.step(range(8,49),[sum(t<=b for t in ts)/len(ts) for b in range(8,49)],where='post',color=col,label=a.replace('__',' / ')+f' (n={len(ts)})')
        for a,col in [('random','#888888'),('maximin','#171717')]:
            rs=[r for r in search['paths'] if r['family']==f and r['selector']==a];ts=[r['first_valid_hit'] or 49 for r in rs]
            ax.step(range(8,49),[sum(t<=b for t in ts)/len(ts) for b in range(8,49)],where='post',ls='--',color=col,label=a.upper()+' search only (n=16)')
        ax.set_title(f.replace('_',' '));ax.set(xlim=(8,48),ylim=(0,1),xlabel='All paid queries, including startup',ylabel='Completed-path fraction with a valid hit');ax.grid(alpha=.2)
        ax.legend(fontsize=8,loc='upper left')
    fig.suptitle('End-to-end first hit: search, not learned boundary accuracy\nNo-hit and no-pool-candidate worlds retained; one small-island existing/h2 path failed (n=15/16)')
    fig.tight_layout(rect=(0,0,1,.9))
    save(fig,'end_to_end_first_hit','Completion-conditional ECDFs, not survival estimates for interrupted paths. The failed small-island path remains unknown after 29 paid observations; 2/15 completed hits correspond to 2/16 through 3/16 possible scheduled B48 hit fractions. No acquisition ranking follows from sixteen worlds.')
    # Revised titles/captions for the unchanged cached-cost values.
    cr=[r for r in costs if r['panel']=='prefix' and r['group']=='equal_family']
    fig,axs=plt.subplots(1,3,figsize=(15,5))
    for ax,(field,title) in zip(axs,[('attainment_fraction','Joint target attained by B48'),('restricted_paid_query_burden','Restricted burden min(T,48)'),('mean_decision_cpu','Selection CPU seconds')]):
        ax.barh(range(len(cr)),[float(r[field]) for r in cr],color='#3b6fb6');ax.set_yticks(range(len(cr)),[r['arm'].replace('__',' / ') for r in cr]);ax.set_title(title);ax.grid(axis='x',alpha=.2)
    axs[0].set_xlim(0,1)
    fig.suptitle('Common-prefix B32 to B48; eleven families equally weighted\nCompleted paths only; three TEST failures retained separately; no overall query-saving claim')
    fig.tight_layout(rect=(0,0,1,.9));save(fig,'target_query_compute_cost','Prefix panel. Raw completed/attained counts, failed counts, intervals and total CPU are in SAME_TARGET_QUERY_COST.md and the source CSV. Weighted fractions are not raw pooled fractions.')
    facts['review_cpu_seconds']=time.process_time()-start
    atomic_json(ROOT/'results/audits/FINAL_REVIEW_FACTS.json',facts)
    result=dict(status='DERIVED_FIGURES_REQUIRE_VISUAL_REVIEW',utc=now().isoformat(),source_sha256=sha256(Path(__file__)),figures=images,
                unchanged_figure_index_sha256=sha256(ROOT/'figures/FIGURE_INDEX.json'),facts_sha256=sha256(ROOT/'results/audits/FINAL_REVIEW_FACTS.json'),new_model_fits=0)
    atomic_json(out/'REVIEW_RENDER_INDEX.json',result)
    return result


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--threads',type=int,choices=[1],required=True);p.parse_args()
    uid='reference_final_review_render01'
    with Slot():
        add_units([dict(id=uid,kind='cached_review_and_presentation_correction',source_sha256=sha256(Path(__file__)))],'REFERENCE')
        got=claim(uid,os.getpid(),psutil.Process().create_time())
        if got is None: print('Already terminal or live; no duplicate review execution')
        else:
            attempt,_=got
            try:
                result=run();finish(uid,attempt,'COMPLETE','figures/reviewed/REVIEW_RENDER_INDEX.json')
                print(json.dumps({k:v for k,v in result.items() if k!='figures'},indent=2))
            except Exception:
                finish(uid,attempt,'FAILED',note=traceback.format_exc());raise
