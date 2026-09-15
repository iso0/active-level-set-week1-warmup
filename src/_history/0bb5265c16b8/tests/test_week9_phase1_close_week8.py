from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path
from unittest import mock

import numpy as np
import pandas as pd

from src import week9_phase1_close_week8 as w9


class Week9Phase1ClosingTests(unittest.TestCase):
    def test_declared_reporting_grids_preserve_frozen_cadence(self) -> None:
        self.assertEqual(w9.declared_grid_to(80), list(range(16, 81)))
        self.assertEqual(w9.declared_grid_to(120)[-3:], [116, 118, 120])
        self.assertEqual(w9.declared_grid_to(160)[-3:], [152, 156, 160])
        self.assertEqual(w9.declared_grid_to(320)[-3:], [312, 316, 320])
        with self.assertRaises(RuntimeError):
            w9.declared_grid_to(319)

    def test_unresolved_tail_lower_bound_respects_crossing_start_definition(self) -> None:
        value, strict, reason = w9.unresolved_q_lower_bound({316: .82, 320: .88})
        self.assertEqual(value, 316)
        self.assertFalse(strict)
        self.assertIn("Q=316", reason)

        value, strict, _ = w9.unresolved_q_lower_bound({316: .76, 320: .82})
        self.assertEqual(value, 320)
        self.assertFalse(strict)

        value, strict, _ = w9.unresolved_q_lower_bound({316: .88, 320: .76})
        self.assertEqual(value, 320)
        self.assertTrue(strict)

    def test_historical_validation_uses_confirmation_aware_expected_values(self) -> None:
        rows = []
        for horizon, expected in w9.FROZEN_EXPECTED.items():
            rows.extend(
                [
                    {"horizon": horizon, "arm": "binary_margin", "finite_persistent_crossings": expected["margin"], "restricted_mean_query_burden": expected["margin_Q"]},
                    {"horizon": horizon, "arm": "binary_random", "finite_persistent_crossings": expected["random"], "restricted_mean_query_burden": expected["random_Q"]},
                ]
            )
        checks = w9.validate_historical_reproduction(pd.DataFrame(rows))
        self.assertEqual(len(checks), 3)
        self.assertTrue(all(row["status"] == "PASS" for row in checks))

    def test_json_writer_replaces_nonstandard_nan(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "result.json"
            w9.write_json(path, {"finite": np.float64(1.25), "missing": float("nan")})
            payload = json.loads(path.read_text(encoding="utf-8"))
        self.assertEqual(payload, {"finite": 1.25, "missing": None})

    def test_query_saving_requires_positive_fixed_and_bootstrap_bounds(self) -> None:
        paths = pd.DataFrame(
            [
                {"arm": "binary_margin", "crossing_observed_H320": True, "guaranteed_Q_gt_320": False},
                {"arm": "binary_random", "crossing_observed_H320": False, "guaranteed_Q_gt_320": True},
            ]
        )
        pairs = pd.DataFrame({"category": ["margin_observed_random_unresolved"]})
        bootstrap = {
            "mathematical_lower_bound_average_delta_Q": -0.1,
            "mathematical_lower_bound_delta_interval": {"one_sided_95pct_lower": -1.0},
        }
        decision = w9.query_claim_decision(paths, bootstrap, pairs)
        self.assertEqual(decision["status"], "NOT_SUPPORTED_NONPOSITIVE_LOWER_BOUND")
        self.assertFalse(decision["fixed_benchmark_lower_bound_positive"])

        bootstrap["mathematical_lower_bound_average_delta_Q"] = 4.4
        decision = w9.query_claim_decision(paths, bootstrap, pairs)
        self.assertEqual(decision["status"], "SUPPORTED_FIXED_BENCHMARK_ONLY")
        self.assertFalse(decision["design_conditional_bootstrap_lower_bound_positive"])

    def test_final_answers_include_budget40_and_conditional_pca_wording(self) -> None:
        with tempfile.TemporaryDirectory() as directory, mock.patch.object(w9, "OUTPUT", Path(directory)):
            output = Path(directory)
            rows = []
            for budget in (40, 80, 160, 320):
                for subset in ("full81", "B1_q30", "B1_q20"):
                    for estimand, value in (("binary_margin", .8), ("binary_random", .7), ("margin_minus_random", .1)):
                        rows.append({"budget": budget, "subset": subset, "metric": "accuracy", "estimand": estimand, "point_estimate": value, "two_sided_95pct_lower": value - .02, "two_sided_95pct_upper": value + .02})
            pd.DataFrame(rows).to_csv(output / "terminal_metric_summary.csv", index=False)
            pca = {
                "pc1_explained_variance": .3,
                "pc2_explained_variance": .2,
                "pc1_plus_pc2_explained_variance": .5,
                "variance_outside_pc1_pc2": .5,
                "pc1_dominant_loading": {"feature": "LS", "loading": .7},
                "pc2_dominant_loading": {"feature": "ST", "loading": .9},
                "component_interpretations": {
                    "PC1": {"short_interpretation": "LS versus P contrast", "explained_variance_ratio": .3},
                    "PC2": {"short_interpretation": "primarily ST variation", "explained_variance_ratio": .2},
                    "PC3": {"short_interpretation": "primarily VX variation", "explained_variance_ratio": .15},
                },
                "scaling_robustness": {"qualitative_agreement": "demo"},
                "representative_run_id": "demo",
                "representative_selection_is_label_informed": True,
                "slice_caveat": "projected hull only",
                "interpretation_diagnostics": {
                    "mean_opposite_label_fraction_by_representative_test_role": {"B1_q20": .2, "held_out_non_q30": .1},
                    "mean_opposite_label_fraction_by_margin_query_stage": {"acquired_17_40": .3, "acquired_161_320": .05},
                },
            }
            (output / "pca_summary.json").write_text(json.dumps(pca), encoding="utf-8")
            summary = {
                "horizon_results": [
                    {"horizon": 320, "arm": "binary_margin", "finite_persistent_crossings": 100, "unresolved": 0, "finite_rate": 1.0},
                    {"horizon": 320, "arm": "binary_random", "finite_persistent_crossings": 2800, "unresolved": 200, "finite_rate": 2800 / 3000},
                ],
                "query_bootstrap": {"restricted_margin_mean_Q": 50.0, "restricted_random_mean_Q": 70.0, "restricted_delta_Q": 20.0, "restricted_ratio": 1.4},
                "query_saving_claim": {"supervisor_safe_sentence": "Safe sentence."},
            }
            validation = {"status": "PASS", "checks": [{"status": "PASS", "check_id": "demo"}]}
            ledger = pd.DataFrame([{"category": "demo", "claim": "demo", "numeric_result": "demo", "status": "PASS", "strongest_safe_wording": "demo", "must_not_use": "demo"}])
            w9.write_final_reports(summary, validation, ledger)
            answers = pd.read_csv(output / "terminal_accuracy_answers.csv")
            supervisor = (output / "supervisor_summary.md").read_text(encoding="utf-8")
        self.assertEqual(sorted(answers.budget.unique().tolist()), [40, 80, 160, 320])
        self.assertIn("0.200 for q20 versus 0.100", supervisor)
        self.assertIn("label-informed", supervisor)


if __name__ == "__main__":
    unittest.main()
