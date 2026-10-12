"""Week 20 Ioan-package addendum: G5 (H-b302fc6cbd) frame 81, front/side/top, at the pinned NEW revision.

Frame 81 is the last frame before G5's depth maximum (the Week 19 package linked frame 82, which follows a sharp depth
drop).  The earlier gallery is kept unchanged; this adds a separate sheet, inventory and key, and appends a pointer.
Step: python -m src.week20_ioan_addendum
"""
from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "outputs" / "week20_active_temporal_development" / "ioan_addendum"
GAL19 = ROOT / "outputs" / "week19_temporal_regime_dev_pilot" / "ioan_gallery"
NEW_REV = "2e1eec9c98fd57609d2815f174586336ab59da07"
HF = "https://huggingface.co/datasets/ioandanielc/sph_v2"
SID = "P-387p361336282_VX-0p960187357846_LS-4p72484046084e-05_ST-390p52586458_M-TI64_XI-0p0002_XF-0p0014_XL-0p0012_TE-0p0021_DT-5p02414509376e-06_H-b302fc6cbd"
FRAMES = (81,)
VIEWS = ("front", "side", "top")
SCALE = 2


def main():
    from PIL import Image, ImageDraw
    from src.week19_pilot_review import _font
    from src.week19_sources import lp, remote_meta, resolve
    OUT.mkdir(parents=True, exist_ok=True)
    paths = [f"{SID}/frames/{v}/frame_{f:05d}.png" for f in FRAMES for v in VIEWS]
    meta = remote_meta(NEW_REV, paths)
    res = pd.DataFrame([resolve(NEW_REV, r["path"], r) for r in meta.to_dict("records")]).merge(meta, on=["revision", "path"])
    fm = pd.read_csv(ROOT / "outputs/week19_temporal_regime_audit/tables/frame_level_map.csv.gz", usecols=["sim_id", "frame_pos", "timestep", "time_ms", "depth_um", "label_final"])
    fm = fm[fm.sim_id == SID].set_index("frame_pos")
    reg = pd.read_csv(ROOT / "outputs/week19_temporal_regime_audit/tables/temporal_registry.csv").set_index("sim_id").loc[SID]
    old = pd.read_csv(GAL19 / "image_inventory.csv")
    rows = []
    for r in res.itertuples():
        f = int(r.path.split("frame_")[1][:5]); v = r.path.split("/frames/")[1].split("/")[0]
        im = Image.open(lp(r.local)); im.load(); a = np.asarray(im.convert("RGB")).reshape(-1, 3)
        rows.append({"gallery_case": "G5", "sim_id": SID, "frame_idx": f, "solver_iteration": int(fm.loc[f, "timestep"]), "time_ms": float(fm.loc[f, "time_ms"]), "view": v,
                     "repo_path": r.path, "url": f"{HF}/resolve/{NEW_REV}/{r.path}", "revision": NEW_REV, "source": r.source, "verified": bool(r.verified),
                     "identity_check": r.check, "sha256": r.lfs_sha256, "bytes": int(r.size), "width_px": im.size[0], "height_px": im.size[1], "mode": im.mode,
                     "n_colours": int(len(np.unique(a, axis=0))), "usability": "usable", "usability_note": "content inside the field of view; legible at native resolution",
                     "obtained": "downloaded 2026-10-12 at the pinned revision; identity-verified before use", "already_in_week19_set": r.path in set(old.repo_path)})
    inv = pd.DataFrame(rows); inv.to_csv(OUT / "image_inventory_addendum.csv", index=False, lineterminator="\n")
    # side-by-side sheet: frame 81 (new) and frame 82 (already in the Week 19 package), same scale, no labels
    f_head, f_cap = _font(30), _font(20)
    rows82 = old[(old.gallery_case == "G5") & (old.frame_idx == 82)]
    tiles = []
    for f, src in ((81, inv), (82, rows82)):
        for v in VIEWS:
            t = src[src.view == v].iloc[0]
            im = Image.open(lp(ROOT / "data/raw/sph_v2" / NEW_REV / t.repo_path)).convert("RGB")
            tiles.append((f, v, im.resize((im.size[0] * SCALE, im.size[1] * SCALE), Image.NEAREST), t))
    pad, cap, head = 24, 58, 70
    colw = {v: max(t[2].size[0] for t in tiles if t[1] == v) for v in VIEWS}
    W = pad + sum(colw[v] + pad for v in VIEWS); H = head + 2 * (256 * SCALE + cap + pad)
    sheet = Image.new("RGB", (W, H), "white"); d = ImageDraw.Draw(sheet)
    d.text((pad, 18), f"G5 frames 81 (added 2026-10-12) and 82: native PNGs ×{SCALE} by pixel replication", font=f_head, fill="black")
    y = head
    for f in (81, 82):
        x = pad
        for v in VIEWS:
            _, _, big, t = [z for z in tiles if z[0] == f and z[1] == v][0]
            d.text((x, y), f"G5 · frame {f} · iteration {int(fm.loc[f, 'timestep']):,} · t = {fm.loc[f, 'time_ms']:.6f} ms · {v}", font=f_cap, fill="black")
            d.text((x, y + 26), f"native {big.size[0] // SCALE}×{big.size[1] // SCALE} px", font=f_cap, fill="#555555")
            sheet.paste(big, (x, y + cap)); d.rectangle([x - 1, y + cap - 1, x + big.size[0], y + cap + big.size[1]], outline="#999999")
            x += colw[v] + pad
        y += 256 * SCALE + cap + pad
    sheet.save(OUT / "contact_sheet_G5_frames81_82.png", optimize=True)
    t81, t82, tmax = float(fm.loc[81, "time_ms"]), float(fm.loc[82, "time_ms"]), float(reg.A_active_max_ms)
    links = " · ".join(f"[{t.view}]({t.url})" for t in inv.itertuples())
    (OUT / "GALLERY_ADDENDUM.md").write_text(f"""# Gallery addendum (2026-10-12): G5 frame 81

The Week 19 gallery (`../../week19_temporal_regime_dev_pilot/ioan_gallery/GALLERY.md`) is unchanged.

**What is added.** Frame 81 of G5 in front, side and top views, fetched at the pinned NEW revision `{NEW_REV}` and verified by LFS SHA-256 (`image_inventory_addendum.csv`). All three images are usable.

**Timing.**

| Frame | Iteration | Monitor time (ms) | Offset from G5's maximum-depth time |
|---:|---:|---:|---:|
| 81 (added) | {int(fm.loc[81, 'timestep']):,} | {t81:.6f} | {(t81 - tmax) * 1e3:+.2f} µs before |
| 82 (already linked) | {int(fm.loc[82, 'timestep']):,} | {t82:.6f} | {(t82 - tmax) * 1e3:+.2f} µs after |

G5's maximum-depth time is {tmax:.6f} ms.

![G5 frames 81 and 82](contact_sheet_G5_frames81_82.png)

**Originals, frame 81:** {links}.

Recorded labels and monitored depths for these frames are in [KEY_ADDENDUM.md](KEY_ADDENDUM.md).
""", encoding="utf-8", newline="\n")
    (OUT / "KEY_ADDENDUM.md").write_text(f"""# Key addendum (open after the first pass): G5 = H-b302fc6cbd (has_keyhole = 0)

| Frame | Time (ms) | Recorded label | Monitored melt-subset depth (µm) |
|---:|---:|---|---:|
| 81 | {t81:.6f} | {fm.loc[81, 'label_final']} | {fm.loc[81, 'depth_um']:.2f} |
| 82 | {t82:.6f} | {fm.loc[82, 'label_final']} | {fm.loc[82, 'depth_um']:.2f} |

**Notes.**
- The depth maximum is {reg.A_active_max_um:.2f} µm at {tmax:.6f} ms, which lies between the two frames.
- Frame 81 is the last frame before the sharp depth drop; frame 82 shows the state after it.
- Depth is a melt-bound reading, not an image-derived cavity measurement.
""", encoding="utf-8", newline="\n")
    for name, text in (("GALLERY.md", "\n\n## Addendum (2026-10-12)\n\nG5 frame 81 (the last frame before G5's depth maximum) was added in front, side and top views. It is in `../../week20_active_temporal_development/ioan_addendum/GALLERY_ADDENDUM.md`, with exact timing. This gallery is otherwise unchanged.\n"),
                       ("KEY.md", "\n\n## Addendum (2026-10-12)\n\nThe labels and depths for G5 frame 81 are in `../../week20_active_temporal_development/ioan_addendum/KEY_ADDENDUM.md`.\n")):
        p = GAL19 / name; b = p.read_bytes(); nl = b"\r\n" if b.count(b"\r\n") > b.count(b"\n") // 2 else b"\n"
        if b"Addendum (2026-10-12)" not in b:
            p.write_bytes(b.rstrip(b"\r\n") + text.replace("\n", nl.decode()).encode("utf-8"))
    print(inv[["frame_idx", "view", "verified", "bytes", "width_px", "height_px", "n_colours"]].to_string())
    return inv


if __name__ == "__main__":
    main()
