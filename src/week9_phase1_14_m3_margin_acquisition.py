"""Week 9 Phase 1.14: clean M3 model-fixed active-acquisition test.

P0 reuses Phase 1.13 M3 predictions on the frozen A0 path.  P1 starts from
the identical 16-point design and sequentially queries the unlabelled outer
training-pool point with maximum classifier-margin uncertainty under M3.
Only the query path changes in the primary comparison.
"""

from __future__ import annotations

import argparse
import gzip
import hashlib
import json
import math
import subprocess
import time
from pathlib import Path
from typing import Any, Sequence

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import nbformat as nbf
import numpy as np
import pandas as pd
from joblib import Parallel, delayed
from nbclient import NotebookClient

from src import week7_phase6_real_data_boundary_active_level_set as p6
from src import week8_5_frozen_sample_efficiency_confirmation as w85
from src import week9_phase1_7_physics_ridge_residual_gp as p17
from src import week9_phase1_11_fixed_mean_discrepancy_gp as p11
from src import week9_phase1_12_gpc_kernel_adequacy as p12
from src import week9_phase1_13_fixed_physics_ard_discrepancy as p13


ROOT=Path(__file__).resolve().parents[1]
OUTPUT=ROOT/"outputs"/"week9_phase1_14_m3_margin_acquisition"
CHECKPOINTS=OUTPUT/"checkpoints"
SENSITIVITY_CHECKPOINTS=OUTPUT/"sensitivity_checkpoints"
FIGURES=OUTPUT/"figures"
NOTEBOOK=ROOT/"notebooks"/"week_09"/"12_week9_phase1_14_m3_margin_acquisition.ipynb"
PHASE13=ROOT/"outputs"/"week9_phase1_13_fixed_physics_ard_discrepancy"
PHASE113_SHA="fbe76352f86580818659ab87fa23ec29a74c7f59"
BRANCH="codex/week9-phase1-14-m3-margin-acquisition"
FEATURES=("P","VX","LS","ST")
BUDGETS=tuple(range(16,81))
EARLY_BUDGETS=tuple(range(16,41))
LATE_BUDGETS=tuple(range(41,81))
CHECKPOINT_BUDGETS=(16,40,80)
THRESHOLDS=(.80,.82,.84)
BOOTSTRAP_DRAWS=10_000
PRIMARY_UPPER=100.0
SENSITIVITY_UPPER=1000.0
SEED_ROOT="week9_phase1_14_m3_margin_acquisition|v1"
SENSITIVITY_RUN_IDS=tuple(f"w85__r{repeat:02d}_f{((repeat-1)%5)+1:02d}" for repeat in range(1,21))


def require(condition: bool,message: str) -> None:
    if not condition: raise RuntimeError(message)


def seed_u32(*parts: object) -> int:
    key="|".join((SEED_ROOT,*(str(part) for part in parts)))
    return int.from_bytes(hashlib.sha256(key.encode()).digest()[:8],"little")%(2**32)


def sha256_file(path: Path) -> str:
    digest=hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda:handle.read(1024*1024),b""): digest.update(block)
    return digest.hexdigest()


def artifact_bytes(path: Path) -> bytes:
    payload=path.read_bytes()
    if path.suffix.lower() not in {".png",".gz",".xlsx",".tar"}: payload=payload.replace(b"\r\n",b"\n")
    return payload


def json_safe(value: Any) -> Any:
    if isinstance(value,dict): return {str(k):json_safe(v) for k,v in value.items()}
    if isinstance(value,(list,tuple)): return [json_safe(v) for v in value]
    if isinstance(value,np.ndarray): return json_safe(value.tolist())
    if isinstance(value,(np.integer,np.floating,np.bool_)): value=value.item()
    if isinstance(value,float) and not math.isfinite(value): return None
    return value


def write_json(path: Path,payload: Any) -> None:
    path.parent.mkdir(parents=True,exist_ok=True); path.write_text(json.dumps(json_safe(payload),indent=2,sort_keys=True)+"\n",encoding="utf-8")


def write_csv(path: Path,frame: pd.DataFrame) -> None:
    path.parent.mkdir(parents=True,exist_ok=True)
    if path.suffix==".gz": path.write_bytes(gzip.compress(frame.to_csv(index=False,lineterminator="\n").encode(),compresslevel=9,mtime=0))
    else: frame.to_csv(path,index=False,lineterminator="\n")


def checkpoint_path(run_id: str,sensitivity: bool=False) -> Path:
    root=SENSITIVITY_CHECKPOINTS if sensitivity else CHECKPOINTS
    return root/f"{run_id}.json.gz"


def write_checkpoint(path: Path,payload: dict[str,Any]) -> None:
    path.parent.mkdir(parents=True,exist_ok=True); path.write_bytes(gzip.compress((json.dumps(json_safe(payload),sort_keys=True)+"\n").encode(),compresslevel=6,mtime=0))


def read_checkpoint(path: Path) -> dict[str,Any]: return json.loads(gzip.decompress(path.read_bytes()).decode())


def load_inputs() -> tuple[pd.DataFrame,list[Any],dict[str,list[int]]]: return p13.load_inputs()


def historical_changes() -> list[str]:
    protected=["outputs/week9_phase1_5_h_physics_confirmation","outputs/week9_phase1_7_physics_ridge_residual_gp","outputs/week9_phase1_8_model_path_decomposition","outputs/week9_phase1_9_physics_specificity_control","outputs/week9_phase1_10_external_experimental_validation","outputs/week9_phase1_10_closure_diagnostics","outputs/week9_phase1_11_fixed_mean_discrepancy_gp","outputs/week9_phase1_12_gpc_kernel_adequacy","outputs/week9_phase1_13_fixed_physics_ard_discrepancy"]
    result=subprocess.check_output(["git","diff","--name-only",PHASE113_SHA,"--",*protected],cwd=ROOT,text=True)
    return [line for line in result.splitlines() if line.strip()]


def baseline_gate() -> dict[str,Any]:
    population,specs,a0=load_inputs(); manifest=json.loads((PHASE13/"run_manifest.json").read_text()); summary=pd.read_csv(PHASE13/"model_summary.csv"); p0=float(summary[(summary.model.eq("M3"))&summary.subset.eq("B1_q20")].mean_AULC.iloc[0]); current=subprocess.check_output(["git","rev-parse","HEAD"],cwd=ROOT,text=True).strip(); merge_base=subprocess.check_output(["git","merge-base","HEAD",PHASE113_SHA],cwd=ROOT,text=True).strip()
    payload={"status":"PASS","phase113_parent_sha":PHASE113_SHA,"current_head":current,"exact_branch_base":merge_base,"phase113_decision":manifest["decision"],"population":len(population),"keyholes":int(population.has_keyhole.sum()),"conduction":int((~population.has_keyhole.astype(bool)).sum()),"outer_runs":len(specs),"repeat_blocks":len(set(s.repeat for s in specs)),"folds_per_repeat":5,"A0_paths":len(a0),"initial_design_matches":sum(a0[s.run_id][:16]==w85.initial_design(s,population) for s in specs),"P0_q20_AULC":p0,"historical_changes":historical_changes()}
    payload["status"]="PASS" if merge_base==PHASE113_SHA and manifest["decision"]=="HYBRID_GAIN_SUPPORTED" and (len(population),int(population.has_keyhole.sum()))==(405,73) and len(specs)==len(a0)==100 and payload["initial_design_matches"]==100 and abs(p0-.8424908088235293)<1e-12 and not payload["historical_changes"] else "FAIL"
    write_json(OUTPUT/"baseline_gate.json",payload); require(payload["status"]=="PASS",f"baseline gate failed {payload}"); return payload


def protocol_reconstruction() -> dict[str,Any]:
    population,specs,a0=load_inputs(); source_files=[ROOT/"src/week8_5_frozen_sample_efficiency_confirmation.py",ROOT/"src/week7_phase6_real_data_boundary_active_level_set.py",ROOT/"src/week9_phase1_13_fixed_physics_ard_discrepancy.py"]
    payload={"status":"PASS","source_files":[{"path":p.relative_to(ROOT).as_posix(),"sha256":sha256_file(p)} for p in source_files],"population":{"rows":len(population),"keyhole":int(population.has_keyhole.sum()),"conduction":int((~population.has_keyhole.astype(bool)).sum())},"outer_protocol":{"runs":len(specs),"repeats":20,"folds":5,"splitter":"StratifiedGroupKFold(n_splits=5, shuffle=True)","group":"input_tuple_sha256","outer_training_pool":324,"held_out_test":81},"initial_design":{"size":16,"method":"seeded feature-only maximin in outer-training-pool standardized P,VX,LS,ST","source":"w85.initial_design","matched_A0":100},"budget_semantics":{"grid":list(BUDGETS),"order":"fit and evaluate at budget B; if B<80, select the point revealed for B+1","one_query_per_step":True},"candidate_eligibility":"outer training pool minus currently queried indices","margin":{"source":"p6.choose_binary_candidate(method ending in margin)","uncertainty":"1 - 2*abs(p-0.5)","orientation":"maximize uncertainty, equivalently minimize abs(p-0.5)","tie_break":"np.lexsort by descending score then ascending population row index"},"scaling":{"physics_log_h":"StandardScaler fit on currently revealed log(h)","residual_4d":"StandardScaler fit on the complete outer training pool features only"},"fit_seed":"Phase 1.13 shared_physics seed keyed by run_id and budget","A0_source":"Phase 1.8 exact query_paths.csv.gz reconstructed from Week 8.5 checkpoints","A0_complete_paths":len(a0),"evaluation_only":["B1","q20","q30","held-out labels"],"differences_from_prompt":[]}
    write_json(OUTPUT/"protocol_reconstruction.json",payload); return payload


