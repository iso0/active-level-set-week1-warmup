"""Deterministic, allowlist-only reading draft; never execute imported research."""
from __future__ import annotations

import argparse
import collections
import csv
import hashlib
import io
import json
import os
from pathlib import Path, PurePosixPath
import posixpath
import re
import subprocess
from urllib.parse import quote, unquote, urlsplit

NS = "docs/research/integration-2026-10-28"
BASE = "3caf7c4e49499f30e6c9b642a226454068f08969"
REPO = "iso0/active-level-set-week1-warmup"
INPUT_HASH = "4d975ea1a4ba839e776e4ecff2a463af88dac82ce6df9f2d2f7b0e00d313edb7"
INPUTS = {
    "schema": "thesis-public-draft-build-inputs-v1",
    "expected_review_manifest_sha256": INPUT_HASH,
    "expected_review_files": 608,
    "expected_review_head": BASE,
    "expected_review_branch": "research-hub-integration-2026-10-28",
    "source_category_required": "PUBLIC_CANDIDATE",
    "publication_approved": False,
    "build_date": "2026-10-28",
    "primary_repository": REPO,
    "primary_visibility": "public",
    "published_commit_verified": BASE,
    "primary_commit_url": "https://github.com/" + REPO + "/commit/" + BASE,
}
CAMPAIGNS = {
    "AD18": ("astra_deep_discovery_20261018", "833211403b50051e1bee25c8af38de8443e154b4"),
    "RP20": ("astra_representation_planning_20261020", "797654d1aad53f28139db1ff994a6602096b7801"),
    "LC24": ("astra_local_correction_20261024", "3b3eb1f5cc596b30d445b0ecc59ac6baa71c98f2"),
    "JL26": ("astra_joint_local_20261026", "a71c638ac9338297021bfc5ba75bd73b1aa0cb9c"),
}
OPS_DOC = re.compile(r"(^OPUS_|^AUTOMATION_|^PERSISTENCE|^CURRENT_REMAINING|^OPERATIONS|^CLOSURE_LOG|^EXPOSURE_LOG|^STATUS\.md$|^REPORT_ASSEMBLY_PLAN|^FINAL_PRESENTATION_PLAN|^FIGURE_AND_AUDIT_PLAN|^DEVELOPMENT_REVIEW_CHECKLIST|^INTEGRATION_GUIDE|^VISUAL_AND_NUMERICAL_REVIEW|^LITERATURE|^ORIGINALITY)", re.I)
OPS_PY = re.compile(r"^(?:control|coordination|controller|ledger|queue_store|resources|run_queue|runner|capacity_watch|operational_watchdog|adapt_runtime|bootstrap|fetch.*|download.*|setup.*|register.*|.*supervisor|.*scheduler|.*watchdog|.*watch|.*bundle|.*delivery|.*handoff|freeze.*|prepare.*|finalize.*|.*worker|seal.*|preserve.*|close.*|.*runtime|resume.*|.*queue|.*coordination|.*resource|.*export|build_review.*|assemble_review.*)\.py$", re.I)
MACHINE = re.compile(r"(?<![A-Za-z0-9])(?:[A-Za-z]:[\\/]|/(?:home|Users)/[A-Za-z0-9_.-]+(?:/|\b)|/mnt/[a-z]/|\\\\[A-Za-z0-9_-]+[\\/])")
NETWORK = re.compile(r"\b(?:10\.\d+\.\d+\.\d+|192\.168\.\d+\.\d+|172\.(?:1[6-9]|2\d|3[01])\.\d+\.\d+|127\.0\.0\.1)\b|https?://[^\s/]+\.(?:internal|local)(?:[:/]|$)", re.I)
SECRETS = [
    re.compile(r"-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----"),
    re.compile(r"\b(?:gh[pousr]_[A-Za-z0-9]{20,}|github_pat_[A-Za-z0-9_]{30,}|AKIA[0-9A-Z]{16}|sk-[A-Za-z0-9_-]{24,})\b"),
    re.compile(r"\b(?:password|passwd|api[_-]?key|access[_-]?token|client[_-]?secret)\s*[:=]\s*['\"][^'\"\n]{6,}['\"]", re.I),
    re.compile(r"https?://[^/\s:@]+:[^/\s@]+@", re.I),
]
RIGHTS = re.compile(r"(?:^\s*(?:#|//|\*)?\s*Copyright\b|all rights reserved|confidential|publication.restricted)", re.I | re.M)
MD = re.compile(r"(!?)\[([^\]\n]*)\]\((<[^>\n]+>|[^)\n]+)\)")
URL = re.compile(r"https?://[^\s<>)\]]+")
ENV = dict(os.environ, GIT_OPTIONAL_LOCKS="0", GIT_NO_LAZY_FETCH="1", GIT_TERMINAL_PROMPT="0", GIT_LFS_SKIP_SMUDGE="1", PYTHONDONTWRITEBYTECODE="1")


def sha(data):
    return hashlib.sha256(data).hexdigest()


def read_csv(path):
    with path.open(encoding="utf-8", newline="") as f:
        return list(csv.DictReader(f))


def stable_digest(rows):
    h = hashlib.sha256()
    for row in sorted(rows, key=lambda r: r[0]):
        h.update((json.dumps(row, ensure_ascii=False, separators=(",", ":")) + "\n").encode())
    return h.hexdigest()


def protected_inline_ranges(line):
    """Code and mathematical notation are source content, not navigation."""
    tick = chr(96)
    patterns = [re.escape(tick) + r"+[^\n]*?" + re.escape(tick) + r"+", r"\$[^$\n]+\$", r"\\\([^\n]*?\\\)", r"\\\[[^\n]*?\\\]"]
    return [m.span() for pattern in patterns for m in re.finditer(pattern, line)]


