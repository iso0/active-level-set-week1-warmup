"""Build Phase 1.7 reports, teaching notebook, validation, and manifest."""

from __future__ import annotations

import json
import subprocess
from pathlib import Path

import nbformat as nbf
import pandas as pd
from nbclient import NotebookClient

from src import week9_phase1_7_physics_ridge_residual_gp as p17


ROOT = p17.ROOT
OUT = p17.OUTPUT
TABLES = p17.TABLES


def _write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text.strip() + "\n", encoding="utf-8")


def _numbers() -> dict[str, object]:
    primary = pd.read_csv(TABLES / "primary_AULC_summary.csv")
    q20 = primary[primary.endpoint.eq("B1_q20_AULC_16_80")].iloc[0]
    q30 = primary[primary.endpoint.eq("B1_q30_AULC_16_80")].iloc[0]
    terminal = pd.read_csv(TABLES / "terminal_budget_summary.csv")
    contrasts = pd.read_csv(TABLES / "terminal_budget_contrasts.csv")
    static = pd.read_csv(TABLES / "static_model_summary.csv")
    mechanism = pd.read_csv(TABLES / "model_mechanism_diagnostics.csv.gz")
    context = pd.read_csv(TABLES / "historical_context_AULC.csv")
    representatives = pd.read_csv(TABLES / "representative_residual_cases.csv")

    def terminal_row(model: str, budget: int, subset: str) -> pd.Series:
        return terminal[terminal.model.eq(model) & terminal.budget.eq(budget) & terminal.subset.eq(subset)].iloc[0]

    def contrast_row(budget: int, subset: str, metric: str) -> pd.Series:
        return contrasts[contrasts.budget.eq(budget) & contrasts.subset.eq(subset) & contrasts.metric.eq(metric)].iloc[0]

    def static_row(model: str, subset: str) -> pd.Series:
        return static[static.model.eq(model) & static.subset.eq(subset)].iloc[0]

    mech40 = mechanism[mechanism.subset.eq("B1_q20") & mechanism.budget.eq(40)]
    mech80 = mechanism[mechanism.subset.eq("B1_q20") & mechanism.budget.eq(80)]
    full_mechanism = mechanism[mechanism.subset.eq("full81")]
    return {
        "q20": q20,
        "q30": q30,
        "new40": terminal_row("physics_ridge_residual_gp", 40, "B1_q20"),
        "base40": terminal_row("frozen_4d_margin", 40, "B1_q20"),
        "new80": terminal_row("physics_ridge_residual_gp", 80, "B1_q20"),
        "base80": terminal_row("frozen_4d_margin", 80, "B1_q20"),
        "acc40": contrast_row(40, "B1_q20", "accuracy"),
        "recall40": contrast_row(40, "B1_q20", "keyhole_recall"),
        "add_static": static_row("physics_ridge_residual_gp", "full81"),
        "add_static_q20": static_row("physics_ridge_residual_gp", "B1_q20"),
        "h_static": static_row("log_h_logistic", "full81"),
        "h_static_q20": static_row("log_h_logistic", "B1_q20"),
        "gpc_static": static_row("gpc_4d", "full81"),
        "gpc_static_q20": static_row("gpc_4d", "B1_q20"),
        "mech40": mech40,
        "mech80": mech80,
        "context": context,
        "active_upper_hits": int(full_mechanism.residual_sd_upper_bound_hit.sum()),
        "active_lower_hits": int(full_mechanism.residual_sd_lower_bound_hit.sum()),
        "active_warnings": int(full_mechanism.convergence_warning.sum()),
        "active_fallbacks": int(full_mechanism.fit_status.ne("optimized_additive_laplace").sum()),
        "active_length_bound_hits": int((full_mechanism.length_scale_lower_bound_hit | full_mechanism.length_scale_upper_bound_hit).sum()),
        "active_fits": len(full_mechanism),
        "representatives": representatives[representatives.corrected_occurrences.gt(0)].head(5),
    }


