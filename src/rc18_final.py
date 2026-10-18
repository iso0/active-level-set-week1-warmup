"""RC18 final programme driver (PROTOCOL_20261018.md): final repeats 5-8; units are checkpointed by src/rc18_common.run_units.

Jobs (one runner job each; a worker refuses to start unless every manifest hash matches):
  reg-new-maximin   NEW x {M0, M0Q, SHQ, TRQ, TRSQ} x MAXIMIN                      100 units
  reg-old-maximin   OLD x {M0, SHQ} x MAXIMIN                                       40 units
  reg-designs       NEW x {M0, TRSQ} and OLD x {M0, SHQ} x {RANDOM, MOIVR}          160 units
  region            {NEW, OLD} x {M0, RICH} x 6 acquisitions, B8-B40               480 units
  label             NEW x 5 label arms, B8-B40                                      100 units
    python -m src.rc18_final manifest | check | <job> | evaluate
"""
from __future__ import annotations

import json
import sys

import src.jdl_stage_m as SMM
import src.rc18_campaign as C
import src.rc18_common as RC

FIN = C.OUT / "final"
MANIFEST = FIN / "RC18_FINAL_MANIFEST.json"
REPEATS = (5, 6, 7, 8)
CODE = ("src/rc18_final.py", "src/rc18_campaign.py", "src/rc18_gp.py", "src/rc18_common.py", "src/rc18_eval.py", "src/jdl_phys_al.py",
        "src/jdl_stage_m.py", "src/week18_engine.py", "src/jdl_evaluate.py",
        "outputs/research_campaign_20261018/astra_pilot/astra_monitor_discovery_20261016/discovery.py")
DATA = ("outputs/research_campaign_20261018/opus/data/SUMMARIES.csv", "outputs/research_campaign_20261018/opus/main/old_emulators/mu_OLD_at_NEW.csv",
        "outputs/research_campaign_20261018/opus/main/old_emulators/EMULATORS.json", "outputs/joint_depth_label_development/physical/physical_summaries.csv",
        "outputs/joint_depth_label_development/phys_al/extracted_summaries.csv", "outputs/research_campaign_20261018/opus/PROTOCOL_20261018.md")


def jobs():
    J = {"reg-new-maximin": [("reg", "NEW", m, "MAXIMIN") for m in ("M0", "M0Q", "SHQ", "TRQ", "TRSQ")],
         "reg-old-maximin": [("reg", "OLD", m, "MAXIMIN") for m in ("M0", "SHQ")],
         "reg-designs": [("reg", p, m, a) for p, ms in (("NEW", ("M0", "TRSQ")), ("OLD", ("M0", "SHQ"))) for m in ms for a in ("RANDOM", "MOIVR")],
         "region": [("region", p, m, a) for p in ("NEW", "OLD") for m in ("M0", C.RICH[p]) for a in C.REGION_ACQS],
         "label": [("label", "NEW", None, a) for a in C.LABEL_ARMS]}
    return J


def unit_list(job):
    out = {}
    for kind, pop, m, a in jobs()[job]:
        for t in C.tasks(pop, REPEATS):
            name = f"{pop}__r{t['repeat']}_f{t['fold']}__{m or 'label'}__{a}"
            out[name] = (kind, pop, t, m, a)
    return out


def write_manifest():
    man = {"study": "RC18_FINAL", "status": "FROZEN BEFORE ANY FINAL OUTCOME", "written_utc": RC.utc(), "parent_commit": SMM._git("rev-parse", "HEAD"),
           "repeats": list(REPEATS), "jobs": {k: [list(map(str, x)) for x in v] for k, v in jobs().items()},
           "units": {k: len(unit_list(k)) for k in jobs()}, "rich": C.RICH, "region": {"response": "vmax_spike_logratio", "tau": C.SPIKE_TAU},
           "code_sha256": {c: SMM.sha256(SMM.ROOT / c) for c in CODE}, "data_sha256": {c: SMM.sha256(SMM.ROOT / c) for c in DATA}}
    FIN.mkdir(parents=True, exist_ok=True); MANIFEST.write_text(json.dumps(man, indent=1), encoding="utf-8"); print(json.dumps(man["units"]))


def check():
    man = json.loads(MANIFEST.read_text(encoding="utf-8"))
    if not SMM._git("log", "--format=%H", "--", str(MANIFEST.relative_to(SMM.ROOT)).replace("\\", "/")):
        raise SystemExit("commit the RC18 final manifest before any final run")
    for grp in ("code_sha256", "data_sha256"):
        for c, h in man[grp].items():
            if SMM.sha256(SMM.ROOT / c) != h:
                raise SystemExit(f"{c} changed after the RC18 final freeze")
    return man


def work(job):
    check(); RC.limit_threads(1); T = {p: C.targets(p) for p in ("NEW", "OLD")}; U = unit_list(job)
    def fn(name):
        kind, pop, t, m, a = U[name]
        if kind == "reg":
            return C.run_reg(t, pop, m, a, T[pop])
        if kind == "region":
            return C.run_region(t, pop, m, a, T[pop])
        return C.run_label(t, pop, a)
    d = FIN / job
    RC.run_units(list(U), fn, d / "units", d / "locks", d / "failed", log=lambda s: print(s, flush=True))


if __name__ == "__main__":
    step = sys.argv[1]
    if step == "manifest":
        write_manifest()
    elif step == "check":
        check(); print("manifest OK")
    else:
        work(step)
