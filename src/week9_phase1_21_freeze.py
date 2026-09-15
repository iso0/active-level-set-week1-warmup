"""Week 9 Phase 1.21 — aggregate the repeat audit and freeze the pre-registered protocol.

Refuses to write the protocol unless: every audit root has been scanned; no file or git object
anywhere contains a repeat in the replication range; both gates passed; and no replication
checkpoint exists yet.
"""
from __future__ import annotations

import datetime
import hashlib
import json
import subprocess
from pathlib import Path

from src import week9_phase1_21_analysis as ana
from src import week9_phase1_21_repeat_audit_driver as driver
from src import week9_phase1_21_simplification_replication as rep

OUT = rep.OUTPUT
AUDIT = OUT / "repeat_audit"
MAIN_REPO = Path(r"C:\Users\ozgur\Documents\thesis")


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def git_audit() -> dict:
    refs = subprocess.run(["git", "for-each-ref", "--format=%(objectname) %(refname:short)", "refs/heads", "refs/remotes"],
                          cwd=MAIN_REPO, capture_output=True, text=True, check=True).stdout.split("\n")
    refs = [r.split(" ", 1) for r in refs if r.strip()]
    stash = subprocess.run(["git", "stash", "list", "--format=%H %gs"], cwd=MAIN_REPO, capture_output=True,
                           text=True, check=True).stdout.split("\n")
    stash_commits = []
    for line in stash:
        if line.strip():
            commit = line.split(" ", 1)[0]
            parents = subprocess.run(["git", "rev-list", "--parents", "-n", "1", commit], cwd=MAIN_REPO,
                                     capture_output=True, text=True, check=True).stdout.split()
            stash_commits += parents
    objects = sorted({r[0] for r in refs} | set(stash_commits))
    pattern = r"w85__r(2[1-9]|[3-9][0-9]|[1-9][0-9][0-9])_f|outer_split\|repeat\|(2[1-9]|[3-9][0-9]|[1-9][0-9][0-9])"
    names_hits = []
    for obj in objects:
        names = subprocess.run(["git", "ls-tree", "-r", "--name-only", obj], cwd=MAIN_REPO, capture_output=True,
                               text=True, errors="ignore").stdout
        import re
        names_hits += [f"{obj[:10]}:{n}" for n in names.split("\n") if re.search(r"w85__r(2[1-9]|[3-9][0-9]|[1-9][0-9][0-9])_f", n)]
    content = subprocess.run(["git", "grep", "-I", "-l", "-E", pattern, *objects], cwd=MAIN_REPO,
                             capture_output=True, text=True, errors="ignore").stdout.split("\n")
    splits_calls = subprocess.run(["git", "grep", "-I", "-n", "-E", r"build_splits\([^)]*repeats\s*=", *objects],
                                  cwd=MAIN_REPO, capture_output=True, text=True, errors="ignore").stdout.split("\n")
    calls = sorted({line.split(":", 1)[1] for line in splits_calls if line.strip()})
    return {"repository": str(MAIN_REPO), "refs_audited": len(refs), "stash_commits_audited": len(stash_commits),
            "file_names_with_repeat_ge_21": names_hits, "text_files_with_repeat_ge_21": [c for c in content if c.strip()],
            "build_splits_calls_with_explicit_repeats": calls,
            "limitation": "git grep -I skips binary (compressed) blobs; compressed checkpoints are covered by file names "
                          "and by the working-tree scans"}


