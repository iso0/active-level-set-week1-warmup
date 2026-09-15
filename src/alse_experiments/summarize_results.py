"""Print the headline table from results/ and write it to results/SUMMARY.md.

One row per canonical decision artifact: the decision string, the key numbers
and the results-relative path. Files missing from results/ print as 'missing'.

    python experiments/summarize_results.py
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from alse.config import RESULTS_DIR  # noqa: E402

R1 = "real/R1_phase6_active_arms"
R2 = "real/R2_phase7_hybrids"
R3 = "real/R3_frozen_protocol"
R4 = "real/R4_h320_closure"
P1, P2 = "physics/P1_h_coordinate", "physics/P2_physics_ridge_residual"
P3, P4 = "physics/P3_model_path_decomposition", "physics/P4_physics_specificity"
P5 = "physics/P5_model_chain"
P6, P7 = "physics/P6_m3_margin_acquisition", "physics/P7_exact_gpc_sur"


def load(rel: str):
    """CSV as a DataFrame, JSON as a dict, or None when the file is not in results/."""
    path = RESULTS_DIR / rel
    if not path.is_file():
        return None
    return json.loads(path.read_text(encoding="utf-8")) if path.suffix == ".json" else pd.read_csv(path)


def ci(row, lo: str = "ci_lower", hi: str = "ci_upper") -> str:
    return f"[{row[lo]:+.6f}, {row[hi]:+.6f}]"


def first(frame: pd.DataFrame, **match) -> pd.Series:
    mask = pd.Series(True, index=frame.index)
    for column, value in match.items():
        mask &= frame[column] == value
    return frame[mask].iloc[0]


def headline_rows() -> list[dict]:
    rows: list[dict] = []

    def add(label: str, rel: str, render) -> None:
        data = load(rel)
        if data is None:
            rows.append({"phase": label, "decision": "missing", "key numbers": "", "file": rel})
            return
        decision, numbers = render(data)
        rows.append({"phase": label, "decision": str(decision), "key numbers": numbers, "file": rel})

    add("Phase 6 (R1) formulation", f"{R1}/phase6_final_decision.csv", lambda f: (
        f.iloc[0]["final_decision"],
        f"q20 error AULC Max minus Binary {f.iloc[0]['q20_aulc_max_minus_binary']:+.6f} "
        f"{ci(f.iloc[0], 'q20_paired_ci_low', 'q20_paired_ci_high')}; BA AULC "
        f"{f.iloc[0]['balanced_accuracy_aulc_max_minus_binary']:+.6f}; domain_robustness_pass "
        f"{f.iloc[0]['domain_robustness_pass']}"))
    add("Phase 7 (R2) hybrids", f"{R2}/phase7_final_decision.csv", lambda f: (
        f.iloc[0]["decision"],
        f"preregistered rule sha256 {str(f.iloc[0]['decision_rule_sha256'])[:8]}; hybrids passing: "
        f"{f.iloc[0]['hybrid_success_json']}"))
    scorecard = load(f"{R2}/phase7_method_scorecard.csv")
    if scorecard is not None:
        rows[-1]["key numbers"] += "; B1 q20 error AULC " + ", ".join(
            f"{m} {first(scorecard, method=m)['mean_B1_q20_aulc']:.4f}"
            for m in ("binary_uncertainty_repulsion", "hybrid_binary_gate20_max_depth_straddle", "hybrid_equal_rank_fusion",
                      "max_depth_straddle", "shared_random_binary_head"))
    ledger = load(f"{R3}/decision_ledger.csv")
    if ledger is None:
        rows.append({"phase": "Week 8.5 (R3) frozen protocol", "decision": "missing", "key numbers": "",
                     "file": f"{R3}/decision_ledger.csv"})
    else:
        for _, r in ledger.iterrows():
            numbers = "" if pd.isna(r["point_estimate"]) else (
                f"point {r['point_estimate']:.6f}; one-sided 95% lower {r['one_sided_95pct_lower_bound']:.6f}; "
                f"gate {r['pass_threshold']}; rho_random {r['rho_random']}; H={r['horizon']}")
            rows.append({"phase": f"Week 8.5 (R3) {r['claim']}", "decision": r["decision"], "key numbers": numbers,
                         "file": f"{R3}/decision_ledger.csv"})
    add("H=320 closure (R4) query saving", f"{R4}/query_saving_claim_decision.json", lambda d: (
        d["status"],
        f"matched categories {d['matched_category_counts']}; Random unresolved {d['random_unresolved']} "
        f"({d['random_unresolved_guaranteed_Q_gt_320']} guaranteed Q>320, {d['random_unresolved_tail_indeterminate']} indeterminate)"))
    add("Phase 1.5 (P1) h coordinate", f"{P1}/active_AULC_contrasts.csv", lambda f: (
        "-", "; ".join(
            f"{m} {r['model_mean']:.6f} ({r['difference']:+.6f} {ci(r)}, {r['repeat_blocks_positive']}/{r['repeat_blocks']})"
            for m in ("h_model_h_acquisition", "gpc4_h_acquisition", "gpc5_margin", "gpc4_assisted_product")
            for r in [first(f, model=m, comparator="frozen_4d_margin", metric="B1_q20_AULC_16_80")])
        + f"; frozen 4D margin {first(f, comparator='frozen_4d_margin')['comparator_mean']:.6f}"))
    add("Phase 1.7 (P2) physics ridge + residual", f"{P2}/primary_decision.json", lambda d: (
        d["decision"], f"{d['endpoint']} {d['new_mean']:.6f} vs {d['baseline_mean']:.6f}; delta {d['delta']:+.6f} "
        f"{ci(d)}; {d['positive_repeat_blocks']}/{d['repeat_blocks']} repeat blocks positive"))
    add("Phase 1.8 (P3) model vs path", f"{P3}/primary_decomposition.csv", lambda f: (
        f.iloc[0]["decision"], "; ".join(
            f"{e} {first(f, effect=e)['mean']:+.6f} {ci(first(f, effect=e))}" for e in ("TOTAL", "MODEL", "PATH"))))
    add("Phase 1.9 (P4) physics specificity", f"{P4}/primary_AULC_summary.csv", lambda f: (
        f.iloc[0]["decision"], "; ".join(
            f"{e} {first(f, estimand=e)['mean']:+.6f} [{first(f, estimand=e)['ci_low']:+.6f}, {first(f, estimand=e)['ci_high']:+.6f}]"
            for e in ("Y00", "G10", "Y10", "physics_minus_generic", "generic_minus_4D"))))
    for sub, label, primary in (("M2_fixed_mean", "Phase 1.11 (P5) M2 fixed mean", "M2-M0"),
                                ("G0_G4_kernels", "Phase 1.12 (P5) G0-G4 kernels", "G3-G0"),
                                ("M3_fixed_physics_ard", "Phase 1.13 (P5) M3 fixed physics + ARD", "M3-H")):
        manifest = load(f"{P5}/{sub}/run_manifest.json") or {}
        contrasts = load(f"{P5}/{sub}/paired_contrasts.csv")
        add(label, f"{P5}/{sub}/model_summary.csv", lambda f, m=manifest, c=contrasts, p=primary: (
            m.get("decision", "-"),
            "B1_q20 AULC " + ", ".join(f"{r['model']} {r['mean_AULC']:.6f}" for _, r in f[f["subset"] == "B1_q20"].iterrows())
            + ("" if c is None else "; " + p + " " + f"{first(c, contrast=p, subset='B1_q20')['mean_difference']:+.6f} "
               + ci(first(c, contrast=p, subset="B1_q20"))
               + f", {first(c, contrast=p, subset='B1_q20')['positive_repeat_blocks']}/20")))
    manifest = load(f"{P6}/run_manifest.json") or {}
    late = load(f"{P6}/early_late_contrasts.csv")
    add("Phase 1.14 (P6) M3-margin vs A0 replay", f"{P6}/paired_contrasts.csv", lambda f: (
        manifest.get("decision", "-"),
        f"P1-P0 B1_q20 {first(f, subset='B1_q20')['mean_difference']:+.6f} {ci(first(f, subset='B1_q20'))}, "
        f"{first(f, subset='B1_q20')['positive_repeat_blocks']}/20"
        + ("" if late is None else "; " + "; ".join(
            f"{r['region']} {r['mean_difference']:+.6f} {ci(r)}" for _, r in late.iterrows()))))
    aulc = load(f"{P7}/model_aulc_summary.csv")
    contrasts = load(f"{P7}/q20_primary_contrasts.csv")
    add("Phase 1.18B (P7) exact GPC-SUR", f"{P7}/primary_decision.json", lambda d: (
        d["decision"],
        ("" if aulc is None else "q20 AULC " + ", ".join(f"{r['model']} {r['mean_AULC']:.6f}" for _, r in aulc.iterrows()) + "; ")
        + ("" if contrasts is None else "; ".join(
            f"{r['contrast']} {r['mean_difference']:+.6f} {ci(r)}" for _, r in contrasts.iterrows()))))
    for name, rel in (("physics refit", f"{P7}/physics_refit_decision.json"),
                      ("sample efficiency", f"{P7}/sample_efficiency_decision.json")):
        add(f"Phase 1.18B (P7) {name}", rel, lambda d: (d["decision"], ""))
    return rows


def main() -> None:
    frame = pd.DataFrame(headline_rows())
    lines = ["# Headline results", "", "Regenerated by `python experiments/summarize_results.py` from `results/`.",
             "Paths are relative to `results/`; 'missing' marks files not curated yet.", "",
             "| Phase | Decision | Key numbers | File |", "|---|---|---|---|"]
    lines += [f"| {r['phase']} | {r['decision']} | {r['key numbers']} | `{r['file']}` |" for _, r in frame.iterrows()]
    text = "\n".join(lines) + "\n"
    (RESULTS_DIR / "SUMMARY.md").write_text(text, encoding="utf-8")
    print(text)
    print(f"wrote {RESULTS_DIR / 'SUMMARY.md'} ({len(frame)} rows)")


if __name__ == "__main__":
    main()
