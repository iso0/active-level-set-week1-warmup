"""Build the concise Phase 1.5 reports, notebook, and manifests from cached results."""

from __future__ import annotations

import json
import re
import subprocess
from pathlib import Path

import nbformat as nbf
import pandas as pd
from nbclient import NotebookClient

from src import week9_phase1_5_h_physics_confirmation as p15


ROOT = p15.ROOT
OUT = p15.OUTPUT


def _write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text.strip() + "\n", encoding="utf-8", newline="\n")


def _contrast(model: str, comparator: str, metric: str = "B1_q20_AULC_16_80") -> pd.Series:
    frame = pd.read_csv(OUT / "active_AULC_contrasts.csv")
    return frame[
        frame.model.eq(model) & frame.comparator.eq(comparator) & frame.metric.eq(metric)
    ].iloc[0]


def _static(model: str, subset: str = "full81") -> pd.Series:
    frame = pd.read_csv(OUT / "static_model_summary.csv")
    return frame[frame.model.eq(model) & frame.subset.eq(subset)].iloc[0]


def _kernel_bound_hit(kernel: str) -> bool:
    constant = re.search(r"([0-9.eE+-]+)\*\*2\s*\*\s*Matern", str(kernel))
    length = re.search(r"length_scale=([0-9.eE+-]+)", str(kernel))
    if not constant or not length:
        return False
    constant_base = float(constant.group(1))
    constant_value = constant_base**2
    length_value = float(length.group(1))
    c_low, c_high = p15.p6.KERNEL_CONSTANT_BOUNDS
    l_low, l_high = p15.p6.KERNEL_LENGTH_BOUNDS
    return bool(
        constant_base <= c_low**0.5 + 0.001
        or constant_base >= c_high**0.5 - 0.15
        or length_value <= l_low * 1.001
        or length_value >= l_high * 0.999
    )


def build_kernel_diagnostics() -> pd.DataFrame:
    rows = []
    static = pd.read_csv(OUT / "static_oof_predictions.csv.gz", usecols=["run_id", "model", "fit_status", "kernel"])
    static = static[static.model.str.startswith("gpc_")].drop_duplicates(["run_id", "model"])
    for model, group in static.groupby("model"):
        hits = group.kernel.map(_kernel_bound_hit)
        rows.append({"analysis": "static", "model": model, "unique_fits": len(group), "bound_hits": int(hits.sum()), "bound_hit_rate": float(hits.mean()), "fallback_fits": int((~group.fit_status.str.startswith("optimized")).sum())})
    active = pd.read_csv(OUT / "active_per_budget_metrics.csv.gz")
    active = active[active.kernel.notna() & active.kernel.ne("NA")].drop_duplicates(["run_id", "prediction_model", "budget"])
    for model, group in active.groupby("prediction_model"):
        hits = group.kernel.map(_kernel_bound_hit)
        rows.append({"analysis": "active_declared_checkpoint_evaluations", "model": model, "unique_fits": len(group), "bound_hits": int(hits.sum()), "bound_hit_rate": float(hits.mean()), "fallback_fits": int((~group.fit_status.str.startswith("optimized")).sum())})
    result = pd.DataFrame(rows)
    p15.write_csv(OUT / "gpc_kernel_bound_diagnostics.csv", result)
    return result


