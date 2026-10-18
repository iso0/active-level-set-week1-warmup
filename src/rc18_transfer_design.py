"""RC18 addendum A2 (exploratory; PROTOCOL_ADDENDUM_A2.md): which first NEW simulations should be bought once the transfer
model (TRSQ) exists? Designs from B0 on the NEW final tasks (repeats 5-8), budgets B0-B24:
  MAXIMIN0   frozen label-free maximin path from B0 (= the final MAXIMIN units, reused, not rerun)
  RANDOM0    seeded random from B0
  MOIVR0     argmax sum_t IVR_t / Var_t from B0 (offset-only fits below 5 usable rows: no IVR, MAXIMIN path continues)
  GAP0       transfer-gap (Opus's acquisition idea): argmax sum_t [latent var of the residual GP_t(x) + latent var of the
             OLD emulator_t(x)] / Var_t over the 6 NEW primary targets; with < 5 usable paid rows only the OLD-emulator variance
             is used. Var_t = variance of the OLD-emulator predictions over the pool (a fixed, label-free scale).
Imports the frozen modules unchanged; Var_t never uses unpaid NEW outputs.
    python -m src.rc18_transfer_design work | evaluate
"""
from __future__ import annotations

import sys
import time

import numpy as np

import src.rc18_campaign as C
import src.rc18_common as RC
import src.rc18_gp as G

REPEATS = (5, 6, 7, 8)
D = C.OUT / "transfer_design"
BMAX = 24
DESIGNS = ("RANDOM0", "MOIVR0", "GAP0")


def run(task, design, Tt):
    ids = np.asarray(task["ids"]).astype(str); Z = C.zstd(task); pool, test = task["pool"], task["test"]
    cols = C.ALL_T; Y = Tt.reindex(ids)[cols].to_numpy(float); short = C.qa_short(ids)
    e = C.emulator_at(ids); E = {k: e[k].to_numpy(float) for k in e.columns}; prim = C.PRIMARY["NEW"]
    scale = {c: max(1e-12, float(np.var(E[f"{c}__mu"][pool]))) for c in prim}
    rng = np.random.default_rng(71000 + 100 * task["repeat"] + task["fold"]); L = []; evals = []; t0 = time.time()
    for b in range(0, BMAX + 1):
        paid = np.asarray(L, int); fits = C.fit_model("TRSQ", Z, Y, paid, cols, emu=E, short=short)
        pr = {c: (None if fits.get(c) is None else [v.tolist() for v in fits[c].predict(test)]) for c in cols}
        evals.append({"budget": b, "pred": pr})
        if b == BMAX:
            break
        unpaid = np.setdiff1d(pool, L)
        if design == "RANDOM0":
            nxt = int(rng.choice(unpaid))
        elif design == "MOIVR0":
            gp_fits = {c: fits[c] for c in prim if isinstance(fits.get(c), C.Fitted)}
            if gp_fits:
                sc = np.zeros(len(unpaid))
                for c, f in gp_fits.items():
                    sc += G.ivr(f.g, None, None, Z[unpaid], None, Z[pool], None) / scale[c]
                nxt = int(unpaid[int(np.argmax(sc))])
            else:
                nxt = int([i for i in task["path"] if i not in set(L)][0])
        elif design == "GAP0":
            sc = np.zeros(len(unpaid))
            for c in prim:
                v = E[f"{c}__lat"][unpaid].copy(); f = fits.get(c)
                if isinstance(f, C.Fitted):
                    v = v + f.predict(unpaid)[1]
                sc += v / scale[c]
            nxt = int(unpaid[int(np.argmax(sc))])
        else:
            raise ValueError(design)
        L.append(nxt)
    return {"population": "NEW", "repeat": task["repeat"], "fold": task["fold"], "model": "TRSQ", "acq": design, "paid": L,
            "paid_ids": [ids[i] for i in L], "test_ids": [ids[i] for i in test], "evals": evals, "seconds": time.time() - t0}


def work():
    import src.rc18_final as F
    F.check(); RC.limit_threads(1); Tt = C.targets("NEW"); U = {}
    for t in C.tasks("NEW", REPEATS):
        for d in DESIGNS:
            U[f"NEW__r{t['repeat']}_f{t['fold']}__TRSQ__{d}"] = (t, d)
    def fn(name):
        t, d = U[name]; return run(t, d, Tt)
    RC.run_units(list(U), fn, D / "units", D / "locks", D / "failed", log=lambda s: print(s, flush=True))


if __name__ == "__main__":
    {"work": work}[sys.argv[1]]()
