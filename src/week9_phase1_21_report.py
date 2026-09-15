"""Week 9 Phase 1.21 — final report and final-policy freeze, generated from frozen artifacts only."""
from __future__ import annotations

import datetime
import hashlib
import json
from pathlib import Path

import pandas as pd

from src import week9_phase1_21_analysis as ana
from src import week9_phase1_21_simplification_replication as rep

OUT = rep.OUTPUT
PHASE120 = OUT.parent / "week9_phase1_20_acquisition_search"
A, B, CCM, CCM8 = rep.CANDIDATE_A, rep.CANDIDATE_B, "cov_then_misfit_B40", "early8__cov_then_misfit_B40"
NAME = {rep.CONTROL: "M3 margin", A: "A: coverage -> margin", B: "B: 8 maximin + coverage -> margin",
        CCM: "old CCM (reference)", CCM8: "old early8 + CCM (reference)"}


def ci(r: dict, d: int = 4) -> str:
    return f"{r['mean']:+.{d}f} [{r['ci_low']:+.{d}f}, {r['ci_high']:+.{d}f}]"


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def table(header: list[str], rows: list[list]) -> list[str]:
    return ["| " + " | ".join(header) + " |", "|" + "---|" * len(header)] + ["| " + " | ".join(map(str, r)) + " |" for r in rows]


def freeze_final_policy(res: dict) -> dict:
    path = OUT / "FINAL_POLICY_FREEZE.json"
    if path.is_file():
        return json.loads(path.read_text(encoding="utf-8"))
    src = Path(rep.__file__).parent
    payload = {
        "frozen_at_utc": datetime.datetime.now(datetime.timezone.utc).isoformat(),
        "basis": "Phase 1.21 pre-registered replication on repeats 61-120 (REPLICATION_RESULT.json); no further tuning",
        "final_policy": {
            "name": B, "role": "recommended protocol (largest replicated effect; the simplest rule, non-inferior to its CCM version)",
            "seed": "first 8 points of the frozen seeded maximin order, extended along that order only until both classes are queried",
            "until_B40": "inside the log-h band estimated from queried labels only, padded by max(0.05, 0.25 x width): "
                         "argmax rank(1 - 2|p - 0.5|) + rank(standardised-x distance to the nearest queried point); plain margin if the band is empty",
            "from_B40": "plain M3 probability margin",
            "parameters": {"k_seed": 8, "pad_fraction": rep.PAD_FRACTION, "pad_floor": 0.05, "switch_budget": rep.SWITCH_BUDGET,
                           "uncertainty_weight": rep.UNCERTAINTY_WEIGHT, "coordinates": "standardised original 4D x (scaler fit on the training pool)"},
        },
        "pure_acquisition_companion": {"name": A, "role": "same rule with the frozen 16-point seed; isolates the acquisition effect "
                                                         "from the change of initial design"},
        "control": "M3 probability margin with the frozen 16-point seed",
        "evaluator": "M3 (frozen physics logistic mean on log h + ARD Matern-3/2 GP discrepancy), refit at every budget",
        "replicated_effects_vs_margin": {p: {t["window"]: [t["mean"], t["ci_low"], t["ci_high"]]
                                             for t in res["primary_tests"] if t["policy"] == p} for p in (A, B)},
        "code_sha256": {n: sha(src / n) for n in ("week9_phase1_20_acquisition_search.py", "week9_phase1_20_early_start.py",
                                                  "week9_phase1_21_simplification_replication.py",
                                                  "week9_phase1_13_fixed_physics_ard_discrepancy.py",
                                                  "week9_phase1_11_fixed_mean_discrepancy_gp.py")},
        "external_blind_test": "possible from now on; requires the user's explicit approval; the external pool has not been opened, "
                               "read or computed on, and its own protocol (endpoints, adaptation of B1 subsets to that pool) must be "
                               "pre-registered before any label of it is read",
    }
    path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    return payload


