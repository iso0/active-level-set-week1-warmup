"""RC18 step B1 — results-independent inspection for a physics-mediated label model (descriptive; evaluator-level, no AL).

Question: is the map (physical outputs -> Keyhole label) more transferable between campaigns than the map (x -> label), which
failed in Week 17? Uses OBSERVED outputs of all runs (so this is not a learner result):
  1. per output, AUC for the label in NEW overall and inside NEW's fast-scan corner (VX > 0.85, where depth-based E1 fails);
  2. a logistic classifier on standardised observed outputs trained on ALL OLD runs, applied to NEW's observed outputs:
     AUC and BA at p >= 0.5 on NEW, overall and in the corner; compared with the same for an x-only logistic classifier
     trained on OLD (the Week 17 x->label transfer, re-done here as the reference).
    python -m src.rc18_inspect_label
"""
from __future__ import annotations

import json

import numpy as np
import pandas as pd
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import roc_auc_score

import src.rc18_campaign as C
import src.rc18_common as RC
import src.rc18_inspect as INS

OUT = RC.CAMP / "inspection"
FAST_VX = 0.85
FEATS = ["log_A_um", "vmax_spike_logratio", "tmax_T0_K", "log_ke_T0_nJ", "laser_T0_W", "vmax_spike_us"]


def ba(y, p):
    q = p >= 0.5; return 0.5 * (np.mean(q[y == 1]) + np.mean(~q[y == 0])) if (y == 0).any() and (y == 1).any() else np.nan


def main():
    N, O = INS.table("NEW"), INS.table("OLD"); res = {"per_output_AUC": {}, "transfer": {}}
    corner = N.VX.to_numpy() > FAST_VX; yN = N.y.to_numpy().astype(int)
    for c in FEATS:
        v = N[c].to_numpy(float); ok = np.isfinite(v); okc = ok & corner
        res["per_output_AUC"][c] = {"NEW_all": float(roc_auc_score(yN[ok], v[ok])),
                                    "NEW_corner": float(roc_auc_score(yN[okc], v[okc])) if 0 < yN[okc].sum() < okc.sum() else None,
                                    "corner_n": int(okc.sum()), "corner_neg": int((yN[okc] == 0).sum())}
    for name, cols in (("physics_outputs", FEATS[:3]), ("physics_outputs_all6", FEATS), ("x_only", ["logP", "logV", "logR", "ST"])):
        ok_o = np.all(np.isfinite(O[cols].to_numpy(float)), axis=1); Xo = O[cols].to_numpy(float)[ok_o]; yo = O.y.to_numpy().astype(int)[ok_o]
        mu, sd = Xo.mean(0), Xo.std(0) + 1e-12
        lr = LogisticRegression(C=1.0, max_iter=5000).fit((Xo - mu) / sd, yo)
        ok_n = np.all(np.isfinite(N[cols].to_numpy(float)), axis=1); Xn = (N[cols].to_numpy(float)[ok_n] - mu) / sd; yn = yN[ok_n]; cn = corner[ok_n]
        p = lr.predict_proba(Xn)[:, 1]
        res["transfer"][name] = {"features": cols, "n_old": int(ok_o.sum()), "NEW_AUC": float(roc_auc_score(yn, p)), "NEW_BA": float(ba(yn, p)),
                                 "NEW_corner_AUC": float(roc_auc_score(yn[cn], p[cn])) if 0 < yn[cn].sum() < cn.sum() else None,
                                 "NEW_corner_BA": float(ba(yn[cn], p[cn])), "NEW_specificity": float(np.mean(p[yn == 0] < 0.5)),
                                 "NEW_sensitivity": float(np.mean(p[yn == 1] >= 0.5))}
    (OUT / "LABEL_INSPECTION.json").write_text(json.dumps(res, indent=1), encoding="utf-8"); print(json.dumps(res, indent=1))


if __name__ == "__main__":
    main()
