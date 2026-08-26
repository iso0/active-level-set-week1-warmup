from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

import numpy as np
import pandas as pd

from src import week8_5_frozen_sample_efficiency_confirmation as w85


class FrozenConfirmationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.population = w85.load_population()
        cls.specs = w85.build_splits(cls.population)
        cls.distances = w85.b1_distance(cls.population)

    def test_seed_derivation_and_namespace_are_exact(self) -> None:
        key = "week8_5_frozen_confirmation|v1|outer_split|repeat|01"
        self.assertEqual(w85.seed_key("outer_split", "repeat", "01"), key)
        self.assertEqual(w85.seed_u32(key), w85.seed_u32(key))
        self.assertFalse(any(old in key for old in ("6022026", "primary_common", "shared_pool_permutation")))

    def test_chooser_source_excludes_evaluation_and_hidden_label_inputs(self) -> None:
        valid, evidence = w85.audit_chooser_source()
        self.assertTrue(valid)
        self.assertEqual(evidence["chooser_keyword_arguments"], ["candidate_indices", "method", "pool_scaled", "probabilities", "queried_indices"])

    def test_seed_collision_audit_qualifies_fit_uint32_but_preserves_random_orders(self) -> None:
        frame = pd.DataFrame(
            [
                {"seed_kind": "fit", "seed_key": "fit|one", "seed_u32": 17},
                {"seed_kind": "fit", "seed_key": "fit|two", "seed_u32": 17},
                *[{"seed_kind": "random_order", "seed_key": f"order|{index}", "seed_u32": index} for index in range(3000)],
            ]
        )
        random_ok, evidence = w85.audit_seed_registry(frame)
        self.assertTrue(random_ok)
        self.assertEqual(evidence["fit_seed_collision_group_count"], 1)
        self.assertEqual(evidence["fit_seed_collisions"][0]["distinct_seed_keys"], ["fit|one", "fit|two"])

    def test_saved_mechanism_audit_uses_persisted_split_manifest(self) -> None:
        checkpoint = next(w85.CHECKPOINT_ROOT.glob("w85__r01_f01__binary_margin__c01.json"))
        valid, evidence = w85.audit_information_flow_artifacts(self.specs, [checkpoint])
        self.assertTrue(valid)
        self.assertEqual(evidence["checkpoint_count"], 1)
        self.assertEqual(evidence["saved_mechanism_record_count"], 144)
        self.assertTrue(evidence["candidate_and_query_indices_training_only"])

    def test_repulsion_mechanism_derivative_schema_and_counts(self) -> None:
        valid, evidence = w85.audit_repulsion_mechanism_derivatives()
        self.assertTrue(valid)
        self.assertEqual(evidence["diagnostic_row_count"], 28800)
        self.assertEqual(evidence["rows_by_arm"], {"binary_margin": 14400, "binary_uncertainty_repulsion": 14400})
        self.assertTrue(evidence["nearest_distance_non_missing"])

    def test_protocol_is_canonical_and_hashed(self) -> None:
        self.assertEqual(w85.protocol_sha256(), "bb16865a06d8fbdeea00f8c41f0929bfb7fbaf2f7b3e4ebade9cb2ffc59b1c66")

    def test_split_membership_group_disjointness_and_boundary_counts(self) -> None:
        self.assertEqual(len(self.specs), 100)
        for spec in self.specs:
            self.assertEqual(len(spec.train_indices), 324)
            self.assertEqual(len(spec.test_indices), 81)
            self.assertTrue(set(spec.train_indices).isdisjoint(spec.test_indices))
            train_groups = set(self.population.iloc[list(spec.train_indices)].input_tuple_sha256)
            test_groups = set(self.population.iloc[list(spec.test_indices)].input_tuple_sha256)
            self.assertTrue(train_groups.isdisjoint(test_groups))
            flags = w85.boundary_flags(spec, self.population, self.distances)
            self.assertEqual(int(flags["B1_q20"].sum()), 17)
            self.assertEqual(int(flags["B1_q30"].sum()), 25)

    def test_initial_design_is_deterministic_arm_matched_and_both_classes(self) -> None:
        for spec in self.specs:
            first = w85.initial_design(spec, self.population)
            self.assertEqual(first, w85.initial_design(spec, self.population))
            self.assertEqual(len(first), 16)
            self.assertEqual(len(set(first)), 16)
            self.assertTrue(set(first).issubset(spec.train_indices))
            self.assertEqual(self.population.iloc[first].has_keyhole.nunique(), 2)

    def test_aulc_uses_historical_orientation_and_integer_grid(self) -> None:
        budgets = np.arange(16, 81)
        frame = pd.DataFrame({"budget": budgets, "metric": budgets.astype(float)})
        self.assertEqual(w85.aulc(frame, "metric", 16, 80), 48.0)

    def test_persistent_crossing_and_right_censoring(self) -> None:
        frame = pd.DataFrame({"budget": [16, 17, 18, 19, 20], "metric": [.7, .8, .81, .82, .79]})
        crossing, observed = w85.persistent_crossing(frame, "metric", .8)
        self.assertTrue(observed)
        self.assertEqual(crossing, 17)
        crossing, observed = w85.persistent_crossing(frame, "metric", .85)
        self.assertFalse(observed)
        self.assertTrue(np.isnan(crossing))

    def test_random_order_information_flow_and_checkpoint_resume(self) -> None:
        population, specs = w85.smoke_fixture()
        distances = w85.b1_distance(population)
        with tempfile.TemporaryDirectory() as first_dir, tempfile.TemporaryDirectory() as second_dir:
            one = w85.run_trajectory(specs[0], "binary_random", 1, 18, population, distances, checkpoint_dir=Path(first_dir))
            two = w85.run_trajectory(specs[0], "binary_random", 1, 18, population, distances, checkpoint_dir=Path(second_dir))
            resumed = w85.run_trajectory(specs[0], "binary_random", 1, 18, population, distances, checkpoint_dir=Path(first_dir))
            self.assertEqual(one, two)
            self.assertEqual(one, resumed)
            train = set(specs[0].train_indices)
            test = set(specs[0].test_indices)
            selected = {row["selected_population_row_index"] for row in one["mechanism"]}
            self.assertTrue(selected.issubset(train))
            self.assertTrue(selected.isdisjoint(test))
            self.assertTrue(all(not row["test_rows_available_to_acquisition"] for row in one["mechanism"]))
            self.assertTrue(all(not row["hidden_pool_labels_available_to_acquisition"] for row in one["mechanism"]))
            self.assertTrue(all(not row["B1_available_to_acquisition"] for row in one["mechanism"]))


if __name__ == "__main__":
    unittest.main(verbosity=2)
