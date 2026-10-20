"""RC21 design diagnostics quoted in PROTOCOL_RC21_STAGE1.md section 1 (evaluator-side, full 541-run DEV pool; labels and outputs
are SEEN here, so nothing in this file is a result or enters any learner):
  * direction of a 4-input logistic boundary vs the h direction (cosine, fitted exponents);
  * 5-fold CV log loss / BA of h-only, 4-input, h + transverse (linear / quadratic), ARD-RBF GPC, and oracle-output classifiers;
  * the fast-scan corner (VX > 0.85 m/s, P > 330 W): counts, nearest-neighbour label agreement vs the whole pool, and the share
    of the RC20 margin paths' budget spent there.
    python -m src.rc21_diagnostics       -> opus_rc21/diagnostics/DESIGN_DIAGNOSTICS.json / .md
"""
from __future__ import annotations

import json

import numpy as np
import pandas as pd

import src.rc18_common as RC
import src.rc19_pool as P
import src.rc21_phr as PH

OUT = RC.ROOT / "outputs" / "research_campaign_20261020" / "opus_rc21" / "diagnostics"


def main():
    RC.limit_threads(1)
    from sklearn.gaussian_process import GaussianProcessClassifier
    from sklearn.gaussian_process.kernels import RBF, ConstantKernel
    from sklearn.linear_model import LogisticRegression
    from sklearn.model_selection import StratifiedKFold
    M = P.manifest(); X = M[list(P.INPUTS)].to_numpy(float); y = M.y.to_numpy(int); lx = np.log(X); Z = (lx - lx.mean(0)) / lx.std(0)
    h = lx[:, 0] - 0.5 * lx[:, 1] - 1.5 * lx[:, 2]; zh = (h - h.mean()) / h.std(); nb = (M.source_batch == "NEW").to_numpy()
    d = PH.H_DIR * lx.std(0); d = d / np.linalg.norm(d); Q, _ = np.linalg.qr(np.c_[d, np.eye(4)]); U = Z @ Q[:, 1:4]
    res = {"utc": RC.utc(), "n": int(len(y)), "keyhole_rate": float(y.mean())}
    g = LogisticRegression(C=1e4, max_iter=5000).fit(lx, y); b = g.coef_[0]; gz = LogisticRegression(C=1e4, max_iter=5000).fit(Z, y); w = gz.coef_[0]
    res["boundary_direction"] = {"raw_log_input_coef_over_P": (b / b[0]).tolist(), "h_law": [1.0, -0.5, -1.5, 0.0], "cosine_with_h_direction_in_Z": float(w @ d / np.linalg.norm(w))}
    ATS = M[["log_A_um", "tmax_T0_K", "vmax_spike_logratio"]].to_numpy(float); ok = np.all(np.isfinite(ATS), 1); S = (ATS - np.nanmean(ATS[ok], 0)) / np.nanstd(ATS[ok], 0)
    cv = StratifiedKFold(5, shuffle=True, random_state=0)

    def cvp(make, F):
        p = np.full(len(y), np.nan); idx = np.flatnonzero(ok)
        for tr, te in cv.split(F[idx], y[idx]):
            p[idx[te]] = make().fit(F[idx[tr]], y[idx[tr]]).predict_proba(F[idx[te]])[:, 1]
        pp = np.clip(p[ok], 1e-6, 1 - 1e-6); yy = y[ok]; c = ok & nb & (y == 0)
        return {"LL": float(-np.mean(yy * np.log(pp) + (1 - yy) * np.log(1 - pp))), "BA": float(0.5 * (np.mean(pp[yy == 1] >= .5) + np.mean(pp[yy == 0] < .5))),
                "NEW_conduction_recall": float(np.mean(p[c] < .5)), "NEW_conduction_n": int(c.sum())}
    L1 = lambda C=1.0: (lambda: LogisticRegression(C=C, max_iter=5000))
    res["cv_on_rows_with_all_outputs"] = {
        "h only (C=1)": cvp(L1(), zh[:, None]), "h only (C=100)": cvp(L1(100.0), zh[:, None]), "4 log inputs (C=1)": cvp(L1(), Z), "4 log inputs (C=100)": cvp(L1(100.0), Z),
        "h + U linear": cvp(L1(), np.c_[zh, U]), "h + U + quadratic": cvp(L1(), np.c_[zh, U, zh[:, None] * U, U ** 2, zh ** 2]),
        "ARD-RBF GPC on Z": cvp(lambda: GaussianProcessClassifier(ConstantKernel(4.0) * RBF(np.ones(4)), random_state=0), Z),
        "oracle log A (evaluator only)": cvp(L1(), S[:, :1]), "oracle A, T, S": cvp(L1(), S), "oracle A, T, S + h": cvp(L1(), np.c_[S, zh])}
    c = ((M.VX > 0.85) & (M.P > 330)).to_numpy(); idx = np.flatnonzero(c)
    D = np.linalg.norm(Z[idx][:, None] - Z[idx][None], axis=2); np.fill_diagonal(D, np.inf); yc = y[idx]
    Dg = np.linalg.norm(Z[:, None] - Z[None], axis=2); np.fill_diagonal(Dg, np.inf)
    paths = []
    for f in sorted((RC.ROOT / "outputs/research_campaign_20261020/opus_rc20/c-final/units").glob("*.json.gz")):
        u = RC.read_json_gz(f)
        for B in (24, 60):
            paths.append({"arm": u["arm"], "B": B, "share_corner": float(np.mean(pd.Series(c, index=M.index).reindex(u["paid_ids"][:B]).to_numpy(bool)))})
    res["corner"] = {"definition": "VX > 0.85 m/s and P > 330 W", "runs": int(c.sum()), "keyhole": int(yc.sum()), "conduction": int((yc == 0).sum()),
                     "NEW_conduction_in_corner": int((c & nb & (y == 0)).sum()), "pool_share": float(c.mean()),
                     "nn_label_agreement_corner": float(np.mean(yc == yc[D.argmin(1)])), "nn_label_agreement_pool": float(np.mean(y == y[Dg.argmin(1)])),
                     "rc20_paid_share_in_corner": pd.DataFrame(paths).groupby(["arm", "B"]).share_corner.mean().round(3).reset_index().to_dict("records") if paths else None}
    OUT.mkdir(parents=True, exist_ok=True); (OUT / "DESIGN_DIAGNOSTICS.json").write_text(json.dumps(res, indent=1), encoding="utf-8")
    rows = [f"| {k} | {v['LL']:.4f} | {v['BA']:.4f} | {v['NEW_conduction_recall']:.3f} |" for k, v in res["cv_on_rows_with_all_outputs"].items()]
    L = ["# RC21 design diagnostics (evaluator-side, full 541-run DEV pool; NOT results)", "",
         f"Boundary direction: 4-input logistic exponents (relative to P) {np.round(res['boundary_direction']['raw_log_input_coef_over_P'], 3).tolist()} vs h-law (1, −0.5, −1.5, 0); "
         f"cosine with the h direction in standardised log-input space {res['boundary_direction']['cosine_with_h_direction_in_Z']:.4f}.", "",
         "5-fold CV on the 484 runs with all three outputs (oracle rows use the TRUE outputs and are evaluator-only bounds):", "",
         "| model | LL | BA | NEW-conduction recall |", "|---|---|---|---|", *rows, "",
         f"Fast-scan corner ({res['corner']['definition']}): {res['corner']['runs']} runs ({res['corner']['keyhole']} Keyhole, {res['corner']['conduction']} conduction; "
         f"{100 * res['corner']['pool_share']:.1f} % of the pool); nearest-neighbour label agreement {res['corner']['nn_label_agreement_corner']:.2f} in the corner vs "
         f"{res['corner']['nn_label_agreement_pool']:.2f} in the whole pool.", "", "Share of the RC20 paid budget spent in the corner (fresh repeats 19–26):", "",
         "| arm | budget | share |", "|---|---|---|", *[f"| {r['arm']} | {r['B']} | {r['share_corner']:.3f} |" for r in (res['corner']['rc20_paid_share_in_corner'] or [])], ""]
    (OUT / "DESIGN_DIAGNOSTICS.md").write_text("\n".join(L) + "\n", encoding="utf-8"); print("\n".join(L))


if __name__ == "__main__":
    main()
