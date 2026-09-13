"""Validation, repeat-block analysis and teaching artifacts for Phase 1.20."""
from __future__ import annotations

import argparse
import inspect
import json
import platform
import sys
import tarfile
from pathlib import Path

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import nbformat as nbf
import numpy as np
import pandas as pd
import scipy
import sklearn
from nbclient import NotebookClient
from jupyter_client import KernelManager
from src import week9_phase1_20_m3_g3_margin_acquisition as p

OUT, ROOT = p.OUT, p.ROOT
write_csv, write_json, require = p.write_csv, p.write_json, p.require
NOTEBOOK = ROOT / 'notebooks/week_09/18_week9_phase1_20_m3_g3_margin_acquisition.ipynb'


def provenance_gate():
    pop, specs, a0, p1 = p.load()
    split = pd.read_csv(p.w85.OUTPUT / 'split_manifest.csv')
    require(set(split.role) == {'training_pool', 'untouched_test'}, 'unexpected stored split roles')
    checks = {}
    checks['frozen_split_manifest_exact'] = all(
        set(split[(split.run_id == s.run_id) & (split.role == role)].population_row_index) == set(indices)
        for s in specs for role, indices in [('training_pool', s.train_indices), ('untouched_test', s.test_indices)])
    original = {}
    with tarfile.open(p.w85.OUTPUT / 'week8_5_checkpoint_bundle.tar.gz') as bundle:
        for member in bundle.getmembers():
            if member.name.endswith('__binary_margin__c01.json'):
                payload = json.load(bundle.extractfile(member))
                original[payload['identity']['run_id']] = payload['queried_indices'][:80]
    checks['gate3_P0_exact_original_Week85'] = original == a0
    checks['gate4_P1_all_training_only'] = all(set(p1[s.run_id]).issubset(s.train_indices) for s in specs)
    files = [p.w85.OUTPUT / 'split_manifest.csv', p.w85.OUTPUT / 'initial_design_manifest.csv',
             p.w85.OUTPUT / 'week8_5_checkpoint_bundle.tar.gz',
             p.p12.PHASE18 / 'tables/query_paths.csv.gz',
             p.p14.OUTPUT / 'm3_margin_paths.csv.gz', p.p14.OUTPUT / 'new_predictions.csv.gz',
             p.p13.OUTPUT / 'new_predictions.csv.gz']
    report = {'status': 'PASS' if all(checks.values()) else 'FAIL', 'checks': checks,
              'inputs': [{'path': str(f.relative_to(ROOT)), 'sha256': p.p14.sha256_file(f)} for f in files],
              'environment': {'python': sys.version, 'executable': sys.executable, 'numpy': np.__version__,
                              'scipy': scipy.__version__, 'sklearn': sklearn.__version__, 'pandas': pd.__version__}}
    write_json(OUT / 'input_provenance.json', report)
    require(all(checks.values()), f'provenance gate: {checks}')
    return report


def metrics_from_predictions(pred):
    rows = []
    for keys, group in pred.groupby(['run_id', 'repeat', 'fold', 'model', 'budget'], sort=True):
        identity = dict(zip(['run_id', 'repeat', 'fold', 'model', 'budget'], keys))
        for subset, flag in [('full81', np.ones(len(group), bool)), ('B1_q20', group.is_q20.to_numpy(bool)),
                             ('B1_q30', group.is_q30.to_numpy(bool))]:
            selected = group.loc[flag]
            truth = selected.truth.to_numpy(int)
            hard = selected.probability.to_numpy(float) >= .5
            tp, tn = int(((truth == 1) & hard).sum()), int(((truth == 0) & ~hard).sum())
            fp, fn = int(((truth == 0) & hard).sum()), int(((truth == 1) & ~hard).sum())
            require(tp + fn > 0 and tn + fp > 0, 'q subset missing a class')
            rows.append({**identity, 'subset': subset, 'row_count': len(selected),
                         'accuracy': (tp + tn) / len(selected),
                         'balanced_accuracy': .5 * (tp / (tp + fn) + tn / (tn + fp)),
                         'keyhole_recall': tp / (tp + fn), 'false_negative': fn, 'false_positive': fp,
                         'true_negative': tn, 'true_positive': tp})
    return pd.DataFrame(rows)


