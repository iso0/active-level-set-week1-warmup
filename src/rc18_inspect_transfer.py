"""RC18 step B0b — transfer inspection: does a GP trained on ALL OLD runs (historical, available before NEW) predict NEW?

Descriptive input to the model-direction choice (no AL). Per target: GP (Matern 3/2 ARD, log inputs standardised on OLD) on all
OLD runs -> prediction at every NEW run; R^2 against the NEW mean, Pearson r, and 5-fold CV R^2 of a linear recalibration
a + b * mu_OLD(x) on NEW (recalibration fitted out of fold). Also the regime-split residual SD of the NEW full-pool GP.
    python -m src.rc18_inspect_transfer
"""
from __future__ import annotations

import json
import warnings

import numpy as np
from sklearn.gaussian_process import GaussianProcessRegressor
from sklearn.gaussian_process.kernels import ConstantKernel, Matern, WhiteKernel
from sklearn.linear_model import LinearRegression
from sklearn.model_selection import KFold

import src.jdl_phys_al as PAL
import src.rc18_common as RC
import src.rc18_inspect as INS


def gp(Z, y):
    k = ConstantKernel(1.0, (1e-3, 1e3)) * Matern(np.ones(Z.shape[1]), (1e-2, 1e2), nu=1.5) + WhiteKernel(1e-2, (1e-6, 1.0))
    with warnings.catch_warnings():
        warnings.simplefilter("ignore"); return GaussianProcessRegressor(k, normalize_y=True, n_restarts_optimizer=0, random_state=0).fit(Z, y)


def main():
    RC.limit_threads(1)
    N, O = INS.table("NEW"), INS.table("OLD")
    cols = ["logP", "logV", "logR", "ST"]; XO = O[cols].to_numpy(float); XN = N[cols].to_numpy(float)
    mu, sd = XO.mean(0), XO.std(0); ZO, ZN = (XO - mu) / sd, (XN - mu) / sd
    res = {"note": "OLD-trained GP on all OLD runs predicts NEW; NEW ST range 302-500 K exceeds OLD's 300-400 K (extrapolation in ST)", "targets": {}}
    for c in list(PAL.PRIMARY) + list(PAL.SECONDARY):
        yo, yn = O[c].to_numpy(float), N[c].to_numpy(float); okO, okN = np.isfinite(yo), np.isfinite(yn)
        g = gp(ZO[okO], yo[okO]); m = g.predict(ZN[okN]); y = yn[okN]
        r2 = float(1 - np.sum((y - m) ** 2) / np.sum((y - y.mean()) ** 2)); r = float(np.corrcoef(y, m)[0, 1])
        p = np.zeros_like(y)
        for tr, te in KFold(5, shuffle=True, random_state=0).split(m):
            p[te] = LinearRegression().fit(m[tr, None], y[tr]).predict(m[te, None])
        r2cal = float(1 - np.sum((y - p) ** 2) / np.sum((y - y.mean()) ** 2))
        res["targets"][c] = {"R2_raw_OLD_to_NEW": r2, "pearson_r": r, "cvR2_recalibrated": r2cal, "mean_offset": float(np.mean(y - m)),
                             "OLD_gp_lengthscales": [float(v) for v in g.kernel_.k1.k2.length_scale]}
        print(json.dumps({c: res["targets"][c]}), flush=True)
    (INS.OUT / "TRANSFER_INSPECTION.json").write_text(json.dumps(res, indent=1), encoding="utf-8")


if __name__ == "__main__":
    main()
