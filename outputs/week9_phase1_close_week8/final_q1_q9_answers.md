# Explicit answers to Q1–Q9

## Q1_margin_crossed_all_100_by_320

```json
{
  "answer": false,
  "count": 91,
  "unresolved": 9
}
```

## Q2_random_crossings_by_320

```json
{
  "count": 2727,
  "percentage": 90.9,
  "unresolved": 273
}
```

## Q3_restricted_mean_query_burden_H320

```json
{
  "binary_margin": 53.47,
  "binary_random": 78.46633333333334
}
```

## Q4_restricted_H320_difference

```json
24.99633333333334
```

## Q5_restricted_H320_ratio

```json
1.4674833239822955
```

## Q6_at_least_X_average_queries

```json
{
  "bootstrap_scope": "Descriptive uncertainty under the frozen repeat/fold/continuation design; not a population or transfer guarantee.",
  "design_conditional_bootstrap_lower_bound_positive": false,
  "fixed_benchmark_lower_bound_positive": false,
  "hierarchical_one_sided_95pct_lower_bound_queries": null,
  "margin_all_100_observed": false,
  "matched_category_counts": {
    "both_crossed": 2608,
    "margin_crossed_random_unresolved": 122,
    "neither_crossed": 151,
    "random_crossed_margin_unresolved": 119
  },
  "naive_Qrandom_gt_320_for_every_unresolved_is_valid": false,
  "path_specific_average_saving_lower_bound_queries": null,
  "random_unresolved": 273,
  "random_unresolved_guaranteed_Q_gt_320": 267,
  "random_unresolved_tail_indeterminate": 6,
  "restricted_H320_delta_is_automatically_a_lower_bound": false,
  "rounded_down_supervisor_X_queries": null,
  "status": "NOT_SUPPORTED_MARGIN_TAIL_UNRESOLVED",
  "supervisor_safe_sentence": "An 'at least X queries saved on average' claim is not identified because at least one Margin crossing remains unresolved at H=320.",
  "why_naive_prompt_argument_fails": "Historical Q is the first of three passing checkpoints. An unresolved path passing at 316 and 320 may later receive Q=316 after a 324 pass."
}
```

## Q7_terminal_accuracies

```json
[
  {
    "binary_margin_accuracy": 0.9579012345679008,
    "budget": 40,
    "margin_minus_random": 0.0138477366255137,
    "matched_random_accuracy": 0.9440534979423872,
    "subset": "full81"
  },
  {
    "binary_margin_accuracy": 0.8708000000000005,
    "budget": 40,
    "margin_minus_random": 0.0420400000000007,
    "matched_random_accuracy": 0.8287599999999997,
    "subset": "B1_q30"
  },
  {
    "binary_margin_accuracy": 0.8170588235294112,
    "budget": 40,
    "margin_minus_random": 0.0425490196078421,
    "matched_random_accuracy": 0.774509803921569,
    "subset": "B1_q20"
  },
  {
    "binary_margin_accuracy": 0.962469135802469,
    "budget": 80,
    "margin_minus_random": 0.0109506172839497,
    "matched_random_accuracy": 0.9515185185185192,
    "subset": "full81"
  },
  {
    "binary_margin_accuracy": 0.8792000000000004,
    "budget": 80,
    "margin_minus_random": 0.0300400000000005,
    "matched_random_accuracy": 0.8491599999999999,
    "subset": "B1_q30"
  },
  {
    "binary_margin_accuracy": 0.8329411764705873,
    "budget": 80,
    "margin_minus_random": 0.0370784313725481,
    "matched_random_accuracy": 0.7958627450980391,
    "subset": "B1_q20"
  },
  {
    "binary_margin_accuracy": 0.9625925925925924,
    "budget": 160,
    "margin_minus_random": 0.0051810699588477,
    "matched_random_accuracy": 0.9574115226337446,
    "subset": "full81"
  },
  {
    "binary_margin_accuracy": 0.8796,
    "budget": 160,
    "margin_minus_random": 0.0142133333333333,
    "matched_random_accuracy": 0.8653866666666667,
    "subset": "B1_q30"
  },
  {
    "binary_margin_accuracy": 0.8352941176470583,
    "budget": 160,
    "margin_minus_random": 0.0195490196078427,
    "matched_random_accuracy": 0.8157450980392156,
    "subset": "B1_q20"
  },
  {
    "binary_margin_accuracy": 0.9625925925925924,
    "budget": 320,
    "margin_minus_random": 0.0001810699588475,
    "matched_random_accuracy": 0.9624115226337449,
    "subset": "full81"
  },
  {
    "binary_margin_accuracy": 0.8796,
    "budget": 320,
    "margin_minus_random": 0.0004933333333333,
    "matched_random_accuracy": 0.8791066666666667,
    "subset": "B1_q30"
  },
  {
    "binary_margin_accuracy": 0.8347058823529407,
    "budget": 320,
    "margin_minus_random": 0.0005882352941172,
    "matched_random_accuracy": 0.8341176470588235,
    "subset": "B1_q20"
  }
]
```

