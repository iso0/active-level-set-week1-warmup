"""Week 9 Phase 1.23 — post-hoc, declared-before-running SPH ablations on Phase 1.21 repeats 61-120.

Adversarial-review questions answered on real data (not a search; no selection follows):
  Q1  Is Candidate B's gain acquisition or initial design?   ->  early8__margin
  Q2  Does the label-estimated band matter on SPH?            ->  global_unc_div_then_margin_B40
Both reuse the Phase 1.21 runner, evaluator and splits unchanged, write to a Phase 1.23 folder, and are
compared with the frozen Phase 1.21 checkpoints (read-only) using the Phase 1.21 repeat-block estimator.
Declared in SPH_ABLATION_DECLARATION.json before the first run.  Descriptive: no Holm verdict, no claim
of confirmation; repeats 61-120 were already used once for the Phase 1.21 replication.
"""
from __future__ import annotations

import datetime
import gzip
import hashlib
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd
from joblib import Parallel, delayed

from src import week8_5_frozen_sample_efficiency_confirmation as w85
from src import week9_phase1_20_acquisition_search as search
from src import week9_phase1_21_analysis as ana21
from src import week9_phase1_21_simplification_replication as rep
from src import week9_phase1_23_synthetic as syn

OUT = syn.OUTPUT
ROOT = OUT / "sph_ablation_checkpoints"
DECLARATION = OUT / "SPH_ABLATION_DECLARATION.json"
ABLATIONS = {"early8__margin": (8, search.pol_margin),
             "global_unc_div_then_margin_B40": (16, syn.make_global_uncertainty_diversity())}
rep.POLICIES.update(ABLATIONS)          # in-memory registration only; the Phase 1.21 module file is unchanged


def run_one(policy, spec, population, arrays, distances):
    rep.POLICIES.update(ABLATIONS)
    return rep.run_spec(policy, spec, population, arrays, distances, ROOT)


def declare() -> None:
    assert not DECLARATION.exists(), "already declared"
    assert not ROOT.exists() or not any(ROOT.rglob("*.json.gz")), "ablation checkpoints already exist"
    src = Path(__file__).parent
    payload = {
        "declared_at_utc": datetime.datetime.now(datetime.timezone.utc).isoformat(),
        "status": "post-hoc adversarial ablation, declared before running; descriptive only",
        "data": "Phase 1.21 replication repeats 61-120 (300 outer CV runs of the same 405 simulations); already used once",
        "policies": {"early8__margin": "first 8 frozen maximin points (extended along the frozen order until both "
                                       "classes), then plain M3 margin",
                     "global_unc_div_then_margin_B40": "frozen rank(uncertainty) + rank(distance) over ALL candidates "
                                                       "until B40 (no band), then margin; same weights/switch as frozen"},
        "comparisons": {"B - early8__margin": "acquisition value under the early start",
                        "early8__margin - margin": "initial-design value",
                        "A - global_unc_div": "value of the label-estimated band on SPH",
                        "global_unc_div - margin": "global uncertainty+diversity vs margin"},
        "endpoints": "q20 accuracy AULC 16-80 and 16-40; repeat-block bootstrap (10,000) and sign-flip as Phase 1.21",
        "no_decision_rule": "reported with CIs; no success criterion; cannot change any frozen Phase 1.21 conclusion",
        "code_sha256": {n: hashlib.sha256((src / n).read_bytes()).hexdigest() for n in
                        ("week9_phase1_23_sph_ablation.py", "week9_phase1_21_simplification_replication.py",
                         "week9_phase1_23_synthetic.py", "week9_phase1_20_acquisition_search.py")},
    }
    DECLARATION.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    print("DECLARED")


def run(workers: int = 8) -> None:
    assert DECLARATION.exists(), "declare first"
    population, specs = rep.load_all_specs()
    arrays = search.build_arrays(population)
    distances = w85.b1_distance(population)
    chosen = [s for s in specs if s.repeat in set(rep.REPLICATION_REPEATS)]
    for policy in ABLATIONS:
        Parallel(n_jobs=workers)(delayed(run_one)(policy, s, population, arrays, distances) for s in chosen)
        print("done", policy, flush=True)


def analyse() -> dict:
    metrics = {p: ana21.load_metrics(p) for p in (rep.CONTROL, rep.CANDIDATE_A, rep.CANDIDATE_B)}
    metrics.update({p: ana21.load_metrics(p, ROOT) for p in ABLATIONS})
    pairs = {"B - early8__margin": (rep.CANDIDATE_B, "early8__margin"), "early8__margin - margin": ("early8__margin", rep.CONTROL),
             "A - global_unc_div": (rep.CANDIDATE_A, "global_unc_div_then_margin_B40"),
             "global_unc_div - margin": ("global_unc_div_then_margin_B40", rep.CONTROL),
             "B - margin (reference, Phase 1.21)": (rep.CANDIDATE_B, rep.CONTROL),
             "A - margin (reference, Phase 1.21)": (rep.CANDIDATE_A, rep.CONTROL)}
    out = {}
    for name, (a, b) in pairs.items():
        for lo, hi in ((16, 80), (16, 40)):
            sa, sb = ana21.block_series(metrics[a], lo, hi), ana21.block_series(metrics[b], lo, hi)
            out[f"{name} | AULC {lo}-{hi}"] = ana21.paired((sa - sb).to_numpy(), f"p123-ablation|{name}|{lo}-{hi}")
    (OUT / "SPH_ABLATION_RESULT.json").write_text(json.dumps(out, indent=2), encoding="utf-8")
    return out


if __name__ == "__main__":
    {"declare": declare, "run": run, "analyse": lambda: print(json.dumps(analyse(), indent=2))}[sys.argv[1]]()