def main() -> None:
    scans = {}
    for tag in driver.ROOTS:
        path = AUDIT / f"scan_{tag}.json"
        rep.require(path.is_file(), f"audit root not scanned: {tag}")
        scans[tag] = json.loads(path.read_text(encoding="utf-8"))
    git = git_audit()
    used = sorted({r for s in scans.values() for r in s["repeats_found"]})
    replication = set(rep.REPLICATION_REPEATS)
    collisions = sorted(set(used) & replication)
    rep.require(not collisions, f"replication repeats already used somewhere: {collisions}")
    rep.require(not git["file_names_with_repeat_ge_21"] and not git["text_files_with_repeat_ge_21"],
                "git history mentions repeats >= 21; inspect before freezing")
    audit = {
        "question": "which outer-split repeat blocks of w85.build_splits were ever used by any design, screening, "
                    "tuning, confirmation, diagnostic or plot, anywhere on this machine",
        "method": "pattern match of run ids w85__rNN_fNN and seed keys outer_split|repeat|NN in file names, text, "
                  "gzip/zip/tar members, parquet string columns and raw bytes; git refs and stash via git grep",
        "roots": {tag: {"root": s["root"], "files_scanned": s["files_scanned"], "files_with_run_ids": s["files_with_run_ids"],
                        "repeats_found": [min(s["repeats_found"]), max(s["repeats_found"])] if s["repeats_found"] else None,
                        "files_with_repeat_above_20": len(s["files_with_repeat_above_20"]),
                        "files_with_repeat_above_60": len(s["files_with_repeat_above_60"]),
                        "read_errors": s["errors"]} for tag, s in scans.items()},
        "git": git,
        "repeats_used_anywhere": [min(used), max(used)] if used else None,
        "repeats_1_20": "frozen Week 8.5 splits: every phase from Week 8.5 through 1.19B, the R&D packages, Phases 1.10B and 1.20",
        "repeats_21_60": "Phase 1.20 confirmation only (margin, cov_then_misfit_B40, early8__cov_then_misfit_B40)",
        "repeats_61_120_found": collisions,
        "verdict": "repeats 61-120 are untouched internal replication partitions",
    }
    (OUT / "REPEAT_USAGE_AUDIT.json").write_text(json.dumps(audit, indent=2), encoding="utf-8")

    split_gate = json.loads((OUT / "gate_splits.json").read_text())
    equivalence = json.loads((OUT / "gate_runner_equivalence_addendum.json").read_text())
    rep.require(split_gate["status"] == "PASS", "split gate")
    rep.require(equivalence["resolution_status"].startswith("PASS"), "runner equivalence gate")
    existing = sorted(str(p.relative_to(OUT)) for p in rep.CHECKPOINTS.rglob("*.json.gz")) if rep.CHECKPOINTS.exists() else []
    rep.require(not existing, "replication checkpoints already exist")

    src = Path(rep.__file__).parent
    code = {name: sha(src / name) for name in (
        "week9_phase1_21_simplification_replication.py", "week9_phase1_21_analysis.py",
        "week9_phase1_20_acquisition_search.py", "week9_phase1_20_early_start.py",
        "week9_phase1_13_fixed_physics_ard_discrepancy.py", "week9_phase1_11_fixed_mean_discrepancy_gp.py",
        "week9_phase1_7_physics_ridge_residual_gp.py", "week8_5_frozen_sample_efficiency_confirmation.py")}
    protocol = {
        "phase": "Week 9 Phase 1.21 - simplification and clean replication",
        "frozen_at_utc": datetime.datetime.now(datetime.timezone.utc).isoformat(),
        "hypothesis": ("The replicated Phase 1.20 gain is an early boundary-coverage effect: coverage inside the queried-label "
                       "log-h band until B40 followed by plain M3 margin (Candidate A) improves on M3 margin as CCM did, and "
                       "does so again on partitions never used before; the same holds with an earlier active start "
                       "(Candidate B). The late misfit-avoidance component is not needed."),
        "no_search": "exactly one control and two candidates; no parameter is tuned; two descriptive references",
        "control": {"name": rep.CONTROL, "definition": "M3 probability margin, frozen 16-point maximin seed"},
        "candidates": {
            rep.CANDIDATE_A: {
                "seed": "frozen 16-point maximin design (w85.initial_design)",
                "B16_to_B39": "estimated log-h band from queried labels only ([lowest queried Keyhole, highest queried "
                              "Conduction], or the bracket while separable), padded by max(0.05, 0.25 x width); inside the "
                              "band choose argmax rank(1 - 2|p - 0.5|) + rank(standardised-x distance to nearest queried "
                              "point); plain margin if the band is empty",
                "B40_to_B79": "plain M3 probability margin (no misfit avoidance)",
                "object": "week9_phase1_20_acquisition_search.make_band_coverage('x', weight_unc=1.0, pad_fraction=0.25, "
                          "switch_budget=40)",
                "parameters": {"pad_fraction": rep.PAD_FRACTION, "pad_floor": 0.05, "switch_budget": rep.SWITCH_BUDGET,
                               "uncertainty_weight": rep.UNCERTAINTY_WEIGHT, "coordinates": "standardised original 4D x (P, VX, LS, ST), scaler fit on the outer training pool"},
                "provenance": "identical to Phase 1.20 CCM before B40 (50/50 development runs share the first 40 queries); "
                              "screened in Phase 1.20 development as sched_bmm_B40 (dev +0.0022 on 16-80, +0.0067 on 16-40); "
                              "never run on any confirmation repeat",
            },
            rep.CANDIDATE_B: {
                "seed": "first 8 points of the frozen maximin order; if they lack a class, extend along the SAME frozen order "
                        "until both classes are queried (week9_phase1_20_early_start.seed_prefix)",
                "then": "Candidate A's rule from the end of the seed (coverage below B40, plain margin from B40)",
                "metrics_from": "B16, identical budget grid to the control",
            },
        },
        "descriptive_references_not_candidates": {
            "cov_then_misfit_B40": "Phase 1.20 family-A finalist (CCM)",
            "early8__cov_then_misfit_B40": "Phase 1.20 family-B finalist",
            "role": "answer whether the late misfit component is needed; never selected, never Holm-counted",
        },
        "evaluator": "M3 exactly as Phase 1.13/1.14, refit on the queried prefix at every budget",
        "replication_data": {
            "repeats": [min(rep.REPLICATION_REPEATS), max(rep.REPLICATION_REPEATS)],
            "repeat_blocks": len(rep.REPLICATION_REPEATS),
            "outer_cv_runs_per_policy": 5 * len(rep.REPLICATION_REPEATS),
            "generator": "w85.build_splits(population, repeats=120, folds=5); first 100 specs bit-identical to the frozen "
                         "splits and first 300 to those used in Phase 1.20 (gate_splits.json)",
            "status": "untouched internal replication partitions: further outer cross-validation partitions of the same "
                      "405-simulation population, not new simulations and not external data",
            "audit": "REPEAT_USAGE_AUDIT.json",
            "power": "from Phase 1.20 confirmation variances only: 60 blocks give ~0.90 power for Candidate A on 16-40, "
                     "~0.72 on 16-80, ~1.00 for Candidate B (two-sided alpha 0.025)",
        },
        "endpoints": {
            "primary": "Fold-B1-q20 accuracy AULC 16-80",
            "early_sample_efficiency": "Fold-B1-q20 accuracy AULC 16-40",
            "secondary": ["AULC 41-80", "q30 accuracy AULC 16-80", "q20 balanced accuracy AULC 16-80",
                          "q20 Keyhole recall (AULC 16-80 and at B40)", "full81 accuracy (AULC 16-80 and at B80)",
                          "simulations saved at margin's accuracy at B24/B32/B40/B60 (mean curves, descriptive)"],
        },
        "inference": {
            "unit": "repeat block (mean of its 5 outer runs), paired against the control",
            "bootstrap": "10,000 repeat-block draws, percentile 95% CI",
            "permutation": "10,000 sign flips of repeat-block differences",
            "multiplicity": "Holm over {A, B} x {16-80, 16-40} = 4 tests",
            "consistency": "identical estimators to Phase 1.20 confirmation; new seed namespace phase1_21",
        },
        "decision": {
            "alpha": ana.ALPHA,
            "REPLICATED_if": ["Holm-adjusted p < 0.05 and 95% CI > 0 on at least one of the two main windows",
                              "the other main window has a non-negative point estimate", "guardrails pass"],
            "guardrails": {"B40_q20_KH_recall_change_min": ana.GUARD_KH_RECALL_B40,
                           "B80_full81_accuracy_change_min": ana.GUARD_FULL81_ACCURACY_B80},
            "noninferiority_margin": ana.NONINFERIORITY_MARGIN,
            "misfit_question_rule": {
                "COVERAGE_SUFFICIENT": "candidate REPLICATED and (candidate - its CCM reference) 95% CI lower bound > -margin "
                                       "on both main windows",
                "COVERAGE_WORKS_BUT_CCM_MEASURABLY_BETTER": "candidate REPLICATED, non-inferiority fails, and the CCM reference "
                                                            "is better with a CI excluding zero in a main window",
                "COVERAGE_WORKS_NONINFERIORITY_INCONCLUSIVE": "candidate REPLICATED, non-inferiority fails, no significant CCM advantage",
                "NOT_REPLICATED": "candidate not REPLICATED",
                "margin_rationale": "about half of the Phase 1.20 confirmed CCM effects (+0.0023 on 16-80, +0.0055 on 16-40), rounded down (stricter)",
                "by_construction": "each candidate and its CCM reference share every query up to B40, so the 16-40 comparison is expected to be ~0; the informative misfit comparison is 16-80 (driven by 41-80)",
            },
        },
        "information_guard": "policies receive masked label and depth arrays (-1 / NaN for unqueried rows); test labels, "
                             "unqueried labels, depths and B1 distances are unreachable; audited in invariance_audit.json",
        "numerical_environment": "OMP_NUM_THREADS=OPENBLAS_NUM_THREADS=MKL_NUM_THREADS=1 for every run of every policy "
                                 "(gate_runner_equivalence_addendum.json)",
        "gates": {"splits": split_gate["status"], "runner_equivalence": equivalence["resolution_status"]},
        "code_sha256": code,
        "confirmation_checkpoints_existing_at_freeze": existing,
        "external_blind_pool": "not opened, not read, not computed on; to be proposed only after Phase 1.21 is complete",
    }
    path = OUT / "PHASE1_21_PREREGISTERED_PROTOCOL.json"
    rep.require(not path.exists(), "protocol already frozen")
    path.write_text(json.dumps(protocol, indent=2), encoding="utf-8")
    print("FROZEN", path.name, sha(path)[:16], "| repeats used anywhere:", audit["repeats_used_anywhere"],
          "| collisions with 61-120:", collisions)


if __name__ == "__main__":
    main()
