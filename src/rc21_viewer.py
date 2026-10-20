"""RC21 single-learner boundary-evolution view (presentation only; not frozen). Same machinery as src/rc19b_viewer.py: ONE
learner (arm path, construction, repeat, fold) refitted on its own first b paid runs with the SAME code path as the trajectory,
evaluated on a grid over log P x log VX at a chosen LS slice with ST fixed, plus that fold's held-out runs; the refit test
predictions are checked against the recorded ones. Pre-declared learner: first final repeat (27), fold 1.
Learners: NEW on its own margin path, SHQ_ATS_H on the SAME paid path (new model vs RC20 model on identical data), SHQ_ATS_H on
its own path, SHQ_ATS_X on its own path, ATSAPPROX and E1RAW on their own paths.
    python -m src.rc21_viewer build      -> opus_rc21/viewer/rc21_boundary_view.html (+ .json)
"""
from __future__ import annotations

import json
import warnings

import numpy as np

import src.rc18_common as RC
import src.rc19_pool as P
import src.rc19b_keyhole as K
import src.rc19b_viewer as V
import src.rc21_attr as RA
import src.rc21_decisions as DEC

OUT = RC.ROOT / "outputs" / "research_campaign_20261020" / "opus_rc21"
RF = (27, 1)
DESC = {"PHR": "RC21 PHR: honest SHQ (A, T, S) + exact log-h trend + h-transverse shrinkable residual, Laplace GP classification averaged over a fixed grid.",
        "PHR_NR": "RC21 PHR without the residual (learned regularisation only).",
        "SHQ_ATS_H": "RC20 candidate: honest SHQ (A, T, S) + exact log h, L2 logistic C = 1.",
        "SHQ_ATS_X": "Generic-input control: honest SHQ (A, T, S) + the 4 exact log inputs, L2 logistic C = 1.",
        "ATSAPPROX": "RC19 approximation on its own margin path.", "E1RAW": "Week 18 E1 (depth GP + threshold) on its own straddle path."}


def learners():
    return (("NEW_MARGIN", DEC.NEW), ("NEW_MARGIN", "SHQ_ATS_H"), ("H_MARGIN", "SHQ_ATS_H"), ("X_MARGIN", "SHQ_ATS_X"), ("ATSAPPROX_MARGIN", "ATSAPPROX"), ("E1S", "E1RAW"))


def learner(task, unit, M, arm, cons, Xg):
    te, gr = V._ext_task(task, Xg); Ze = P.zstd(te); pos = {s: i for i, s in enumerate(task["ids"])}; paid = [pos[s] for s in unit["paid_ids"]]; out = {}
    phys = arm in ("NEW_MARGIN", "H_MARGIN", "X_MARGIN"); nt = len(te["test"])
    rec = {e["budget"]: (e["p_all"][cons] if phys else e["p"][cons]) for e in unit["evals"]}
    rng = np.random.default_rng([P.SPLIT_SEED, 19, task["repeat"], task["fold"]])
    for b in V.BUDGETS:
        rev = V._ext_rev(task, M, paid[:b], len(Xg))
        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            if phys:
                o, _ = RA.state(te, rev, Ze, np.r_[te["test"], gr], which=(cons,)); pt = np.asarray(o[cons][:nt], float); pg = np.asarray(o[cons][nt:], float)
            else:
                o, _, info, _ = K.constructions(te, rev, Ze, K.ADAPTIVE[arm], rng, K=10, extra=gr); pt = np.asarray(o[cons], float); pg = np.asarray(info["_extra"][cons], float)
        r = np.asarray([np.nan if v is None else v for v in rec[b]], float) if rec.get(b) is not None else np.full(len(pt), np.nan)
        out[str(b)] = {"grid": V._enc(pg), "paid": [int(i) for i in paid[:b]], "test_p": [round(float(v), 5) for v in pt],
                       "check": float(np.nanmax(np.abs(pt - r))) if np.isfinite(r).any() else None, "constant": bool(np.nanstd(pg) < 1e-9)}
    return out


def build():
    RC.limit_threads(1); M = P.manifest(); lp, lv, Xg = V.grid(M); ids = M.index.to_numpy(str)
    data = {"grid": {"logP": np.round(lp, 4).tolist(), "logVX": np.round(lv, 4).tolist(), "LS_um": list(V.LS_SLICES_UM), "ST_K": list(V.ST_FIXED_K), "NG": V.NG,
                     "ls_band": V.LS_BAND_UM, "st_band": V.ST_BAND_K},
            "runs": {"logP": np.round(np.log(M.P), 4).tolist(), "logVX": np.round(np.log(M.VX), 4).tolist(), "LS_um": np.round(M.LS * 1e6, 2).tolist(),
                     "ST": np.round(M.ST, 1).tolist(), "y": M.y.astype(int).tolist(), "id": ids.tolist(), "inside": [None] * len(ids)},
            "budgets": list(V.BUDGETS), "tasks": {}}
    r, f = RF; t = {(x["repeat"], x["fold"]): x for x in P.tasks([r])}[(r, f)]; L = {}
    for arm, cons in learners():
        u = RC.read_json_gz(OUT / "d-final" / "units" / f"r{r}_f{f}__{arm}.json.gz")
        key = f"{arm} · {cons}"; L[key] = {"cons": cons, "desc": DESC.get(cons, cons), "budgets": learner(t, u, M, arm, cons, Xg)}
        chk = [v["check"] for v in L[key]["budgets"].values() if v["check"] is not None]
        print(key, "max refit-vs-recorded", max(chk) if chk else None, flush=True)
    data["tasks"]["label"] = {"name": "Keyhole label", "stage": f"RC21 sequential stage (fresh DEV repeat {r}), fold {f}", "repeat": r, "fold": f, "cut_name": "P(Keyhole)",
                              "test": [int(i) for i in t["test"]], "learners": L}
    html = V.HTML.replace('<option value="region">velocity-spike region</option>', "").replace("<title>Single-Learner Boundary View</title>", "<title>RC21 Boundary Evolution</title>")
    first = f"NEW_MARGIN · {DEC.NEW}"
    html = html.replace('if (D.tasks.label.learners["ATSCF_MARGIN · ATSCF"]) ls.value = "ATSCF_MARGIN · ATSCF";', f'if (D.tasks.label.learners["{first}"]) ls.value = "{first}";')
    js = json.dumps(data, separators=(",", ":")); (OUT / "viewer").mkdir(parents=True, exist_ok=True)
    (OUT / "viewer" / "rc21_boundary_view.json").write_text(js, encoding="utf-8"); (OUT / "viewer" / "rc21_boundary_view.html").write_text(html.replace("__DATA__", js), encoding="utf-8")
    print(OUT / "viewer" / "rc21_boundary_view.html", len(js) // 1024, "KB")


if __name__ == "__main__":
    build()