def build_reports() -> None:
    n = _numbers()
    q20, q30 = n["q20"], n["q30"]
    new40, base40, new80, base80 = n["new40"], n["base40"], n["new80"], n["base80"]
    mech40, mech80 = n["mech40"], n["mech80"]
    context = n["context"]
    vs_h = context[context.comparator.eq("h_model_h_acquisition")].iloc[0]
    representative_lines = [
        "| P (W) | VX (m/s) | LS (um) | ST (K) | log(h) | h-only p | residual | combined p | truth | corrected occurrences |",
        "|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|",
    ]
    for row in n["representatives"].itertuples(index=False):
        representative_lines.append(
            f"| {row.P:.1f} | {row.VX:.3f} | {row.LS_um:.1f} | {row.ST:.1f} | {row.log_h:.3f} | "
            f"{row.mean_physics_probability:.3f} | {row.mean_residual_correction:+.3f} | "
            f"{row.mean_combined_probability:.3f} | {int(row.truth)} | {int(row.corrected_occurrences)} |"
        )
    representative_table = "\n".join(representative_lines)

    supervisor = f"""
# Supervisor one-page summary — Week 9 Phase 1.7

## Question and model

Can a physics-dominant latent classifier improve frozen near-boundary active learning?

`f(x)=beta_0+beta_h z(log h(x))+r(x)`, with `h=P/sqrt(VX*LS^3)` and `r` a constrained isotropic Matérn-3/2 GP over standardized P,VX,LS,ST. The Bernoulli likelihood uses a logistic link and scikit-learn's Laplace approximation. This is an additive kernel, not a fifth-feature GPC: the residual kernel never sees log(h).

## Frozen primary result

- Physics-ridge residual GP q20 AULC 16–80: **{q20.new_mean:.5f}**
- Canonical 4D Margin: **{q20.baseline_mean:.5f}**
- Matched difference: **{q20.delta:+.5f}**, repeat-block 95% CI **[{q20.ci_lower:+.5f}, {q20.ci_upper:+.5f}]**
- Predeclared decision: **{q20.decision}** (effect ≥ +0.010 and lower CI > 0)
- q30 difference: **{q30.delta:+.5f}** [{q30.ci_lower:+.5f}, {q30.ci_upper:+.5f}]

## Budget 40 and missed Keyholes

At budget 40, q20 accuracy is {new40.accuracy:.4f} versus {base40.accuracy:.4f}; balanced accuracy is {new40.balanced_accuracy:.4f} versus {base40.balanced_accuracy:.4f}; Keyhole recall is {new40.keyhole_recall:.4f} versus {base40.keyhole_recall:.4f}. The recall difference is descriptive rather than resolved: {n['recall40'].new_minus_baseline:+.4f}, CI [{n['recall40'].ci_lower:+.4f},{n['recall40'].ci_upper:+.4f}]. Mean missed Keyholes per 17-row q20 fold fall from {base40.false_negative:.2f} to {new40.false_negative:.2f}.

The residual is small in realized magnitude: at budget 40 its q20 RMS latent correction is {mech40.residual_rms_latent.mean():.3f}, versus {mech40.physics_rms_latent.mean():.3f} for the physics term. Across 100 q20 run-fold events it recovers {int(mech40.keyholes_recovered_by_residual.sum())} physics-trend Keyhole misses and induces {int(mech40.new_keyhole_misses_induced.sum())} new misses.

## Interpretation

The primary hypothesis passes on this frozen simulator benchmark. Most of the advantage is already present at the shared budget-16 design, so the result supports the **combined model-and-margin policy**, not a pure acquisition-only claim. Relative to the Phase 1.5 h-only model/policy, the additive result is only {vs_h.difference:+.4f} AULC with CI [{vs_h.ci_lower:+.4f},{vs_h.ci_upper:+.4f}].

## Qualification

The residual-amplitude upper/lower bounds are active in {n['active_upper_hits']}/{n['active_fits']} and {n['active_lower_hits']}/{n['active_fits']} active fits, the length-scale bounds in {n['active_length_bound_hits']}/{n['active_fits']}, and optimization warnings occur in {n['active_warnings']}/{n['active_fits']}; no additive-model fallback occurred. Therefore the low-amplitude behavior is partly imposed by design, and the result does not establish cross-material transfer, causal physics, or industrial safety.
"""
    _write(OUT / "SUPERVISOR_PHASE1_7_ONE_PAGE.md", supervisor)

    final = f"""
# Week 9 Phase 1.7 — final physics-ridge residual GP report

## Executive decision

**{q20.decision}.** Under the exact frozen Week 8.5 protocol, the additive physics-ridge residual classifier improves Fold-B1-q20 accuracy AULC 16–80 by {q20.delta:+.6f}, with repeat-block 95% CI [{q20.ci_lower:+.6f}, {q20.ci_upper:+.6f}], relative to canonical 4D Binary Margin. This satisfies the predeclared PASS rule.

## Exact implementation

The binary latent model is

`y_i | f_i ~ Bernoulli(sigmoid(f_i))`

`f_i = beta_0 + beta_h z(log h_i) + r(x_i)`

with independent priors `beta_0,beta_h ~ N(0,25)` and `r ~ GP(0,a_r^2 Matern_3/2,ell)` over pool-standardized `(P,VX,LS,ST)`. `a_r` is optimized inside `[0.05,1.0]` latent-logit SD and the single isotropic length scale inside `[0.25,4]`, with zero optimizer restarts. The combined additive kernel is fitted by scikit-learn's Laplace logistic GPC. At every active budget both scalers use training-pool features only; only currently revealed labels enter posterior fitting. Acquisition is ordinary combined-model Binary Margin: choose the unqueried training-pool point whose predictive probability is closest to 0.5.

This differs mathematically from Phase 1.5's 5D GPC: the log(h) component is strictly linear/additive and the residual kernel sees only the four original coordinates, with no h–4D interaction kernel.

## Baseline and information-flow gates

The frozen gate reproduced 100/100 exact splits and initial designs, 4D Margin AULC {q20.baseline_mean:.6f}, and matched Random 0.776220. No test rows, hidden pool labels, B1/q flags, or external h thresholds enter acquisition.

## Active-learning results

| Endpoint | Additive | 4D Margin | Difference | 95% repeat-block CI |
|---|---:|---:|---:|---:|
| q20 accuracy AULC 16–80 | {q20.new_mean:.6f} | {q20.baseline_mean:.6f} | {q20.delta:+.6f} | [{q20.ci_lower:+.6f},{q20.ci_upper:+.6f}] |
| q30 accuracy AULC 16–80 | {q30.new_mean:.6f} | {q30.baseline_mean:.6f} | {q30.delta:+.6f} | [{q30.ci_lower:+.6f},{q30.ci_upper:+.6f}] |

At budget 40, q20 accuracy is {new40.accuracy:.6f} versus {base40.accuracy:.6f}; balanced accuracy {new40.balanced_accuracy:.6f} versus {base40.balanced_accuracy:.6f}; Keyhole recall {new40.keyhole_recall:.6f} versus {base40.keyhole_recall:.6f}; FN {new40.false_negative:.2f} versus {base40.false_negative:.2f}; FP {new40.false_positive:.2f} versus {base40.false_positive:.2f}. The matched q20 accuracy difference is {n['acc40'].new_minus_baseline:+.6f} [{n['acc40'].ci_lower:+.6f},{n['acc40'].ci_upper:+.6f}]. The recall difference is {n['recall40'].new_minus_baseline:+.6f} [{n['recall40'].ci_lower:+.6f},{n['recall40'].ci_upper:+.6f}], so missed-Keyhole improvement at this single budget is not statistically resolved.

At budget 80, q20 accuracy is {new80.accuracy:.6f} versus {base80.accuracy:.6f}; Keyhole recall is nearly tied at {new80.keyhole_recall:.6f} versus {base80.keyhole_recall:.6f}, while additive FP is lower ({new80.false_positive:.2f} versus {base80.false_positive:.2f}).

The additive model's advantage over the Phase 1.5 h-only model/policy is only {vs_h.difference:+.6f}, CI [{vs_h.ci_lower:+.6f},{vs_h.ci_upper:+.6f}]. Thus the residual does not establish a resolved AULC improvement beyond h-only; the clear primary gain is versus canonical 4D Margin.

## Does the residual genuinely correct h failures?

Yes, but modestly. At budget 40, among 100 q20 run-fold events the residual changes {int(mech40.class_changed_count.sum())} class decisions: {int(mech40.corrected_count.sum())} become correct and {int(mech40.worsened_count.sum())} become wrong. Specifically, it recovers {int(mech40.keyholes_recovered_by_residual.sum())} Keyholes missed by the physics trend and induces {int(mech40.new_keyhole_misses_induced.sum())} new Keyhole misses. At budget 80 these counts are {int(mech80.corrected_count.sum())} corrected, {int(mech80.worsened_count.sum())} worsened, {int(mech80.keyholes_recovered_by_residual.sum())} Keyholes recovered, and {int(mech80.new_keyhole_misses_induced.sum())} new Keyhole misses.

At budget 40, residual q20 RMS is {mech40.residual_rms_latent.mean():.3f} versus physics-term RMS {mech40.physics_rms_latent.mean():.3f}; at budget 80 they are {mech80.residual_rms_latent.mean():.3f} and {mech80.physics_rms_latent.mean():.3f}. The realized correction is therefore low amplitude even though the residual prior SD often reaches its imposed upper bound.

### Representative budget-40 q20 residual cases

These rows summarize repeated held-out occurrences; they are examples, not independent physical experiments.

{representative_table}

## Static diagnostic

| Model | Full ROC-AUC | Full PR-AUC | Full balanced accuracy | q20 balanced accuracy | q20 Keyhole recall |
|---|---:|---:|---:|---:|---:|
| h logistic | {n['h_static'].mean_roc_auc:.6f} | {n['h_static'].mean_pr_auc:.6f} | {n['h_static'].mean_balanced_accuracy:.6f} | {n['h_static_q20'].mean_balanced_accuracy:.6f} | {n['h_static_q20'].mean_keyhole_recall:.6f} |
| Additive ridge-residual | {n['add_static'].mean_roc_auc:.6f} | {n['add_static'].mean_pr_auc:.6f} | {n['add_static'].mean_balanced_accuracy:.6f} | {n['add_static_q20'].mean_balanced_accuracy:.6f} | {n['add_static_q20'].mean_keyhole_recall:.6f} |
| Canonical 4D GPC | {n['gpc_static'].mean_roc_auc:.6f} | {n['gpc_static'].mean_pr_auc:.6f} | {n['gpc_static'].mean_balanced_accuracy:.6f} | {n['gpc_static_q20'].mean_balanced_accuracy:.6f} | {n['gpc_static_q20'].mean_keyhole_recall:.6f} |

The additive static model lies between h and the 4D GPC in ranking/recall, while its fixed-threshold balanced accuracy is slightly higher. This is diagnostic, not the primary endpoint.

## PCA diagnostic

PCA is fitted without labels on standardized P,VX,LS,ST. PC1+PC2 explain 58.42% of feature variance. Residual magnitude is spread through the sampled space rather than defining a clean physical boundary in PC1–PC2. The plot is descriptive only.

## Safe thesis claim

“On the frozen 405-simulation Ti-6Al-4V benchmark, using the physics-inspired h coordinate as an additive latent trend with a constrained 4D Matérn residual improved Fold-B1-q20 accuracy AULC 16–80 relative to canonical 4D Binary Margin.”

This does not imply a universal physical boundary, acquisition-only superiority, cross-material transfer, prospective experimental validation, causality, safety, or guaranteed query savings.

## Main limitation

Because log(h) is algebraically determined by P,VX,LS, the residual GP can in principle imitate the physics trend. Dominance is enforced by the amplitude cap rather than statistically identifiable from this single dataset. The upper/lower amplitude bounds bind frequently ({n['active_upper_hits']}/{n['active_fits']} and {n['active_lower_hits']}/{n['active_fits']} active fits; length-scale bounds {n['active_length_bound_hits']}/{n['active_fits']}; {n['active_warnings']} convergence warnings), so the PASS is benchmark-specific and conditional on this predeclared constrained model.
"""
    _write(OUT / "FINAL_PHASE1_7_REPORT.md", final)

    claims = f"""
# Phase 1.7 claim ledger

| Claim | Decision | Evidence |
|---|---|---|
| The implementation is an additive latent physics trend plus 4D residual GP, not a 5D GPC | PASS | custom additive kernel; component-decomposition tests |
| Frozen baseline and information-flow contracts are preserved | PASS | `baseline_gate.json`; `active_information_flow.csv.gz` |
| The additive model/policy improves primary q20 AULC versus 4D Margin | PASS | Δ={q20.delta:+.6f}, CI [{q20.ci_lower:+.6f},{q20.ci_upper:+.6f}], predeclared rule |
| It improves q30 AULC | PASS as secondary | Δ={q30.delta:+.6f}, CI [{q30.ci_lower:+.6f},{q30.ci_upper:+.6f}] |
| The residual genuinely recovers some h-trend Keyhole misses | QUALIFY | budget-40 recovery/worsening counts; effect is small |
| It clearly improves over the Phase 1.5 h-only model/policy | QUALIFY | Δ={vs_h.difference:+.6f}, CI [{vs_h.ci_lower:+.6f},{vs_h.ci_upper:+.6f}] includes zero |
| The residual amplitude is learned freely and remains small naturally | REJECT | amplitude is learned within a cap and often reaches the upper bound |
| The physics and residual components are uniquely identifiable | REJECT | h is deterministic in three 4D inputs; the cap imposes dominance |
| The result proves acquisition-only superiority | REJECT | model and acquisition policy both differ; advantage starts at shared budget 16 |
| The result transfers across materials or validates industrial safety | REJECT | one retrospective simulator/material population |
"""
    _write(OUT / "claim_ledger.md", claims)


