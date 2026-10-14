"""Postprocessing only. No fitting, reseeding, tuning or numerical setting changes."""
import runtime as rt
import re
import numpy as np
from scipy.stats import t as student


def describe(values):
    a=np.array([x for x in values if x is not None],float)
    if not len(a):return {'n':0,'mean':None,'interval':None,'values':values}
    mean=float(a.mean());interval=None
    if len(a)>1:
        half=float(student.ppf(.975,len(a)-1)*a.std(ddof=1)/np.sqrt(len(a)))
        interval=[mean-half,mean+half]
    return {'n':len(a),'mean':mean,'interval':interval,'minimum':float(a.min()),'maximum':float(a.max()),
            'positive_count':int((a>0).sum()),'values':values}


def run():
    rt.wait_slot();raw=rt.load(rt.ROOT/'CONTROLLED_RESULTS.json');rows=raw['per_checkpoint'];contrasts=raw['paired_contrasts']
    groups=[]
    for name in raw['manifest']['worlds']:
        for c in ('balanced_risk - probability_variance','balanced_risk - balanced_margin'):
            subset=[r for r in contrasts if r['world']==name and r['contrast']==c]
            groups.append({'world':name,'contrast':c,'planned_pairs':4,'complete_pairs':sum(r['complete'] for r in subset),
                           'BA_AULC':describe([r['AULC']['BA'] if r['complete'] else None for r in subset]),
                           'declared_loss_AULC':describe([r['AULC']['declared_batch_loss'] if r['complete'] else None for r in subset]),
                           'BA_B10':describe([r['B10']['BA'] if r['complete'] else None for r in subset]),
                           'region_positive_recall_AULC':describe([r['AULC']['region_positive_recall'] if r['complete'] else None for r in subset])})
    arm_metrics=[]
    for name in raw['manifest']['worlds']:
        for arm in raw['manifest']['arms']:
            paths=[p for p in raw['paths'] if p['world']==name and p['arm']==arm]
            metrics=('BA','declared_batch_loss','sensitivity','specificity','brier','log_loss',
                     'probability_MSE','pi_90_coverage','pi_90_width','region_error',
                     'region_positive_recall','region_negative_recall')
            arm_metrics.append({'world':name,'arm':arm,'planned_seeds':4,'complete_seeds':sum(p['complete'] for p in paths),
                                'B10':{m:describe([p['B10'][m] if p['complete'] else None for p in paths]) for m in metrics}})
    readouts=[]
    # B6 uses exactly one common startup across selectors; take the margin copy
    # once, avoiding triple-counting identical fits. B10 readouts are path-specific.
    for name in raw['manifest']['worlds']:
        for budget in (6,10):
            chosen=[r for r in rows if r['world']==name and r['budget']==budget and r['arm']=='balanced_margin' and r['status']=='ok' and 'metrics' in r]
            for comparator in ('cutoff_0.5','paid_fraction','posterior_mean_pi'):
                def diff(metric):
                    return [None if r['metrics']['PBR'][metric] is None or r['metrics'][comparator][metric] is None else
                            r['metrics']['PBR'][metric]-r['metrics'][comparator][metric] for r in chosen]
                readouts.append({'world':name,'budget':budget,'path':'balanced_margin','contrast':'PBR - '+comparator,
                                 **{m:describe(diff(m)) for m in ('BA','sensitivity','specificity','region_positive_recall')}})
    qrows=[r['query'] for r in rows if r.get('query')]
    riskq=[r['query'] for r in rows if r['arm']=='balanced_risk' and r.get('query')]
    numerical={'query_records':len(qrows),'unresolved_queries':sum(q.get('status')!='accepted' for q in qrows),
               'accepted_near_ties':sum(q.get('status')=='accepted' and not q.get('ranking_resolved',False) for q in qrows),
               'risk_near_ties':sum(q.get('status')=='accepted' and not q.get('ranking_resolved',False) for q in riskq),
               'risk_queries':len(riskq),'max_tower_risk_difference':max([q.get('max_tower_risk_difference',0) or 0 for q in riskq],default=0),
               'max_low_ESS_outcome_mass':max([q.get('low_ess_outcome_mass',0) for q in riskq],default=0),
               'fallback_fits':sum(r.get('model_diagnostics',{}).get('fallback',False) for r in rows)}
    numerical['max_tower_risk_difference']=max([numerical['max_tower_risk_difference']]+
        [h.get('tower_risk_difference',0) for q in riskq for h in q.get('history',[])])
    numerical['risk_tie_choices_different_from_estimated_argmax']=sum(q.get('status')=='accepted' and q['selected']!=q['estimated_argmax'] for q in riskq)
    numerical['stops']=[{k:r.get(k) for k in ('world','seed','arm','budget','status','error')} for r in rows if r['status']!='ok']
    numerical['decision_ambiguous_points']=sum(sum(r.get('test_decision_numerics',{}).get('ambiguous',[])) for r in rows)
    fractions=[]
    for r in rows:
        if r['arm']=='balanced_margin' and r['budget']==6 and 'paid_fraction' in r:
            fractions.append({k:r[k] for k in ('world','seed','paid_fraction','reference_pi_mean','EVALUATOR_true_reference_pi','EVALUATOR_true_test_pi')})
    for r in rows:
        if 'metrics' in r:
            for m in r['metrics'].values():
                loss=.5 if m['BA'] is None else 1-m['BA']
                if abs(m['declared_batch_loss']-loss)>1e-12:raise RuntimeError('Frozen evaluation loss inconsistent')
            for proper in ('brier','log_loss'):
                if len({m[proper] for m in r['metrics'].values()})!=1:raise RuntimeError('Decision-only comparison changed probability scores')
    raw['evaluation_note']='declared_batch_loss is the prospectively specified 1-BA, or 1/2 on one-class batches; derived without changing predictions'
    raw['postprocessing_sha256']=rt.sha(rt.ROOT/'summarize_results.py')
    rt.save(rt.ROOT/'CONTROLLED_RESULTS.json',raw)
    summary={'status':raw['status'],'by_world':groups,'by_world_arm':arm_metrics,'decision_only_readouts':readouts,
             'numerical':numerical,'startup_fraction_diagnostics':fractions,
             'uncertainty_note':'Student-t 95% intervals across four paired synthetic seeds; descriptive, often wide, no SPH population interpretation. Incomplete pairs remain explicit.'}
    rt.save(rt.ROOT/'RESULTS_SUMMARY.json',summary)
    lines=['**Controlled results: matched decision/acquisition experiment**','',
           f"Status: {raw['status']}. {sum(p['complete'] for p in raw['paths'])}/84 trajectories complete.",'',
           '| World | BA-risk minus comparator | Complete / 4 | Valid BA pairs | Mean BA-AULC difference | Seed interval |','|---|---|---:|---:|---:|---|']
    def fmt(x):return 'NA' if x is None else f'{x:+.4f}'
    for g in groups:
        d=g['BA_AULC'];ci='NA' if d['interval'] is None else '['+', '.join(fmt(x) for x in d['interval'])+']'
        lines.append(f"| {g['world']} | {g['contrast'].split(' - ')[1]} | {g['complete_pairs']} | {d['n']} | {fmt(d['mean'])} | {ci} |")
    lines += ['', 'Intervals describe these four generated seeds. No universal selector ranking or query-saving claim follows.', '',
              f"Numerical diagnostics: {numerical['accepted_near_ties']} accepted query decisions were near ties; {numerical['unresolved_queries']} query computations stopped. Max risk tower discrepancy: {numerical['max_tower_risk_difference']:.6g}.", '',
              'All per-seed/per-budget probabilities, decisions, class counts, local errors, uncertainty intervals, paths and stops are in CONTROLLED_RESULTS.json. Startup paid/reference/true-reference fractions and decision-only contrasts are in RESULTS_SUMMARY.json.', '',
              '**Terminal outcomes, same model and decision rule.** Entries below are means across completed seeds; all per-metric counts and descriptive seed intervals are in RESULTS_SUMMARY.json. Undefined recalls remain null, not zero. Proper-score and local-region losses are not suppressed when BA improves.', '',
              '| World | Selector | Complete / 4 | BA | Sensitivity | Specificity | Brier | Log loss | Region error | Region positive recall | Region negative recall |',
              '|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|']
    for group in arm_metrics:
        vals=[fmt(group['B10'][m]['mean']) for m in ('BA','sensitivity','specificity','brier','log_loss','region_error','region_positive_recall','region_negative_recall')]
        lines.append(f"| {group['world']} | {group['arm']} | {group['complete_seeds']} | "+' | '.join(vals)+' |')
    lines += ['', 'The always-defined prospective loss (1-BA or 1/2 on a one-class batch) and its paired AULC contrasts are reported separately in RESULTS_SUMMARY.json. Numerical-stop outputs remain in the raw file but are not treated as accepted endpoints.', '',
              f"Budget used: {raw['accounting']['top_level_requests']} top-level requests; {raw['accounting']['component_solves']} component solves; {raw['accounting'].get('pending_component_reserve',0)} component solves reserved for unresolved interruptions. No query-saving endpoint was estimated."]
    (rt.ROOT/'CONTROLLED_SUMMARY.md').write_text('\n'.join(lines)+'\n',encoding='utf-8')
    checks=raw['numerical_checks'];f=checks['finite_pool'];g=checks['gaussian_acquisition'];ng=checks['nonGaussian_inference'];toy=checks['additional_idea']
    report='\n'.join(lines)+f"\n\nIndependent references: exact fixed-pool action error {f['risk_coefficient_vs_all_actions_error']:.3g}; IID-batch enumeration error {checks['iid_batch']['max_error']:.3g}; Gaussian-mixture acquisition error {g['max_acquisition_error']:.6g}. The one-label V2 EP probability/risk errors are {ng['EP_probability_error']:.6g}/{ng['EP_risk_error']:.6g}; its paired-score discrepancy is {ng['EP_paired_acquisition_error']:.6g}, with reference refinement difference {ng['exact_paired_reference_convergence']:.6g}. These separate posterior error from integration error. The two-state posterior-mean-prevalence approximation incurs risk regret {checks['uncertain_prevalence']['plug_in_regret']:.6g}.\n\nThe known-probability mixed-cell counterexample reaches BA {toy['BA_optimal']:.4f} while retaining zero positives in that cell. The fixed 80% cell-recall safeguard lowers BA to {toy['BA_with_80_percent_cell_recall']:.4f}; it does not identify individuals.\n"
    design=rt.ROOT/'DECISION_ACQUISITION_DESIGN.md';text=design.read_text(encoding='utf-8')
    if '<!-- RESULTS_BEGIN -->' in text:
        text=re.sub(r'<!-- RESULTS_BEGIN -->.*?<!-- RESULTS_END -->',lambda _: '<!-- RESULTS_BEGIN -->\n'+report+'\n<!-- RESULTS_END -->',text,flags=re.S)
    else:text=text.replace('RESULTS_SECTION_PENDING_COMPLETION',report)
    tr=("**Türkçe açıklama.** Yenilik, modelin olasılıklarını ve sınıf oranı belirsizliğini aynı karar hesabında tutmak ve sonraki simülasyonu aynı BA kaybında beklenen azalmaya göre seçmek. V2 modeli değişmedi. Ücretli örneklerdeki pozitif oranı hedef kitlenin oranı sayılmadı. Matematiksel karşı örnek, kusursuz olasılıklarla bile yüksek BA uğruna karışık bölgedeki bütün pozitiflerin feda edilebildiğini gösteriyor. Bu yüzden yeni kural fiziksel sınırı bulma garantisi vermiyor. Sentetik sonuçlar yukarıda kayıpları ve sayısal duruşlarıyla birlikte verildi; SPH üstünlüğü veya sorgu tasarrufu kanıtlanmış değil. En ayırt edici sonraki adım, Opus'un tamamlanan V2 kayıtlarında yalnızca karar kuralını değiştirip BA ile kısa-Keyhole yakalamayı birlikte karşılaştırmak; yerel ayrım zayıf kalırsa sorun yalnızca eşik değildir.")
    if '<!-- TURKISH_BEGIN -->' in text:
        text=re.sub(r'<!-- TURKISH_BEGIN -->.*?<!-- TURKISH_END -->',lambda _: '<!-- TURKISH_BEGIN -->\n'+tr+'\n<!-- TURKISH_END -->',text,flags=re.S)
    else:text=text.replace('TURKISH_SECTION_PENDING_COMPLETION',tr)
    text=text.replace('**Execution status: QUEUED; numerical acceptance and all controlled outcomes are pending.**',
                      '**Execution status: COMPUTATION FINISHED; scientific review is still required.**')
    design.write_text(text,encoding='utf-8')
    print('Summary written; no fits or model settings changed.',flush=True)


if __name__=='__main__':run()