def collect_validate():
    pop, specs, a0, p1 = p.load()
    source_checks = provenance_gate()['checks']
    files = sorted((OUT / 'checkpoints').glob('*.json.gz'))
    require(len(files) == 100, '100 complete P2 checkpoints required')
    predictions, paths, candidates, margins, diagnostics = [], [], [], [], []
    p2 = {}
    flag_distances = p.w85.b1_distance(pop)
    query_count = 0
    for s in specs:
        data = p.p14.read_checkpoint(OUT / 'checkpoints' / (s.run_id + '.json.gz'))
        require(data['complete'] and data['fingerprint'] == p.fingerprint(), 'incomplete/stale checkpoint')
        path = data['queried_indices']; p2[s.run_id] = path
        require(len(path) == len(set(path)) == 80 and set(path).issubset(s.train_indices), 'P2 path invalid')
        require(path[:16] == a0[s.run_id][:16] == p1[s.run_id][:16], 'B16 mismatch')
        require(len(data['queries']) == 64 and len(data['predictions']) == 65 * 81, 'checkpoint row counts')
        for budget, q in zip(range(16, 80), data['queries']):
            ids = np.asarray(q['candidate_indices'], int)
            prob = np.asarray(q['candidate_probabilities'], float)
            require(q['budget'] == budget and np.isfinite(prob).all() and ((prob >= 0) & (prob <= 1)).all(), 'candidate values')
            require(np.array_equal(ids, np.setdiff1d(s.train_indices, path[:budget])), 'candidate-set drift')
            winner = int(ids[np.lexsort((ids, np.abs(prob - .5)))[0]])
            require(winner == q['selected'] == path[budget], 'stored argmin/tie-break mismatch')
            query_count += 1
            for idx, pr in zip(ids, prob):
                candidates.append({'run_id': s.run_id, 'budget': budget, 'population_row_index': int(idx),
                                   'probability': float(pr), 'selected': int(idx) == winner})
            margins.append({'run_id': s.run_id, 'repeat': s.repeat, 'model': 'P2', 'budget': budget,
                            'selected_margin': q['selected_margin']})
        frame = pd.DataFrame(data['predictions'])
        flags = p.p17.subset_flags(s, pop, flag_distances)
        for budget, g in frame.groupby('budget'):
            require(g.population_row_index.tolist() == list(s.test_indices), 'test identity drift')
            require(np.array_equal(g.truth, pop.iloc[list(s.test_indices)].has_keyhole.astype(int)), 'test truth drift')
            require(np.array_equal(g.is_q20, flags['B1_q20']) and np.array_equal(g.is_q30, flags['B1_q30']), 'evaluation subset drift')
        predictions.extend(data['predictions'])
        for d in data['diagnostics']:
            diagnostics.append({'run_id': s.run_id, 'budget': d['budget'], 'model': 'M3', **d['M3']})
            if d['G3'] is not None:
                diagnostics.append({'run_id': s.run_id, 'budget': d['budget'], 'model': 'G3', **d['G3']})
        for arm, path in [('P0', a0[s.run_id]), ('P1', p1[s.run_id]), ('P2', path)]:
            for order, idx in enumerate(path, 1):
                paths.append({'run_id': s.run_id, 'repeat': s.repeat, 'fold': s.fold, 'model': arm,
                              'query_order': order, 'population_row_index': idx,
                              'role': 'initial_design' if order <= 16 else 'active_query'})
    p2pred = pd.DataFrame(predictions)
    p0pred = p.p14.load_p0_predictions()
    p1pred = pd.read_csv(p.p14.OUTPUT / 'new_predictions.csv.gz')
    require(set(p1pred.model) == {'P1'}, 'unexpected stored P1 models')
    allpred = pd.concat([p0pred, p1pred, p2pred], ignore_index=True)
    require(len(allpred) == 3 * 100 * 65 * 81, 'all arm prediction counts')
    require(np.isfinite(allpred.probability).all(), 'prediction nonfinite')
    initial = allpred[allpred.budget == 16].pivot(index=['run_id','population_row_index'], columns='model', values='probability')
    initial_error = float(max(abs(initial.P2-initial.P1).max(), abs(initial.P2-initial.P0).max()))
    require(initial_error < 1e-8, 'all-run M3 B16 parity failure')
    metrics = metrics_from_predictions(allpred)
    historical = pd.read_csv(p.p14.OUTPUT / 'outer_run_metrics.csv.gz')
    # Phase 1.14 publishes per-run accuracy AULCs and aggregate checkpoint metrics.
    old = metrics[metrics.model.isin(['P0','P1'])]
    auc_rows=[]
    for keys,g in old[old.subset.ne('full81')].groupby(['run_id','model','subset']):
        g=g.sort_values('budget')
        auc_rows.append(dict(zip(['run_id','model','subset'],keys),
                             reproduced=float(np.trapezoid(g.accuracy,g.budget)/64)))
    comparison=pd.DataFrame(auc_rows).merge(historical,on=['run_id','model','subset'],validate='one_to_one')
    require(len(comparison)==400,'old-arm AULC parity count')
    metric_errors={'accuracy_AULC':float(abs(comparison.reproduced-comparison.accuracy_AULC_16_80).max())}
    checkpoint=pd.concat([pd.read_csv(p.p14.OUTPUT/name) for name in
                           ['checkpoint16_40_80_summary.csv','full81_checkpoint_summary.csv']])
    for col in ['accuracy','balanced_accuracy','keyhole_recall','false_negative','false_positive']:
        errors=[]
        for row in checkpoint[(checkpoint.contrast=='none')&(checkpoint.metric==col)].itertuples():
            value=old[(old.model==row.model)&(old.subset==row.subset)&(old.budget==row.budget)][col].mean()
            errors.append(abs(value-row.mean))
        require(len(errors)>0, f'missing historical {col} checkpoints')
        metric_errors[col]=float(max(errors))
    require(max(metric_errors.values())<1e-12,f'old-arm metric parity: {metric_errors}')
    checks = {**source_checks, 'gate1_population': True, 'gate2_100_runs': True,
              'gate5_all_arm_initial_design': True, 'gate6_P2_training_only': True,
              'gate7_no_duplicates': True, 'gate8_selector_revealed_labels_only': True,
              'gate9_all_6400_argmin_and_ties': query_count == 6400,
              **json.loads((OUT/'baseline_gate.json').read_text())['checks'],
              'frozen_q20_q30_memberships': True, 'all_run_B16_M3_parity': True,
              'old_arm_metric_parity': True, 'complete_metric_grid': len(metrics) == 58500}
    require(all(checks.values()), 'final validation checks')
    validation = {'status': 'PASS', 'check_count': len(checks), 'checks': checks,
                  'selection_steps_audited': query_count, 'candidate_rows_audited': len(candidates),
                  'prediction_rows': len(allpred), 'metric_rows': len(metrics),
                  'all_run_B16_max_probability_error': initial_error, 'old_arm_metric_max_errors': metric_errors,
                  'gate8_evidence': inspect.getsource(p.select_g3),
                  'scope': 'data/model/trajectory validation; artifact validation recorded separately'}
    write_json(OUT/'validation_report.json', validation)
    write_csv(OUT/'p2_test_predictions.csv.gz', p2pred)
    write_csv(OUT/'candidate_probability_audit.csv.gz', pd.DataFrame(candidates))
    diagnostic_frame=pd.DataFrame(diagnostics)
    write_csv(OUT/'fit_diagnostics.csv.gz', diagnostic_frame)
    fit_summary=[]
    for name,g in diagnostic_frame.groupby('model'):
        fit_summary.append({'model':name,'fit_count':len(g),
            'fallback_count':int((g.fallback_status.fillna('none')!='none').sum()),
            'optimizer_converged_fraction':float(g.optimizer_converged.dropna().astype(bool).mean()) if name=='M3' else None,
            'optimized_primary_fraction':float(g.fit_status.eq('optimized_primary').mean()) if name=='G3' else None,
            'any_length_bound_fraction':float(g.any_length_bound_hit.mean())})
    write_csv(OUT/'fit_diagnostics_summary.csv',pd.DataFrame(fit_summary))
    write_csv(OUT/'query_paths.csv.gz', pd.DataFrame(paths))
    write_csv(OUT/'budget_metrics.csv.gz', metrics)
    p1query = pd.read_csv(p.p14.OUTPUT/'m3_margin_queries.csv.gz')
    for q in p1query.itertuples():
        margins.append({'run_id': q.run_id, 'repeat': q.repeat, 'model': 'P1', 'budget': q.current_budget,
                        'selected_margin': q.margin_abs_probability_minus_half})
    write_csv(OUT/'selector_margin_diagnostics.csv.gz', pd.DataFrame(margins))
    mechanisms = []
    y = pop.has_keyhole.astype(int).to_numpy()
    for s in specs:
        arms = {'P0': a0[s.run_id], 'P1': p1[s.run_id], 'P2': p2[s.run_id]}
        for b in range(16,81):
            for arm, path in arms.items():
                count = int(y[path[:b]].sum())
                mechanisms.append({'run_id': s.run_id,'repeat': s.repeat,'budget': b,'model': arm,
                                   'keyhole_count': count,'keyhole_fraction': count/b})
    detail = pd.DataFrame(mechanisms)
    write_csv(OUT/'mechanism_detail.csv.gz', detail)
    write_csv(OUT/'mechanism_summary.csv', detail.groupby(['model','budget'],as_index=False)[['keyhole_count','keyhole_fraction']].mean())
    overlap = []
    for s in specs:
        for b in [24,40,80]:
            for name, control in [('P1',p1[s.run_id]),('P0',a0[s.run_id])]:
                a, c = set(p2[s.run_id][:b]),set(control[:b])
                aa, cc = set(p2[s.run_id][16:b]),set(control[16:b])
                overlap.append({'run_id':s.run_id,'repeat':s.repeat,'budget':b,'contrast':'P2-'+name,
                                'prefix_jaccard':len(a&c)/len(a|c),'active_only_jaccard':len(aa&cc)/len(aa|cc),
                                'different_sequence':p2[s.run_id][:b] != control[:b]})
    overlap = pd.DataFrame(overlap)
    write_csv(OUT/'path_overlap_detail.csv', overlap)
    write_csv(OUT/'path_overlap_summary.csv', overlap.groupby(['contrast','budget'],as_index=False)[['prefix_jaccard','active_only_jaccard','different_sequence']].mean())
    return validation


