"""Week 19 Phase 1: frame-label sequences, has_keyhole reproduction and regime descriptors.

Observation only.  Source labels (`label_1`, `label_2`, `label_final`) and their original order are preserved;
`has_keyhole` = any frame with `label_final == 'Keyhole'` (alse.data / Week 7 rule) is re-derived and compared
with the frozen value.  Nothing is relabelled and no simulation is removed.

Ordering: frames of one simulation are ordered by (timestep, source row), as in Week 7
(`week7_phase1_sph_v2_dataset_shift_audit.sequence_audit`).

Episode conventions (no bridging):
  * K run    = maximal block of consecutive frames labelled Keyhole.  Any other label, including technical labels
               (Initial Emptiness, Scanning Stopped, Solidifying Stopped, Screenshot Bug, Unsure) or Forming Phase,
               ends a run.  Runs are never joined across a gap.
  * K block  = K runs that are not separated by an observed Conduction frame (used only to decide alternation;
               it does not claim that Keyhole persisted through the gap).
  * alternation = >= 2 K blocks, i.e. an observed Conduction frame between Keyhole frames.
  * final active regime = label of the last frame labelled Conduction or Keyhole.  "Final active regime = K" is
               called "K ongoing at observation end"; it is never renamed "continuous/persistent K".
Ratios: K/(F+C+K) (Week 7 `keyhole_fraction_of_relevant_physical_frames`) and Ioan's K/(K+C); the second is
undefined (NaN), not zero, when K+C = 0.
"""
from __future__ import annotations

import hashlib

import numpy as np
import pandas as pd

from src.week19_sources import NEW_LABEL_FILE, NEW_REV, OLD_LEDGERS, OLD_REV, eligible_new, eligible_old, local_file, lp

CODE = {"Initial Emptiness": "IE", "Forming Phase": "F", "Conduction": "C", "Keyhole": "K",
        "Scanning Stopped": "SS", "Solidifying Stopped": "SoS", "Screenshot Bug": "SB", "Unsure": "U"}
PHYSICAL = {"F", "C", "K"}
TECHNICAL = {"IE", "SS", "SoS", "SB", "U"}
SOURCE_COLUMNS = ["name", "hash", "P", "VX", "LS", "ST", "bug_free", "correctly_finished", "timestep",
                  "label_1", "label_2", "label_final"]


def _read_ledger(path, campaign, partition=None):
    df = pd.read_csv(lp(path), dtype={"label_1": str, "label_2": str, "label_final": str})
    if df.columns.tolist() != SOURCE_COLUMNS:
        raise RuntimeError(f"{path}: unexpected schema {df.columns.tolist()}")
    df.insert(0, "source_row", np.arange(len(df), dtype=int))
    df.insert(0, "campaign", campaign)
    df.insert(1, "partition", partition if partition else "NEW_OCT")
    return df.rename(columns={"name": "sim_id"})


def load_labels():
    """Eligible frames only (405 OLD + 136 NEW); returns (frames, membership_audit)."""
    old = eligible_old(); new = eligible_new()
    parts = []
    for part, fname in OLD_LEDGERS.items():
        parts.append(_read_ledger(local_file(OLD_REV, fname), "OLD", part))
    oldL = pd.concat(parts, ignore_index=True)
    newL = _read_ledger(local_file(NEW_REV, NEW_LABEL_FILE), "NEW")
    audit = {
        "old_ledger_experiments": int(oldL.sim_id.nunique()),
        "old_ledger_frames": int(len(oldL)),
        "old_experiments_in_more_than_one_partition": int((oldL.groupby("sim_id").partition.nunique() > 1).sum()),
        "old_eligible_present": int(old.sim_id.isin(oldL.sim_id).sum()),
        "old_not_eligible": sorted(set(oldL.sim_id) - set(old.sim_id)),
        "new_label_file_experiments": int(newL.sim_id.nunique()),
        "new_eligible_present": int(new.sim_id.isin(newL.sim_id).sum()),
        "new_not_eligible_count": int(len(set(newL.sim_id) - set(new.sim_id))),
    }
    # Partition recorded in the frozen population must agree with the ledger partition.
    pmap = oldL.drop_duplicates("sim_id").set_index("sim_id").partition
    audit["old_partition_mismatch"] = int((old.set_index("sim_id").partition != pmap.reindex(old.sim_id).to_numpy()).sum())
    oldL = oldL[oldL.sim_id.isin(old.sim_id)]
    # The 49 non-eligible (Bug-withheld) NEW runs are dropped here, before any label is interpreted.
    newL = newL[newL.sim_id.isin(new.sim_id)]
    frames = pd.concat([oldL, newL], ignore_index=True)
    frames["code"] = frames.label_final.map(CODE)
    if frames.code.isna().any():
        raise RuntimeError(f"unknown label_final values: {sorted(frames.loc[frames.code.isna(), 'label_final'].unique())}")
    frames["code_1"] = frames.label_1.map(CODE); frames["code_2"] = frames.label_2.map(CODE)
    frames = frames.sort_values(["campaign", "sim_id", "timestep", "source_row"], kind="stable").reset_index(drop=True)
    frames["frame_pos"] = frames.groupby("sim_id").cumcount()
    return frames, audit


