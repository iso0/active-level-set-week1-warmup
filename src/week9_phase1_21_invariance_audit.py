"""Week 9 Phase 1.21 — leakage / invariance audit for Candidates A and B.

For development runs only (repeats 1-10; replication partitions are never used here), follow each
candidate's own trajectory.  At audited states, rebuild the evaluator fit and the policy State from
(i) the true label/depth arrays and (ii) arrays in which EVERY unqueried row's label and depth has
been replaced by random values.  A label-blind policy must produce the same M3 probabilities and
the same chosen row in both.  Audited budgets include the early-start states (B8-B15), the coverage
phase (B16-B39) and the margin phase (B40-B79).  A static check confirms that no policy function
in the audited call graph references the unmasked arrays.
"""
from __future__ import annotations

import inspect
import json

import numpy as np
from sklearn.preprocessing import StandardScaler

from src import week8_5_frozen_sample_efficiency_confirmation as w85
from src import week9_phase1_11_fixed_mean_discrepancy_gp as p11
from src import week9_phase1_13_fixed_physics_ard_discrepancy as p13
from src import week9_phase1_20_acquisition_search as search
from src import week9_phase1_20_early_start as early
from src import week9_phase1_21_simplification_replication as rep

AUDIT_RUNS = ("w85__r01_f02", "w85__r04_f05", "w85__r07_f03", "w85__r10_f01")
AUDIT_BUDGETS = set(range(8, 16)) | {16, 20, 25, 30, 35, 39, 40, 45, 55, 65, 79}


def state_for(policy_arrays: search.Arrays, spec, revealed: np.ndarray, budget: int, xs, zs, train):
    fit = p13.fit_hybrid(policy_arrays.x4, policy_arrays.logh, policy_arrays.labels, revealed, train,
                         p11.fit_physics_mean(policy_arrays.logh, policy_arrays.labels, revealed,
                                              p13.seed_u32("shared_physics", spec.run_id, budget)),
                         "M3", search.LENGTH_UPPER)
    candidates = np.setdiff1d(train, revealed)
    comp = p13.components(fit, policy_arrays.x4[candidates], policy_arrays.logh[candidates])
    n = len(policy_arrays.labels)
    seen_label = np.full(n, -1, dtype=int)
    seen_label[revealed] = policy_arrays.labels[revealed]
    seen_depth = np.full(n, np.nan)
    seen_depth[revealed] = policy_arrays.logdepth[revealed]
    return search.State(run_id=spec.run_id, budget=budget, revealed=revealed, candidates=candidates,
                        seen_label=seen_label, seen_logdepth=seen_depth, x_scaled=xs, z_scaled=zs,
                        logh=policy_arrays.logh, p_cand=comp["probability"], mean_cand=comp["final_latent"],
                        var_cand=comp["latent_variance"], fit=fit,
                        rng=np.random.default_rng(p13.seed_u32("random", spec.run_id, budget)),
                        x4=policy_arrays.x4, train=train, cache={}, leaky_rank=None), comp["probability"]


def main() -> None:
    population, specs = rep.load_all_specs()
    truth = search.build_arrays(population)
    by_id = {s.run_id: s for s in specs}
    rng = np.random.default_rng(p13.seed_u32("phase1_21-invariance"))
    records, mismatches = [], 0
    for policy in (rep.CANDIDATE_A, rep.CANDIDATE_B):
        k, select = rep.POLICIES[policy]
        for run_id in AUDIT_RUNS:
            spec = by_id[run_id]
            search.require(spec.repeat <= 10, "audit must stay on development repeats")
            train = np.asarray(spec.train_indices, dtype=int)
            xs = StandardScaler().fit(truth.x4[train]).transform(truth.x4)
            zs = StandardScaler().fit(truth.orth[train]).transform(truth.orth)
            queried = early.seed_prefix(w85.initial_design(spec, population), truth.labels, k)
            for budget in range(len(queried), 80):
                revealed = np.asarray(queried, dtype=int)
                true_state, true_p = state_for(truth, spec, revealed, budget, xs, zs, train)
                chosen = select(true_state)
                if budget in AUDIT_BUDGETS:
                    hidden = np.setdiff1d(np.arange(len(truth.labels)), revealed)
                    scrambled = search.Arrays(x4=truth.x4, logh=truth.logh, labels=truth.labels.copy(),
                                              logdepth=truth.logdepth.copy(), orth=truth.orth)
                    scrambled.labels[hidden] = rng.integers(0, 2, len(hidden))
                    scrambled.logdepth[hidden] = rng.normal(4.5, 1.0, len(hidden))
                    s_state, s_p = state_for(scrambled, spec, revealed, budget, xs, zs, train)
                    s_chosen = select(s_state)
                    same = bool(s_chosen == chosen and np.array_equal(s_p, true_p))
                    mismatches += int(not same)
                    records.append({"policy": policy, "run_id": run_id, "budget": budget,
                                    "phase": "early-start seed/active (<16)" if budget < 16 else
                                             ("coverage (16-39)" if budget < 40 else "margin (40-79)"),
                                    "hidden_rows_scrambled": int(len(hidden)), "same_choice_and_probabilities": same})
                queried.append(chosen)
    static_sources = "".join(inspect.getsource(f) for f in (search.make_band_coverage, search.estimated_band,
                                                             search.pol_margin, search.argbest, search._rank01))
    static_ok = not any(token in static_sources for token in ("arrays.labels", ".labels[", "logdepth[", "leaky_rank"))
    payload = {"status": "PASS" if mismatches == 0 and static_ok else "FAIL",
               "states_audited": len(records), "mismatches": mismatches,
               "static_check_no_unmasked_access_in_policy_code": static_ok,
               "by_phase": {ph: sum(1 for r in records if r["phase"] == ph)
                            for ph in sorted({r["phase"] for r in records})},
               "records": records}
    (rep.OUTPUT / "invariance_audit.json").write_text(json.dumps(payload, indent=2), encoding="utf-8")
    print(json.dumps({k: v for k, v in payload.items() if k != "records"}, indent=2))


if __name__ == "__main__":
    main()
