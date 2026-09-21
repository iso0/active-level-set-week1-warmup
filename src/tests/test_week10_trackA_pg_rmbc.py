from __future__ import annotations

import unittest

import numpy as np
import pandas as pd

from src import week10_trackA_pg_rmbc as study


class TestWeek10PGRMBC(unittest.TestCase):
    def test_h_maximin_order_is_deterministic_and_row_tied(self):
        logh = np.array([0.0, 1.0, 0.5, 0.5, 0.25])
        train = [4, 3, 2, 1, 0]
        order = study.h_maximin_order(logh, train)
        self.assertEqual(order[:2], [0, 1])
        self.assertEqual(order[2], 2)  # row 2 wins the exact row-2/row-3 tie
        self.assertEqual(order, study.h_maximin_order(logh, train))
        self.assertEqual(set(order), set(train))

    def test_seed_until_both_never_infers(self):
        order = [0, 1, 2, 3]
        labels = np.array([0, 0, 1, 1])
        self.assertEqual(study.seed_until_both(order, labels, 2), [0, 1, 2])

    def test_dominance_ignores_ST_and_is_strict(self):
        frame = pd.DataFrame({
            "P": [1.0, 2.0, 2.0], "VX": [2.0, 1.0, 1.0],
            "LS": [2.0, 1.0, 1.0], "ST": [100.0, -999.0, 999.0],
        })
        dom = study.dominance_matrix(frame)
        self.assertTrue(dom[0, 1])
        self.assertTrue(dom[0, 2])
        self.assertFalse(dom[1, 2])  # identical P/VX/LS despite different ST
        self.assertFalse(np.diag(dom).any())

    def test_robust_leverage_counts_only_relevant_candidates(self):
        frame = pd.DataFrame({
            "P": [1, 2, 3, 4], "VX": [4, 3, 2, 1], "LS": [4, 3, 2, 1], "ST": [0, 0, 0, 0],
        })
        dom = study.dominance_matrix(frame)
        cand = np.array([0, 1, 2])  # row 3 is deliberately irrelevant
        g_kh, g_c, robust = study.leverage_counts(cand, cand, dom)
        np.testing.assert_array_equal(g_kh, [2, 1, 0])
        np.testing.assert_array_equal(g_c, [0, 1, 2])
        np.testing.assert_array_equal(robust, [0, 1, 0])

    def test_separability_has_required_direction(self):
        logh = np.array([0.0, 1.0, 2.0, 3.0])
        labels = np.array([0, 0, 1, 1])
        self.assertTrue(study.is_h_separable([0, 1, 2, 3], labels, logh))
        labels[1] = 1
        labels[2] = 0
        self.assertFalse(study.is_h_separable([0, 1, 2, 3], labels, logh))

    def test_rank_normalization_matches_phase121(self):
        values = np.array([0.2, 0.2, 0.9, 0.1])
        np.testing.assert_array_equal(study.rank01(values), study.search._rank01(values))

    def test_probability_disagreement_does_not_enter_score_source(self):
        source = study.inspect.getsource(study.choose_band)
        score_line = [line for line in source.splitlines() if "score =" in line]
        self.assertTrue(score_line)
        self.assertTrue(all("disagreement" not in line for line in score_line))

    def test_only_five_policies_are_declared(self):
        self.assertEqual(len(study.POLICIES), 5)
        self.assertEqual(study.POLICIES, (study.P0, study.P1, study.P2, study.P3, study.P4))


if __name__ == "__main__":
    unittest.main()