def runs(codes, target="K"):
    """(start, end) inclusive index pairs of maximal consecutive runs of `target`."""
    out, start = [], None
    for i, c in enumerate(codes):
        if c == target and start is None:
            start = i
        if c != target and start is not None:
            out.append((start, i - 1)); start = None
    if start is not None:
        out.append((start, len(codes) - 1))
    return out


def gap_type(gap):
    s = set(gap)
    if "C" in s:
        return "contains_C"
    if "F" in s:
        return "F_no_C"
    return "technical_only"


def describe(codes):
    """Frame-based descriptors of one ordered label sequence (list of codes)."""
    codes = list(codes)
    n = {k: codes.count(k) for k in ["IE", "F", "C", "K", "SS", "SoS", "SB", "U"]}
    nF, nC, nK = n["F"], n["C"], n["K"]
    r = {f"n_{k}": v for k, v in n.items()}
    r["n_frames"] = len(codes)
    r["has_keyhole_reproduced"] = int(nK > 0)
    r["has_conduction"] = int(nC > 0)
    r["frac_K_FCK"] = nK / (nF + nC + nK) if (nF + nC + nK) else np.nan
    r["frac_K_KC"] = nK / (nK + nC) if (nK + nC) else np.nan          # undefined, not zero, if K+C = 0
    kr = runs(codes, "K")
    r["n_K_runs"] = len(kr)
    r["longest_K_run_frames"] = max((b - a + 1 for a, b in kr), default=0)
    gaps = [codes[kr[i][1] + 1:kr[i + 1][0]] for i in range(len(kr) - 1)]
    gt = [gap_type(g) for g in gaps]
    r["n_K_gaps_contains_C"] = gt.count("contains_C")
    r["n_K_gaps_F_no_C"] = gt.count("F_no_C")
    r["n_K_gaps_technical_only"] = gt.count("technical_only")
    r["n_K_blocks"] = (len(kr) - gt.count("F_no_C") - gt.count("technical_only")) if kr else 0
    r["alternation"] = int(r["n_K_blocks"] >= 2)
    act = [(i, c) for i, c in enumerate(codes) if c in ("C", "K")]
    sw = [(act[j - 1], act[j]) for j in range(1, len(act)) if act[j][1] != act[j - 1][1]]
    r["n_switch_K_to_C"] = sum(1 for a, b in sw if a[1] == "K")
    r["n_switch_C_to_K"] = sum(1 for a, b in sw if a[1] == "C")
    r["n_switch_direct"] = sum(1 for a, b in sw if b[0] == a[0] + 1)
    r["n_switch_bracketing_other_frames"] = sum(1 for a, b in sw if b[0] > a[0] + 1)
    first = lambda c: next((i for i, x in enumerate(codes) if x == c), np.nan)
    last = lambda c: next((len(codes) - 1 - i for i, x in enumerate(reversed(codes)) if x == c), np.nan)
    r.update({"first_K_pos": first("K"), "last_K_pos": last("K"), "first_C_pos": first("C"), "last_C_pos": last("C"),
              "first_F_pos": first("F"), "last_F_pos": last("F"),
              "first_active_pos": act[0][0] if act else np.nan, "last_active_pos": act[-1][0] if act else np.nan})
    r["final_active_regime"] = act[-1][1] if act else ""
    phys = [c for c in codes if c in PHYSICAL]
    r["last_physical_label"] = phys[-1] if phys else ""
    r["last_frame_label"] = codes[-1] if codes else ""
    r["last_frame_is_K"] = int(bool(codes) and codes[-1] == "K")
    if act:
        tail = codes[act[-1][0] + 1:]
        r["labels_after_last_active"] = "+".join(sorted(set(tail))) if tail else "none"
    else:
        r["labels_after_last_active"] = ""
    if nK:
        after = [c for c in codes[int(r["last_K_pos"]) + 1:] if c in PHYSICAL]
        r["physical_after_last_K"] = "+".join(sorted(set(after))) if after else "none"
        r["K_then_only_C"] = int(bool(after) and set(after) == {"C"})
        r["C_before_first_K"] = int(nC > 0 and r["first_C_pos"] < r["first_K_pos"])
    else:
        r["physical_after_last_K"] = ""; r["K_then_only_C"] = 0; r["C_before_first_K"] = 0
    fa = r["first_active_pos"]
    r["F_after_active_onset"] = int(bool(act) and any(c == "F" for c in codes[int(fa) + 1:]))
    fp = next((i for i, c in enumerate(codes) if c in PHYSICAL), None)
    r["IE_after_physical_onset"] = int(fp is not None and any(c == "IE" for c in codes[fp + 1:]))
    # Primary, mutually exclusive descriptor.
    if nK == 0 and nC == 0:
        d = "forming_only" if nF else "no_physical_label"
    elif nK == 0:
        d = "conduction_only"
    elif nC == 0:
        d = "keyhole_only__K_at_end"
    elif r["final_active_regime"] == "C":
        d = "K_then_C__no_later_K" if r["n_K_blocks"] == 1 else "alternating__terminal_C"
    else:
        d = "C_then_K__K_at_end" if r["n_K_blocks"] == 1 else "alternating__K_at_end"
    r["descriptor"] = d
    r["K_ongoing_at_observation_end"] = int(r["final_active_regime"] == "K")
    r["collapsed_sequence"] = "-".join(c for i, c in enumerate(codes) if i == 0 or c != codes[i - 1])
    r["collapsed_active_sequence"] = "-".join(c for i, (j, c) in enumerate(act) if i == 0 or c != act[i - 1][1])
    r["label_sequence_sha256"] = hashlib.sha256("\n".join(codes).encode()).hexdigest()
    return r, kr, gaps


