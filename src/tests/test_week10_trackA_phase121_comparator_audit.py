import json
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace

import numpy as np
import pandas as pd

from src import week10_trackA_phase121_comparator_audit as audit


class ComparatorAuditTests(unittest.TestCase):
    def test_protocol_is_frozen_and_parseable(self):
        payload = json.loads(audit.PROTOCOL.read_text(encoding="utf-8"))
        self.assertEqual(audit.sha256_file(audit.PROTOCOL), audit.PROTOCOL_SHA)
        self.assertEqual(payload["protocol_id"], "week10_trackA_phase121_comparator_audit/v1.0.0")

    def test_holm_adjustment(self):
        result = audit.holm_adjust({"a": 0.01, "b": 0.04})
        self.assertAlmostEqual(result["a"], 0.02)
        self.assertAlmostEqual(result["b"], 0.04)

    def test_primary_family_and_q30_secondary_are_locked(self):
        self.assertEqual(len(audit.NEW_PRIMARY_CONTRASTS), 2)
        self.assertIn(("B1_q30", "accuracy", 40), audit.ANALYSIS_ENDPOINTS)
        self.assertIn(("B1_q30", "balanced_accuracy", 40), audit.ANALYSIS_ENDPOINTS)

    def test_authoritative_a0_bundle_is_pinned(self):
        inputs = audit.additional_input_hashes()
        key = str(audit.A0_BUNDLE.relative_to(audit.ROOT)).replace("\\", "/")
        self.assertIn(key, inputs)
        self.assertEqual(inputs[key], audit.A0_BUNDLE_PUBLISHED_SHA256)

    def test_week85_protocol_semantics_match_recorded_canonical_hash(self):
        payload = json.loads(audit.W85_PROTOCOL_ORIGINAL.read_text(encoding="utf-8"))
        canonical = audit.w85.canonical_protocol_bytes(payload)
        recorded = audit.W85_PROTOCOL_SHA_RECORD.read_text(encoding="utf-8").split()[0]
        self.assertEqual(audit.hashlib.sha256(canonical).hexdigest(), recorded)

    def test_bootstrap_interval_is_deterministic(self):
        values = np.array([0.1, 0.2, 0.3, 0.4])
        self.assertEqual(audit.bootstrap_interval(values, 17), audit.bootstrap_interval(values, 17))

    def test_aulc_normalization(self):
        rows = []
        for budget in range(16, 41):
            for subset in ("full81", "B1_q30", "B1_q20"):
                rows.append({"policy": "p", "run_id": "r", "repeat": 1, "fold": 1,
                             "subset": subset, "budget": budget, "accuracy": 0.75,
                             "balanced_accuracy": 0.60})
        for budget in range(41, 81):
            for subset in ("full81", "B1_q30", "B1_q20"):
                rows.append({"policy": "p", "run_id": "r", "repeat": 1, "fold": 1,
                             "subset": subset, "budget": budget, "accuracy": 0.75,
                             "balanced_accuracy": 0.60})
        frame = audit.aulc_table(pd.DataFrame(rows))
        self.assertTrue(np.allclose(frame[frame.metric.eq("accuracy")].aulc, 0.75))
        self.assertTrue(np.allclose(frame[frame.metric.eq("balanced_accuracy")].aulc, 0.60))

    def test_sign_flip_detects_zero(self):
        values = np.array([1.0, -1.0] * 30)
        self.assertGreater(audit.sign_flip_p(values, 3), 0.9)

    def test_sidecar_reuse_is_fail_closed(self):
        with tempfile.TemporaryDirectory() as directory:
            checkpoint = Path(directory) / "checkpoint.json"
            expected = {"binding": "x"}
            checkpoint.write_text("payload", encoding="utf-8")
            with self.assertRaisesRegex(AssertionError, "partial checkpoint/sidecar pair"):
                audit.validate_sidecar(checkpoint, expected)
            audit.bind_checkpoint(checkpoint, expected)
            self.assertTrue(audit.validate_sidecar(checkpoint, expected))
            with self.assertRaisesRegex(AssertionError, "provenance drift"):
                audit.validate_sidecar(checkpoint, {"binding": "y"})

    def test_metric_metadata_and_row_counts_are_enforced(self):
        spec = SimpleNamespace(run_id="w85__r061_f01", repeat=61, fold=1)
        rows = []
        for budget in range(16, 81):
            for subset, count in (("full81", 81), ("B1_q30", 25), ("B1_q20", 17)):
                rows.append({"policy": "p", "run_id": spec.run_id, "repeat": 61, "fold": 1,
                             "budget": budget, "subset": subset, "accuracy": 0.5,
                             "balanced_accuracy": 0.5, "keyhole_recall": 0.5,
                             "conduction_recall": 0.5, "false_negative": 1, "false_positive": 1,
                             "true_negative": 1, "true_positive": 1, "row_count": count})
        audit.validate_metrics(rows, spec, "p")
        rows[0]["run_id"] = "wrong"
        with self.assertRaisesRegex(AssertionError, "metric run id drift"):
            audit.validate_metrics(rows, spec, "p")


if __name__ == "__main__":
    unittest.main()
