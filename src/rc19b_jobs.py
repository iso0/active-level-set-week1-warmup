"""RC19B unit lists for the persistent queue (src/rc19_runner.ps1; plan opus_pooled/runner/PLAN.json).
Outputs: outputs/research_campaign_20261018/opus_rc19b/<job>/units/<unit>.json.gz (unit protocol of src/rc18_common.run_units).
    python -m src.rc19b_jobs work <job> [--threads 1]
"""
from __future__ import annotations

import sys

import src.rc18_common as RC
import src.rc19_eval as EV
import src.rc19_pool as P

OUT = RC.ROOT / "outputs" / "research_campaign_20261018" / "opus_rc19b"
REPLAY_BUDGETS = list(range(8, 61, 4))
REPLAY_PATHS = ("E1_STRADDLE", "PHYSCF_ATS_MARGIN", "E1_MAXIMIN")      # existing RC19 final paths (repeats 3-10)


def units(job):
    if job == "b-replay":
        return [(f"r{r}_f{f}__{src}", ("replay", src, r, f)) for r in P.FINAL_REPEATS for f in range(1, 6) for src in REPLAY_PATHS]
    if job == "b-replay-k":                                            # fold-size factor on the label-free paths
        return [(f"r{r}_f{f}__E1_MAXIMIN__K", ("replay_k", "E1_MAXIMIN", r, f)) for r in P.FINAL_REPEATS for f in range(1, 6)]
    if job == "b-dur-replay":
        import src.rc19b_duration as D
        return [(f"r{r}_f{f}__{m}__{a}", ("dur_replay", (m, a), r, f)) for r in P.FINAL_REPEATS for f in range(1, 6) for (m, a) in D.REPLAY_ARMS]
    import src.rc19b_final as F
    return F.units(job)


def work(job):
    RC.limit_threads(1); U = units(job); M = P.manifest(); spec = dict(U); reps = sorted({s[2] for _, s in U}); T = {(t["repeat"], t["fold"]): t for t in P.tasks(reps)}
    if job.startswith("b-final"):
        import src.rc19b_final as F
        F.check()

    def fn(name):
        kind, a, r, f = spec[name]; t = T[(r, f)]
        if kind == "replay":
            import src.rc19b_keyhole as K
            u = RC.read_json_gz(P.OUT / "final" / "final-label" / "units" / f"r{r}_f{f}__label__{a}__path.json.gz")
            return K.replay_unit(t, u, M, REPLAY_BUDGETS)
        if kind == "replay_k":
            import src.rc19b_keyhole as K
            u = RC.read_json_gz(P.OUT / "final" / "final-label" / "units" / f"r{r}_f{f}__label__{a}__path.json.gz")
            return K.replay_k_unit(t, u, M, REPLAY_BUDGETS)
        if kind == "dur_replay":
            import src.rc19b_duration as D
            m, acq = a; u = RC.read_json_gz(P.OUT / "final" / "final-reg" / "units" / f"r{r}_f{f}__reg__{m}__{acq}.json.gz")
            return D.replay_unit(t, u, M)
        if kind == "label":
            import src.rc19b_keyhole as K
            return K.run_adaptive(t, a, 60, M=M)
        if kind == "reg":
            import src.rc19b_duration as D
            m, acq = a; return D.run_reg_b(t, m, acq, 80, M=M)
        raise ValueError(kind)
    d = OUT / job
    RC.run_units([n for n, _ in U], fn, d / "units", d / "locks", d / "failed", log=lambda s: print(s, flush=True))


if __name__ == "__main__":
    if sys.argv[1] == "work":
        work(sys.argv[2])
    elif sys.argv[1] == "list":
        print({j: len(units(j)) for j in ("b-replay",)})
