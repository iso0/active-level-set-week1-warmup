"""Closeout validation for Week 7 Phase 5.5 artifacts and notebook."""

from __future__ import annotations

import ast
import csv
import hashlib
import json
import subprocess
from pathlib import Path
from typing import Any

import nbformat
import pandas as pd
from PIL import Image

from src.week7_sph_v2_common import output_manifest, sha256_file, write_csv, write_json


ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "outputs" / "week7_05_5_g3_robustness_transfer_analysis"
NOTEBOOK = ROOT / "notebooks" / "week_07" / "05_5_g3_robustness_transfer_analysis.ipynb"
SOURCE = ROOT / "src" / "week7_phase5_5_g3_robustness_transfer_analysis.py"
BUILDER = ROOT / "scripts" / "build_week7_05_5_notebook.py"
PHASE5_SHA = "3367f4c9b5af2def802f72a65258f5cc01896bac"
PHASE5_BRANCH = "codex/week7-phase5-keyhole-physical-proxy-analysis"
PHASE55_BRANCH = "codex/week7-phase5-5-g3-robustness-transfer"
CURRENT_REVISION = "b6dc254a2b607a31cb9f97b40990339c3d5ca1e8"
ORIGINAL = Path(r"C:\Users\ozgur\Documents\thesis")
PHASE5_WORKTREE = Path(r"C:\Users\ozgur\Documents\thesis-week7-phase5-keyhole-physical-proxy-analysis")

MINIMUM_ARTIFACTS = [
    "phase55_preflight.json", "input_provenance.json", "hf_change_audit.json",
    "population_readiness_by_partition.csv", "label_composition_by_partition.csv",
    "candidate_availability_by_partition.csv", "candidate_group_descriptives_by_partition.csv",
    "candidate_univariate_separation_by_partition.csv", "threshold_within_population_summary.csv",
    "threshold_cross_population_transfer_summary.csv", "threshold_cross_population_fold_details.csv",
    "threshold_stability_summary.csv", "threshold_margin_diagnostics.csv",
    "proxy_bootstrap_uncertainty_summary.csv", "subgroup_transient_persistent_summary.csv",
    "subgroup_t0_timing_summary.csv", "process_map_partition_summary.csv",
    "phase55_boundary_formulation_recommendation.csv", "g3_vs_r3_vs_max_vs_t0_transfer_decision.csv",
    "phase55_scorecard.csv", "validation_results.csv", "requirement_checklist.csv",
    "summary.json", "results_summary.md", "figure_manifest.csv", "output_manifest.csv",
]


def git(*args: str, cwd: Path = ROOT, check: bool = True) -> str:
    result = subprocess.run(
        ["git", *args], cwd=cwd, check=check, capture_output=True,
        text=True, encoding="utf-8",
    )
    return result.stdout.strip()


def notebook_audit() -> dict[str, Any]:
    nb = nbformat.read(NOTEBOOK, as_version=4)
    code_cells = [cell for cell in nb.cells if cell.cell_type == "code"]
    errors = []
    for index, cell in enumerate(code_cells, start=1):
        for output in cell.get("outputs", []):
            if output.get("output_type") == "error":
                errors.append({"cell": index, "ename": output.get("ename"), "evalue": output.get("evalue")})
    headings = [
        line.strip()
        for cell in nb.cells if cell.cell_type == "markdown"
        for line in cell.source.splitlines() if line.startswith("## ")
    ]
    return {
        "code_cell_count": len(code_cells),
        "execution_counts": [cell.get("execution_count") for cell in code_cells],
        "stored_errors": errors,
        "section_headings": headings,
    }


def manifest_audit() -> dict[str, Any]:
    rows = list(csv.DictReader((OUT / "output_manifest.csv").open(encoding="utf-8-sig", newline="")))
    missing = []
    mismatched = []
    for row in rows:
        relative = row.get("relative_path") or row.get("path") or row.get("file")
        path = ROOT / relative
        if not path.is_file():
            missing.append(relative)
            continue
        actual = hashlib.sha256(path.read_bytes()).hexdigest().lower()
        expected = (row.get("sha256") or row.get("sha_256") or "").lower()
        if actual != expected:
            mismatched.append(relative)
    return {"row_count": len(rows), "missing": missing, "mismatched": mismatched}