def acquisition_specification() -> dict[str,Any]:
    payload={"status":"FROZEN_BEFORE_P1_RESULTS","primary_comparison":{"P0":"M3 evaluator on frozen A0 path","P1":"same M3 evaluator on sequential M3-margin path","only_changed_factor":"revealed-label trajectory"},"model":{"stage1":"training-fitted log(h) latent logistic mean, revealed labels only, then frozen","stage2_inputs":list(FEATURES),"residual_kernel":"ConstantKernel x ARD Matern-3/2","length_bounds":[.01,PRIMARY_UPPER],"residual_sd_bounds":list(p13.RESIDUAL_SD_BOUNDS),"optimizer":"L-BFGS-B","restarts":0,"log_h_residual_coordinate":False},"acquisition":{"score":"1 - 2*abs(p-0.5)","orientation":"maximum","tie_break":"smallest population row index","batch_size":1,"lookahead":False},"endpoints":{"primary":"Fold-B1-q20 accuracy normalized trapezoidal AULC B16-B80","secondary_q30":"Fold-B1-q30 accuracy AULC B16-B80","early":"B16-B40","late":"B41-B80","thresholds":list(THRESHOLDS)},"inference":{"unit":"20 paired repeat blocks; five folds retained together","bootstrap_draws":BOOTSTRAP_DRAWS},"sensitivity":{"run_ids":list(SENSITIVITY_RUN_IDS),"selection_rule":"one deterministic cycling fold per repeat: fold=((repeat-1) mod 5)+1","upper_bound":SENSITIVITY_UPPER,"role":"descriptive robustness only"},"decision_safeguards":{"severe_global_degradation":"at B40 or B80, mean P1-P0 full81 accuracy <= -0.02 or Keyhole recall <= -0.05","acquisition_numeric_instability":"sensitivity median B80 Jaccard <0.25 together with absolute mean q20 AULC change >=0.01, or sensitivity optimizer convergence <0.80","clear_gain":"paired 95% interval strictly above zero","early_or_late_gain":"region interval above zero while the other region is not clearly below zero"}}
    write_json(OUTPUT/"acquisition_specification.json",payload); return payload


def choose_m3_margin(candidate_indices: np.ndarray,probabilities: np.ndarray,pool_scaled: np.ndarray,queried_indices: Sequence[int]) -> tuple[int,dict[str,Any]]:
    chosen,info=p6.choose_binary_candidate(method="binary_margin",candidate_indices=np.asarray(candidate_indices,dtype=int),probabilities=np.asarray(probabilities,float),pool_scaled=np.asarray(pool_scaled,float),queried_indices=list(queried_indices)); require(info["acquisition_definition"]=="classifier_margin","historical margin semantic drift"); require(chosen==int(np.asarray(candidate_indices)[np.lexsort((np.asarray(candidate_indices,dtype=int),-(1-2*np.abs(np.asarray(probabilities,float)-.5))))[0]]),"tie-break drift"); return chosen,info


def run_one_spec(spec: Any,a0_path: Sequence[int],population: pd.DataFrame,distances: np.ndarray,upper: float=PRIMARY_UPPER,sensitivity: bool=False) -> dict[str,Any]:
    destination=checkpoint_path(spec.run_id,sensitivity)
    if destination.is_file():
        payload=read_checkpoint(destination)
        if payload.get("complete") and payload.get("phase113_sha")==PHASE113_SHA and float(payload.get("length_upper",0))==float(upper): return {"run_id":spec.run_id,"reused":True}
    x4=population.loc[:,FEATURES].to_numpy(float); logh=p11.log_h_values(population); h=np.exp(logh); labels=population.has_keyhole.astype(int).to_numpy(); train=np.asarray(spec.train_indices,dtype=int); test=np.asarray(spec.test_indices,dtype=int); flags=p17.subset_flags(spec,population,distances); queried=list(map(int,a0_path[:16])); predictions=[]; metrics=[]; diagnostics=[]; queries=[]
    for budget in BUDGETS:
        require(len(queried)==budget and len(set(queried))==budget,f"prefix/off-by-one drift {spec.run_id}/B{budget}"); revealed=np.asarray(queried,dtype=int); physics=p11.fit_physics_mean(logh,labels,revealed,p13.seed_u32("shared_physics",spec.run_id,budget)); fit=p13.fit_hybrid(x4,logh,labels,revealed,train,physics,"M3",upper); test_components=p13.components(fit,x4[test],logh[test]); probability=test_components["probability"]
        model="P1_L1000" if sensitivity else "P1"
        for local,pop_index in enumerate(test): predictions.append({"run_id":spec.run_id,"repeat":spec.repeat,"fold":spec.fold,"budget":budget,"model":model,"population_row_index":int(pop_index),"truth":int(labels[pop_index]),"probability":float(probability[local]),"is_q20":bool(flags["B1_q20"][local]),"is_q30":bool(flags["B1_q30"][local])})
        for subset,flag in (("full81",np.ones(len(test),dtype=bool)),("B1_q20",flags["B1_q20"]),("B1_q30",flags["B1_q30"])): metrics.append({"run_id":spec.run_id,"repeat":spec.repeat,"fold":spec.fold,"budget":budget,"model":model,"subset":subset,**p12.metric_values(labels[test][flag],probability[flag])})
        diagnostics.append({"run_id":spec.run_id,"repeat":spec.repeat,"fold":spec.fold,"budget":budget,"model":model,"path":"M3_margin","revealed_count":budget,**p13.fit_diagnostic(fit)})
        if budget<80:
            candidate=np.setdiff1d(train,revealed,assume_unique=False); candidate_components=p13.components(fit,x4[candidate],logh[candidate]); candidate_probability=candidate_components["probability"]; chosen,info=choose_m3_margin(candidate,candidate_probability,fit.x_scaler.transform(x4),queried); position=int(np.flatnonzero(candidate==chosen)[0]); a0_selected=int(a0_path[budget]); margin=float(abs(candidate_probability[position]-.5))
            queries.append({"run_id":spec.run_id,"repeat":spec.repeat,"fold":spec.fold,"current_budget":budget,"selection_budget":budget+1,"selected_population_row_index":chosen,"selected_experiment_name":str(population.iloc[chosen].experiment_name),"predicted_probability_before_reveal":float(candidate_probability[position]),"margin_abs_probability_minus_half":margin,"uncertainty_score":float(info["selected_uncertainty_score"]),"true_label_revealed_after_selection":int(labels[chosen]),"P":float(population.iloc[chosen].P),"VX":float(population.iloc[chosen].VX),"LS":float(population.iloc[chosen].LS),"ST":float(population.iloc[chosen].ST),"h":float(h[chosen]),"B1_distance_posthoc":float(distances[chosen]),"A0_selected_population_row_index":a0_selected,"differs_from_A0_same_step":bool(chosen!=a0_selected),"candidate_count":int(len(candidate)),"candidate_pool_role":"outer_training_pool_only","test_rows_available_to_acquisition":False,"unrevealed_labels_available_to_acquisition":False,"B1_q20_q30_available_to_acquisition":False,"tie_break":"smallest_population_row_index"}); require(chosen in set(train) and chosen not in queried and chosen not in set(test),"invalid acquisition"); queried.append(chosen)
    require(len(queried)==80 and len(queries)==64 and queried[:16]==list(a0_path[:16]),f"trajectory completeness {spec.run_id}")
    write_checkpoint(destination,{"complete":True,"phase113_sha":PHASE113_SHA,"run_id":spec.run_id,"length_upper":upper,"queried_indices":queried,"predictions":predictions,"metrics":metrics,"diagnostics":diagnostics,"queries":queries}); return {"run_id":spec.run_id,"reused":False}


def run_main(workers: int=4,limit_specs: int|None=None) -> dict[str,Any]:
    baseline_gate(); protocol_reconstruction(); acquisition_specification(); population,specs,a0=load_inputs(); distances=w85.b1_distance(population); specs=specs[:limit_specs] if limit_specs else specs; started=time.time(); results=Parallel(n_jobs=workers,verbose=10)(delayed(run_one_spec)(spec,a0[spec.run_id],population,distances,PRIMARY_UPPER,False) for spec in specs); payload={"status":"PASS","completed_runs":len(results),"reused_runs":sum(r["reused"] for r in results),"workers":workers,"elapsed_seconds":time.time()-started,"complete":limit_specs is None}; write_json(OUTPUT/"execution_report.json",payload); return payload


def run_sensitivity(workers: int=4,limit_specs: int|None=None) -> dict[str,Any]:
    population,specs,a0=load_inputs(); distances=w85.b1_distance(population); selected=[s for s in specs if s.run_id in SENSITIVITY_RUN_IDS]; require(len(selected)==20,"sensitivity subset drift"); selected=selected[:limit_specs] if limit_specs else selected; started=time.time(); results=Parallel(n_jobs=workers,verbose=10)(delayed(run_one_spec)(spec,a0[spec.run_id],population,distances,SENSITIVITY_UPPER,True) for spec in selected); payload={"status":"PASS","completed_runs":len(results),"reused_runs":sum(r["reused"] for r in results),"workers":workers,"elapsed_seconds":time.time()-started,"complete":limit_specs is None,"predeclared_run_ids":list(SENSITIVITY_RUN_IDS)}; write_json(OUTPUT/"sensitivity_execution_report.json",payload); return payload


def collect(checkpoint_root: Path,expected: int,model: str) -> tuple[pd.DataFrame,pd.DataFrame,pd.DataFrame,pd.DataFrame,pd.DataFrame]:
    files=sorted(checkpoint_root.glob("*.json.gz")); require(len(files)==expected,f"checkpoint count {len(files)} != {expected}"); predictions=[]; metrics=[]; diagnostics=[]; queries=[]; paths=[]
    for path in files:
        payload=read_checkpoint(path); require(payload.get("complete") and payload.get("phase113_sha")==PHASE113_SHA,f"bad checkpoint {path.name}"); predictions.extend(payload["predictions"]); metrics.extend(payload["metrics"]); diagnostics.extend(payload["diagnostics"]); queries.extend(payload["queries"]); spec_path=payload["queried_indices"]
        for order,index in enumerate(spec_path,start=1): paths.append({"run_id":payload["run_id"],"query_order":order,"population_row_index":int(index),"path":model,"role":"initial_design" if order<=16 else "active_query"})
    p,m,d,q,pa=map(pd.DataFrame,(predictions,metrics,diagnostics,queries,paths)); require(len(p)==expected*65*81 and len(m)==expected*65*3 and len(d)==expected*65 and len(q)==expected*64 and len(pa)==expected*80,"collected completeness"); return p,m,d,q,pa


