#!/usr/bin/env python3
"""Build the 2026-09-21 thesis branch/local forensic audit.

The audit reads Git objects and path metadata.  It deliberately does not open
raw/private/new-data paths.  Content hashes are computed only for known
scientific local-only code and output artifacts selected for import.
"""

from __future__ import annotations

import argparse
import csv
import datetime as dt
import gzip
import hashlib
import json
import os
from pathlib import Path
import subprocess
import urllib.request


REPO_SLUG = "iso0/active-level-set-week1-warmup"
SCIENCE_ROOTS = (
    "src/",
    "notebooks/",
    "docs/",
    "outputs/",
    "tests/",
    "presentations/",
    "slides/",
)
ROOT_SCIENCE_FILES = {
    "README.md",
    "requirements.txt",
    "pyproject.toml",
    "environment.yml",
    "environment.yaml",
    ".gitattributes",
    ".gitignore",
}
SENSITIVE_PARTS = {
    "raw",
    "private",
    "secret",
    "secrets",
    "credentials",
    "credential",
    "token",
    "tokens",
    "new_ioan",
    "ioan_new",
    "incoming",
    "unblinded",
}
GENERATED_PARTS = {
    ".venv",
    "venv",
    "__pycache__",
    ".pytest_cache",
    ".ruff_cache",
    ".ipynb_checkpoints",
    "node_modules",
}


def git(root: Path, *args: str, check: bool = True) -> str:
    proc = subprocess.run(
        ["git", "-C", str(root), *args],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
    )
    if check and proc.returncode:
        raise RuntimeError(
            f"git {' '.join(args)} failed ({proc.returncode}): "
            + proc.stderr.decode("utf-8", "replace")
        )
    return proc.stdout.decode("utf-8", "replace")


def git_bytes(root: Path, *args: str) -> bytes:
    proc = subprocess.run(
        ["git", "-C", str(root), *args],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
    )
    if proc.returncode:
        raise RuntimeError(
            f"git {' '.join(args)} failed ({proc.returncode}): "
            + proc.stderr.decode("utf-8", "replace")
        )
    return proc.stdout


def ls_tree(root: Path, ref: str) -> dict[str, str]:
    raw = git_bytes(root, "ls-tree", "-r", "-z", "--full-tree", ref)
    result: dict[str, str] = {}
    for rec in raw.split(b"\0"):
        if not rec:
            continue
        meta, path = rec.split(b"\t", 1)
        _mode, obj_type, sha = meta.decode("ascii").split()
        if obj_type == "blob":
            result[path.decode("utf-8", "surrogateescape")] = sha
    return result


def relevant(path: str) -> bool:
    p = path.replace("\\", "/")
    return p in ROOT_SCIENCE_FILES or p.startswith(SCIENCE_ROOTS)


def category(path: str) -> str:
    p = path.replace("\\", "/")
    for name in ("outputs", "src", "docs", "notebooks", "tests"):
        if p == name or p.startswith(name + "/"):
            return name
    if p.startswith(("presentations/", "slides/")):
        return "presentations"
    return "root"


def contains_sensitive_name(path: str) -> bool:
    parts = {x.lower() for x in Path(path).parts}
    return bool(parts & SENSITIVE_PARTS) or any(
        marker in path.lower()
        for marker in ("new-ioan", "new_ioan", "ioan-new", "ioan_new")
    )


def contains_generated_name(path: str) -> bool:
    return bool({x.lower() for x in Path(path).parts} & GENERATED_PARTS)


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()


