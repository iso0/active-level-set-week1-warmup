# Week 18 Phase 2 — baselines on the new benchmark (DEV blocks only)

Tables: `phase2/real_aulc.csv`, `phase2/real_curves.csv`, `phase2/twin_aulc.csv`, `phase2/external_validity_*.csv`.
Code: `src/week18_baselines.py`, `src/week18_metrics.py`, `src/week18_external_validity.py`.

## Real tasks (BA AULC, pooled per repeat, 8 DEV repeats)
| Arm | R1 POOLED | R2 TRANSFER | R2rev | R3 NEW | R3 OLD |
|---|---:|---:|---:|---:|---:|
| G3 + margin | 0.948 | 0.682 | 0.929 | 0.671 | 0.924 |
| G3 + random | 0.924 | 0.657 | 0.900 | **0.681** | 0.892 |
| G3 + Candidate B | 0.933 | 0.682 | 0.927 | 0.674 | 0.913 |
| G3 (fixed OLD hypers) + margin / random | — | **0.686** / 0.667 | — | 0.664 / 0.671 | — |
| LT + margin | 0.947 | 0.685 | 0.920 | 0.656 | 0.931 |
| M3 + margin | **0.950** | 0.669 | 0.929 | 0.601 | 0.930 |
| H + margin | 0.947 | 0.497 | 0.913 | 0.583 | 0.921 |
| GPR-depth + straddle (Week 7) | — | — | **0.941** | — | **0.944** |
- The OLD prior lifts NEW ranking quality strongly (AUC AULC 0.819 → 0.909, R3_NEW → R2) but BA only by +0.011.
- GPR-depth reproduces Week 7: higher BA, lower q20 (R3_OLD q20 0.817 vs G3 0.842).
- Convergence: 704/22,072 fits (mostly R2) stopped at fixed-point error 1e-6–9e-4 under the Week 17 rule;
  reproduced impact |Δp| ≤ 6e-5; solver fixed for all later runs.

## Digital twins (NSD AULC, 8 DEV reps; 3 single-class NEW-like pools skipped as degenerate)
| Twin × distribution | G3+m | G3+rand | G3+candB | LT+m | M3+m | H+m | GPR-depth+straddle |
|---|---:|---:|---:|---:|---:|---:|---:|
| T_GP pooled / OLD / NEW | .900 / .816 / .973 | .674 / .631 / .957 | .851 / .812 / .978 | **.906 / .855 / .982** | .832 / .729 / .934 | .620 / .618 / .904 | — |
| T_GBT pooled / OLD / NEW | .722 / .725 / .821 | .696 / .561 / .706 | .757 / .725 / .867 | **.800** / .720 / **.876** | .752 / .648 / .845 | .572 / .594 / .820 | — |
| T_NW pooled / OLD / NEW | .813 / .762 / .534 | .643 / .660 / .618 | .761 / .809 / .535 | **.854 / .829** / .673 | .828 / .800 / .761 | .793 / .774 / **.762** | — |
| T_QL pooled / OLD / NEW | .891 / .825 / .823 | .641 / .556 / .759 | .836 / .796 / .837 | .950 / **.887** / .937 | **.959** / .866 / **.946** | **.959** / .870 / .941 | — |
| T_TOBIT pooled / OLD / NEW | .873 / .776 / .976 | .775 / .585 / .947 | .809 / .775 / .986 | .864 / .779 / .987 | .801 / .655 / .934 | .673 / .547 / .901 | **.879 / .830 / .996** |
| T_DEPTH OLD | .873 | .631 | .853 | .865 | .733 | .559 | **.932** (same family) |

## External validity (Kendall τ of the five-arm orderings G3+m, G3+rand, G3+cov, LT+m, M3+m)
Mean τ with the real tasks: twins 0.22 (80 pairs), Week 17 held-out cells 0.16 (60 pairs); **real tasks with each
other: 0.00** (10 pairs). The real tasks do not share an ordering of these baselines (NEW reverses random; M3 is
near-best on OLD/POOLED but worst-but-one on NEW). Consequence: no synthetic family — ours or Week 17's — can be
validated as a proxy for "the" real ranking, because there is none; Week 17's held-out conclusion "M3 ≪ G3"
(−0.10) does not hold on OLD/POOLED (M3 ≥ G3), whose physics behaves like the physics-aligned cells H01/H02.
Robust across all real tasks and twins: random refinement is worst except on NEW-like pools.