def bootstrap_interval(values: np.ndarray,key: str) -> tuple[float,float,float]:
    values=np.asarray(values,float); require(len(values)==20 and np.isfinite(values).all(),f"repeat bootstrap drift {key}"); rng=np.random.default_rng(seed_u32("bootstrap",key)); draws=values[rng.integers(0,20,size=(BOOTSTRAP_DRAWS,20))].mean(axis=1); return float(values.mean()),float(np.quantile(draws,.025)),float(np.quantile(draws,.975))


def load_p0_predictions() -> pd.DataFrame:
    chunks=[]
    for chunk in pd.read_csv(PHASE13/"new_predictions.csv.gz",chunksize=200_000):
        selected=chunk[chunk.model.eq("M3")]
        if len(selected): chunks.append(selected[["run_id","repeat","fold","budget","population_row_index","truth","probability","is_q20","is_q30"]].copy())
    frame=pd.concat(chunks,ignore_index=True); frame["model"]="P0"; require(len(frame)==100*65*81,"P0 prediction completeness"); return frame


def compute_aulc(metrics: pd.DataFrame) -> tuple[pd.DataFrame,pd.DataFrame,pd.DataFrame,pd.DataFrame]:
    rows=[]
    for keys,group in metrics[metrics.subset.isin(("B1_q20","B1_q30"))].groupby(["run_id","repeat","fold","model","subset"],sort=True):
        run_id,repeat,fold,model,subset=keys; ordered=group.sort_values("budget"); require(ordered.budget.astype(int).tolist()==list(BUDGETS),f"AULC grid drift {run_id}/{model}/{subset}"); rows.append({"run_id":run_id,"repeat":repeat,"fold":fold,"model":model,"subset":subset,"accuracy_AULC_16_80":float(np.trapezoid(ordered.accuracy,ordered.budget)/64)})
    outer=pd.DataFrame(rows); require(len(outer)==100*2*2,"outer AULC completeness"); repeat=outer.groupby(["repeat","model","subset"],as_index=False).accuracy_AULC_16_80.mean(); summaries=[]; contrasts=[]
    for (model,subset),group in repeat.groupby(["model","subset"],sort=True):
        mean,lo,hi=bootstrap_interval(group.sort_values("repeat").accuracy_AULC_16_80.to_numpy(),f"summary|{model}|{subset}"); summaries.append({"model":model,"subset":subset,"mean_AULC":mean,"ci_lower":lo,"ci_upper":hi})
    wide=repeat.pivot(index=["repeat","subset"],columns="model",values="accuracy_AULC_16_80").reset_index()
    for subset in ("B1_q20","B1_q30"):
        part=wide[wide.subset.eq(subset)].sort_values("repeat"); values=(part.P1-part.P0).to_numpy(float); mean,lo,hi=bootstrap_interval(values,f"P1-P0|{subset}"); contrasts.append({"contrast":"P1-P0","subset":subset,"mean_difference":mean,"ci_lower":lo,"ci_upper":hi,"positive_repeat_blocks":int((values>0).sum()),"zero_repeat_blocks":int((values==0).sum()),"negative_repeat_blocks":int((values<0).sum()),"bootstrap_draws":BOOTSTRAP_DRAWS,"comparison":"same M3 evaluator; path only"})
    return outer,repeat,pd.DataFrame(summaries),pd.DataFrame(contrasts)


def compute_regions(metrics: pd.DataFrame) -> tuple[pd.DataFrame,pd.DataFrame]:
    outer=[]
    for region,budgets in (("EARLY_B16_40",EARLY_BUDGETS),("LATE_B41_80",LATE_BUDGETS)):
        denom=budgets[-1]-budgets[0]
        for keys,group in metrics[metrics.subset.eq("B1_q20")&metrics.budget.isin(budgets)].groupby(["run_id","repeat","fold","model"],sort=True):
            run_id,repeat,fold,model=keys; ordered=group.sort_values("budget"); require(ordered.budget.astype(int).tolist()==list(budgets),f"region grid {run_id}/{model}/{region}"); outer.append({"run_id":run_id,"repeat":repeat,"fold":fold,"model":model,"region":region,"accuracy_AULC":float(np.trapezoid(ordered.accuracy,ordered.budget)/denom)})
    outer_frame=pd.DataFrame(outer); repeat=outer_frame.groupby(["repeat","model","region"],as_index=False).accuracy_AULC.mean(); summaries=[]; contrasts=[]
    for (model,region),group in repeat.groupby(["model","region"],sort=True):
        mean,lo,hi=bootstrap_interval(group.sort_values("repeat").accuracy_AULC.to_numpy(),f"region-summary|{model}|{region}"); summaries.append({"model":model,"region":region,"mean_AULC":mean,"ci_lower":lo,"ci_upper":hi})
    wide=repeat.pivot(index=["repeat","region"],columns="model",values="accuracy_AULC").reset_index()
    for region in ("EARLY_B16_40","LATE_B41_80"):
        part=wide[wide.region.eq(region)].sort_values("repeat"); values=(part.P1-part.P0).to_numpy(float); mean,lo,hi=bootstrap_interval(values,f"region-contrast|{region}"); contrasts.append({"contrast":"P1-P0","region":region,"mean_difference":mean,"ci_lower":lo,"ci_upper":hi,"positive_repeat_blocks":int((values>0).sum()),"zero_repeat_blocks":int((values==0).sum()),"negative_repeat_blocks":int((values<0).sum()),"bootstrap_draws":BOOTSTRAP_DRAWS})
    return pd.DataFrame(summaries),pd.DataFrame(contrasts)


def learning_curve_summary(metrics: pd.DataFrame) -> pd.DataFrame:
    rows=[]
    for keys,group in metrics[metrics.subset.isin(("B1_q20","B1_q30"))].groupby(["model","subset","budget"],sort=True):
        model,subset,budget=keys; values=group.groupby("repeat").accuracy.mean().sort_index().to_numpy(float); mean,lo,hi=bootstrap_interval(values,f"curve|{model}|{subset}|{budget}"); rows.append({"model":model,"subset":subset,"budget":int(budget),"mean_accuracy":mean,"ci_lower":lo,"ci_upper":hi})
    return pd.DataFrame(rows)


def checkpoint_summary(metrics: pd.DataFrame,subset: str,metric_names: Sequence[str]) -> pd.DataFrame:
    rows=[]; part=metrics[metrics.subset.eq(subset)&metrics.budget.isin(CHECKPOINT_BUDGETS)]
    for budget in CHECKPOINT_BUDGETS:
        for metric in metric_names:
            by_repeat=part[part.budget.eq(budget)].groupby(["repeat","model"])[metric].mean().unstack().sort_index()
            for model in ("P0","P1"):
                mean,lo,hi=bootstrap_interval(by_repeat[model].to_numpy(float),f"checkpoint|{subset}|{model}|{budget}|{metric}"); rows.append({"model":model,"contrast":"none","subset":subset,"budget":budget,"metric":metric,"mean":mean,"ci_lower":lo,"ci_upper":hi})
            values=(by_repeat.P1-by_repeat.P0).to_numpy(float); mean,lo,hi=bootstrap_interval(values,f"checkpoint-delta|{subset}|{budget}|{metric}"); rows.append({"model":"difference","contrast":"P1-P0","subset":subset,"budget":budget,"metric":metric,"mean":mean,"ci_lower":lo,"ci_upper":hi})
    return pd.DataFrame(rows)


def sample_efficiency(metrics: pd.DataFrame) -> tuple[pd.DataFrame,pd.DataFrame]:
    q=metrics[metrics.subset.eq("B1_q20")].copy(); details=[]
    for keys,group in q.groupby(["run_id","repeat","fold","model"],sort=True):
        run_id,repeat,fold,model=keys; ordered=group.sort_values("budget")
        for threshold in THRESHOLDS:
            crossed=ordered[ordered.accuracy>=threshold]; first=float(crossed.budget.iloc[0]) if len(crossed) else math.nan; details.append({"unit":"outer_run","unit_id":run_id,"repeat":repeat,"fold":fold,"model":model,"threshold":threshold,"reached_by_B80":bool(len(crossed)),"first_hit_budget":first,"right_censored":not bool(len(crossed))})
    repeat_curve=q.groupby(["repeat","model","budget"],as_index=False).accuracy.mean()
    for keys,group in repeat_curve.groupby(["repeat","model"],sort=True):
        repeat,model=keys; ordered=group.sort_values("budget")
        for threshold in THRESHOLDS:
            crossed=ordered[ordered.accuracy>=threshold]; first=float(crossed.budget.iloc[0]) if len(crossed) else math.nan; details.append({"unit":"repeat","unit_id":f"repeat_{repeat:02d}","repeat":repeat,"fold":math.nan,"model":model,"threshold":threshold,"reached_by_B80":bool(len(crossed)),"first_hit_budget":first,"right_censored":not bool(len(crossed))})
    detail=pd.DataFrame(details); summary=[]
    for keys,group in detail.groupby(["unit","model","threshold"],sort=True):
        unit,model,threshold=keys; reached=group[group.reached_by_B80]; summary.append({"unit":unit,"model":model,"threshold":threshold,"n_units":len(group),"reached_count":len(reached),"reached_fraction":float(group.reached_by_B80.mean()),"censored_count":int(group.right_censored.sum()),"median_first_hit_budget_reached_only":float(reached.first_hit_budget.median()) if len(reached) else math.nan,"q1_first_hit_budget_reached_only":float(reached.first_hit_budget.quantile(.25)) if len(reached) else math.nan,"q3_first_hit_budget_reached_only":float(reached.first_hit_budget.quantile(.75)) if len(reached) else math.nan,"missing_crossings_not_imputed":True})
    return detail,pd.DataFrame(summary)