def alternative_labels(r):
    """Alternative binary labels in NEW columns only (the canonical has_keyhole is never replaced)."""
    out = {}
    for name in ("FCK", "KC"):
        f = r[f"frac_K_{name}"]
        for thr in (0.05, 0.10):
            out[f"alt_K_{name}_ge{int(thr * 100):02d}"] = (np.nan if not np.isfinite(f) else int(f >= thr))
    return out


def sequence_table(frames):
    rows, epis = [], []
    for sid, g in frames.groupby("sim_id", sort=False):
        codes = g.code.tolist()
        r, kr, gaps = describe(codes)
        r.update(alternative_labels(r))
        r["sim_id"] = sid; r["campaign"] = g.campaign.iloc[0]; r["partition"] = g.partition.iloc[0]
        r["n_K_label_1"] = int((g.code_1 == "K").sum()); r["n_K_label_2"] = int((g.code_2 == "K").sum())
        r["label_1_vs_final_disagree_frames"] = int((g.code_1 != g.code).sum())
        r["label_2_vs_final_disagree_frames"] = int((g.code_2 != g.code).sum())
        r["duplicate_timesteps"] = int(g.timestep.duplicated().sum())
        r["timestep_monotone_in_source_order"] = int(g.sort_values("source_row").timestep.is_monotonic_increasing)
        r["bug_free_values"] = "|".join(str(v) for v in sorted(g.bug_free.astype(str).unique()))
        r["correctly_finished_values"] = "|".join(str(v) for v in sorted(g.correctly_finished.astype(str).unique()))
        rows.append(r)
        for i, (a, b) in enumerate(kr):
            epis.append({"sim_id": sid, "campaign": r["campaign"], "run_number": i + 1, "start_pos": a, "end_pos": b,
                         "frames": b - a + 1, "start_timestep": int(g.timestep.iloc[a]), "end_timestep": int(g.timestep.iloc[b]),
                         "label_before": codes[a - 1] if a > 0 else "start", "label_after": codes[b + 1] if b + 1 < len(codes) else "end",
                         "gap_to_next_run": "+".join(sorted(set(gaps[i]))) if i < len(gaps) else "",
                         "gap_to_next_type": gap_type(gaps[i]) if i < len(gaps) else "",
                         "right_censored_by_last_frame": int(b == len(codes) - 1)})
    return pd.DataFrame(rows), pd.DataFrame(epis)
