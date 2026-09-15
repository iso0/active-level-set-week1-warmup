# Week 9 Phase 1 claim ledger

Frozen confirmatory claims and post-hoc diagnostics are kept separate.

## Margin improves Fold-B1-q20 AULC vs matched Random over 16–80

- Category: `frozen_confirmatory`
- Status: `CONFIRMED_FROZEN_WEEK8_5`
- Numeric result: +0.037300 AULC; 20/20 repeat contrasts positive
- Strongest safe wording: Under the frozen Week 8.5 analysis, uncertainty-only Binary Margin learned the empirical near-boundary subset faster than matched Random.
- Must not use: PCA or q20 proves the physical boundary.

## Persistent target attainment by H320

- Category: `posthoc_H320`
- Status: `POSTHOC_DIAGNOSTIC`
- Numeric result: Margin 91/100; Random 2727/3000
- Strongest safe wording: The longer horizon reduces unresolved trajectories; results are a post-hoc closing diagnostic.
- Must not use: H320 was preregistered or upgrades the old QUALIFY decision.

## At least X average query saving

- Category: `posthoc_H320`
- Status: `NOT_SUPPORTED_MARGIN_TAIL_UNRESOLVED`
- Numeric result: {"bootstrap_scope": "Descriptive uncertainty under the frozen repeat/fold/continuation design; not a population or transfer guarantee.", "design_conditional_bootstrap_lower_bound_positive": false, "fixed_benchmark_lower_bound_positive": false, "hierarchical_one_sided_95pct_lower_bound_queries": null, "margin_all_100_observed": false, "matched_category_counts": {"both_crossed": 2608, "margin_crossed_random_unresolved": 122, "neither_crossed": 151, "random_crossed_margin_unresolved": 119}, "naive_Qrandom_gt_320_for_every_unresolved_is_valid": false, "path_specific_average_saving_lower_bound_queries": null, "random_unresolved": 273, "random_unresolved_guaranteed_Q_gt_320": 267, "random_unresolved_tail_indeterminate": 6, "restricted_H320_delta_is_automatically_a_lower_bound": false, "rounded_down_supervisor_X_queries": null, "status": "NOT_SUPPORTED_MARGIN_TAIL_UNRESOLVED", "supervisor_safe_sentence": "An 'at least X queries saved on average' claim is not identified because at least one Margin crossing remains unresolved at H=320.", "why_naive_prompt_argument_fails": "Historical Q is the first of three passing checkpoints. An unresolved path passing at 316 and 320 may later receive Q=316 after a 324 pass."}
- Strongest safe wording: An 'at least X queries saved on average' claim is not identified because at least one Margin crossing remains unresolved at H=320.
- Must not use: Every unresolved H320 Random path has Q>320.

## Terminal accuracy complements AULC

- Category: `posthoc_terminal`
- Status: `DESCRIPTIVE_POSTHOC`
- Numeric result: See terminal_metric_summary.csv
- Strongest safe wording: AULC answers how quickly learning improves; terminal metrics answer model quality at a fixed budget.
- Must not use: Terminal accuracy and AULC are the same estimand.

## PCA clarifies 4D sampled-input geometry

- Category: `posthoc_visualization`
- Status: `VISUAL_DIAGNOSTIC`
- Numeric result: PC1+PC2 explain 58.422% of standardized-feature variance; PC3 explains 25.037%
- Strongest safe wording: Standardized PCA is a label-free view of sampled input variance: PC1 is an LS-versus-P contrast, PC2 is mainly ST variation, and PC3 carries most VX variation.
- Must not use: PCA maximizes Keyhole separation, proves feature importance, or identifies the true 4D physical boundary.