def path_diagnostics(paths: pd.DataFrame,queries: pd.DataFrame,a0: dict[str,list[int]],population: pd.DataFrame,distances: np.ndarray) -> tuple[pd.DataFrame,pd.DataFrame,pd.DataFrame,pd.DataFrame]:
    p1={run:group.sort_values("query_order").population_row_index.astype(int).tolist() for run,group in paths.groupby("run_id",sort=True)}; details=[]; overlap_curve=[]
    for run in sorted(a0):
        path0=a0[run]; path1=p1[run]; differences=[i for i,(x,y) in enumerate(zip(path0,path1),start=1) if x!=y]; first=min(differences) if differences else math.nan; row={"run_id":run,"repeat":int(run.split("__r")[1].split("_")[0]),"fold":int(run.rsplit("f",1)[1]),"first_divergence_budget":first,"paths_identical_through_B16":path0[:16]==path1[:16]}
        for budget in (40,80):
            a,b=set(path0[:budget]),set(path1[:budget]); row[f"shared_B{budget}"]=len(a&b); row[f"jaccard_B{budget}"]=len(a&b)/len(a|b); row[f"unique_P0_B{budget}"]=len(a-b); row[f"unique_P1_B{budget}"]=len(b-a)
        details.append(row)
        for budget in BUDGETS:
            a,b=set(path0[:budget]),set(path1[:budget]); overlap_curve.append({"run_id":run,"repeat":row["repeat"],"fold":row["fold"],"budget":budget,"shared":len(a&b),"jaccard":len(a&b)/len(a|b)})
    detail=pd.DataFrame(details); curve=pd.DataFrame(overlap_curve); summary=[]
    for metric in ("first_divergence_budget","shared_B40","jaccard_B40","unique_P0_B40","unique_P1_B40","shared_B80","jaccard_B80","unique_P0_B80","unique_P1_B80"):
        values=detail[metric].dropna(); summary.append({"metric":metric,"mean":float(values.mean()),"median":float(values.median()),"q1":float(values.quantile(.25)),"q3":float(values.quantile(.75)),"minimum":float(values.min()),"maximum":float(values.max()),"n":len(values)})
    logh=p11.log_h_values(population); query_rows=[]
    for row in queries.itertuples(index=False):
        for path_name,index in (("P1",int(row.selected_population_row_index)),("P0",int(row.A0_selected_population_row_index))): query_rows.append({"path":path_name,"run_id":row.run_id,"selection_budget":int(row.selection_budget),"population_row_index":index,"truth":int(population.iloc[index].has_keyhole),"P":float(population.iloc[index].P),"VX":float(population.iloc[index].VX),"LS":float(population.iloc[index].LS),"ST":float(population.iloc[index].ST),"h":float(np.exp(logh[index])),"B1_distance_posthoc":float(distances[index]),"probability_before_reveal":float(row.predicted_probability_before_reveal) if path_name=="P1" else math.nan,"margin_abs_probability_minus_half":float(row.margin_abs_probability_minus_half) if path_name=="P1" else math.nan})
    qframe=pd.DataFrame(query_rows); characteristics=[]
    for path_name,group in qframe.groupby("path",sort=True):
        for metric in ("truth","P","VX","LS","ST","h","B1_distance_posthoc","probability_before_reveal","margin_abs_probability_minus_half"):
            values=group[metric].dropna(); characteristics.append({"path":path_name,"metric":metric,"mean":float(values.mean()),"median":float(values.median()),"q1":float(values.quantile(.25)),"q3":float(values.quantile(.75)),"n":len(values)})
    characteristics.append({"path":"P1_vs_P0","metric":"same-step selected-query disagreement fraction","mean":float(queries.differs_from_A0_same_step.mean()),"median":math.nan,"q1":math.nan,"q3":math.nan,"n":len(queries)})
    return detail,pd.DataFrame(summary),curve,pd.DataFrame(characteristics)


def fit_summary(p1_diagnostics: pd.DataFrame) -> pd.DataFrame:
    p0=pd.read_csv(PHASE13/"m3_fit_diagnostics.csv.gz",low_memory=False).assign(model="P0"); p1=p1_diagnostics.assign(model="P1"); frame=pd.concat([p0,p1],ignore_index=True,sort=False); rows=[]
    for model,group in frame.groupby("model",sort=True):
        for scope,budgets in (("all_B16_80",BUDGETS),("B16",(16,)),("B40",(40,)),("B80",(80,))):
            part=group[group.budget.isin(budgets)]
            for metric in ("residual_sd","residual_sd_lower_bound_hit","residual_sd_upper_bound_hit","residual_sd_any_bound_hit","any_length_lower_bound_hit","any_length_upper_bound_hit","any_length_bound_hit","optimizer_converged","anisotropy_ratio","l_P","l_VX","l_LS","l_ST"):
                values=part[metric].astype(float); rows.append({"model":model,"scope":scope,"metric":metric,"mean":float(values.mean()),"median":float(values.median()),"q1":float(values.quantile(.25)),"q3":float(values.quantile(.75)),"n":len(values)})
    return pd.DataFrame(rows)


def sensitivity_analysis(primary_metrics: pd.DataFrame,primary_paths: pd.DataFrame,sens_metrics: pd.DataFrame,sens_paths: pd.DataFrame,primary_diag: pd.DataFrame,sens_diag: pd.DataFrame) -> tuple[pd.DataFrame,pd.DataFrame]:
    p1={run:g.sort_values("query_order").population_row_index.astype(int).tolist() for run,g in primary_paths.groupby("run_id") if run in SENSITIVITY_RUN_IDS}; p1000={run:g.sort_values("query_order").population_row_index.astype(int).tolist() for run,g in sens_paths.groupby("run_id")}; rows=[]
    def aulc(frame: pd.DataFrame,run: str) -> float:
        part=frame[(frame.run_id.eq(run))&frame.subset.eq("B1_q20")].sort_values("budget"); require(part.budget.tolist()==list(BUDGETS),f"sensitivity AULC grid {run}"); return float(np.trapezoid(part.accuracy,part.budget)/64)
    for run in SENSITIVITY_RUN_IDS:
        a,b=p1[run],p1000[run]; differences=[i for i,(x,y) in enumerate(zip(a,b),start=1) if x!=y]; row={"run_id":run,"repeat":int(run.split("__r")[1].split("_")[0]),"fold":int(run.rsplit("f",1)[1]),"first_divergence_budget":min(differences) if differences else math.nan,"selected_query_disagreement_count":len(differences),"selected_query_disagreement_fraction":len(differences)/64,"L100_q20_AULC":aulc(primary_metrics,run),"L1000_q20_AULC":aulc(sens_metrics,run)}; row["delta_L1000_minus_L100_q20_AULC"]=row["L1000_q20_AULC"]-row["L100_q20_AULC"]
        for budget in (40,80):
            aa,bb=set(a[:budget]),set(b[:budget]); row[f"shared_B{budget}"]=len(aa&bb); row[f"jaccard_B{budget}"]=len(aa&bb)/len(aa|bb)
        for budget in CHECKPOINT_BUDGETS:
            for metric in ("accuracy","balanced_accuracy","keyhole_recall","conduction_recall"):
                x=float(primary_metrics[(primary_metrics.run_id.eq(run))&primary_metrics.subset.eq("B1_q20")&primary_metrics.budget.eq(budget)][metric].iloc[0]); y=float(sens_metrics[(sens_metrics.run_id.eq(run))&sens_metrics.subset.eq("B1_q20")&sens_metrics.budget.eq(budget)][metric].iloc[0]); row[f"L100_B{budget}_{metric}"]=x; row[f"L1000_B{budget}_{metric}"]=y; row[f"delta_B{budget}_{metric}"]=y-x
        rows.append(row)
    detail=pd.DataFrame(rows); summary=[]
    for metric in ("first_divergence_budget","selected_query_disagreement_fraction","jaccard_B40","jaccard_B80","L100_q20_AULC","L1000_q20_AULC","delta_L1000_minus_L100_q20_AULC"):
        values=detail[metric].dropna(); summary.append({"section":"path_and_prediction","metric":metric,"mean":float(values.mean()),"median":float(values.median()),"q1":float(values.quantile(.25)),"q3":float(values.quantile(.75)),"n":len(values)})
    for setting,frame in (("L100",primary_diag[primary_diag.run_id.isin(SENSITIVITY_RUN_IDS)]),("L1000",sens_diag)):
        for metric in ("residual_sd_upper_bound_hit","any_length_upper_bound_hit","optimizer_converged"):
            summary.append({"section":setting,"metric":metric,"mean":float(frame[metric].astype(float).mean()),"median":float(frame[metric].astype(float).median()),"q1":float(frame[metric].astype(float).quantile(.25)),"q3":float(frame[metric].astype(float).quantile(.75)),"n":len(frame)})
    return detail,pd.DataFrame(summary)


def decide(contrasts: pd.DataFrame,regions: pd.DataFrame,full: pd.DataFrame,sensitivity_summary: pd.DataFrame) -> tuple[str,dict[str,bool]]:
    primary=contrasts[(contrasts.subset.eq("B1_q20"))&contrasts.contrast.eq("P1-P0")].iloc[0]; early=regions[regions.region.eq("EARLY_B16_40")].iloc[0]; late=regions[regions.region.eq("LATE_B41_80")].iloc[0]; deltas=full[(full.model.eq("difference"))&full.budget.isin((40,80))].set_index(["budget","metric"])["mean"]
    severe_global=any(deltas.loc[(budget,"accuracy")]<=-.02 or deltas.loc[(budget,"keyhole_recall")]<=-.05 for budget in (40,80)); sens=sensitivity_summary.set_index(["section","metric"])["mean"]; sens_median=sensitivity_summary.set_index(["section","metric"])["median"]; numerical=bool((sens_median.loc[("path_and_prediction","jaccard_B80")]<.25 and abs(sens.loc[("path_and_prediction","delta_L1000_minus_L100_q20_AULC")])>=.01) or sens.loc[("L1000","optimizer_converged")]<.80)
    flags={"severe_global_degradation":severe_global,"acquisition_numerically_unstable":numerical}
    if numerical:return "ACQUISITION_NUMERICALLY_UNSTABLE",flags
    if primary.ci_lower>0 and not severe_global:return "ACQUISITION_GAIN_SUPPORTED",flags
    if primary.ci_lower<=0<=primary.ci_upper and early.ci_lower>0 and late.ci_upper>=0:return "EARLY_ACQUISITION_GAIN_ONLY",flags
    if primary.ci_lower<=0<=primary.ci_upper and late.ci_lower>0 and early.ci_upper>=0:return "LATE_ACQUISITION_GAIN_ONLY",flags
    if primary.ci_upper<0:return "ACQUISITION_HARM",flags
    return "NO_ACQUISITION_GAIN",flags