## Q8_terminal_vs_AULC

```json
{
  "frozen_AULC_delta_margin_minus_random": 0.037299785539,
  "interpretation": "The terminal Fold-B1-q20 accuracy comparison has positive point estimates at 40, 80, 160, and 320, but the H320 contrast is practically zero and its design-conditional 95% interval [-0.0011, +0.0023] crosses zero. The frozen AULC contrast remains positive and measures earlier learning speed. Balanced accuracy and Keyhole recall are separate descriptive terminal endpoints; all of these remain different estimands.",
  "terminal_q20_deltas": [
    {
      "binary_margin_accuracy": 0.8170588235294112,
      "budget": 40,
      "margin_minus_random": 0.0425490196078421,
      "matched_random_accuracy": 0.774509803921569,
      "subset": "B1_q20"
    },
    {
      "binary_margin_accuracy": 0.8329411764705873,
      "budget": 80,
      "margin_minus_random": 0.0370784313725481,
      "matched_random_accuracy": 0.7958627450980391,
      "subset": "B1_q20"
    },
    {
      "binary_margin_accuracy": 0.8352941176470583,
      "budget": 160,
      "margin_minus_random": 0.0195490196078427,
      "matched_random_accuracy": 0.8157450980392156,
      "subset": "B1_q20"
    },
    {
      "binary_margin_accuracy": 0.8347058823529407,
      "budget": 320,
      "margin_minus_random": 0.0005882352941172,
      "matched_random_accuracy": 0.8341176470588235,
      "subset": "B1_q20"
    }
  ]
}
```

## Q9_PCA

