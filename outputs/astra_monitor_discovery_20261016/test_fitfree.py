"""Tiny deterministic software checks. No model fit or synthetic trajectory run."""
from __future__ import annotations
from dataclasses import fields
import json
import math
from pathlib import Path
import time
import unittest
from discovery import Config, Predictions, Observation, SurpriseLocalDiscovery, maximin_start
from monitor_support import time_basis, time_summary, input_time_kernel
import ast
import tempfile
from run_pilot import check_reservation


class ContractTests(unittest.TestCase):
    def setUp(self):
        self.x = [(.4+i*.005, .5, .5, .5) for i in range(24)]

    def posterior(self, selector, mean=0., sd=.1):
        return Predictions("stub-paid-"+str(len(selector.paid)), len(selector.paid),
                           [mean]*len(self.x), [sd]*len(self.x), [0.]*len(self.x))

    def test_never_select_paid_or_twice_pending(self):
        s = SurpriseLocalDiscovery(self.x, [0, 1])
        c = s.ask(self.posterior(s))
        self.assertNotIn(c.index, (0, 1))
        with self.assertRaises(RuntimeError):
            s.ask(self.posterior(s))
        with self.assertRaises(ValueError):
            s.tell(Observation(0, 1., True, "ok"))

    def test_unpaid_information_not_in_interface(self):
        allowed = {f.name for f in fields(Predictions)}
        self.assertEqual(allowed, {"model_id", "paid_count", "mean", "latent_sd", "noise_sd", "aux_variance"})
        with self.assertRaises(TypeError):
            Predictions("bad", 0, (), (), (), short_k=[1])

    def test_precise_posterior_copy(self):
        means = [0.]*24
        p = Predictions("copy", 0, means, [1.]*24, [0.]*24)
        h = p.digest()
        means[0] = 100.
        self.assertEqual(p.mean[0], 0.)
        self.assertEqual(p.digest(), h)

    def test_stale_and_nonfinite_posterior_rejected(self):
        s = SurpriseLocalDiscovery(self.x, [0])
        with self.assertRaises(ValueError):
            s.ask(Predictions("stale", 0, [0.]*24, [1.]*24, [0.]*24))
        with self.assertRaises(ValueError):
            s.ask(Predictions("nan", 1, [float("nan")]*24, [1.]*24, [0.]*24))

    def test_surprise_uses_pre_observation_posterior(self):
        s = SurpriseLocalDiscovery(self.x)
        c = s.ask(self.posterior(s))
        e = s.tell(Observation(c.index, 1., True, "ok"))
        self.assertTrue(e["triggered"])
        self.assertAlmostEqual(e["raw_z"], 10.)
        c = s.ask(self.posterior(s, mean=1.))
        self.assertEqual(c.reason, "local_verify")
        # New fitted model would expect 1.0; the BEFORE-anchor reference did not.
        e = s.tell(Observation(c.index, 1., True, "ok"))
        self.assertAlmostEqual(e["raw_z"], 0.)
        self.assertTrue(e["corroborated_now"])

    def test_monitor_quality_cannot_trigger_and_cost_is_charged(self):
        for value, ok in ((1e9, False), (float("nan"), True), (None, False)):
            s = SurpriseLocalDiscovery(self.x)
            c = s.ask(self.posterior(s))
            e = s.tell(Observation(c.index, value, ok, "quality issue", 1))
            self.assertFalse(e["triggered"])
            self.assertIsNone(s.episode)
            self.assertIn(c.index, s.paid)
            self.assertEqual(e["canonical_label"], 1)
            json.dumps(e, allow_nan=False)

    def test_unconfirmed_episode_stops_after_two_checks(self):
        s = SurpriseLocalDiscovery(self.x)
        c = s.ask(self.posterior(s))
        s.tell(Observation(c.index, 1., True, "ok"))
        for _ in range(3):
            c = s.ask(self.posterior(s))
            e = s.tell(Observation(c.index, 0., True, "ok"))
        self.assertEqual(e["episode_ended"], "no_local_corroboration")
        self.assertIsNone(s.episode)

    def test_confirmed_episode_quota_and_global_exploration(self):
        s = SurpriseLocalDiscovery(self.x)
        c = s.ask(self.posterior(s))
        s.tell(Observation(c.index, 1., True, "ok"))
        reasons = []
        for _ in range(7):
            c = s.ask(self.posterior(s, mean=1.))
            reasons.append(c.reason)
            e = s.tell(Observation(c.index, 1., True, "ok"))
        self.assertEqual(sum(a.startswith("local_") for a in reasons), 4)
        self.assertEqual(reasons[3], "global_random")
        self.assertEqual(e["episode_ended"], "local_quota")
        self.assertIsNone(s.episode)

    def test_misscaled_uncertainty_guard_uses_past_only(self):
        s = SurpriseLocalDiscovery(self.x)
        s.global_residuals = [5., 5., 5., 5.]
        c = s.ask(self.posterior(s))
        e = s.tell(Observation(c.index, 100., True, "ok"))
        self.assertTrue(e["calibration_alert_before"])
        self.assertFalse(e["triggered"])
        self.assertAlmostEqual(e["scale_before"], 5/.6744897501960817)

    def test_ablation_identical_without_surprises(self):
        a = SurpriseLocalDiscovery(self.x, seed=19)
        b = SurpriseLocalDiscovery(self.x, seed=19, mode="straddle_global")
        for _ in range(12):
            ca, cb = a.ask(self.posterior(a)), b.ask(self.posterior(b))
            self.assertEqual(ca.index, cb.index)
            for s, c in ((a, ca), (b, cb)):
                s.tell(Observation(c.index, 0., True, "ok"))

    def test_noise_is_in_surprise_denominator(self):
        s = SurpriseLocalDiscovery(self.x)
        p = Predictions("noise", 0, [0.]*24, [.01]*24, [10.]*24)
        c = s.ask(p)
        e = s.tell(Observation(c.index, 1., True, "ok"))
        self.assertFalse(e["triggered"])

    def test_feature_only_start_reproducible(self):
        a = maximin_start(self.x, 8, 73)
        self.assertEqual(a, maximin_start(self.x, 8, 73))
        self.assertEqual(len(set(a)), 8)

    def test_auxiliary_variance_only_not_oracle(self):
        s = SurpriseLocalDiscovery(self.x, mode="multi_variance")
        p = Predictions("aux", 0, [0.]*24, [1.]*24, [0.]*24, [0.]*23+[2.])
        self.assertEqual(s.ask(p).index, 23)

    def test_radius_cannot_be_replaced_by_group_membership(self):
        s = SurpriseLocalDiscovery(self.x, config=Config(radius=.001))
        c = s.ask(self.posterior(s))
        s.tell(Observation(c.index, 1., True, "ok"))
        self.assertEqual(s.ask(self.posterior(s)).reason, "global_straddle")

    def test_correlated_bias_counterexample_is_not_a_physical_guarantee(self):
        # World A: true local shift. World B: the same reported shift is sensor bias.
        # Both pass an imperfect QA flag. The observations available to the policy
        # are identical, so it CANNOT distinguish their physical causes.
        a, b = SurpriseLocalDiscovery(self.x), SurpriseLocalDiscovery(self.x)
        for j in range(2):
            ca, cb = a.ask(self.posterior(a)), b.ask(self.posterior(b))
            self.assertEqual(ca.index, cb.index)
            ea = a.tell(Observation(ca.index, 1., True, "QA passed"))
            eb = b.tell(Observation(cb.index, 1., True, "QA passed"))
            self.assertEqual(ea, eb)
        self.assertTrue(ea["corroborated_now"])


