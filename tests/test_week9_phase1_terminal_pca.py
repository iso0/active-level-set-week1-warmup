import json
import tempfile
import unittest
from pathlib import Path

import numpy as np
import pandas as pd

from src import week8_5_frozen_sample_efficiency_confirmation as w85
from src import week9_phase1_terminal_pca as phase1


def synthetic_population(rows: int = 405) -> pd.DataFrame:
    rng = np.random.default_rng(91)
    x = rng.normal(size=(rows, 4))
    labels = ((0.9 * x[:, 0] - 0.7 * x[:, 1] + 0.35 * x[:, 2]) > 0.35).astype(int)
    return pd.DataFrame(
        {
            "P": x[:, 0],
            "VX": x[:, 1],
            "LS": x[:, 2],
            "ST": x[:, 3],
            "has_keyhole": labels,
            "experiment_name": [f"synthetic_{index:03d}" for index in range(rows)],
            "input_tuple_sha256": [f"group_{index:03d}" for index in range(rows)],
        }
    )


class TerminalMetricTests(unittest.TestCase):
    def test_classification_metrics_use_keyhole_as_positive_class(self) -> None:
        truth = np.array([0, 0, 0, 1, 1, 1])
        probability = np.array([0.1, 0.7, 0.2, 0.4, 0.8, 0.9])
        metrics = phase1.classification_metrics(truth, probability)
        self.assertAlmostEqual(metrics["accuracy"], 4 / 6)
        self.assertAlmostEqual(metrics["keyhole_recall"], 2 / 3)
        self.assertAlmostEqual(metrics["specificity"], 2 / 3)
        self.assertAlmostEqual(metrics["balanced_accuracy"], 2 / 3)
        self.assertEqual(metrics["false_negative"], 1)
        self.assertEqual(metrics["false_positive"], 1)

    def test_terminal_metrics_cover_full_q30_q20(self) -> None:
        truth = np.array(([0, 1] * 40) + [0])
        frame = pd.DataFrame(
            {
                "run_id": "run",
                "repeat": 1,
                "fold": 1,
                "arm": "binary_margin",
                "continuation_id": 1,
                "budget": 40,
                "manual_has_keyhole": truth,
                "probability_keyhole": np.where(truth == 1, 0.9, 0.1),
                "is_full81": True,
                "is_B1_q30": np.arange(81) < 25,
                "is_B1_q20": np.arange(81) < 17,
            }
        )
        metrics = phase1.terminal_metrics_from_predictions(frame)
        self.assertEqual(set(metrics["subset"]), set(phase1.SUBSETS))
        self.assertTrue(np.allclose(metrics["accuracy"], 1.0))
        self.assertEqual(int(metrics.set_index("subset").loc["full81", "row_count"]), 81)
        self.assertEqual(int(metrics.set_index("subset").loc["B1_q30", "row_count"]), 25)
        self.assertEqual(int(metrics.set_index("subset").loc["B1_q20", "row_count"]), 17)

    def test_random_is_averaged_within_fold_and_bootstrap_keeps_hierarchy(self) -> None:
        rows = []
        for repeat in (1, 2):
            for fold in (1, 2):
                base = {
                    "run_id": f"r{repeat}f{fold}",
                    "repeat": repeat,
                    "fold": fold,
                    "budget": 80,
                    "subset": "full81",
                    "true_negative": 50.0,
                    "true_positive": 10.0,
                    "row_count": 81.0,
                }
                rows.append(
                    {
                        **base,
                        "arm": "binary_margin",
                        "continuation_id": 1,
                        "accuracy": 0.8,
                        "balanced_accuracy": 0.75,
                        "keyhole_recall": 0.7,
                        "specificity": 0.8,
                        "false_negative": 3.0,
                        "false_positive": 4.0,
                    }
                )
                for continuation in range(1, 31):
                    rows.append(
                        {
                            **base,
                            "arm": "binary_random",
                            "continuation_id": continuation,
                            "accuracy": 0.6,
                            "balanced_accuracy": 0.55,
                            "keyhole_recall": 0.5,
                            "specificity": 0.6,
                            "false_negative": 6.0,
                            "false_positive": 8.0,
                        }
                    )
        path_metrics = pd.DataFrame(rows)
        fold = phase1.fold_level_terminal_metrics(path_metrics)
        random = fold[fold.arm.eq("binary_random")]
        self.assertTrue(np.allclose(random["accuracy"], 0.6))
        self.assertTrue((random["continuations_averaged_within_fold"] == 30).all())
        summary, draws = phase1.hierarchical_terminal_summary(path_metrics, draws=20, seed=3)
        contrast = summary.query("metric == 'accuracy' and estimand == 'margin_minus_random'").iloc[0]
        self.assertAlmostEqual(float(contrast["point_estimate"]), 0.2)
        self.assertTrue(np.allclose(draws["margin_minus_random"], draws["binary_margin"] - draws["binary_random"]))