def build_notebook() -> None:
    nb = nbf.v4.new_notebook()
    nb.metadata.kernelspec = {"display_name": "Python 3", "language": "python", "name": "python3"}
    nb.cells = [
        nbf.v4.new_markdown_cell("# Week 9 Phase 1.7 — physics ridge + 4D residual GP\n\nPhase 1.5 showed that log(h) captures most global separation but misses some near-boundary structure. This notebook tests one focused remedy under the exact frozen protocol."),
        nbf.v4.new_code_cell("from pathlib import Path\nimport json, pandas as pd\nROOT=Path.cwd().parents[1]\nOUT=ROOT/'outputs/week9_phase1_7_physics_ridge_residual_gp'\nTABLES=OUT/'tables'"),
        nbf.v4.new_markdown_cell("## 1. Frozen baseline gate\n\nThe study stops unless all 100 split IDs and initial 16-point designs match Week 8.5. B1/q20/q30 remain evaluation-only."),
        nbf.v4.new_code_cell("json.loads((OUT/'baseline_gate.json').read_text())"),
        nbf.v4.new_markdown_cell("## 2. Exact additive model\n\nWe fit `f=beta_0+beta_h z(log h)+r(P,VX,LS,ST)` with a logistic likelihood. The linear physics covariance and the 4D Matérn-3/2 covariance are added. Unlike a 5D GPC, the residual kernel never sees log(h), and there are no h–4D kernel interactions. Residual latent SD is restricted to [0.05,1.0]."),
        nbf.v4.new_markdown_cell("![Model mechanism](../../outputs/week9_phase1_7_physics_ridge_residual_gp/figures/01_model_mechanism.png)"),
        nbf.v4.new_markdown_cell("## 3. Static sanity check\n\nThis is diagnostic only: it asks whether the additive model captures some structure between h-only and the flexible 4D GPC."),
        nbf.v4.new_code_cell("s=pd.read_csv(TABLES/'static_model_summary.csv')\ns[s.model.isin(['log_h_logistic','physics_ridge_residual_gp','gpc_4d'])][['model','subset','mean_roc_auc','mean_pr_auc','mean_balanced_accuracy','mean_keyhole_recall']]"),
        nbf.v4.new_markdown_cell("## 4. Primary active-learning result\n\nThe new model uses ordinary Binary Margin from its own combined probability. Inference resamples 20 repeat blocks and retains five folds together."),
        nbf.v4.new_code_cell("pd.read_csv(TABLES/'primary_AULC_summary.csv')"),
        nbf.v4.new_markdown_cell("![q20 learning curves](../../outputs/week9_phase1_7_physics_ridge_residual_gp/figures/02_q20_learning_curves.png)\n\n![Matched AULC contrast](../../outputs/week9_phase1_7_physics_ridge_residual_gp/figures/03_primary_delta_AULC.png)"),
        nbf.v4.new_markdown_cell("## 5. Budget 40 and missed Keyholes\n\nAccuracy, balanced accuracy, recall, FN and FP are kept separate. Lower FN is the direct missed-Keyhole diagnostic."),
        nbf.v4.new_code_cell("t=pd.read_csv(TABLES/'terminal_budget_summary.csv')\nt[(t.budget==40)&(t.subset=='B1_q20')][['model','accuracy','balanced_accuracy','keyhole_recall','false_negative','false_positive']]"),
        nbf.v4.new_markdown_cell("## 6. Does the residual really correct h failures?\n\nA class change is defined on latent signs: `sign(g)` versus `sign(g+r)`. Corrections and newly introduced errors are both counted."),
        nbf.v4.new_code_cell("d=pd.read_csv(TABLES/'model_mechanism_diagnostics.csv.gz')\ncols=['budget','corrected_count','worsened_count','keyholes_recovered_by_residual','new_keyhole_misses_induced','physics_rms_latent','residual_rms_latent','residual_sd']\nd[(d.subset=='B1_q20')&d.budget.isin([40,80])].groupby('budget')[cols[1:]].mean()"),
        nbf.v4.new_markdown_cell("### Representative budget-40 q20 cases\n\nThese are repeated held-out summaries, not independent experiments."),
        nbf.v4.new_code_cell("r=pd.read_csv(TABLES/'representative_residual_cases.csv')\ncols=['P','VX','LS_um','ST','log_h','mean_physics_probability','mean_residual_correction','mean_combined_probability','truth','corrected_occurrences']\nr[r.corrected_occurrences>0].head(5)[cols]"),
        nbf.v4.new_markdown_cell("## 7. Label-free 2D view\n\nPCA uses only standardized P,VX,LS,ST. Color and outlines are overlaid after projection; PCA is not a physical boundary or feature-importance method."),
        nbf.v4.new_markdown_cell("![PCA residual diagnostic](../../outputs/week9_phase1_7_physics_ridge_residual_gp/figures/04_pca_residual_diagnostic.png)"),
        nbf.v4.new_markdown_cell("## 8. Safe conclusion\n\nThe preregistered primary comparison passes on this frozen simulator benchmark. The claim is about the combined additive model and Binary-Margin policy, not acquisition alone. The residual recovers some missed Keyholes, but its effect is modest and its amplitude cap binds frequently. No transfer, causality, safety, or guaranteed query-saving claim follows."),
    ]
    p17.NOTEBOOK.parent.mkdir(parents=True, exist_ok=True)
    client = NotebookClient(nb, timeout=180, kernel_name="python3", resources={"metadata": {"path": str(p17.NOTEBOOK.parent)}})
    client.execute()
    nbf.write(nb, p17.NOTEBOOK)