def source_scope_audit() -> dict[str, Any]:
    tree = ast.parse(SOURCE.read_text(encoding="utf-8"))
    imports = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imports.extend(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom):
            imports.append(node.module or "")
    text = SOURCE.read_text(encoding="utf-8").lower()
    forbidden_tokens = [
        "gaussianprocessregressor", "gaussianprocessclassifier", "ridge(",
        "randomforest", "acquisition_function(", "fit_predict(",
    ]
    return {
        "imports": imports,
        "forbidden_token_hits": [token for token in forbidden_tokens if token in text],
        "model_namespace_imports": [item for item in imports if item.startswith("sklearn.") and not item.startswith("sklearn.metrics")],
    }


def original_dirty_audit(preflight: dict[str, Any]) -> dict[str, Any]:
    original = preflight["original_worktree"]
    current_status = git("status", "--porcelain=v1", cwd=ORIGINAL).splitlines()
    hashes = []
    for record in original["protected_dirty_files"]:
        path = ORIGINAL / record["path"]
        actual = sha256_file(path) if path.is_file() else ""
        hashes.append(actual.lower() == str(record["expected_sha256"]).lower())
    return {
        "branch_matches": git("branch", "--show-current", cwd=ORIGINAL) == original["branch"],
        "head_matches": git("rev-parse", "HEAD", cwd=ORIGINAL) == original["head"],
        "status_matches": current_status == original["git_status_short"],
        "protected_hashes_match": bool(hashes) and all(hashes),
        "status_line_count": len(current_status),
        "protected_file_count": len(hashes),
    }


def add_check(rows: list[dict[str, Any]], check_id: str, name: str, passed: bool, detail: str, category: str) -> None:
    rows.append({
        "check_id": check_id, "check": name, "status": "PASS" if passed else "FAIL",
        "detail": detail, "category": category,
    })