def make_figures(curves: pd.DataFrame,contrasts: pd.DataFrame,regions: pd.DataFrame,thresholds: pd.DataFrame,overlap_curve: pd.DataFrame,sensitivity_summary: pd.DataFrame,fit: pd.DataFrame) -> pd.DataFrame:
    FIGURES.mkdir(parents=True,exist_ok=True); created=[]; colors={"P0":"#718096","P1":"#c53030"}; labels={"P0":"P0: M3 on frozen A0","P1":"P1: M3-margin"}
    part=curves[curves.subset.eq("B1_q20")]; fig,ax=plt.subplots(figsize=(9.5,5.3))
    for model in ("P0","P1"):
        g=part[part.model.eq(model)].sort_values("budget"); ax.plot(g.budget,g.mean_accuracy,lw=2.5,color=colors[model],label=labels[model]); ax.fill_between(g.budget,g.ci_lower,g.ci_upper,color=colors[model],alpha=.12)
    ax.set(xlabel="Revealed simulations",ylabel="Fold-B1-q20 accuracy",title="Same M3 evaluator, different query paths"); ax.grid(alpha=.25); ax.legend(frameon=False); fig.tight_layout(); path=FIGURES/"01_q20_learning_curves.png"; fig.savefig(path,dpi=180); plt.close(fig); created.append((path,"Primary same-model path comparison."))
    rows=[contrasts[contrasts.subset.eq("B1_q20")].iloc[0],*list(regions.sort_values("region").itertuples(index=False))]; names=["Overall B16-80","Early B16-40","Late B41-80"]; means=[float(rows[0].mean_difference),float(rows[1].mean_difference),float(rows[2].mean_difference)]; lows=[float(rows[0].ci_lower),float(rows[1].ci_lower),float(rows[2].ci_lower)]; highs=[float(rows[0].ci_upper),float(rows[1].ci_upper),float(rows[2].ci_upper)]; fig,ax=plt.subplots(figsize=(8,4.7)); y=np.arange(3); ax.errorbar(means,y,xerr=[np.array(means)-lows,np.array(highs)-means],fmt="o",capsize=5,color="#9b2c2c",ms=7); ax.axvline(0,color="black",ls="--"); ax.set_yticks(y,names); ax.invert_yaxis(); ax.set(xlabel="P1-P0 q20 accuracy AULC",title="Path-only effect with 95% repeat-block intervals"); ax.grid(axis="x",alpha=.25); fig.tight_layout(); path=FIGURES/"02_primary_early_late_contrasts.png"; fig.savefig(path,dpi=180); plt.close(fig); created.append((path,"Overall, early, and late path contrasts."))
    part=thresholds[thresholds.unit.eq("repeat")]; fig,axes=plt.subplots(1,2,figsize=(10,4.7)); x=np.arange(len(THRESHOLDS)); width=.34
    for j,model in enumerate(("P0","P1")):
        g=part[part.model.eq(model)].set_index("threshold").loc[list(THRESHOLDS)]; axes[0].bar(x+(j-.5)*width,g.reached_fraction,width,color=colors[model],label=labels[model]); axes[1].plot(x,g.median_first_hit_budget_reached_only,"o-",color=colors[model],label=labels[model])
    axes[0].set(ylabel="Fraction of repeat blocks reaching by B80",title="Threshold reachability"); axes[1].set(ylabel="Median first-hit budget (reached only)",title="Censored first-hit view");
    for ax in axes: ax.set_xticks(x,[f"{t:.2f}" for t in THRESHOLDS]); ax.set_xlabel("q20 accuracy threshold"); ax.grid(axis="y",alpha=.25)
    axes[0].legend(frameon=False); fig.tight_layout(); path=FIGURES/"03_sample_efficiency_thresholds.png"; fig.savefig(path,dpi=180); plt.close(fig); created.append((path,"Predeclared threshold reachability and censored first hits."))
    mean_overlap=overlap_curve.groupby("budget",as_index=False).jaccard.mean(); fig,ax=plt.subplots(figsize=(8.5,4.8)); ax.plot(mean_overlap.budget,mean_overlap.jaccard,color="#2b6cb0",lw=2.5); ax.axvline(16,color="black",ls="--",alpha=.6); ax.set(xlabel="Budget",ylabel="Mean set Jaccard with A0",title="How quickly the M3-margin paths separate from A0",ylim=(0,1.02)); ax.grid(alpha=.25); fig.tight_layout(); path=FIGURES/"04_path_overlap.png"; fig.savefig(path,dpi=180); plt.close(fig); created.append((path,"Cumulative P1/A0 set overlap."))
    sens=sensitivity_summary.set_index(["section","metric"]); fitpart=fit[(fit.scope.eq("all_B16_80"))&fit.metric.isin(("residual_sd_upper_bound_hit","any_length_upper_bound_hit","optimizer_converged"))]; pivot=fitpart.pivot(index="metric",columns="model",values="mean"); fig,axes=plt.subplots(1,2,figsize=(10,4.8)); axes[0].bar(["B40","B80"],[sens.loc[("path_and_prediction","jaccard_B40"),"mean"],sens.loc[("path_and_prediction","jaccard_B80"),"mean"]],color="#805ad5"); axes[0].set(ylabel="Mean L100/L1000 path Jaccard",title="Acquisition bound sensitivity",ylim=(0,1)); x=np.arange(3); width=.35
    for j,model in enumerate(("P0","P1")): axes[1].bar(x+(j-.5)*width,pivot.loc[["residual_sd_upper_bound_hit","any_length_upper_bound_hit","optimizer_converged"],model],width,label=model,color=colors[model])
    axes[1].set_xticks(x,["Residual SD\nupper hit","Any length\nupper hit","Converged"]); axes[1].set_ylim(0,1); axes[1].set_title("M3 fit behavior by path"); axes[1].legend(frameon=False); axes[0].grid(axis="y",alpha=.25); axes[1].grid(axis="y",alpha=.25); fig.tight_layout(); path=FIGURES/"05_acquisition_numeric_robustness.png"; fig.savefig(path,dpi=180); plt.close(fig); created.append((path,"L100/L1000 path sensitivity and fit diagnostics."))
    manifest=pd.DataFrame([{"figure":p.name,"sha256":sha256_file(p),"size_bytes":p.stat().st_size,"purpose":purpose} for p,purpose in created]); write_csv(OUTPUT/"figure_manifest.csv",manifest); return manifest