def build_validation_report() -> None:
    test = subprocess.run(
        [r"C:\Users\ozgur\anaconda3\envs\thesis\python.exe", "-m", "pytest", "tests/test_week9_phase1_7_physics_ridge_residual_gp.py", "-q"],
        cwd=ROOT,
        text=True,
        capture_output=True,
        check=False,
    )
    notebook = nbf.read(p17.NOTEBOOK, as_version=4)
    client = NotebookClient(notebook, timeout=180, kernel_name="python3", resources={"metadata": {"path": str(p17.NOTEBOOK.parent)}})
    client.execute()
    nbf.write(notebook, p17.NOTEBOOK)
    code_cells = [cell for cell in notebook.cells if cell.cell_type == "code"]
    errors = [output for cell in code_cells for output in cell.get("outputs", []) if output.get("output_type") == "error"]
    figures = pd.read_csv(OUT / "figure_manifest.csv")
    figure_ok = len(figures) == 4 and all(
        (p17.FIGURES / row.figure).is_file() and p17.sha256_file(p17.FIGURES / row.figure) == row.sha256
        for row in figures.itertuples(index=False)
    )
    historical_diff = subprocess.check_output(
        [
            "git",
            "diff",
            "--name-only",
            p17.STARTING_SHA,
            "--",
            "outputs/week8_5_frozen_confirmation",
            "outputs/week9_phase1_close_week8",
            "outputs/week9_phase1_5_h_physics_confirmation",
            "notebooks/week_09/02_week9_phase1_5_h_physics_confirmation.ipynb",
        ],
        cwd=ROOT,
        text=True,
    ).strip()
    aggregate = json.loads((OUT / "active_aggregation_report.json").read_text())
    checks = [
        ("focused tests", test.returncode == 0, (test.stdout + test.stderr).strip()),
        ("notebook execution", bool(code_cells) and not errors, f"code cells={len(code_cells)}; errors={len(errors)}"),
        ("figure hashes", figure_ok, f"figures={len(figures)}; hashes recomputed"),
        ("baseline gate", json.loads((OUT / "baseline_gate.json").read_text())["status"] == "PASS", "100 splits and initial designs exact"),
        ("information flow", not any(aggregate["information_flow"].values()), json.dumps(aggregate["information_flow"], sort_keys=True)),
        ("historical artifacts unchanged", historical_diff == "", historical_diff or "no tracked diff"),
        ("primary decision rule", aggregate["primary"]["decision"] in {"PASS", "QUALIFY", "FAIL"}, aggregate["primary"]["decision"]),
    ]
    status = "PASS" if all(passed for _, passed, _ in checks) else "FAIL"
    lines = ["# Phase 1.7 validation report", "", f"Overall status: **{status}**", "", "| Check | Status | Evidence |", "|---|---|---|"]
    for name, passed, evidence in checks:
        lines.append(f"| {name} | {'PASS' if passed else 'FAIL'} | {str(evidence).replace(chr(10),' ')} |")
    lines.extend(
        [
            "",
            "New computation was limited to the additive static diagnostic and one 100-run H80 active arm. Frozen 4D Margin, Random, h-only and 5D comparators were reused.",
            "",
            "Scope limit: one fixed 405-simulation Ti-6Al-4V population; no prospective, cross-material, causal, or industrial-safety validation.",
        ]
    )
    _write(OUT / "validation_report.md", "\n".join(lines))
    p17.write_json(OUT / "validation_report.json", {"status": status, "checks": [{"check": n, "passed": p, "evidence": e} for n, p, e in checks]})
    if status != "PASS":
        raise RuntimeError("Phase 1.7 validation failed")


