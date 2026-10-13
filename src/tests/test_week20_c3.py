"""Invariant checks for the Week 20 C3 confirmation (reads committed tables only)."""
import json
import subprocess
from pathlib import Path

import pandas as pd
import pytest

ROOT = Path(__file__).resolve().parents[2]
C3 = ROOT / "outputs" / "week20_active_temporal_development" / "c3"
needs = pytest.mark.skipif(not (C3 / "decision_c3.json").exists(), reason="C3 outputs absent")


def _git(*a):
    return subprocess.run(["git", *a], capture_output=True, text=True, cwd=ROOT)


def test_freeze_precedes_any_c3_output():
    fz = _git("log", "--format=%H", "--diff-filter=A", "--", "outputs/week20_active_temporal_development/c3/freeze_c3.json").stdout.split()
    assert fz and fz[-1].startswith("4164f67b")
    for out in ("c3_tasks_and_startup.csv", "ledger_all_queries.csv.gz", "decision_c3.json"):
        c = _git("log", "--format=%H", "--diff-filter=A", "--", f"outputs/week20_active_temporal_development/c3/{out}").stdout.split()
        if c:
            assert _git("merge-base", "--is-ancestor", fz[-1], c[-1]).returncode == 0 and fz[-1] != c[-1]
    spec = json.loads((C3 / "freeze_c3.json").read_text(encoding="utf-8"))
    frozen = json.loads(_git("show", "acb14d4f:outputs/week20_active_temporal_development/track1/manifest_track1.json").stdout)
    for c in ("src/week20_track1_al.py", "src/week18_engine.py", "src/week18_tasks.py"):
        assert spec["code_sha256"][c] == frozen["code_sha256"][c]
    assert spec["builder_check_on_DEV_5_8"]["identical"]


@needs
def test_c3_runs_complete_once_and_paid_only():
    led = pd.read_csv(C3 / "ledger_all_queries.csv.gz")
    assert set(led.repeat) == {17, 18, 19, 20}
    g = led.groupby(["task", "repeat", "fold", "arm"])
    assert g.ngroups == 180 and (g.query_index.max() == 80).all() and (g.sim_id.nunique() == 80).all()
    st = led[led.rule == "startup_maximin"]
    for _, h in st.groupby(["task", "repeat", "fold"]):
        assert len({tuple(x.sort_values("query_index").sim_id) for _, x in h.groupby("arm")}) == 1
    f = pd.read_csv(C3 / "fit_diagnostics_all.csv.gz")
    assert (f.labels_passed == f.budget).all()
    e1 = f[f.arm != "G3_MARGIN"]
    assert (e1.threshold_replication_abs_diff.fillna(0) < 1e-12).all()


@needs
def test_decision_follows_locked_rule():
    d = json.loads((C3 / "decision_c3.json").read_text(encoding="utf-8"))
    n = d["R3_NEW_ACTIVE_minus_G3"]
    assert d["Q3a"] == (n["mean"] >= 0.02 and n["lo"] > 0)
    assert d["Q3b"] == (d["R3_OLD_ACTIVE_minus_G3"] >= -0.01 and d["R1_POOLED_ACTIVE_minus_G3"] >= -0.01)
    ct = pd.read_csv(C3 / "contrasts.csv")
    r = ct[(ct.task == "R3_NEW") & (ct.arm == "ACTIVE_E1_STRADDLE") & (ct.ref == "G3_MARGIN") & (ct.metric == "BA_AULC")].iloc[0]
    assert abs(r["mean"] - n["mean"]) < 1e-12 and r.repeats == 4
