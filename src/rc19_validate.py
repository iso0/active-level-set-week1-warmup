"""RC19 paid-only validation of the reveal interface and every learner family (no evaluation, no result reading).

Shadow test: each arm is run twice on the same task - once with the real pooled table, once with the outcomes of EVERY row the
first run never paid (all unpaid candidates and all test rows) replaced by random values (labels, depth, all physical
summaries, record-quality flags). A learner that reads only what it paid must produce the identical query path and identical
test predictions. Also checks: test rows cannot be revealed, a row cannot be paid twice, the startup is paid and counted.
    python -m src.rc19_validate
"""
from __future__ import annotations

import json

import numpy as np

import src.rc18_common as RC
import src.rc19_learn as LN
import src.rc19_pool as P


def _corrupt(M, keep_ids, seed):
    rng = np.random.default_rng(seed); X = M.copy(); m = ~X.index.isin(list(keep_ids))
    X.loc[m, "y"] = rng.integers(0, 2, m.sum()); X.loc[m, "A_um"] = rng.uniform(5, 500, m.sum())
    for c in P.TARGETS:
        X.loc[m, c] = rng.normal(0, 10, m.sum())
    X.loc[m, "short_record"] = rng.random(m.sum()) < 0.5
    return X


def _same(a, b):
    return json.dumps(a, sort_keys=True, default=str) == json.dumps(b, sort_keys=True, default=str)


def main():
    RC.limit_threads(1); M = P.manifest(); t = P.tasks((1,))[0]; out = {"utc": RC.utc(), "task": {"repeat": t["repeat"], "fold": t["fold"]}, "checks": {}}
    rev = P.Reveal(t, M)
    try:
        rev.reveal(int(t["test"][0])); out["checks"]["test_row_refused"] = False
    except PermissionError:
        out["checks"]["test_row_refused"] = True
    rev.reveal(int(t["pool"][0]))
    try:
        rev.reveal(int(t["pool"][0])); out["checks"]["double_pay_refused"] = False
    except ValueError:
        out["checks"]["double_pay_refused"] = True
    out["checks"]["unpaid_rows_hidden"] = bool(np.isnan(np.delete(rev.paid_Y(), rev.paid, axis=0)).all() and (np.delete(rev.paid_y(), rev.paid) == -1).all())
    arms = [("reg", "SHQ", "MOIVR"), ("reg", "M0Q", "RANDOM"), ("reg", "SHQH", "MAXIMIN"), ("region", "SHQ", "STRADDLE"), ("region", "M0", "TRUVAR"),
            ("label", "G3_MARGIN", None), ("label", "E1_STRADDLE", None), ("label", "PHYSCF_ATS_MARGIN", None), ("label", "PHYSMC_AT_MARGIN", None)]
    for kind, a, acq in arms:
        def go(Mx):
            if kind == "reg":
                return LN.run_reg(t, a, acq, 20, record=range(8, 21, 4), M=Mx)
            if kind == "region":
                return LN.run_region(t, a, acq, 20, M=Mx)
            return LN.run_label(t, a, 24, M=Mx)
        r1 = go(M); keep = set(r1["paid_ids"]); r2 = go(_corrupt(M, keep, 7))
        key = f"{kind}:{a}:{acq or ''}"
        out["checks"][key] = {"identical_path": r1["paid_ids"] == r2["paid_ids"], "identical_predictions": _same(r1["evals"], r2["evals"]),
                              "startup_paid_and_counted": r1["paid"][:P.B0] == [int(i) for i in t["path"][:P.B0]] and r1["queries"] == len(r1["paid"]),
                              "queries": r1["queries"], "seconds": round(r1["seconds"], 1)}
        print(json.dumps({key: out["checks"][key]}), flush=True)
    flat = [v for v in out["checks"].values() if isinstance(v, bool)] + [all(v[k] for k in ("identical_path", "identical_predictions", "startup_paid_and_counted"))
                                                                         for v in out["checks"].values() if isinstance(v, dict)]
    out["status"] = "PASS" if all(flat) else "FAIL"
    (P.DATA / "PAID_ONLY_VALIDATION.json").write_text(json.dumps(out, indent=1), encoding="utf-8")
    print(out["status"])


if __name__ == "__main__":
    main()