def build_reports() -> None:
    exponent = pd.read_csv(OUT / "empirical_exponent_summary.csv").set_index("exponent")
    zones = pd.read_csv(OUT / "screening_zone_summary.csv").set_index("zone")
    cal = json.loads((OUT / "calibration_summary.json").read_text(encoding="utf-8"))
    active = pd.read_csv(OUT / "active_path_metrics.csv")
    h_vs_margin = _contrast("h_model_h_acquisition", "frozen_4d_margin")
    h4_vs_margin = _contrast("gpc4_h_acquisition", "frozen_4d_margin")
    gpc5_vs_margin = _contrast("gpc5_margin", "frozen_4d_margin")
    assisted_vs_margin = _contrast("gpc4_assisted_product", "frozen_4d_margin")
    h_static, gpc4, gpc5 = _static("log_h_logistic"), _static("gpc_4d"), _static("gpc_5d_h_augmented")
    h_q20, gpc4_q20 = _static("log_h_logistic", "B1_q20"), _static("gpc_4d", "B1_q20")
    crossing = active.groupby("prediction_model").persistent_q20_0_80_observed.agg(["sum", "count"])
    kernel_diagnostics = build_kernel_diagnostics()
    h_cross = int(crossing.loc["h_model_h_acquisition", "sum"])
    h4_cross = int(crossing.loc["gpc4_h_acquisition", "sum"])

    report4 = f"""
# Phase 1.5 physics-informed active-learning audit

## Protocol and leakage status

The analysis imported the exact Week 8.5 split, initial-design, Fold-B1, AULC and persistent-crossing functions. The frozen baseline gate passed before new arms ran. All 100 outer runs were completed to H80; only the scientifically relevant `h_margin` arm was extended to H160. The 3000 saved Random continuations were reused.

The 19,200 H80 acquisition records state and the focused tests verify: candidates came only from the outer training pool; test rows, hidden unqueried labels and B1/B2/B3 were unavailable; no full-pool label threshold was fitted. Acquisition selectors accept only candidate indices and revealed-label model probabilities.

## Primary q20 AULC 16–80

| Model/policy | Mean AULC | Difference vs frozen 4D Margin | 95% repeat-block CI | Decision |
|---|---:|---:|---:|---|
| frozen 4D Margin | 0.81352 | — | — | reference |
| h query → h model | {h_vs_margin.model_mean:.5f} | {h_vs_margin.difference:+.5f} | [{h_vs_margin.ci_lower:+.5f}, {h_vs_margin.ci_upper:+.5f}] | improves this 1D model-policy pair |
| h query → 4D GPC | {h4_vs_margin.model_mean:.5f} | {h4_vs_margin.difference:+.5f} | [{h4_vs_margin.ci_lower:+.5f}, {h4_vs_margin.ci_upper:+.5f}] | worse 4D exploration |
| 5D GPC Margin | {gpc5_vs_margin.model_mean:.5f} | {gpc5_vs_margin.difference:+.5f} | [{gpc5_vs_margin.ci_lower:+.5f}, {gpc5_vs_margin.ci_upper:+.5f}] | no resolved improvement |
| 4D×h uncertainty | {assisted_vs_margin.model_mean:.5f} | {assisted_vs_margin.difference:+.5f} | [{assisted_vs_margin.ci_lower:+.5f}, {assisted_vs_margin.ci_upper:+.5f}] | worse than 4D Margin |

The key separation is therefore model versus acquisition policy. A strongly constrained 1D learner is sample-efficient on q20, but using its exact query sequence to train a 4D GPC loses {abs(h4_vs_margin.difference):.4f} AULC versus canonical 4D Margin. This is evidence that pure h querying under-explores residual 4D structure.

At budget 40, q20 accuracy was {active[active.prediction_model.eq('h_model_h_acquisition')].budget40_B1_q20_accuracy.mean():.4f} for the h model, {active[active.prediction_model.eq('gpc4_h_acquisition')].budget40_B1_q20_accuracy.mean():.4f} for a 4D GPC on the same h-selected labels, and 0.8171 for frozen 4D Margin.

By H160, stable q20 ≥0.80 was observed in {h_cross}/100 h-model paths and {h4_cross}/100 4D-GPC-on-h-query paths. Frozen 4D Margin reached it in 91/100 by H160. These censored rates do not support a universal “45 queries saved” headline.

## Verdict

- Physics-inspired `h` is useful as a low-dimensional **model prior**.
- Pure h acquisition does not improve learning of the full 4D boundary.
- Redundant 5D embedding is statistically unresolved versus 4D Margin and worsens static probability scores slightly.
- The untuned uncertainty product is inferior to canonical 4D Margin.
- No hidden-label Antigravity threshold was retained.
"""
    _write(ROOT / "reports" / "04_active_learning_audit.md", report4)

    final = f"""
# Week 9 Phase 1.5 — final forensic confirmation

## Executive decision

`h=P/sqrt(VX·LS^3)` is a legitimate physics-inspired coordinate because its process exponents match Gan et al.'s Keyhole-number scaling when `LS` is the Gaussian spot radius. Bare `h` is dimensional and is not the full Keyhole number. Empirically it compresses most global discrimination into one coordinate, but measurable residual 4D structure remains near Fold-B1. Canonical 4D Margin remains the best verified acquisition policy for learning that 4D structure.

## Answers to the requested questions

1. **Physically supported?** Yes, as the process-dependent part of a material-normalized scaling; not as a standalone dimensionless number.
2. **Exponent agreement real?** Consistency is strong: VX/P {exponent.loc['VX relative to P','estimate']:.3f} [{exponent.loc['VX relative to P','ci_lower']:.3f},{exponent.loc['VX relative to P','ci_upper']:.3f}], LS/P {exponent.loc['LS relative to P','estimate']:.3f} [{exponent.loc['LS relative to P','ci_lower']:.3f},{exponent.loc['LS relative to P','ci_upper']:.3f}]. It is not independent discovery or proof.
3. **Nearly sufficient globally?** Nearly, but not fully. `log(h)` ROC-AUC {h_static.mean_roc_auc:.4f} versus 4D GPC {gpc4.mean_roc_auc:.4f}; PR-AUC {h_static.mean_pr_auc:.4f} versus {gpc4.mean_pr_auc:.4f}.
4. **Near-boundary degradation?** On q20, h Keyhole recall {h_q20.mean_keyhole_recall:.3f} versus 4D GPC {gpc4_q20.mean_keyhole_recall:.3f}; the paired h-minus-4D interval excludes zero for recall.
5. **Does ST add anything?** The predeclared partial `h/(1933-ST)` sensitivity, using Gan et al. Supplementary Table 3, is worse than bare h in this 300–400 K domain. This does not establish universal ST irrelevance.
6. **Does h improve GPC?** No verified gain. 5D-minus-4D full ROC-AUC is {gpc5.mean_roc_auc-gpc4.mean_roc_auc:+.6f}; Brier is worse by {gpc5.mean_brier_score-gpc4.mean_brier_score:+.6f}.
7. **Does h improve acquisition?** No fixed-model acquisition improvement was shown. The composite h-only model/policy has q20 AULC {h_vs_margin.difference:+.4f} versus 4D Margin, but that comparison changes both model and acquisition and its advantage is already visible at the shared budget-16 design. The controlled fixed-4D comparison shows h queries significantly hurt the 4D GPC.
8. **Does pure h acquisition harm 4D exploration?** Yes: the same h-selected queries give the 4D GPC {h4_vs_margin.difference:+.4f} AULC versus 4D Margin, CI [{h4_vs_margin.ci_lower:+.4f},{h4_vs_margin.ci_upper:+.4f}].
9. **Physics ridge + residual?** Scientifically plausible because h captures dominant variation and the 4D model recovers some OOF ensemble errors, but per-repeat residual stability was not separately established. No additive GP was implemented; it remains a focused next-step prototype.
10. **Three-zone screening?** It survives as retrospective simulator-domain screening: low zone {int(zones.loc['low_p_lt_0.05','count'])} rows with one Keyhole (NPV {zones.loc['low_p_lt_0.05','negative_predictive_value']:.4f}); high zone {int(zones.loc['high_p_gt_0.95','count'])} with two Conduction (PPV {zones.loc['high_p_gt_0.95','positive_predictive_value']:.4f}). It is not a safety or CAM-approval rule.
11. **Antigravity correct:** physical exponent family, strong 1D global discrimination, interesting OOF screening potential, and the need to inspect physics-informed acquisition.
12. **Antigravity wrong/overstated:** LS as diameter, h as dimensionless, universal thresholds, same-data screening confidence, hidden-label threshold acquisition, and ~45-query headlines.
13. **Core slides:** theory/empirical exponent figure; static/boundary comparison; active q20 curves emphasizing h-model gain versus h-query→4D loss.
14. **Appendix only:** calibration bins/zones, residual maps, physical-score candidates, H160 censoring details, 5D and uncertainty-product negatives.
15. **Most promising Phase 2 method:** a preregistered additive physics ridge plus lower-amplitude 4D residual GP, compared directly with canonical 4D Margin. It is a proposal, not a Phase 1.5 result.

## Calibration and limitations

OOF Brier is {cal['OOF_Brier']:.4f}, ECE {cal['ECE']:.4f}, and MCE {cal['MCE']:.4f} using ten fixed equal-width bins. MCE is driven by a sparse worst bin, so it is not inconsistent with low weighted ECE. All inference describes one fixed 405-run Ti-6Al-4V simulator population and split stability; it is not prospective experimental, cross-alloy, causal, or safety validation.

All saved GPC fits optimized without fallback, but kernel-bound hits were non-negligible: 4D static {int(kernel_diagnostics[(kernel_diagnostics.analysis.eq('static')) & kernel_diagnostics.model.eq('gpc_4d')].bound_hits.iloc[0])}/100 and the full table is in `gpc_kernel_bound_diagnostics.csv`. This does not invalidate protocol-matched comparisons, but it qualifies GPC probability/calibration interpretation and motivates a future kernel-sensitivity check rather than stronger claims here.
"""
    _write(OUT / "FINAL_PHASE1_5_REPORT.md", final)

    supervisor = f"""
# Supervisor one-page summary — Week 9 Phase 1.5

## Question

Can the physics-inspired coordinate `h=P/sqrt(VX·LS^3)` explain the Conduction–Keyhole regime and improve active learning under the exact frozen Week 8.5 protocol?

## What is physically correct

Gan et al. use `Ke = eta P / [(Tl-T0) pi rho Cp sqrt(alpha V r0^3)]`; therefore h has the correct process exponents when `LS=r0`. Repository source code confirms LS is the Gaussian spot radius. Bare h has units `W s^(1/2) m^-2`, so it is not dimensionless and no universal cross-alloy threshold is claimed.

## Main results

- Empirical exponents are consistent with theory: VX/P {exponent.loc['VX relative to P','estimate']:.3f} and LS/P {exponent.loc['LS relative to P','estimate']:.3f}, with both theoretical values inside bootstrap intervals.
- Globally, log(h) is strong (ROC-AUC {h_static.mean_roc_auc:.4f}) but below 4D GPC ({gpc4.mean_roc_auc:.4f}), especially in PR-AUC and probability quality.
- At q20, h misses more Keyholes: recall {h_q20.mean_keyhole_recall:.3f} versus {gpc4_q20.mean_keyhole_recall:.3f} for 4D GPC.
- The 5D redundant GPC does not give a resolved static or active-learning improvement.
- All GPC fits optimized, but frequent constant-kernel upper-bound hits—especially for 4D GPC—qualify probability/calibration interpretation.
- q20 AULC: 4D Margin 0.81352; h query→h model {h_vs_margin.model_mean:.5f}; h query→4D GPC {h4_vs_margin.model_mean:.5f}; 5D Margin {gpc5_vs_margin.model_mean:.5f}; 4D×h uncertainty {assisted_vs_margin.model_mean:.5f}.

## Interpretation

The physics ridge is a useful low-dimensional inductive bias, but it is not a sufficient acquisition coordinate for learning the full 4D empirical boundary. The h-only model/policy composite is strong at low budget; however, this cannot isolate an acquisition benefit, and its query sequence makes a 4D GPC significantly worse than canonical 4D Margin. The honest conclusion is not “h saves 45 queries.” It is: **h captures the dominant global direction, while canonical 4D Margin remains the best verified policy for residual boundary structure.**

## Recommendation

Show figures 1, 4 and 6. If Phase 2 pursues this thread, test one clean additive `g(log h)+r(x)` GP against frozen 4D Margin; do not expand the acquisition zoo.
"""
    _write(OUT / "SUPERVISOR_PHASE1_5_ONE_PAGE.md", supervisor)

    ledger = """
# Phase 1.5 claim ledger

| Claim | Decision | Evidence and code path |
|---|---|---|
| h has genuine physical support | PASS | Gan Eq. 1/3; `reports/01_*`; `h_coordinates` |
| empirical exponents match theory | QUALIFY | `empirical_exponent_summary.csv`; both theory points lie inside marginal bootstrap CIs; consistency, not proof |
| h is dimensionless | REJECT | SI audit gives `W s^(1/2) m^-2`; full material normalization is missing |
| ST is irrelevant | REJECT | only partial correction in a narrow 300–400 K domain was tested; it did not help |
| h is sufficient over 4D | QUALIFY | high global AUC, but worse PR/Brier and q20 Keyhole recall than 4D GPC |
| three-zone screening is useful | QUALIFY | `screening_zone_summary.csv`; OOF retrospective simulator-domain only |
| one numerical h threshold transfers across alloys | REJECT | absorptivity/material constants and spot conventions are absent |
| h active learning saves about 45 queries | REJECT | exact persistent/censored protocol does not establish this headline |
| 5D GPC improves sample efficiency | REJECT | q20 AULC difference vs 4D Margin has a 95% CI crossing zero |
| pure 1D h acquisition plateaus | QUALIFY | H160 stable-target results remain censored and pure h querying underperforms for a 4D GPC |
| physics-based initial boundary clustering helps | REJECT | not tested; exact frozen 16-point initial design was preserved |
| additive physics-ridge modeling is promising | QUALIFY | residual structure motivates one prototype, but no additive model was fitted here |

Primary literature: Gan et al. 2021; Cunningham et al. 2019; King et al. 2014; Hann et al. 2010/2011. Numerical artifacts are under `outputs/week9_phase1_5_h_physics_confirmation/`; implementation is `src/week9_phase1_5_h_physics_confirmation.py`.
"""
    _write(OUT / "claim_ledger.md", ledger)


