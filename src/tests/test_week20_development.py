"""Invariant checks for the Week 20 development outputs (reads committed tables; fits nothing)."""
import json
import subprocess
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "outputs" / "week20_active_temporal_development"
T1, T2 = OUT / "track1", OUT / "track2"
needs_t1 = pytest.mark.skipif(not (T1 / "ledger_all_queries.csv.gz").exists(), reason="Track 1 outputs absent")
needs_t2 = pytest.mark.skipif(not (T2 / "evaluation_per_run.csv.gz").exists(), reason="Track 2 outputs absent")


def _git(*a):
    return subprocess.run(["git", *a], capture_output=True, text=True, cwd=ROOT)


@needs_t1
def test_ledgers_complete_and_startup_identical():
    led = pd.read_csv(T1 / "ledger_all_queries.csv.gz")
    g = led.groupby(["task", "repeat", "fold", "arm"])
    assert g.ngroups == 180 and (g.query_index.max() == 80).all() and (g.sim_id.nunique() == 80).all()
    st = led[led.rule == "startup_maximin"]
    for _, h in st.groupby(["task", "repeat", "fold"]):
        seqs = {a: tuple(x.sort_values("query_index").sim_id) for a, x in h.groupby("arm")}
        assert len(set(seqs.values())) == 1                                   # identical initial revealed information


@needs_t1
def test_fits_used_paid_data_only_and_reproduce_history():
    f = pd.read_csv(T1 / "fit_diagnostics_all.csv.gz")
    assert (f.labels_passed == f.budget).all() and (f.status == "ok").all()
    e1 = f[f.arm != "G3_MARGIN"]
    assert (e1.threshold_replication_abs_diff.fillna(0) < 1e-12).all()
    fid = pd.read_csv(T1 / "fidelity_vs_week18_caches.csv")
    assert fid.rows_equal.all() and fid.max_abs_dp.max() <= 1e-4


def test_freezes_precede_results():
    assert _git("merge-base", "--is-ancestor", "acb14d4f", "d50e43b9").returncode == 0    # Track 1 manifest before Track 1 results
    log = _git("log", "--format=%H", "-1", "--", "outputs/week20_active_temporal_development/track1/manifest_track1.json").stdout.strip()
    assert log.startswith("acb14d4f")
    t2 = _git("log", "--format=%H", "--diff-filter=A", "--", "outputs/week20_active_temporal_development/track2/manifest_track2.json").stdout.strip().splitlines()
    assert t2 and t2[-1].startswith("a17126cf")


def test_track2_checkpoints_and_scalar_reference():
    ck = pd.read_csv(T2 / "checkpoints.csv")
    assert len(ck) == 30 and set(ck.budget) == {16, 40, 80} and (ck.K == 360).all()
    sc = pd.read_csv(T2 / "scalar_reference_fits.csv")
    assert sc.max_abs_diff_vs_pilot_saved.max() < 1e-10
    v = json.loads((T2 / "svgp_validation.json").read_text())
    assert v["kronecker_vs_dense"]["pass_1e-8"] and v["svgp_M375"]["max_abs_mean_diff"] < 1e-3


@needs_t2
def test_track2_evaluation_coverage():
    ev = pd.read_csv(T2 / "evaluation_per_run.csv.gz")
    n_traj = int((pd.read_csv(T2 / "trajectory_inventory.csv").rows > 0).sum())
    for m in ("functional", "svgp", "scalar_A_GP", "mean_trajectory"):
        assert (ev.model == m).sum() == 3 * 2 * n_traj                                 # every held-out run with a trajectory, every checkpoint
    for m in ("functional", "svgp", "mean_trajectory"):
        assert not ev[ev.model == m].traj_rmse.isna().any() and (ev[ev.model == m].n_unsupported_obs_bins == 0).all()
    sv = [json.loads(l) for l in (T2 / "svgp_fits.jsonl").read_text().splitlines() if l.strip()]
    assert sum(r["tag"] == "svgp" for r in sv) == 30 and len({r["checkpoint"] for r in sv if r["tag"] == "svgp"}) == 30


def test_track2_rules_precede_evaluation():
    rules = _git("log", "--format=%H", "--diff-filter=A", "--", "outputs/week20_active_temporal_development/track2/EVALUATION_RULES_T2.md").stdout.split()
    ev = _git("log", "--format=%H", "--diff-filter=A", "--", "outputs/week20_active_temporal_development/track2/evaluation_per_run.csv.gz").stdout.split()
    assert rules
    if ev:
        assert _git("merge-base", "--is-ancestor", rules[-1], ev[-1]).returncode == 0 and rules[-1] != ev[-1]


def test_ioan_addendum():
    inv = pd.read_csv(OUT / "ioan_addendum/image_inventory_addendum.csv")
    assert len(inv) == 3 and inv.verified.all() and set(inv.view) == {"front", "side", "top"} and (inv.frame_idx == 81).all()
    gal = (ROOT / "outputs/week19_temporal_regime_dev_pilot/ioan_gallery/GALLERY.md").read_bytes()
    old = subprocess.run(["git", "show", "7707d7f4:outputs/week19_temporal_regime_dev_pilot/ioan_gallery/GALLERY.md"], capture_output=True, cwd=ROOT).stdout
    assert gal.replace(b"\r\n", b"\n").startswith(old.replace(b"\r\n", b"\n").rstrip(b"\n"))      # earlier gallery preserved; addendum appended