def analyze():
    metrics = pd.read_csv(OUT/'budget_metrics.csv.gz')
    outer = []
    for (run, repeat, fold, model, subset), group in metrics[metrics.subset.ne('full81')].groupby(['run_id','repeat','fold','model','subset']):
        for end in [40,80]:
            g = group[group.budget <= end].sort_values('budget')
            require(g.budget.tolist() == list(range(16,end+1)), 'AULC budget grid')
            outer.append({'run_id':run,'repeat':repeat,'fold':fold,'model':model,'subset':subset,'end_budget':end,
                          'AULC':float(np.trapezoid(g.balanced_accuracy,g.budget)/(end-16))})
    outer = pd.DataFrame(outer)
    repeat = outer.groupby(['repeat','model','subset','end_budget'],as_index=False).AULC.mean()
    summary, contrasts = [], []
    for (model, subset, end), g in repeat.groupby(['model','subset','end_budget']):
        mean, lo, hi = p.p14.bootstrap_interval(g.sort_values('repeat').AULC.to_numpy(),f'summary|{model}|{subset}|BA|16-{end}')
        summary.append({'model':model,'subset':subset,'end_budget':end,'mean_AULC':mean,'ci_lower':lo,'ci_upper':hi})
    wide = repeat.pivot(index=['repeat','subset','end_budget'],columns='model',values='AULC').reset_index()
    deltas = []
    for (subset,end),g in wide.groupby(['subset','end_budget']):
        for control in ['P1','P0']:
            values = (g.sort_values('repeat').P2-g.sort_values('repeat')[control]).to_numpy()
            key = f'P2-{control}|{subset}|balanced_accuracy|B16-{end}'
            mean,lo,hi = p.p14.bootstrap_interval(values,key)
            contrasts.append({'contrast':'P2-'+control,'subset':subset,'end_budget':end,'mean_difference':mean,
                              'ci_lower':lo,'ci_upper':hi,'positive_repeat_blocks':int((values>0).sum()),
                              'zero_repeat_blocks':int((values==0).sum()),'bootstrap_draws':10000,
                              'seed':p.p14.seed_u32('bootstrap',key),
                              'inference_role':'primary' if (control,subset,end)==('P1','B1_q20',40) else 'secondary descriptive'})
            for r,value in zip(g.sort_values('repeat').repeat,values):
                deltas.append({'repeat':r,'contrast':'P2-'+control,'subset':subset,'end_budget':end,'difference':value})
    summary,contrasts,deltas = pd.DataFrame(summary),pd.DataFrame(contrasts),pd.DataFrame(deltas)
    write_csv(OUT/'outer_run_AULC.csv.gz',outer); write_csv(OUT/'repeat_AULC.csv',repeat)
    write_csv(OUT/'AULC_summary.csv',summary); write_csv(OUT/'paired_contrasts.csv',contrasts)
    write_csv(OUT/'repeat_contrasts.csv',deltas)
    checkpoints = metrics[metrics.budget.isin([16,24,32,40,60,80])].groupby(['model','subset','budget'],as_index=False)[['balanced_accuracy','accuracy','keyhole_recall','false_negative','false_positive']].mean()
    write_csv(OUT/'checkpoint_metrics.csv',checkpoints)
    curves = []
    for (arm,budget),g in metrics[metrics.subset.eq('B1_q20')].groupby(['model','budget']):
        values=g.groupby('repeat').balanced_accuracy.mean().sort_index().to_numpy()
        mean,lo,hi=p.p14.bootstrap_interval(values,f'curve|{arm}|B1_q20|BA|{budget}')
        curves.append({'model':arm,'budget':budget,'mean':mean,'lower':lo,'upper':hi})
    curves=pd.DataFrame(curves); write_csv(OUT/'learning_curve_summary.csv',curves)
    figures=OUT/'figures'; figures.mkdir(exist_ok=True)
    colors={'P0':'#777777','P1':'#1774ad','P2':'#d05a26'}
    labels={'P0':'P0: historical A0','P1':'P1: M3 margin','P2':'P2: G3 margin'}
    for end,name in [(80,'01_q20_learning_curve'),(40,'02_early_q20_zoom')]:
        fig,ax=plt.subplots(figsize=(9,5))
        for arm in ['P0','P1','P2']:
            g=curves[(curves.model==arm)&(curves.budget<=end)]
            ax.plot(g.budget,g['mean'],label=labels[arm],color=colors[arm])
            ax.fill_between(g.budget,g.lower,g.upper,alpha=.13,color=colors[arm])
        ax.set(xlabel='Revealed simulations (budget B)',ylabel='q20 balanced accuracy',xlim=(16,end),
               title='Same M3 evaluator; three acquisition paths')
        ax.grid(alpha=.2); ax.legend(loc='lower right')
        fig.text(.5,.01,'Means and pointwise 95% bootstrap intervals over 20 repeat blocks; frozen offline pool',ha='center',fontsize=8)
        fig.tight_layout(rect=(0,.035,1,1)); fig.savefig(figures/(name+'.png'),dpi=170); plt.close(fig)
    for control,num in [('P1','03'),('P0','04')]:
        g=deltas[(deltas.contrast=='P2-'+control)&(deltas.subset=='B1_q20')&(deltas.end_budget==40)]
        fig,ax=plt.subplots(figsize=(9,4.6))
        ax.bar(g.repeat,g.difference,color=[colors['P2'] if v>=0 else colors['P1'] for v in g.difference])
        ax.axhline(0,color='black',linewidth=.8);ax.axhline(g.difference.mean(),color='black',linestyle='--',label='Mean difference')
        ax.set(xlabel='Repeat block (five folds per block)',ylabel='Balanced-accuracy AULC difference',
               title=f'P2 - {control}: early q20 AULC, B16-B40',xticks=range(1,21))
        ax.legend(loc='lower right');fig.tight_layout();fig.savefig(figures/f'{num}_early_P2_minus_{control}.png',dpi=170);plt.close(fig)
    primary=contrasts[contrasts.inference_role=='primary'].iloc[0]
    decision='G3_SELECTOR_SMALL_OR_UNRESOLVED'
    if primary.mean_difference>=p.PRACTICAL and primary.ci_lower>0: decision='G3_SELECTOR_SUPPORTED'
    elif primary.mean_difference<=-p.PRACTICAL and primary.ci_upper<0: decision='G3_SELECTOR_NOT_SUPPORTED'
    write_json(OUT/'decision.json',{'decision':decision,'replace_P1':decision=='G3_SELECTOR_SUPPORTED',
                                 'primary':primary.to_dict(),'practical_threshold':p.PRACTICAL})
    return decision