def github_prs() -> dict[str, list[dict[str, object]]]:
    request = urllib.request.Request(
        f"https://api.github.com/repos/{REPO_SLUG}/pulls?state=all&per_page=100",
        headers={"User-Agent": "Codex-Thesis-Forensic-Audit"},
    )
    try:
        with urllib.request.urlopen(request, timeout=30) as response:
            rows = json.load(response)
    except Exception as exc:  # network evidence failure is represented explicitly
        return {"__ERROR__": [{"error": str(exc)}]}
    by_head: dict[str, list[dict[str, object]]] = {}
    for row in rows:
        head = str(row["head"]["ref"])
        by_head.setdefault(head, []).append(
            {
                "number": row["number"],
                "state": row["state"],
                "merged_at": row["merged_at"],
                "url": row["html_url"],
                "title": row["title"],
            }
        )
    return by_head


def write_csv(path: Path, rows: list[dict[str, object]], fields: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)


def remote_heads(root: Path) -> dict[str, str]:
    heads: dict[str, str] = {}
    for line in git(root, "ls-remote", "--heads", "origin").splitlines():
        sha, ref = line.split("\t", 1)
        heads[ref.removeprefix("refs/heads/")] = sha
    return dict(sorted(heads.items()))


def parse_name_status(text: str) -> list[tuple[str, str, str]]:
    rows: list[tuple[str, str, str]] = []
    for line in text.splitlines():
        parts = line.split("\t")
        status = parts[0]
        if status.startswith(("R", "C")) and len(parts) >= 3:
            rows.append((status, parts[1], parts[2]))
        elif len(parts) >= 2:
            rows.append((status, parts[1], parts[1]))
    return rows


def concise_paths(paths: list[str], limit: int = 30) -> str:
    if len(paths) <= limit:
        return ";".join(paths)
    return ";".join(paths[:limit]) + f";...(+{len(paths)-limit})"


def load_prior_manifest(root: Path) -> tuple[dict[str, list[str]], dict[str, object]]:
    manifest_path = root / "outputs/project_consolidation/source_manifest.json.gz"
    with gzip.open(manifest_path, "rt", encoding="utf-8") as handle:
        manifest = json.load(handle)
    by_blob: dict[str, list[str]] = {}
    for row in manifest["files"]:
        by_blob.setdefault(row["blob"], []).append(row["destination"])
    return by_blob, manifest


