"""Every saved paid transition and posterior snapshot, without model refitting."""
import argparse
import gzip
import hashlib
import json
import time
from coordination import ROOT, Slot, now
from ledger import atomic_json, sha256, connection


def run():
    import numpy as np
    from posterior import GaussianState
    from mixture_acquisition import state_hash
    manifest = json.loads((ROOT/"FROZEN_TEST_V1.json").read_text())
    for name, value in manifest["source_hashes"].items():
        assert sha256(ROOT/name) == value
    start = time.process_time()
    out = ROOT/"results/audits"
    out.mkdir(exist_ok=True)
    cache = out/"path_integrity"
    cache.mkdir(exist_ok=True)
    totals, issues = [], []
    sources = {}
    numerical = []
    for unit in manifest["units"]:
        resultfile = ROOT/"results/TEST"/(unit["id"]+".json.gz")
        if not resultfile.exists():
            issues.append({"unit": unit["id"], "kind": "missing_result"})
            continue
        r = json.loads(gzip.decompress(resultfile.read_bytes()))
        path = ROOT/r["prequery_records"]
        receipt = cache/(unit["id"]+".json")
        if receipt.exists():
            old = json.loads(receipt.read_text())
            assert old["result_sha256"] == sha256(resultfile)
            totals.append(old)
            numerical.extend(old["numerical"])
            continue
        try:
            ids = r["paid_ids"]
            assert len(ids) == unit["horizon"] == len(set(ids)) == len(r["observations"])
            assert ids[:unit["start_budget"]] == r["world"]["public_prefix_ids"][:unit["start_budget"]]
            assert r["manifest_sha256"] == sha256(ROOT/"FROZEN_TEST_V1.json")
            key = unit["world_id"]
            signature = (r["world"]["world_hash"], json.dumps(r["observations"][:8], sort_keys=True))
            if key in sources:
                assert sources[key] == signature
            sources[key] = signature
            assert len(list(path.glob("*.pre.json"))) == unit["horizon"]-unit["start_budget"]
            rows, hashes = [], []
            for budget in range(unit["start_budget"]+1, unit["horizon"]+1):
                prefix = path/f"b{budget:03d}"
                prefile, paidfile, snapfile = [prefix.with_suffix(s) for s in (".pre.json", ".paid.json", ".npz")]
                pre = json.loads(prefile.read_text())
                paid = json.loads(paidfile.read_text())
                assert paid == r["observations"][budget-1]
                assert paid["paid_id"] == pre["selected"] == ids[budget-1]
                assert pre["paid_before"] == budget-1
                assert paid["cost"] == 1 and pre["selected"] in pre["ids"]
                assert pre["snapshot_file_sha256"] == sha256(snapfile)
                with np.load(snapfile, allow_pickle=False) as z:
                    s = GaussianState(*(z[name] for name in ("reference_mean", "reference_variance", "candidate_mean",
                         "candidate_covariance", "cross_covariance", "noise_variance")),
                         float(z["availability"]), str(z["source_hash"].item()), tuple(map(int, z["ids"])))
                    assert list(s.ids) == pre["ids"] and s.source_hash == pre["model_hash"]
                    digest = s.digest()
                    if "component_weights" in z:
                        mixture = {k[len("component_"):]: z[k] for k in z.files if k.startswith("component_")}
                        mh = state_hash(mixture)
                        assert mh == pre["details"]["mixture_state_hash"]
                        digest = hashlib.sha256((digest+mh).encode()).hexdigest()
                    assert digest == pre["snapshot_hash"] == paid["prequery_hash"]
                    assert np.isfinite(s.reference_mean).all() and (s.reference_variance > 0).all()
                    assert (s.noise_variance >= 0).all()
                    assert np.min(np.linalg.eigvalsh(s.candidate_covariance)) >= -1e-7
                if pre["mode"] in ("risk_h2", "mixture_risk_h1"):
                    d = pre["details"]
                    rows.append({"unit": unit["id"], "family": unit["family"], "panel": unit["panel"],
                        "model": unit["model"], "mode": pre["mode"], "budget": budget,
                        "integration_accepted": d["integration_accepted"], "order": d["order"],
                        "rank_changed": d["rank_changed"], "fallback": d.get("fallback"),
                        "absolute_score_converged": d.get("absolute_score_converged"),
                        "quadrature_diagnostics": d.get("quadrature_diagnostics")})
                hashes.append({"budget": budget, "pre_sha256": sha256(prefile), "paid_sha256": sha256(paidfile),
                               "snapshot_sha256": pre["snapshot_file_sha256"], "posterior_hash": pre["snapshot_hash"]})
            output = {"unit": unit["id"], "status": "PASS", "result_sha256": sha256(resultfile),
                      "paid_n": len(ids), "post_startup_snapshots": len(hashes), "hashes": hashes, "numerical": rows}
            atomic_json(receipt, output)
            totals.append(output); numerical.extend(rows)
        except Exception as exc:
            issues.append({"unit": unit["id"], "kind": "integrity_error", "error": repr(exc)})
    from analyze_test import write_csv
    write_csv(out/"numerical_decision_diagnostics.csv", numerical)
    groups = {}
    for row in numerical:
        key = row["panel"]+"__"+row["model"]+"__"+row["mode"]
        s = groups.setdefault(key, {"decisions": 0, "unaccepted": 0, "fallbacks": 0, "rank_changes": 0})
        s["decisions"] += 1
        s["unaccepted"] += not row["integration_accepted"]
        s["fallbacks"] += bool(row["fallback"])
        s["rank_changes"] += row["rank_changed"]
    output = {"status": "PASS" if not issues else "ISSUES_RETAINED", "utc": now().isoformat(),
        "complete_path_receipts": len(totals), "snapshots": sum(r["post_startup_snapshots"] for r in totals),
        "issues": issues, "numeric_groups": groups, "cpu_seconds": time.process_time()-start,
        "source_sha256": sha256(__file__), "test_manifest_sha256": sha256(ROOT/"FROZEN_TEST_V1.json"),
        "scope": "All completed TEST path snapshots, unique IDs and paid transitions; cached per-path receipts retain immutable hashes. No replay of paid simulator outcomes or model fits."}
    atomic_json(out/"PATH_INTEGRITY.json", output)
    print(json.dumps(output, indent=2))


if __name__ == "__main__":
    p = argparse.ArgumentParser(); p.add_argument("--threads", type=int, choices=[1], required=True); p.parse_args()
    with Slot():
        run()
