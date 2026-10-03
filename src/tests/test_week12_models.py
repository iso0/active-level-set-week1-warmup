import importlib
import json

import numpy as np
import pandas as pd
from threadpoolctl import threadpool_limits


def _toy_frame(n=12, offset=0):
    idx = np.arange(n, dtype=float) + float(offset)
    frame = pd.DataFrame({
        "sim_id": [f"toy_{offset}_{i}" for i in range(n)],
        "P": 1.0 + 0.07 * idx,
        "VX": 0.8 + 0.05 * np.sin(idx),
        "LS": 1.1 + 0.04 * idx,
        "ST": 0.9 + 0.03 * np.cos(idx),
        "has_keyhole": (np.arange(n) % 2).astype(int),
    })
    frame["row_index"] = np.arange(n)
    frame["log_h"] = np.log(frame.P) - 0.5 * np.log(frame.VX) - 1.5 * np.log(frame.LS)
    return frame


def test_failure_metrics_keep_missing_class_metrics_nan():
    module = importlib.import_module("src.week12_models")
    result = module._failure_metrics(np.array([0, 1, 1]))
    assert result["n"] == 3
    assert np.isnan(result["balanced_accuracy"])
    assert np.isnan(result["roc_auc"])
    assert np.isnan(result["pr_auc_keyhole"])
    assert np.isnan(result["brier"])


def test_historical_model_smoke_and_components_on_toy_rows():
    module = importlib.import_module("src.week12_models")
    frame = _toy_frame()
    train, test = np.arange(8), np.arange(8, 12)
    with threadpool_limits(limits=1):
        for name in module.MODELS:
            prediction, diagnostics = module._fit_predict(name, frame, train, test, 11, float(frame.has_keyhole.iloc[train].mean()))
            assert diagnostics["fit_status"] != "FAILED", (name, diagnostics)
            assert np.isfinite(prediction.probability.to_numpy(float)).all()
            if name in ("H", "M3"):
                assert {"physics_latent", "final_latent"}.issubset(prediction.columns)


def test_transfer_prediction_is_invariant_to_new_labels_and_scaler_is_old_only():
    module = importlib.import_module("src.week12_models")
    old = _toy_frame(12, 0)
    new = _toy_frame(4, 100)
    changed = new.copy()
    changed["has_keyhole"] = 1 - changed["has_keyhole"]
    with threadpool_limits(limits=1):
        fit, diagnostics = module._fit_model("G0", old, np.arange(len(old)), 17)
        p1, _ = module._predict_model("G0", fit, new, np.arange(len(new)))
        p2, _ = module._predict_model("G0", fit, changed, np.arange(len(changed)))
    assert diagnostics["scaler_scope"] == "training_rows_4d"
    assert np.allclose(fit.scaler.mean_, module._x(old).mean(axis=0))
    assert np.allclose(p1, p2)


def test_pooled_oof_summary_preserves_one_class_nan_metrics(tmp_path):
    module = importlib.import_module("src.week12_models")
    pred = pd.DataFrame({
        "model": ["H"] * 4,
        "repeat": [1] * 4,
        "fold": [1, 1, 2, 2],
        "row_index": [0, 1, 2, 3],
        "truth": [1, 1, 1, 0],
        "probability": [0.8, 0.7, 0.6, 0.2],
        "is_q20": [True, True, True, False],
        "is_q30": [True, True, False, False],
    })
    rows = []
    for fold, part in pred.groupby("fold"):
        for subset, mask in (("full", np.ones(len(part), bool)), ("q20", part.is_q20.to_numpy(bool)), ("q30", part.is_q30.to_numpy(bool))):
            y, p = part.truth.to_numpy(int)[mask], part.probability.to_numpy(float)[mask]
            metric = module.metrics(y, p) if len(y) else module._failure_metrics(y)
            rows.append({"split_id": f"r1_f{fold}", "repeat": 1, "fold": fold, "model": "H", "subset": subset, **metric, "fit_status": "ok"})
    module._new_only_summary(pd.DataFrame(rows), pred, tmp_path)
    pooled = pd.read_csv(tmp_path / "pooled_oof_per_repeat.csv")
    q20 = pooled[pooled.subset.eq("q20")].iloc[0]
    assert np.isnan(q20.balanced_accuracy)
    assert np.isnan(q20.roc_auc)
    assert q20.accuracy == 1.0


def test_new_only_checkpoint_serialization_and_coverage_qc(tmp_path, monkeypatch):
    module = importlib.import_module("src.week12_models")
    new = _toy_frame(4)
    splits = [
        {"split_id": "r1_f1", "repeat": 1, "fold": 1, "train_indices": [0, 1], "test_indices": [2, 3]},
        {"split_id": "r1_f2", "repeat": 1, "fold": 2, "train_indices": [2, 3], "test_indices": [0, 1]},
    ]

    def fake_fit_predict(name, frame, train, test, fit_seed, old_prevalence=None):
        rows = [{"model": name, "row_index": int(i), "sim_id": str(frame.sim_id.iloc[i]), "truth": int(frame.has_keyhole.iloc[i]), "probability": 0.25 + 0.1 * int(i), "fit_status": "ok"} for i in test]
        return pd.DataFrame(rows), {"model": name, "fit_status": "ok", "fit_seed": int(fit_seed)}

    monkeypatch.setattr(module, "OUT", tmp_path)
    monkeypatch.setattr(module, "load_new", lambda: new.copy())
    monkeypatch.setattr(module, "load_old", lambda: new.copy())
    monkeypatch.setattr(module, "load_splits", lambda: splits)
    monkeypatch.setattr(module, "sha", lambda path: "fixture-hash")
    monkeypatch.setattr(module, "_provenance", lambda mode, frame, old: {"mode": mode, "schema_version": "fixture"})
    monkeypatch.setattr(module, "_subset_flags", lambda frame, indices: {20: np.array([True, False]), 30: np.array([True, False])})
    monkeypatch.setattr(module, "_fit_predict", fake_fit_predict)

    result = module.run_new_only()
    assert result["status"] == "PASS"
    checkpoint_root = tmp_path / "models" / "new_only" / "checkpoints"
    for split in splits:
        payload = json.loads((checkpoint_root / f"{split['split_id']}.json").read_text())
        assert isinstance(payload["predictions"], list)
        assert len(payload["predictions"]) == len(module.MODELS) * 2
    qc = json.loads((tmp_path / "models" / "new_only" / "qc.json").read_text())
    assert qc["status"] == "PASS"
    assert qc["per_group_row_count_failures"] == []
    assert qc["pooled_oof_coverage_failures"] == []
