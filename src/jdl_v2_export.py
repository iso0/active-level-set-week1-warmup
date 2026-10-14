"""Post-fit export of V2 mixture posteriors (no effect on any fit, prediction or comparison metric).

Added 2026-10-14 after Astra's decision-acquisition handoff and before the V2 comparison manifest was frozen, so that
the cached-posterior decision audit and any later lookahead can work from the exact fitted V2 checkpoints without
refitting.  For a fitted src.jdl_v2_model.JointModelV2, the fold's fixed feature-only reference pool x_ref and the
evaluation inputs x_eval, it stores for every coupling component k, jointly over X = [x_ref; x_eval]:
    weight, log evidence, rho, inference diagnostics,
    h mean and full covariance, f mean and full covariance, the f-h cross-covariance Cov(f(X), h(X)), theta mean/var.
These are the full within-component Gaussian approximations; with the weights they give the complete mixture,
including between-component variation.  Nothing is moment-matched.  Files are written atomically and fingerprinted
(SHA-256 of the file plus a hash of inputs, configuration and paid IDs) in a JSON sidecar.
"""
from __future__ import annotations

import hashlib
import io
import json
import os
from pathlib import Path

import numpy as np

EXPORT_VERSION = "jdl-v2-export-1.0"


def _h(*arrays):
    g = hashlib.sha256()
    for a in arrays:
        g.update(np.ascontiguousarray(np.asarray(a, float)).tobytes())
    return g.hexdigest()


def export_mixture(model, x_ref, x_eval):
    X = np.vstack([np.asarray(x_ref, float), np.asarray(x_eval, float)])
    arrays = {"x_ref": np.asarray(x_ref, float), "x_eval": np.asarray(x_eval, float), "weights": np.asarray(model.weights, float),
              "log_evidence": np.asarray(model.diagnostics["log_evidence"], float), "rho": np.array([c.rho for c in model.components], float)}
    for k, q in enumerate(model.component_posteriors(X)):
        arrays[f"h_mean_{k}"] = q["h_mean"]; arrays[f"h_cov_{k}"] = q["h_cov"]
        arrays[f"f_mean_{k}"] = q["f_mean"]; arrays[f"f_cov_{k}"] = q["f_cov"]; arrays[f"f_h_cov_{k}"] = q["f_h_cov"]
        arrays[f"theta_{k}"] = np.array([q["theta_mean"], q["theta_var"]])
    return arrays


def save_export(path, arrays, meta):
    path = Path(path); path.parent.mkdir(parents=True, exist_ok=True)
    buf = io.BytesIO(); np.savez_compressed(buf, **arrays); blob = buf.getvalue()
    tmp = path.with_suffix(path.suffix + ".tmp")
    with open(tmp, "wb") as fh:
        fh.write(blob); fh.flush(); os.fsync(fh.fileno())
    os.replace(tmp, path)
    side = {"version": EXPORT_VERSION, "file_sha256": hashlib.sha256(blob).hexdigest(),
            "inputs_sha256": _h(arrays["x_ref"], arrays["x_eval"]), **meta}
    stmp = path.with_suffix(".json.tmp")
    stmp.write_text(json.dumps(side, indent=1), encoding="utf-8"); os.replace(stmp, path.with_suffix(".json"))
    return side


def load_export(path):
    path = Path(path)
    side = json.loads(path.with_suffix(".json").read_text(encoding="utf-8"))
    blob = path.read_bytes()
    if hashlib.sha256(blob).hexdigest() != side["file_sha256"]:
        raise RuntimeError(f"export {path.name} does not match its recorded SHA-256")
    with np.load(io.BytesIO(blob), allow_pickle=False) as z:
        arrays = {k: z[k] for k in z.files}
    if _h(arrays["x_ref"], arrays["x_eval"]) != side["inputs_sha256"]:
        raise RuntimeError(f"export {path.name}: input fingerprint mismatch")
    return arrays, side


def components(arrays):
    """List of per-component dicts in the form src.jdl_v2_model.Component.posterior returns (over [x_ref; x_eval])."""
    out = []
    for k in range(len(arrays["weights"])):
        out.append({"h_mean": arrays[f"h_mean_{k}"], "h_cov": arrays[f"h_cov_{k}"], "f_mean": arrays[f"f_mean_{k}"], "f_cov": arrays[f"f_cov_{k}"],
                    "f_h_cov": arrays[f"f_h_cov_{k}"], "theta_mean": float(arrays[f"theta_{k}"][0]), "theta_var": float(arrays[f"theta_{k}"][1])})
    return out
