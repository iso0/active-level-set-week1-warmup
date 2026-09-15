"""Week 9 Phase 1.21 — repository-wide audit of which outer-split repeat blocks were ever used.

Every outer run produced by the frozen generator ``w85.build_splits`` is named
``w85__r{repeat:02d}_f{fold:02d}`` and seeded with the key ``outer_split|repeat|{repeat:02d}``.
A repeat block counts as USED if either token appears anywhere on disk: in a file name, in a text
file, inside gzip / zip / tar archives, in parquet string columns, or in raw bytes of other files
(pickles, sqlite).  Git history is audited separately with ``git grep`` over every ref and stash.

The audit only pattern-matches; it never loads labels or fits anything.  Run one root per process:

    py -3.14 -c "import sys; sys.argv=['a','<root>','<tag>']; from src.week9_phase1_21_repeat_audit import main; main()"
"""
from __future__ import annotations

import gzip
import io
import json
import re
import sys
import tarfile
import time
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "outputs" / "week9_phase1_21_simplification_replication" / "repeat_audit"

RUN_ID = re.compile(rb"w85__r(\d{2,3})_f(\d{2})")
SEED_KEY = re.compile(rb"outer_split\|repeat\|(\d{2,3})")
CHUNK = 64 * 1024 * 1024
OVERLAP = 64
SKIP_SUFFIX = {".png", ".jpg", ".jpeg", ".gif", ".svg", ".pdf", ".pyc", ".woff", ".woff2", ".ttf", ".ico", ".mp4"}
ZIP_SUFFIX = {".zip", ".npz", ".pptx", ".xlsx", ".docx"}


def scan_stream(handle, found: set[int]) -> None:
    tail = b""
    while True:
        block = handle.read(CHUNK)
        if not block:
            break
        data = tail + block
        for match in RUN_ID.finditer(data):
            found.add(int(match.group(1)))
        for match in SEED_KEY.finditer(data):
            found.add(int(match.group(1)))
        tail = data[-OVERLAP:]


def scan_member(name: str, raw, found: set[int]) -> None:
    lowered = name.lower()
    if lowered.endswith(".gz") and not lowered.endswith((".tar.gz", ".tgz")):
        with gzip.GzipFile(fileobj=raw) as inner:
            scan_stream(inner, found)
    else:
        scan_stream(raw, found)


def scan_file(path: Path) -> tuple[set[int], str | None]:
    found: set[int] = set()
    for match in RUN_ID.finditer(path.name.encode("utf-8", "ignore")):
        found.add(int(match.group(1)))
    suffix = path.suffix.lower()
    name = path.name.lower()
    try:
        if suffix in SKIP_SUFFIX:
            return found, None
        if name.endswith((".tar.gz", ".tgz")):
            with tarfile.open(path, "r:gz") as bundle:
                for member in bundle:
                    if member.isfile():
                        for m in RUN_ID.finditer(member.name.encode()):
                            found.add(int(m.group(1)))
                        handle = bundle.extractfile(member)
                        if handle is not None:
                            scan_member(member.name, handle, found)
        elif suffix == ".gz":
            with gzip.open(path, "rb") as handle:
                scan_stream(handle, found)
        elif suffix in ZIP_SUFFIX:
            with zipfile.ZipFile(path) as archive:
                for info in archive.infolist():
                    for m in RUN_ID.finditer(info.filename.encode()):
                        found.add(int(m.group(1)))
                    if info.is_dir() or info.filename.lower().endswith(tuple(SKIP_SUFFIX)):
                        continue
                    with archive.open(info) as handle:
                        if info.filename.lower().endswith(".zip"):
                            nested = zipfile.ZipFile(io.BytesIO(handle.read()))
                            for sub in nested.infolist():
                                if not sub.is_dir():
                                    with nested.open(sub) as h2:
                                        scan_member(sub.filename, h2, found)
                        else:
                            scan_member(info.filename, handle, found)
        elif suffix == ".parquet":
            import pyarrow.parquet as pq
            table = pq.read_table(path)
            for column in table.columns:
                if "string" in str(column.type) or "dictionary" in str(column.type):
                    text = "\n".join(map(str, column.to_pylist())).encode()
                    scan_stream(io.BytesIO(text), found)
        else:
            with open(path, "rb") as handle:
                scan_stream(handle, found)
        return found, None
    except Exception as exc:                          # recorded, never silently dropped
        return found, f"{type(exc).__name__}: {exc}"[:300]


def main() -> None:
    root, tag = Path(sys.argv[1]), sys.argv[2]
    OUT.mkdir(parents=True, exist_ok=True)
    started = time.time()
    hits, errors, scanned = [], [], 0
    for path in root.rglob("*"):
        if not path.is_file() or ".git" in path.parts or "week9_phase1_21_simplification_replication" in path.parts:
            continue                               # never scan this audit's own outputs
        scanned += 1
        found, error = scan_file(path)
        if error:
            errors.append({"path": str(path), "error": error})
        if found:
            hits.append({"path": str(path), "repeats": sorted(found)})
    used = sorted({r for h in hits for r in h["repeats"]})
    payload = {"root": str(root), "tag": tag, "files_scanned": scanned, "files_with_run_ids": len(hits),
               "repeats_found": used, "max_repeat": max(used) if used else None,
               "files_with_repeat_above_20": [h for h in hits if max(h["repeats"]) > 20],
               "files_with_repeat_above_60": [h for h in hits if max(h["repeats"]) > 60],
               "errors": errors, "seconds": round(time.time() - started, 1)}
    (OUT / f"scan_{tag}.json").write_text(json.dumps(payload, indent=2), encoding="utf-8")
    print(tag, "scanned", scanned, "files; repeats", used[:5], "...", used[-5:] if used else [],
          "; >60 files:", len(payload["files_with_repeat_above_60"]), "; errors:", len(errors), flush=True)


if __name__ == "__main__":
    main()