def build_validation() -> pd.DataFrame:
    preflight = json.loads((OUT / "phase55_preflight.json").read_text(encoding="utf-8"))
    hf = json.loads((OUT / "hf_change_audit.json").read_text(encoding="utf-8"))
    summary = json.loads((OUT / "summary.json").read_text(encoding="utf-8"))
    readiness = pd.read_csv(OUT / "population_readiness_by_partition.csv").set_index("population")
    refresh = pd.read_csv(OUT / "current_revision_target_refresh_audit.csv")
    targets = pd.read_parquet(OUT / "current_revision_simulation_level_targets.parquet")
    availability = pd.read_csv(OUT / "candidate_availability_by_partition.csv")
    within = pd.read_csv(OUT / "threshold_within_population_summary.csv")
    within_folds = pd.read_csv(OUT / "threshold_within_population_fold_details.csv")
    transfer = pd.read_csv(OUT / "threshold_cross_population_transfer_summary.csv")
    transfer_details = pd.read_csv(OUT / "threshold_cross_population_fold_details.csv")
    bootstrap = pd.read_csv(OUT / "proxy_bootstrap_uncertainty_summary.csv")
    margins = pd.read_csv(OUT / "threshold_margin_diagnostics.csv")
    figures = pd.read_csv(OUT / "figure_manifest.csv")
    decision = pd.read_csv(OUT / "g3_vs_r3_vs_max_vs_t0_transfer_decision.csv").set_index("candidate_id")
    notebook = notebook_audit()
    scope = source_scope_audit()
    original = original_dirty_audit(preflight)
    rows: list[dict[str, Any]] = []

    add_check(rows,"V01","Phase 5.5 branch and exact Phase 5 parent",git("branch","--show-current")==PHASE55_BRANCH and git("rev-parse","HEAD")==PHASE5_SHA,git("branch","--show-current")+" @ "+git("rev-parse","HEAD"),"provenance")
    phase5_local=git("rev-parse","HEAD",cwd=PHASE5_WORKTREE); phase5_upstream=git("rev-parse","@{upstream}",cwd=PHASE5_WORKTREE); phase5_remote=git("ls-remote","--heads","origin",f"refs/heads/{PHASE5_BRANCH}",cwd=PHASE5_WORKTREE).split("\t")[0]
    add_check(rows,"V02","Committed Phase 5 local/upstream/remote equality",phase5_local==phase5_upstream==phase5_remote==PHASE5_SHA,f"local={phase5_local}; upstream={phase5_upstream}; remote={phase5_remote}","provenance")
    live=git("ls-remote","https://huggingface.co/datasets/ioandanielc/sph_v2","refs/heads/main").split("\t")[0]
    add_check(rows,"V03","Live HF main is the analysed revision",live==CURRENT_REVISION,live,"dataset")
    add_check(rows,"V04","HF diff is exactly 110 approved additions",hf["only_expected_monitor_additions"] and hf["change_record_count"]==110 and hf["changed_experiment_count"]==55,str(hf["filename_counts"]),"dataset")
    protected_hf=not any([hf["new_data_paths_changed"],hf["label_paths_changed"],hf["geometry_paths_changed"],hf["iteration_paths_changed"]]) and hf["modified_or_deleted_paths"]==0
    add_check(rows,"V05","Labels, new-data, geometry, and iteration paths unchanged",protected_hf,"all protected path classes unchanged","dataset")
    add_check(rows,"V06","Exactly 55 pinned failures changed to current PASS",int(refresh["status_changed"].sum())==55 and refresh.loc[refresh["status_changed"],"phase55_refresh_action"].eq("reextracted_from_current_verified_monitor_bundle").all(),f"status_changed={int(refresh['status_changed'].sum())}","target_refresh")
    unexpected_reuse_change=refresh[~refresh["phase55_refresh_action"].eq("reextracted_from_current_verified_monitor_bundle") & refresh["status_changed"]]
    add_check(rows,"V07","No unchanged-input target status changed",unexpected_reuse_change.empty,f"unexpected={len(unexpected_reuse_change)}","target_refresh")
    add_check(rows,"V08","All 407 simulations retained with 405 usable",len(targets)==407 and targets["experiment_name"].is_unique and int(targets["physical_target_extraction_success"].sum())==405,f"rows={len(targets)}; usable={int(targets['physical_target_extraction_success'].sum())}","target_refresh")
    exact_readiness=(readiness.loc["new-data","physical_target_ready_count"]==164 and readiness.loc["old-data-local","physical_target_ready_count"]==178 and readiness.loc["old-data-remote-clean","physical_target_ready_count"]==63 and readiness.loc["all-old","physical_target_ready_count"]==241 and readiness.loc["all-combined","physical_target_ready_count"]==405)
    add_check(rows,"V09","Partition readiness counts are exact",exact_readiness,"164/165; 178/179; 63/63; 241/242; 405/407","target_refresh")
    add_check(rows,"V10","Candidate availability is explicit for all five populations",len(availability)==5*8 and availability["available_count"].gt(0).all(),f"rows={len(availability)}","population")
    add_check(rows,"V11","Five-population LOO summary is complete",len(within)==5*8 and set(within["population"])=={"new-data","old-data-local","old-data-remote-clean","all-old","all-combined"},f"summary_rows={len(within)}; folds={len(within_folds)}","threshold")
    exact_training_sizes = all(
        len(group) == int(group["training_n"].iloc[0]) + 1
        and group["training_n"].nunique() == 1
        for _, group in within_folds.groupby(["population", "candidate_id"])
    )
    add_check(rows,"V12","LOO threshold selection excludes held-out simulation",within_folds["leakage_guard"].eq("threshold and direction selected without held-out simulation").all() and exact_training_sizes,"all fold guards present and training_n=fold_n-1","threshold")
    heldout=transfer[transfer["evaluation_type"].eq("cross_population_transfer")]
    add_check(rows,"V13","Six disjoint transfer routes plus pooled descriptive reference",heldout["route_id"].nunique()==6 and transfer["route_id"].nunique()==7 and heldout["train_test_overlap_n"].eq(0).all(),f"held_out_routes={heldout['route_id'].nunique()}; all_routes={transfer['route_id'].nunique()}","transfer")
    detail_guard=transfer_details.loc[transfer_details["evaluation_type"].eq("cross_population_transfer"),"leakage_guard"].eq("disjoint train/test populations").all()
    add_check(rows,"V14","Transfer detail guards and fixed training thresholds recorded",detail_guard and transfer_details["training_selected_threshold"].notna().all(),f"detail_rows={len(transfer_details)}","transfer")
    expected_bootstrap=5*4*5+6*4*3
    add_check(rows,"V15","Full simulation-level bootstrap table complete",len(bootstrap)==expected_bootstrap and bootstrap["bootstrap_resamples"].eq(5000).all() and bootstrap["bootstrap_unit"].eq("simulation").all(),f"rows={len(bootstrap)}; expected={expected_bootstrap}; resamples={bootstrap['bootstrap_resamples'].min()}","uncertainty")
    tolerance = 1e-12
    add_check(rows,"V16","All bootstrap intervals are finite and ordered",bootstrap[["estimate","ci_low","ci_high"]].notna().all().all() and (bootstrap["ci_low"]<=bootstrap["estimate"]+tolerance).all() and (bootstrap["estimate"]<=bootstrap["ci_high"]+tolerance).all(),"all estimates inside 95% intervals within 1e-12 floating tolerance","uncertainty")
    add_check(rows,"V17","Threshold margin diagnostics cover all main candidates",len(margins)==5*4*3 and margins["nearest_below_experiment"].notna().all() and margins["nearest_above_experiment"].notna().all(),f"rows={len(margins)}","threshold")
    add_check(rows,"V18","G3 recommendation is conservative",not bool(decision.loc["G3","robust_across_predeclared_transfer_routes"]) and bool(decision.loc["G3","transferable_with_partition_shift_caveat"]) and not bool(decision.loc["G3","label_replacement_authorized"]),str(decision.loc["G3","decision"]),"decision")
    image_ok=[]
    for relative in figures["figure"]:
        path=OUT/relative
        try:
            with Image.open(path) as image:
                image.verify()
            image_ok.append(path.is_file() and path.stat().st_size>0)
        except Exception:
            image_ok.append(False)
    add_check(rows,"V19","At least 20 valid explanatory figures",len(figures)>=20 and all(image_ok) and figures["population_units_method_caveat_in_figure"].all(),f"figures={len(figures)}","artifact")
    add_check(rows,"V20","Teaching notebook has 20 sequential error-free code cells",notebook["code_cell_count"]==20 and notebook["execution_counts"]==list(range(1,21)) and not notebook["stored_errors"] and len(notebook["section_headings"])==20,f"code_cells={notebook['code_cell_count']}; headings={len(notebook['section_headings'])}; errors={len(notebook['stored_errors'])}","notebook")
    add_check(rows,"V21","Minimum artifact set is complete",all((OUT/name).is_file() for name in MINIMUM_ARTIFACTS),f"required={len(MINIMUM_ARTIFACTS)}; missing={[name for name in MINIMUM_ARTIFACTS if not (OUT/name).is_file()]}","artifact")
    add_check(rows,"V22","Source contains no modelling namespace or forbidden operation",not scope["model_namespace_imports"] and not scope["forbidden_token_hits"],f"model_imports={scope['model_namespace_imports']}; forbidden={scope['forbidden_token_hits']}","scope")
    add_check(rows,"V23","Original dirty checkout is byte-for-byte unchanged",all([original["branch_matches"],original["head_matches"],original["status_matches"],original["protected_hashes_match"]]),f"status_lines={original['status_line_count']}; protected={original['protected_file_count']}","protection")
    remote_phase55=git("ls-remote","--heads","origin",f"refs/heads/{PHASE55_BRANCH}")
    upstream=subprocess.run(["git","rev-parse","@{upstream}"],cwd=ROOT,capture_output=True,text=True).returncode==0
    add_check(rows,"V24","Phase 5.5 remains uncommitted and unpushed",git("rev-parse","HEAD")==PHASE5_SHA and not remote_phase55 and not upstream,"HEAD remains Phase 5; no upstream; remote branch absent","scope")
    return pd.DataFrame(rows)


