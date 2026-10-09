"""Unit tests for the Week 19 frame-label sequence descriptors (synthetic sequences only; no data access)."""
import math

import numpy as np

from src.week19_sequences import alternative_labels, describe, runs
from src.week19_series import _hold_dt, _time_above


def d(seq):
    return describe(seq.split())[0]


def test_runs_never_bridge_gaps():
    assert runs("K K IE K C K".split()) == [(0, 1), (3, 3), (5, 5)]


def test_conduction_only_and_ratios():
    r = d("IE F F C C SS")
    assert r["descriptor"] == "conduction_only" and r["has_keyhole_reproduced"] == 0
    assert r["frac_K_FCK"] == 0 and r["frac_K_KC"] == 0


def test_K_over_KC_undefined_without_active_frames():
    r = d("IE F F SS")
    assert r["descriptor"] == "forming_only"
    assert math.isnan(r["frac_K_KC"]) and r["frac_K_FCK"] == 0
    alt = alternative_labels(r)
    assert math.isnan(alt["alt_K_KC_ge05"]) and alt["alt_K_FCK_ge05"] == 0


def test_K_then_only_C():
    r = d("IE F K K C C C SS")
    assert r["descriptor"] == "K_then_C__no_later_K" and r["K_then_only_C"] == 1
    assert r["n_K_blocks"] == 1 and r["alternation"] == 0 and r["n_switch_K_to_C"] == 1
    assert r["final_active_regime"] == "C" and r["K_ongoing_at_observation_end"] == 0


def test_technical_gap_is_not_alternation():
    r = d("F K K SS K K")
    # two strict K runs separated by a technical-only gap: one K block, no observed alternation
    assert r["n_K_runs"] == 2 and r["n_K_gaps_technical_only"] == 1 and r["n_K_blocks"] == 1
    assert r["alternation"] == 0 and r["descriptor"] == "keyhole_only__K_at_end"
    assert r["last_frame_is_K"] == 1 and r["K_ongoing_at_observation_end"] == 1


def test_alternation_requires_observed_conduction():
    r = d("F K C K C")
    assert r["n_K_blocks"] == 2 and r["alternation"] == 1 and r["descriptor"] == "alternating__terminal_C"
    assert r["n_switch_K_to_C"] == 2 and r["n_switch_C_to_K"] == 1
    r = d("F C K C K SS")
    assert r["descriptor"] == "alternating__K_at_end" and r["last_frame_is_K"] == 0 and r["K_ongoing_at_observation_end"] == 1


def test_switch_bracketing_counts_intermediate_frames():
    r = d("F K IE C")
    assert r["n_switch_K_to_C"] == 1 and r["n_switch_bracketing_other_frames"] == 1 and r["n_switch_direct"] == 0


def test_F_after_K_flags_and_week7_transient_difference():
    r = d("F K F C")
    assert r["F_after_active_onset"] == 1 and r["physical_after_last_K"] == "C+F" and r["K_then_only_C"] == 0
    r = d("F C K F")
    # final active regime is K although the last physical label is F (Week 7 would call this transient)
    assert r["final_active_regime"] == "K" and r["last_physical_label"] == "F"


def test_alternative_label_thresholds():
    r = d("F F F F F F F F F F F F F F F F F F K C")   # K/(F+C+K) = 1/20 = 0.05, K/(K+C) = 0.5
    alt = alternative_labels(r)
    assert alt["alt_K_FCK_ge05"] == 1 and alt["alt_K_FCK_ge10"] == 0 and alt["alt_K_KC_ge10"] == 1


def test_time_above_hold_rule():
    t = np.array([0.0, 1.0, 2.0, 4.0])
    depth = np.array([100.0, 120.0, np.nan, 130.0])
    valid = np.isfinite(depth)
    dt = _hold_dt(t)
    ms, frac, rowfrac = _time_above(depth, valid, dt, 111.0)
    # rows 0 and 1 hold 1 s each, the last row holds 0; the invalid row is excluded from both sums
    assert np.isclose(ms, 1e3) and np.isclose(frac, 0.5) and np.isclose(rowfrac, 2 / 3)
