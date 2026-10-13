"""Invariant checks for the Week 20 Track 1 extension (DEV repeats 5-8 + guard ablation); reads committed tables only."""
import json
import subprocess
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

ROOT = Path(__file__).resolve().parents[2]
X = ROOT / "outputs" / "week20_active_temporal_development" / "track1_ext"
needs = pytest.mark.skipif(not (X / "ledger_all_queries.csv.gz").exists(), reason="extension outputs absent")
GUARD = "WHOLE_E1_GUARD_STRADDLE"


def _git(*a):
    return subprocess.run(["git", *a], capture_output=True, text=True, cwd=ROOT)


def test_manifest_frozen_before_results():
    first = _git("log", "--format=%H", "--diff-filter=A", "--", "outputs/week20_active_temporal_development/track1_ext/manifest_track1_ext.json").stdout.split()
    assert first and first[-1].startswith("c96eaefb")
    led = _git("log", "--format=%H", "--diff-filter=A", "--", "outputs/week20_active_temporal_development/track1_ext/ledger_all_queries.csv.gz").stdout.split()
    if led:
        assert _git("merge-base", "--is-ancestor", first[-1], led[-1]).returncode == 0 and first[-1] != led[-1]
    m = json.loads((X / "manifest_track1_ext.json").read_text(encoding="utf-8"))
    frozen = json.loads(_git("show", "acb14d4f:outputs/week20_active_temporal_development/track1/manifest_track1.json").stdout)
    for c in ("src/week20_track1_al.py", "src/week18_engine.py", "src/week18_tasks.py"):
        assert m["code_sha256"][c] == frozen["code_sha256"][c]                       # frozen Track 1 code unchanged


@needs
def test_ledgers_complete_paid_only_and_identical_startup():
    led = pd.read_csv(X / "ledger_all_queries.csv.gz")
    g = led.groupby(["task", "repeat", "fold", "arm"])
    assert (g.query_index.max() == 80).all() and (g.sim_id.nunique() == 80).all() and set(led.repeat) == {5, 6, 7, 8}
    assert g.ngroups >= 200
    st = led[led.rule == "startup_maximin"]
    for _, h in st.groupby(["task", "repeat", "fold"]):
        assert len({tuple(x.sort_values("query_index").sim_id) for _, x in h.groupby("arm")}) == 1
    f = pd.read_csv(X / "fit_diagnostics_all.csv.gz")
    assert (f.labels_passed == f.budget).all() and (f.status == "ok").all()
    e1 = f[f.arm.isin(["WHOLE_E1_STRADDLE", "ACTIVE_E1_STRADDLE"])]
    assert (e1.threshold_replication_abs_diff.fillna(0) < 1e-12).all()
    d = f[f.arm == GUARD]
    guard_steps = d.slope_nonpositive.astype(bool) & np.isclose(d.u_um, 111.0)
    assert (d[~guard_steps].threshold_replication_abs_diff.fillna(0) < 1e-12).all()      # the guard is the only change


@needs
def test_fidelity_guard_identity_and_reproduction():
    fid = pd.read_csv(X / "fidelity_vs_week18_caches.csv")
    assert fid.rows_equal.all()
    known = (fid.task == "R1_POOLED") & (fid.repeat == 8) & (fid.fold == 1) & (fid.arm == "G3_MARGIN")      # X-H0 falsified here (reported)
    assert fid[~known].max_abs_dp.max() <= 1e-4 and fid[known].max_abs_dp.max() > 1e-4
    diag = pd.read_csv(X / "DIAG_g3_R1_POOLED_r8f1_divergence.csv")
    one, four = diag[diag.variant == "engine_run_1_threads"], diag[diag.variant == "engine_run_4_threads"]
    assert one.max_abs_dp_vs_ledgered.max() == 0 and four.max_abs_dp_vs_cache.max() <= 1e-4   # 1 thread = extension; 4 threads = Week 18 cache
    gc = pd.read_csv(X / "guard_identity_and_activation.csv")
    ide = gc[gc.identity_expected]
    assert ide.paths_identical.all() and (ide.max_abs_dp_D_vs_A == 0).all()
    assert (gc[gc.D_guard_activations > 0].A_nonpositive_slope_steps > 0).all()
    dec = json.loads((X / "decision.json").read_text(encoding="utf-8"))
    assert dec["repeats_1_4_AULC_reproduced_max_abs_diff"] < 1e-12