def requirements(validation: pd.DataFrame) -> pd.DataFrame:
    groups = [
        ("R01","Exact Phase 5 parent and safe Phase 5 publication",["V01","V02"]),
        ("R02","Exact merged HF snapshot and bounded restoration diff",["V03","V04","V05"]),
        ("R03","Current target refresh and full-row retention",["V06","V07","V08","V09"]),
        ("R04","Five population composition and candidate availability",["V10"]),
        ("R05","Leakage-free within-population LOO thresholds",["V11","V12"]),
        ("R06","Disjoint cross-population transfer",["V13","V14"]),
        ("R07","5,000-resample simulation-level uncertainty",["V15","V16"]),
        ("R08","Threshold gaps and conservative G3 decision",["V17","V18"]),
        ("R09","Twenty explanatory figures",["V19"]),
        ("R10","Twenty-section executed teaching notebook",["V20"]),
        ("R11","Minimum outputs and integrity manifest",["V21"]),
        ("R12","Hard stop and protected original checkout",["V22","V23","V24"]),
    ]
    lookup=validation.set_index("check_id")["status"].to_dict()
    return pd.DataFrame([{"requirement_id":rid,"requirement":text,"status":"PASS" if all(lookup[item]=="PASS" for item in checks) else "FAIL","validation_checks":";".join(checks)} for rid,text,checks in groups])