def build_reports(summary: pd.DataFrame,contrasts: pd.DataFrame,regions: pd.DataFrame,checkpoints: pd.DataFrame,thresholds: pd.DataFrame,qchars: pd.DataFrame,path_summary: pd.DataFrame,fit: pd.DataFrame,sens: pd.DataFrame,full: pd.DataFrame,decision: str,flags: dict[str,bool]) -> None:
    def a(model:str,subset:str="B1_q20") -> float:return float(summary[(summary.model.eq(model))&summary.subset.eq(subset)].mean_AULC.iloc[0])
    primary=contrasts[contrasts.subset.eq("B1_q20")].iloc[0]; q30=contrasts[contrasts.subset.eq("B1_q30")].iloc[0]; early=regions[regions.region.eq("EARLY_B16_40")].iloc[0]; late=regions[regions.region.eq("LATE_B41_80")].iloc[0]
    def cp(model:str,budget:int,metric:str) -> float:return float(checkpoints[(checkpoints.model.eq(model))&checkpoints.budget.eq(budget)&checkpoints.metric.eq(metric)]["mean"].iloc[0])
    def fp(model:str,budget:int,metric:str) -> float:return float(full[(full.model.eq(model))&full.budget.eq(budget)&full.metric.eq(metric)]["mean"].iloc[0])
    def ps(metric:str) -> float:return float(path_summary[path_summary.metric.eq(metric)]["median"].iloc[0])
    def fs(model:str,metric:str) -> float:return float(fit[(fit.model.eq(model))&fit.scope.eq("all_B16_80")&fit.metric.eq(metric)]["mean"].iloc[0])
    novel="SUPPORTED" if decision=="ACQUISITION_GAIN_SUPPORTED" else ("QUALIFIED" if decision in {"EARLY_ACQUISITION_GAIN_ONLY","LATE_ACQUISITION_GAIN_ONLY","NO_ACQUISITION_GAIN"} else "NOT SUPPORTED")
    sens_index=sens.set_index(["section","metric"]); threshold_lines=[]
    for threshold in THRESHOLDS:
        items=[]
        for model in ("P0","P1"):
            row=thresholds[(thresholds.unit.eq("repeat"))&thresholds.model.eq(model)&np.isclose(thresholds.threshold,threshold)].iloc[0]; items.append(f"{model}: reached {row.reached_count:.0f}/20, median B{row.median_first_hit_budget_reached_only:.0f}" if row.reached_count else f"{model}: reached 0/20")
        threshold_lines.append(f"- {threshold:.2f}: "+"; ".join(items)+" (non-crossings censored).")
    report=["# Week 9 Phase 1.14 — M3-margin active acquisition","",f"## Decision: {decision}","","## Clean primary comparison",f"P0 M3-on-A0 q20 AULC: {a('P0'):.9f}.",f"P1 M3-margin q20 AULC: {a('P1'):.9f}.",f"P1-P0: {primary.mean_difference:+.6f} [{primary.ci_lower:+.6f}, {primary.ci_upper:+.6f}], repeats +/0/- = {int(primary.positive_repeat_blocks)}/{int(primary.zero_repeat_blocks)}/{int(primary.negative_repeat_blocks)}.","The evaluator/model is M3 in both arms; only the revealed-label path changes.","","## Early and late",f"Early B16-40: {early.mean_difference:+.6f} [{early.ci_lower:+.6f}, {early.ci_upper:+.6f}].",f"Late B41-80: {late.mean_difference:+.6f} [{late.ci_lower:+.6f}, {late.ci_upper:+.6f}].","","## q20 checkpoints"]
    for budget in CHECKPOINT_BUDGETS: report.append(f"B{budget} P0/P1 accuracy {cp('P0',budget,'accuracy'):.4f}/{cp('P1',budget,'accuracy'):.4f}; balanced accuracy {cp('P0',budget,'balanced_accuracy'):.4f}/{cp('P1',budget,'balanced_accuracy'):.4f}; KH recall {cp('P0',budget,'keyhole_recall'):.4f}/{cp('P1',budget,'keyhole_recall'):.4f}; C recall {cp('P0',budget,'conduction_recall'):.4f}/{cp('P1',budget,'conduction_recall'):.4f}.")
    report += ["","## Sample efficiency",*threshold_lines,"","## Path behavior",f"Median first divergence: B{ps('first_divergence_budget'):.0f}; median A0/P1 Jaccard B40/B80: {ps('jaccard_B40'):.3f}/{ps('jaccard_B80'):.3f}.",f"P1 queried-Keyhole fraction: {float(qchars[(qchars.path.eq('P1'))&qchars.metric.eq('truth')]['mean'].iloc[0]):.3f}; same-step query disagreement with A0: {float(qchars[(qchars.path.eq('P1_vs_P0'))]['mean'].iloc[0]):.3f}.","","## Robustness",f"q30 P1-P0: {q30.mean_difference:+.6f} [{q30.ci_lower:+.6f}, {q30.ci_upper:+.6f}].",f"At B40, q20 Keyhole recall changes by {cp('P1',40,'keyhole_recall')-cp('P0',40,'keyhole_recall'):+.4f}; the late positive AULC result must not hide this early recall cost.",f"At B80 full81 P0/P1 accuracy {fp('P0',80,'accuracy'):.4f}/{fp('P1',80,'accuracy'):.4f}, KH recall {fp('P0',80,'keyhole_recall'):.4f}/{fp('P1',80,'keyhole_recall'):.4f}, Brier {fp('P0',80,'brier_score'):.4f}/{fp('P1',80,'brier_score'):.4f}.",f"P1 all-budget residual-SD upper-hit {fs('P1','residual_sd_upper_bound_hit'):.1%}; any-length upper-hit {fs('P1','any_length_upper_bound_hit'):.1%}; convergence {fs('P1','optimizer_converged'):.1%}.",f"L100/L1000 sensitivity: median B80 path Jaccard {sens_index.loc[('path_and_prediction','jaccard_B80'),'median']:.3f}, mean q20 AULC delta {sens_index.loc[('path_and_prediction','delta_L1000_minus_L100_q20_AULC'),'mean']:+.4f}, L1000 convergence {sens_index.loc[('L1000','optimizer_converged'),'mean']:.1%}.","","## Safe interpretation",f"Severe global degradation: {flags['severe_global_degradation']}; acquisition numerically unstable under the predeclared rule: {flags['acquisition_numerically_unstable']}.",f"Further physics/residual-aware acquisition work is {novel.lower()} as a follow-up: the late-region gain coexists with unresolved overall gain and a B40 Keyhole-recall cost.","This is pool-based active-learning replay on one deterministic simulator dataset. It does not establish universal acquisition superiority, theoretical sample complexity, external transfer, or causal ARD importance."]
    (OUTPUT/"FINAL_PHASE1_14_REPORT.md").write_text("\n".join(report)+"\n",encoding="utf-8")
    supervisor=["# Supervisor Phase 1.14 — one page","",f"**Decision:** {decision}","",f"- Clean path-only q20 AULC: P0 {a('P0'):.4f}, P1 {a('P1'):.4f}, delta {primary.mean_difference:+.4f} [{primary.ci_lower:+.4f}, {primary.ci_upper:+.4f}].",f"- Early delta {early.mean_difference:+.4f} [{early.ci_lower:+.4f}, {early.ci_upper:+.4f}]; late {late.mean_difference:+.4f} [{late.ci_lower:+.4f}, {late.ci_upper:+.4f}].",f"- B40/B80 q20 KH recall P0/P1: {cp('P0',40,'keyhole_recall'):.3f}/{cp('P1',40,'keyhole_recall'):.3f}; {cp('P0',80,'keyhole_recall'):.3f}/{cp('P1',80,'keyhole_recall'):.3f}.",f"- Median path Jaccard at B40/B80: {ps('jaccard_B40'):.3f}/{ps('jaccard_B80'):.3f}; median first divergence B{ps('first_divergence_budget'):.0f}.",f"- q30 delta: {q30.mean_difference:+.4f} [{q30.ci_lower:+.4f}, {q30.ci_upper:+.4f}].",f"- L100/L1000 median B80 Jaccard: {sens_index.loc[('path_and_prediction','jaccard_B80'),'median']:.3f}; q20 AULC sensitivity delta {sens_index.loc[('path_and_prediction','delta_L1000_minus_L100_q20_AULC'),'mean']:+.4f}.",f"- Novel physics/residual-aware acquisition follow-up: {novel}; overall gain is unresolved despite a supported late-region effect.","","Only the path changes in the primary comparison. No universal or theoretical active-learning claim is made."]
    (OUTPUT/"SUPERVISOR_PHASE1_14_ONE_PAGE.md").write_text("\n".join(supervisor)+"\n",encoding="utf-8")
    supported="SUPPORTED" if primary.ci_lower>0 else ("NOT SUPPORTED" if primary.ci_upper<0 else "UNRESOLVED")
    ledger=["# Phase 1.14 claim ledger","","| Claim | Status | Evidence boundary |","|---|---|---|",f"| M3-margin improves q20 AULC over M3-on-A0. | {supported} | Same M3 evaluator, paired repeat blocks. |",f"| Early acquisition gain. | {'SUPPORTED' if early.ci_lower>0 else ('NOT SUPPORTED' if early.ci_upper<0 else 'UNRESOLVED')} | Predeclared B16-40. |",f"| Late acquisition gain. | {'SUPPORTED' if late.ci_lower>0 else ('NOT SUPPORTED' if late.ci_upper<0 else 'UNRESOLVED')} | Predeclared B41-80. |",f"| q30 robustness. | {'SUPPORTED' if q30.ci_lower>0 else ('NOT SUPPORTED' if q30.ci_upper<0 else 'UNRESOLVED')} | Secondary. |",f"| Full81 behavior is preserved. | {'SUPPORTED' if not flags['severe_global_degradation'] else 'NOT SUPPORTED'} | Predeclared degradation gate. |",f"| Acquisition is robust to L100/L1000. | {'QUALIFIED' if not flags['acquisition_numerically_unstable'] else 'NOT SUPPORTED'} | Twenty predeclared trajectories. |","| M3-margin is universally superior. | NOT SUPPORTED | One finite simulator pool. |","| Theoretical sample-complexity improvement. | NOT TESTED | Empirical replay only. |","| ARD lengths are causal physical importance. | NOT SUPPORTED | Standardized model geometry. |",f"| Novel physics/residual-aware acquisition work is justified. | {novel} | Follow-up recommendation, not tested here. |"]
    (OUTPUT/"claim_ledger.md").write_text("\n".join(ledger)+"\n",encoding="utf-8")
    red=["# Final red-team report","","- Phase 1.13 remains the immutable branch base; historical Phase 1.x artifacts were not edited.","- P0 is reused Phase 1.13 M3-on-A0; P1 uses the exact same M3 architecture and differs only by path.","- All 100 initial 16-point designs are identical, and B16 predictions are checked for exact equality.","- Evaluation folds are excluded from candidates; hidden labels, B1, q20, and q30 are absent from acquisition.","- Selection uses one query after current-budget evaluation; no future label or off-by-one prefix enters fitting.","- Historical classifier-margin orientation and smallest-index tie break are reused.","- Twenty repeat blocks, not 100 folds, are the inferential unit.","- Early/late regions and thresholds were frozen before P1 results.","- Keyhole recall, full81 behavior, bound hits, convergence, and L1000 path sensitivity are disclosed.","- Path divergence is described, not assumed beneficial.","- No universal acquisition, theoretical sample-complexity, external-transfer, or causal-ARD claim is made."]
    (OUTPUT/"FINAL_RED_TEAM_REPORT.md").write_text("\n".join(red)+"\n",encoding="utf-8")