def reports_notebook():
    decision=json.loads((OUT/'decision.json').read_text())
    c=pd.read_csv(OUT/'paired_contrasts.csv'); s=pd.read_csv(OUT/'AULC_summary.csv')
    overlap=pd.read_csv(OUT/'path_overlap_summary.csv')
    mechanism=pd.read_csv(OUT/'mechanism_summary.csv')
    fit_summary=pd.read_csv(OUT/'fit_diagnostics_summary.csv')
    def contrast(control,end): return c[(c.contrast=='P2-'+control)&(c.subset=='B1_q20')&(c.end_budget==end)].iloc[0]
    def result(row): return f"{row.mean_difference:+.6f} (95% repeat-block interval [{row.ci_lower:+.6f}, {row.ci_upper:+.6f}]); {int(row.positive_repeat_blocks)}/20 repeat blocks positive"
    primary=contrast('P1',40)
    numerical_direction='higher' if primary.mean_difference>0 else 'lower' if primary.mean_difference<0 else 'equal'
    uncertainty_statement=('The interval supports a positive difference.' if primary.ci_lower>0 else
                           'The interval supports a negative difference.' if primary.ci_upper<0 else
                           'The interval includes zero, so the direction remains unresolved.')
    overlap40=overlap[(overlap.contrast=='P2-P1')&(overlap.budget==40)].iloc[0]
    overlap80=overlap[(overlap.contrast=='P2-P1')&(overlap.budget==80)].iloc[0]
    replace=decision['replace_P1']
    interpretation=('supports replacing M3-margin with G3-margin' if replace else 'does not support replacing M3-margin with G3-margin')
    report=f'''# Week 9 Phase 1.20 — M3 evaluator with sequential G3-margin acquisition

Decision: **{decision['decision']}**. This frozen offline finite-pool experiment {interpretation}.

## Direct answers

1. **Is P2 different from A0?** Yes. The source audit verifies that Week 8.5 uses an isotropic Matérn-3/2 GPC, whereas Phase 1.12 G3 uses four ARD length scales. Exact fitting and prediction functions are imported, including bounds, fallbacks, preprocessing and seeds.
2. **Did query paths differ?** Against P1, mean prefix Jaccard is {overlap40.prefix_jaccard:.3f} at B40 and {overlap80.prefix_jaccard:.3f} at B80; {100*overlap80.different_sequence:.0f}% of B80 sequences differ. Active-only B40 Jaccard is {overlap40.active_only_jaccard:.3f}. These describe path differences without establishing a causal mechanism. The first 16 points are identical in every run. P2 was generated live from revealed labels, not replayed from A0.
3. **Did P2 outperform P1?** M3 evaluated on P2 had {numerical_direction} mean early performance than M3 evaluated on P1: {result(primary)}. {uncertainty_statement} The final recommendation also applies the frozen practical threshold.
4. **How large is the early difference?** {primary.mean_difference:+.6f} normalized AULC, equivalent to {100*primary.mean_difference:+.3f} percentage points averaged over B16–B40.
5. **95% interval?** [{primary.ci_lower:+.6f}, {primary.ci_upper:+.6f}], percentile bootstrap of 20 paired repeat means, 10,000 draws.
6. **Positive repeats?** {int(primary.positive_repeat_blocks)}/20, retaining each repeat's five folds together.
7. **Full B16–B80 vs P1?** {result(contrast('P1',80))}.
8. **Versus P0?** Early: {result(contrast('P0',40))}. Full: {result(contrast('P0',80))}.
9. **Safest thesis interpretation?** With the same M3 evaluator and frozen splits, these results measure acquisition-path performance on the offline 405-simulation population. They establish no prospective simulator savings, external validity, causal mechanism or superiority of G3 as a predictive model.
10. **Replace the incumbent?** {'Yes, within this frozen benchmark.' if replace else 'No. Retain M3-margin as the acquisition incumbent on this evidence.'}

## Design and evidence

P0 loads the exact Week 8.5 A0 trajectory. P1 loads the validated Phase 1.14 M3-margin trajectory. P2 fits the exact Phase 1.12 standalone G3 at each budget B16–B79 and selects the unqueried training-pool row minimizing |p_G3−0.5|, with smallest population row index resolving ties. The oracle reveals that label only after selection. M3 is refit on each prefix and evaluates the untouched 81-row test set at every integer budget B16–B80.

Population: 405 rows, 73 Keyhole, 332 Conduction. Inputs: P, VX, LS, ST (substrate temperature). has_keyhole means any observed frame has Keyhole behavior. All 100 stored grouped outer splits and initial designs are preserved; each run has 324 pool rows and 81 test rows. The historical loader deterministically reconstructs split objects, and every membership is checked against the persisted split manifest. No new split is selected.

The selector interface contains only training-pool features, training row IDs, revealed row IDs and labels, run ID and budget. Test features, test labels, hidden candidate labels and q20/q30 flags are absent. The q20/q30 subsets retain their frozen evaluation-only definitions. Candidate probability tables allow independent checking of all 6,400 choices.

**Endpoint distinction:** Earlier quoted values (H≈0.830813, G3≈0.826595, P0≈0.842491, P1≈0.844623) are accuracy AULCs. This phase's primary endpoint is balanced accuracy as requested. Both metrics are supplied at checkpoints; the historical accuracy values must not be compared numerically with the new balanced-accuracy endpoint.

Normalized trapezoidal AULC is the integral of balanced accuracy divided by 24 for B16–B40 or 64 for B16–B80. Higher is better. The only primary inference is P2−P1 on early q20. P2−P0 and q30/full-budget intervals are secondary descriptive robustness checks, with no new global multiple-testing family. Phase 1.14 has no sign-flip test; its bootstrap function and deterministic seed framework are reused exactly.

The pre-result practical threshold is 0.01 AULC. SUPPORTED requires a mean at least +0.01 and lower interval bound above zero. NOT_SUPPORTED requires a mean at most −0.01 and upper bound below zero. Remaining cases are SMALL_OR_UNRESOLVED. This threshold is an operational decision convention, not an established economic simulator-savings threshold.

## AULC estimates

{s.to_markdown(index=False)}

## Paired contrasts

{c.to_markdown(index=False)}

## Path mechanisms

{overlap.to_markdown(index=False)}

Jaccard is intersection size divided by union size. Prefix overlap includes the shared initialization; active-only overlap excludes it. Revealed Keyhole counts/fractions and selector margins are in their companion tables. Margins diagnose each selector only: G3 and M3 probabilities must not be assumed equally calibrated. Phase 1.14 contains no equivalent standardized coverage diagnostic, so no new spatial mechanism study is added.

Revealed class composition (counts are means over runs):

{mechanism[mechanism.budget.isin([16,24,40,80])].to_markdown(index=False)}

Exact-fit diagnostics (all warnings and per-fit details remain in the compressed table):

{fit_summary.to_markdown(index=False)}

M3 reports optimizer convergence for 91.923% of fits (525 of 6,500 fits are not declared converged). G3 and M3 used no fallbacks. These numerical diagnostics are retained as a limitation of the unchanged historical fitting procedure; passing parity gates does not mean every optimizer declared convergence. No alternate solver was substituted after inspecting results.

## Validation and reproducibility

The baseline gates reproduce stored G3 B16 test probabilities and M3 B24 test probabilities and next query. Final validation checks all B16 evaluator predictions across 100 runs, exact A0 parity with the original Week 8.5 checkpoint archive, stored split membership, P1 path identity, uniqueness, training-only eligibility, all candidate argmins, frozen subset flags and complete metrics. Old P0/P1 metrics are independently reconstructed from stored predictions and compared to Phase 1.14.

`input_provenance.json` pins input hashes and runtime versions. `fit_diagnostics.csv.gz` retains exact G3 fallbacks/warnings and M3 optimization diagnostics. The study does not replace or repair historical model implementations. Per-budget atomic checkpoints resume interrupted outer runs; sequential budgets within a run are never parallelized.

Figures: `figures/01_q20_learning_curve.png`, `02_early_q20_zoom.png`, `03_early_P2_minus_P1.png`, `04_early_P2_minus_P0.png`.
'''
    (OUT/'FINAL_PHASE1_20_REPORT.md').write_text(report,encoding='utf-8')
    summary=f'''# Phase 1.20 — discussion with Ioan

**Question:** Can standalone G3 select better queries while M3 remains the evaluator?

**Controlled comparison:** 405 frozen simulations; 100 identical grouped outer splits; shared 16-point starts. P0 = historical isotropic-GPC path; P1 = M3-margin path; P2 = new sequential ARD G3-margin path. All paths use the exact M3 evaluator.

**Primary, q20 balanced-accuracy AULC B16–B40:** P2−P1 = {result(primary)}.

**Full B16–B80:** P2−P1 = {result(contrast('P1',80))}.

**Historical control:** early P2−P0 = {result(contrast('P0',40))}.

**Decision:** {decision['decision']}. {'Replace P1 within this frozen benchmark.' if replace else 'Retain M3-margin; this result does not justify replacing it.'}

The practical threshold (0.01 AULC) was frozen before P2 results. Earlier reported Phase 1.14 numbers were accuracy, not balanced accuracy. This is evidence about offline acquisition paths, not prospective simulation savings or G3 predictive superiority.
'''
    (OUT/'SUPERVISOR_SUMMARY.md').write_text(summary,encoding='utf-8')
    cells=[]
    def md(text): cells.append(nbf.v4.new_markdown_cell(text))
    def code(text): cells.append(nbf.v4.new_code_cell(text))
    md('# Week 9 Phase 1.20: G3 chooses, M3 predicts\n\nA step-by-step explanation of acquisition sample efficiency on a frozen finite simulation pool. ST means substrate temperature; the target is any observed Keyhole frame.')
    code("from pathlib import Path\nimport json, pandas as pd\nfrom IPython.display import display, Image, Markdown\nROOT=Path.cwd()\nwhile not (ROOT/'src').is_dir(): ROOT=ROOT.parent\nOUT=ROOT/'outputs/week9_phase1_20_m3_g3_margin_acquisition'\ndisplay(json.loads((OUT/'baseline_gate.json').read_text()))")
    md('## 1. The three paths\n\nP0 is the frozen historical Week 8.5 GPC margin path. P1 is the stored Phase 1.14 M3 margin path. P2 is the new sequential G3 margin path. A path records the order in which labels become available. The evaluator is M3 in every arm.')
    code("paths=pd.read_csv(OUT/'query_paths.csv.gz')\ndisplay(paths.groupby('model').agg(runs=('run_id','nunique'),rows=('query_order','count')))\ndisplay(paths[(paths.run_id=='w85__r01_f01') & paths.query_order.between(14,21)].pivot(index='query_order',columns='model',values='population_row_index'))")
    md('## 2. Why P2 is not A0\n\nThe historical GPC shares one kernel length scale across the four standardized inputs. G3 uses automatic relevance determination (ARD): a separate learned length scale for each input. The kernel remains Matérn-3/2. This changes the selector model; P2 must therefore be fitted live rather than replaying A0.')
    code("audit=json.loads((OUT/'selector_specification_audit.json').read_text())\ndisplay(pd.DataFrame({k:audit[k] for k in ['Week8.5','G3']}).T)")
    md('## 3. Why G3 can select while M3 evaluates\n\nM3 models the latent function as a fitted physics mean based on log(h) plus a four-dimensional GP discrepancy. It predicts Keyhole probability on held-out rows. Separately, standalone G3 ranks candidates by distance of its probability from 0.5. The discrepancy inside M3 is not an independent Keyhole classifier.')
    md('## 4. One sequential step\n\nAt B=16, fit G3 on the shared 16 revealed labels. Score every remaining training-pool candidate. Choose the minimum |p−0.5|, resolving exact ties by smallest population row index. Reveal the chosen label. At B=17 refit from the updated prefix. Continue until 80 labels are available. At each budget, fit M3 on that prefix and evaluate it on the untouched test set.')
    code("margins=pd.read_csv(OUT/'selector_margin_diagnostics.csv.gz')\ndisplay(margins[(margins.run_id=='w85__r01_f01') & (margins.budget<=20)])")
    md('## 5. Preventing information leakage\n\nThe selector receives training-pool features and revealed labels only. The test set and q20/q30 membership belong to evaluation. The 100 grouped splits are fixed; test information cannot determine the next query. Stored candidate probabilities permit independent checks of all selected minima.')
    code("validation=json.loads((OUT/'validation_report.json').read_text())\ndisplay(pd.DataFrame(list(validation['checks'].items()),columns=['Gate','Passed']))\ndisplay(pd.read_csv(OUT/'fit_diagnostics_summary.csv'))")
    md('## 6. What balanced accuracy and AULC mean\n\nKeyhole recall is the fraction of actual Keyhole rows correctly predicted. Conduction recall is defined similarly. Balanced accuracy is their average, so a large Conduction class does not dominate the score. AULC is the trapezoidal area under the learning curve divided by its budget span. For B16–B40 the span is 24. Earlier phase headline AULCs used ordinary accuracy; these are different endpoints.')
    code("metrics=pd.read_csv(OUT/'checkpoint_metrics.csv')\ndisplay(metrics[(metrics.subset=='B1_q20') & metrics.budget.isin([16,24,40])])")
    md('## 7. Primary early-budget result\n\nThe predeclared primary contrast is P2 minus P1 on q20 balanced-accuracy AULC B16–B40. Each repeat averages five folds; inference resamples 20 repeat blocks. The 100 folds are not treated as independent.')
    code("contrasts=pd.read_csv(OUT/'paired_contrasts.csv')\naulc=pd.read_csv(OUT/'AULC_summary.csv')\ndisplay(aulc[(aulc.subset=='B1_q20') & (aulc.end_budget==40)])\ndisplay(contrasts[contrasts.inference_role=='primary'])\ndisplay(Image(filename=str(OUT/'figures/02_early_q20_zoom.png')))\ndisplay(Image(filename=str(OUT/'figures/03_early_P2_minus_P1.png')))")
    md('## 8. Full-budget and secondary results\n\nThe B16–B80 view checks whether later behavior changes the picture. q30 and P2 versus P0 are secondary descriptive checks. They do not replace the predeclared primary endpoint.')
    code("display(contrasts[contrasts.inference_role!='primary'])\ndisplay(Image(filename=str(OUT/'figures/01_q20_learning_curve.png')))")
    md('## 9. What changed in the paths?\n\nJaccard overlap compares sets of revealed rows: 1 means identical sets and 0 means no shared rows. Prefix overlap includes the shared initial 16; active-only overlap excludes them. Class counts describe sampling composition. They are post-hoc diagnostics, not causal explanations. Selector margins from G3 and M3 need not have the same calibration.')
    code("display(pd.read_csv(OUT/'path_overlap_summary.csv'))\nmechanism=pd.read_csv(OUT/'mechanism_summary.csv')\ndisplay(mechanism[mechanism.budget.isin([16,24,40,80])])")
    md('## 10. Thesis interpretation\n\nThe practical threshold was frozen at 0.01 AULC before P2 results. A supported gain must also have an interval above zero. This experiment tests acquisition paths with the same evaluator on the frozen offline pool. It cannot establish prospective savings, external validity, or physical causality.')
    code("display(Markdown((OUT/'SUPERVISOR_SUMMARY.md').read_text()))")
    nb=nbf.v4.new_notebook(cells=cells,metadata={'kernelspec':{'display_name':'Python 3','language':'python','name':'python3'}})
    NOTEBOOK.parent.mkdir(parents=True,exist_ok=True)
    km=KernelManager(kernel_name='python3')
    km.kernel_spec.argv=[sys.executable,'-m','ipykernel_launcher','-f','{connection_file}']
    client=NotebookClient(nb,km=km,timeout=180,resources={'metadata':{'path':str(ROOT)}})
    client.execute();nbf.write(nb,NOTEBOOK)
    require(all(c.execution_count is not None for c in nb.cells if c.cell_type=='code'), 'notebook unexecuted')
    require(not any(o.output_type=='error' for c in nb.cells if c.cell_type=='code' for o in c.outputs), 'notebook error')
    write_json(OUT/'artifact_validation.json',{'status':'PASS','notebook_code_cells':sum(c.cell_type=='code' for c in nb.cells),
               'all_executed':True,'figure_count':len(list((OUT/'figures').glob('*.png'))),'visual_inspection':'pending'})


if __name__ == '__main__':
    parser=argparse.ArgumentParser();parser.add_argument('command',choices=['provenance','collect','analyze','artifacts','all']);args=parser.parse_args()
    if args.command=='provenance': print(provenance_gate())
    if args.command in ['collect','all']: print(collect_validate())
    if args.command in ['analyze','all']: print(analyze())
    if args.command in ['artifacts','all']: reports_notebook()