def main() -> int:
    validation=build_validation()
    checklist=requirements(validation)
    write_csv(OUT/"validation_results.csv",validation)
    write_csv(OUT/"requirement_checklist.csv",checklist)
    summary=json.loads((OUT/"summary.json").read_text(encoding="utf-8"))
    summary["validation"] = validation["status"].value_counts().to_dict()
    summary["requirements"] = checklist["status"].value_counts().to_dict()
    summary["notebook"] = notebook_audit()
    write_json(OUT/"summary.json",summary)
    results=(OUT/"results_summary.md").read_text(encoding="utf-8")
    marker="\n## Final validation dashboard\n"
    if marker in results:
        results=results.split(marker,1)[0].rstrip()+"\n"
    results += marker + f"\n- validation: **{int((validation['status']=='PASS').sum())}/{len(validation)} PASS**\n- requirements: **{int((checklist['status']=='PASS').sum())}/{len(checklist)} PASS**\n- notebook: **20 executed code cells, zero stored errors**\n- figures: **{len(pd.read_csv(OUT/'figure_manifest.csv'))} verified images**\n"
    (OUT/"results_summary.md").write_text(results,encoding="utf-8")
    write_csv(OUT/"output_manifest.csv",output_manifest(OUT))
    manifest=manifest_audit()
    if validation["status"].ne("PASS").any() or checklist["status"].ne("PASS").any() or manifest["missing"] or manifest["mismatched"]:
        print(validation[validation["status"].ne("PASS")].to_string(index=False))
        print(checklist[checklist["status"].ne("PASS")].to_string(index=False))
        print(json.dumps(manifest,indent=2))
        return 1
    print(json.dumps({
        "validation_passed":len(validation),"validation_total":len(validation),
        "requirements_passed":len(checklist),"requirements_total":len(checklist),
        "manifest_verified":manifest["row_count"],"manifest_total":manifest["row_count"],
    },indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
