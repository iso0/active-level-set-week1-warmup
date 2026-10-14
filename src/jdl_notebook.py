"""Build and execute the step-by-step notebook JOINT_MODEL_WALKTHROUGH.ipynb.

No Jupyter kernel is installed in this environment (and no package was downloaded), so the cells are executed here
in order, in one shared namespace, and their real stdout and figures are written into the notebook.  The notebook
re-runs unchanged in any Jupyter kernel with the repository on the path.

Step: python -m src.jdl_notebook
"""
from __future__ import annotations

import base64
import contextlib
import io
import os
import sys
import traceback
from pathlib import Path

import nbformat

ROOT = Path(__file__).resolve().parents[1]
NB = ROOT / "outputs" / "joint_depth_label_development" / "JOINT_MODEL_WALKTHROUGH.ipynb"

CELLS = [
    ("md", """# Joint depth–label GP: a step-by-step walkthrough

**What this notebook covers:** it explains the model, fits it to one real Stage M checkpoint, makes one paid update, computes one acquisition decision, and then shows the study's actual results.
- Everything uses the frozen Stage M priors and the repository port `src/jdl_model.py`.
- The demonstration checkpoint is NEW DEV repeat 1, fold 1, which is Stage M data. The acquisition shown here is an illustration, not a Stage A result.

**The model.**

$$f \\sim GP(0, k_f),\\quad \\theta \\sim N(0, 0.35^2),\\quad \\delta \\sim GP(0, k_\\delta^{c}),\\qquad h(x) = f(x) - \\theta + \\delta(x)$$
$$z = \\log(A/111\\,\\mu m) \\mid f \\sim N(f, 0.03^2),\\qquad Y \\mid h \\sim \\mathrm{Bernoulli}\\{\\Phi(h/0.15)\\}$$

- **Response:** f is the log active-window depth relative to 111 µm.
- **Threshold:** θ is an uncertain global threshold.
- **Discrepancy:** δ is a smooth discrepancy, centred on the fixed feature-only candidate pool.
- **Inference:** the paid responses condition f exactly; a joint probit Laplace step then adds the paid labels. Every cross-covariance between f, θ and δ is kept.
- **Information contract:** the learner sees paid rows only. Test labels and test depths are used only by the evaluator."""),
    ("code", """import numpy as np, pandas as pd, json
from scipy.special import ndtr
import src.jdl_model as JM
import src.jdl_stage_m as SMM
cfg = JM.STAGE_M_CONFIG
print({k: v for k, v in cfg.__dict__.items()})
man = json.loads((SMM.OUT / 'STUDY_MANIFEST.json').read_text(encoding='utf-8'))
print('frozen manifest written', man['written_utc'], '| primary contrast:', man['primary_contrast'])"""),
    ("md", """## 1. One real checkpoint: NEW, repeat 1, fold 1, B16 (feature-only maximin prefix)

- **What the oracle returns:** only the paid rows' outcomes, as (Y, z). The missing-A run keeps its label with z = NaN.
- **Inputs:** log(P, VX, LS, ST), standardized over the fold's pool."""),
    ("code", """task = [t for t in SMM.build_tasks() if (t['population'], t['repeat'], t['fold']) == ('NEW', 1, 1)][0]
paths = pd.read_csv(SMM.SM / 'paths.csv')
g = paths[(paths.population == 'NEW') & (paths.repeat == 1) & (paths.fold == 1)].sort_values('query_index')
pos = {s: i for i, s in enumerate(task['ids'])}; task['path'] = g.sim_id.map(pos).to_numpy(int)
std, scaler = SMM.standardizer(task)
paid = SMM.Oracle(task).reveal(task['path'][:16])
print('paid simulations:', len(paid.ids), '| positives', int(paid.y.sum()), '| negatives', int((paid.y == 0).sum()), '| responses', int(np.isfinite(paid.z).sum()))
print(pd.DataFrame({'Y': paid.y, 'z=log(A/111)': np.round(paid.z, 3), 'sim_id (full)': paid.ids}).head(8).to_string(index=False))
model = JM.JointDepthLabelGP(std(task['X'][task['pool']]), cfg).fit(std(paid.X), paid.y, paid.z)
print({k: model.diagnostics[k] for k in ('solver_status', 'gradient_inf', 'gradient_accepted', 'newton_iterations')})
post = model.marginals(std(task['X'][task['test']]))
print('theta posterior: mean %.3f, sd %.3f (prior sd 0.35)' % (post['theta_mean'], np.sqrt(post['theta_var'])))"""),
    ("md", """## 2. What a prediction is made of

Each test probability is Φ(μ_h / √(τ² + V_h)), with μ_h = μ_f − μ_θ + μ_δ. The label column is shown for the reader only; the model never sees it.

Simulations are identified by their full IDs. The H suffix alone is not unique: two test simulations in this very fold end in `H-24e1882408`, a suffix shared by 14 NEW simulations."""),
    ("code", """te = task['test']
tab = pd.DataFrame({'VX': task['VX'][te].round(3), 'f (pred z)': post['f_mean'].round(3),
                    'theta': round(post['theta_mean'], 3), 'delta': post['delta_mean'].round(3), 'h': post['h_mean'].round(3),
                    'sd(h)': np.sqrt(post['h_var']).round(3), 'p': post['p'].round(3), 'label (evaluator only)': task['y'][te],
                    'sim_id (full)': [task['ids'][i] for i in te]})
print(tab.sort_values('p').head(10).to_string(index=False))"""),
    ("md", """## 3. One paid update

- **What happens:** the next simulation on the frozen path is paid, and its label and response are revealed together.
- **How the model updates:** it is refit from the original prior with every paid likelihood factor exactly once. The old posterior is never reused as a new prior."""),
    ("code", """paid17 = SMM.Oracle(task).reveal(task['path'][:17])
new = paid17.ids[-1]
print('revealed:', new, '| Y =', paid17.y[-1], '| z =', round(float(paid17.z[-1]), 3))
model17 = JM.JointDepthLabelGP(std(task['X'][task['pool']]), cfg).fit(std(paid17.X), paid17.y, paid17.z)
post17 = model17.marginals(std(task['X'][te]))
xref = std(task['X'][task['pool']])
print('theta: %.3f -> %.3f | sd %.3f -> %.3f' % (post['theta_mean'], post17['theta_mean'], np.sqrt(post['theta_var']), np.sqrt(post17['theta_var'])))
print('integrated Var[pi] over the pool: %.5f -> %.5f' % (model.integrated_probability_variance(xref).mean(), model17.integrated_probability_variance(xref).mean()))
print('largest change in a test probability: %.3f' % np.max(np.abs(post17['p'] - post['p'])))"""),
    ("md", """## 4. One acquisition calculation (paired probability-variance reduction)

For a candidate j the score is the expected reduction of the pool-averaged Var[Φ(h/τ)] after observing (Z_j, Y_j) together:

$$a(j) = E_{Z_j}\\sum_i w_i\\Big[(p_i(Z_j) - p_i)^2 + \\frac{\\{J_{ij}(Z_j) - p_i(Z_j)q(Z_j)\\}^2}{q(Z_j)[1-q(Z_j)]}\\Big].$$

- **Integration over Z:** Gauss–Hermite.
- **J_ij:** a bivariate normal CDF (Genz).
- **Ranking rule:** compare 15 and 31 nodes, and accept the top candidate if its gap exceeds 2e plus the tail bound. Otherwise use 63 nodes, then a tie or a STOP. There is no fallback to margin.
- **Status:** an illustration on Stage M data, not a Stage A result."""),
    ("code", """from src.jdl_stage_a import select_pv, select_margin
cand = np.setdiff1d(task['pool'], task['path'][:16]); cid = [task['ids'][i] for i in cand]
log = []
j, rec = select_pv(model, std(task['X'][cand]), cid, xref, log)
s = pd.DataFrame([r for r in log if r['gh_order'] == 31]).sort_values('score', ascending=False).head(5)
print(s[['score', 'response_component', 'label_component', 'candidate']].round(6).to_string(index=False))
print('decision:', rec['decision'], '| e(15,31) = %.2e, gap = %.2e' % (rec['e_15_31'], rec['gap_31']))
jm, recm = select_margin(model, std(task['X'][cand]), cid, [])
print('probability-variance pick:', rec['selected'])
print('margin pick:              ', recm['selected'])"""),
    ("md", "## 5. The actual results"),
    ("code", """dec = json.loads((SMM.SM / 'STAGE_M_DECISION.json').read_text(encoding='utf-8'))
print('Stage M screen:', dec['decision'], '|', dec['NEW_B40_J_minus_Binary'])
m = pd.read_csv(SMM.SM / 'metrics_per_repeat.csv')
print(m[(m.population == 'NEW') & (m.budget == 40)].groupby('arm')[['BA', 'specificity', 'log_loss', 'AUC']].mean().round(3).to_string())
ta = pd.read_csv(SMM.OUT / 'mechanism/POSTHOC_threshold_alignment.csv')
print(ta[(ta.population == 'NEW') & (ta.budget == 40)].groupby('arm')[['BA_at_0.5', 'BA_at_paid_prevalence']].mean().round(3).to_string())"""),
    ("code", """import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
fig, ax = plt.subplots(figsize=(6, 3.2))
pr = pd.read_csv(SMM.SM / 'predictions_all.csv.gz')
yv = dict(zip(task['ids'], task['y']))
for arm, c in (('J', '#AA3377'), ('Binary_matched', '#999999')):
    g2 = pr[(pr.population == 'NEW') & (pr.budget == 40) & (pr.arm == arm)]
    lab = g2.sim_id.map(yv)
    ax.hist(g2.p[lab == 0], bins=20, range=(0, 1), alpha=.6, color=c, label=f'{arm}: negatives')
ax.axvline(0.5, color='k', ls=':', lw=1); ax.axvline(0.9, color='k', ls='--', lw=1)
ax.set_xlabel('predicted P(Keyhole) for the 12 NEW negatives (both repeats, B40)'); ax.legend(fontsize=7, frameon=False)
ax.set_title('Ranked below the positives but above 0.5: the decision rule matters', fontsize=8, loc='left')
plt.tight_layout(); plt.show()"""),
    ("code", """for name in ('exploratory/EX1_ba_aligned_decision_rule/EX1_RESULTS.json', 'exploratory/EX2_trained_response_prior/EX2_RESULTS.json'):
    p = SMM.OUT / name
    print(name, '->', json.dumps(json.loads(p.read_text(encoding='utf-8')), default=float)[:900] if p.exists() else 'not available')
tr = SMM.OUT / 'temporal_repair/summary_trajectory.csv'
print(pd.read_csv(tr).round(3).to_string() if tr.exists() else 'temporal repair: not available')"""),
    ("md", """## 6. Reading the results

- **What depth adds.** Paid continuous depth adds label information on OLD and POOLED, and improves NEW ranking and probability quality.
- **Why the screen failed.** The frozen NEW screen requires a balanced-accuracy gain at p ≥ 0.5 and it failed. The diagnostics point to the decision threshold under 91 % prevalence, to over-smoothed depth predictions in the fast-scan corner, and to 12 negatives being too few to resolve +0.01 BA.
- **The exploratory tests (fresh DEV repeats 5–8, manifests committed before any fit).**
  - EX1: predicting Keyhole when p ≥ π̂ (the paid prevalence) instead of p ≥ 0.5 raised NEW B40 J balanced accuracy from 0.543 to 0.878 (+0.335, interval +0.241 to +0.419), with specificity +0.81 and sensitivity −0.14. The same rule *lowered* Binary-matched BA (−0.067), so the gain is not a generic threshold effect.
  - EX2: a response prior trained on the paid depths (ML-II) halved the fast-scan depth error (RMSE 0.236 → 0.117) and added +0.028 BA at π̂ (interval +0.012 to +0.047).
  - Both are exploratory. Neither changes the frozen Stage M decision, and neither has been confirmed on reserved data.
- **What the gain consists of (POST-HOC, `exploratory/EXPLORATORY_REPORT.md` §3).**
  - At p ≥ π̂, the joint model labels the whole fast-scan corner (VX > 0.85 m/s) "no Keyhole": all 11 fast negatives are rejected and nearly all 12 fast positives are missed.
  - None of the tested models separated the cases inside that corner. This does not show that no discriminator exists.
  - The one persistent false positive is a slow scan whose recording ended early and which has no A.
- **Errata of 2026-10-14.**
  - p ≥ π̂ is a train-only heuristic: the paid fraction is not an unbiased prevalence estimate.
  - Its global BA gain costs short-K detection (J_trained 0.675 → 0.05), so J_trained at 0.5 remains a serious comparator.
  - Small ablation effects do not establish physical (non-)identifiability."""),
]


