# Phase 1.20 wording errata (recorded in Phase 1.21)

The Phase 1.20 files are historical outputs and are left unchanged. The corrections below apply wherever
Phase 1.20 material is quoted, summarised or reused (thesis text, slides, Phase 1.21 and later reports).
No number changes; only how the numbers are described.

| where | wording used | corrected wording | why |
|---|---|---|---|
| `PROTOCOL_AMENDMENT_1.json` (reason), chat summaries | "324-label ceiling", "theoretical ceiling" (0.8565) | "empirical all-label M3 reference" or "empirical headroom reference" | 0.8565 is the q20 accuracy of M3 fitted on all 324 training labels of each outer run. It is an observed reference for this model and evaluator, not a bound: a different model, or a different subset of labels, can score higher. |
| `PROTOCOL_AMENDMENT_1.json` (reason) | "reducible-error budget (max +0.031 on 16-40, +0.0125 on 16-80 ...)" | "observed headroom relative to the empirical all-label M3 reference (+0.031 on 16-40, +0.0125 on 16-80)" | "Maximum possible improvement" is not established. The correct statement is: improvement relative to the empirical all-label M3 reference leaves only this much observed headroom. |
| `figures/03_mechanisms.png` (legend; from `src/week9_phase1_20_figures.py`) | "M3 with all 324 labels (ceiling)" | "M3 with all 324 labels (empirical all-label reference)" | as above |
| `figures/03_mechanisms.png` (panel title) | "only false positives are reducible" | "in the evaluated regime, false negatives remained approximately stable while most observed learning gains came from reducing false positives" | The figure shows what happened under these policies and budgets, not what is possible under any policy. |
| `FINAL_PHASE1_20_REPORT.md`, `PROTOCOL_AMENDMENT_1.json` | "250 runs", "250 confirmation runs" | "250 outer cross-validation runs (50 repeat blocks) on the same 405-simulation population" | The runs are not 250 independent simulations and not new data. They are re-partitions of the same 405 simulations, so runs within and across repeat blocks share simulations. This is why inference uses repeat blocks, and why confirmation on repeats 11-60 is internal confirmation, not external validation. |

Using the corrected wording, Phase 1.20's confirmed effects read (repeats 11-60, q20 accuracy AULC):

- CCM (`cov_then_misfit_B40`): +0.0023 on 16-80 and +0.0055 on 16-40 over M3 margin. Relative to the empirical
  all-label M3 reference this is about 18% (16-80) and 18% (16-40) of the observed headroom.
- early8 + CCM: +0.0041 on 16-80 and +0.0116 on 16-40. That is about 33% and 37% of the observed headroom.

(Headroom = empirical all-label M3 reference minus margin's AULC in the same window, as quantified in amendment 1 on development repeats: +0.0125 on 16-80, +0.031 on 16-40.)
