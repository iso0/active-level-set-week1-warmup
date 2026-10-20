"""RC20 single-learner boundary-evolution view (presentation only; not frozen). Same machinery as src/rc19b_viewer.py: ONE
learner (arm path, construction, repeat, fold) refitted on its own first b paid runs with the SAME code path as the trajectory,
evaluated on a grid over log P x log VX at a chosen LS slice with ST fixed, plus that fold's held-out runs; the refit test
predictions are checked against the recorded ones. Pre-declared learner: first final repeat (19), fold 1.
Learners: the candidate SHQ_ATS_H on its own margin path, SHQ_ATS on the SAME paid path (with vs without log h on identical
data), ATSCF, ATSAPPROX and E1RAW on their own paths, and the candidate on its eta-straddle path.
    python -m src.rc20_viewer build      -> opus_rc20/viewer/rc20_boundary_view.html (+ .json)
"""
from __future__ import annotations

import json
import warnings

import numpy as np

import src.rc18_common as RC
import src.rc19_pool as P
import src.rc19b_keyhole as K
import src.rc19b_viewer as V
import src.rc20_attr as A

OUT = RC.ROOT / "outputs" / "research_campaign_20261020" / "opus_rc20"
RF = (19, 1)
LEARNERS = (("CAND_MARGIN", "SHQ_ATS_H"), ("CAND_MARGIN", "SHQ_ATS"), ("ATSCF_MARGIN", "ATSCF"), ("ATSAPPROX_MARGIN", "ATSAPPROX"), ("E1S", "E1RAW"),
            ("CAND_ETASTRADDLE", "SHQ_ATS_H"))
DESC = {"SHQ_ATS_H": "RC20 candidate: honest SHQ cross-fitted (A, T, S) + exact log h in the same L2 logistic classifier.",
        "SHQ_ATS": "The same upstream fits and classifier WITHOUT log h (= ATSCF construction), on the candidate's paid path.",
        "ATSCF": "ATSCF (honest K = 10) on its own margin path.", "ATSAPPROX": "RC19 approximation on its own margin path.",
        "E1RAW": "Week 18 E1 (depth GP + threshold) on its own straddle path."}


def learner(task, unit, M, arm, cons, Xg):
    te, gr = V._ext_task(task, Xg); Ze = P.zstd(te); pos = {s: i for i, s in enumerate(task["ids"])}; paid = [pos[s] for s in unit["paid_ids"]]; out = {}
    if arm.startswith("CAND"):
        rec = {e["budget"]: (e["p"].get(cons) if cons in e["p"] else e.get("p_all", {}).get(cons)) for e in unit["evals"]}
    else:
        rec = {e["budget"]: e["p"][cons] for e in unit["evals"]}
    rng = np.random.default_rng([P.SPLIT_SEED, 19, task["repeat"], task["fold"]])
    for b in V.BUDGETS:
        rev = V._ext_rev(task, M, paid[:b], len(Xg))
        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            if arm.startswith("CAND"):
                o, info = A.constructions(te, rev, Ze, (cons,), extra=gr)
            else:
                o, _, info, _ = K.constructions(te, rev, Ze, K.ADAPTIVE[arm], rng, K=10, extra=gr)
        pt = np.asarray(o[cons], float); pg = np.asarray(info["_extra"][cons], float)
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
    for arm, cons in LEARNERS:
        u = RC.read_json_gz(OUT / "c-final" / "units" / f"r{r}_f{f}__{arm}.json.gz")
        key = f"{arm} · {cons}"; L[key] = {"cons": cons, "desc": DESC.get(cons, cons), "budgets": learner(t, u, M, arm, cons, Xg)}
        chk = [v["check"] for v in L[key]["budgets"].values() if v["check"] is not None]
        print(key, "max refit-vs-recorded", max(chk) if chk else None, flush=True)
    data["tasks"]["label"] = {"name": "Keyhole label", "stage": f"RC20 sequential stage (fresh DEV repeat {r}), fold {f}", "repeat": r, "fold": f, "cut_name": "P(Keyhole)",
                              "test": [int(i) for i in t["test"]], "learners": L}
    html = V.HTML.replace('<option value="region">velocity-spike region</option>', "").replace("<title>Single-Learner Boundary View</title>", "<title>RC20 Boundary Evolution</title>")
    html = html.replace('if (D.tasks.label.learners["ATSCF_MARGIN · ATSCF"]) ls.value = "ATSCF_MARGIN · ATSCF";', 'if (D.tasks.label.learners["CAND_MARGIN · SHQ_ATS_H"]) ls.value = "CAND_MARGIN · SHQ_ATS_H";')
    js = json.dumps(data, separators=(",", ":")); (OUT / "viewer").mkdir(parents=True, exist_ok=True)
    (OUT / "viewer" / "rc20_boundary_view.json").write_text(js, encoding="utf-8"); (OUT / "viewer" / "rc20_boundary_view.html").write_text(html.replace("__DATA__", js), encoding="utf-8")
    print(OUT / "viewer" / "rc20_boundary_view.html", len(js) // 1024, "KB")


if __name__ == "__main__":
    build()
