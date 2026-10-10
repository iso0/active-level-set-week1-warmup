"""Checks for the Week 19 pilot review (saved predictions only; no learner fit is run by these tests)."""
import re

import numpy as np
import pandas as pd
import pytest

import src.week19_pilot_review as R

needs_review = pytest.mark.skipif(not (R.REV / "B40_classification_changes.csv").exists(), reason="review outputs absent")


def test_margin_identities_and_four_cell_corners():
    w = R.wide()
    assert len(w) == 272 and not w.duplicated(["sim_id", "repeat"]).any()
    for k in R.ARM:
        assert np.abs(w[f"mu_{k}"] - (w[f"margin_{k}"] + w[f"lu_{k}"])).max() < 1e-12          # absolute mean = latent + log u
        assert ((w[f"margin_{k}"] >= 0).astype(int) == (w[f"p_{k}"] >= 0.5).astype(int)).all()  # class is the margin sign
        assert (w[f"cell_{k}{k}"] == w[f"class_{k}"]).all()
    assert np.abs(w.d_margin - (w.d_mu - w.d_lu)).max() < 1e-12


@needs_review
def test_change_table_is_complete_and_attribution_consistent():
    w = R.wide(); ch = pd.read_csv(R.REV / "B40_classification_changes.csv")
    assert len(ch) == int((w.class_W != w.class_A).sum())
    for t in ch.itertuples():
        mean_alone, thr_alone = t.cell_AW != t.cell_WW, t.cell_WA != t.cell_WW
        exp = ("either change alone flips" if mean_alone and thr_alone else "mean change alone flips; threshold change alone does not" if mean_alone
               else "threshold change alone flips; mean change alone does not" if thr_alone else "neither alone flips; only the joint change does")
        assert t.attribution == exp
        assert (t.margin_W >= 0) == bool(t.class_WHOLE) and (t.margin_A >= 0) == bool(t.class_ACTIVE)


@needs_review
def test_late_negative_isolation_rows():
    it = pd.read_csv(R.REV / "late_negative_isolation_by_checkpoint.csv")
    iso = it[it.only_difference_is_late_negative]
    assert set(zip(iso.budget, iso.repeat, iso.fold)) == {(16, 2, 5), (40, 1, 2)}
    same = it[it.n_paid_with_different_response == 0]
    assert len(same) == 1 and (same.u_um_WHOLE == same.u_um_ACTIVE).all() and (same.class_changes == 0).all()   # identical data, identical fit


@needs_review
def test_oracle_cohorts_and_recheck():
    o = pd.read_csv(R.REV / "oracle_vs_GP_same_cohort.csv")
    c = o[o["class"].isin(["positives", "negatives"])]
    n = c.groupby(["budget", "arm"]).n_predictions.sum()
    assert (n.xs(R.ARM["W"], level="arm") == 272).all() and (n.xs(R.ARM["A"], level="arm") == 270).all()
    assert (c.oracle_recheck_disagreements == 0).all()


@needs_review
def test_gallery_is_label_free_and_complete():
    g = (R.GAL / "GALLERY.md").read_text(encoding="utf-8")
    assert not re.search(r"(?i)keyhole|conduction|forming|scanning stopped|has_keyhole|WHOLE_E1|ACTIVE_E1|G3_SHARED|p_keyhole", g)
    inv = pd.read_csv(R.GAL / "image_inventory.csv")
    assert len(inv) == 30 and inv.verified.all() and inv.repo_path.is_unique
    assert set(inv.usability) <= {"usable", "nearly empty", "blank", "unclear", "unreadable", "missing"}
    assert "Keyhole" in (R.GAL / "KEY.md").read_text(encoding="utf-8")


@needs_review
def test_experimental_files_unchanged_and_brief_limits():
    ex = R.experimental_files_unchanged()
    assert ex.unchanged.all() and len(ex) > 20
    t = (R.OUT / "IOAN_MEETING_BRIEF.md").read_text(encoding="utf-8")
    assert len([x for x in t.split() if any(ch.isalnum() for ch in x)]) <= 350
    assert len(re.findall(r"^\*\*Q\d", t, flags=re.M)) <= 5
    assert "similar inputs and depth trajectories" in t and "the morphology difference has not been established" in t
