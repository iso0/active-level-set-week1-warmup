"""FR inventory of already-used split / startup IDs (read only): scans every recorded unit file name under outputs/ for the STD repeat,
the K5 (k-means 5 regions; RC22 'block' / BLOCK / BLOCK_A) startup and the K4 (BLOCK_B) startup IDs, and lists which campaigns used them.
    python -m src.fr_inventory
"""
from __future__ import annotations

import json
import os
import re
from collections import defaultdict

import src.rc18_common as RC

OUT = RC.ROOT / "outputs" / "research_campaign_20261029" / "opus_final_robustness" / "freeze"
PAT = [("STD", re.compile(r"(?:^|__|_)STD__r(\d+)_f\d")), ("STD", re.compile(r"^STD__r(\d+)_f\d")), ("STD", re.compile(r"MATCH_STD__r(\d+)_f\d")),
       ("STD", re.compile(r"(?:RAND8|LOCAL8|START\w*)__r(\d+)_f\d")), ("STD", re.compile(r"^r(\d+)_f\d")),
       ("K5", re.compile(r"(?:^|__)K5__s(\d+)_b\d")), ("K5", re.compile(r"(?:^|__)(?:BLOCK|BLOCK_A|MATCH_BLOCK|MATCH_BLOCK_A)__s(\d+)_b\d")), ("K5", re.compile(r"^s(\d+)_b\d")),
       ("K4", re.compile(r"(?:^|__)K4__s(\d+)_b\d")), ("K4", re.compile(r"(?:^|__)(?:BLOCK_B|MATCH_BLOCK_B)__s(\d+)_b\d"))]


def scan():
    used = {"STD": defaultdict(set), "K5": defaultdict(set), "K4": defaultdict(set)}; n = 0
    root = RC.ROOT / "outputs"
    for dp, dn, fn in os.walk(root):
        rel = os.path.relpath(dp, root).replace("\\", "/")
        if "opus_final_robustness" in rel:
            continue
        camp = "/".join(rel.split("/")[:2])
        for f in fn:
            if not (f.endswith(".json.gz") or f.endswith(".json")):
                continue
            n += 1
            for kind, rx in PAT:
                m = rx.search(f)
                if m:
                    used[kind][int(m.group(1))].add(camp); break
    return used, n


if __name__ == "__main__":
    used, n = scan(); OUT.mkdir(parents=True, exist_ok=True)
    res = {"files_scanned": n}
    for k, d in used.items():
        ids = sorted(d); res[k] = {"n_ids": len(ids), "min": ids[0] if ids else None, "max": ids[-1] if ids else None,
                                   "gaps_below_max": [i for i in range(1, (ids[-1] if ids else 0) + 1) if i not in d],
                                   "max_by_campaign": {c: max(i for i in ids if c in d[i]) for c in sorted({c for i in ids for c in d[i]})}}
    (OUT / "ID_INVENTORY.json").write_text(json.dumps(res, indent=1), encoding="utf-8"); print(json.dumps({k: (v if k == "files_scanned" else {a: v[a] for a in ("n_ids", "min", "max")}) for k, v in res.items()}, indent=1))