def build_notebook() -> None:
    nb = nbf.v4.new_notebook()
    nb["metadata"]["kernelspec"] = {"display_name": "Python 3", "language": "python", "name": "python3"}
    nb["cells"] = [
        nbf.v4.new_markdown_cell("# Week 9 Phase 1.5 — forensic confirmation of the physics-informed h coordinate\n\nThis notebook is a readable result tour. It consumes the frozen Phase 1.5 artifacts and does not rerun expensive active learning."),
        nbf.v4.new_markdown_cell("## 1. Definitions and question\n\nWe test $h=P/\\sqrt{VX\\,LS^3}$. Repository provenance fixes **LS as Gaussian spot radius** and **ST as substrate temperature**. Bare h is dimensional; Gan's full Keyhole number adds absorptivity and material/thermal normalization."),
        nbf.v4.new_code_cell("from pathlib import Path\nimport json, pandas as pd\nROOT = Path.cwd().parents[1]\nOUT = ROOT/'outputs'/'week9_phase1_5_h_physics_confirmation'\naudit=json.loads((OUT/'data_and_protocol_audit.json').read_text())\n{k:audit[k] for k in ['rows','keyhole','conduction','LS_definition','ST_definition','frozen_outer_runs']}"),
        nbf.v4.new_markdown_cell("## 2. Are the empirical exponents consistent with theory?\n\nCoefficient ratios are fitted on unstandardized log features, then assessed by bootstrap and split stability. The careful wording is *consistent with*, not *discovered the law*."),
        nbf.v4.new_code_cell("pd.read_csv(OUT/'empirical_exponent_summary.csv')"),
        nbf.v4.new_markdown_cell("![Theory versus empirical exponents](../../outputs/week9_phase1_5_h_physics_confirmation/figures/01_theory_vs_empirical_exponents.png)"),
        nbf.v4.new_markdown_cell("## 3. How much of the problem is one-dimensional?\n\nThe next table uses the exact 20×5 frozen grouped splits. Global ranking can be excellent while probability quality and boundary-specific recall still differ."),
        nbf.v4.new_code_cell("s=pd.read_csv(OUT/'static_model_summary.csv')\ns[s.model.isin(['log_h_logistic','logistic_M1','logistic_M3','gpc_4d','gpc_5d_h_augmented'])][['model','subset','mean_roc_auc','mean_pr_auc','mean_balanced_accuracy','mean_keyhole_recall','mean_brier_score']]"),
        nbf.v4.new_markdown_cell("![Boundary difficulty](../../outputs/week9_phase1_5_h_physics_confirmation/figures/04_boundary_difficulty.png)"),
        nbf.v4.new_markdown_cell("## 4. Does OOF screening survive?\n\nThe zones use predictions made while each simulation was held out. They describe retrospective simulator-domain screening, not a safety rule."),
        nbf.v4.new_code_cell("pd.read_csv(OUT/'screening_zone_summary.csv')"),
        nbf.v4.new_code_cell("json.loads((OUT/'calibration_summary.json').read_text()) | {'reliability':'shown in figure'}"),
        nbf.v4.new_markdown_cell("![OOF screening and calibration](../../outputs/week9_phase1_5_h_physics_confirmation/figures/02_logh_distribution_and_oof_calibration.png)"),
        nbf.v4.new_markdown_cell("## 5. Does h help active learning?\n\nAll acquisition models use only revealed labels. Fold-B1 and test labels are evaluation-only. The two evaluations separate *h-model quality* from *h-query policy quality for a fixed 4D GPC*. The h-only advantage is already visible at the shared budget-16 design, so it cannot be attributed purely to acquisition."),
        nbf.v4.new_code_cell("a=pd.read_csv(OUT/'active_AULC_contrasts.csv')\na[a.metric.eq('B1_q20_AULC_16_80')][['model','comparator','model_mean','comparator_mean','difference','ci_lower','ci_upper']]"),
        nbf.v4.new_markdown_cell("![Active-learning q20 curves](../../outputs/week9_phase1_5_h_physics_confirmation/figures/06_active_q20_learning_curves.png)"),
        nbf.v4.new_markdown_cell("## 6. Final interpretation\n\n- h is physically motivated and globally strong.\n- It is not dimensionless or universally thresholded.\n- Residual 4D structure matters near Fold-B1.\n- The h-only model/policy composite is strong at low budget, but this does not isolate an acquisition benefit; h-selected labels make a 4D GPC worse than 4D Margin.\n- The 5D embedding and uncertainty product do not beat canonical 4D Margin.\n- A single additive physics-ridge + 4D residual prototype is the focused next method worth testing."),
    ]
    p15.NOTEBOOK.parent.mkdir(parents=True, exist_ok=True)
    nbf.write(nb, p15.NOTEBOOK)
    client = NotebookClient(nb, timeout=180, kernel_name="python3", resources={"metadata": {"path": str(p15.NOTEBOOK.parent)}})
    client.execute()
    nbf.write(nb, p15.NOTEBOOK)


