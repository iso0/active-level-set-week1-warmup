from __future__ import annotations

import copy
import hashlib
import json
import shutil
import tarfile
import tempfile
import unittest
from pathlib import Path
from unittest import mock

import pandas as pd

from src import week8_5_frozen_sample_efficiency_confirmation as w85
from src import week9_phase1_horizon_extension as h320


class HorizonExtensionTests(unittest.TestCase):
    def test_extension_grid_is_exact(self) -> None:
        self.assertEqual(h320.extension_budgets(), list(range(164, 321, 4)))
        self.assertEqual(len(h320.extension_budgets()), 40)
        self.assertEqual(h320.PLANNED_MARGIN_FITS, 16100)
        self.assertEqual(h320.PLANNED_RANDOM_FITS_UPPER_BOUND, 22773)
        self.assertEqual(h320.PLANNED_TOTAL_FITS_UPPER_BOUND, 38873)
        with self.assertRaises(RuntimeError):
            h320.extension_budgets(160, 319, 4)

    def test_canonical_protocol_preflight_tolerates_checkout_line_endings(self) -> None:
        report = h320.validate_frozen_environment(check_archive=False)
        self.assertEqual(report["frozen_protocol_sha256"], h320.FROZEN_PROTOCOL_SHA256)
        self.assertEqual(report["frozen_source_hashes"], h320.FROZEN_SOURCE_HASHES)

    def test_extraction_repairs_same_size_corruption_by_sha256(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            destination = Path(directory) / "checkpoints"
            h320.extract_frozen_checkpoints(destination)
            target = sorted(destination.glob("*.json"))[0]
            original = target.read_bytes()
            replacement = bytes([original[0] ^ 1]) + original[1:]
            self.assertEqual(len(replacement), len(original))
            target.write_bytes(replacement)
            report = h320.extract_frozen_checkpoints(destination)
            self.assertEqual(target.read_bytes(), original)
            self.assertEqual(report["extracted_now"], 1)
            self.assertEqual(report["reused_by_sha256"], 3199)

    def test_frozen_random_confirmation_count_is_2493_of_3000(self) -> None:
        crossings = pd.read_csv(h320.FROZEN_OUTPUT / "query_crossings.csv")
        selected = crossings[
            crossings["arm"].eq("binary_random")
            & crossings["target"].eq(0.80)
            & crossings["boundary"].eq("B1")
            & crossings["quantile"].eq(20)
        ]
        self.assertEqual(len(selected), 3000)
        self.assertEqual(int(selected["event_observed"].sum()), 2493)

    def test_crossing_start_and_confirmation_are_distinct_for_horizon_censoring(self) -> None:
        rows = [
            {"budget": 192, h320.PRIMARY_METRIC: 0.70},
            {"budget": 196, h320.PRIMARY_METRIC: 0.80},
            {"budget": 200, h320.PRIMARY_METRIC: 0.85},
            {"budget": 204, h320.PRIMARY_METRIC: 0.90},
        ]
        evidence = h320.persistent_crossing_evidence(rows)
        self.assertEqual(evidence["start_budget"], 196)
        self.assertEqual(evidence["confirmation_budget"], 204)
        final = h320.finalize_crossing_classification(evidence, [], target_horizon=320)
        self.assertFalse(final["observed_by_horizon"]["200"])
        self.assertTrue(final["observed_by_horizon"]["240"])

    def test_real_frozen_random_payload_and_historical_prediction_recovery(self) -> None:
        population = w85.load_population()
        spec = w85.build_splits(population)[0]
        name = f"checkpoints/{h320.frozen_checkpoint_name(spec, 'binary_random', 1)}"
        with tarfile.open(h320.FROZEN_ARCHIVE, "r:gz") as archive:
            handle = archive.extractfile(name)
            self.assertIsNotNone(handle)
            raw = handle.read()
        payload = json.loads(raw)
        evidence = h320.validate_frozen_payload(payload, spec, "binary_random", 1, population)
        self.assertEqual(evidence["queried_count"], 160)
        self.assertEqual(evidence["mechanism_count"], 144)
        rows = h320.generate_prediction_rows(
            spec,
            "binary_random",
            1,
            40,
            payload,
            hashlib.sha256(raw).hexdigest(),
            population,
        )
        self.assertEqual(len(rows), 81)
        self.assertEqual({row["budget"] for row in rows}, {40})
        self.assertEqual({row["truth_has_keyhole"] for row in rows}, {0, 1})
        self.assertTrue(all(0.0 <= row["probability_has_keyhole"] <= 1.0 for row in rows))

    def test_random_continuation_matches_direct_frozen_engine_and_resumes(self) -> None:
        population, specs = w85.smoke_fixture()
        spec = specs[0]
        distances = w85.b1_distance(population)
        with tempfile.TemporaryDirectory() as source_dir, tempfile.TemporaryDirectory() as direct_dir, tempfile.TemporaryDirectory() as extension_dir:
            with mock.patch.object(w85, "protocol_sha256", return_value=h320.FROZEN_PROTOCOL_SHA256):
                source = w85.run_trajectory(
                    spec,
                    "binary_random",
                    1,
                    18,
                    population,
                    distances,
                    checkpoint_dir=Path(source_dir),
                )
                source_path = Path(source_dir) / w85.checkpoint_path(spec, "binary_random", 1).name
                source_sha = hashlib.sha256(source_path.read_bytes()).hexdigest()
                shutil.copy2(source_path, Path(direct_dir) / source_path.name)
                direct = w85.run_trajectory(
                    spec,
                    "binary_random",
                    1,
                    22,
                    population,
                    distances,
                    checkpoint_dir=Path(direct_dir),
                )
                extended = h320.continue_trajectory(
                    spec,
                    "binary_random",
                    1,
                    source,
                    source_sha,
                    population,
                    distances,
                    target_horizon=22,
                    checkpoint_step=1,
                    checkpoint_root=Path(extension_dir),
                )
                resumed = h320.continue_trajectory(
                    spec,
                    "binary_random",
                    1,
                    source,
                    source_sha,
                    population,
                    distances,
                    target_horizon=22,
                    checkpoint_step=1,
                    checkpoint_root=Path(extension_dir),
                )

        self.assertEqual(extended, resumed)
        self.assertEqual(extended["queried_indices"], direct["queried_indices"])
        retained_budgets = {row["budget"] for row in extended["extension_rows"]}
        direct_rows = [
            {key: value for key, value in row.items()}
            for row in direct["rows"]
            if row["budget"] in retained_budgets
        ]
        extension_rows = [
            {key: value for key, value in row.items() if key != "analysis_status"}
            for row in extended["extension_rows"]
        ]
        self.assertEqual(extension_rows, direct_rows)
        direct_mechanism = [row for row in direct["mechanism"] if row["selection_budget"] > 18]
        self.assertEqual(extended["extension_mechanism"], direct_mechanism)
        self.assertEqual(len(extended["terminal_prediction_rows"]), len(spec.test_indices))
        crossing = extended["persistent_crossing"]
        self.assertIn("start_budget", crossing)
        self.assertIn("confirmation_budget", crossing)

    def test_margin_crossing_metadata_updates_after_source_horizon(self) -> None:
        population, specs = w85.smoke_fixture()
        spec = specs[0]
        distances = w85.b1_distance(population)
        with tempfile.TemporaryDirectory() as source_dir, tempfile.TemporaryDirectory() as extension_dir:
            with mock.patch.object(w85, "protocol_sha256", return_value=h320.FROZEN_PROTOCOL_SHA256):
                source = w85.run_trajectory(
                    spec,
                    "binary_margin",
                    1,
                    18,
                    population,
                    distances,
                    checkpoint_dir=Path(source_dir),
                )
            for row in source["rows"]:
                row[h320.PRIMARY_METRIC] = 0.0
            source_sha = hashlib.sha256(json.dumps(source, sort_keys=True).encode()).hexdigest()

            original_metrics = w85.compute_metrics
            def passing_metrics(truth, probability, flag):
                result = original_metrics(truth, probability, flag)
                result["accuracy"] = 0.9
                return result

            with mock.patch.object(w85, "compute_metrics", side_effect=passing_metrics):
                extended = h320.continue_trajectory(
                    spec,
                    "binary_margin",
                    1,
                    source,
                    source_sha,
                    population,
                    distances,
                    target_horizon=22,
                    checkpoint_step=1,
                    checkpoint_root=Path(extension_dir),
                )

        crossing = extended["persistent_crossing"]
        self.assertTrue(crossing["observed"])
        self.assertEqual(crossing["start_budget"], 19)
        self.assertEqual(crossing["confirmation_budget"], 21)

    def test_completed_payload_validator_rejects_leakage_and_mechanism_tamper(self) -> None:
        population, specs = w85.smoke_fixture()
        spec = specs[0]
        distances = w85.b1_distance(population)
        with tempfile.TemporaryDirectory() as source_dir, tempfile.TemporaryDirectory() as extension_dir:
            with mock.patch.object(w85, "protocol_sha256", return_value=h320.FROZEN_PROTOCOL_SHA256):
                source = w85.run_trajectory(
                    spec, "binary_random", 1, 18, population, distances, checkpoint_dir=Path(source_dir)
                )
                source_path = Path(source_dir) / w85.checkpoint_path(spec, "binary_random", 1).name
                source_sha = hashlib.sha256(source_path.read_bytes()).hexdigest()
                extended = h320.continue_trajectory(
                    spec,
                    "binary_random",
                    1,
                    source,
                    source_sha,
                    population,
                    distances,
                    target_horizon=22,
                    checkpoint_step=1,
                    checkpoint_root=Path(extension_dir),
                )

        corrupt = copy.deepcopy(extended)
        corrupt["extension_mechanism"][0]["test_rows_available_to_acquisition"] = True
        with self.assertRaisesRegex(RuntimeError, "Test leakage flag"):
            h320.validate_completed_extension_payload(
                corrupt,
                source,
                source_sha,
                spec,
                "binary_random",
                1,
                population,
                checkpoints=list(range(19, 23)),
                target_horizon=22,
            )

    def test_historical_prefix_drift_fails_closed(self) -> None:
        population, specs = w85.smoke_fixture()
        spec = specs[0]
        distances = w85.b1_distance(population)
        with tempfile.TemporaryDirectory() as checkpoint_dir:
            with mock.patch.object(w85, "protocol_sha256", return_value=h320.FROZEN_PROTOCOL_SHA256):
                payload = w85.run_trajectory(
                    spec,
                    "binary_random",
                    1,
                    18,
                    population,
                    distances,
                    checkpoint_dir=Path(checkpoint_dir),
                )
        corrupt = copy.deepcopy(payload)
        corrupt["queried_indices"][0], corrupt["queried_indices"][1] = (
            corrupt["queried_indices"][1],
            corrupt["queried_indices"][0],
        )
        with self.assertRaisesRegex(RuntimeError, "initial-design prefix drift"):
            h320.validate_frozen_payload(
                corrupt,
                spec,
                "binary_random",
                1,
                population,
                source_horizon=18,
            )


if __name__ == "__main__":
    unittest.main()