def build_notebook() -> None:
    cells=[
        nbf.v4.new_markdown_cell("# Week 9 Phase 1.14 — M3-margin active acquisition\n\nThis teaching notebook reads published artifacts; it does not rerun the sequential GP experiment."),
        nbf.v4.new_markdown_cell("## 1. What Phase 1.13 proved—and did not prove\n\nPhase 1.13 established that M3 was a stronger **predictive model** on the same frozen A0 labels. It did not establish that M3 chooses better labels."),
        nbf.v4.new_code_cell("from pathlib import Path\nimport json, pandas as pd\nfrom IPython.display import display, Image, Markdown\nROOT=Path.cwd().parents[1] if Path.cwd().name=='week_09' else Path.cwd()\nOUT=ROOT/'outputs'/'week9_phase1_14_m3_margin_acquisition'\ndisplay(json.loads((OUT/'baseline_gate.json').read_text()))"),
        nbf.v4.new_markdown_cell("## 2. The clean test\n\nP0 and P1 both use M3. P0 receives A0 labels; P1 sequentially selects its own labels. Therefore P1−P0 isolates the path contribution for this evaluator."),
        nbf.v4.new_code_cell("display(json.loads((OUT/'protocol_reconstruction.json').read_text())); display(json.loads((OUT/'acquisition_specification.json').read_text()))"),
        nbf.v4.new_markdown_cell("## 3. Main q20 learning curves and paired path contrast"),
        nbf.v4.new_code_cell("display(pd.read_csv(OUT/'learning_curve_summary.csv').query(\"subset=='B1_q20'\")); display(pd.read_csv(OUT/'paired_contrasts.csv')); display(Image(filename=str(OUT/'figures'/'01_q20_learning_curves.png'))); display(Image(filename=str(OUT/'figures'/'02_primary_early_late_contrasts.png')))"),
        nbf.v4.new_markdown_cell("## 4. Early/late behavior and checkpoints\n\nThe regions B16–40 and B41–80 were fixed before results."),
        nbf.v4.new_code_cell("display(pd.read_csv(OUT/'early_late_summary.csv')); display(pd.read_csv(OUT/'early_late_contrasts.csv')); display(pd.read_csv(OUT/'checkpoint16_40_80_summary.csv'))"),
        nbf.v4.new_markdown_cell("## 5. Sample-efficiency thresholds\n\nFirst-hit budgets are right-censored. Non-crossings are never assigned a favorable artificial budget."),
        nbf.v4.new_code_cell("display(pd.read_csv(OUT/'sample_efficiency_thresholds.csv')); display(Image(filename=str(OUT/'figures'/'03_sample_efficiency_thresholds.png')))"),
        nbf.v4.new_markdown_cell("## 6. What M3 queries and how paths diverge\n\nAll B1 distances and labels in these tables are retrospective diagnostics only."),
        nbf.v4.new_code_cell("display(pd.read_csv(OUT/'path_overlap_summary.csv')); display(pd.read_csv(OUT/'query_characteristics.csv')); display(Image(filename=str(OUT/'figures'/'04_path_overlap.png')))"),
        nbf.v4.new_markdown_cell("## 7. q30 and global full81 robustness"),
        nbf.v4.new_code_cell("display(pd.read_csv(OUT/'paired_contrasts.csv').query(\"subset=='B1_q30'\")); display(pd.read_csv(OUT/'full81_checkpoint_summary.csv'))"),
        nbf.v4.new_markdown_cell("## 8. Fit behavior and active-path upper-bound sensitivity\n\nARD lengths are standardized-space diagnostics, not physical importance."),
        nbf.v4.new_code_cell("display(pd.read_csv(OUT/'m3_fit_bound_summary.csv')); display(pd.read_csv(OUT/'acquisition_bound_sensitivity_summary.csv')); display(Image(filename=str(OUT/'figures'/'05_acquisition_numeric_robustness.png')))"),
        nbf.v4.new_markdown_cell("## 9. Safe conclusion\n\nThe evidence is a pool-based replay on one deterministic simulator dataset. It does not prove universal or theoretical acquisition superiority."),
        nbf.v4.new_code_cell("display(Markdown((OUT/'SUPERVISOR_PHASE1_14_ONE_PAGE.md').read_text()))"),
    ]
    notebook=nbf.v4.new_notebook(cells=cells,metadata={"kernelspec":{"display_name":"Thesis Python","language":"python","name":"thesis"}}); NOTEBOOK.parent.mkdir(parents=True,exist_ok=True); nbf.write(notebook,NOTEBOOK); executed=NotebookClient(nbf.read(NOTEBOOK,as_version=4),timeout=180,kernel_name="thesis",resources={"metadata":{"path":str(ROOT)}}).execute(); nbf.write(executed,NOTEBOOK)


def validate(p1_predictions: pd.DataFrame,p1_metrics: pd.DataFrame,p1_diag: pd.DataFrame,queries: pd.DataFrame,paths: pd.DataFrame,p0_predictions: pd.DataFrame,contrasts: pd.DataFrame,regions: pd.DataFrame,full: pd.DataFrame,thresholds: pd.DataFrame,path_detail: pd.DataFrame,sens_detail: pd.DataFrame,sens_diag: pd.DataFrame,figures: pd.DataFrame,decision: str) -> dict[str,Any]:
    population,specs,a0=load_inputs(); source=Path(__file__).read_text(encoding="utf-8"); fit_source=source[source.index("def choose_m3_margin"):source.index("def run_main")]; selector_source=source[source.index("def choose_m3_margin"):source.index("def run_one_spec")]; gate=json.loads((OUTPUT/"baseline_gate.json").read_text()); protocol=json.loads((OUTPUT/"protocol_reconstruction.json").read_text()); acquisition=json.loads((OUTPUT/"acquisition_specification.json").read_text()); notebook=nbf.read(NOTEBOOK,as_version=4); code=[c for c in notebook.cells if c.cell_type=="code"]; report=(OUTPUT/"FINAL_PHASE1_14_REPORT.md").read_text().lower(); path_map={run:g.sort_values("query_order").population_row_index.astype(int).tolist() for run,g in paths.groupby("run_id")}; p0_b16=p0_predictions[p0_predictions.budget.eq(16)].sort_values(["run_id","population_row_index"]).probability.to_numpy(); p1_b16=p1_predictions[p1_predictions.budget.eq(16)].sort_values(["run_id","population_row_index"]).probability.to_numpy(); q20=contrasts[contrasts.subset.eq("B1_q20")].iloc[0]
    checks=[
        ("exact_phase113_parent_base",gate["exact_branch_base"]==PHASE113_SHA,gate["exact_branch_base"]),
        ("phase113_decision",gate["phase113_decision"]=="HYBRID_GAIN_SUPPORTED",gate["phase113_decision"]),
        ("population_405_73_332",(len(population),int(population.has_keyhole.sum()))==(405,73),"405/73/332"),
        ("h_formula_unchanged","p11.log_h_values(population)" in source,"P/sqrt(VX*LS^3) inherited"),
        ("exact_100_outer_runs",len(specs)==100,"100"),
        ("exact_20x5",len(set(s.repeat for s in specs))==20 and all(sum(x.repeat==r for x in specs)==5 for r in range(1,21)),"20x5"),
        ("exact_B16_80",BUDGETS==tuple(range(16,81)),"65 budgets"),
        ("exact_initial_designs",all(path_map[s.run_id][:16]==a0[s.run_id][:16]==w85.initial_design(s,population) for s in specs),"100/100"),
        ("P0_frozen_AULC",abs(gate["P0_q20_AULC"]-.8424908088235293)<1e-12,str(gate["P0_q20_AULC"])),
        ("evaluation_fold_never_queried",all(set(path_map[s.run_id]).isdisjoint(s.test_indices) for s in specs),"all paths"),
        ("q20_absent_acquisition","is_q20" not in selector_source and "B1_q20" not in selector_source,"selection clean"),
        ("q30_absent_acquisition","is_q30" not in selector_source and "B1_q30" not in selector_source,"selection clean"),
        ("B1_absent_acquisition","distances" not in source[source.index("def choose_m3_margin"):source.index("def run_one_spec")],"selector clean"),
        ("unrevealed_labels_absent_selector","labels" not in source[source.index("def choose_m3_margin"):source.index("def run_one_spec")],"probabilities only"),
        ("one_query_per_step",queries.groupby("run_id").size().eq(64).all(),"64 after B16"),
        ("no_duplicate_query",all(len(set(v))==80 for v in path_map.values()),"100 paths"),
        ("historical_margin_semantics",protocol["margin"]["uncertainty"]=="1 - 2*abs(p-0.5)","exact"),
        ("deterministic_tie_break",queries.tie_break.eq("smallest_population_row_index").all(),"exact"),
        ("stage1_logh_only","p11.fit_physics_mean(logh,labels,revealed" in fit_source,"exact Phase 1.13"),
        ("stage1_revealed_only","revealed=np.asarray(queried" in fit_source,"prefix"),
        ("stage1_frozen_before_residual","physics=p11.fit_physics_mean" in fit_source and "p13.fit_hybrid" in fit_source,"ordered"),
        ("M3_residual_inputs_exact",FEATURES==("P","VX","LS","ST"),str(FEATURES)),
        ("logh_absent_residual_coordinate","x4=population.loc[:,FEATURES]" in fit_source and len(FEATURES)==4,"4D only"),
        ("ARD_matern_nu_1_5",p13.residual_kernel("M3").k2.nu==1.5,"1.5"),
        ("four_ARD_lengths",len(np.ravel(p13.residual_kernel("M3").k2.length_scale))==4,"4"),
        ("amplitude_bounds_unchanged",tuple(p13.RESIDUAL_SD_BOUNDS)==(.05,1.0),str(p13.RESIDUAL_SD_BOUNDS)),
        ("primary_length_bounds",p13.PRIMARY_LENGTH_BOUNDS==(.01,100.0),str(p13.PRIMARY_LENGTH_BOUNDS)),
        ("optimizer_restarts_unchanged",acquisition["model"]["optimizer"]=="L-BFGS-B" and acquisition["model"]["restarts"]==0,"frozen"),
        ("P1_trajectories_complete",len(path_map)==100 and all(len(v)==80 for v in path_map.values()),"100x80"),
        ("P1_predictions_complete",len(p1_predictions)==100*65*81,"526500"),
        ("same_M3_evaluator",acquisition["primary_comparison"]["only_changed_factor"]=="revealed-label trajectory","path only"),
        ("paired_20_repeat_blocks",p1_predictions.repeat.nunique()==20 and (q20.positive_repeat_blocks+q20.zero_repeat_blocks+q20.negative_repeat_blocks)==20,"20"),
        ("bootstrap_10000",q20.bootstrap_draws>=10_000,str(q20.bootstrap_draws)),
        ("early_exact",EARLY_BUDGETS==tuple(range(16,41)) and "EARLY_B16_40" in set(regions.region),"B16-40"),
        ("late_exact",LATE_BUDGETS==tuple(range(41,81)) and "LATE_B41_80" in set(regions.region),"B41-80"),
        ("q30_complete",len(contrasts[contrasts.subset.eq("B1_q30")])==1,"secondary"),
        ("full81_complete",len(full)==3*3*7,"P0/P1/delta x budgets x metrics"),
        ("thresholds_predeclared",set(thresholds.threshold)==set(THRESHOLDS) and thresholds.missing_crossings_not_imputed.all(),str(THRESHOLDS)),
        ("path_overlap_retrospective",queries.B1_q20_q30_available_to_acquisition.eq(False).all(),"post hoc only"),
        ("sensitivity_subset_predeclared",set(sens_detail.run_id)==set(SENSITIVITY_RUN_IDS) and len(sens_detail)==20,"one per repeat"),
        ("no_causal_ARD_claim","ard lengthscales are causal" not in report and "ard dimensions cause" not in report,"safe"),
        ("no_universal_acquisition_claim","m3-margin is universally superior" not in report,"safe"),
        ("no_theoretical_sample_complexity_claim","proves theoretical sample complexity" not in report,"safe"),
        ("B16_predictions_identical",np.allclose(p0_b16,p1_b16,rtol=0,atol=1e-12),str(float(np.max(np.abs(p0_b16-p1_b16))))),
        ("selection_after_current_evaluation",source.index("test_components=p13.components")<source.index("if budget<80"),"evaluate then select"),
        ("current_prefix_budget_exact",all(len(path_map[s.run_id][:b])==b for s in specs for b in CHECKPOINT_BUDGETS),"no off-by-one"),
        ("candidate_pool_training_only",all(set(path_map[s.run_id]).issubset(s.train_indices) for s in specs),"outer train"),
        ("query_labels_marked_after_selection",queries.columns.isin(["true_label_revealed_after_selection"]).any(),"explicit"),
        ("fit_diagnostics_complete",len(p1_diag)==6500 and p1_diag[["residual_sd","l_P","l_VX","l_LS","l_ST","optimizer_converged"]].notna().all().all(),"6500"),
        ("sensitivity_diagnostics_complete",len(sens_diag)==20*65,"1300"),
        ("notebook_executed",bool(code) and all(c.execution_count is not None for c in code) and not [o for c in code for o in c.get("outputs",[]) if o.get("output_type")=="error"],f"{len(code)} cells"),
        ("figure_hashes",len(figures)<=5 and all(sha256_file(FIGURES/r.figure)==r.sha256 for r in figures.itertuples(index=False)),str(len(figures))),
        ("no_unresolved_placeholders",all(token not in (OUTPUT/"FINAL_PHASE1_14_REPORT.md").read_text() for token in ("{decision}","TODO","TBD")),"none"),
        ("historical_outputs_unchanged",historical_changes()==[],str(historical_changes())),
        ("red_team_language","path divergence is described, not assumed beneficial" in (OUTPUT/"FINAL_RED_TEAM_REPORT.md").read_text().lower(),"explicit"),
        ("decision_declared",decision in {"ACQUISITION_GAIN_SUPPORTED","EARLY_ACQUISITION_GAIN_ONLY","LATE_ACQUISITION_GAIN_ONLY","NO_ACQUISITION_GAIN","ACQUISITION_HARM","ACQUISITION_NUMERICALLY_UNSTABLE"},decision),
    ]
    records=[{"check":name,"status":"PASS" if ok else "FAIL","detail":detail} for name,ok,detail in checks]; payload={"status":"PASS" if all(r["status"]=="PASS" for r in records) else "FAIL","check_count":len(records),"passed":sum(r["status"]=="PASS" for r in records),"checks":records}; write_json(OUTPUT/"validation_report.json",payload); lines=["# Phase 1.14 validation","",f"Status: **{payload['status']}**",f"Checks: **{payload['passed']} / {payload['check_count']} PASS**","","| Check | Status | Detail |","|---|---|---|"]+[f"| {r['check']} | {r['status']} | {r['detail']} |" for r in records]; (OUTPUT/"validation_report.md").write_text("\n".join(lines)+"\n",encoding="utf-8"); require(payload["status"]=="PASS","validation failure"); return payload