def build_manifest() -> None:
    files = []
    for base in (OUT, ROOT / "reports"):
        for path in sorted(base.rglob("*")):
            if path.is_file() and path != OUT / "run_manifest.json" and "checkpoints" not in path.parts and "smoke" not in path.parts:
                files.append({"path": str(path.relative_to(ROOT)).replace("\\", "/"), "sha256": p15.sha256_file(path), "bytes": path.stat().st_size})
    for path in (
        p15.NOTEBOOK,
        ROOT / "src" / "week9_phase1_5_h_physics_confirmation.py",
        ROOT / "scripts" / "build_week9_phase1_5_artifacts.py",
        ROOT / "tests" / "test_week9_phase1_5_h_physics_confirmation.py",
    ):
        files.append({"path": str(path.relative_to(ROOT)).replace("\\", "/"), "sha256": p15.sha256_file(path), "bytes": path.stat().st_size})
    manifest = {
        "study": "Week 9 Phase 1.5 h physics confirmation",
        "starting_branch": p15.STARTING_BRANCH,
        "starting_sha": p15.STARTING_SHA,
        "study_branch": p15.BRANCH,
        "head_before_publication_commit": subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip(),
        "final_sha_note": "The exact final commit SHA is reported after publication; embedding a commit's own SHA in that commit is self-referential.",
        "historical_outputs_modified": False,
        "files": files,
    }
    p15.write_json(OUT / "run_manifest.json", manifest)


