"""RC18 addendum A1 (exploratory robustness; PROTOCOL_ADDENDUM_A1.md): the MAXIMIN regression comparison of the final programme
re-run on DEV repeats 3-4 (two more task partitions of the same simulations) with the frozen code of src/rc18_campaign.py.
Not part of the primary verdict. Imports the frozen modules; changes nothing in them.
    python -m src.rc18_robust work | evaluate
"""
from __future__ import annotations

import sys

import src.rc18_campaign as C
import src.rc18_common as RC

REPEATS = (3, 4)
D = C.OUT / "robust_r34"


def units():
    U = {}
    for pop, ms in (("NEW", ("M0", "M0Q", "SHQ", "TRQ", "TRSQ")), ("OLD", ("M0", "SHQ"))):
        for t in C.tasks(pop, REPEATS):
            for m in ms:
                U[f"{pop}__r{t['repeat']}_f{t['fold']}__{m}__MAXIMIN"] = (pop, t, m)
    return U


def work():
    import src.rc18_final as F
    F.check(); RC.limit_threads(1); T = {p: C.targets(p) for p in ("NEW", "OLD")}; U = units()
    def fn(name):
        pop, t, m = U[name]; return C.run_reg(t, pop, m, "MAXIMIN", T[pop])
    RC.run_units(list(U), fn, D / "units", D / "locks", D / "failed", log=lambda s: print(s, flush=True))


def evaluate():
    import src.rc18_eval as E
    import src.rc18_report as REPm
    full = {p: C.full_r2(p, REPEATS) for p in ("NEW", "OLD")}
    R = E.eval_reg(D, ("NEW", "OLD"), REPEATS, full=full)
    d = R[(R["pop"] == "NEW") & R.target.isin(C.PRIMARY["NEW"])]
    a = d[d.model == "M0"].set_index(["target", "repeat"]).budget_to_target; b = d[d.model == "TRSQ"].set_index(["target", "repeat"]).budget_to_target
    S = (a - b); print({"mean_saved_r34": float(S.mean()), "per_repeat": S.groupby("repeat").mean().to_dict(), "per_target": S.groupby("target").mean().to_dict()})
    R.drop(columns=["curve"]).to_csv(D / "eval.csv", index=False, lineterminator="\n")


if __name__ == "__main__":
    {"work": work, "evaluate": evaluate}[sys.argv[1]]()
