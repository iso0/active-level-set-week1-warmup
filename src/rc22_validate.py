"""RC22 numerical acceptance before any scientific comparison (no evaluation metric is computed here):
  1. the fast residual-free PHR_NRMAP equals the RC21 construction (src.rc21_attr.state) exactly;
  2. reproduction: the REF, H and E1S runners with the standard startup reproduce the RC21B trajectories (repeat 35, fold 1)
     exactly (paid order and every recorded probability);
  3. startups and blocks are label-free and lawful (paths computed without labels; test rows never candidates; class discovery
     counted); one-class starts are counted (evaluator-side, descriptive);
  4. shadow: with every outcome outside a trajectory's own paid runs randomised, the new arms (margin + coverage, BALD_LAP +
     coverage, BALD_GRID, MAXIMIN) pay the same runs and predict identically;
  5. selector numerics: the Gauss-Hermite BALD_LAP equals a Monte Carlo reference; BALD_GRID equals its direct formula;
  6. recalibration honesty: perturbing a paid run's own outcomes never changes its own out-of-fold recalibration input;
  7. missing-channel stress touches only paid T / S channels (labels, depth, unpaid rows untouched);
  8. timing per paid state.
    python -m src.rc22_validate
"""
from __future__ import annotations

import json
import time

import numpy as np
from scipy.special import expit

import src.rc18_common as RC
import src.rc19_pool as P
import src.rc19b_keyhole as K
import src.rc21_attr as RA
import src.rc22_common as C
import src.rc22_jobs as J
from src.rc19_validate import _corrupt

OUT = J.OUT


def _same(u, ref, key_map):
    ok = u["paid_ids"] == ref["paid_ids"] and len(u["evals"]) == len(ref["evals"])
    for e1, e2 in zip(u["evals"], ref["evals"]):
        for a, b in key_map:
            ok = ok and e1["p"][a] == e2["p"][b]
    return bool(ok)


