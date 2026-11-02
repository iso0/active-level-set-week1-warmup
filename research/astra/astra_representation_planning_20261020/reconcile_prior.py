"""Read-only reconciliation and portable evidence bundle. Never imports old numerical code."""
import csv
from contextlib import redirect_stdout
from datetime import datetime, timezone
import hashlib
import importlib.util
import io
import json
from pathlib import Path
import shutil
import statistics
import subprocess
import zipfile
from coordination import ROOT, CAMPAIGN, Slot


def digest(path):
    with Path(path).open("rb") as f:
        return hashlib.file_digest(f, "sha256").hexdigest()


def run():
    prior = Path(CAMPAIGN["prior_package"])
    out = ROOT / "review_bundle"
    out.mkdir(exist_ok=True)
    report = out / "LOCAL_RECONCILIATION.json"
    if report.exists():
        saved = json.loads(report.read_text())
        assert saved["status"] == "PASS"
        return saved
    # Even cached-table arithmetic is charged to the new allocation.
    with Slot():
        spec = importlib.util.spec_from_file_location("saved_delivery_verifier", prior / "verify_delivery.py")
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        captured = io.StringIO()
        with redirect_stdout(captured):
            exit_code = module.main()
        verified = json.loads(captured.getvalue())
        assert exit_code == 0
        assert verified["status"] == "PASS", verified
        sha = subprocess.check_output(["git", "-C", str(prior), "rev-parse", "HEAD"], text=True).strip()
        dirty = subprocess.check_output(["git", "-C", str(prior), "status", "--porcelain"], text=True)
        assert sha == CAMPAIGN["prior_final_commit"] and not dirty
        table = prior / "results/analysis/v2__TEST/per_seed_endpoints.csv"
        with table.open(newline="", encoding="utf-8-sig") as f:
            rows = list(csv.DictReader(f))
        selected = {(r["family"], r["seed"], r["model"]): r for r in rows
                    if r["selector"] == "boundary_regional" and r["model"] in ("simple", "structure")}
        worlds = sorted({(r["family"], r["seed"]) for r in rows})
        effects = []
        for family, seed in worlds:
            a, b = [selected[family, seed, kind] for kind in ("structure", "simple")]
            effects.append({"family": family, "seed": seed,
                            "delta_error": float(a["error"]) - float(b["error"]),
                            "structure_error": float(a["error"]), "simple_error": float(b["error"]),
                            "structure_attained": a["target_event"] == "True",
                            "simple_attained": b["target_event"] == "True"})
        observed = {
            "worlds": len(worlds),
            "primary_H4_delta_error": statistics.mean(r["delta_error"] for r in effects),
            "anisotropic_structure_error": statistics.mean(r["structure_error"] for r in effects if r["family"] == "anisotropic"),
            "anisotropic_simple_error": statistics.mean(r["simple_error"] for r in effects if r["family"] == "anisotropic"),
            "other_13_families_delta_error": statistics.mean(r["delta_error"] for r in effects if r["family"] != "anisotropic"),
            "structure_attained": sum(r["structure_attained"] for r in effects),
            "simple_attained": sum(r["simple_attained"] for r in effects),
        }
        assert observed["worlds"] == 336
        assert observed["structure_attained"] == 148 and observed["simple_attained"] == 164
        assert abs(observed["primary_H4_delta_error"] + .0326465) < 1e-6
        package = out / "prior_completed_evidence"
        names = set()
        for pattern in ("*.py", "*.ps1", "*.md", "*.json", "requirements.txt",
                        "history/**/*", "handoff/**/*", "results/analysis/**/*",
                        "results/final_tables/*", "results/final_readout/*",
                        "results/references/*", "results/*.json", "results/finalization/*.json"):
            for p in prior.glob(pattern):
                if p.is_file() and "__pycache__" not in p.parts:
                    names.add(p.relative_to(prior).as_posix())
        # All per-world tables are included. Raw fit trajectories are selectively included,
        # with all omitted raw files still bound by the original complete delivery manifest.
        replay = json.loads((prior / "results/analysis/v2__TEST/PATH_REPLAY.json").read_text())
        def raw_ids(obj):
            if isinstance(obj, str) and obj.startswith("v2__TEST__"):
                yield obj
            if isinstance(obj, dict):
                for x in obj.values():
                    yield from raw_ids(x)
            if isinstance(obj, list):
                for x in obj:
                    yield from raw_ids(x)
        for unit in set(raw_ids(replay)):
            p = prior / "results/TEST" / (unit + ".json.gz")
            if p.exists():
                names.add(p.relative_to(prior).as_posix())
        hashes = {}
        for name in sorted(names):
            src, dst = prior / name, package / name
            dst.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(src, dst)
            hashes[name] = digest(src)
            assert digest(dst) == hashes[name]
        figures = [name for name in hashes if name.startswith("results/analysis/v2__TEST/") and name.endswith(".png")]
        assert len(figures) == 18
        index = {"original_root": str(prior), "original_commit": sha, "files": hashes,
                 "figures": figures, "raw_trajectories_included": [n for n in hashes if n.endswith(".json.gz")],
                 "omitted": [
                     "Most raw trajectory gzip files: every per-world endpoint and learning readout is included; original DELIVERY_MANIFEST.json binds all raw files.",
                     "SQLite queues, checkpoints, stdout logs and Git object database: retained in the original local package, not necessary for numerical table review.",
                     "External/private physical data and external literature PDFs: not included.",
                 ]}
        (out / "PRIOR_BUNDLE_MANIFEST.json").write_text(json.dumps(index, indent=2) + "\n")
        result = {"status": "PASS", "utc": datetime.now(timezone.utc).isoformat(),
                  "prior_commit": sha, "prior_git_clean": True, "prior_delivery_verification": verified,
                  "recomputed_from_all_world_endpoints": observed, "source_files_copied_byte_identically": len(hashes),
                  "bundle_manifest_sha256": digest(out / "PRIOR_BUNDLE_MANIFEST.json"),
                  "fits_repeated": 0, "numerical_references_reexecuted": 0,
                  "interpretation": "The old broad gain is coordinate-anisotropy representation evidence, not an ARD comparison or general discovery gain."}
        report.write_text(json.dumps(result, indent=2) + "\n")
        with zipfile.ZipFile(out / "PRIOR_COMPLETED_REVIEW.zip", "w", compression=zipfile.ZIP_DEFLATED, compresslevel=6) as z:
            for name in sorted(hashes):
                z.write(package / name, "prior_completed_evidence/" + name)
            for name in ("PRIOR_BUNDLE_MANIFEST.json", "LOCAL_RECONCILIATION.json"):
                z.write(out / name, name)
        (out / "ZIP_SHA256.json").write_text(json.dumps({"PRIOR_COMPLETED_REVIEW.zip": digest(out / "PRIOR_COMPLETED_REVIEW.zip")}, indent=2) + "\n")
        return result


if __name__ == "__main__":
    print(json.dumps(run(), indent=2))