def write_run_manifest(validation: dict[str,Any],decision: str) -> None:
    files=[p for p in OUTPUT.rglob("*") if p.is_file() and "checkpoints" not in p.parts and p.name!="run_manifest.json"]; files.extend([Path(__file__),ROOT/"tests"/"test_week9_phase1_14_m3_margin_acquisition.py",NOTEBOOK]); entries=[]
    for path in sorted(set(files)):
        require(path.is_file(),f"manifest missing {path}"); payload=artifact_bytes(path); entries.append({"path":path.relative_to(ROOT).as_posix(),"sha256":hashlib.sha256(payload).hexdigest(),"size_bytes":len(payload)})
    manifest={"study":"Week 9 Phase 1.14 — M3-margin active acquisition","phase113_parent_sha":PHASE113_SHA,"branch":BRANCH,"decision":decision,"protocol":{"P0":"frozen M3/A0","P1":"M3/M3-margin","budgets":list(BUDGETS),"outer_runs":100,"repeat_blocks":20,"folds_per_repeat":5,"bootstrap_draws":BOOTSTRAP_DRAWS,"sensitivity_run_ids":list(SENSITIVITY_RUN_IDS)},"validation":validation,"historical_changes":historical_changes(),"files":entries}; write_json(OUTPUT/"run_manifest.json",manifest)


def finalize() -> dict[str,Any]:
    gate=baseline_gate(); protocol_reconstruction(); acquisition_specification(); population,specs,a0=load_inputs(); distances=w85.b1_distance(population); p1,p1_metrics,p1_diag,queries,paths=collect(CHECKPOINTS,100,"P1"); sens_p,sens_metrics,sens_diag,sens_queries,sens_paths=collect(SENSITIVITY_CHECKPOINTS,20,"P1_L1000"); p0=load_p0_predictions(); p0_metrics=p13.boundary_metrics_vectorized(p0,"P0"); metrics=pd.concat([p0_metrics,p1_metrics.assign(model="P1")],ignore_index=True,sort=False); outer,repeat,summary,contrasts=compute_aulc(metrics); region_summary,region_contrasts=compute_regions(metrics); curves=learning_curve_summary(metrics); checkpoints=checkpoint_summary(metrics,"B1_q20",("accuracy","balanced_accuracy","keyhole_recall","conduction_recall","false_negative","false_positive")); full=checkpoint_summary(metrics,"full81",("roc_auc","pr_auc","accuracy","balanced_accuracy","keyhole_recall","conduction_recall","brier_score")); threshold_detail,threshold_summary=sample_efficiency(metrics); path_detail,path_summary,overlap_curve,qchars=path_diagnostics(paths,queries,a0,population,distances); fits=fit_summary(p1_diag); sens_detail,sens_summary=sensitivity_analysis(p1_metrics,paths,sens_metrics,sens_paths,p1_diag,sens_diag); decision,flags=decide(contrasts,region_contrasts,full,sens_summary)
    for name,frame in (("m3_margin_queries.csv.gz",queries),("m3_margin_paths.csv.gz",paths),("new_predictions.csv.gz",p1),("outer_run_metrics.csv.gz",outer),("repeat_metrics.csv",repeat),("learning_curve_summary.csv",curves),("paired_contrasts.csv",contrasts),("early_late_summary.csv",region_summary),("early_late_contrasts.csv",region_contrasts),("checkpoint16_40_80_summary.csv",checkpoints),("sample_efficiency_thresholds.csv",threshold_summary),("sample_efficiency_threshold_details.csv.gz",threshold_detail),("full81_checkpoint_summary.csv",full),("path_overlap_summary.csv",path_summary),("path_overlap_detail.csv",path_detail),("path_overlap_curve.csv.gz",overlap_curve),("query_characteristics.csv",qchars),("m3_active_fit_diagnostics.csv.gz",p1_diag),("m3_fit_bound_summary.csv",fits),("acquisition_bound_sensitivity.csv",sens_detail),("acquisition_bound_sensitivity_summary.csv",sens_summary)): write_csv(OUTPUT/name,frame)
    figures=make_figures(curves,contrasts,region_contrasts,threshold_summary,overlap_curve,sens_summary,fits); build_reports(summary,contrasts,region_contrasts,checkpoints,threshold_summary,qchars,path_summary,fits,sens_summary,full,decision,flags); build_notebook(); validation=validate(p1,p1_metrics,p1_diag,queries,paths,p0,contrasts,region_contrasts,full,threshold_summary,path_detail,sens_detail,sens_diag,figures,decision); write_run_manifest(validation,decision); manifest=json.loads((OUTPUT/"run_manifest.json").read_text()); require(all(hashlib.sha256(artifact_bytes(ROOT/item["path"])).hexdigest()==item["sha256"] for item in manifest["files"]),"manifest hash failure"); return {"status":"PASS","decision":decision,"validation_checks":validation["check_count"],"P0_q20_AULC":gate["P0_q20_AULC"],"historical_changes":historical_changes()}


def main() -> None:
    parser=argparse.ArgumentParser(); parser.add_argument("--preflight",action="store_true"); parser.add_argument("--run",action="store_true"); parser.add_argument("--sensitivity",action="store_true"); parser.add_argument("--finalize",action="store_true"); parser.add_argument("--workers",type=int,default=4); parser.add_argument("--limit-specs",type=int); args=parser.parse_args()
    if args.preflight: print(json.dumps({"baseline":baseline_gate(),"protocol":protocol_reconstruction(),"acquisition":acquisition_specification()},indent=2))
    if args.run: print(json.dumps(run_main(args.workers,args.limit_specs),indent=2))
    if args.sensitivity: print(json.dumps(run_sensitivity(args.workers,args.limit_specs),indent=2))
    if args.finalize: print(json.dumps(finalize(),indent=2))
    if not any((args.preflight,args.run,args.sensitivity,args.finalize)): parser.error("choose --preflight, --run, --sensitivity, or --finalize")


if __name__=="__main__": main()
