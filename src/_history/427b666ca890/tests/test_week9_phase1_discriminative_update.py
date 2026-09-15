from __future__ import annotations

import unittest

import numpy as np
import pandas as pd
from sklearn.metrics import roc_auc_score

from src import week9_phase1_discriminative_update as update


class DiscriminativeUpdateTests(unittest.TestCase):
    def test_m3_preserves_hierarchy_and_adds_only_p_by_vx(self) -> None:
        z = np.arange(32, dtype=float).reshape(8, 4)
        design, names = update.make_design(z, "M3")
        self.assertEqual(names, ["P", "VX", "LS", "ST", "P×VX"])
        np.testing.assert_array_equal(design[:, :4], z)
        np.testing.assert_array_equal(design[:, 4], z[:, 0] * z[:, 1])

    def test_keyhole_process_score_formula_uses_ls_in_metres(self) -> None:
        population = pd.DataFrame(
            {
                "P": [200.0, 320.0],
                "VX": [0.5, 0.8],
                "LS": [50e-6, 80e-6],
                "ST": [300.0, 350.0],
            }
        )
        values, definitions = update.physical_scores(population)
        expected = population.P.to_numpy() / np.sqrt(
            population.VX.to_numpy() * population.LS.to_numpy() ** 3
        )
        np.testing.assert_allclose(values["keyhole_process_score_h__raw"], expected)
        row = definitions.set_index("score").loc["keyhole_process_score_h"]
        self.assertEqual(row["formula"], "P / √(VX·LS³)")
        self.assertFalse(bool(row["dimensionless"]))

    def test_auc_direction_is_fixed_before_bootstrap(self) -> None:
        y = np.array([0, 0, 0, 1, 1, 1])
        feature = np.array([6.0, 5.0, 4.0, 3.0, 2.0, 1.0])
        direction = -1.0 if roc_auc_score(y, feature) < 0.5 else 1.0
        indices = update.stratified_bootstrap_indices(y, draws=30, seed=19)
        bootstrapped = [roc_auc_score(y[index], direction * feature[index]) for index in indices]
        self.assertEqual(direction, -1.0)
        self.assertTrue(all(value == 1.0 for value in bootstrapped))

    def test_population_audit_uses_only_canonical_405_rows(self) -> None:
        population, summary, table = update.audit_population()
        self.assertEqual(len(population), 405)
        self.assertEqual(summary["keyhole"], 73)
        self.assertEqual(summary["conduction"], 332)
        self.assertTrue(summary["no_407_row_population_used"])
        ls = table.set_index("feature").loc["LS"]
        self.assertEqual(ls["reported_units"], "µm")
        self.assertGreater(float(ls["minimum"]), 35.0)
        self.assertLess(float(ls["maximum"]), 95.0)


if __name__ == "__main__":
    unittest.main()