def main() -> None:
    protocol_path = OUT / "PHASE1_21_PREREGISTERED_PROTOCOL.json"
    protocol = json.loads(protocol_path.read_text(encoding="utf-8"))
    res = json.loads((OUT / "REPLICATION_RESULT.json").read_text(encoding="utf-8"))
    audit = json.loads((OUT / "REPEAT_USAGE_AUDIT.json").read_text(encoding="utf-8"))
    inv = json.loads((OUT / "invariance_audit.json").read_text(encoding="utf-8"))
    ref = json.loads((OUT / "all_label_reference.json").read_text(encoding="utf-8"))
    prefix = json.loads((OUT / "shared_prefix_check.json").read_text(encoding="utf-8"))
    mech = pd.read_csv(OUT / "mechanism_summary.csv").set_index("policy")
    final = freeze_final_policy(res)

    tests = {(t["policy"], t["window"]): t for t in res["primary_tests"]}
    v, mv, sec = res["verdicts"], res["misfit_verdict"], res["secondary"]
    comp = {(c["candidate"], c["window"]): c for c in res["misfit_question"]}
    blocks, runs = res["replication"]["repeat_blocks"], res["replication"]["outer_cv_runs_per_policy"]
    ref_q20 = ref["by_subset"]["B1_q20"]["accuracy"]
    metrics = {p: ana.load_metrics(p) for p in (rep.CONTROL, A, B, *rep.REFERENCES)}

    def headroom(policy, window):
        t = tests[(policy, window)]
        room = ref_q20 - t["margin_AULC"]
        return room, t["mean"] / room

    def fpfn(policy, lo, hi):
        m = metrics[policy]
        m = m[(m.subset == "B1_q20") & (m.budget >= lo) & (m.budget <= hi)]
        return m.false_positive.mean(), m.false_negative.mean()

    t80a, t40a, t80b, t40b = tests[(A, "16-80")], tests[(A, "16-40")], tests[(B, "16-80")], tests[(B, "16-40")]
    c80a, c4180a, c80b = comp[(A, "16-80")], comp[(A, "41-80")], comp[(B, "16-80")]
    saved = {p: {s["margin_budget"]: s for s in sec[p]["simulations_saved"]} for p in (A, B)}
    share_a = t80a["mean"] / sec[CCM]["vs margin AULC 16-80"]["mean"]
    q20 = {p: metrics[p][metrics[p].subset == "B1_q20"].groupby("budget").accuracy.mean() for p in (rep.CONTROL, A, B)}
    b80 = {p: float(c.loc[80]) for p, c in q20.items()}
    dip = float(q20[A].loc[19] - q20[rep.CONTROL].loc[19])

    L = ["# Week 9 Phase 1.21 — simplification and clean replication", ""]
    L += ["## Verdict", "",
          "**The improvement is an early boundary-coverage effect, and it replicated on untouched partitions.**", "",
          f"- Both simplified rules beat M3 margin on both pre-registered windows (all four Holm-adjusted p <= "
          f"{max(t['holm_p'] for t in res['primary_tests']):.4f}, all CIs above zero, guardrails met): "
          f"A REPLICATED = {v[A]['REPLICATED']}, B REPLICATED = {v[B]['REPLICATED']}.",
          f"- With the early start (Candidate B) the late misfit component is unnecessary: B minus old early8+CCM on 16-80 = "
          f"{ci(c80b)}, non-inferior at the frozen margin 0.0010 (pre-registered verdict `{mv[B]}`). "
          "This is outcome A of the Phase 1.21 brief.",
          f"- With the frozen seed (Candidate A) the simple rule keeps all of CCM's 16-40 gain (identical queries up to B40 in "
          f"{prefix[A]['first40_identical_to_reference']}/{prefix[A]['runs']} runs) and {100 * share_a:.0f}% of its 16-80 gain. "
          f"The remainder, A minus CCM = {ci(c80a)} on 16-80 (sign-flip p {c80a['signflip_p']:.3f}), is neither shown non-inferior "
          f"at the 0.0010 margin nor significant (pre-registered verdict `{mv[A]}`). "
          "This is outcome B of the brief: the necessary part is the early coverage; the late misfit component adds at most about "
          "0.001 AULC with the frozen seed, which this replication cannot resolve.", "",
          f"Data: repeats {res['replication']['repeats'][0]}-{res['replication']['repeats'][1]} of the frozen split generator, "
          f"{blocks} repeat blocks, {runs} outer cross-validation runs per policy. These are **untouched internal replication "
          "partitions** of the same 405-simulation population. They are not 300 independent simulations, not new simulations "
          "and not external data. Runs share simulations, which is why every test uses the repeat block as its unit.", ""]

    L += ["## 1. Summary", ""]
    bullets = [
        f"Candidate A vs margin: AULC 16-80 {ci(t80a)}, AULC 16-40 {ci(t40a)}; {t80a['positive_blocks']}/{blocks} and "
        f"{t40a['positive_blocks']}/{blocks} blocks positive.",
        f"Candidate B vs margin: AULC 16-80 {ci(t80b)}, AULC 16-40 {ci(t40b)}; {t80b['positive_blocks']}/{blocks} and "
        f"{t40b['positive_blocks']}/{blocks} blocks positive.",
        f"The effect sizes agree with the earlier phases: CCM vs margin was +0.0023 / +0.0055 on repeats 11-60 and is "
        f"{sec[CCM]['vs margin AULC 16-80']['mean']:+.4f} / {sec[CCM]['vs margin AULC 16-40']['mean']:+.4f} here; "
        f"Candidate A (screened as sched_bmm_B40) was +0.0022 / +0.0067 on development repeats 1-10.",
        f"Misfit component: B minus early8+CCM {ci(c80b)} (non-inferior); A minus CCM {ci(c80a)} (inconclusive; the gap sits in "
        f"41-80: {ci(c4180a)}).",
        f"Sample efficiency (mean curves, descriptive): margin's B40 q20 accuracy ({saved[A][40]['margin_q20_accuracy']:.4f}) is "
        f"reached at B{saved[A][40]['candidate_first_budget']} by A and B{saved[B][40]['candidate_first_budget']} by B, i.e. "
        f"{saved[A][40]['simulations_saved']} and {saved[B][40]['simulations_saved']} fewer simulations.",
        f"By B80 the rules converge: full81 accuracy change {sec[A]['B80 full81 accuracy change']:+.4f} (A) and "
        f"{sec[B]['B80 full81 accuracy change']:+.4f} (B); A's final 80 queried simulations equal margin's in "
        f"{prefix['A_final80_set_identical_to_margin']}/300 runs. Coverage changes the order of the boundary queries, not the final set.",
        f"Relative to the empirical all-label M3 reference on these partitions (q20 accuracy {ref_q20:.4f}), B's gain uses "
        f"{100 * headroom(B, '16-80')[1]:.0f}% of the observed 16-80 headroom ({headroom(B, '16-80')[0]:.4f}) and A's "
        f"{100 * headroom(A, '16-80')[1]:.0f}%.",
        f"Repeats 61-120 were verified untouched: {sum(r['files_scanned'] for r in audit['roots'].values()):,} files in "
        f"{len(audit['roots'])} locations plus {audit['git']['refs_audited']} git refs and the stash; highest repeat ever used = "
        f"{audit['repeats_used_anywhere'][1]}. Leakage audit: {inv['states_audited']} states, {inv['mismatches']} changes when "
        "every unqueried label and depth was scrambled.",
    ]
    L += [f"- {b}" for b in bullets] + [""]

    L += ["## 2. Pre-registration", "",
          f"`PHASE1_21_PREREGISTERED_PROTOCOL.json`, frozen {protocol['frozen_at_utc']} (sha256 {sha(protocol_path)[:16]}), "
          f"before any replication run (replication checkpoints existing at freeze: "
          f"{protocol['confirmation_checkpoints_existing_at_freeze']}). The first replication checkpoint was written at "
          "19:05:03 UTC. The protocol fixes the hypothesis, one control, two candidates, two descriptive references, every "
          "parameter, the repeat range, the endpoints, the estimators, Holm over 4 tests, guardrails, the replication rule, the "
          "non-inferiority margins, the numerical environment and the sha256 of all code involved. The analysis re-reads the "
          "protocol and refuses to run if its constants differ.", ""]

    L += ["## 3. Untouched repeat audit", ""]
    L += table(["location", "files scanned", "files with run ids", "repeats found", "files > 20", "files > 60"],
               [[t, f"{r['files_scanned']:,}", f"{r['files_with_run_ids']:,}", r["repeats_found"],
                 r["files_with_repeat_above_20"], r["files_with_repeat_above_60"]] for t, r in audit["roots"].items()])
    errors = sum(len(r["read_errors"]) for r in audit["roots"].values())
    L += ["", f"Git ({audit['git']['repository']}): {audit['git']['refs_audited']} refs and {audit['git']['stash_commits_audited']} "
          f"stash commits; file names with repeat >= 21: {len(audit['git']['file_names_with_repeat_ge_21'])}; text files with "
          f"repeat >= 21: {len(audit['git']['text_files_with_repeat_ge_21'])}; the only explicit `build_splits(repeats=...)` call "
          f"is the synthetic-data smoke-test fixture: {audit['git']['build_splits_calls_with_explicit_repeats']}.",
          f"Read errors: {errors} (joblib's own test fixtures inside `.venv` that are not gzip despite the extension, and two "
          "Office `~$` lock files).",
          "Repeats 1-20: frozen Week 8.5 splits, used by every earlier phase; Phase 1.20 developed on 1-10 and confirmed on "
          "11-60. Repeats 21-60: used only by that Phase 1.20 confirmation. Repeats 61-120: never used before this phase.", ""]

    L += ["## 4. Replication results (pre-registered tests)", ""]
    L += table(["rule", "window", "margin AULC", "rule AULC", "difference [95% CI]", "blocks positive", "sign-flip p", "Holm p"],
               [[NAME[p], w, f"{tests[(p, w)]['margin_AULC']:.4f}", f"{tests[(p, w)]['candidate_AULC']:.4f}", ci(tests[(p, w)]),
                 f"{tests[(p, w)]['positive_blocks']}/{blocks}", f"{tests[(p, w)]['signflip_p']:.4f}", f"{tests[(p, w)]['holm_p']:.4f}"]
                for p in (A, B) for w in ("16-80", "16-40")])
    L += [""]
    L += table(["rule", "B40 q20 Keyhole recall change (>= -0.03)", "B80 full81 accuracy change (>= -0.01)", "REPLICATED"],
               [[NAME[p], f"{v[p]['guardrails']['B40_q20_KH_recall_change']:+.4f}",
                 f"{v[p]['guardrails']['B80_full81_accuracy_change']:+.4f}", v[p]["REPLICATED"]] for p in (A, B)])
    L += ["", "Descriptive references against margin on the same partitions:", ""]
    L += table(["reference", "AULC 16-80", "AULC 16-40"],
               [[NAME[p], ci(sec[p]["vs margin AULC 16-80"]), ci(sec[p]["vs margin AULC 16-40"])] for p in rep.REFERENCES])
    L += [""]

    L += ["## 5. Is the late misfit component needed?", ""]
    L += table(["comparison", "window", "difference [95% CI]", "sign-flip p", "non-inferiority margin", "non-inferior"],
               [[f"{NAME[c['candidate']]} minus {NAME[c['reference']]}", c["window"], ci(c), f"{c['signflip_p']:.3f}",
                 c["noninferiority_margin"] if c["noninferiority_margin"] is not None else "-",
                 c["noninferior"] if c["noninferior"] is not None else "-"] for c in res["misfit_question"]])
    L += ["", f"16-40 is exactly zero by construction: each candidate and its CCM reference share the first 40 queries in "
          f"{prefix[A]['first40_identical_to_reference']}/300 (A) and {prefix[B]['first40_identical_to_reference']}/300 (B) runs "
          "(`shared_prefix_check.json`). The informative comparison is 16-80, driven by 41-80.",
          f"Pre-registered verdicts: A `{mv[A]}`, B `{mv[B]}`. The late component changes plain margin's choice in "
          f"{100 * mech.loc[CCM, 'differs_from_margin_B40_79']:.0f}% of late steps, yet CCM's final 80-point set still overlaps "
          f"margin's by Jaccard {mech.loc[CCM, 'jaccard_vs_margin_B80']:.2f}; its effect on accuracy is small.", ""]

    L += ["## 6. Learning curves and paired differences", "",
          "`figures/01_learning_curves.png` — mean q20 accuracy by budget for margin, the simple rule and old CCM "
          "(left: frozen seed; right: early start). `figures/02_paired_differences.png` — per-budget differences with 95% "
          "repeat-block bands, and simple minus old CCM.", "",
          f"What the curves show: the gain is built before B40. With the frozen seed the coverage rule first costs a little "
          f"(B19: {dip:+.4f}) and overtakes margin from B20; with the early start the active steps begin before B16, so the "
          f"curve is ahead from B16. After B40 all curves converge: B80 q20 accuracy {b80[rep.CONTROL]:.4f} (margin), "
          f"{b80[A]:.4f} (A), {b80[B]:.4f} (B).", ""]

    L += ["## 7. Secondary endpoints (difference vs margin, 95% CI)", ""]
    keys = ["AULC 41-80 q20 accuracy", "q30 accuracy AULC 16-80", "q20 balanced accuracy AULC 16-80",
            "q20 Keyhole recall AULC 16-80", "full81 accuracy AULC 16-80"]
    order = (A, B, CCM, CCM8)
    L += table(["endpoint", *[NAME[p] for p in order]],
               [[k, *[ci(sec[p][k]) for p in order]] for k in keys]
               + [[k, *[f"{sec[p][k]:+.4f}" for p in order]] for k in ("B40 q20 Keyhole recall change", "B80 full81 accuracy change")])

    def saved_cell(policy, budget):
        s = {x["margin_budget"]: x for x in sec[policy]["simulations_saved"]}[budget]
        if s["candidate_first_budget"] is None:
            return "not reached"
        return f"B{s['candidate_first_budget']} ({s['simulations_saved']}, {s['percent_fewer']}%)"

    L += ["", "## 8. Simulations saved (mean curves, descriptive)", ""]
    L += table(["margin budget", "margin q20 accuracy", *[f"{NAME[p]}: first budget reaching it (saved, % fewer)" for p in order]],
               [[f"B{b}", f"{saved[A][b]['margin_q20_accuracy']:.4f}", *[saved_cell(p, b) for p in order]]
                for b in ana.SAVED_LEVEL_BUDGETS])
    L += ["", "A single crossing of two mean curves is noisy (see B60), so these numbers illustrate the AULC result; they are "
          "not a separate test.", ""]

    L += ["## 9. Mechanism (post-hoc, explanatory only)", "",
          "None of these quantities enters the pre-registered verdict. `figures/03_mechanism.png`.", ""]
    rows = []
    for lo, hi in ((16, 40), (41, 80)):
        for p in (rep.CONTROL, A, B):
            fp, fn = fpfn(p, lo, hi)
            rows.append([f"{lo}-{hi}", NAME[p], f"{fp:.3f}", f"{fn:.3f}"])
    rows.append(["all 324 labels", "empirical all-label M3 reference", f"{ref['by_subset']['B1_q20']['false_positive']:.3f}",
                 f"{ref['by_subset']['B1_q20']['false_negative']:.3f}"])
    L += table(["budgets", "rule", "mean q20 false positives per run", "mean q20 false negatives per run"], rows)
    fp_m, fn_m = fpfn(rep.CONTROL, 16, 40)
    fp_a, fn_a = fpfn(A, 16, 40)
    fp_b, fn_b = fpfn(B, 16, 40)
    L += ["", f"In the evaluated regime, false negatives remained approximately stable (about 1.7-1.8 per run from B20 to B80, "
          f"and {ref['by_subset']['B1_q20']['false_negative']:.2f} even with all 324 labels) while most observed learning gains "
          f"came from reducing false positives. Over B16-40, compared with margin, A has {fp_m - fp_a:.3f} fewer false positives "
          f"and {fn_m - fn_a:.3f} fewer false negatives per run; B has {fp_m - fp_b:.3f} and {fn_m - fn_b:.3f}.", ""]
    mcols = [("separable_B16", "runs still separable in log h, B16"), ("separable_B20", "same, B20"), ("separable_B24", "same, B24"),
             ("nn_distance_B24", "mean nearest-neighbour distance of queried points, B24"), ("nn_distance_B40", "same, B40"),
             ("chosen_in_band_B16_39", "B16-39 queries inside the estimated band"),
             ("differs_from_margin_B16_39", "B16-39 steps choosing a different row than margin would"),
             ("differs_from_margin_B40_79", "B40-79 steps choosing a different row than margin would"),
             ("jaccard_vs_margin_B40", "query-set Jaccard with margin's own path, B40"), ("jaccard_vs_margin_B80", "same, B80")]
    mo = (rep.CONTROL, A, CCM, B, CCM8)
    L += table(["quantity", *[NAME[p] for p in mo]], [[lab, *[f"{mech.loc[p, c]:.3f}" for p in mo]] for c, lab in mcols])
    L += ["", f"Reading: margin keeps querying where the two classes are already bracketed, so "
          f"{100 * mech.loc[rep.CONTROL, 'separable_B16']:.0f}% of the frozen-seed runs are still perfectly separable in log h at "
          f"B16 and {100 * mech.loc[rep.CONTROL, 'separable_B20']:.0f}% at B20. The coverage rule spreads queries along the "
          "label-estimated band (larger nearest-neighbour distances at B24/B40, flatter position histogram). This breaks "
          f"separability sooner ({100 * mech.loc[A, 'separable_B20']:.0f}% at B20) and removes early false positives. Starting "
          f"after 8 maximin points gets the same effect even earlier ({100 * mech.loc[B, 'separable_B16']:.0f}% separable at B16).", ""]

    L += ["## 10. Leakage / invariance audit", "",
          f"`invariance_audit.json`, status {inv['status']}: {inv['states_audited']} development states (repeats 1-10 only) "
          f"covering {inv['by_phase']}. Every unqueried label and depth was replaced by random values; M3 probabilities and the "
          f"chosen row were identical in every state (mismatches {inv['mismatches']}). Static check that the policy code reads "
          f"no unmasked array: {inv['static_check_no_unmasked_access_in_policy_code']}. Policies receive only masked label/depth "
          "arrays, test rows are never candidates, and B1 distances are computed for evaluation only.", "",
          "Other gates: the extended split generator reproduces the frozen 100 runs and the 300 runs of Phase 1.20 bit-identically "
          "(`gate_splits.json`). The runner reproduced 10 of 11 Phase 1.20 trajectories bit-identically. The 11th came from a "
          "multi-threaded smoke test that diverged at a near-tie, and it was reproduced exactly under multi-threaded BLAS "
          "(`gate_runner_equivalence_addendum.json`). Every replication run used single-thread BLAS, as frozen.", ""]

    ha, hb = headroom(A, "16-80"), headroom(B, "16-80")
    L += ["## 11. What we can claim in the thesis", "",
          f"1. On this 405-simulation population, with M3 as the evaluator, a two-phase acquisition rule — until B40, uncertainty "
          f"plus coverage inside the log-h band estimated from queried labels; from B40, plain margin — improves Fold-B1-q20 "
          f"accuracy AULC over M3 margin. The gain is {t80a['mean']:+.4f} (16-80) and {t40a['mean']:+.4f} (16-40) with the frozen "
          f"seed, and {t80b['mean']:+.4f} / {t40b['mean']:+.4f} with an 8-point maximin start. This was found in development "
          "(repeats 1-10), confirmed internally (repeats 11-60, CCM form) and replicated under pre-registration on 60 "
          "previously unused repeat blocks (61-120).",
          "2. The improvement is an early boundary-coverage effect: it is built before B40, and the late misfit-avoidance "
          "component is not needed with the early start (non-inferior).",
          f"3. Descriptively, margin's B40 accuracy is reached {saved[A][40]['simulations_saved']}-{saved[B][40]['simulations_saved']} "
          "simulations earlier.",
          f"4. The gain costs nothing at the end: B80 full81 accuracy is unchanged ({sec[A]['B80 full81 accuracy change']:+.4f} A, "
          f"{sec[B]['B80 full81 accuracy change']:+.4f} B) and B40 q20 Keyhole recall stays within the guardrail "
          f"({sec[A]['B40 q20 Keyhole recall change']:+.4f} A, {sec[B]['B40 q20 Keyhole recall change']:+.4f} B).",
          f"5. Improvement relative to the empirical all-label M3 reference ({ref_q20:.4f} on these partitions) leaves only "
          f"{ha[0]:.4f} observed headroom on 16-80; B's gain covers {100 * hb[1]:.0f}% of it and A's {100 * ha[1]:.0f}%.",
          "6. The acquisition is label-blind as audited: scrambling all unqueried labels and depths changes nothing.", ""]
    L += ["## 12. What we cannot claim", "",
          "1. External validity. Repeats 61-120 are untouched internal replication partitions of the same 405 simulations, not "
          "new simulations, not another simulator setting and not experimental data.",
          "2. That 300 runs are 300 independent experiments. They share simulations; the effective unit is the repeat block, "
          "and even blocks are not independent samples from a wider population.",
          "3. That Candidate B's gain is pure acquisition. B also changes the initial design (8 instead of 16 seed points). "
          "The pure acquisition effect is Candidate A's.",
          "4. That the misfit component is useless in general. With the frozen seed its contribution is unresolved "
          f"({ci(c80a)} on 16-80).",
          "5. Any gain in final accuracy at B80, or a Keyhole-recall gain (not significant).",
          f"6. A theoretical ceiling or a maximum possible improvement. At B80 all three rules already match or slightly exceed "
          f"the empirical all-label reference (q20 accuracy {min(b80.values()):.4f}-{max(b80.values()):.4f} vs {ref_q20:.4f}).",
          "7. That the parameters (pad 0.25, switch B40, equal weights, 4D x) are optimal. They were never tuned in this phase.",
          "8. A causal mechanism. The separability, coverage and false-positive analyses are post-hoc explanations, not tested "
          "hypotheses.",
          "9. Anything about other evaluators (only M3 was used) or other boundary definitions (only Fold-B1 q20/q30 and full81).", ""]
    L += ["## 13. Five sentences for Ioan", "",
          "1. We simplified the Phase 1.20 acquisition rule: from B16 to B39 it queries points that are uncertain under M3 and "
          "far from already-queried points, restricted to the log-h band where queried Conduction and Keyhole labels meet; from "
          "B40 it is plain M3 margin.",
          "2. Before running anything we pre-registered the rule, parameters, endpoints and tests, and audited every copy of the "
          "project to confirm that outer-CV repeats 61-120 had never been used — fresh partitions of the same 405 simulations, "
          "not new data.",
          f"3. On these 60 repeat blocks the rule beat margin on Fold-B1-q20 accuracy AULC 16-80 by {t80a['mean']:+.4f} "
          f"(95% CI {t80a['ci_low']:+.4f} to {t80a['ci_high']:+.4f}) with the frozen seed and by {t80b['mean']:+.4f} "
          f"({t80b['ci_low']:+.4f} to {t80b['ci_high']:+.4f}) when active learning starts after 8 maximin points; all four "
          "Holm-adjusted p <= 0.0004, with no guardrail violations.",
          f"4. The gain is an early boundary-coverage effect: it is built before B40, reaches margin's B40 accuracy "
          f"{saved[A][40]['simulations_saved']}-{saved[B][40]['simulations_saved']} simulations earlier, and the late "
          "misfit-avoidance part of the earlier rule is unnecessary with the early start and adds at most about 0.001 AULC with "
          "the frozen seed.",
          "5. The rule is now frozen, and the next step would be a pre-registered blind test on a genuinely external simulation "
          "pool, which we have not opened.", ""]
    L += ["## 14. Final policy freeze and external blind test", "",
          f"`FINAL_POLICY_FREEZE.json` ({final['frozen_at_utc']}): final policy `{final['final_policy']['name']}`, with "
          f"`{final['pure_acquisition_companion']['name']}` as its pure-acquisition companion and M3 margin as control; code "
          "sha256 recorded. No external pool has been opened, read or computed on.", "",
          "## 15. Wording errata for Phase 1.20", "",
          "`PHASE1_20_WORDING_ERRATA.md`: \"ceiling\" becomes \"empirical all-label M3 reference\"; \"reducible-error budget\" "
          "becomes \"observed headroom\"; \"only false positives are reducible\" becomes the regime-specific statement; "
          "\"250 runs\" becomes \"250 outer cross-validation runs of the same 405 simulations\". Historical files unchanged.", "",
          "## Files", "",
          "`src/week9_phase1_21_*.py` (repeat_audit, repeat_audit_driver, simplification_replication, invariance_audit, freeze, "
          "analysis, figures, all_label_reference, report). Outputs in this folder: protocol, audit, gates, checkpoints/ (5 x 300), "
          "REPLICATION_RESULT.json, mechanism_*.csv, all_label_reference*.{json,csv}, shared_prefix_check.json, figures/.", ""]
    (OUT / "FINAL_PHASE1_21_REPORT.md").write_text("\n".join(L), encoding="utf-8")
    print("\n".join(L))


if __name__ == "__main__":
    main()