class TimeTests(unittest.TestCase):
    def test_physical_duration_not_row_mean(self):
        q = time_summary([0., 1., 3.], [0., 2., 2.], planned_end_s=3., observed_end_s=3.,
                         threshold=1., max_gap_s=3.)
        self.assertAlmostEqual(q["time_mean"], 5/3)
        self.assertAlmostEqual(q["duration_above_s"], 2.5)

    def test_gap_and_nonfinite_never_bridged(self):
        q = time_summary([0., 1., 2., 3.], [0., 2., float("nan"), 4.],
                         planned_end_s=4., observed_end_s=3., max_gap_s=2.)
        self.assertEqual(q["valid_duration_s"], 1.)
        self.assertEqual(q["nonfinite_rows"], 1)
        self.assertEqual(q["missing_planned_duration_s"], 3.)
        self.assertTrue(q["truncated"])

    def test_time_basis_partition_and_no_extrapolation(self):
        for t in (0., .09, .18, .70, .9):
            b = time_basis(t)
            self.assertAlmostEqual(sum(b), 1.)
            self.assertTrue(all(v >= 0 for v in b))
        with self.assertRaises(ValueError):
            time_basis(.91)

    def test_kernel_is_symmetric_with_explicit_feature_map(self):
        x, z = [0.]*4, [.1]*4
        a = input_time_kernel(x, .1, z, .3)
        b = input_time_kernel(z, .3, x, .1)
        self.assertAlmostEqual(a, b)
        self.assertGreaterEqual(input_time_kernel(x, .1, x, .1), 0.)


class ExecutionGateTests(unittest.TestCase):
    def test_no_reservation_no_numerics(self):
        with self.assertRaises(RuntimeError):
            check_reservation(None, {"code_digest": "example"})

    def test_existing_pool_plan_without_new_grant_is_not_permission(self):
        with tempfile.TemporaryDirectory() as d:
            p = Path(d)/"record.json"
            p.write_text(json.dumps({"studies": [], "note": "idle machine"}))
            with self.assertRaises(RuntimeError):
                check_reservation(p, {"code_digest": "example"})

    def test_all_code_parses_without_importing_numerical_models(self):
        for p in Path(__file__).parent.glob("*.py"):
            ast.parse(p.read_text(encoding="utf-8"), filename=str(p))

    def test_selector_has_no_truth_or_file_access_imports(self):
        tree = ast.parse(Path(__file__).with_name("discovery.py").read_text(encoding="utf-8"))
        modules = []
        for item in ast.walk(tree):
            if isinstance(item, ast.Import):
                modules.extend(a.name for a in item.names)
            elif isinstance(item, ast.ImportFrom):
                modules.append(item.module)
        self.assertFalse(set(modules) & {"synthetic", "numpy", "pandas", "pathlib", "os"})


if __name__ == "__main__":
    started = time.perf_counter()
    result = unittest.TextTestRunner(verbosity=2).run(unittest.defaultTestLoader.loadTestsFromModule(__import__(__name__)))
    report = {"status": "PASS" if result.wasSuccessful() else "FAIL", "tests": result.testsRun,
              "failures": len(result.failures), "errors": len(result.errors),
              "elapsed_s": time.perf_counter()-started, "model_fits": 0,
              "synthetic_experiments": 0, "scope": "deterministic software contracts and hand-calculable time examples"}
    Path(__file__).with_name("FITFREE_CHECKS.json").write_text(json.dumps(report, indent=2)+"\n", encoding="utf-8")
    raise SystemExit(0 if result.wasSuccessful() else 1)