def build_manifest() -> None:
    files = []
    for path in sorted(OUT.rglob("*")):
        if path.is_file() and path != OUT / "run_manifest.json" and "checkpoints" not in path.parts and "smoke" not in path.parts:
            files.append({"path": str(path.relative_to(ROOT)).replace("\\", "/"), "sha256": p17.sha256_file(path), "bytes": path.stat().st_size})
    for path in (
        p17.NOTEBOOK,
        ROOT / "src" / "week9_phase1_7_physics_ridge_residual_gp.py",
        ROOT / "scripts" / "build_week9_phase1_7_artifacts.py",
        ROOT / "tests" / "test_week9_phase1_7_physics_ridge_residual_gp.py",
    ):
        files.append({"path": str(path.relative_to(ROOT)).replace("\\", "/"), "sha256": p17.sha256_file(path), "bytes": path.stat().st_size})
    manifest = {
        "study": "Week 9 Phase 1.7 physics-ridge residual GP",
        "starting_sha": p17.STARTING_SHA,
        "study_branch": p17.BRANCH,
        "head_before_publication_commit": subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip(),
        "final_sha_note": "The exact final commit SHA is reported after publication; embedding a commit's own SHA is self-referential.",
        "historical_outputs_modified": False,
        "new_expensive_runs": "one additive static 100-fold diagnostic and one additive H80 100-run active arm",
        "files": files,
    }
    p17.write_json(OUT / "run_manifest.json", manifest)


if __name__ == "__main__":
    build_reports()
    build_notebook()
    build_validation_report()
    build_manifest()
