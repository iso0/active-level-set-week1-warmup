"""RC19 pooled from-scratch campaign: unit lists for the runner queue (development and, after the freeze, final jobs).

Unit protocol = src.rc18_common.run_units (O_EXCL claim, atomic checkpoint, failures recorded and never retried, no claim after
the campaign deadline). Outputs: outputs/research_campaign_20261018/opus_pooled/<stage>/<job>/units/<unit>.json.gz.
    python -m src.rc19_jobs work <job> [--threads 1]
    python -m src.rc19_jobs list
"""
from __future__ import annotations

import json
import sys

import src.rc18_common as RC
import src.rc19_pool as P

DEV = {
    # regression: models under the matched MAXIMIN path, plus RANDOM / MOIVR for the simple and the sharing model
    "dev-reg": [("reg", m, "MAXIMIN", 80) for m in ("M0", "M0Q", "SHQ", "SHQH")] + [("reg", m, a, 80) for m in ("M0Q", "SHQ") for a in ("RANDOM", "MOIVR")],
    "dev-region": [("region", m, a, 60) for m in ("M0", "SHQ", "SHQH") for a in ("MAXIMIN", "RANDOM", "STRADDLE", "TRUVAR")],
    "dev-label": [("label", a, None, 60) for a in ("G3_MARGIN", "E1_STRADDLE", "E1_MAXIMIN", "PHYSCF_A_MARGIN", "PHYSCF_AT_MARGIN", "PHYSCF_ATS_MARGIN",
                                                   "PHYSMC_A_MARGIN", "PHYSMC_AT_MARGIN", "PHYSMC_ATS_MARGIN", "PHYSCF_ATS_MAXIMIN")],
    # added after dev-label (motivated by the NEW fast-scan corner failure; every paid output, no selection)
    "dev-label2": [("label", a, None, 60) for a in ("PHYSCF_ALL_MARGIN", "PHYSMC_ALL_MARGIN")],
    # bounded D smoke test on development repeats (same code as the final D job)
    "dev-temporal": [("temporal", "M0Q", "PATH", 40)],
    # offline full-pool references (attainable accuracy for absolute target levels; not a learner)
    "dev-full": [("full", m, "FULL_POOL", 0) for m in ("M0Q", "SHQ")],
}


def units(job):
    """(name, spec, repeat, fold) for every unit of a job, in claim order (cheap and informative units first)."""
    stage, specs, reps = ("dev", DEV[job], P.DEV_REPEATS) if job in DEV else (None, None, None)
    if stage is None:
        import src.rc19_final as F
        stage, specs, reps = "final", F.JOBS[job], P.FINAL_REPEATS
    out = []
    for r in reps:
        for f in range(1, 6):
            for sp in specs:
                kind, a, b, bmax = sp
                out.append((f"r{r}_f{f}__{kind}__{a}__{b or 'path'}", sp, r, f))
    return stage, out


def work(job):
    RC.limit_threads(1)
    stage, U = units(job); d = P.OUT / stage / job; T = {(t["repeat"], t["fold"]): t for t in P.tasks(sorted({r for _, _, r, _ in U}))}
    M = P.manifest(); spec = {n: (sp, r, f) for n, sp, r, f in U}
    if stage == "final":
        import src.rc19_final as F
        F.check()
    import src.rc19_learn as LN
    FT = CV = None
    if any(sp[0] == "temporal" for _, sp, _, _ in U):                      # RC18 audited per-run features and early curves (no model)
        import numpy as np
        import pandas as pd
        import src.rc18_temporal as TT
        FT = pd.read_csv(TT.OUT / "FEATURES.csv").set_index("sim_id")[TT.FEATS]; CV = dict(np.load(TT.OUT / "CURVES.npz"))

    def fn(name):
        (kind, a, b, bmax), r, f = spec[name]; t = T[(r, f)]
        if kind == "reg":
            return LN.run_reg(t, a, b, bmax, M=M)
        if kind == "region":
            return LN.run_region(t, a, b, bmax, M=M)
        if kind == "label":
            return LN.run_label(t, a, bmax, M=M)
        if kind == "full":
            return LN.full_reg(t, a, M=M)
        if kind == "temporal":                                                # bounded D: early-horizon endpoint, B16 / B40 of the paid MAXIMIN path
            import src.rc18_temporal as TT
            return {"rows": TT.curve_models(t, "POOLED", a, FT, CV, budgets=(16, 40)), "repeat": r, "fold": f, "model": a}
        raise ValueError(kind)
    RC.run_units([n for n, _, _, _ in U], fn, d / "units", d / "locks", d / "failed", log=lambda s: print(s, flush=True))


if __name__ == "__main__":
    if sys.argv[1] == "work":
        work(sys.argv[2])
    elif sys.argv[1] == "list":
        for j in DEV:
            print(j, len(units(j)[1]))
    else:
        raise SystemExit("usage: work <job> | list")