class Draft:
    def __init__(self, review, root, populate=False, resume=False):
        self.review, self.root = review.resolve(), root.resolve()
        self.populate = populate
        self.resume = resume
        self.records, self.artifacts, self.transforms = [], {}, []
        self.included, self.allowlist, self.diff = [], [], []
        self.generated, self.input_blobs = set(), {}
        self.public_targets, self.external_targets = set(), set()
        self.links_checked = 0

    def output(self, relative, data, generated=True):
        pp = PurePosixPath(relative)
        if pp.is_absolute() or ".." in pp.parts or any(":" in x for x in pp.parts):
            raise RuntimeError("Unsafe output path")
        dest = self.root.joinpath(*pp.parts)
        if not dest.resolve().is_relative_to(self.root):
            raise RuntimeError("Output containment failure")
        dest.parent.mkdir(parents=True, exist_ok=True)
        if isinstance(data, str):
            data = data.encode("utf-8")
        if dest.exists():
            if not self.resume or not dest.is_file() or dest.read_bytes() != data:
                raise RuntimeError("STOP: existing output differs; nothing overwritten")
        else:
            with dest.open("xb") as f:
                f.write(data)
        if generated:
            self.generated.add(relative)

    def jout(self, path, value):
        self.output(path, json.dumps(value, indent=2, ensure_ascii=False) + "\n")

    def cout(self, path, rows, fields=None):
        buffer = io.StringIO(newline="")
        w = csv.DictWriter(buffer, fieldnames=fields or list(rows[0]), extrasaction="ignore", lineterminator="\n")
        w.writeheader()
        w.writerows(rows)
        self.output(path, buffer.getvalue())

    def git(self, *args, input=None, check=True):
        p = subprocess.run(["git", "--no-optional-locks", "-c", "gc.auto=0", "-c", "maintenance.auto=false", "-c", "core.fsmonitor=false", "-C", str(self.review), *args], env=ENV, input=input, capture_output=True)
        if check and p.returncode:
            raise RuntimeError("Read-only Git verification failed")
        return p

    def verify_input(self):
        manifest = self.review / NS / "INTEGRATION_SHA256.csv"
        if sha(manifest.read_bytes()) != INPUT_HASH:
            raise RuntimeError("STOP: review checksum manifest changed")
        rows = read_csv(manifest)
        known = {r["relative_path"] for r in rows} | {NS + "/INTEGRATION_SHA256.csv"}
        for row in rows:
            if re.search(r"sealed.?oracle|NEW185_SEALED", row["relative_path"], re.I):
                raise RuntimeError("Protected filename refused before reading")
            path = self.review / row["relative_path"]
            data = path.read_bytes()
            if len(data) != int(row["bytes"]) or sha(data) != row["sha256"]:
                raise RuntimeError("STOP: reviewed file changed")
            self.input_blobs[row["relative_path"]] = {"sha256": row["sha256"], "bytes": len(data)}
        self.input_blobs[NS + "/INTEGRATION_SHA256.csv"] = {"sha256": INPUT_HASH, "bytes": manifest.stat().st_size}
        status = self.git("status", "--porcelain=v1", "-z", "--untracked-files=all").stdout
        actual = {r[3:].decode("utf-8") for r in status.split(b"\0") if r.startswith(b"?? ")}
        if actual != known or len(known) != 608:
            raise RuntimeError("STOP: reviewed file set/status changed")
        if self.git("rev-parse", "HEAD").stdout.decode().strip() != BASE:
            raise RuntimeError("STOP: reviewed HEAD changed")
        if self.git("symbolic-ref", "--short", "HEAD").stdout.decode().strip() != INPUTS["expected_review_branch"]:
            raise RuntimeError("STOP: reviewed branch changed")
        self.before_status = sha(status)
        self.before_index = sha(Path(self.git("rev-parse", "--git-path", "index").stdout.decode().strip()).read_bytes())
        self.before_refs = self.git("for-each-ref", "--format=%(refname)|%(objectname)").stdout
        return rows

    def initialize(self):
        script_bytes = Path(__file__).read_bytes()
        if self.populate or self.resume:
            names = {p.relative_to(self.root).as_posix() for p in self.root.rglob("*") if p.is_file()}
            if self.populate and names != {"BUILD_INPUTS.json", "tools/build_public_draft.py"}:
                raise RuntimeError("STOP: initial owned draft has unexpected files")
            if self.resume and any(name in names for name in ("PUBLIC_DRAFT_SHA256.csv", "PUBLIC_DRAFT_VALIDATION.json", "PUBLICATION_DECISIONS_REQUIRED.md")):
                raise RuntimeError("STOP: completed/control-record draft cannot be resumed")
            if json.loads((self.root / "BUILD_INPUTS.json").read_text(encoding="utf-8")) != INPUTS:
                raise RuntimeError("STOP: initialization marker does not match")
            self.generated.update({"BUILD_INPUTS.json", "tools/build_public_draft.py"})
        else:
            self.root.mkdir(exist_ok=False)
            self.output("tools/build_public_draft.py", script_bytes)
            self.jout("BUILD_INPUTS.json", INPUTS)

    def load_records(self):
        prov = json.loads((self.review / "docs/research/PROVENANCE.json").read_text(encoding="utf-8"))
        evidence = {r["file_id"]: r for r in prov["imports"]}
        package = read_csv(self.review / NS / "PUBLICATION_CLASSIFICATION.csv")
        generated = read_csv(self.review / NS / "GENERATED_MATERIAL_REVIEW.csv")
        for row in package:
            ev = evidence.get(row["evidence_file_id"])
            r = {"record_id": row["package_file_id"], "review_path": row["preserved_original_path"], "logical_path": row["source_package_path"], "source_category": row["review_category"], "source_sha256": row["sha256"], "byte_size": int(row["byte_size"]), "evidence": ev, "campaign_id": ev["campaign_id"] if ev else "EDITORIAL"}
            self.records.append(r)
        for n, row in enumerate(sorted(generated, key=lambda r: r["path"]), 1):
            info = self.input_blobs[row["path"]]
            self.records.append({"record_id": f"GEN-{n:04d}", "review_path": row["path"], "logical_path": row["path"], "source_category": row["review_category"], "source_sha256": info["sha256"], "byte_size": info["bytes"], "evidence": None, "campaign_id": "EDITORIAL"})
        if len(self.records) != 608 or sum(r["source_category"] == "PUBLIC_CANDIDATE" for r in self.records) != 357:
            raise RuntimeError("Review category inventory changed")
        self.by_id = {r["record_id"]: r for r in self.records}
        self.by_evidence = {r["evidence"]["file_id"]: r for r in self.records if r["evidence"]}
        self.by_coordinate = {(r["evidence"]["campaign_id"], r["evidence"]["original_relative_path"]): r for r in self.records if r["evidence"]}
        source_link_rows = read_csv(self.review / NS / "CURRENT_SOURCE_LINKS.csv")
        paths = {r["original_resolved_relative_path"] for r in source_link_rows if r["integration_resolution"] == "RESOLVES_IN_INTEGRATED_THESIS_BASE"}
        paths.update(r["evidence"]["original_relative_path"] for r in self.records if r["campaign_id"] == "THESIS-NAV")
        allowed = sorted(p for p in paths if PurePosixPath(p).suffix.lower() in {".md", ".py"} and not OPS_DOC.search(PurePosixPath(p).name) and not OPS_PY.search(PurePosixPath(p).name) and not re.search(r"sealed.?oracle|NEW185_SEALED", p, re.I))
        response = self.git("cat-file", "--batch-check", input=("\n".join(BASE + ":" + p for p in allowed) + "\n").encode()).stdout.decode().splitlines()
        if len(response) != len(allowed):
            raise RuntimeError("Published target metadata response mismatch")
        self.public_targets = {p for p, result in zip(allowed, response) if not result.endswith(" missing") and " blob " in result}

    def screen(self, record, data):
        if record["source_category"] != "PUBLIC_CANDIDATE":
            return "EXCLUDED_REVIEW_CATEGORY", []
        try:
            text = data.decode("utf-8")
        except UnicodeDecodeError:
            return "HELD_FOCUSED_REVIEW", ["NON_UTF8_CONTENT"]
        flags = []
        if MACHINE.search(text): flags.append("MACHINE_OR_UNC_PATH")
        if NETWORK.search(text): flags.append("PRIVATE_NETWORK_OR_SERVICE")
        if any(p.search(text) for p in SECRETS): flags.append("POSSIBLE_CREDENTIAL_PATTERN")
        if RIGHTS.search(text): flags.append("RIGHTS_OR_RESTRICTION_NOTICE")
        suffix = PurePosixPath(record["logical_path"]).suffix.lower()
        if suffix == ".md" and re.search(r"<(?:script|iframe|object|embed|img)\b|\b(?:href|src)\s*=", text, re.I):
            flags.append("ACTIVE_OR_EMBEDDED_MARKUP")
        if flags:
            return "HELD_FOCUSED_REVIEW", flags
        ev = record["evidence"]
        if not ev:
            return "REBUILT_EDITORIAL_INPUT", []
        if record["campaign_id"] == "THESIS-NAV":
            if ev["original_relative_path"] not in self.public_targets:
                return "HELD_FOCUSED_REVIEW", ["PUBLISHED_REFERENCE_UNVERIFIED"]
            return "REFERENCED_PUBLISHED_PRIMARY", []
        leaf = PurePosixPath(record["logical_path"]).name
        operational = suffix in {".ps1", ".sh", ".bat", ".cmd"} or OPS_DOC.search(leaf) or OPS_PY.search(leaf) or re.search(r"subprocess\.(?:Popen|run|call)|schtasks|Register-ScheduledTask|sqlite3\.connect|os\.system", text)
        if operational:
            return "HELD_OPERATIONAL_OR_RIGHTS_REVIEW", ["OPERATIONAL_AUTOMATION_OR_THIRD_PARTY_TEXT_SCOPE"]
        if suffix not in {".py", ".md", ".txt"}:
            return "HELD_FOCUSED_REVIEW", ["NON_READING_LAYER_DATATYPE"]
        return "INCLUDED_SOURCE", []

    def select(self):
        for r in self.records:
            if r["source_category"] != "PUBLIC_CANDIDATE":
                r.update(disposition="EXCLUDED_REVIEW_CATEGORY", flags=[])
            else:
                data = (self.review / r["review_path"]).read_bytes()
                if sha(data) != r["source_sha256"]:
                    raise RuntimeError("Reviewed public candidate hash changed")
                disposition, flags = self.screen(r, data)
                r.update(disposition=disposition, flags=flags)
                if disposition == "INCLUDED_SOURCE":
                    logical = r["logical_path"]
                    prefix = "provenance/selection-annex/"
                    if logical.startswith(prefix):
                        suffix = logical[len(prefix):]
                        campaign, remainder = suffix.split("/", 1)
                        logical = "research/astra/" + campaign + "/archive/" + remainder
                    r["public_path"] = logical
                    r["data"] = data
                    self.included.append(r)
        if any(not any(r["campaign_id"] == cid and PurePosixPath(r.get("public_path", "")).name == "FINAL_REPORT.md" and "/archive/" not in r.get("public_path", "") for r in self.included) for cid in CAMPAIGNS):
            raise RuntimeError("A campaign's primary conclusion would be absent")
        for r in self.records:
            status = "INCLUDED" if r["disposition"] == "INCLUDED_SOURCE" else "PUBLISHED_PRIMARY" if r["disposition"] == "REFERENCED_PUBLISHED_PRIMARY" else "EDITORIAL_SUMMARY" if r["disposition"] == "REBUILT_EDITORIAL_INPUT" else "RESTRICTED"
            puburl = self.published_url(r["evidence"]["original_relative_path"]) if status == "PUBLISHED_PRIMARY" else ""
            self.artifacts["REC-" + r["record_id"]] = {"artifact_id": "REC-" + r["record_id"], "campaign_id": r["campaign_id"], "access_status": status, "description": r.get("public_path") or "Reviewed record " + r["record_id"] + "; original excluded or replaced by a public editorial summary", "public_path": r.get("public_path", ""), "public_url": puburl, "source_record_id": r["record_id"], "source_sha256": r["source_sha256"], "byte_size": r["byte_size"], "original_commit": r["evidence"]["original_commit"] if r["evidence"] else "", "source_review_category": r["source_category"], "publication_approved": "false", "availability_note": "Payload included only for explicit allowlist members; no archive or data release is asserted"}

    def published_url(self, path):
        if path not in self.public_targets:
            raise RuntimeError("Unverified published target URL refused")
        self.external_targets.add(path)
        return "https://github.com/" + REPO + "/blob/" + BASE + "/" + quote(path, safe="/._-")

    def archive_link(self, document, artifact_id):
        return self.relative(document, "docs/research/ARCHIVE_MANIFEST.md") + "#" + artifact_id.lower()

    def relative(self, document, target):
        return quote(os.path.relpath(self.root / target, (self.root / document).parent).replace("\\", "/"), safe="/._-")

    def pending(self, record, raw, reason="Not included; access or rights remain unresolved"):
        artifact_id = "PENDING-" + sha((record["record_id"] + "\0" + raw).encode())[:16].upper()
        if artifact_id not in self.artifacts:
            self.artifacts[artifact_id] = {"artifact_id": artifact_id, "campaign_id": record["campaign_id"], "access_status": "PENDING_ARCHIVE", "description": "Referenced evidence or scholarly reference outside this approved-host reading scope", "public_path": "", "public_url": "", "source_record_id": record["record_id"], "source_sha256": "", "byte_size": "", "original_commit": record["evidence"]["original_commit"] if record["evidence"] else "", "source_review_category": "NOT_REVIEWED_FOR_THIS_DRAFT", "publication_approved": "false", "availability_note": reason}
        return artifact_id

    def resolve(self, record, raw, document):
        try:
            parsed = urlsplit(raw)
        except ValueError:
            aid = self.pending(record, raw, "Malformed historical link retained as an explicit pending reference")
            return self.archive_link(document, aid), "PENDING_ARCHIVE", aid
        if re.search(r"sealed.?oracle|NEW185_SEALED", unquote(parsed.path), re.I):
            aid = self.pending(record, "PROTECTED_REFERENCE", "Protected material is excluded and was not accessed")
            self.artifacts[aid]["access_status"] = "RESTRICTED"
            return self.archive_link(document, aid), "RESTRICTED", aid
        if parsed.scheme or parsed.netloc:
            prefix = "/" + REPO + "/blob/" + BASE + "/"
            if parsed.scheme == "https" and parsed.netloc == "github.com" and parsed.path.startswith(prefix):
                candidate = unquote(parsed.path[len(prefix):])
                if candidate in self.public_targets:
                    return self.published_url(candidate), "PUBLISHED_PRIMARY", ""
            aid = self.pending(record, raw, "External URL is outside the verified primary-repository allowlist; no availability assertion")
            return self.archive_link(document, aid), "PENDING_ARCHIVE", aid
        if not parsed.path and parsed.fragment:
            return "#" + parsed.fragment, "LOCAL_FRAGMENT", ""
        original = record["evidence"]["original_relative_path"]
        normalized = posixpath.normpath(posixpath.join(posixpath.dirname(original), unquote(parsed.path))) if parsed.path else original
        match = self.by_coordinate.get((record["campaign_id"], normalized))
        if match:
            aid = "REC-" + match["record_id"]
            if match["disposition"] == "INCLUDED_SOURCE":
                suffix = "#" + parsed.fragment if parsed.fragment else ""
                return self.relative(document, match["public_path"]) + suffix, "INCLUDED", aid
            if match["disposition"] == "REFERENCED_PUBLISHED_PRIMARY":
                return self.published_url(match["evidence"]["original_relative_path"]), "PUBLISHED_PRIMARY", aid
            return self.archive_link(document, aid), "RESTRICTED", aid
        if record["campaign_id"] == "THESIS-NAV" and normalized in self.public_targets:
            return self.published_url(normalized), "PUBLISHED_PRIMARY", ""
        aid = self.pending(record, normalized)
        return self.archive_link(document, aid), "PENDING_ARCHIVE", aid

    def rewrite_markdown(self, record):
        text = record["data"].decode("utf-8")
        result, fenced, math_block = [], False, False
        document = record["public_path"]
        for line_no, line in enumerate(text.splitlines(keepends=True), 1):
            if line.lstrip().startswith((chr(96) * 3, "~~~")):
                fenced = not fenced
                result.append(line)
                continue
            if fenced:
                result.append(line)
                continue
            if line.strip() in {"$$", "\\[", "\\]"}:
                math_block = not math_block
                result.append(line)
                continue
            if math_block:
                result.append(line)
                continue
            protected = protected_inline_ranges(line)
            def replacement(m):
                if any(a <= m.start() < b for a, b in protected):
                    return m.group(0)
                raw = m.group(3).strip()
                raw = raw[1:raw.find(">")] if raw.startswith("<") else re.split(r'\s+["\']', raw, maxsplit=1)[0]
                target, access, aid = self.resolve(record, raw, document)
                label = m.group(2)
                if m.group(1):
                    label = "Figure reference: " + label
                if access in {"RESTRICTED", "PENDING_ARCHIVE"}:
                    label += " (" + access + ")"
                self.transforms.append({"source_record_id": record["record_id"], "public_path": document, "source_line": line_no, "transformation": "NAVIGATION_LABEL_AND_TARGET_ONLY", "original_target_sha256": sha(raw.encode()), "access_status": access, "archive_artifact_id": aid})
                return "[" + label + "](" + target + ")"
            updated = MD.sub(replacement, line)
            # Reference-style definitions keep the original definition key.
            definition = re.match(r"^(\s*\[[^\]]+\]:\s*)(\S+)(.*)$", updated)
            if definition:
                raw = definition.group(2).strip("<>")
                target, access, aid = self.resolve(record, raw, document)
                updated = definition.group(1) + target + definition.group(3) + ("\n" if updated.endswith("\n") else "")
                self.transforms.append({"source_record_id": record["record_id"], "public_path": document, "source_line": line_no, "transformation": "REFERENCE_DEFINITION_TARGET_ONLY", "original_target_sha256": sha(raw.encode()), "access_status": access, "archive_artifact_id": aid})
            ranges = [m.span() for m in MD.finditer(updated)] + protected_inline_ranges(updated)
            pieces, cursor = [], 0
            for match in URL.finditer(updated):
                if any(a <= match.start() < b for a, b in ranges) or definition:
                    continue
                raw = match.group().rstrip(".,;")
                target, access, aid = self.resolve(record, raw, document)
                pieces.append(updated[cursor:match.start()])
                pieces.append("[Reference (" + access + ")](" + target + ")")
                cursor = match.start() + len(raw)
                self.transforms.append({"source_record_id": record["record_id"], "public_path": document, "source_line": line_no, "transformation": "BARE_REFERENCE_URL_ONLY", "original_target_sha256": sha(raw.encode()), "access_status": access, "archive_artifact_id": aid})
            if pieces:
                pieces.append(updated[cursor:])
                updated = "".join(pieces)
            result.append(updated)
        return "".join(result).encode("utf-8")

    def write_sources(self):
        for r in self.included:
            data = self.rewrite_markdown(r) if r["public_path"].endswith(".md") else r["data"]
            self.output(r["public_path"], data, generated=False)
            r["draft_sha256"], r["draft_bytes"] = sha(data), len(data)
            r["content_treatment"] = "NAVIGATION_ONLY_READING_VIEW" if data != r["data"] else "BYTE_IDENTICAL"
            if not r["public_path"].endswith(".md") and sha(data) != r["source_sha256"]:
                raise RuntimeError("Non-Markdown scientific source was changed")

    def public_reference(self, evidence_id):
        r = self.by_evidence[evidence_id]
        aid = "REC-" + r["record_id"]
        item = {"artifact_id": aid, "source_evidence_id": evidence_id, "source_sha256": r["source_sha256"], "original_commit": r["evidence"]["original_commit"]}
        if r["disposition"] == "INCLUDED_SOURCE":
            item.update(access_status="INCLUDED", public_path=r["public_path"], draft_sha256=r["draft_sha256"])
        elif r["disposition"] == "REFERENCED_PUBLISHED_PRIMARY":
            item.update(access_status="PUBLISHED_PRIMARY", public_url=self.published_url(r["evidence"]["original_relative_path"]))
        else:
            item.update(access_status="RESTRICTED", public_registry="docs/research/ARCHIVE_MANIFEST.md#" + aid.lower())
        return item

    def registries(self):
        claims_record = next(r for r in self.records if r["logical_path"] == "docs/research/CLAIM_LEDGER.csv")
        experiments_record = next(r for r in self.records if r["logical_path"] == "docs/research/EXPERIMENT_REGISTRY.csv")
        if any(r["source_category"] != "PUBLIC_CANDIDATE" for r in (claims_record, experiments_record)):
            raise RuntimeError("Editorial scientific inputs are not public candidates")
        claims = read_csv(self.review / claims_record["review_path"])
        experiments = read_csv(self.review / experiments_record["review_path"])
        public_claims = []
        for row in claims:
            refs = []
            for ref in json.loads(row["evidence_references"]):
                value = self.public_reference(ref["file_id"])
                value.update(original_line_start=ref["line_start"], original_line_end=ref["line_end"])
                refs.append(value)
            public_claims.append({"claim_id": row["claim_id"], "campaign_id": row["campaign_id"], "statement": row["statement"], "interpretation_origin": row["interpretation_origin"], "scientific_status": row["scientific_status"], "evidence_scope": row["evidence_scope"], "experiment_ids": row["experiment_ids"], "evidence_references": json.dumps(refs, ensure_ascii=False), "reported_metrics_from_existing_source": row["reported_metrics_verbatim_or_rounded_from_source"], "limitations": row["limitations"], "editorial_input_source_sha256": claims_record["source_sha256"], "new_analysis_performed": "false", "publication_approved": "false"})
        public_experiments = []
        for row in experiments:
            value = {k: row[k] for k in ["experiment_id", "campaign_id", "phase", "interpretation_origin", "data_scope", "endpoint_as_reported", "budget_as_reported", "independent_unit_and_dependence", "recorded_status", "claim_ids", "documentary_commit", "details_and_limits"]}
            value.update(protocol_references=json.dumps([self.public_reference(i) for i in json.loads(row["protocol_file_ids"])], ensure_ascii=False), report_references=json.dumps([self.public_reference(i) for i in json.loads(row["report_file_ids"])], ensure_ascii=False), editorial_input_source_sha256=experiments_record["source_sha256"], new_execution_performed="false", publication_approved="false")
            public_experiments.append(value)
        self.cout("docs/research/CLAIM_LEDGER.csv", public_claims)
        self.cout("docs/research/EXPERIMENT_REGISTRY.csv", public_experiments)
        self.cout("docs/research/REPORTED_FINDINGS.csv", [{"claim_id": r["claim_id"], "campaign_id": r["campaign_id"], "reported_metrics": r["reported_metrics_from_existing_source"], "scientific_status": r["scientific_status"], "scope": r["evidence_scope"], "limits": r["limitations"], "origin": "Projection of the reviewed public-candidate claim ledger; no endpoint recalculation"} for r in public_claims])
        self.public_claims, self.public_experiments = public_claims, public_experiments

    def source_metadata(self):
        provenance, screen = [], []
        for r in self.records:
            disposition = r["disposition"]
            self.diff.append({"review_record_id": r["record_id"], "campaign_id": r["campaign_id"], "source_review_category": r["source_category"], "source_sha256": r["source_sha256"], "source_bytes": r["byte_size"], "draft_disposition": disposition, "public_path": r.get("public_path", ""), "draft_sha256": r.get("draft_sha256", ""), "draft_bytes": r.get("draft_bytes", ""), "publication_approved": "false", "reason_codes": json.dumps(r["flags"]), "nonpublic_original_names_and_paths_omitted": "true" if r["source_category"] != "PUBLIC_CANDIDATE" or disposition.startswith("HELD") else "false"})
            if r["source_category"] == "PUBLIC_CANDIDATE":
                screen.append({"review_record_id": r["record_id"], "campaign_id": r["campaign_id"], "source_sha256": r["source_sha256"], "disposition": disposition, "flags": json.dumps(r["flags"]), "matched_sensitive_values_disclosed": "false"})
                ev = r["evidence"]
                row = {"source_record_id": r["record_id"], "campaign_id": r["campaign_id"], "source_review_category": "PUBLIC_CANDIDATE", "disposition": disposition, "source_sha256": r["source_sha256"], "source_bytes": r["byte_size"], "public_path": r.get("public_path", ""), "draft_sha256": r.get("draft_sha256", ""), "draft_bytes": r.get("draft_bytes", ""), "publication_approved": "false"}
                if ev and disposition in {"INCLUDED_SOURCE", "REFERENCED_PUBLISHED_PRIMARY"}:
                    row.update(original_repo_id=ev["campaign_id"], original_commit=ev["original_commit"], original_relative_path=ev["original_relative_path"], original_git_blob_id=ev["git_blob_id"], historical_context="true" if "/archive/" in r.get("public_path", "") else "false", content_treatment=r.get("content_treatment", "REFERENCE_ONLY"))
                provenance.append(row)
                self.allowlist.append(row)
        self.cout("docs/research/DIFF_FROM_LOCAL_REVIEW.csv", self.diff)
        self.cout("docs/research/PUBLIC_CANDIDATE_SCREEN.csv", screen)
        self.cout("PUBLICATION_ALLOWLIST.csv", self.allowlist, ["source_record_id", "campaign_id", "source_review_category", "disposition", "source_sha256", "source_bytes", "public_path", "draft_sha256", "draft_bytes", "publication_approved", "original_repo_id", "original_commit", "original_relative_path", "original_git_blob_id", "historical_context", "content_treatment"])
        self.jout("PUBLICATION_ALLOWLIST.json", {"schema": "public-draft-explicit-allowlist-v1", "source_manifest_sha256": INPUT_HASH, "category_required": "PUBLIC_CANDIDATE", "included_source_record_ids": [r["record_id"] for r in self.included], "published_reference_record_ids": [r["record_id"] for r in self.records if r["disposition"] == "REFERENCED_PUBLISHED_PRIMARY"], "editorial_input_record_ids": [r["record_id"] for r in self.records if r["disposition"] == "REBUILT_EDITORIAL_INPUT"], "held_public_candidate_record_ids": [r["record_id"] for r in self.records if r["disposition"].startswith("HELD")], "denied_categories": ["PRIVATE_ONLY", "NEEDS_AUTHORIZATION", "NEEDS_SECURITY_REVIEW"], "publication_approved": False, "reproduction": "Use tools/build_public_draft.py with a reviewed input and a fresh destination. Existing destinations are refused; no imported code is run."})
        self.jout("docs/research/PROVENANCE_PUBLIC.json", {"schema": "public-reading-provenance-v1", "campaigns": [{"campaign_id": cid, "original_repository_name": name, "original_commit": commit, "original_history_public_url": None, "note": "Local independent Git history provenance; no GitHub hosting of this Astra commit is asserted"} for cid, (name, commit) in CAMPAIGNS.items()], "published_primary": {"repository": REPO, "commit": BASE, "public_commit_url": INPUTS["primary_commit_url"], "verification": "Public repository and exact commit confirmed read-only through the GitHub connector; permitted target paths additionally checked by Git object metadata"}, "allowlisted_records": provenance, "forensic_originals": "Retained only in the existing local review area; absolute machine paths, usernames, branch-status dumps and private inventories are not copied", "scientific_content_policy": "Source code/dependency text remains byte-identical; Markdown may change navigation targets/availability labels only; conclusions, values, scope and frozen decisions are not recalculated or revised", "publication_approved": False})
        self.cout("docs/research/SOURCE_TRANSFORMATIONS.csv", self.transforms, ["source_record_id", "public_path", "source_line", "transformation", "original_target_sha256", "access_status", "archive_artifact_id"])

    def pages(self):
        nav = "docs/research/SCIENTIFIC_NAVIGATION.md"
        def evidence(eid, label):
            r = self.by_evidence[eid]
            if r["disposition"] == "INCLUDED_SOURCE":
                return "[" + label + "](" + self.relative(nav, r["public_path"]) + ")"
            if r["disposition"] == "REFERENCED_PUBLISHED_PRIMARY":
                return "[" + label + "](" + self.published_url(r["evidence"]["original_relative_path"]) + ")"
            return "[" + label + " — RESTRICTED](" + self.archive_link(nav, "REC-" + r["record_id"]) + ")"
        def ev_for(path):
            return self.by_coordinate[("THESIS-NAV", path)]["evidence"]["file_id"]
        c1 = "outputs/research_campaign_20261026/opus_c1_confirmation/"
        self.output(nav, "# Scientific scopes and reading order\n\n**EDITORIAL SYNTHESIS — no new scientific analysis or publication approval.**\n\n" +
            "## Historical Track A\n\n" + evidence(ev_for("docs/trackA_freeze/TRACK_A_FINAL_STATE.md"), "The frozen Track A decision") + " retains M3 probability margin with feature-only B16 initialization as the historical incumbent/control for its manual-label comparisons. Keep its q20 accuracy-AULC identity. It is not a universal current-model label. Claim TRACKA-001.\n\n" +
            "## Week 17 and Week 18\n\n" + evidence(ev_for("outputs/week17_model_and_acquisition/WEEK17_REPORT.md"), "Week 17") + " reports NO CHANGE JUSTIFIED and retains G3 + margin for that study. " + evidence(ev_for("outputs/week18_independent_research/REPORT.md"), "Week 18") + " retains G3 + margin for binary-only tasks. Depth GP + straddle improvement is confined to OLD-type tasks where revealed depth determines the label; it is not extended to NEW/POOLED. Subsequent corrections remain in the original report. Claims W17-001 and W18-001.\n\n" +
            "## Later C1C in-pool result\n\n" + evidence(ev_for(c1 + "DECISION_C1C.md"), "The C1C decision") + " recommends C1 + margin for specified early and stop-at-0.95 uses within the existing 541-run pool, retaining HA_LEAN + margin as frozen reference and safer extrapolation/sustaining-target reference. This is not external validation. Sustainment was not improved; alternative-start reliability limits and full-pool design exposure remain. Claims C1C-001 through C1C-004.\n\nThe Week 18 block named C1 and the later C1C learner are distinct identifiers. HA_LEAN is not assumed to be an alias of the earlier G3 classifier. The " + evidence(ev_for(c1 + "EXTERNAL_VALIDATION_PLAN_C1C.md"), "external validation plan") + " is a plan, not an executed or authorized experiment.\n\n" +
            "## Astra synthetic campaigns\n\nAD18: scoped representation finding, without general acquisition/query-saving success. RP20: no general planning/local-representation gain and three preserved incomplete paths. LC24: both DEV expansion screens failed; no independent TEST. JL26: independent synthetic model increment, but the practical screen failed against fixed_extra and no acquisition expansion followed. Synthetic latent-monitor evidence is distinct from physical Keyhole labels and C1C in-pool evidence.\n\nEvery conclusion has source references and limits in [CLAIM_LEDGER.csv](CLAIM_LEDGER.csv) and [EXPERIMENT_REGISTRY.csv](EXPERIMENT_REGISTRY.csv). No cross-campaign ranking is introduced.\n")
        self.output("docs/research/READING_GUIDE.md", "# Reading guide\n\nStart at RESEARCH_INDEX, then SCIENTIFIC_NAVIGATION, campaign README_PUBLIC pages, the claim ledger and experiment registry. Imported source is archival reading material; no source script, task text or old agent instruction is authorization to execute anything. No AGENTS/CLAUDE file is installed in this draft.\n\nINCLUDED means a source file is in this local draft. PUBLISHED_PRIMARY means a pinned document/source already exists in the primary thesis repository. RESTRICTED means an original is deliberately absent pending rights/security/operational review. PENDING_ARCHIVE is a transparent reference placeholder; it does not claim an asset, dataset or release is available. Publication approval remains false everywhere.\n\nOnly the newly authored build utility is a deterministic file/metadata tool. It does not import research modules, run experiments, change the reviewed worktree or use an external disk.\n")
        self.output("DATA_AVAILABILITY.md", "# Data and archive availability\n\nThis draft includes no simulation datasets, raw compressed unit records, NPZ checkpoints, SQLite databases, figure files or PDFs. Restricted evidence is represented by explicit registry entries, never by invented Release URLs. The original local review/preservation records remain authoritative for the excluded material. No private inventory or absolute source-machine path is reproduced.\n\nReported metrics in REPORTED_FINDINGS.csv are projections of already reviewed claim text, not new statistical analyses or substitutes for raw evidence. Synthetic, physical-pool, historical, in-pool and external scopes remain distinct. The sealed oracle is completely excluded and was not accessed.\n\nSee [the archive registry](docs/research/ARCHIVE_MANIFEST.md). No decision about releasing excluded data is required to approve this first text/code draft. A separate authorization would be needed for any future data or figure package.\n")
        self.output("RIGHTS_AND_ATTRIBUTION.md", "# Rights and attribution pending\n\nNo license has been selected or granted by the assistant. PUBLIC_CANDIDATE is a review category, not ownership verification or publication approval. Included source and text retain campaign/commit/hash provenance, including historical implementations. Confirm the authority to distribute each campaign's authored text and source, and identify any third-party material before approval.\n\nOperational handoffs, schedulers and literature-review/excerpt files outside the chosen scope remain held. Figures, datasets and PDFs are absent. Published primary-thesis documents are referenced through verified pinned URLs instead of being newly copied. Known method components do not establish a novelty claim.\n\nThe two publication decisions, exact membership hashes and campaign/type groups are in PUBLICATION_DECISIONS_REQUIRED.md. Those decisions concern content and terms only; they do not authorize a Git commit or upload.\n")
        self.output("docs/research/SELECTION_SCOPE.md", "# Selection and preservation scope\n\nThe local integrated hub retains all 608 reviewed records. Its earlier 511-versus-393 comparison contained 366 shared records, 145 omissions preserved in an annex and 27 additions. This first public draft applies a separate category-and-content allowlist. Exclusion here is a publication decision boundary, not deletion or a scientific judgment. Failed experiments, negative conclusions and incomplete findings remain in the campaign reports and scoped registries.\n\nDIFF_FROM_LOCAL_REVIEW.csv accounts for all 608 records with opaque IDs, hashes and dispositions; private original names/paths are omitted. PUBLICATION_ALLOWLIST lists every included source and every reviewed public-candidate input. Exact private forensic manifests stay in the existing local review area.\n")
        summaries = {
            "AD18": "Representation helps on the tested anisotropic boundary; local discovery/acquisition does not establish general improvement or query savings. Small-island failures and versioned amendments remain visible.",
            "RP20": "The proposed local representation and two-step planning do not establish general useful gains. Three incomplete learned paths remain part of the reported record; no terminal outcomes are imputed.",
            "LC24": "Both prospective DEV expansion screens failed. V2 reuses the exposed worlds/paths; no independent TEST or new local-model acquisition experiment was run.",
            "JL26": "Joint global/local learning has a positive independent synthetic model increment, but misses the frozen practical screen versus fixed_extra. No acquisition expansion or physical validation is claimed.",
        }
        campaign_table = []
        for cid, (name, commit) in CAMPAIGNS.items():
            doc = "research/astra/" + name + "/README_PUBLIC.md"
            records = [r for r in self.included if r["campaign_id"] == cid]
            report = next(r for r in records if r["evidence"]["original_relative_path"] == "FINAL_REPORT.md")
            index = next((r for r in records if r["evidence"]["original_relative_path"] == "RESULTS_INDEX.md"), None)
            links = "\n".join("- [" + PurePosixPath(r["public_path"]).name + "](" + self.relative(doc, r["public_path"]) + ")" for r in records if r["public_path"].endswith(".md") and "/archive/" not in r["public_path"])
            self.output(doc, "# " + cid + ": " + name + "\n\n**PUBLICATION DRAFT — not approved. Editorial reading guide.**\n\nOriginal independent repository commit: " + commit + ". No public hosting of that Astra commit is asserted.\n\n" + summaries[cid] + "\n\nStart with [the original scientific report reading view](" + self.relative(doc, report["public_path"]) + "). Scientific conclusions are unchanged; only navigation links/availability labels may differ. Source code is byte-identical, and historical variants are under archive/.\n\n## Reports and protocols\n\n" + links + "\n\n## Evidence limits\n\nFrozen JSON, detailed tables, figures and raw execution records not authorized for this draft remain [explicitly restricted or pending](" + self.relative(doc, "docs/research/ARCHIVE_MANIFEST.md") + "). This is a reading layer, not a runnable complete experiment distribution. Operational scripts were not executed or publication-approved. No new endpoint was computed.\n")
            campaign_table.append("| [" + cid + "](" + doc + ") | " + str(len(records)) + " | " + commit + " | " + summaries[cid] + " |")
        self.output("RESEARCH_INDEX.md", "# Thesis Research Hub — first publication draft\n\n**Local draft only. No file is approved, committed or uploaded.** Read [the two grouped publication decisions](PUBLICATION_DECISIONS_REQUIRED.md), then [scientific navigation by scope](docs/research/SCIENTIFIC_NAVIGATION.md). This is an editorial reading layer built only from reviewed PUBLIC_CANDIDATE sources and newly written safe summaries.\n\n## Campaigns\n\n| Campaign | Included source files | Original commit | Recorded conclusion and scope |\n|---|---:|---|---|\n" + "\n".join(campaign_table) + "\n\n## Registries\n\n- [Claim ledger](docs/research/CLAIM_LEDGER.csv): 16 scoped claims, with original versus editorial interpretation explicit.\n- [Experiment registry](docs/research/EXPERIMENT_REGISTRY.csv): 15 phase/control contexts, with negative and incomplete results retained.\n- [Reported findings](docs/research/REPORTED_FINDINGS.csv): existing reported values only, no recalculation.\n- [Archive manifest](docs/research/ARCHIVE_MANIFEST.md) and [machine-readable registry](docs/research/ARCHIVE_MANIFEST.csv): included, already-published, RESTRICTED and PENDING_ARCHIVE entries.\n- [Public provenance](docs/research/PROVENANCE_PUBLIC.json): logical repository IDs, commits, Git blob IDs and hashes without personal machine paths.\n- [Reproducible allowlist](PUBLICATION_ALLOWLIST.json), [file-level allowlist](PUBLICATION_ALLOWLIST.csv), [differences from all 608 local records](docs/research/DIFF_FROM_LOCAL_REVIEW.csv).\n- [Selection scope](docs/research/SELECTION_SCOPE.md), [rights](RIGHTS_AND_ATTRIBUTION.md), [data availability](DATA_AVAILABILITY.md), [reading guide](docs/research/READING_GUIDE.md).\n- [Draft validation](PUBLIC_DRAFT_VALIDATION.json), [SHA-256 manifest](PUBLIC_DRAFT_SHA256.csv), [group members and hashes](PUBLICATION_GROUP_MEMBERS.csv).\n\nHistorical Track A M3 controls, Week 17–18 G3/binary and OLD depth-threshold findings, later C1C C1/HA_LEAN in-pool decisions and the four Astra synthetic campaigns remain separate. No external validation or general new-method claim is introduced. No figures, datasets, raw unit records, databases or active agent instructions are included.\n")

    def archive_pages(self):
        for cid in CAMPAIGNS:
            aid = "RAW-" + cid
            self.artifacts[aid] = {"artifact_id": aid, "campaign_id": cid, "access_status": "RESTRICTED", "description": "Raw execution/data evidence outside this publication draft", "public_path": "", "public_url": "", "source_record_id": "", "source_sha256": "", "byte_size": "", "original_commit": CAMPAIGNS[cid][1], "source_review_category": "OUTSIDE_PUBLIC_DRAFT_SCOPE", "publication_approved": "false", "availability_note": "No public asset, dataset or release URL is asserted; separate authorization is required"}
        rows = [self.artifacts[k] for k in sorted(self.artifacts)]
        self.cout("docs/research/ARCHIVE_MANIFEST.csv", rows)
        lines = ["# Public evidence and archive registry", "", "All entries remain unapproved. INCLUDED is local draft content. PUBLISHED_PRIMARY is a verified pinned primary-repository reference. RESTRICTED originals are absent. PENDING_ARCHIVE is a reference placeholder, not a claim of availability. Private original filenames and forensic paths are omitted.", ""]
        doc = "docs/research/ARCHIVE_MANIFEST.md"
        for r in rows:
            lines += ["### " + r["artifact_id"], "", "- Status: **" + r["access_status"] + "**; campaign: " + r["campaign_id"] + ".", "- " + r["description"] + "."]
            if r["public_path"]:
                lines.append("- [Open retained reading evidence](" + self.relative(doc, r["public_path"]) + ").")
            if r["public_url"]:
                lines.append("- [Open already-published primary source](" + r["public_url"] + ").")
            if r["source_sha256"]:
                lines.append("- Original content SHA-256: " + r["source_sha256"] + ".")
            lines.append("")
        self.output(doc, "\n".join(lines))

    def heading_ids(self, path):
        ids, counts = set(), collections.Counter()
        for line in path.read_text(encoding="utf-8-sig").splitlines():
            match = re.match(r"^#{1,6}\s+(.+?)\s*#*\s*$", line)
            if match:
                slug = re.sub(r"[^\w\- ]", "", match.group(1).strip().lower()).replace(" ", "-")
                ids.add(slug if not counts[slug] else slug + "-" + str(counts[slug]))
                counts[slug] += 1
        return ids

    def validate(self, future=()):
        future = set(future)
        rows, errors = [], []
        for p in sorted(self.root.rglob("*.md")):
            rel = p.relative_to(self.root).as_posix()
            fenced, math_block = False, False
            for line_no, line in enumerate(p.read_text(encoding="utf-8-sig").splitlines(), 1):
                if line.lstrip().startswith((chr(96) * 3, "~~~")):
                    fenced = not fenced
                    continue
                if fenced:
                    continue
                if line.strip() in {"$$", "\\[", "\\]"}:
                    math_block = not math_block
                    continue
                if math_block:
                    continue
                protected = protected_inline_ranges(line)
                targets = [m.group(3).strip() for m in MD.finditer(line) if not any(a <= m.start() < b for a, b in protected)]
                definition = re.match(r"^\s*\[[^\]]+\]:\s*(\S+)", line)
                if definition:
                    targets.append(definition.group(1))
                for raw in targets:
                    raw = raw[1:raw.find(">")] if raw.startswith("<") else re.split(r'\s+["\']', raw, maxsplit=1)[0]
                    parsed = urlsplit(raw)
                    status = "LOCAL"
                    if parsed.scheme or parsed.netloc:
                        prefix = "https://github.com/" + REPO + "/blob/" + BASE + "/"
                        if not raw.startswith(prefix) or unquote(parsed.path.split("/blob/" + BASE + "/", 1)[-1]) not in self.public_targets:
                            errors.append((rel, line_no, "unapproved external navigation host or target"))
                        status = "VERIFIED_PUBLISHED_PRIMARY"
                    else:
                        target = (p.parent / unquote(parsed.path)).resolve() if parsed.path else p
                        if not target.is_relative_to(self.root):
                            errors.append((rel, line_no, "outside draft"))
                        elif not target.exists() and target.relative_to(self.root).as_posix() not in future:
                            errors.append((rel, line_no, "missing target"))
                        elif parsed.fragment and target.is_file() and target.suffix.lower() == ".md" and unquote(parsed.fragment) not in self.heading_ids(target):
                            errors.append((rel, line_no, "missing fragment"))
                    rows.append({"document": rel, "line": line_no, "target": raw, "resolution": status})
        for p in self.root.rglob("*"):
            if not p.is_file():
                continue
            rel = p.relative_to(self.root).as_posix()
            if p.name.lower() in {"agents.md", "claude.md", "gemini.md"}:
                errors.append((rel, 0, "active imported agent policy"))
            if p.suffix.lower() in {".png", ".pdf", ".svg", ".npz", ".gz", ".sqlite", ".jsonl"}:
                errors.append((rel, 0, "unapproved figure/dataset/raw format"))
            text = p.read_text(encoding="utf-8-sig")
            if MACHINE.search(text) or NETWORK.search(text) or any(x.search(text) for x in SECRETS):
                errors.append((rel, 0, "sensitive-path/network/credential scan"))
            if p.suffix == ".json":
                json.loads(text)
            if p.suffix == ".csv":
                with p.open(encoding="utf-8", newline="") as f:
                    list(csv.reader(f))
        if errors:
            raise RuntimeError("Draft validation failed (values withheld): " + json.dumps(errors[:15]))
        return rows

    def decisions(self, groups, final_count):
        member_rows = []
        for group, members in groups.items():
            for path in members:
                data = (self.root / path).read_bytes()
                member_rows.append({"group_id": group, "public_path": path, "bytes": len(data), "sha256": sha(data), "publication_approved": "false"})
        self.cout("PUBLICATION_GROUP_MEMBERS.csv", member_rows)
        lines = ["# Publication decisions required — first draft", "", "**No decision has been taken by the assistant. Zero files are approved, committed or uploaded.** Two grouped decisions are sufficient for this text/code draft. Excluded data, figures, operations and private originals require no approval now because they are absent.", "", "## Decision D01: authority to distribute the four campaigns", "", "Confirm ownership/permission for the included authored code, dependency descriptions, protocols, reports and historical variants in each campaign below. Hold any subgroup whose authorship or third-party status is unclear. This is not approval of excluded datasets, figures or literature excerpts.", "", "| Campaign | Code/dependency files | Report/protocol files | Total | Bytes | SHA-256 member-set digest |", "|---|---:|---:|---:|---:|---|"]
        for cid in CAMPAIGNS:
            entries = [r for r in member_rows if r["group_id"] == "D01-" + cid]
            code = sum(PurePosixPath(r["public_path"]).suffix != ".md" for r in entries)
            lines.append("| " + cid + " | " + str(code) + " | " + str(len(entries) - code) + " | " + str(len(entries)) + " | " + str(sum(r["bytes"] for r in entries)) + " | " + stable_digest([[r["public_path"], r["bytes"], r["sha256"]] for r in entries]) + " |")
        editorial = [r for r in member_rows if r["group_id"] == "D02-EDITORIAL"]
        editorial_total = final_count - len(self.included)
        lines += ["", "## Decision D02: editorial scope, attribution and release terms", "", "Review the 16 scoped claims, 15 experiment contexts, unchanged negative/incomplete findings, M3/G3/C1C navigation, public link/availability labels, and campaign attribution. Specify the code/text reuse terms you authorize; no license is invented. Confirm that linking to the nine already-published thesis documents is an acceptable source-reference choice. These are same-pool/synthetic/historical distinctions, not new external validation.", "", "This decision covers **" + str(editorial_total) + " newly authored editorial/build/manifest files**. The non-circular member set contains " + str(len(editorial)) + " files / " + str(sum(r["bytes"] for r in editorial)) + " bytes; its SHA-256 digest is **" + stable_digest([[r["public_path"], r["bytes"], r["sha256"]] for r in editorial]) + "**.", "", "Three control files are excluded from that member-set digest to avoid self-hash cycles: PUBLICATION_GROUP_MEMBERS.csv, this decision document, and PUBLIC_DRAFT_SHA256.csv. The final SHA-256 manifest gives the individual hashes of the first two and every other draft file; the checksum manifest's own hash is reported at completion. Exact membership/hashes are in [PUBLICATION_GROUP_MEMBERS.csv](PUBLICATION_GROUP_MEMBERS.csv).", "", "## What is deliberately outside both decisions", "", "PRIVATE_ONLY, NEEDS_AUTHORIZATION and NEEDS_SECURITY_REVIEW originals were not copied. Additional operational/literature/rights-review public candidates remain held. No raw simulation dataset, checkpoint, database, figure, PDF or sealed oracle is part of this draft. No Release URL is fabricated. Any later expansion requires a separate artifact-specific decision.", "", "## Exact draft and input accounting", "", "- Draft files: " + str(final_count) + ".", "- Included original reading sources: " + str(len(self.included)) + ".", "- Referenced published thesis documents: " + str(sum(r["disposition"] == "REFERENCED_PUBLISHED_PRIMARY" for r in self.records)) + " (their payloads are not newly copied).", "- All 608 integrated review records are accounted for in DIFF_FROM_LOCAL_REVIEW.csv; no private original filename/path is disclosed for excluded records.", "- [Explicit allowlist](PUBLICATION_ALLOWLIST.csv), [input/output differences](docs/research/DIFF_FROM_LOCAL_REVIEW.csv), [final hashes](PUBLIC_DRAFT_SHA256.csv), [validation](PUBLIC_DRAFT_VALIDATION.json).", "", "Digest recipe: SHA-256 of sorted compact UTF-8 JSON lines [public_path, bytes, sha256], each followed by LF. These decisions do not authorize git add, commit, upload, release creation or a change of repository visibility."]
        self.output("PUBLICATION_DECISIONS_REQUIRED.md", "\n".join(lines) + "\n")

    def finish(self):
        before_records = len([p for p in self.root.rglob("*") if p.is_file()])
        # Validation, membership, decisions and the checksum are the final four files.
        final_count = before_records + 4
        nav_rows = self.validate({"PUBLICATION_DECISIONS_REQUIRED.md", "PUBLICATION_GROUP_MEMBERS.csv", "PUBLIC_DRAFT_SHA256.csv", "PUBLIC_DRAFT_VALIDATION.json"})
        self.cout("docs/research/PUBLIC_LINKS.csv", nav_rows)
        final_count += 1
        claims = self.public_claims
        experiments = self.public_experiments
        if len({r["claim_id"] for r in claims}) != 16 or len({r["experiment_id"] for r in experiments}) != 15:
            raise RuntimeError("Scientific registry identifiers changed")
        for r in claims:
            if not set(json.loads(r["experiment_ids"])) <= {e["experiment_id"] for e in experiments}:
                raise RuntimeError("Unknown experiment ID")
            for ref in json.loads(r["evidence_references"]):
                if ref["access_status"] == "INCLUDED" and not (self.root / ref["public_path"]).is_file():
                    raise RuntimeError("Claim evidence absent")
        current_status = self.git("status", "--porcelain=v1", "-z", "--untracked-files=all").stdout
        current_index = Path(self.git("rev-parse", "--git-path", "index").stdout.decode().strip()).read_bytes()
        if sha(current_status) != self.before_status or sha(current_index) != self.before_index or self.git("for-each-ref", "--format=%(refname)|%(objectname)").stdout != self.before_refs:
            raise RuntimeError("Reviewed worktree changed during draft build")
        self.verify_input()
        counts = dict(collections.Counter(r["disposition"] for r in self.records))
        validation = {"schema": "public-draft-validation-v1", "status": "STRUCTURAL_AND_SCREENING_CHECKS_PASS_NOT_PUBLICATION_APPROVAL", "source_review_records": 608, "reviewed_public_candidates": 357, "record_dispositions": counts, "included_original_sources": len(self.included), "included_source_bytes": sum(r["draft_bytes"] for r in self.included), "byte_identical_sources": sum(r["content_treatment"] == "BYTE_IDENTICAL" for r in self.included), "navigation_only_markdown_views": sum(r["content_treatment"] != "BYTE_IDENTICAL" for r in self.included), "campaigns_retained": sorted(CAMPAIGNS), "claims": 16, "experiment_contexts": 15, "new_statistical_analyses": 0, "private_or_authorization_or_security_category_originals_copied": 0, "figures_pdfs_raw_datasets_or_databases": 0, "active_agent_instruction_files": 0, "scanned_sensitive_path_or_credential_findings_in_included_files": 0, "public_navigation_links_checked_before_final_control_documents": len(nav_rows), "navigation_missing_targets": 0, "verified_published_primary_target_paths": len(self.public_targets), "published_primary_repository": REPO, "published_primary_commit": BASE, "original_review_unchanged": True, "original_review_manifest_sha256": INPUT_HASH, "draft_file_count": final_count, "decision_groups": 2, "publication_approved_files": 0, "remaining_decisions": ["D01: confirm campaign ownership/permission including historical source and authored text", "D02: approve editorial scope/attribution and specify authorized code/text reuse terms"], "excluded_uncertain_cases_remain_local": True, "external_disk_access": False, "sealed_oracle_access": False, "imported_scripts_executed": False, "research_tests_simulations_experiments_or_graphify": False, "git_mutations_or_uploads": False, "manifest_self_hash_note": "Final manifest excludes itself; its hash is printed at completion"}
        self.jout("PUBLIC_DRAFT_VALIDATION.json", validation)
        included_paths = {r["public_path"] for r in self.included}
        groups = {"D01-" + cid: [r["public_path"] for r in self.included if r["campaign_id"] == cid] for cid in CAMPAIGNS}
        groups["D02-EDITORIAL"] = sorted(p.relative_to(self.root).as_posix() for p in self.root.rglob("*") if p.is_file() and p.relative_to(self.root).as_posix() not in included_paths)
        self.decisions(groups, final_count)
        self.validate({"PUBLIC_DRAFT_SHA256.csv"})
        paths = sorted(p for p in self.root.rglob("*") if p.is_file())
        checksum_rows = [{"path": p.relative_to(self.root).as_posix(), "bytes": p.stat().st_size, "sha256": sha(p.read_bytes()), "role": "allowlisted_source_or_navigation_view" if p.relative_to(self.root).as_posix() in included_paths else "new_public_editorial_or_control"} for p in paths]
        self.cout("PUBLIC_DRAFT_SHA256.csv", checksum_rows)
        actual_count = sum(p.is_file() for p in self.root.rglob("*"))
        if actual_count != final_count:
            raise RuntimeError("Final file count does not match deterministic plan")
        for row in checksum_rows:
            data = (self.root / row["path"]).read_bytes()
            if len(data) != row["bytes"] or sha(data) != row["sha256"]:
                raise RuntimeError("Final public draft checksum mismatch")
        print(json.dumps({"status": "PUBLIC_DRAFT_CREATED_UNAPPROVED", "files": actual_count, "bytes": sum(p.stat().st_size for p in self.root.rglob("*") if p.is_file()), "source_dispositions": counts, "included_sources": len(self.included), "included_source_files_by_campaign": dict(collections.Counter(r["campaign_id"] for r in self.included)), "claims": 16, "experiments": 15, "required_grouped_decisions": 2, "publication_approved": 0, "source_review_unchanged": True, "public_manifest_sha256": sha((self.root / "PUBLIC_DRAFT_SHA256.csv").read_bytes()), "allowlist_sha256": sha((self.root / "PUBLICATION_ALLOWLIST.csv").read_bytes())}, ensure_ascii=True))

    def build(self):
        self.verify_input()
        self.initialize()
        self.load_records()
        self.select()
        self.write_sources()
        self.registries()
        self.source_metadata()
        self.pages()
        self.archive_pages()
        self.finish()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--review-dir", type=Path, required=True)
    parser.add_argument("--destination", type=Path, required=True)
    parser.add_argument("--populate-initial-owned-draft", action="store_true", help="Initial task bootstrap only; refuses anything except its two owned bootstrap files")
    parser.add_argument("--resume-owned-incomplete-draft", action="store_true", help="Current-task recovery only; existing output must match byte-for-byte and is never overwritten")
    args = parser.parse_args()
    if args.destination.exists() and not (args.populate_initial_owned_draft or args.resume_owned_incomplete_draft):
        raise SystemExit("STOP: destination already exists; nothing overwritten")
    Draft(args.review_dir, args.destination, args.populate_initial_owned_draft, args.resume_owned_incomplete_draft).build()


if __name__ == "__main__":
    main()