class CheckpointAndPredictionTests(unittest.TestCase):
    @staticmethod
    def payload(horizon: int, offset: int = 0) -> dict:
        return {
            "complete": True,
            "horizon": horizon,
            "identity": {
                "run_id": "w85__r01_f01",
                "repeat": 1,
                "fold": 1,
                "arm": "binary_margin",
                "continuation_id": 1,
            },
            "queried_indices": list(range(offset, offset + horizon)),
            "rows": [],
            "mechanism": [],
        }

    def test_loader_prefers_highest_horizon_after_prefix_check(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "h160.json").write_text(json.dumps(self.payload(160)), encoding="utf-8")
            (root / "h320.json").write_text(json.dumps(self.payload(320)), encoding="utf-8")
            loaded = phase1.load_checkpoint_payloads([root])
            self.assertEqual(int(next(iter(loaded.values()))["horizon"]), 320)

    def test_loader_normalizes_real_like_week9_extension_and_embedded_predictions(self) -> None:
        extension = self.payload(320)
        extension.pop("horizon")
        extension.update(
            {
                "source_horizon": 160,
                "target_horizon": 320,
                "extension_rows": [{"budget": 164}, {"budget": 320}],
                "terminal_prediction_rows": [
                    {
                        "run_id": "w85__r01_f01",
                        "repeat": 1,
                        "fold": 1,
                        "arm": "binary_margin",
                        "continuation_id": 1,
                        "budget": 320,
                        "population_row_index": 17,
                        "truth_has_keyhole": 1,
                        "probability_has_keyhole": 0.73,
                    }
                ],
            }
        )
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            historical = root / "a_h160.json"
            week9 = root / "b_h320.json"
            historical.write_text(json.dumps(self.payload(160)), encoding="utf-8")
            week9.write_text(json.dumps(extension), encoding="utf-8")
            loaded = phase1.load_checkpoint_payloads([historical, week9])
        payload = next(iter(loaded.values()))
        self.assertEqual(payload["horizon"], 320)
        self.assertEqual(payload["effective_horizon_source"], "target_horizon")
        self.assertEqual(len(payload["queried_indices"]), 320)
        embedded = phase1.embedded_terminal_prediction_rows(loaded)
        self.assertEqual(int(embedded.iloc[0]["manual_has_keyhole"]), 1)
        self.assertAlmostEqual(float(embedded.iloc[0]["probability_keyhole"]), 0.73)
        self.assertEqual(embedded.iloc[0]["prediction_source"], "embedded_week9_terminal_prediction")

    def test_loader_fails_closed_on_trajectory_prefix_drift(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "a.json").write_text(json.dumps(self.payload(160)), encoding="utf-8")
            (root / "b.json").write_text(json.dumps(self.payload(320, offset=1)), encoding="utf-8")
            with self.assertRaisesRegex(RuntimeError, "prefix drift"):
                phase1.load_checkpoint_payloads([root])

    def test_minimal_extension_predictions_receive_exact_fold_local_flags(self) -> None:
        population = synthetic_population()
        spec = w85.SplitSpec(
            run_id="test_run",
            repeat=1,
            fold=1,
            train_indices=tuple(range(324)),
            test_indices=tuple(range(324, 405)),
        )
        test = np.asarray(spec.test_indices)
        minimal = pd.DataFrame(
            {
                "run_id": spec.run_id,
                "repeat": 1,
                "fold": 1,
                "arm": "binary_margin",
                "continuation_id": 1,
                "budget": 320,
                "population_row_index": test,
                "truth": population.loc[test, "has_keyhole"].to_numpy(),
                "probability": np.linspace(0.1, 0.9, 81),
            }
        )
        flagged = phase1.add_evaluation_flags(minimal, population, [spec])
        phase1.validate_prediction_rows(flagged, population, [spec])
        self.assertEqual(int(flagged["is_B1_q20"].sum()), 17)
        self.assertEqual(int(flagged["is_B1_q30"].sum()), 25)

    def test_horizon_prediction_aliases_are_normalized(self) -> None:
        frame = pd.DataFrame(
            {
                "run_id": ["run"],
                "repeat": [1],
                "fold": [1],
                "arm": ["binary_random"],
                "continuation_id": [4],
                "budget": [320],
                "population_row_index": [9],
                "truth_has_keyhole": [0],
                "probability_has_keyhole": [0.125],
            }
        )
        normalized = phase1.normalize_prediction_rows(frame)
        self.assertEqual(int(normalized.iloc[0]["manual_has_keyhole"]), 0)
        self.assertAlmostEqual(float(normalized.iloc[0]["probability_keyhole"]), 0.125)


