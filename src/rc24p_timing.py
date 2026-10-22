"""RC24 post-audit: limited timing diagnostic of the NEW short-Keyhole events (owner instruction 2026-10-22, section 5).

Read-only inputs (Hugging Face ioandanielc/sph_v2 @ 2e1eec9c, git-ignored data/raw of the main checkout):
  <run>/frames.csv            frame_idx, timestep (= solver iteration of the saved frame), label (per-frame regime label)
  <run>/monitor/time.dat, iter.dat   physical time of every solver iteration (same length) -> the REAL time axis of every frame
  labels_new_data_4_prep.csv  label_1 / label_2 / label_final per saved frame (two labelling passes + final)
For each of the 10 NEW short-Keyhole originals and the 12 NEW conduction runs: run-length segments of the frame labels, the FIRST
contiguous 'Forming Phase' segment (start / end), any later re-entry into 'Forming Phase', the first / last 'Keyhole' frame, all in
physical time (ms) and in frame index, and the label agreement of the two labelling passes on the keyhole frames.
RC24's hard_region/HARD_MECHANISM.json used forming_end = the LAST forming frame of the whole record and a 0..1 relative axis; this
diagnostic replaces that construction (dated correction in post_audit/TIMING_CORRECTION.md).
    python -m src.rc24p_timing
"""
from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pandas as pd

import src.rc18_common as RC
import src.rc19_pool as P

RAW = Path(r"C:\Users\ozgur\Documents\thesis\data\raw\sph_v2\2e1eec9c98fd57609d2815f174586336ab59da07")
OUT = RC.ROOT / "outputs" / "research_campaign_20261021" / "opus_rc24" / "post_audit"


def segments(labels):
    seg = []; start = 0
    for i in range(1, len(labels) + 1):
        if i == len(labels) or labels[i] != labels[start]:
            seg.append((labels[start], start, i - 1)); start = i
    return seg


def run(sid, lab_all):
    d = RAW / sid; fr = pd.read_csv(d / "frames.csv"); tt = np.loadtxt(d / "monitor" / "time.dat"); it = np.loadtxt(d / "monitor" / "iter.dat")
    t_ms = np.interp(fr.timestep.to_numpy(float), it, tt) * 1e3; L = fr.label.astype(str).to_numpy(); seg = segments(list(L))
    form = [s for s in seg if s[0] == "Forming Phase"]; kseg = [s for s in seg if s[0] == "Keyhole"]; k = np.flatnonzero(L == "Keyhole")
    first_form = form[0] if form else None
    la = lab_all[lab_all.name == sid].sort_values("timestep")
    agree = None
    if len(la) == len(fr) and len(k):
        agree = {"label_1_keyhole_share_on_K_frames": float((la.label_1.to_numpy()[k] == "Keyhole").mean()), "label_2_keyhole_share_on_K_frames": float((la.label_2.to_numpy()[k] == "Keyhole").mean()),
                 "frames_label_equals_label_final": float((la.label_final.to_numpy() == L).mean())}
    return {"sim_id": sid, "frames": len(fr), "frame_dt_ms_median": float(np.median(np.diff(t_ms))), "segments": " > ".join(f"{s[0][:4]}x{s[2] - s[1] + 1}" for s in seg),
            "first_forming_start_ms": float(t_ms[first_form[1]]) if first_form else np.nan, "first_forming_end_ms": float(t_ms[first_form[2]]) if first_form else np.nan,
            "forming_segments": len(form), "last_forming_frame_ms": float(t_ms[form[-1][2]]) if form else np.nan,
            "first_K_ms": float(t_ms[k[0]]) if len(k) else np.nan, "last_K_ms": float(t_ms[k[-1]]) if len(k) else np.nan, "keyhole_frames": int(len(k)), "keyhole_segments": len(kseg),
            "K_starts_after_first_forming_end": bool(len(k) and first_form and k[0] > first_form[2]),
            "K_ends_before_last_forming_frame": bool(len(k) and form and k[-1] < form[-1][2]),
            "frames_between_first_forming_end_and_first_K": int(k[0] - first_form[2]) if (len(k) and first_form) else None,
            "record_end_ms": float(t_ms[-1]), "label_agreement": agree}


def main():
    OUT.mkdir(parents=True, exist_ok=True); M = P.manifest().reset_index(); lab = pd.read_csv(RAW / "labels_new_data_4_prep.csv")
    N = M[M.source_batch == "NEW"]; grp = N[N.shortK_NEW_original.astype(bool) | (N.y == 0)]
    rows = []
    for _, r in grp.iterrows():
        x = run(r.sim_id, lab); x["group"] = "shortK_NEW" if r.y == 1 else "cond_NEW"; x["A_um"] = float(r.A_um) if np.isfinite(r.A_um) else None; rows.append(x)
    D = pd.DataFrame(rows); D.drop(columns=["label_agreement"]).to_csv(OUT / "timing_frames_summary.csv", index=False)
    sk = D[D.group == "shortK_NEW"]
    res = {"n_shortK": int(len(sk)), "n_cond": int((D.group == "cond_NEW").sum()),
           "shortK_with_more_than_one_forming_segment": int((sk.forming_segments > 1).sum()),
           "shortK_first_K_after_first_forming_segment": int(sk.K_starts_after_first_forming_end.sum()),
           "shortK_K_ends_before_last_forming_frame": int(sk.K_ends_before_last_forming_frame.sum()),
           "shortK_first_K_ms": sk.first_K_ms.describe().round(4).to_dict(), "shortK_last_K_ms": sk.last_K_ms.describe().round(4).to_dict(),
           "shortK_first_forming_end_ms": sk.first_forming_end_ms.describe().round(4).to_dict(),
           "cond_first_forming_end_ms": D[D.group == "cond_NEW"].first_forming_end_ms.describe().round(4).to_dict(),
           "frame_dt_ms_median": float(D.frame_dt_ms_median.median()), "per_run": D.to_dict(orient="records")}
    (OUT / "TIMING_DIAGNOSTIC.json").write_text(json.dumps(res, indent=1, default=str), encoding="utf-8")
    print(D[["group", "sim_id", "segments", "first_forming_end_ms", "first_K_ms", "last_K_ms", "forming_segments", "K_starts_after_first_forming_end", "K_ends_before_last_forming_frame"]].to_string(index=False, max_colwidth=60))
    print(json.dumps({k: v for k, v in res.items() if k != "per_run"}, indent=1))


if __name__ == "__main__":
    main()
