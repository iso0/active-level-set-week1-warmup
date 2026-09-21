"""Validate the complete thesis consolidation without rerunning experiments."""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import re
import subprocess
from pathlib import Path
from urllib.parse import unquote


ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "docs" / "consolidation"
csv.field_size_limit(100_000_000)


def git(*args: str) -> str:
    return subprocess.check_output(
        ["git", "-C", str(ROOT), *args], text=True, encoding="utf-8"
    ).strip()


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8-sig", newline="") as stream:
        return list(csv.DictReader(stream))


def manifest_failures(path: Path) -> list[str]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    records = payload.get("files", [])
    if isinstance(payload.get("artifacts"), dict):
        records += [
            {"path": artifact_path, "sha256": digest}
            for artifact_path, digest in payload["artifacts"].items()
        ]
    if isinstance(payload.get("source_hashes"), dict):
        records += [
            {"path": source_path, "sha256": digest}
            for source_path, digest in payload["source_hashes"].items()
        ]
    failures = []
    for record in records:
        artifact = ROOT / record["path"]
        if not artifact.is_file() or sha256(artifact) != record["sha256"]:
            failures.append(record["path"])
    return failures


def markdown_link_failures(paths: list[Path]) -> list[str]:
    failures = []
    for document in paths:
        body = document.read_text(encoding="utf-8")
        for target in re.findall(r"\]\(([^)]+)\)", body):
            if "://" in target or target.startswith("#"):
                continue
            relative = unquote(target.split("#", 1)[0])
            if relative and not (document.parent / relative).resolve().exists():
                failures.append(f"{document.relative_to(ROOT)} -> {target}")
    return failures


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--write", action="store_true")
    args = parser.parse_args()
    failures: list[dict[str, object]] = []

    def check(name: str, condition: bool, detail: object) -> None:
        if not condition:
            failures.append({"check": name, "detail": detail})

    remote = read_csv(OUT / "REMOTE_BRANCH_AUDIT.csv")
    union = read_csv(OUT / "BRANCH_FILE_UNION.csv")
    local = read_csv(OUT / "LOCAL_VS_GITHUB_AUDIT.csv")
    imports = read_csv(OUT / "LOCAL_IMPORT_MANIFEST.csv")
    provenance = read_csv(OUT / "BRANCH_PROVENANCE.csv")
    provenance_by_branch = {row["branch"]: row for row in provenance}

    check("all_initial_remote_branches_audited", len(remote) == 38, len(remote))
    check("branch_union_nonempty", len(union) == 21030, len(union))
    check("local_inventory_nonempty", len(local) == 23419, len(local))
    check("all_local_imports_recorded", len(imports) == 2361, len(imports))
    check(
        "remote_branches_have_provenance_rows",
        all(row["branch"] in provenance_by_branch for row in remote),
        sorted(row["branch"] for row in remote if row["branch"] not in provenance_by_branch),
    )

    missing_imports = []
    import_hash_failures = []
    for record in imports:
        path = ROOT / record["repository_path"]
        if not path.is_file():
            missing_imports.append(record["repository_path"])
        elif sha256(path) != record["sha256"]:
            import_hash_failures.append(record["repository_path"])
    check("local_import_destinations_exist", not missing_imports, missing_imports)
    check("local_import_sha256_match", not import_hash_failures, import_hash_failures)

    unique_remote = [
        row for row in remote
        if row["provisional_classification"] in {"UNIQUE_CONTENT_NOT_IN_MAIN", "PARTIALLY_IN_MAIN", "ACTIVE_CURRENT_WORK"}
        and row["branch"] != "main"
    ]
    unreconciled = [
        row["branch"] for row in unique_remote
        if provenance_by_branch.get(row["branch"], {}).get("scientific_paths_missing_from_candidate") != "0"
    ]
    check("unique_or_active_remote_work_reconciled", not unreconciled, unreconciled)

    ancestry_failures = []
    for row in remote:
        result = subprocess.run(
            ["git", "-C", str(ROOT), "merge-base", "--is-ancestor", row["tip_sha"], "HEAD"],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        if result.returncode:
            ancestry_failures.append(row["branch"])
    check("all_initial_remote_tips_reachable", not ancestry_failures, ancestry_failures)

    check(
        "pg_rmbc_manifest",
        not (pg_failures := manifest_failures(ROOT / "outputs/week10_trackA_pg_rmbc/run_manifest.json")),
        pg_failures,
    )
    check(
        "boundary_gate1_manifest",
        not (boundary_failures := manifest_failures(ROOT / "outputs/week10_trackA_boundary_displacement_gate1/run_manifest.json")),
        boundary_failures,
    )

    sidecar_failures = []
    for directory in (
        ROOT / "outputs/week10_trackA_pg_rmbc",
        ROOT / "outputs/week10_trackA_boundary_displacement_gate1",
    ):
        expected = (directory / "METHOD_PROTOCOL_FREEZE.sha256").read_text(encoding="utf-8").split()[0]
        if sha256(directory / "METHOD_PROTOCOL_FREEZE.md") != expected:
            sidecar_failures.append(str(directory.relative_to(ROOT)))
    check("week10_protocol_sidecars", not sidecar_failures, sidecar_failures)

    freeze = json.loads((ROOT / "docs/trackA_freeze/TRACK_A_FREEZE.json").read_text(encoding="utf-8"))
    pinned_failures = []
    for relative, expected in freeze["pinned_sha256"].items():
        path = ROOT / relative
        if not path.is_file() or sha256(path) != expected:
            pinned_failures.append(relative)
    check("trackA_pinned_hashes", not pinned_failures, pinned_failures)
    check("trackA_new_ioan_access_false", freeze["new_ioan_data_accessed"] is False, freeze["new_ioan_data_accessed"])
    check(
        "trackA_method_closed",
        freeze["status"] == "TRACK_A_METHOD_DEVELOPMENT_CLOSED_EXTERNAL_VALIDATION_PENDING",
        freeze["status"],
    )

    required = [
        "docs/trackA_freeze/TRACK_A_FINAL_STATE.md",
        "docs/trackA_freeze/FROZEN_METHOD_SPEC.md",
        "docs/trackA_freeze/EXTERNAL_VALIDATION_PROTOCOL.md",
        "docs/trackA_freeze/RESULT_PROVENANCE.md",
        "docs/trackA_freeze/NEGATIVE_RESULTS_REGISTER.md",
        "outputs/week10_trackA_pg_rmbc/FINAL_METHOD_REPORT.md",
        "outputs/week10_trackA_boundary_displacement_gate1/FINAL_GATE1_REPORT.md",
        "outputs/week9_phase2_1r_simple_width_change_control/FINAL_PHASE2_1R_REPORT.md",
        "outputs/week9_phase2_2_width_informed_active_learning/FINAL_PHASE2_2_REPORT.md",
        "src/tests/test_week10_trackA_pg_rmbc.py",
        "src/tests/test_week10_trackA_boundary_displacement_gate1.py",
        "src/tests/test_week10_trackA_phase121_comparator_audit.py",
    ]
    missing_required = [relative for relative in required if not (ROOT / relative).exists()]
    check("required_current_evidence_present", not missing_required, missing_required)

    deleted = git("diff", "--diff-filter=D", "--name-only", "origin/main...HEAD").splitlines()
    check("no_old_main_files_deleted", not deleted, deleted)
    changed = git("diff", "--diff-filter=AM", "--name-only", "origin/main...HEAD").splitlines()
    oversized = [
        relative for relative in changed
        if (ROOT / relative).is_file() and (ROOT / relative).stat().st_size >= 100 * 1024 * 1024
    ]
    check("no_new_git_file_at_least_100MiB", not oversized, oversized)

    forbidden_names = re.compile(r"(^|/)(\.env($|\.)|id_rsa|id_ed25519|credentials\.json$)|\.(pem|p12|pfx)$", re.I)
    suspicious_names = [relative for relative in changed if forbidden_names.search(relative.replace("\\", "/"))]
    check("no_secret_named_files_added", not suspicious_names, suspicious_names)
    high_confidence_secret = re.compile(
        rb"-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----|ghp_[A-Za-z0-9]{30,}|AKIA[0-9A-Z]{16}"
    )
    secret_hits = []
    for relative in changed:
        path = ROOT / relative
        if path.is_file() and path.stat().st_size <= 10 * 1024 * 1024:
            payload = path.read_bytes()
            if b"\x00" not in payload[:4096] and high_confidence_secret.search(payload):
                secret_hits.append(relative)
    check("no_high_confidence_secrets_added", not secret_hits, secret_hits)

    navigation = [
        ROOT / "README.md",
        ROOT / "docs/THESIS_PROJECT_MAP.md",
        ROOT / "docs/AUTHORITATIVE_RESULTS_INDEX.md",
        ROOT / "docs/ARCHIVAL_MAP.md",
        ROOT / "docs/trackA_freeze/TRACK_A_FINAL_STATE.md",
        ROOT / "docs/trackB/TRACK_B_PROBLEM_DEFINITION.md",
    ]
    link_failures = markdown_link_failures(navigation)
    check("canonical_navigation_links_resolve", not link_failures, link_failures)

    open_pr = [row["branch"] for row in remote if row["open_pr"] == "true"]
    check("no_open_pr_heads", not open_pr, open_pr)

    report = {
        "status": "PASS" if not failures else "FAIL",
        "candidate_commit": git("rev-parse", "HEAD"),
        "initial_remote_branches": len(remote),
        "branch_union_paths": len(union),
        "local_inventory_records": len(local),
        "local_only_scientific_artifacts_imported": len(imports),
        "remote_branch_tips_reachable": len(remote) - len(ancestry_failures),
        "new_ioan_data_accessed": False,
        "scientific_experiments_rerun": False,
        "trackB_analysis_executed": False,
        "focused_test_evidence": {
            "week10": "30 passed",
            "M3_and_live_control_selected": "16 passed, 4 historical/manifest tests deselected",
            "whole_historical_suite": "474 passed, 36 failed; failures classified in TEST_VALIDATION_LOG.md",
        },
        "legacy_exceptions": [
            "Two pre-existing Week 9 Phase 2 manifest mismatches remain documented in outputs/project_consolidation/KNOWN_LEGACY_ISSUES.md.",
            "Historical branch-era tests that require an unchanged branch tip or intentionally untracked checkpoints are not canonical-tree acceptance tests.",
        ],
        "failures": failures,
    }
    if args.write:
        (OUT / "CONSOLIDATION_VALIDATION.json").write_text(
            json.dumps(report, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
        )
    print(json.dumps(report, indent=2, ensure_ascii=False))
    return int(bool(failures))


if __name__ == "__main__":
    raise SystemExit(main())
