import csv
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace

import numpy as np
import pandas as pd

from src.external_validation import analysis, freeze, intake, reference_manifests, runner
from src.external_validation.common import ARMS, BUDGETS, PRIMARY, ReadinessError, encoded, sha


class MockEvaluator:
    def fit_predict(self, x, revealed, revealed_labels, train, predict, run_id, budget):
        self.last_label_count = len(revealed_labels)
        values = np.asarray(x)[np.asarray(predict), 0]
        probabilities = 1 / (1 + np.exp(-(values - np.median(np.asarray(x)[train, 0]))))
        return probabilities, {"mock": True, "revealed_label_count": len(revealed_labels)}, object()


class ExternalValidationReadinessTests(unittest.TestCase):
    def _csv(self, path, columns, rows):
        with Path(path).open("w", encoding="utf-8", newline="") as handle:
            writer = csv.DictWriter(handle, fieldnames=columns, lineterminator="\n")
            writer.writeheader()
            writer.writerows(rows)

    def _manifest_rows(self, prefix, count, offset):
        return [{"sim_id": f"{prefix}{i:04d}", "config_token": f"{prefix}-cfg-{i}",
                 "group_token": f"g{i:03d}", "P": 100 + offset + i,
                 "VX": 0.2 + (offset + i) / 1000, "LS": 0.00005 + i / 1e8,
                 "ST": 300 + (i % 20)} for i in range(count)]

    def _intake(self, root, new_rows):
        root = Path(root)
        manifest, old407, old405 = root / "manifest.csv", root / "old407.csv", root / "old405.csv"
        inventory, output = root / "inventory.csv", root / "intake.json"
        self._csv(manifest, intake.MANIFEST_COLUMNS, new_rows)
        self._csv(old407, intake.MANIFEST_COLUMNS, self._manifest_rows("a", 407, 10_000))
        self._csv(old405, intake.MANIFEST_COLUMNS, self._manifest_rows("b", 405, 20_000))
        files = [{"file_name": f"input-{i:04d}.dat", "sim_id": r["sim_id"], "kind": "input",
                  "byte_size": "10", "sha256": "a" * 64, "status": "ok"}
                 for i, r in enumerate(new_rows)]
        files.append({"file_name": "oracle.csv", "sim_id": "SEALED", "kind": "sealed_oracle",
                      "byte_size": "10", "sha256": "b" * 64, "status": "ok"})
        self._csv(inventory, intake.INVENTORY_COLUMNS, files)
        report = intake.intake(manifest, old407, old405, inventory, output,
            provenance={"source": "Ioan", "received_utc": "2026-10-01T00:00:00Z",
                        "simulator_version": "future-v1", "independence_evidence": "new campaign ledger"},
            units={"P": "W", "VX": "m/s", "LS": "m", "ST": "K"})
        return output, report

    def _decisions(self, rows):
        outputs = {name: f"run/{name}{freeze.OUTPUT_SUFFIXES[name]}" for name in freeze.OUTPUT_FIELDS}
        groups = [row["group_token"] for row in rows]
        assignments = []
        for repeat in (1, 2):
            assignments.append({"repeat": repeat, "folds": [
                {"fold": fold + 1, "test_group_tokens": groups[fold * 21:(fold + 1) * 21]}
                for fold in range(5)]})
        return {"owner": "protocol-owner", "grouping": "group_token",
                "split_construction": "PreassignedGroupFiveFold",
                "repeat_count": 2, "fold_count": 5, "random_seeds": [101, 202],
                "exact_feasible_budgets": BUDGETS,
                "paired_interval_method": analysis.SUPPORTED_INTERVAL,
                "failure_fallback_rules": dict(freeze.EXPECTED_FAILURE_RULES),
                "output_locations": outputs, "included_ids": [r["sim_id"] for r in rows],
                "owner_excluded_ids": [], "prelabel_fold_assignment": assignments}

    def test_normal_intake_inventory_overlap_and_shift_are_label_free(self):
        with tempfile.TemporaryDirectory() as directory:
            rows = self._manifest_rows("new", 105, 0)
            output, report = self._intake(directory, rows)
            self.assertEqual(report["blockers"], [])
            self.assertEqual(len(report["technically_usable_rows"]), 105)
            self.assertIn("P", report["range_and_shift"]["OLD-405"])
            self.assertEqual(Path(str(output) + ".sha256").read_text().strip(),
                             sha(output.read_bytes()))

    def test_canonical_old_reference_export_is_label_free(self):
        with tempfile.TemporaryDirectory() as directory:
            paths = reference_manifests.export(directory)
            old407 = pd.read_csv(paths["OLD-407"])
            old405 = pd.read_csv(paths["OLD-405"])
            self.assertEqual(list(old407.columns), list(intake.MANIFEST_COLUMNS))
            self.assertEqual((len(old407), len(old405)), (407, 405))
            self.assertNotIn("has_keyhole", old407.columns)

    def test_duplicate_ids_overlap_and_missing_feature_are_reported(self):
        with tempfile.TemporaryDirectory() as directory:
            rows = self._manifest_rows("new", 4, 0)
            rows[1]["sim_id"] = rows[0]["sim_id"]
            rows[2]["P"] = ""
            rows[3].update(self._manifest_rows("a", 1, 10_000)[0])
            _, report = self._intake(directory, rows)
            self.assertIn(rows[0]["sim_id"], report["duplicate_ids"])
            self.assertTrue(any("missing_or_invalid_feature" in x["reasons"]
                                for x in report["technical_exclusion_candidates"]))
            self.assertIn("OLD_POPULATION_OVERLAP_REQUIRES_PROVENANCE_RESOLUTION", report["blockers"])

    def test_unexpected_label_column_is_rejected_before_body_read(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "bad.csv"
            path.write_text("sim_id,config_token,group_token,P,VX,LS,ST,has_keyhole\n"
                            "n,c,g,1,1,1,1,SECRET_LABEL_BODY\n", encoding="utf-8")
            reader = intake.BlindReader([path])
            with self.assertRaisesRegex(ReadinessError, "Unexpected columns"):
                reader.csv(path, intake.MANIFEST_COLUMNS)
            self.assertEqual([x["phase"] for x in reader.audit], ["header"])
            self.assertLess(reader.audit[0]["bytes"], path.stat().st_size)

    def test_inventory_path_traversal_is_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            rows = self._manifest_rows("new", 3, 0)
            root = Path(directory)
            manifest, old407, old405 = root / "manifest.csv", root / "old407.csv", root / "old405.csv"
            inventory_path, output = root / "inventory.csv", root / "out.json"
            self._csv(manifest, intake.MANIFEST_COLUMNS, rows)
            self._csv(old407, intake.MANIFEST_COLUMNS, self._manifest_rows("a", 407, 10_000))
            self._csv(old405, intake.MANIFEST_COLUMNS, self._manifest_rows("b", 405, 20_000))
            files = [{"file_name": "../oracle.csv", "sim_id": "SEALED", "kind": "sealed_oracle",
                      "byte_size": "10", "sha256": "a" * 64, "status": "ok"}]
            files += [{"file_name": f"i{i}.dat", "sim_id": row["sim_id"], "kind": "input",
                       "byte_size": "10", "sha256": "b" * 64, "status": "ok"}
                      for i, row in enumerate(rows)]
            self._csv(inventory_path, intake.INVENTORY_COLUMNS, files)
            with self.assertRaisesRegex(ReadinessError, "traversal"):
                intake.intake(manifest, old407, old405, inventory_path, output,
                    provenance={"source": "x", "received_utc": "x", "simulator_version": "x",
                                "independence_evidence": "x"},
                    units={"P": "W", "VX": "m/s", "LS": "m", "ST": "K"})

    def test_freeze_requires_b80_and_exact_hash(self):
        with tempfile.TemporaryDirectory() as directory:
            rows = self._manifest_rows("new", 105, 0)
            intake_path, _ = self._intake(directory, rows)
            decisions = self._decisions(rows)
            decisions["included_ids"] = decisions["included_ids"][:80]
            decisions["owner_excluded_ids"] = [{"sim_id": r["sim_id"], "technical_reason": "synthetic"}
                                                for r in rows[80:]]
            with self.assertRaisesRegex(ReadinessError, "B80 is impossible"):
                freeze.build_addendum(intake_path, decisions)
            decisions = self._decisions(rows)
            target = Path(directory) / "frozen"
            freeze.generate(intake_path, target, decisions)
            sealed = freeze.verify(target / "EXTERNAL_BATCH_FREEZE.json")
            self.assertEqual(sealed["arms"], list(ARMS))
            self.assertEqual(sealed["minimum_training_pool_size"], 84)
            self.assertEqual(len(runner.build_splits([r["group_token"] for r in rows], sealed)), 10)
            (target / "EXTERNAL_BATCH_FREEZE.sha256").write_text("bad\n", encoding="ascii")
            with self.assertRaisesRegex(ReadinessError, "Malformed"):
                freeze.verify(target / "EXTERNAL_BATCH_FREEZE.json")

    def test_freeze_carries_every_intake_technical_exclusion(self):
        with tempfile.TemporaryDirectory() as directory:
            rows = self._manifest_rows("new", 106, 0)
            rows[-1]["P"] = ""
            intake_path, report = self._intake(directory, rows)
            usable = report["technically_usable_rows"]
            sealed = freeze.build_addendum(intake_path, self._decisions(usable))
            self.assertEqual(len(sealed["included_ids"]), 105)
            self.assertEqual(len(sealed["excluded_rows"]), 1)
            self.assertEqual(len(sealed["original_manifest_ids"]), 106)
            self.assertIn("missing_or_invalid_feature", sealed["excluded_rows"][0]["technical_reasons"])

    def test_runner_rejects_policy_endpoint_override_and_b16_class_failure(self):
        frozen = {"arms": list(ARMS), "primary_endpoint": PRIMARY,
                  "exact_feasible_budgets": BUDGETS}
        x = np.arange(420, dtype=float).reshape(105, 4) + 1
        labels = (x[:, 0] > np.median(x[:, 0])).astype(int)
        split = [{"split_id": "s", "repeat": 1, "fold": 1,
                  "train_indices": list(range(85)), "test_indices": list(range(85, 105)),
                  "split_seed": 7}]
        with self.assertRaisesRegex(ReadinessError, "policy override"):
            runner.run_locked(x, list(map(str, range(105))), labels, split, frozen,
                              MockEvaluator(), arms=ARMS[:2])
        with self.assertRaisesRegex(ReadinessError, "endpoint override"):
            runner.run_locked(x, list(map(str, range(105))), labels, split, frozen,
                              MockEvaluator(), primary_endpoint="q30")
        with self.assertRaisesRegex(ReadinessError, "lacks both classes"):
            runner._starting_path(ARMS[0], list(range(16)), np.zeros(20, int))

    def test_candidate_b_reads_seed_labels_only_as_revealed(self):
        class Spy:
            def __init__(self, values):
                self.values, self.accessed = values, []
            def __getitem__(self, index):
                self.accessed.append(int(index))
                return self.values[index]
        labels = Spy([0] * 10 + [1] + [0] * 9)
        path = runner._starting_path(ARMS[1], list(range(16)), labels)
        self.assertEqual(path, list(range(11)))
        self.assertEqual(labels.accessed, list(range(11)))

    def test_external_maximin_matches_frozen_seed_namespace(self):
        rng = np.random.default_rng(31)
        x = rng.uniform([100, .2, .00004, 290], [400, 2, .00012, 600], size=(105, 4))
        labels = (x[:, 0] > np.median(x[:, 0])).astype(int)
        population = pd.DataFrame(x, columns=("P", "VX", "LS", "ST"))
        population["has_keyhole"] = labels
        split = {"split_id": "external__r001_f01", "split_seed": 101}
        spec = SimpleNamespace(run_id=split["split_id"], train_indices=tuple(range(84)))
        frozen = {"initial_design_seed_namespace":
                  "w85.seed_u32(w85.seed_key('run',split_id,'initial_design'))"}
        ours = runner.feature_only_maximin(x, spec.train_indices, runner._initial_seed(frozen, split))
        historical = runner.bind_real_implementations()["w85"].initial_design(spec, population)
        self.assertEqual(ours, historical)

    def test_mock_three_arm_dry_run_preserves_paths_predictions_and_diagnostics(self):
        rng = np.random.default_rng(9)
        x = rng.uniform([100, .2, .00004, 290], [400, 2, .00012, 600], size=(105, 4))
        labels = (x[:, 0] > np.median(x[:, 0])).astype(int)
        frozen = {"arms": list(ARMS), "primary_endpoint": PRIMARY,
                  "exact_feasible_budgets": BUDGETS}
        split = [{"split_id": "s", "repeat": 1, "fold": 1,
                  "train_indices": list(range(85)), "test_indices": list(range(85, 105)),
                  "split_seed": 7}]
        result = runner.run_locked(x, [f"s{i}" for i in range(105)], labels, split,
                                   frozen, MockEvaluator())
        self.assertEqual(result["arms"], list(ARMS))
        self.assertEqual(len(result["predictions"]), 3 * 65 * 20)
        for arm in ARMS:
            path = [r for r in result["paths"] if r["arm"] == arm]
            self.assertEqual(len(path), 80)
            self.assertEqual(len({r["row_index"] for r in path}), 80)
        self.assertTrue(result["fit_diagnostics"])

    def test_fatal_runner_error_returns_preserved_partial_artifacts(self):
        class FailingEvaluator(MockEvaluator):
            def __init__(self): self.calls = 0
            def fit_predict(self, *args, **kwargs):
                self.calls += 1
                if self.calls == 2:
                    raise RuntimeError("synthetic fit failure")
                return super().fit_predict(*args, **kwargs)
        rng = np.random.default_rng(23)
        x = rng.uniform([100, .2, .00004, 290], [400, 2, .00012, 600], size=(105, 4))
        labels = (x[:, 0] > np.median(x[:, 0])).astype(int)
        split = [{"split_id": "s", "repeat": 1, "fold": 1,
                  "train_indices": list(range(85)), "test_indices": list(range(85, 105)),
                  "split_seed": 7}]
        frozen = {"arms": list(ARMS), "primary_endpoint": PRIMARY,
                  "exact_feasible_budgets": BUDGETS}
        result = runner.run_locked(x, [f"s{i}" for i in range(105)], labels, split,
                                   frozen, FailingEvaluator())
        self.assertFalse(result["complete"])
        self.assertTrue(result["paths"] and result["predictions"] and result["fit_diagnostics"])
        self.assertEqual(result["failures"][0]["event"], "STOP")

    def test_oracle_digest_and_size_are_enforced(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "oracle.csv"
            payload = b"sim_id,has_keyhole\ns1,0\ns2,1\n"
            path.write_bytes(payload)
            frozen = {"sealed_oracle_inventory": {"file_name": path.name,
                      "byte_size": str(len(payload)), "sha256": sha(payload)},
                      "original_manifest_ids": ["s1", "s2"],
                      "included_ids": ["s1", "s2"]}
            self.assertEqual(runner.open_oracle(path, frozen), {"s1": 0, "s2": 1})
            frozen["included_ids"] = ["s1"]  # s2 is a known technical exclusion; original oracle stays sealed.
            self.assertEqual(runner.open_oracle(path, frozen), {"s1": 0})
            frozen["sealed_oracle_inventory"]["sha256"] = "0" * 64
            with self.assertRaisesRegex(ReadinessError, "size or SHA-256"):
                runner.open_oracle(path, frozen)

    def test_test_label_counterfactual_cannot_change_selection_paths(self):
        rng = np.random.default_rng(19)
        x = rng.uniform([100, .2, .00004, 290], [400, 2, .00012, 600], size=(105, 4))
        labels = (x[:, 0] > np.median(x[:, 0])).astype(int)
        split = [{"split_id": "s", "repeat": 1, "fold": 1,
                  "train_indices": list(range(85)), "test_indices": list(range(85, 105)),
                  "split_seed": 17}]
        frozen = {"arms": list(ARMS), "primary_endpoint": PRIMARY,
                  "exact_feasible_budgets": BUDGETS}
        first = runner.run_locked(x, [f"s{i}" for i in range(105)], labels, split,
                                  frozen, MockEvaluator())
        changed = labels.copy()
        changed[85:] = 1 - changed[85:]
        second = runner.run_locked(x, [f"s{i}" for i in range(105)], changed, split,
                                   frozen, MockEvaluator())
        key = lambda result: [(r["arm"], r["query_order"], r["row_index"]) for r in result["paths"]]
        self.assertEqual(key(first), key(second))
        changed_x = x.copy()
        changed_x[85:] *= 1000
        third = runner.run_locked(changed_x, [f"s{i}" for i in range(105)], labels, split,
                                  frozen, MockEvaluator())
        self.assertEqual(key(first), key(third))

    def test_locked_analysis_separates_all_three_claims(self):
        rng = np.random.default_rng(4)
        x = rng.uniform([100, .2, .00004, 290], [400, 2, .00012, 600], size=(100, 4))
        labels = np.array([0, 1] * 50)
        sim_ids = [f"s{i:03d}" for i in range(100)]
        splits, predictions = [], []
        for repeat in (1, 2):
            for fold in range(1, 6):
                sid = f"r{repeat}f{fold}"
                test_indices = list(range((fold - 1) * 20, fold * 20))
                splits.append({"split_id": sid, "repeat": repeat, "fold": fold,
                               "train_indices": [i for i in range(100) if i not in set(test_indices)],
                               "test_indices": test_indices})
                for arm in ARMS:
                    for budget in BUDGETS:
                        for row in test_indices:
                            truth = labels[row]
                            if arm == ARMS[1]:
                                probability = .9 if truth else .1
                            elif arm == ARMS[2]:
                                probability = .8 if truth else .2
                            else:
                                probability = (.6 if truth else .4) if row % 4 else (.4 if truth else .6)
                            predictions.append({"split_id": sid, "repeat": repeat, "fold": fold,
                                "arm": arm, "budget": budget, "row_index": row,
                                "sim_id": sim_ids[row], "truth": int(truth),
                                "probability": probability})
        run = {"arms": list(ARMS), "primary_endpoint": PRIMARY, "complete": True,
               "split_manifest": splits, "predictions": predictions, "failures": []}
        frozen = {"paired_interval_method": analysis.SUPPORTED_INTERVAL,
                  "q20_scaling_scope": analysis.SUPPORTED_Q_SCALING}
        missing = {**run, "predictions": predictions[:-1]}
        with self.assertRaisesRegex(ReadinessError, "Incomplete (arm/fold/budget|held-out)"):
            analysis.metrics_from_predictions(missing, x, labels, sim_ids, frozen)
        duplicated = {**run, "predictions": predictions + [dict(predictions[0])]}
        with self.assertRaisesRegex(ReadinessError, "Duplicate per-test-ID"):
            analysis.metrics_from_predictions(duplicated, x, labels, sim_ids, frozen)
        nonfinite_rows = [dict(row) for row in predictions]
        nonfinite_rows[0]["probability"] = float("nan")
        with self.assertRaisesRegex(ReadinessError, "Nonfinite prediction"):
            analysis.metrics_from_predictions({**run, "predictions": nonfinite_rows},
                                              x, labels, sim_ids, frozen)
        out_of_range = [dict(row) for row in predictions]
        out_of_range[0]["probability"] = 1.1
        with self.assertRaisesRegex(ReadinessError, "outside"):
            analysis.metrics_from_predictions({**run, "predictions": out_of_range},
                                              x, labels, sim_ids, frozen)
        wrong_truth = [dict(row) for row in predictions]
        wrong_truth[0]["truth"] = 1 - wrong_truth[0]["truth"]
        with self.assertRaisesRegex(ReadinessError, "IDs/truth"):
            analysis.metrics_from_predictions({**run, "predictions": wrong_truth},
                                              x, labels, sim_ids, frozen)
        result = analysis.analyze(run, x, labels, sim_ids, frozen)
        self.assertEqual(set(result["claim_ledger"]), {"primary_endpoint", "external_confirmation",
                         "incumbent_replacement", "pure_acquisition_attribution", "failures"})
        self.assertTrue(result["claim_ledger"]["external_confirmation"]["pass"])
        self.assertTrue(result["claim_ledger"]["pure_acquisition_attribution"]["pass"])
        counterfactual = result["contrasts"].copy()
        mask = ((counterfactual.endpoint == "q20_accuracy_AULC_B16_B80") &
                (counterfactual.role == "challenger_vs_control"))
        counterfactual.loc[mask, ["mean_difference", "ci95_lower"]] = [0.001, -0.001]
        ledger = analysis.claim_ledger(counterfactual, [])
        self.assertFalse(ledger["external_confirmation"]["pass"])
        self.assertTrue(ledger["pure_acquisition_attribution"]["same_B16_positive_evidence"])
        self.assertFalse(ledger["pure_acquisition_attribution"]["pass"])

    def test_real_frozen_modules_import_and_bind(self):
        bound = runner.bind_real_implementations()
        self.assertEqual(set(bound), {"w85", "p11", "p13", "search", "p121"})

    def test_real_m3_small_synthetic_fit(self):
        rng = np.random.default_rng(121)
        x = rng.uniform([100, .2, .00004, 290], [400, 2, .00012, 600], size=(24, 4))
        probability, diagnostic, _ = runner.FrozenM3Evaluator().fit_predict(
            x, np.arange(16), np.arange(16) % 2, np.arange(20), np.arange(20, 24), "smoke", 16)
        self.assertTrue(np.isfinite(probability).all())
        self.assertTrue(((probability > 0) & (probability < 1)).all())
        self.assertIn("fallback_status", diagnostic)

    def test_cli_synthetic_dry_run_end_to_end(self):
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory) / "evidence.json"
            completed = subprocess.run(
                [sys.executable, "-m", "src.external_validation.cli", "synthetic-dry-run",
                 "--output", str(output)], cwd=Path(__file__).resolve().parents[2],
                capture_output=True, text=True)
            self.assertEqual(completed.returncode, 0, completed.stderr)
            evidence = json.loads(output.read_text(encoding="utf-8"))
            self.assertEqual(evidence["status"], "PASS")
            self.assertEqual(evidence["data"], "FAKE_SYNTHETIC_ONLY")
            self.assertEqual(evidence["splits"], 10)


if __name__ == "__main__":
    unittest.main()
