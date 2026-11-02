"""GT independent recomputation (PROTOCOL_GT.md section 7): BA per learner and budget, the AULC windows and the headline paired
contrasts, recomputed from the EXPORTS ONLY (predictions_f32.npz + the pooled manifest labels), with code that does not import
src.el_eval / src.gt_eval. Compares with the evaluator's JSON results; acceptance max |diff| <= 1e-9 (float32 inputs on both sides).
    python -m src.gt_recompute g2 | g3 | g4
"""
from __future__ import annotations

import json
import sys
from collections import defaultdict

import numpy as np
import pandas as pd

OUTD = None


def _root():
    from pathlib import Path
    return Path(__file__).resolve().parents[1] / "outputs" / "research_campaign_20261102" / "opus_geometry_temperature"


def ba_rows(z, labels):
    """{(system, cond, cluster, learner): (budgets, BA per budget)}; BA = mean of the two class recalls at p >= 0.5; NaN if one class."""
    out = {}
    for k in z.files:
        if k.endswith("|budgets") or k.endswith("|test_ids"):
            continue
        P = z[k].astype(np.float64); ids = z[k + "|test_ids"]; b = z[k + "|budgets"].astype(int); y = labels.reindex(ids).to_numpy(int)
        hat = P >= 0.5; n1, n0 = (y == 1).sum(), (y == 0).sum()
        if n1 == 0 or n0 == 0:
            ba = np.full(len(b), np.nan)
        else:
            ba = 0.5 * ((hat & (y == 1)).sum(1) / n1 + (~hat & (y == 0)).sum(1) / n0)
        s, c, r, f = k.split("|"); out[(s, c, int(r), int(f))] = (b, ba)
    return out


def window_mean(b, v, lo, hi):
    m = (b >= lo) & (b <= hi); return float(np.mean(v[m])) if m.any() else np.nan


def paired(rows, x, a, cond, lo, hi):
    """Mean over clusters of the per-cluster mean of per-learner (x - a) window means."""
    per = defaultdict(list)
    for (s, c, r, f), (b, v) in rows.items():
        if s != x or c != cond or (a, c, r, f) not in rows:
            continue
        bx = window_mean(b, v, lo, hi); ba_ = window_mean(*rows[(a, c, r, f)], lo, hi)
        if np.isfinite(bx) and np.isfinite(ba_):
            per[r].append(bx - ba_)
    cm = [np.mean(v) for v in per.values()]
    return float(np.mean(cm)) if cm else np.nan


def run(stage, pairs):
    root = _root(); rows = {}
    labels = pd.read_csv(root.parents[1] / "research_campaign_20261018" / "opus_pooled" / "data" / "POOLED_MANIFEST.csv", index_col=0)["y"]
    for fp in sorted((root / "exports" / stage).glob("predictions_f32*.npz")):
        rows.update(ba_rows(np.load(fp), labels))
    res = {"stage": stage, "contrasts": {}}
    for (x, a, cond) in pairs:
        for (lo, hi, w) in ((8, 24, "B8_B24"), (8, 60, "B8_B60"), (28, 60, "B28_B60")):
            res["contrasts"][f"{x}-{a}|{cond}|{w}"] = paired(rows, x, a, cond, lo, hi)
    return res


def compare(stage, res, ev):
    diffs = {}
    for k, v in res["contrasts"].items():
        xa, cond, w = k.split("|"); x, a = xa.split("-", 1)
        ref = ev(cond, x, a, w)
        if ref is not None:
            diffs[k] = {"recomputed": v, "evaluator": ref, "abs_diff": abs(v - ref)}
    mx = max(d["abs_diff"] for d in diffs.values()) if diffs else np.nan
    out = {"stage": stage, "max_abs_diff": mx, "pass": bool(np.isfinite(mx) and mx <= 1e-9), "rows": diffs}
    p = _root() / "exports" / stage / "RECOMPUTE_ACCEPTANCE.json"; p.write_text(json.dumps(out, indent=1), encoding="utf-8"); print(json.dumps({k: out[k] for k in ("stage", "max_abs_diff", "pass")}))


def g2():
    R = json.loads((_root() / "dev" / "G2_RESULT.json").read_text(encoding="utf-8"))
    systems = [s for s in R["contrasts"]["STD"]]
    pairs = [(s, "C1", c) for s in systems for c in ("STD", "K5", "K4")]
    res = run("g2", pairs)

    def ev(cond, x, a, w):
        c = R["contrasts"].get(cond, {}).get(x, {}); key = {"B8_B24": "dBA_B8_B24", "B8_B60": "dBA_B8_B60", "B28_B60": "dBA_B28_B60"}[w]
        return c.get(key, {}).get("mean")
    compare("g2", res, ev)


def g3():
    R = json.loads((_root() / "dev" / "G3_RESULT.json").read_text(encoding="utf-8")); pairs = [tuple(p.split("|")) for p in R["recompute_pairs"]]
    res = run("g3", pairs)

    def ev(cond, x, a, w):
        key = {"B8_B24": "dBA_B8_B24", "B8_B60": "dBA_B8_B60", "B28_B60": "dBA_B28_B60"}[w]
        return R["contrasts"].get(cond, {}).get(f"{x}-{a}", {}).get(key, {}).get("mean")
    compare("g3", res, ev)


def g4():
    R = json.loads((_root() / "validation" / "G4_RESULT.json").read_text(encoding="utf-8")); pairs = [tuple(p.split("|")) for p in R["recompute_pairs"]]
    res = run("g4", pairs)

    def ev(cond, x, a, w):
        key = {"B8_B24": "dBA_B8_B24", "B8_B60": "dBA_B8_B60", "B28_B60": "dBA_B28_B60"}[w]
        return R["contrasts"].get(cond, {}).get(f"{x}-{a}", {}).get(key, {}).get("mean")
    compare("g4", res, ev)


if __name__ == "__main__":
    {"g2": g2, "g3": g3, "g4": g4}[sys.argv[1]]()
