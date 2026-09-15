"""Week 9 Phase 1.23 — freeze the synthetic stress-test protocol before any synthetic trajectory exists."""
from __future__ import annotations

import dataclasses
import datetime
import hashlib
import json
from pathlib import Path

from src import week9_phase1_23_grid as grid
from src import week9_phase1_23_synthetic as syn


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main() -> None:
    out = syn.OUTPUT / "PHASE1_23_SYNTHETIC_PROTOCOL.json"
    search_existing = sorted(str(p.relative_to(syn.OUTPUT)) for p in syn.CHECKPOINTS.rglob("*.json.gz"))
    assert not search_existing, f"synthetic trajectories already exist: {search_existing[:5]}"
    assert not out.exists(), "protocol already frozen"
    truths = sorted(str(p.relative_to(syn.OUTPUT)) for p in syn.CHECKPOINTS.rglob("*.npz"))
    src = Path(syn.__file__).parent
    protocol = {
        "phase": "Week 9 Phase 1.23 - pre-registered synthetic stress test of the frozen Phase 1.21 policies",
        "frozen_at_utc": datetime.datetime.now(datetime.timezone.utc).isoformat(),
        "purpose": "map where the frozen boundary-conditioned coverage rule helps, is equivalent to, or hurts plain M3 "
                   "margin; not to make it win",
        "no_tuning": "pad 0.25, pad floor 0.05, uncertainty weight 1, switch B40, k_seed 8 and standardised-x coverage "
                     "coordinates are the Phase 1.21 values; M3 is the Phase 1.13 fit_hybrid object; nothing is tuned on "
                     "synthetic or SPH results",
        "sph_data_used_to_choose_settings": "no. Synthetic inputs, physics direction, units, prevalence, pool size and "
                                            "families were fixed from first principles. Inherited from the frozen method "
                                            "only: budgets 16-80, the B40 switch and the absolute pad floor 0.05 (in h units)",
        "known_scale_dependence": "pad_floor 0.05 is absolute in h units; here SD(h) = 0.289, so the floor is 0.17 SD(h)",
        "generator": {
            "domain": "x ~ U[0,1]^4 i.i.d.",
            "physics_coordinate": "h(x) = u.(x - 1/2), u = (1,1,1,1)/2 (unit norm), SD(h) = sqrt(1/12)",
            "orthogonal_coordinates": "z_j = q_j.(x - 1/2), q_1..q_3 an orthonormal basis of u-perp (QR of [u, e1, e2, e3])",
            "displacement_field": "random Fourier features (1000) of an RBF-kernel GP with length-scale l, standardised to "
                                  "mean 0 / SD 1 on the reference set",
            "families": {
                "physics_exact (F7)": "y = 1[h > t]",
                "shift (F1-F3)": "y = 1[h - a SD(h) delta(z_1..z_d) > t]; F1 = a 0.1; F2 = a 0.3, l 0.5; F3 = a 0.3 l 0.2 or a 0.6",
                "fold (F4)": "y = 1[h - a SD(h) delta(x - 1/2) > t], delta over all 4 inputs (non-monotone in h), l 0.15",
                "islands (F5)": "y = 1[h > t0] XOR [x inside one of k balls of radius 0.2 centred where 1.2r <= |h - t0| <= 3r]",
                "rotated (F6)": "y = 1[cos(theta) h + sin(theta) z_1 > t]; the physics coordinate is wrong by angle theta",
            },
            "threshold": "t = (1 - prevalence) quantile of the score on the reference set",
            "per_function_sets": {"pool": "i.i.d. candidates (400; 1000 in two sensitivity cells)",
                                  "test": "4000 i.i.d. points, independent of the pool",
                                  "reference": "100000 i.i.d. points used only for boundary distances and thresholds"},
            "boundary_distance": "Euclidean distance (x units) from a test point to the nearest reference point of the "
                                 "opposite class",
            "near_boundary_subsets": "q20 / q30 = the 20% / 30% of test points with the smallest boundary distance "
                                     "(ties by index); the SPH B1 idea applied to a dense independent test set",
            "seeds": "sha256-derived from ('week9_phase1_23', 'truth', cell_id, function index); maximin seed from "
                     "('maximin', cell, index); random order from ('random', cell, index); physics fit seed per budget",
            "replication_unit": "independently generated ground-truth function (own field, threshold, pool, test and "
                                "reference sets); no function is reused across cells",
        },
        "grid": {"core_cells": [dataclasses.asdict(c) for c in grid.CORE],
                 "sensitivity_cells": [dataclasses.asdict(c) for c in grid.SENSITIVITY],
                 "functions_per_cell": grid.N_FUNCTIONS,
                 "family_labels": {c.cell_id: grid.family_of(c.cell_id) for c in grid.CELLS}},
        "design": {"budgets": "16..80, M3 refit at every budget", "initial_design":
                   "seeded greedy maximin order over the pool in standardised x (Week 8.5 rule); a policy with seed size k "
                   "takes the first k points and extends along the same order until both classes are queried",
                   "metrics_from": "B16 for every policy"},
        "policies": {
            "random": "frozen 16-point seed, then a seeded random order",
            "margin": "CONTROL: frozen 16-point seed, M3 probability margin",
            "coverage_then_margin_B40": "CANDIDATE A (frozen): Phase 1.20 make_band_coverage('x', 1.0, 0.25, 40)",
            "early8__coverage_then_margin_B40": "CANDIDATE B (frozen): 8-point seed + Candidate A's rule",
            "early8__margin": "ABLATION: 8-point seed + margin (separates initial-design from acquisition effects)",
            "global_unc_div_then_margin_B40": "LITERATURE ANALOGUE / ABLATION: the frozen rank(uncertainty) + rank(distance) "
                                              "score over ALL candidates (no label-estimated h-band) until B40, then "
                                              "margin (sequential uncertainty + diversity, cf. Brinker 2003)",
            "straddle": f"LITERATURE BASELINE (cells {list(grid.STRADDLE_CELLS)} only): Bryan et al. 2005 straddle "
                        "1.96 sd - |mean| on the M3 latent",
            "sensitivity_cells_run": list(grid.SENSITIVITY_POLICIES),
        },
        "endpoints": {
            "primary_map": "q20 accuracy AULC over budgets 16-80 and 16-40, candidate minus margin, per function",
            "co_primary_global": "global accuracy AULC 16-80 and 16-40 (1 - volume of the symmetric difference, "
                                 "estimated on the dense test set)",
            "secondary": ["q20 accuracy AULC 41-80", "q30 accuracy AULC 16-80", "global balanced accuracy AULC 16-80",
                          "error depth q95 (95th percentile boundary distance of misclassified test points) at B40 and B80",
                          "global accuracy at B80"],
            "aulc": "trapezoid over integer budgets divided by (hi - lo)",
            "ablation_contrasts": ["A - global_unc_div (value of boundary conditioning)",
                                   "B - early8__margin (acquisition value under the early start)",
                                   "early8__margin - margin (initial-design value)",
                                   "A - random and margin - random (sanity)", "straddle - margin (straddle cells)"],
        },
        "inference": {
            "unit": "function (independent ground truth), paired across policies",
            "estimate": "mean paired difference; 95% percentile bootstrap CI (10,000 draws over functions); 90% CI for "
                        "equivalence",
            "test": "two-sided sign-flip permutation of paired differences (10,000 draws)",
            "multiplicity": "Holm over the 80 primary tests {A, B} x {q20 AULC 16-80, 16-40} x 20 core cells; "
                            "unadjusted CIs are also reported",
            "classification": {
                "HELPS_MATERIAL": "Holm p < 0.05, 95% CI > 0 and mean >= 0.005",
                "HELPS_SMALL": "Holm p < 0.05, 95% CI > 0 and mean < 0.005",
                "HURTS": "Holm p < 0.05 and 95% CI < 0",
                "EQUIVALENT": "not HELPS/HURTS and 90% CI inside [-0.005, +0.005]",
                "INCONCLUSIVE": "otherwise",
                "equivalence_margin_rationale": "0.5 percentage point of AULC; the SPH pure-acquisition effect (+0.0032) "
                                                "would itself fall inside this margin",
            },
            "phase_diagram": "mean A - margin (and B - margin) per cell as heatmaps over amplitude x length x "
                             "heterogeneity dimension, plus a family strip",
            "validity_map": "per function: A - margin against the truth's best-1D-h-threshold error (label structure "
                            "only), binned by quintile with bootstrap CIs; and an OLS of A - margin on amplitude, length, "
                            "het_dim within the shift family with HC3 standard errors (descriptive)",
            "mechanism_post_hoc": ["share of runs whose queried labels are still separable in h by budget",
                                   "share of B16-39 queries inside the estimated band", "share of steps differing from "
                                   "margin", "band width as share of the pool", "M3 residual SD"],
        },
        "predictions_from_theory_note": {
            "P1": "physics_exact (F7, both sensitivity versions): A and B not better than margin on q20 AULC 16-40 "
                  "(EQUIVALENT or HURTS); margin behaves as bisection in h, which is optimal for a 1D threshold",
            "P2": "F1 (a = 0.1): no material help (EQUIVALENT, HELPS_SMALL or small HURTS)",
            "P3": "shift cells with a >= 0.3 (8 cells): A - margin > 0 on q20 AULC 16-40 in the majority; larger for "
                  "a = 0.6 than a = 0.3 and for d = 3 than d = 1 (directional); no directional prediction for length-scale",
            "P4": "where A helps, |A - margin| on 41-80 is smaller than on 16-40",
            "P5": "F6 rotated: no systematic help from band conditioning; A - global_unc_div <= 0 at 60 and 90 degrees; "
                  "A - margin not predicted",
            "P6": "F5 islands: A - margin EQUIVALENT (islands lie outside the band)",
            "P7": "F4 fold: no confident prediction; weakly A >= margin at a = 0.6",
            "P8": "shift cells with a >= 0.3: A - global_unc_div > 0 (the band adds value over global diversity)",
            "P9": "early8__margin - margin > 0 in most cells; B - early8__margin has the sign of A - margin",
            "P10": "straddle - margin approximately 0 under M3's steep physics mean in F7; no prediction elsewhere",
        },
        "overall_verdict_rules": {
            "A_GENERALISES_IN_PREDICTED_REGION": "A is HELPS_* in >= 4 of the 8 shift cells with a >= 0.3 (q20 AULC 16-40) "
                                                 "and is not HURTS with mean <= -0.005 in F1 or F7",
            "A_SPH_SPECIFIC": "A is HELPS_* in <= 1 of those 8 cells",
            "A_MIXED": "otherwise",
            "BAND_CONDITIONING_MATTERS": "A - global_unc_div has 95% CI > 0 in >= 4 of those 8 cells (q20 AULC 16-40)",
            "BAND_CONDITIONING_NOT_SHOWN": "otherwise",
        },
        "numerical_environment": "OMP_NUM_THREADS = OPENBLAS_NUM_THREADS = MKL_NUM_THREADS = 1",
        "pre_freeze_activity_disclosed": [
            "timing smoke on 5 separate smoke cells (outputs/.../synthetic_smoke; ids never used in the grid); only "
            "runtimes and seed sizes were inspected",
            "generator validity gate on function 0 (and 1 for islands) of every cell: prevalence, class counts, q20 class "
            "share, best-1D-threshold error; no policy was involved",
            "island radius changed from 0.12 to 0.2 after the gate showed 0.2-0.75% flipped volume (islands "
            "unreachable by any policy); decided from label structure only",
            "toy checks for the theory note on separate random data: C = 1e6 logistic threshold at the gap midpoint; "
            "M3 margin choice near the midpoint in h",
        ],
        "truth_caches_existing_at_freeze": truths,
        "code_sha256": {n: sha(src / n) for n in ("week9_phase1_23_synthetic.py", "week9_phase1_23_grid.py",
                                                  "week9_phase1_20_acquisition_search.py",
                                                  "week9_phase1_13_fixed_physics_ard_discrepancy.py",
                                                  "week9_phase1_11_fixed_mean_discrepancy_gp.py")},
        "phase1_21_final_policy_freeze_sha256": sha(syn.ROOT / "outputs" / "week9_phase1_21_simplification_replication"
                                                    / "FINAL_POLICY_FREEZE.json"),
        "trajectories_existing_at_freeze": search_existing,
    }
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(protocol, indent=2), encoding="utf-8")
    print("FROZEN", out.name, sha(out)[:16], "cells", len(grid.CELLS), "trajectories", len(grid.jobs()))


if __name__ == "__main__":
    main()