def build_validation_report() -> None:
    test = subprocess.run(
        [r"C:\Users\ozgur\anaconda3\envs\thesis\python.exe", "-m", "pytest", "tests/test_week9_phase1_5_h_physics_confirmation.py", "-q"],
        cwd=ROOT,
        text=True,
        capture_output=True,
        check=False,
    )
    notebook = nbf.read(p15.NOTEBOOK, as_version=4)
    client = NotebookClient(notebook, timeout=180, kernel_name="python3", resources={"metadata": {"path": str(p15.NOTEBOOK.parent)}})
    client.execute()
    nbf.write(notebook, p15.NOTEBOOK)
    code_cells = [cell for cell in notebook.cells if cell.cell_type == "code"]
    notebook_ok = bool(code_cells) and all(cell.execution_count is not None for cell in code_cells)
    notebook_errors = [output for cell in code_cells for output in cell.get("outputs", []) if output.get("output_type") == "error"]
    historical_diff = subprocess.check_output(
        ["git", "diff", "--name-only", p15.STARTING_SHA, "--", "outputs/week8_5_frozen_confirmation", "outputs/week9_phase1_close_week8"],
        cwd=ROOT,
        text=True,
    ).strip()
    figures = pd.read_csv(OUT / "figure_manifest.csv")
    figure_hashes_ok = len(figures) == 8 and all(
        (OUT / "figures" / row.figure).is_file() and p15.sha256_file(OUT / "figures" / row.figure) == row.sha256
        for row in figures.itertuples(index=False)
    )
    active = json.loads((OUT / "active_aggregation_report.json").read_text(encoding="utf-8"))
    kernel = build_kernel_diagnostics()
    checks = [
        ("focused tests", test.returncode == 0, (test.stdout + test.stderr).strip()),
        ("notebook execution", notebook_ok and not notebook_errors, f"{len(code_cells)} code cells; errors={len(notebook_errors)}"),
        ("figure count and hashes", figure_hashes_ok, f"figures={len(figures)}; hashes recomputed"),
        ("active information flow", all(value is False for value in active["information_flow"].values()), json.dumps(active["information_flow"], sort_keys=True)),
        ("historical tracked outputs unchanged", historical_diff == "", historical_diff or "no tracked diff"),
        ("baseline reproduction", json.loads((OUT / "baseline_reproduction_gate.json").read_text())["status"] == "PASS", "numerical tolerance gate"),
        ("GPC fallbacks and bound diagnostics", int(kernel.fallback_fits.sum()) == 0, f"fallbacks={int(kernel.fallback_fits.sum())}; bound hits disclosed in gpc_kernel_bound_diagnostics.csv"),
    ]
    status = "PASS" if all(passed for _, passed, _ in checks) else "FAIL"
    lines = ["# Phase 1.5 validation report", "", f"Overall status: **{status}**", "", "| Check | Status | Evidence |", "|---|---|---|"]
    for name, passed, evidence in checks:
        lines.append(f"| {name} | {'PASS' if passed else 'FAIL'} | {evidence.replace(chr(10), ' ')} |")
    lines.extend(
        [
            "",
            "The frozen Week 8.5 and existing Week 9 Phase 1 directories were read-only inputs. The original dirty checkout was not edited; this study ran in its own worktree and branch.",
            "",
            "Scientific scope limits: fixed 405-run Ti-6Al-4V simulator population; repeated-split uncertainty rather than new-experiment uncertainty; no prospective, cross-alloy, causal, or manufacturing-safety validation.",
        ]
    )
    _write(OUT / "validation_report.md", "\n".join(lines))
    p15.write_json(
        OUT / "validation_report.json",
        {"status": status, "checks": [{"check": str(n), "passed": bool(p), "evidence": str(e)} for n, p, e in checks]},
    )
    if status != "PASS":
        raise RuntimeError("Phase 1.5 validation failed")


if __name__ == "__main__":
    build_reports()
    build_notebook()
    build_validation_report()
    build_manifest()