class PCATests(unittest.TestCase):
    def test_pca_fit_is_label_independent_and_standardized(self) -> None:
        population = synthetic_population(120)
        first = phase1.fit_feature_only_pca(population)
        permuted = population.copy()
        permuted["has_keyhole"] = np.random.default_rng(7).permutation(permuted["has_keyhole"].to_numpy())
        second = phase1.fit_feature_only_pca(permuted)
        self.assertTrue(np.allclose(first.scores[["PC1", "PC2", "PC3", "PC4"]], second.scores[["PC1", "PC2", "PC3", "PC4"]]))
        self.assertTrue(np.allclose(first.loadings.drop(columns="feature"), second.loadings.drop(columns="feature")))
        standardized = first.scaler.transform(population.loc[:, phase1.FEATURES])
        self.assertTrue(np.allclose(standardized.mean(axis=0), 0.0, atol=1e-12))
        self.assertTrue(np.allclose(standardized.std(axis=0), 1.0, atol=1e-12))

    def test_representative_fold_selection_is_deterministic_and_not_visual(self) -> None:
        population = synthetic_population()
        specs = []
        indices = np.arange(405)
        for fold in range(1, 6):
            test = indices[(fold - 1) * 81 : fold * 81]
            train = np.setdiff1d(indices, test)
            specs.append(w85.SplitSpec(f"run_{fold}", 1, fold, tuple(train), tuple(test)))
        table_one, chosen_one = phase1.representative_fold_table(population, specs)
        table_two, chosen_two = phase1.representative_fold_table(population, list(reversed(specs)))
        self.assertEqual(chosen_one.run_id, chosen_two.run_id)
        self.assertEqual(int(table_one.q20_rows.min()), 17)
        self.assertEqual(int(table_one.q30_rows.max()), 25)
        self.assertTrue(table_one.selection_rule.str.contains("run_id tie-break", regex=False).all())
        pca = phase1.fit_feature_only_pca(population)
        diagnostic, summary = phase1.pca_interpretation_diagnostics(
            population,
            pca,
            chosen_one,
            {"queried_indices": list(chosen_one.train_indices[:160])},
        )
        self.assertEqual(int((diagnostic.representative_test_role == "B1_q20").sum()), 17)
        self.assertEqual(int(diagnostic.margin_query_number.notna().sum()), 160)
        self.assertEqual(summary["diagnostic_status"], "after-the-fact 2D projection interpretation only")


if __name__ == "__main__":
    unittest.main()
