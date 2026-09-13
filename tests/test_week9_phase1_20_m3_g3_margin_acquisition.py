"""Information-boundary, tie-breaking and metric tests (no new model code)."""
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import numpy as np
import pandas as pd
from sklearn.preprocessing import StandardScaler

from src import week9_phase1_20_m3_g3_margin_acquisition as p
from src.week9_phase1_20_analysis import metrics_from_predictions


class Phase120Tests(unittest.TestCase):
    def test_selector_receives_only_revealed_labels_and_train_scaled_features(self):
        rng = np.random.default_rng(73)
        features = rng.normal(size=(324,4))
        ids = np.arange(324)[::-1] + 1000
        revealed = ids[:16]
        labels = np.arange(16) % 2
        scaled = StandardScaler().fit_transform(features)
        with patch.object(p.p12, 'fit_gpc_model', return_value=(object(),{})) as fit:
            # Equal scores: smallest population index must win despite reversed pool order.
            with patch.object(p.p12, 'predict_positive', return_value=np.full(308,.5)):
                chosen,candidates,probability,_ = p.select_g3(features,ids,revealed,labels,'test',16)
        self.assertEqual(chosen,1000)
        np.testing.assert_array_equal(fit.call_args.args[2],labels)
        np.testing.assert_allclose(fit.call_args.args[1],scaled[:16])
        self.assertEqual(len(candidates),308)
        self.assertTrue(set(candidates).isdisjoint(revealed))

    def test_selector_rejects_hidden_label_vector(self):
        with self.assertRaisesRegex(RuntimeError,'revealed only'):
            p.select_g3(np.zeros((324,4)),np.arange(324),list(range(16)),np.zeros(324),'test',16)

    def test_metric_class_balance_and_threshold(self):
        frame=pd.DataFrame({'run_id':['r']*6,'repeat':[1]*6,'fold':[1]*6,'model':['P2']*6,
                            'budget':[16]*6,'truth':[0,0,0,0,1,1],
                            'probability':[.2,.3,.4,.5,.2,.8],'is_q20':[True]*6,'is_q30':[True]*6})
        result=metrics_from_predictions(frame)
        self.assertTrue((result.false_negative==1).all())
        self.assertTrue((result.false_positive==1).all())
        np.testing.assert_allclose(result.balanced_accuracy,.625)
        np.testing.assert_allclose(result.accuracy,4/6)

    def test_atomic_checkpoint_roundtrip(self):
        with tempfile.TemporaryDirectory() as directory:
            path=Path(directory)/'run.json.gz'
            p.atomic_checkpoint(path,{'queried_indices':[7,1], 'complete':False})
            self.assertEqual(p.p14.read_checkpoint(path)['queried_indices'],[7,1])
            p.atomic_checkpoint(path,{'queried_indices':[7,1,8], 'complete':True})
            self.assertTrue(p.p14.read_checkpoint(path)['complete'])
            self.assertEqual(len(list(Path(directory).iterdir())),1)

    def test_repeat_block_bootstrap_deterministic(self):
        values=np.linspace(-.03,.07,20)
        self.assertEqual(p.p14.bootstrap_interval(values,'phase120-test'),p.p14.bootstrap_interval(values,'phase120-test'))
        with self.assertRaises(RuntimeError):
            p.p14.bootstrap_interval(np.zeros(100),'invalid-fold-inference')


if __name__=='__main__': unittest.main()