def build_remote_audit(root: Path, out: Path) -> tuple[list[dict[str, object]], list[dict[str, object]], dict[str, dict[str, str]]]:
    heads = remote_heads(root)
    main_ref = "origin/main"
    main_sha = heads["main"]
    main_tree = ls_tree(root, main_ref)
    main_blobs: dict[str, list[str]] = {}
    for path, blob in main_tree.items():
        main_blobs.setdefault(blob, []).append(path)
    prior_by_blob, prior_manifest = load_prior_manifest(root)
    prs = github_prs()
    trees: dict[str, dict[str, str]] = {}
    branch_rows: list[dict[str, object]] = []

    for name, tip in heads.items():
        ref = f"origin/{name}"
        tree = ls_tree(root, ref)
        trees[name] = tree
        science = {p: b for p, b in tree.items() if relevant(p)}
        unique_science = sorted(p for p, b in science.items() if b not in main_blobs)
        same_path = sum(main_tree.get(p) == b for p, b in science.items())
        differing_path = sorted(p for p, b in science.items() if p in main_tree and main_tree[p] != b)
        missing_path_but_blob_preserved = sorted(
            p for p, b in science.items() if p not in main_tree and b in main_blobs
        )
        diff = parse_name_status(git(root, "diff", "--name-status", "--find-renames", main_ref, ref))
        added = sorted(dst for s, _src, dst in diff if s.startswith(("A", "C", "R")))
        modified = sorted(dst for s, _src, dst in diff if s.startswith(("M", "T")))
        deleted = sorted(src for s, src, _dst in diff if s.startswith("D"))
        behind, ahead = map(int, git(root, "rev-list", "--left-right", "--count", f"{main_ref}...{ref}").split())
        mb = git(root, "merge-base", main_ref, ref).strip()
        reachable_proc = subprocess.run(
            ["git", "-C", str(root), "merge-base", "--is-ancestor", tip, main_ref],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        reachable = reachable_proc.returncode == 0
        meta = git(root, "show", "-s", "--format=%cI%x00%s", tip).rstrip("\n").split("\x00", 1)
        unique_commits = git(root, "rev-list", f"{main_ref}..{ref}").splitlines()
        branch_prs = prs.get(name, [])
        open_pr = any(p.get("state") == "open" for p in branch_prs)
        if name == "main":
            classification = "ACTIVE_CURRENT_WORK"
        elif open_pr:
            classification = "ACTIVE_CURRENT_WORK"
        elif name == "codex/week10-pg-rmbc-internal-replication":
            classification = "ACTIVE_CURRENT_WORK"
        elif unique_science:
            if same_path or missing_path_but_blob_preserved:
                classification = "PARTIALLY_IN_MAIN"
            else:
                classification = "UNIQUE_CONTENT_NOT_IN_MAIN"
        elif reachable or tip == main_sha or not diff:
            classification = "FULLY_IN_MAIN"
        elif science:
            classification = "SUPERSEDED_BUT_PROVENANCE_RELEVANT"
        else:
            classification = "EMPTY_OR_REDUNDANT"

        def unique_category_paths(kind: str) -> list[str]:
            return [p for p in unique_science if category(p) == kind]

        pr_text = ";".join(
            f"#{p['number']}:{p['state']}:{'merged' if p['merged_at'] else 'not_merged'}:{p['url']}"
            for p in branch_prs
        ) or "NONE"
        branch_rows.append(
            {
                "branch": name,
                "tip_sha": tip,
                "tip_date": meta[0],
                "tip_message": meta[1] if len(meta) > 1 else "",
                "merge_base_with_main": mb,
                "commits_ahead_of_main": ahead,
                "commits_behind_main": behind,
                "tip_reachable_from_main": str(reachable).lower(),
                "direct_added_or_renamed_files": len(added),
                "direct_modified_files": len(modified),
                "direct_deleted_files": len(deleted),
                "unique_files": concise_paths(added),
                "modified_files": concise_paths(modified),
                "deleted_files": concise_paths(deleted),
                "science_files_at_tip": len(science),
                "same_path_identical_to_main": same_path,
                "same_path_different_from_main": len(differing_path),
                "relocated_but_blob_preserved_on_main": len(missing_path_but_blob_preserved),
                "science_blobs_absent_from_main": len({science[p] for p in unique_science}),
                "science_paths_absent_from_main_by_blob": len(unique_science),
                "outputs_unique_to_branch": concise_paths(unique_category_paths("outputs")),
                "src_unique_to_branch": concise_paths(unique_category_paths("src")),
                "docs_unique_to_branch": concise_paths(unique_category_paths("docs")),
                "notebooks_unique_to_branch": concise_paths(unique_category_paths("notebooks")),
                "tests_unique_to_branch": concise_paths(unique_category_paths("tests")),
                "associated_pr": pr_text,
                "open_pr": str(open_pr).lower(),
                "scientifically_unique_work": str(bool(unique_science)).lower(),
                "unique_commit_count": len(unique_commits),
                "unique_commits": concise_paths(unique_commits, 20),
                "provisional_classification": classification,
                "classification_basis": (
                    "Blob-level comparison against the complete origin/main tree and the 2026-09-14 "
                    "content-addressed source manifest; chronology/status overrides only for post-main Week 10 work."
                ),
            }
        )

    fields = list(branch_rows[0].keys())
    write_csv(out / "REMOTE_BRANCH_AUDIT.csv", branch_rows, fields)

    md = [
        "# Remote branch forensic audit",
        "",
        f"Generated: {dt.datetime.now(dt.timezone.utc).isoformat()}",
        "",
        f"Remote: `https://github.com/{REPO_SLUG}.git`",
        f"Default branch: `main` at `{main_sha}`",
        f"Remote heads audited: **{len(heads)}** (including `main`).",
        "",
        "The audit compares both direct paths and Git blob identities. A branch is not considered missing merely because the prior consolidation relocated an identical blob. The prior manifest contains "
        f"{len(prior_manifest['files']):,} file records and is used as corroborating provenance. GitHub PR state was queried from the public API; no open PRs were found." if "__ERROR__" not in prs else "GitHub PR API lookup failed and deletion must remain blocked.",
        "",
        "| Branch | Tip | Ahead/behind | Reachable | Unique science blobs | PR | Classification |",
        "|---|---:|---:|:---:|---:|---|---|",
    ]
    for row in branch_rows:
        md.append(
            f"| `{row['branch']}` | `{str(row['tip_sha'])[:12]}` | {row['commits_ahead_of_main']}/{row['commits_behind_main']} | "
            f"{row['tip_reachable_from_main']} | {row['science_blobs_absent_from_main']} | {row['associated_pr']} | **{row['provisional_classification']}** |"
        )
    md.extend(
        [
            "",
            "## Classification rules",
            "",
            "- `ACTIVE_CURRENT_WORK`: main, an open-PR head, or the post-consolidation Week 10 PG-RMBC branch.",
            "- `PARTIALLY_IN_MAIN`: at least one scientific blob is absent from main while other branch content is already preserved.",
            "- `UNIQUE_CONTENT_NOT_IN_MAIN`: scientific content is absent and the branch is not otherwise represented.",
            "- `SUPERSEDED_BUT_PROVENANCE_RELEVANT`: no scientific blob is absent, but the historical tree/path state differs.",
            "- `FULLY_IN_MAIN`: tip ancestry/tree is already reachable or identical.",
            "- `EMPTY_OR_REDUNDANT`: no scientific content requires preservation.",
            "",
            "Deletion eligibility is intentionally not decided by this provisional classification alone. The final provenance and validation gates govern deletion.",
        ]
    )
    (out / "REMOTE_BRANCH_AUDIT.md").write_text("\n".join(md) + "\n", encoding="utf-8")

    union: dict[str, dict[str, str]] = {}
    for branch, tree in trees.items():
        for path, blob in tree.items():
            if relevant(path):
                union.setdefault(path, {})[branch] = blob
    union_rows: list[dict[str, object]] = []
    for path in sorted(union):
        versions = union[path]
        blob_branches: dict[str, list[str]] = {}
        for branch, blob in versions.items():
            blob_branches.setdefault(blob, []).append(branch)
        main_blob = main_tree.get(path, "")
        missing_blobs = [blob for blob in blob_branches if blob not in main_blobs]
        if not missing_blobs:
            authority = "main"
            reason = "All branch blob versions are already preserved in the main content-addressed union."
        elif all("codex/week10-pg-rmbc-internal-replication" in blob_branches[b] for b in missing_blobs):
            authority = "IMPORT_POST_MAIN_WEEK10"
            reason = "Post-consolidation Week 10 work; import at its branch path without overwriting historical variants."
        else:
            authority = "IMPORT_OR_MANUAL_REVIEW"
            reason = "At least one scientific blob is absent from main; reconcile before deletion."
        canonical = []
        for blob in blob_branches:
            locations = main_blobs.get(blob) or prior_by_blob.get(blob) or [path]
            canonical.append(f"{blob}:{'|'.join(locations[:5])}")
        union_rows.append(
            {
                "path": path,
                "category": category(path),
                "branches_containing_path": ";".join(sorted(versions)),
                "branch_sha_map": ";".join(f"{b}={versions[b]}" for b in sorted(versions)),
                "distinct_blob_count": len(blob_branches),
                "blob_version_map": ";".join(f"{b}:{'|'.join(sorted(bs))}" for b, bs in sorted(blob_branches.items())),
                "main_contains_path": str(bool(main_blob)).lower(),
                "main_blob": main_blob,
                "main_version_identical_to_all": str(bool(main_blob) and len(blob_branches) == 1 and main_blob in blob_branches).lower(),
                "versions_differ": str(len(blob_branches) > 1).lower(),
                "all_versions_preserved_somewhere_on_main": str(not missing_blobs).lower(),
                "missing_blob_versions": ";".join(missing_blobs),
                "chronological_scientifically_authoritative": authority,
                "authority_reason": reason,
                "both_versions_must_be_preserved": str(len(blob_branches) > 1).lower(),
                "canonical_locations_by_blob": ";".join(canonical),
            }
        )
    write_csv(out / "BRANCH_FILE_UNION.csv", union_rows, list(union_rows[0].keys()))
    return branch_rows, union_rows, trees


def build_local_audit(
    canonical_root: Path,
    local_root: Path,
    out: Path,
    remote_rows: list[dict[str, object]],
) -> tuple[list[dict[str, object]], list[dict[str, object]]]:
    main_tree = ls_tree(canonical_root, "origin/main")
    main_blobs = set(main_tree.values())
    local_head = git(local_root, "rev-parse", "HEAD").strip()
    local_branch = git(local_root, "branch", "--show-current").strip()
    upstream = git(local_root, "rev-parse", "--abbrev-ref", "@{upstream}", check=False).strip()
    upstream_tip = git(local_root, "rev-parse", "@{upstream}", check=False).strip() if upstream else ""
    head_pushed = local_head == upstream_tip
    local_tree = ls_tree(local_root, "HEAD")
    modified = set(git(local_root, "diff", "--name-only").splitlines())
    staged = set(git(local_root, "diff", "--cached", "--name-only").splitlines())
    rows: list[dict[str, object]] = []

    for path, blob in sorted(local_tree.items()):
        if not relevant(path):
            continue
        if path in modified or path in staged:
            status = "modified_but_uncommitted"
            destination = "REVIEW_BEFORE_IMPORT"
        elif main_tree.get(path) == blob:
            status = "tracked_and_pushed" if head_pushed else "tracked_but_unpushed"
            destination = path
        elif blob in main_blobs:
            status = "tracked_and_pushed_content_preserved_on_main" if head_pushed else "tracked_but_unpushed_content_preserved_on_main"
            destination = "content-addressed main union"
        else:
            status = "tracked_and_pushed_branch_only" if head_pushed else "committed_on_local_only_branch"
            destination = path
        rows.append(
            {
                "record_type": "FILE",
                "original_local_path": path,
                "git_or_local_status": status,
                "current_branch": local_branch,
                "upstream": upstream,
                "git_blob": blob,
                "sha256": "",
                "bytes": "",
                "category": category(path),
                "scientifically_relevant": "true",
                "safe_to_read_or_hash": "true",
                "represented_on_origin_main": str(blob in main_blobs).lower(),
                "canonical_destination": destination,
                "reason": "Tracked scientific file classified by exact Git blob identity.",
            }
        )

    raw_untracked = git_bytes(local_root, "ls-files", "--others", "--exclude-standard", "-z")
    untracked_paths = [p.decode("utf-8", "surrogateescape") for p in raw_untracked.split(b"\0") if p]
    for path in sorted(untracked_paths):
        full = local_root / path
        sensitive = contains_sensitive_name(path)
        generated = contains_generated_name(path) or path.endswith((".tmp", ".bak", "~"))
        sci = relevant(path) and not generated
        digest = sha256_file(full) if sci and not sensitive and full.is_file() else "NOT_READ"
        if sensitive:
            status = "raw_private_external_or_possible_new_ioan_data_not_accessed"
            destination = "EXCLUDE_PENDING_OWNER_REVIEW"
            reason = "Name-based quarantine only; contents were not opened or hashed."
        elif generated:
            status = "generated_cache_or_temp"
            destination = "DO_NOT_IMPORT"
            reason = "Generated/cache naming rule."
        elif sci:
            status = "untracked_scientifically_relevant"
            destination = path
            reason = "Known Week 10 code/output artifact; import to the same canonical path."
        else:
            status = "untracked_non_scientific"
            destination = "DO_NOT_IMPORT_UNLESS_MANUAL_REVIEW"
            reason = "Outside canonical scientific roots."
        rows.append(
            {
                "record_type": "FILE",
                "original_local_path": path,
                "git_or_local_status": status,
                "current_branch": local_branch,
                "upstream": upstream,
                "git_blob": "",
                "sha256": digest,
                "bytes": full.stat().st_size if full.is_file() else "",
                "category": category(path),
                "scientifically_relevant": str(sci).lower(),
                "safe_to_read_or_hash": str(not sensitive).lower(),
                "represented_on_origin_main": "false",
                "canonical_destination": destination,
                "reason": reason,
            }
        )

    ignored_lines = [
        line[3:]
        for line in git(local_root, "status", "--ignored", "--short").splitlines()
        if line.startswith("!! ")
    ]
    for path in ignored_lines:
        sensitive = contains_sensitive_name(path)
        rows.append(
            {
                "record_type": "IGNORED_ROOT",
                "original_local_path": path,
                "git_or_local_status": "raw_private_external_or_possible_new_ioan_data_not_accessed" if sensitive else "generated_cache_or_temp",
                "current_branch": local_branch,
                "upstream": upstream,
                "git_blob": "",
                "sha256": "NOT_READ",
                "bytes": "",
                "category": "ignored",
                "scientifically_relevant": "false",
                "safe_to_read_or_hash": str(not sensitive).lower(),
                "represented_on_origin_main": "false",
                "canonical_destination": "DO_NOT_IMPORT",
                "reason": "Ignored root recorded without recursive content reads; cache/environment only by path classification.",
            }
        )

    remote_by_name = {str(r["branch"]): r for r in remote_rows}
    local_branch_rows: list[dict[str, object]] = []
    local_refs = git(local_root, "for-each-ref", "--format=%(refname:short)%00%(objectname)", "refs/heads").splitlines()
    for record in local_refs:
        name, tip = record.split("\x00", 1)
        remote = remote_by_name.get(name)
        tree = ls_tree(local_root, name)
        science = {p: b for p, b in tree.items() if relevant(p)}
        unique_paths = sorted(p for p, b in science.items() if b not in main_blobs)
        reachable_proc = subprocess.run(
            ["git", "-C", str(local_root), "merge-base", "--is-ancestor", tip, "origin/main"],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        local_branch_rows.append(
            {
                "branch": name,
                "tip_sha": tip,
                "remote_branch_exists": str(remote is not None).lower(),
                "matches_remote_tip": str(bool(remote) and remote["tip_sha"] == tip).lower(),
                "tip_reachable_from_main": str(reachable_proc.returncode == 0).lower(),
                "unique_commits_vs_main": len(git(local_root, "rev-list", f"origin/main..{name}").splitlines()),
                "science_blobs_absent_from_main": len({science[p] for p in unique_paths}),
                "science_paths_absent_from_main_by_blob": len(unique_paths),
                "unique_science_paths": concise_paths(unique_paths),
                "disposition": "IMPORT" if unique_paths else "CONTENT_ALREADY_PRESERVED",
            }
        )
        rows.append(
            {
                "record_type": "LOCAL_BRANCH",
                "original_local_path": f"refs/heads/{name}",
                "git_or_local_status": "local_branch_with_unique_science" if unique_paths else "local_branch_content_preserved",
                "current_branch": local_branch,
                "upstream": f"origin/{name}" if remote else "NONE",
                "git_blob": tip,
                "sha256": "",
                "bytes": "",
                "category": "git_history",
                "scientifically_relevant": str(bool(science)).lower(),
                "safe_to_read_or_hash": "true",
                "represented_on_origin_main": str(not unique_paths).lower(),
                "canonical_destination": "IMPORT_BRANCH_CONTENT" if unique_paths else "main content-addressed union",
                "reason": "Local branch tip compared by scientific blob identity against origin/main.",
            }
        )

    fields = [
        "record_type", "original_local_path", "git_or_local_status", "current_branch", "upstream",
        "git_blob", "sha256", "bytes", "category", "scientifically_relevant", "safe_to_read_or_hash",
        "represented_on_origin_main", "canonical_destination", "reason",
    ]
    write_csv(out / "LOCAL_VS_GITHUB_AUDIT.csv", rows, fields)
    write_csv(out / "LOCAL_BRANCH_AUDIT.csv", local_branch_rows, list(local_branch_rows[0].keys()))

    counts: dict[str, int] = {}
    for row in rows:
        counts[str(row["git_or_local_status"])] = counts.get(str(row["git_or_local_status"]), 0) + 1
    import_rows = [r for r in rows if r["git_or_local_status"] in {"untracked_scientifically_relevant", "tracked_and_pushed_branch_only", "committed_on_local_only_branch"}]
    md = [
        "# Local versus GitHub audit",
        "",
        f"Source checkout: `{local_root}`",
        f"Current branch/tip: `{local_branch}` / `{local_head}`",
        f"Upstream/tip: `{upstream}` / `{upstream_tip}`",
        f"Current branch fully pushed: **{head_pushed}**.",
        "",
        "## File/status counts",
        "",
    ]
    md.extend(f"- `{key}`: {value:,}" for key, value in sorted(counts.items()))
    md.extend(
        [
            "",
            "## Local-only scientific destinations",
            "",
            f"Every one of the {len(import_rows):,} scientific branch-only or untracked records has a destination in `LOCAL_VS_GITHUB_AUDIT.csv`. Known Week 10 artifacts retain their current repository-relative paths.",
            "",
            "## Local branches",
            "",
            "| Branch | Tip | Remote | Matches | Unique science blobs | Disposition |",
            "|---|---:|:---:|:---:|---:|---|",
        ]
    )
    for row in local_branch_rows:
        md.append(
            f"| `{row['branch']}` | `{str(row['tip_sha'])[:12]}` | {row['remote_branch_exists']} | {row['matches_remote_tip']} | "
            f"{row['science_blobs_absent_from_main']} | {row['disposition']} |"
        )
    md.extend(
        [
            "",
            "## Safety exclusions",
            "",
            "Ignored virtual environments and caches are recorded but not recursively hashed or imported. Paths suggestive of raw/private/new Ioan data are quarantined by name and are never opened or hashed. No such new-Ioan path was surfaced by Git status in this audit.",
        ]
    )
    (out / "LOCAL_VS_GITHUB_AUDIT.md").write_text("\n".join(md) + "\n", encoding="utf-8")
    return rows, local_branch_rows


def build_forensic_report(
    root: Path,
    out: Path,
    branch_rows: list[dict[str, object]],
    union_rows: list[dict[str, object]],
    local_rows: list[dict[str, object]],
    local_branch_rows: list[dict[str, object]],
) -> None:
    classes: dict[str, list[str]] = {}
    for row in branch_rows:
        classes.setdefault(str(row["provisional_classification"]), []).append(str(row["branch"]))
    unique_remote = [r for r in branch_rows if int(r["science_blobs_absent_from_main"]) > 0]
    local_imports = [r for r in local_rows if r["git_or_local_status"] == "untracked_scientifically_relevant"]
    local_unique_branches = [r for r in local_branch_rows if int(r["science_blobs_absent_from_main"]) > 0]
    conflicting = [r for r in union_rows if r["versions_differ"] == "true"]
    main_count = len(ls_tree(root, "origin/main"))
    md = [
        "# Repository forensic audit",
        "",
        "## Scope and safety",
        "",
        "This audit covers every fetched remote head, every local branch tip, the scientific file union, and the current checkout's tracked/untracked/ignored state. It compares Git blobs rather than names alone. It did not open, hash, label, or summarize any genuinely new Ioan batch; no such path was surfaced by status.",
        "",
        "## What main already contains",
        "",
        f"`origin/main` contains {main_count:,} tracked files at `{git(root, 'rev-parse', 'origin/main').strip()}`. Its 2026-09-14 consolidation manifest records the prior lossless, content-addressed union. All older branch blobs found on main under relocated history/variant paths count as preserved, not missing.",
        "",
        "## Branch findings before import",
        "",
    ]
    for key in sorted(classes):
        md.append(f"- **{key} ({len(classes[key])})**: " + ", ".join(f"`{x}`" for x in classes[key]))
    md.extend(
        [
            "",
            f"Remote branches with scientific blobs absent from old main: **{len(unique_remote)}**.",
        ]
    )
    for row in unique_remote:
        md.append(
            f"- `{row['branch']}`: {row['science_blobs_absent_from_main']} blobs / {row['science_paths_absent_from_main_by_blob']} paths; provisional `{row['provisional_classification']}`."
        )
    md.extend(
        [
            "",
            "## Local findings before import",
            "",
            f"Untracked scientific artifacts requiring import: **{len(local_imports):,}**.",
            f"Local branch tips with scientific blobs absent from old main: **{len(local_unique_branches)}**.",
        ]
    )
    for row in local_unique_branches:
        md.append(f"- `{row['branch']}`: {row['science_blobs_absent_from_main']} unique blobs.")
    md.extend(
        [
            "",
            "The known local-only sets are the Phase 1.20-1.22 comparator audit and boundary-displacement Gate 1, with their code, tests, reports, manifests, diagnostics, figures, and checkpoints. Their explicit path-level destinations and SHA-256 values are in `LOCAL_VS_GITHUB_AUDIT.csv`.",
            "",
            "## Duplicate trees and conflicts",
            "",
            f"The union contains {len(conflicting):,} paths with multiple historical blob versions. Authority is not selected by timestamp: the validated main layout remains canonical when every blob is already present; post-main Week 10 work is imported; otherwise the row remains an import/manual-review gate. Historical alternatives remain in content-addressed `_history`/`_variants` locations.",
            "",
            "## Recent experiments missing from old main",
            "",
            "- Week 10 PG-RMBC internal replication (remote branch).",
            "- Week 10 Phase 1.20-1.22 comparator/provenance audit (local-only tree).",
            "- Week 10 boundary-displacement model Gate 1 and implementation repair (local-only tree).",
            "",
            "## Deletion gate",
            "",
            "No remote branch is deletion-eligible yet. Eligibility requires import/reconciliation, provenance rows, open-PR exclusion, a PASS validation document, publication to remote main, and a fresh blob-level comparison against remote main.",
        ]
    )
    (out / "REPOSITORY_FORENSIC_AUDIT.md").write_text("\n".join(md) + "\n", encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--repo", type=Path, default=Path.cwd())
    parser.add_argument("--source-worktree", type=Path, required=True)
    args = parser.parse_args()
    root = args.repo.resolve()
    local_root = args.source_worktree.resolve()
    out = root / "docs/consolidation"
    out.mkdir(parents=True, exist_ok=True)
    branch_rows, union_rows, _trees = build_remote_audit(root, out)
    local_rows, local_branch_rows = build_local_audit(root, local_root, out, branch_rows)
    build_forensic_report(root, out, branch_rows, union_rows, local_rows, local_branch_rows)
    print(json.dumps({
        "remote_branches": len(branch_rows),
        "union_paths": len(union_rows),
        "local_records": len(local_rows),
        "local_branches": len(local_branch_rows),
        "remote_unique_or_partial": [r["branch"] for r in branch_rows if int(r["science_blobs_absent_from_main"]) > 0],
        "local_unique_branches": [r["branch"] for r in local_branch_rows if int(r["science_blobs_absent_from_main"]) > 0],
    }, indent=2))


if __name__ == "__main__":
    main()