def run_cells():
    ns = {"__name__": "__notebook__"}
    sys.path.insert(0, str(ROOT))
    os.chdir(ROOT)
    nb = nbformat.v4.new_notebook()
    nb.metadata["kernelspec"] = {"name": "python3", "display_name": "Python 3", "language": "python"}
    nb.metadata["executed_by"] = "src/jdl_notebook.py (cells executed in order in one namespace; no Jupyter kernel installed)"
    count = 0
    for kind, src in CELLS:
        if kind == "md":
            nb.cells.append(nbformat.v4.new_markdown_cell(src)); continue
        count += 1
        buf = io.StringIO(); outputs = []
        try:
            import matplotlib
            matplotlib.use("Agg")
            import matplotlib.pyplot as plt
            plt.show = lambda *a, **k: None
            with contextlib.redirect_stdout(buf):
                exec(compile(src, f"<cell {count}>", "exec"), ns)
            if buf.getvalue():
                outputs.append(nbformat.v4.new_output("stream", name="stdout", text=buf.getvalue()))
            for num in plt.get_fignums():
                b = io.BytesIO(); plt.figure(num).savefig(b, format="png", dpi=120); plt.close(num)
                outputs.append(nbformat.v4.new_output("display_data", data={"image/png": base64.b64encode(b.getvalue()).decode()}))
        except Exception:
            outputs.append(nbformat.v4.new_output("stream", name="stdout", text=buf.getvalue()))
            outputs.append(nbformat.v4.new_output("error", ename="Error", evalue="cell failed", traceback=traceback.format_exc().splitlines()))
        cell = nbformat.v4.new_code_cell(src, execution_count=count); cell.outputs = outputs
        nb.cells.append(cell)
    NB.parent.mkdir(parents=True, exist_ok=True)
    nbformat.write(nb, str(NB))
    errs = sum(1 for c in nb.cells if c.cell_type == "code" and any(o.get("output_type") == "error" for o in c.outputs))
    print("notebook written:", NB, "| code cells:", count, "| cells with errors:", errs)


if __name__ == "__main__":
    run_cells()