```json
{
  "caveat": "Two-dimensional PCA-plane classifier slice masked only by the PC1-PC2 projected convex hull. Setting PC3=PC4=0 does not establish occupancy on the observed four-dimensional data manifold; this is not the true empirical, Keyhole, or physical boundary.",
  "combined_variance": 0.5842210622928455,
  "component_interpretations": {
    "PC1": {
      "component": "PC1",
      "direction_interpretation": "Positive PC1 corresponds to higher standardized LS and lower standardized P in the chosen sign orientation.",
      "dominant_feature": "LS",
      "dominant_loading": 0.7102383569037456,
      "explained_variance_ratio": 0.3196647110661834,
      "high_magnitude_features": [
        "P",
        "LS"
      ],
      "negative_high_magnitude_features": [
        "P"
      ],
      "positive_high_magnitude_features": [
        "LS"
      ],
      "relative_threshold": 0.65,
      "scientific_scope": "input-variance direction only; not physical importance, causality, or supervised Keyhole association",
      "short_interpretation": "LS versus P contrast"
    },
    "PC2": {
      "component": "PC2",
      "direction_interpretation": "PC2 follows the sampled input-design variation associated mainly with ST; the component sign itself is arbitrary.",
      "dominant_feature": "ST",
      "dominant_loading": 0.9084643327282307,
      "explained_variance_ratio": 0.26455635122666216,
      "high_magnitude_features": [
        "ST"
      ],
      "negative_high_magnitude_features": [],
      "positive_high_magnitude_features": [
        "ST"
      ],
      "relative_threshold": 0.65,
      "scientific_scope": "input-variance direction only; not physical importance, causality, or supervised Keyhole association",
      "short_interpretation": "primarily ST variation"
    },
    "PC3": {
      "component": "PC3",
      "direction_interpretation": "PC3 follows the sampled input-design variation associated mainly with VX; the component sign itself is arbitrary.",
      "dominant_feature": "VX",
      "dominant_loading": 0.9640274371318529,
      "explained_variance_ratio": 0.25037284758450656,
      "high_magnitude_features": [
        "VX"
      ],
      "negative_high_magnitude_features": [],
      "positive_high_magnitude_features": [
        "VX"
      ],
      "relative_threshold": 0.65,
      "scientific_scope": "input-variance direction only; not physical importance, causality, or supervised Keyhole association",
      "short_interpretation": "primarily VX variation"
    },
    "PC4": {
      "component": "PC4",
      "direction_interpretation": "PC4 combines the sampled input-design variation in P/LS; the component sign itself is arbitrary.",
      "dominant_feature": "LS",
      "dominant_loading": 0.6488674065786582,
      "explained_variance_ratio": 0.16540609012264781,
      "high_magnitude_features": [
        "P",
        "LS"
      ],
      "negative_high_magnitude_features": [],
      "positive_high_magnitude_features": [
        "P",
        "LS"
      ],
      "relative_threshold": 0.65,
      "scientific_scope": "input-variance direction only; not physical importance, causality, or supervised Keyhole association",
      "short_interpretation": "joint P + LS direction"
    }
  },
  "interpretation_diagnostics": {
    "caveat": "2D neighbour mixing can hide separation or overlap along PC3/PC4 and is not a physical-boundary metric",
    "class_centroid_distance_pc1_pc2": 2.1894527548992078,
    "class_centroids_pc1_pc2": {
      "Conduction": {
        "PC1": 0.3837136175156445,
        "PC2": -0.09222932293837505
      },
      "Keyhole": {
        "PC1": -1.7451085070574515,
        "PC2": 0.41945390706219876
      }
    },
    "diagnostic_status": "after-the-fact 2D projection interpretation only",
    "margin_query_stage_counts": {
      "acquired_161_320": 160,
      "acquired_17_40": 24,
      "acquired_41_80": 40,
      "acquired_81_160": 80,
      "held_out_test": 81,
      "initial_1_16": 16,
      "unqueried_pool_by_h320": 4
    },
    "mean_opposite_label_fraction_by_margin_query_stage": {
      "acquired_161_320": 0.016875,
      "acquired_17_40": 0.4124999999999999,
      "acquired_41_80": 0.205,
      "acquired_81_160": 0.08249999999999999,
      "held_out_test": 0.08271604938271605,
      "initial_1_16": 0.21875,
      "unqueried_pool_by_h320": 0.0
    },
    "mean_opposite_label_fraction_by_representative_test_role": {
      "B1_q20": 0.2176470588235294,
      "B1_q30_only": 0.075,
      "held_out_non_q30": 0.042857142857142864,
      "not_in_representative_test": 0.09537037037037037
    },
    "neighbours_for_mixing": 10,
    "query_stage_definition": "held-out test rows and the four unqueried H320 pool rows are separated; only revealed queried labels could influence later GPC acquisitions"
  },
  "pc1_dominant_loading": {
    "feature": "LS",
    "loading": 0.7102383569037456
  },
  "pc1_variance": 0.3196647110661834,
  "pc2_dominant_loading": {
    "feature": "ST",
    "loading": 0.9084643327282307
  },
  "pc2_variance": 0.26455635122666216,
  "representative_run_id": "w85__r19_f03",
  "representative_selection_is_label_informed": true,
  "scaling_robustness": {
    "qualitative_agreement": "StandardScaler and RobustScaler agree that ST is strongly represented on PC2 and VX mainly on PC3; they materially disagree on PC1, which is LS-versus-P under StandardScaler but primarily P under RobustScaler.",
    "robust": {
      "explained_variance_ratio": [
        0.47266622853922136,
        0.20369739579075521,
        0.18227144708224394,
        0.14136492858777955
      ],
      "pc1_interpretation": "primarily P variation",
      "pc1_plus_pc2": 0.6763636243299765,
      "pc2_interpretation": "primarily ST variation",
      "pc3_interpretation": "primarily VX variation"
    },
    "st_pc2_loadings": {
      "robust": 0.8681141715416123,
      "standard": 0.9084643327282307
    },
    "standard": {
      "explained_variance_ratio": [
        0.3196647110661834,
        0.26455635122666216,
        0.25037284758450656,
        0.16540609012264781
      ],
      "pc1_interpretation": "LS versus P contrast",
      "pc1_plus_pc2": 0.5842210622928455,
      "pc2_interpretation": "primarily ST variation",
      "pc3_interpretation": "primarily VX variation"
    },
    "standard_vx_loading_energy_pc1_pc2": 0.05089905423032129,
    "standard_vx_loading_energy_pc3": 0.9293488995430086,
    "vx_pc3_loadings": {
      "robust": 0.9697753211299305,
      "standard": 0.9640274371318529
    }
  },
  "variance_outside_pc1_pc2": 0.41577893770715446
}
```