def main():
    RC.limit_threads(1); M = P.manifest(); C.set_manifest(M); res = {"utc": RC.utc()}
    T = {(t["repeat"], t["fold"]): t for t in P.tasks([35, 36, 1])}
    # 1. fast PHR_NRMAP vs RC21
    worst = 0.0
    for (r, f, b) in ((35, 1, 12), (36, 3, 40), (35, 4, 60)):
        t = T[(r, f)]; u = RC.read_json_gz(J.EB / f"r{r}_f{f}__H_MARGIN.json.gz"); pos = {s: i for i, s in enumerate(t["ids"])}
        rev = K._rev_with(t, M, [pos[s] for s in u["paid_ids"][:b]]); Z = P.zstd(t); rows = np.r_[t["test"], np.setdiff1d(t["pool"], rev.paid)]
        o1, _ = RA.state(t, rev, Z, rows, which=("PHR_NRMAP",)); o2, _ = C.state(t, rev, Z, rows, which=("PHR_NRMAP",))
        worst = max(worst, float(np.max(np.abs(o1["PHR_NRMAP"] - o2["PHR_NRMAP"]))))
    res["fast_phr_nrmap_vs_rc21"] = {"max_abs_diff": worst, "PASS": bool(worst <= 1e-12)}; print(res["fast_phr_nrmap_vs_rc21"], flush=True)
    # 2. reproduction of RC21B trajectories
    t = T[(35, 1)]; rep = {}
    for arm, own, ref_arm in (("REF", "PHR_NRMAP", "NEW_MARGIN"), ("H", "SHQ_ATS_H", "H_MARGIN")):
        ref = RC.read_json_gz(J.EB / f"r35_f1__{ref_arm}.json.gz"); u = C.run_phys(t, own, "margin", None, M)
        rep[arm] = _same(u, ref, [(own, own)]) and all(e1["p_all"][k] == e2["p_all"][k] for e1, e2 in zip(u["evals"], ref["evals"]) for k in ("SHQ_ATS_H", "PHR_NRMAP"))
    ref = RC.read_json_gz(J.EB / "r35_f1__E1S.json.gz"); u = C.run_e1s(t, M); rep["E1S"] = _same(u, ref, [("E1RAW", "E1RAW"), ("E1CAL", "E1CAL")])
    res["reproduction_rc21b_r35_f1"] = {**rep, "PASS": bool(all(rep.values()))}; print(res["reproduction_rc21b_r35_f1"], flush=True)
    # 3. startups and blocks
    st = {}
    Mc = _corrupt(M, set(), 5)
    for kind in ("RAND8", "LOCAL8"):
        one, same = 0, True
        for (r, f), tk in ((k, v) for k, v in T.items() if k[0] in (35, 36)):
            t2 = C.startup_task(tk, kind); s8 = t2["path"][:P.B0]; y = M.y.reindex(tk["ids"]).to_numpy(int)[s8]; one += int(len(set(y.tolist())) < 2)
            same = same and set(int(i) for i in s8) <= set(int(i) for i in tk["pool"]) and len(set(t2["path"].tolist())) == len(tk["pool"])
        st[kind] = {"one_class_starts_in_10": one, "paths_are_permutations_of_pool": same}
    B = C.block_tasks([1], M); lab = C.blocks(M); bl = []
    for tb in B:
        yb = M.y.to_numpy(int)[tb["test"]]
        bl.append({"block": tb["block"], "n": int(len(tb["test"])), "keyhole": int(yb.sum()), "conduction": int((yb == 0).sum()), "disjoint": bool(len(np.intersect1d(tb["test"], tb["pool"])) == 0)})
    res["startups_blocks"] = {"startups": st, "blocks": bl, "labels_unused": "startup_task / block_tasks / blocks take no label argument (paths from public X only)",
                              "PASS": bool(all(v["paths_are_permutations_of_pool"] for v in st.values()) and all(b["disjoint"] for b in bl) and sum(b["n"] for b in bl) == len(M))}
    print(res["startups_blocks"], flush=True)
    # 4. shadow trajectories
    sh = {}; t1 = C.startup_task(T[(1, 1)], "LOCAL8")
    for nm, (own, sel, cov) in {"margin_cov": ("PHR_NRMAP", "margin", 5), "bald_lap_cov": ("PHR_NRMAP", "BALD_LAP", 5), "bald_grid": ("PHR_NRMAP", "BALD_GRID", None),
                                "maximin": ("PHR_NRMAP", "MAXIMIN", None)}.items():
        u1 = C.run_phys(t1, own, sel, cov, M, bmax=22); Mc = _corrupt(M, set(u1["paid_ids"]), 2201); u2 = C.run_phys(t1, own, sel, cov, Mc, bmax=22)
        d = max(float(np.nanmax(np.abs(np.asarray(e1["p_all"][k], float) - np.asarray(e2["p_all"][k], float)))) for e1, e2 in zip(u1["evals"], u2["evals"]) for k in e1["p_all"])
        sh[nm] = {"same_paid": u1["paid_ids"] == u2["paid_ids"], "max_abs_p_diff": d, "hows": sorted(set(e.get("how", "") for e in u1["evals"]))}
    C.set_manifest(M)
    res["shadow"] = {**sh, "PASS": bool(all(v["same_paid"] and v["max_abs_p_diff"] == 0.0 for v in sh.values()))}; print(res["shadow"], flush=True)
    # 5. selector numerics
    rng = np.random.default_rng(22); worst_mc, worst_se, worst_grid = 0.0, 0.0, 0.0
    for (r, f, b) in ((35, 2, 16), (36, 5, 40)):
        t = T[(r, f)]; u = RC.read_json_gz(J.EB / f"r{r}_f{f}__NEW_MARGIN.json.gz"); pos = {s: i for i, s in enumerate(t["ids"])}
        rev = K._rev_with(t, M, [pos[s] for s in u["paid_ids"][:b]]); Z = P.zstd(t); cands = np.setdiff1d(t["pool"], rev.paid)
        import src.rc20_attr as A
        R = A.cf(Z, rev, A.ATS, "SHQ", cands, A.KF); h = A.hcol(t); L = rev.paid; y = rev.paid_y()[L]
        _, fam = C.phr_family(R["F"], h[L], y, R["E"], h[cands]); grid, lap, _ = C.bald_scores(fam); idx = rng.choice(len(cands), 40, replace=False)
        for j in idx:
            g = rng.choice(len(fam["w"]), 200000, p=fam["w"]); f = fam["m"][g, j] + np.sqrt(fam["v"][g, j]) * rng.standard_normal(200000); s = expit(f)
            hb = C._hb(s); mc = float(C._hb(np.array([s.mean()]))[0] - hb.mean()); se = float(hb.std() / np.sqrt(len(hb)))
            worst_mc = max(worst_mc, abs(mc - lap[j]) - 3 * se); worst_se = max(worst_se, se)
            pg = expit(fam["m"][:, j]); direct = float(C._hb(np.array([fam["w"] @ pg]))[0] - fam["w"] @ C._hb(pg)); worst_grid = max(worst_grid, abs(direct - grid[j]))
    res["selector_numerics"] = {"bald_lap_mc_excess_over_3se": worst_mc, "max_mc_se": worst_se, "bald_grid_vs_direct": worst_grid, "PASS": bool(worst_mc <= 1e-4 and worst_grid <= 1e-12)}
    print(res["selector_numerics"], flush=True)
    # 6. recalibration honesty
    t = T[(35, 1)]; u = RC.read_json_gz(J.EB / "r35_f1__H_MARGIN.json.gz"); pos = {s: i for i, s in enumerate(t["ids"])}; paid = [pos[s] for s in u["paid_ids"][:24]]
    Z = P.zstd(t); r0 = K._rev_with(t, M, paid); _, _, c0 = C.recal_map(t, r0, Z); worst = 0.0; other = 0
    for j in (2, 9, 17):
        r1 = K._rev_with(t, M, paid); i = paid[j]; r1._y[i] = 1 - r1._y[i]; r1._A[i] *= 1.5; r1._Y[i] = r1._Y[i] + 0.4
        _, _, c1 = C.recal_map(t, r1, Z); worst = max(worst, abs(c1["p_oof"][j] - c0["p_oof"][j])); other += int(np.max(np.abs(np.asarray(c1["p_oof"]) - np.asarray(c0["p_oof"]))) > 1e-9)
    res["recal_honesty"] = {"own_oof_change_max": worst, "other_changed_cases": other, "PASS": bool(worst == 0.0 and other > 0)}; print(res["recal_honesty"], flush=True)
    # 7. masking
    t = T[(35, 1)]; u = RC.read_json_gz(J.EB / "r35_f1__NEW_MARGIN.json.gz"); paid = [pos[s] for s in u["paid_ids"][:40]]; ok = True; cnt = {}
    base = K._rev_with(t, M, paid)
    for cond in J.MISS:
        rv, nm = J.masked_rev(t, M, paid, cond); cnt[cond] = nm
        ok = ok and np.array_equal(rv._y, base._y) and np.array_equal(np.isnan(rv._A), np.isnan(base._A)) and np.nanmax(np.abs(rv._A - base._A)) == 0
        cols = [k for k in range(rv._Y.shape[1]) if k not in (C.ATS_T, C.ATS_S)]
        ok = ok and np.array_equal(np.nan_to_num(rv._Y[:, cols], nan=-9), np.nan_to_num(base._Y[:, cols], nan=-9))
        unpaid = np.setdiff1d(np.arange(rv.n), rv.paid); ok = ok and bool(np.all(np.isnan(rv._Y[unpaid])))
    res["masking"] = {"masked_channel_values_at_B40": cnt, "PASS": bool(ok)}; print(res["masking"], flush=True)
    # 8. timing
    tm = []
    for b in (16, 60):
        rev = K._rev_with(t, M, [pos[s] for s in u["paid_ids"][:b]]); rows = np.r_[t["test"], np.setdiff1d(t["pool"], rev.paid)]
        c1 = time.process_time(); C.state(t, rev, Z, rows, which=("SHQ_ATS_H",)); c2 = time.process_time(); C.state(t, rev, Z, rows, which=("SHQ_ATS_H", "PHR_NRMAP"), want_bald=True)
        c3 = time.process_time(); C.state(t, rev, Z, rows, which=J.INGR, want_bald=True, want_eta=True); c4 = time.process_time()
        tm.append({"budget": b, "H_only_s": c2 - c1, "H+REF+BALD_s": c3 - c2, "all_ingredients_s": c4 - c3})
    res["timing"] = tm; print(tm, flush=True)
    res["status"] = "PASS" if all(v["PASS"] for v in res.values() if isinstance(v, dict) and "PASS" in v) else "FAIL"
    OUT.mkdir(parents=True, exist_ok=True); (OUT / "RC22_VALIDATION.json").write_text(json.dumps(res, indent=1, default=str), encoding="utf-8"); print(res["status"])


if __name__ == "__main__":
    main()
