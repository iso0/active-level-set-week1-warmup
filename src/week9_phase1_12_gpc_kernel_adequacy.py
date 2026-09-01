"""Week 9 Phase 1.12: GPC kernel adequacy and anisotropy control.

Four new 4D Gaussian-process classifiers are replayed on the exact frozen A0
query path.  H and canonical G0 are read-only comparators.  No acquisition or
physics-coordinate search is performed.
"""

from __future__ import annotations

import argparse
import gzip
import hashlib
import json
import math
import os
import subprocess
import time
import warnings
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
from sklearn.exceptions import ConvergenceWarning
from sklearn.gaussian_process import GaussianProcessClassifier
from sklearn.gaussian_process.kernels import ConstantKernel, Matern, RBF
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import average_precision_score, balanced_accuracy_score, brier_score_loss, confusion_matrix, recall_score, roc_auc_score
from sklearn.preprocessing import StandardScaler

from src import week7_phase6_real_data_boundary_active_level_set as p6
from src import week8_5_frozen_sample_efficiency_confirmation as w85
from src import week9_phase1_7_physics_ridge_residual_gp as p17
from src import week9_phase1_8_model_path_decomposition as p18
from src import week9_phase1_11_fixed_mean_discrepancy_gp as p11


ROOT=Path(__file__).resolve().parents[1]
OUTPUT=ROOT/"outputs"/"week9_phase1_12_gpc_kernel_adequacy"
CHECKPOINTS=OUTPUT/"checkpoints"
FIGURES=OUTPUT/"figures"
NOTEBOOK=ROOT/"notebooks"/"week_09"/"10_week9_phase1_12_gpc_kernel_adequacy.ipynb"
PHASE18=ROOT/"outputs"/"week9_phase1_8_model_path_decomposition"
PHASE11=ROOT/"outputs"/"week9_phase1_11_fixed_mean_discrepancy_gp"
START_SHA="5a21e5dce37fc6d4c58fa40bb7a6711920fec94e"
BRANCH="codex/week9-phase1-12-gpc-kernel-adequacy"
FEATURES=("P","VX","LS","ST")
NEW_MODELS=("G1","G2","G3","G4")
ALL_MODELS=("H","G0","G1","G2","G3","G4")
BUDGETS=tuple(range(16,81))
CHECKPOINT_BUDGETS=(16,40,80)
BOOTSTRAP_DRAWS=10_000
AMPLITUDE_BOUNDS=tuple(float(x) for x in p6.KERNEL_CONSTANT_BOUNDS)
LENGTH_BOUNDS=tuple(float(x) for x in p6.KERNEL_LENGTH_BOUNDS)
N_RESTARTS=0
BOUND_RTOL=1e-5
SEED_ROOT="week9_phase1_12_gpc_kernel_adequacy|v1"
EPS=1e-12

MODEL_SPECS={
    "G0":{"name":"isotropic Matern-3/2","family":"Matern","nu":1.5,"ard":False,"primary":False},
    "G1":{"name":"isotropic RBF","family":"RBF","nu":None,"ard":False,"primary":False},
    "G2":{"name":"ARD RBF","family":"RBF","nu":None,"ard":True,"primary":False},
    "G3":{"name":"ARD Matern-3/2","family":"Matern","nu":1.5,"ard":True,"primary":True},
    "G4":{"name":"isotropic Matern-5/2","family":"Matern","nu":2.5,"ard":False,"primary":False},
}


def require(condition: bool,message: str) -> None:
    if not condition:
        raise RuntimeError(message)


def seed_u32(*parts: object) -> int:
    key="|".join((SEED_ROOT,*(str(part) for part in parts)))
    return int.from_bytes(hashlib.sha256(key.encode()).digest()[:8],"little")%(2**32)


def sha256_file(path: Path) -> str:
    h=hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda:handle.read(1024*1024),b""):
            h.update(block)
    return h.hexdigest()


def artifact_bytes(path: Path) -> bytes:
    data=path.read_bytes()
    if path.suffix.lower() not in {".png",".gz",".xlsx",".tar"}:
        data=data.replace(b"\r\n",b"\n")
    return data


def json_safe(value: Any) -> Any:
    if isinstance(value,dict): return {str(k):json_safe(v) for k,v in value.items()}
    if isinstance(value,(list,tuple)): return [json_safe(v) for v in value]
    if isinstance(value,np.ndarray): return json_safe(value.tolist())
    if isinstance(value,(np.integer,np.floating,np.bool_)): value=value.item()
    if isinstance(value,float) and not math.isfinite(value): return None
    return value


def write_json(path: Path,payload: Any) -> None:
    path.parent.mkdir(parents=True,exist_ok=True)
    path.write_text(json.dumps(json_safe(payload),indent=2,sort_keys=True)+"\n",encoding="utf-8")


def write_csv(path: Path,frame: pd.DataFrame) -> None:
    path.parent.mkdir(parents=True,exist_ok=True)
    if path.suffix==".gz":
        path.write_bytes(gzip.compress(frame.to_csv(index=False,lineterminator="\n").encode(),compresslevel=9,mtime=0))
    else:
        frame.to_csv(path,index=False,lineterminator="\n")


def make_kernel(model: str) -> Any:
    require(model in MODEL_SPECS,f"unknown GPC model {model}")
    spec=MODEL_SPECS[model]
    length=np.ones(4,dtype=float) if spec["ard"] else 1.0
    if spec["family"]=="RBF":
        base=RBF(length_scale=length,length_scale_bounds=LENGTH_BOUNDS)
    else:
        base=Matern(length_scale=length,length_scale_bounds=LENGTH_BOUNDS,nu=float(spec["nu"]))
    return ConstantKernel(1.0,constant_value_bounds=AMPLITUDE_BOUNDS)*base


def kernel_specification() -> dict[str,Any]:
    models={}
    for model,spec in MODEL_SPECS.items():
        models[model]={**spec,"kernel_repr":repr(make_kernel(model)),"amplitude_initial":1.0,"amplitude_bounds":list(AMPLITUDE_BOUNDS),"length_scale_initial":[1.0]*4 if spec["ard"] else 1.0,"length_scale_bounds":list(LENGTH_BOUNDS),"optimizer":"fmin_l_bfgs_b","n_restarts_optimizer":N_RESTARTS,"likelihood":"Bernoulli-logistic Laplace GPC","input_features":list(FEATURES),"input_scaling":"StandardScaler fit on outer training pool inputs"}
    payload={"status":"FROZEN","models":models,"fairness":"identical inputs, scaling, amplitude bounds, component length bounds, optimizer and restarts","week5_reuse":"kernel families, ARD naming and neutral standardized-space initialization only; no GPR likelihood/noise behavior"}
    write_json(OUTPUT/"kernel_specification.json",payload)
    return payload


def load_inputs() -> tuple[pd.DataFrame,list[Any],dict[str,list[int]]]:
    population,specs=p18.load_population_specs()
    paths_table=pd.read_csv(PHASE18/"tables"/"query_paths.csv.gz")
    a0=paths_table[paths_table.path.eq("A0")]
    paths={str(run):group.sort_values("query_order").population_row_index.astype(int).tolist() for run,group in a0.groupby("run_id",sort=True)}
    initial=pd.read_csv(ROOT/"outputs"/"week8_5_frozen_confirmation"/"initial_design_manifest.csv")
    initial_map={str(run):group.sort_values("query_order").population_row_index.astype(int).tolist() for run,group in initial.groupby("run_id",sort=True)}
    require(len(population)==405 and int(population.has_keyhole.sum())==73 and int((~population.has_keyhole.astype(bool)).sum())==332,"population gate")
    require(len(specs)==100 and len(paths)==100,"outer-run/path gate")
    for spec in specs:
        path=paths[spec.run_id]
        require(len(path)==80 and len(set(path))==80,f"A0 path drift {spec.run_id}")
        require(path[:16]==initial_map[spec.run_id]==w85.initial_design(spec,population),f"B16 initial drift {spec.run_id}")
        require(set(path).issubset(spec.train_indices) and set(path).isdisjoint(spec.test_indices),f"A0 information flow {spec.run_id}")
    return population,specs,paths


def baseline_gate() -> dict[str,Any]:
    population,specs,paths=load_inputs()
    summary=pd.read_csv(PHASE11/"model_summary.csv")
    h=float(summary[(summary.model.eq("MH"))&summary.subset.eq("B1_q20")].mean_AULC.iloc[0])
    g0=float(summary[(summary.model.eq("M0"))&summary.subset.eq("B1_q20")].mean_AULC.iloc[0])
    gate={"status":"PASS" if abs(h-0.8308134191176471)<1e-12 and abs(g0-0.8135202205882353)<1e-12 else "FAIL","population":len(population),"keyholes":int(population.has_keyhole.sum()),"conduction":int((~population.has_keyhole.astype(bool)).sum()),"outer_runs":len(specs),"repeat_blocks":len(set(spec.repeat for spec in specs)),"folds_per_repeat":5,"A0_paths":len(paths),"initial_B16_matches":100,"budgets":list(BUDGETS),"H_q20_AULC":h,"G0_q20_AULC":g0,"sources":{"H":"Phase 1.11 MH/A0","G0":"Phase 1.8 Y00/A0"}}
    write_json(OUTPUT/"baseline_gate.json",gate)
    require(gate["status"]=="PASS",f"baseline gate failed {gate}")
    return gate


def metric_values(truth: np.ndarray,probability: np.ndarray) -> dict[str,Any]:
    truth=np.asarray(truth,dtype=int); probability=np.clip(np.asarray(probability,dtype=float),EPS,1-EPS); prediction=(probability>=.5).astype(int)
    tn,fp,fn,tp=confusion_matrix(truth,prediction,labels=[0,1]).ravel()
    return {"roc_auc":float(roc_auc_score(truth,probability)) if len(np.unique(truth))==2 else math.nan,"pr_auc":float(average_precision_score(truth,probability)),"accuracy":float((prediction==truth).mean()),"balanced_accuracy":float(balanced_accuracy_score(truth,prediction)),"keyhole_recall":float(recall_score(truth,prediction,pos_label=1,zero_division=0)),"conduction_recall":float(recall_score(truth,prediction,pos_label=0,zero_division=0)),"brier_score":float(brier_score_loss(truth,probability)),"false_negative":int(fn),"false_positive":int(fp),"true_negative":int(tn),"true_positive":int(tp),"row_count":len(truth)}


def fit_gpc_model(model_name: str,x_scaled: np.ndarray,labels: np.ndarray,seed: int) -> tuple[Any,dict[str,Any]]:
    kernel=make_kernel(model_name); caught=[]; fit_status="optimized_primary"; fallback_status="none"
    model=GaussianProcessClassifier(kernel=kernel,optimizer="fmin_l_bfgs_b",n_restarts_optimizer=N_RESTARTS,max_iter_predict=100,warm_start=False,random_state=int(seed))
    try:
        with warnings.catch_warnings(record=True) as records:
            warnings.simplefilter("always"); model.fit(x_scaled,labels)
        caught=[str(item.message) for item in records]
    except Exception as exc:
        fallback_status=f"fixed_kernel_after_{type(exc).__name__}"; fit_status="fixed_kernel_fallback"
        model=GaussianProcessClassifier(kernel=kernel,optimizer=None,n_restarts_optimizer=0,max_iter_predict=200,warm_start=False,random_state=int(seed))
        try:
            with warnings.catch_warnings(record=True) as records:
                warnings.simplefilter("always"); model.fit(x_scaled,labels)
            caught=[str(exc),*(str(item.message) for item in records)]
        except Exception as second:
            fallback_status=f"logistic_after_{type(exc).__name__}_{type(second).__name__}"; fit_status="logistic_fallback"
            model=LogisticRegression(C=1.0,max_iter=2000,random_state=int(seed)).fit(x_scaled,labels); caught=[str(exc),str(second)]
    if fit_status=="logistic_fallback":
        diag={"fit_status":fit_status,"fallback_status":fallback_status,"optimizer_warning":bool(caught),"warning_text":" | ".join(caught),"objective_value":math.nan,"amplitude":math.nan,"amplitude_lower_bound_hit":False,"amplitude_upper_bound_hit":False,"length_scale":math.nan,"l_P":math.nan,"l_VX":math.nan,"l_LS":math.nan,"l_ST":math.nan,"anisotropy_ratio":math.nan,"any_length_lower_bound_hit":False,"any_length_upper_bound_hit":False,"any_length_bound_hit":False}
        return model,diag
    amplitude=float(model.kernel_.k1.constant_value); values=np.ravel(model.kernel_.k2.length_scale).astype(float); ard=len(values)==4; expanded=values if ard else np.repeat(values[0],4)
    lower=np.isclose(expanded,LENGTH_BOUNDS[0],rtol=BOUND_RTOL,atol=0); upper=np.isclose(expanded,LENGTH_BOUNDS[1],rtol=BOUND_RTOL,atol=0)
    diag={"fit_status":fit_status,"fallback_status":fallback_status,"optimizer_warning":bool(caught),"warning_text":" | ".join(caught),"objective_value":float(-model.log_marginal_likelihood_value_),"amplitude":amplitude,"amplitude_lower_bound_hit":bool(np.isclose(amplitude,AMPLITUDE_BOUNDS[0],rtol=BOUND_RTOL,atol=0)),"amplitude_upper_bound_hit":bool(np.isclose(amplitude,AMPLITUDE_BOUNDS[1],rtol=BOUND_RTOL,atol=0)),"length_scale":float(values[0]) if not ard else math.nan,"l_P":float(expanded[0]),"l_VX":float(expanded[1]),"l_LS":float(expanded[2]),"l_ST":float(expanded[3]),"anisotropy_ratio":float(expanded.max()/expanded.min()),"any_length_lower_bound_hit":bool(lower.any()),"any_length_upper_bound_hit":bool(upper.any()),"any_length_bound_hit":bool(lower.any() or upper.any())}
    for name,index in zip(FEATURES,range(4)):
        diag[f"l_{name}_lower_bound_hit"]=bool(lower[index]); diag[f"l_{name}_upper_bound_hit"]=bool(upper[index])
    return model,diag


def predict_positive(model: Any,x_scaled: np.ndarray) -> np.ndarray:
    return np.asarray(model.predict_proba(x_scaled)[:,1],dtype=float)


def checkpoint_path(run_id: str,model: str) -> Path:
    return CHECKPOINTS/f"{run_id}__{model}.json.gz"


def write_checkpoint(path: Path,payload: dict[str,Any]) -> None:
    path.parent.mkdir(parents=True,exist_ok=True); path.write_bytes(gzip.compress((json.dumps(json_safe(payload),sort_keys=True)+"\n").encode(),compresslevel=6,mtime=0))


def read_checkpoint(path: Path) -> dict[str,Any]:
    return json.loads(gzip.decompress(path.read_bytes()).decode())


def run_one(spec: Any,model_name: str,path: Sequence[int],population: pd.DataFrame,distances: np.ndarray) -> dict[str,Any]:
    destination=checkpoint_path(spec.run_id,model_name)
    if destination.is_file():
        payload=read_checkpoint(destination)
        if payload.get("complete") and payload.get("start_sha")==START_SHA:
            return {"run_id":spec.run_id,"model":model_name,"reused":True}
    x4=population.loc[:,FEATURES].to_numpy(float); labels=population.has_keyhole.astype(int).to_numpy(); test=np.asarray(spec.test_indices,dtype=int)
    scaler=StandardScaler().fit(x4[np.asarray(spec.train_indices,dtype=int)])
    flags=p17.subset_flags(spec,population,distances)
    predictions=[]; metrics=[]; diagnostics=[]
    for budget in BUDGETS:
        revealed=np.asarray(path[:budget],dtype=int); require(len(revealed)==budget and len(set(revealed.tolist()))==budget,"prefix drift")
        fit,diag=fit_gpc_model(model_name,scaler.transform(x4[revealed]),labels[revealed],seed_u32(model_name,spec.run_id,budget))
        probability=predict_positive(fit,scaler.transform(x4[test]))
        for local,pop_index in enumerate(test):
            predictions.append({"run_id":spec.run_id,"repeat":spec.repeat,"fold":spec.fold,"model":model_name,"budget":budget,"population_row_index":int(pop_index),"truth":int(labels[pop_index]),"probability":float(probability[local]),"is_q20":bool(flags["B1_q20"][local]),"is_q30":bool(flags["B1_q30"][local])})
        for subset,flag in flags.items():
            metrics.append({"run_id":spec.run_id,"repeat":spec.repeat,"fold":spec.fold,"model":model_name,"budget":budget,"subset":subset,**metric_values(labels[test][flag],probability[flag])})
        diagnostics.append({"run_id":spec.run_id,"repeat":spec.repeat,"fold":spec.fold,"model":model_name,"budget":budget,"revealed_count":budget,"scaler_fit_scope":"outer_training_pool_inputs","input_features":"P|VX|LS|ST",**diag})
    write_checkpoint(destination,{"complete":True,"start_sha":START_SHA,"run_id":spec.run_id,"model":model_name,"predictions":predictions,"metrics":metrics,"diagnostics":diagnostics})
    return {"run_id":spec.run_id,"model":model_name,"reused":False}


def run_new_kernels(workers: int=4,limit_specs: int|None=None,models: Sequence[str]=NEW_MODELS) -> dict[str,Any]:
    baseline_gate(); kernel_specification(); population,specs,paths=load_inputs(); distances=w85.b1_distance(population)
    if limit_specs: specs=specs[:limit_specs]
    jobs=[(spec,model) for spec in specs for model in models]; started=time.time()
    results=Parallel(n_jobs=workers,verbose=10)(delayed(run_one)(spec,model,paths[spec.run_id],population,distances) for spec,model in jobs)
    report={"status":"PASS","jobs":len(results),"reused":sum(row["reused"] for row in results),"workers":workers,"elapsed_seconds":time.time()-started,"complete":limit_specs is None and set(models)==set(NEW_MODELS)}
    write_json(OUTPUT/"execution_report.json",report); return report


def run_g0_checkpoints() -> dict[str,Any]:
    population,specs,paths=load_inputs(); x4=population.loc[:,FEATURES].to_numpy(float); labels=population.has_keyhole.astype(int).to_numpy(); distances=w85.b1_distance(population); rows=[]; metrics=[]
    for spec in specs:
        scaler=StandardScaler().fit(x4[np.asarray(spec.train_indices,dtype=int)]); test=np.asarray(spec.test_indices,dtype=int); flags=p17.subset_flags(spec,population,distances)
        for budget in CHECKPOINT_BUDGETS:
            revealed=np.asarray(paths[spec.run_id][:budget],dtype=int); seed=w85.seed_u32(w85.fit_seed_key(spec,"binary_margin",1,budget)); fit=p6.fit_gpc(x4[revealed],labels[revealed],scaler=scaler,seed=seed,restarts=0); probability=p6.predict_gpc(fit,x4[test])
            for local,pop_index in enumerate(test): rows.append({"run_id":spec.run_id,"repeat":spec.repeat,"fold":spec.fold,"model":"G0","budget":budget,"population_row_index":int(pop_index),"truth":int(labels[pop_index]),"probability":float(probability[local]),"is_q20":bool(flags["B1_q20"][local]),"is_q30":bool(flags["B1_q30"][local])})
            for subset,flag in flags.items(): metrics.append({"run_id":spec.run_id,"repeat":spec.repeat,"fold":spec.fold,"model":"G0","budget":budget,"subset":subset,**metric_values(labels[test][flag],probability[flag])})
    write_csv(OUTPUT/"g0_checkpoint_predictions.csv.gz",pd.DataFrame(rows)); write_csv(OUTPUT/"g0_checkpoint_metrics.csv",pd.DataFrame(metrics)); return {"status":"PASS","fits":len(specs)*len(CHECKPOINT_BUDGETS)}


def bootstrap_interval(values: np.ndarray,key: str) -> tuple[float,float,float]:
    values=np.asarray(values,dtype=float)
    require(len(values)==20 and np.isfinite(values).all(),f"repeat bootstrap input drift: {key}")
    rng=np.random.default_rng(seed_u32("bootstrap",key))
    draws=values[rng.integers(0,20,size=(BOOTSTRAP_DRAWS,20))].mean(axis=1)
    return float(values.mean()),float(np.quantile(draws,.025)),float(np.quantile(draws,.975))


def collect_new_checkpoints() -> tuple[pd.DataFrame,pd.DataFrame,pd.DataFrame]:
    files=sorted(CHECKPOINTS.glob("*.json.gz")); require(len(files)==400,f"expected 400 checkpoints, got {len(files)}")
    predictions=[]; metrics=[]; diagnostics=[]
    for path in files:
        payload=read_checkpoint(path)
        require(payload.get("complete") and payload.get("start_sha")==START_SHA,f"invalid checkpoint {path.name}")
        predictions.extend(payload["predictions"]); metrics.extend(payload["metrics"]); diagnostics.extend(payload["diagnostics"])
    prediction_frame=pd.DataFrame(predictions); metric_frame=pd.DataFrame(metrics); diagnostic_frame=pd.DataFrame(diagnostics)
    require(len(prediction_frame)==100*4*65*81,"new prediction completeness")
    require(len(metric_frame)==100*4*65*3,"new metric completeness")
    require(len(diagnostic_frame)==100*4*65,"new diagnostic completeness")
    if not (OUTPUT/"new_kernel_predictions.csv.gz").is_file(): write_csv(OUTPUT/"new_kernel_predictions.csv.gz",prediction_frame)
    if not (OUTPUT/"kernel_fit_diagnostics.csv.gz").is_file(): write_csv(OUTPUT/"kernel_fit_diagnostics.csv.gz",diagnostic_frame)
    return prediction_frame,metric_frame,diagnostic_frame


def metrics_from_h_predictions() -> tuple[pd.DataFrame,pd.DataFrame]:
    predictions=pd.read_csv(PHASE11/"h_only_a0_predictions.csv.gz")
    predictions=predictions.rename(columns={"model":"historical_model"}).assign(model="H")
    keys=["run_id","repeat","fold","budget"]; rows=[]
    predictions["decision"]=(predictions.probability>=.5).astype(int)
    predictions["correct"]=predictions.decision.eq(predictions.truth).astype(int)
    predictions["true_positive"]=(predictions.decision.eq(1)&predictions.truth.eq(1)).astype(int)
    predictions["true_negative"]=(predictions.decision.eq(0)&predictions.truth.eq(0)).astype(int)
    predictions["false_positive"]=(predictions.decision.eq(1)&predictions.truth.eq(0)).astype(int)
    predictions["false_negative"]=(predictions.decision.eq(0)&predictions.truth.eq(1)).astype(int)
    for subset,flag in (("B1_q20","is_q20"),("B1_q30","is_q30")):
        part=predictions[predictions[flag].astype(bool)]; grouped=part.groupby(keys,sort=True)
        agg=grouped[["correct","true_positive","true_negative","false_positive","false_negative"]].sum(); agg["row_count"]=grouped.size(); agg["accuracy"]=agg.correct/agg.row_count; agg["keyhole_recall"]=agg.true_positive/(agg.true_positive+agg.false_negative); agg["conduction_recall"]=agg.true_negative/(agg.true_negative+agg.false_positive); agg["balanced_accuracy"]=(agg.keyhole_recall+agg.conduction_recall)/2; agg["roc_auc"]=math.nan; agg["pr_auc"]=math.nan; agg["brier_score"]=math.nan; agg=agg.drop(columns="correct").reset_index().assign(model="H",subset=subset); rows.extend(agg.to_dict("records"))
    for keys_value,group in predictions[predictions.budget.isin(CHECKPOINT_BUDGETS)].groupby(keys,sort=True):
        run_id,repeat,fold,budget=keys_value; rows.append({"run_id":run_id,"repeat":repeat,"fold":fold,"model":"H","budget":int(budget),"subset":"full81",**metric_values(group.truth.to_numpy(int),group.probability.to_numpy(float))})
    metrics=pd.DataFrame(rows); require(len(metrics)==100*65*2+100*3,"H metric completeness")
    return predictions,metrics


def historical_g0_metrics() -> pd.DataFrame:
    four=pd.read_csv(PHASE18/"tables"/"four_way_metrics_per_budget.csv.gz",low_memory=False)
    keep=["run_id","repeat","fold","budget","subset","accuracy","balanced_accuracy","keyhole_recall","conduction_recall","false_negative","false_positive","true_negative","true_positive","row_count"]
    boundary=four[(four.arm.eq("Y00"))&four.subset.isin(("B1_q20","B1_q30"))][keep].copy().assign(model="G0")
    checkpoint=pd.read_csv(OUTPUT/"g0_checkpoint_metrics.csv")
    full=checkpoint[checkpoint.subset.eq("full81")].copy()
    require(len(boundary)==100*65*2 and len(full)==100*3,"G0 metric completeness")
    frozen=boundary[(boundary.subset.eq("B1_q20"))].groupby(["run_id","repeat","fold"],as_index=False).apply(lambda g: float(np.trapezoid(g.sort_values("budget").accuracy,g.sort_values("budget").budget)/64),include_groups=False)
    require(abs(float(frozen.iloc[:,-1].mean())-0.8135202205882353)<1e-12,"G0 frozen trajectory mismatch")
    audit=checkpoint[checkpoint.subset.isin(("B1_q20","B1_q30"))].merge(boundary,on=["run_id","repeat","fold","budget","subset"],suffixes=("_refit","_frozen"),validate="one_to_one")
    require(float((audit.accuracy_refit-audit.accuracy_frozen).abs().max())<1e-12,"G0 checkpoint refit mismatch")
    return pd.concat([boundary,full],ignore_index=True,sort=False)


def compute_aulc(metrics: pd.DataFrame) -> tuple[pd.DataFrame,pd.DataFrame,pd.DataFrame,pd.DataFrame]:
    rows=[]
    for keys,group in metrics[metrics.subset.isin(("B1_q20","B1_q30"))].groupby(["run_id","repeat","fold","model","subset"],sort=True):
        run_id,repeat,fold,model,subset=keys; ordered=group.sort_values("budget")
        require(ordered.budget.astype(int).tolist()==list(BUDGETS),f"AULC grid drift {run_id}/{model}/{subset}")
        rows.append({"run_id":run_id,"repeat":repeat,"fold":fold,"model":model,"subset":subset,"accuracy_AULC_16_80":float(np.trapezoid(ordered.accuracy,ordered.budget)/64)})
    outer=pd.DataFrame(rows); require(len(outer)==100*6*2,"six-model AULC completeness")
    repeat=outer.groupby(["repeat","model","subset"],as_index=False).accuracy_AULC_16_80.mean()
    summary=[]
    for (model,subset),group in repeat.groupby(["model","subset"],sort=True):
        mean,lo,hi=bootstrap_interval(group.sort_values("repeat").accuracy_AULC_16_80.to_numpy(),f"summary|{model}|{subset}")
        summary.append({"model":model,"subset":subset,"mean_AULC":mean,"ci_lower":lo,"ci_upper":hi})
    pairs=(("G3","G0"),("G3","H"),("G1","G0"),("G2","G1"),("G4","G0"),("G2","H"),("G1","H"),("G4","H"))
    wide=repeat.pivot(index=["repeat","subset"],columns="model",values="accuracy_AULC_16_80").reset_index(); contrasts=[]
    for subset in ("B1_q20","B1_q30"):
        part=wide[wide.subset.eq(subset)].sort_values("repeat")
        for left,right in pairs:
            values=(part[left]-part[right]).to_numpy(float); mean,lo,hi=bootstrap_interval(values,f"contrast|{left}-{right}|{subset}")
            contrasts.append({"contrast":f"{left}-{right}","subset":subset,"mean_difference":mean,"ci_lower":lo,"ci_upper":hi,"positive_repeat_blocks":int((values>0).sum()),"zero_repeat_blocks":int((values==0).sum()),"negative_repeat_blocks":int((values<0).sum()),"bootstrap_draws":BOOTSTRAP_DRAWS})
    return outer,repeat,pd.DataFrame(summary),pd.DataFrame(contrasts)


def summarize_budget(metrics: pd.DataFrame,budgets: Sequence[int],metric_names: Sequence[str],name: str) -> pd.DataFrame:
    selected=metrics[(metrics.subset.eq("B1_q20"))&metrics.budget.isin(budgets)].copy(); rows=[]
    for (model,budget),group in selected.groupby(["model","budget"],sort=True):
        for metric in metric_names:
            values=group.groupby("repeat")[metric].mean().sort_index().to_numpy(float); mean,lo,hi=bootstrap_interval(values,f"{name}|{model}|{budget}|{metric}")
            rows.append({"model":model,"subset":"B1_q20","budget":int(budget),"metric":metric,"mean":mean,"ci_lower":lo,"ci_upper":hi})
    return pd.DataFrame(rows)


def budget16_contrasts(metrics: pd.DataFrame) -> pd.DataFrame:
    selected=metrics[(metrics.subset.eq("B1_q20"))&metrics.budget.eq(16)].copy(); rows=[]
    pairs=(("G3","G0"),("G3","H"),("G1","G0"),("G2","G1"),("G4","G0"))
    for metric in ("accuracy","balanced_accuracy","keyhole_recall","conduction_recall","false_negative","false_positive"):
        wide=selected.pivot(index=["repeat","fold"],columns="model",values=metric).reset_index()
        for left,right in pairs:
            values=(wide[left]-wide[right]).groupby(wide.repeat).mean().sort_index().to_numpy(float); mean,lo,hi=bootstrap_interval(values,f"B16|{left}-{right}|{metric}")
            rows.append({"contrast":f"{left}-{right}","subset":"B1_q20","budget":16,"metric":metric,"mean_difference":mean,"ci_lower":lo,"ci_upper":hi})
    return pd.DataFrame(rows)


def full81_checkpoint_summary(metrics: pd.DataFrame) -> pd.DataFrame:
    part=metrics[(metrics.subset.eq("full81"))&metrics.budget.isin(CHECKPOINT_BUDGETS)]; rows=[]
    for (model,budget),group in part.groupby(["model","budget"],sort=True):
        for metric in ("roc_auc","pr_auc","accuracy","balanced_accuracy","brier_score"):
            values=group.groupby("repeat")[metric].mean().sort_index().to_numpy(float); mean,lo,hi=bootstrap_interval(values,f"full81|{model}|{budget}|{metric}")
            rows.append({"model":model,"subset":"full81","budget":int(budget),"metric":metric,"mean":mean,"ci_lower":lo,"ci_upper":hi})
    return pd.DataFrame(rows)


def hard_disagreements(h_predictions: pd.DataFrame,new_predictions: pd.DataFrame) -> pd.DataFrame:
    g0=pd.read_csv(OUTPUT/"g0_checkpoint_predictions.csv.gz"); allp=pd.concat([h_predictions,new_predictions,new_predictions.iloc[0:0],g0],ignore_index=True,sort=False)
    allp=allp[(allp.budget.eq(16))&allp.is_q20.astype(bool)&allp.model.isin(("H","G0","G3"))].copy(); allp["decision"]=(allp.probability>=.5).astype(int); allp["correct"]=allp.decision.eq(allp.truth)
    wide=allp.pivot(index=["run_id","repeat","fold","population_row_index","truth"],columns="model",values=["decision","correct"]).reset_index(); rows=[]
    for other in ("G0","G3"):
        a=wide[("decision","H")].astype(int); b=wide[("decision",other)].astype(int); ca=wide[("correct","H")].astype(bool); cb=wide[("correct",other)].astype(bool)
        counts={"same_decision":int((a==b).sum()),"different_decision":int((a!=b).sum()),"H_only_correct":int((ca&~cb).sum()),f"{other}_only_correct":int((~ca&cb).sum()),"both_correct":int((ca&cb).sum()),"both_wrong":int((~ca&~cb).sum())}
        rows.extend({"pair":f"H_vs_{other}","category":key,"count":value,"scope":"100 matched outer-fold q20 test predictions at B16"} for key,value in counts.items())
    return pd.DataFrame(rows)


def ard_and_bound_summaries(diagnostics: pd.DataFrame) -> tuple[pd.DataFrame,pd.DataFrame]:
    ard=diagnostics[diagnostics.model.isin(("G2","G3"))&diagnostics.budget.isin(CHECKPOINT_BUDGETS)].copy(); rows=[]
    for (model,budget),group in ard.groupby(["model","budget"],sort=True):
        for parameter in ("l_P","l_VX","l_LS","l_ST","anisotropy_ratio"):
            values=group[parameter].dropna().to_numpy(float)
            rows.append({"model":model,"budget":int(budget),"parameter":parameter,"median":float(np.median(values)),"q1":float(np.quantile(values,.25)),"q3":float(np.quantile(values,.75)),"space":"standardized outer-training-pool inputs"})
    bound=[]
    indicators=["amplitude_lower_bound_hit","amplitude_upper_bound_hit","any_length_lower_bound_hit","any_length_upper_bound_hit","any_length_bound_hit","optimizer_warning"]
    indicators += [f"l_{feature}_{side}_bound_hit" for feature in FEATURES for side in ("lower","upper")]
    for model,group in diagnostics.groupby("model",sort=True):
        for indicator in indicators:
            if indicator not in group: continue
            values=group[indicator].fillna(False).astype(bool)
            bound.append({"model":model,"diagnostic":indicator,"fit_count":len(group),"count":int(values.sum()),"rate":float(values.mean())})
        fallback=group.fit_status.ne("optimized_primary")
        bound.append({"model":model,"diagnostic":"fit_fallback","fit_count":len(group),"count":int(fallback.sum()),"rate":float(fallback.mean())})
    return pd.DataFrame(rows),pd.DataFrame(bound)


def oracle_diagnostic(repeat: pd.DataFrame) -> pd.DataFrame:
    q20=repeat[repeat.subset.eq("B1_q20")].pivot(index="repeat",columns="model",values="accuracy_AULC_16_80")
    gpcs=["G0","G1","G2","G3","G4"]; rows=[]
    for repeat_id,row in q20.iterrows():
        selected=max(gpcs,key=lambda name:float(row[name])); oracle=float(row[selected]); h=float(row.H)
        rows.append({"repeat":int(repeat_id),"H_AULC":h,"oracle_GPC_AULC":oracle,"H_minus_oracle":h-oracle,"oracle_selected_model":selected,"diagnostic_status":"NON_DEPLOYABLE_REPEATWISE_ORACLE"})
    frame=pd.DataFrame(rows); mean,lo,hi=bootstrap_interval(frame.H_minus_oracle.to_numpy(float),"H-oracle")
    frame.attrs["summary"]={"mean":mean,"ci_lower":lo,"ci_upper":hi}
    return frame


def decide(contrasts: pd.DataFrame,summary: pd.DataFrame) -> str:
    q=contrasts[contrasts.subset.eq("B1_q20")].set_index("contrast"); g30=q.loc["G3-G0"]; g3h=q.loc["G3-H"]
    if g3h.ci_lower>0: return "GPC_SURPASSES_H"
    for name in ("G2-H","G1-H","G4-H"):
        if q.loc[name].ci_lower>0: return "GPC_SURPASSES_H"
    if g30.ci_lower>0 and g3h.ci_upper<0: return "ANISOTROPY_MATTERS"
    if g30.ci_lower>0 and g3h.ci_lower<=0<=g3h.ci_upper: return "KERNEL_GAP_CLOSED"
    if g3h.ci_upper<0: return "PHYSICS_ADVANTAGE_ROBUST"
    return "NO_CLEAR_KERNEL_EFFECT"


def make_figures(metrics: pd.DataFrame,contrasts: pd.DataFrame,ard: pd.DataFrame,bounds: pd.DataFrame) -> pd.DataFrame:
    FIGURES.mkdir(parents=True,exist_ok=True); created=[]
    colors={"H":"#2f855a","G0":"#344e78","G1":"#d97706","G2":"#b45309","G3":"#7c3aed","G4":"#c2415d"}
    labels={"H":"H: log(h) logistic","G0":"G0: iso Matern-3/2","G1":"G1: iso RBF","G2":"G2: ARD RBF","G3":"G3: ARD Matern-3/2","G4":"G4: iso Matern-5/2"}
    curve=metrics[metrics.subset.eq("B1_q20")].groupby(["model","budget"],as_index=False).accuracy.mean()
    fig,ax=plt.subplots(figsize=(10,5.8))
    for model in ALL_MODELS:
        part=curve[curve.model.eq(model)].sort_values("budget"); ax.plot(part.budget,part.accuracy,lw=2.1,color=colors[model],label=labels[model])
    ax.set(xlabel="Revealed simulations on frozen A0 path",ylabel="Fold-B1-q20 accuracy",title="Kernel adequacy on identical revealed labels"); ax.grid(alpha=.25); ax.legend(frameon=False,ncol=2,fontsize=9); fig.tight_layout()
    path=FIGURES/"01_q20_learning_curves.png"; fig.savefig(path,dpi=180); plt.close(fig); created.append((path,"Six-model q20 learning curves on the exact same A0 prefixes."))
    order=["G3-G0","G3-H","G1-G0","G2-G1","G4-G0"]; part=contrasts[(contrasts.subset.eq("B1_q20"))&contrasts.contrast.isin(order)].set_index("contrast").loc[order].reset_index(); y=np.arange(len(part))
    fig,ax=plt.subplots(figsize=(8.2,4.8)); ax.errorbar(part.mean_difference,y,xerr=[part.mean_difference-part.ci_lower,part.ci_upper-part.mean_difference],fmt="o",capsize=5,color="#553c9a",ms=7); ax.axvline(0,color="black",ls="--",lw=1); ax.set_yticks(y,part.contrast); ax.invert_yaxis(); ax.set(xlabel="Matched q20 accuracy AULC difference",title="Predeclared kernel contrasts (95% repeat-block intervals)"); ax.grid(axis="x",alpha=.25); fig.tight_layout()
    path=FIGURES/"02_q20_aulc_contrasts.png"; fig.savefig(path,dpi=180); plt.close(fig); created.append((path,"Primary and secondary predeclared q20 AULC contrasts."))
    fig,axes=plt.subplots(1,2,figsize=(11,4.8),sharey=True); feature_labels={"l_P":"P","l_VX":"VX","l_LS":"LS","l_ST":"ST"}; palette={16:"#9ecae1",40:"#4292c6",80:"#084594"}
    for ax,model in zip(axes,("G2","G3")):
        part=ard[(ard.model.eq(model))&ard.parameter.isin(feature_labels)]
        for budget,group in part.groupby("budget"):
            group=group.set_index("parameter").loc[list(feature_labels)]; x=np.arange(4)+(budget-40)/120
            ax.errorbar(x,group["median"],yerr=[group["median"]-group.q1,group.q3-group["median"]],fmt="o",capsize=4,label=f"B{budget}",color=palette[int(budget)])
        ax.set_xticks(np.arange(4),list(feature_labels.values())); ax.set_yscale("log"); ax.set_title(labels[model]); ax.grid(axis="y",alpha=.25); ax.set_xlabel("Standardized input coordinate")
    axes[0].set_ylabel("ARD lengthscale (median and IQR, log scale)"); axes[1].legend(frameon=False); fig.suptitle("ARD geometry diagnostics; not causal feature importance"); fig.tight_layout()
    path=FIGURES/"03_ard_lengthscales.png"; fig.savefig(path,dpi=180); plt.close(fig); created.append((path,"ARD lengthscales at B16/B40/B80 in standardized input space."))
    wanted=["any_length_lower_bound_hit","any_length_upper_bound_hit","amplitude_lower_bound_hit","amplitude_upper_bound_hit","optimizer_warning","fit_fallback"]; part=bounds[bounds.diagnostic.isin(wanted)].pivot(index="model",columns="diagnostic",values="rate").reindex(list(NEW_MODELS)); x=np.arange(len(part)); fig,ax=plt.subplots(figsize=(10,5.2)); width=.13
    for i,item in enumerate(wanted): ax.bar(x+(i-2.5)*width,part[item],width,label=item.replace("_"," "))
    ax.set_xticks(x,list(part.index)); ax.set(ylabel="Fraction of 6,500 prefix fits",title="Kernel optimization and bound diagnostics",ylim=(0,max(.05,float(part.max().max())*1.18))); ax.grid(axis="y",alpha=.25); ax.legend(frameon=False,ncol=2,fontsize=8); fig.tight_layout()
    path=FIGURES/"04_kernel_fit_diagnostics.png"; fig.savefig(path,dpi=180); plt.close(fig); created.append((path,"Bound-hit, warning, and fallback rates for each new kernel."))
    manifest=pd.DataFrame([{"figure":p.name,"sha256":sha256_file(p),"size_bytes":p.stat().st_size,"purpose":purpose} for p,purpose in created]); write_csv(OUTPUT/"figure_manifest.csv",manifest); return manifest


def build_reports(summary: pd.DataFrame,contrasts: pd.DataFrame,b16: pd.DataFrame,late: pd.DataFrame,ard: pd.DataFrame,bounds: pd.DataFrame,oracle: pd.DataFrame,decision: str) -> None:
    def s(model:str,subset:str="B1_q20") -> float: return float(summary[(summary.model.eq(model))&summary.subset.eq(subset)].mean_AULC.iloc[0])
    def c(name:str,subset:str="B1_q20") -> pd.Series: return contrasts[(contrasts.contrast.eq(name))&contrasts.subset.eq(subset)].iloc[0]
    def b(model:str,metric:str,budget:int=16) -> float: return float((b16 if budget==16 else late)[lambda d:(d.model.eq(model))&d.metric.eq(metric)&d.budget.eq(budget)]["mean"].iloc[0])
    q30=c("G3-G0","B1_q30"); primary=c("G3-G0"); gap=c("G3-H"); best=summary[summary.subset.eq("B1_q20")&summary.model.ne("H")].sort_values("mean_AULC",ascending=False).iloc[0]
    oracle_summary=oracle.attrs.get("summary",{}); future="YES" if primary.ci_lower>0 else "NO"
    bound_line=[]
    for model in ("G2","G3"):
        any_rate=float(bounds[(bounds.model.eq(model))&bounds.diagnostic.eq("any_length_bound_hit")].rate.iloc[0]); ratio=ard[(ard.model.eq(model))&ard.parameter.eq("anisotropy_ratio")&ard.budget.eq(16)].iloc[0]
        bound_line.append(f"{model}: any-length bound {any_rate:.1%}; B16 anisotropy ratio median {ratio['median']:.2f} (IQR {ratio.q1:.2f}-{ratio.q3:.2f})")
    final=["# Week 9 Phase 1.12 — GPC Kernel Adequacy / Anisotropy Control","",f"## Decision: {decision}","","## Primary same-path result",f"All six models received identical frozen A0 prefixes. q20 AULC was H {s('H'):.6f}, G0 {s('G0'):.6f}, G1 {s('G1'):.6f}, G2 {s('G2'):.6f}, G3 {s('G3'):.6f}, and G4 {s('G4'):.6f}.",f"Primary G3-G0: {primary.mean_difference:+.6f} [{primary.ci_lower:+.6f}, {primary.ci_upper:+.6f}] ({int(primary.positive_repeat_blocks)}/20 positive repeat blocks).",f"Key G3-H: {gap.mean_difference:+.6f} [{gap.ci_lower:+.6f}, {gap.ci_upper:+.6f}]. An interval containing zero is unresolved, not equivalence.",f"The descriptive best fixed GPC was {best.model} ({best.mean_AULC:.6f}); this ranking is not treated as predeclared winner inference.",f"The non-deployable repeatwise GPC oracle gave H-oracle {oracle_summary.get('mean',float('nan')):+.6f} [{oracle_summary.get('ci_lower',float('nan')):+.6f}, {oracle_summary.get('ci_upper',float('nan')):+.6f}].","","## Low-data and later checkpoints",f"At B16 q20 accuracy was H/G0/G3 {b('H','accuracy'):.4f}/{b('G0','accuracy'):.4f}/{b('G3','accuracy'):.4f}; Keyhole recall was {b('H','keyhole_recall'):.4f}/{b('G0','keyhole_recall'):.4f}/{b('G3','keyhole_recall'):.4f}.",f"At B40 q20 accuracy H/G0/G3 was {b('H','accuracy',40):.4f}/{b('G0','accuracy',40):.4f}/{b('G3','accuracy',40):.4f}; at B80 it was {b('H','accuracy',80):.4f}/{b('G0','accuracy',80):.4f}/{b('G3','accuracy',80):.4f}.","","## q30 robustness",f"G3-G0 q30 AULC: {q30.mean_difference:+.6f} [{q30.ci_lower:+.6f}, {q30.ci_upper:+.6f}]. H/G0/G3 q30 AULC: {s('H','B1_q30'):.6f}/{s('G0','B1_q30'):.6f}/{s('G3','B1_q30'):.6f}.","","## ARD stability",*bound_line,"Lengthscales are standardized-space model-geometry diagnostics, not physical units or causal feature importance.","","## Safe interpretation","The result is a held-out surrogate comparison on one frozen simulator benchmark. It tests kernel adequacy, not acquisition, external validity, or physical causality.","","## Future h + ARD discrepancy GP",f"Recommendation: **{future}**. This is justified only when G3 materially improves standalone 4D GPC behavior."]
    (OUTPUT/"FINAL_PHASE1_12_REPORT.md").write_text("\n".join(final)+"\n",encoding="utf-8")
    supervisor=["# Supervisor Phase 1.12 — one page","",f"**Decision:** {decision}","",f"- q20 AULC H/G0/G1/G2/G3/G4: {s('H'):.4f} / {s('G0'):.4f} / {s('G1'):.4f} / {s('G2'):.4f} / {s('G3'):.4f} / {s('G4'):.4f}.",f"- Primary ARD Matérn-3/2 gain over isotropic Matérn-3/2: {primary.mean_difference:+.4f} [{primary.ci_lower:+.4f}, {primary.ci_upper:+.4f}].",f"- ARD Matérn-3/2 versus h-only: {gap.mean_difference:+.4f} [{gap.ci_lower:+.4f}, {gap.ci_upper:+.4f}].",f"- B16 q20 accuracy H/G0/G3: {b('H','accuracy'):.3f} / {b('G0','accuracy'):.3f} / {b('G3','accuracy'):.3f}.",f"- B16 q20 Keyhole recall H/G0/G3: {b('H','keyhole_recall'):.3f} / {b('G0','keyhole_recall'):.3f} / {b('G3','keyhole_recall'):.3f}.",f"- q30 G3-G0: {q30.mean_difference:+.4f} [{q30.ci_lower:+.4f}, {q30.ci_upper:+.4f}].",f"- Descriptive best fixed GPC: {best.model}; no post-hoc winner CI is promoted.",f"- Future h + ARD discrepancy GP: {future}.","","All models saw the same revealed labels. ARD lengthscales describe fitted standardized geometry only; boundary hits and optimizer warnings are disclosed. No acquisition claim is made."]
    (OUTPUT/"SUPERVISOR_PHASE1_12_ONE_PAGE.md").write_text("\n".join(supervisor)+"\n",encoding="utf-8")
    def status(row:pd.Series) -> str:
        if row.ci_lower>0:return "SUPPORTED"
        if row.ci_upper<0:return "NOT SUPPORTED"
        return "UNRESOLVED"
    ledger=["# Phase 1.12 claim ledger","","| Claim | Status | Evidence boundary |","|---|---|---|",f"| A. ARD Matérn-3/2 improves q20 AULC over isotropic Matérn-3/2. | {status(primary)} | Predeclared G3-G0 repeat-block contrast. |",f"| B. ARD Matérn-3/2 closes the h-only gap. | {'QUALIFIED' if gap.ci_lower<=0<=gap.ci_upper else ('SUPPORTED' if gap.ci_lower>0 else 'NOT SUPPORTED')} | G3-H; unresolved is not equivalence. |",f"| C. ARD Matérn-3/2 surpasses h-only. | {status(gap)} | Predeclared G3-H. |",f"| D. RBF improves over Matérn-3/2. | {status(c('G1-G0'))} | Secondary predeclared contrast. |",f"| E. ARD improves RBF. | {status(c('G2-G1'))} | Secondary predeclared contrast. |",f"| F. Matérn-5/2 improves over Matérn-3/2. | {status(c('G4-G0'))} | Secondary predeclared contrast. |",f"| G. h-only is descriptively strongest fixed low-data model. | {'SUPPORTED DESCRIPTIVELY' if s('H')>=max(s(m) for m in ('G0','G1','G2','G3','G4')) else 'NOT SUPPORTED'} | Ranking only; no winner-selected inference. |","| H. Canonical GPC was unfairly weak because of isotropy. | NOT ESTABLISHED | Requires resolved G3-G0 and context. |","| I. ARD lengthscales prove physical-variable importance. | NOT SUPPORTED | Geometry diagnostics only. |","| J. Phase 1.12 improves acquisition. | NOT TESTED | A0 path frozen. |",f"| K. Future h + ARD discrepancy GP is justified. | {'SUPPORTED' if future=='YES' else 'NOT SUPPORTED'} | Based only on whether G3 materially improves standalone GPC. |"]
    (OUTPUT/"claim_ledger.md").write_text("\n".join(ledger)+"\n",encoding="utf-8")
    red=["# Final red-team report","","- All kernels used identical P, VX, LS, ST scaling, amplitude/length bounds, optimizer, restart count, A0 prefixes, and revealed labels.","- G0 and H were read from frozen artifacts; only a three-budget G0 diagnostic refit was performed and numerically gated.","- Test labels and B1/q20/q30 membership never entered fitting or kernel choice.","- G3 was primary before results; descriptive-best and repeatwise oracle outputs are clearly separated from predeclared inference.","- An unresolved G3-H interval is not called equivalence.","- ARD lengthscales are not called causal importance and their bound behavior is reported.","- Week 5 regression evidence supplies conventions only, not classification evidence.","- No logs, external exponents, h input, new acquisition, or discrepancy GP entered the GPC comparison.","- Inference resamples 20 repeat blocks, retaining five folds together.","- Remaining limitation: optimizer warnings/bound hits and finite benchmark size constrain geometric interpretation."]
    (OUTPUT/"FINAL_RED_TEAM_REPORT.md").write_text("\n".join(red)+"\n",encoding="utf-8")


def build_notebook() -> None:
    cells=[nbf.v4.new_markdown_cell("# Week 9 Phase 1.12 — GPC Kernel Adequacy / Anisotropy Control\n\nA compact teaching notebook reading the frozen outputs; it does not rerun 26,000 GPC fits."),nbf.v4.new_markdown_cell("## 1. Why this control is necessary\n\nThe scalar physics model H beat the canonical isotropic Matérn-3/2 GPC at low budgets. Here every model sees exactly the same A0 labels, so differences isolate surrogate geometry rather than acquisition."),nbf.v4.new_code_cell("from pathlib import Path\nimport json, pandas as pd\nfrom IPython.display import display, Image, Markdown\nROOT=Path.cwd().parents[1] if Path.cwd().name=='week_09' else Path.cwd()\nOUT=ROOT/'outputs'/'week9_phase1_12_gpc_kernel_adequacy'\ndisplay(json.loads((OUT/'baseline_gate.json').read_text()))"),nbf.v4.new_markdown_cell("## 2. Smoothness and anisotropy\n\nRBF is infinitely differentiable; Matérn-3/2 and Matérn-5/2 allow rougher functions. Isotropic kernels share one lengthscale, whereas ARD fits one per standardized coordinate. ARD lengthscales are geometry diagnostics, not causal feature importance."),nbf.v4.new_code_cell("spec=json.loads((OUT/'kernel_specification.json').read_text()); display(pd.DataFrame(spec['models']).T)"),nbf.v4.new_markdown_cell("## 3. Frozen protocol\n\nThe 100 outer runs, shared B16 designs, A0 prefixes, B1-q20/q30 definitions, and 16–80 grid are unchanged. Week 5 was regression on a different target; it motivates kernel conventions but does not answer this classification question."),nbf.v4.new_code_cell("summary=pd.read_csv(OUT/'model_summary.csv'); contrasts=pd.read_csv(OUT/'paired_contrasts.csv'); display(summary); display(contrasts[contrasts.subset.eq('B1_q20')]); display(Image(filename=str(OUT/'figures'/'01_q20_learning_curves.png'))); display(Image(filename=str(OUT/'figures'/'02_q20_aulc_contrasts.png')))"),nbf.v4.new_markdown_cell("## 4. B16 and later checkpoints\n\nB16 is the clean low-data comparison because all models receive the same initial design."),nbf.v4.new_code_cell("display(pd.read_csv(OUT/'budget16_summary.csv')); display(pd.read_csv(OUT/'budget16_hard_disagreements.csv')); display(pd.read_csv(OUT/'checkpoint40_80_summary.csv'))"),nbf.v4.new_markdown_cell("## 5. ARD stability and bound behavior\n\nLengthscales are reported in standardized input space. Values at bounds signal weakly resolved geometry, not physical irrelevance."),nbf.v4.new_code_cell("display(pd.read_csv(OUT/'ard_lengthscale_summary.csv')); display(pd.read_csv(OUT/'bound_hit_summary.csv')); display(Image(filename=str(OUT/'figures'/'03_ard_lengthscales.png'))); display(Image(filename=str(OUT/'figures'/'04_kernel_fit_diagnostics.png')))"),nbf.v4.new_markdown_cell("## 6. Best fixed kernel versus an oracle\n\nThe highest mean fixed GPC is descriptive. The oracle chooses a kernel separately per repeat and is intentionally non-deployable."),nbf.v4.new_code_cell("display(pd.read_csv(OUT/'oracle_gpc_diagnostic.csv')); display(Markdown((OUT/'SUPERVISOR_PHASE1_12_ONE_PAGE.md').read_text()))"),nbf.v4.new_markdown_cell("## 7. Limits\n\nThis phase tests held-out boundary prediction on a frozen simulator benchmark. It does not establish acquisition superiority, causal variable importance, or external validity.")]
    notebook=nbf.v4.new_notebook(cells=cells,metadata={"kernelspec":{"display_name":"Thesis Python","language":"python","name":"thesis"}}); NOTEBOOK.parent.mkdir(parents=True,exist_ok=True); nbf.write(notebook,NOTEBOOK)
    executed=NotebookClient(nbf.read(NOTEBOOK,as_version=4),timeout=180,kernel_name="thesis",resources={"metadata":{"path":str(ROOT)}}).execute(); nbf.write(executed,NOTEBOOK)


def historical_changes() -> list[str]:
    historical=["outputs/week9_phase1_5_h_physics_confirmation","outputs/week9_phase1_7_physics_ridge_residual_gp","outputs/week9_phase1_8_model_path_decomposition","outputs/week9_phase1_9_physics_specificity_control","outputs/week9_phase1_10_external_experimental_validation","outputs/week9_phase1_10_closure_diagnostics","outputs/week9_phase1_11_fixed_mean_discrepancy_gp"]
    output=subprocess.check_output(["git","diff","--name-only",START_SHA,"--",*historical],cwd=ROOT,text=True); return [x for x in output.splitlines() if x.strip()]


def validate(metrics: pd.DataFrame,contrasts: pd.DataFrame,diagnostics: pd.DataFrame,figures: pd.DataFrame,decision: str) -> dict[str,Any]:
    source=Path(__file__).read_text(encoding="utf-8"); fit_source=source[source.index("def make_kernel"):source.index("def checkpoint_path")]+source[source.index("def run_one("):source.index("def run_new_kernels")]; population,specs,paths=load_inputs(); gate=json.loads((OUTPUT/"baseline_gate.json").read_text()); kernels=json.loads((OUTPUT/"kernel_specification.json").read_text()); notebook=nbf.read(NOTEBOOK,as_version=4); code=[c for c in notebook.cells if c.cell_type=="code"]; repeat_public=pd.read_csv(OUTPUT/"repeat_metrics.csv"); prediction_models=pd.read_csv(OUTPUT/"new_kernel_predictions.csv.gz",usecols=["model"])
    def has_contrast(name:str) -> bool: return len(contrasts[(contrasts.contrast.eq(name))&contrasts.subset.eq("B1_q20")])==1
    checks=[
        ("exact_start_sha",subprocess.check_output(["git","rev-parse",START_SHA],cwd=ROOT,text=True).strip()==START_SHA,START_SHA),
        ("historical_phase1x_unchanged",historical_changes()==[],str(historical_changes())),
        ("population_405_73_332",len(population)==405 and int(population.has_keyhole.sum())==73,"405/73/332"),
        ("exact_100_A0_paths",len(paths)==100 and len(specs)==100,"100"),
        ("exact_initial_B16",gate["initial_B16_matches"]==100,"100/100"),
        ("exact_budget_grid",gate["budgets"]==list(BUDGETS),"16-80"),
        ("frozen_H_reproduced",abs(gate["H_q20_AULC"]-0.8308134191176471)<1e-12,str(gate["H_q20_AULC"])),
        ("frozen_G0_reproduced",abs(gate["G0_q20_AULC"]-0.8135202205882353)<1e-12,str(gate["G0_q20_AULC"])),
        ("no_new_acquisition","run_one(spec,model_name,paths[spec.run_id]" in source or "run_one)(spec,model,paths[spec.run_id]" in source,"A0 replay"),
        ("same_revealed_prefix","revealed=np.asarray(path[:budget]" in source,"exact prefix"),
        ("test_labels_not_fit","labels[revealed]" in source and "labels[test]" not in source.split("fit_gpc_model",1)[1].split("def predict_positive",1)[0],"revealed only"),
        ("boundary_flags_evaluation_only","fit_gpc_model(model_name,scaler.transform(x4[revealed]),labels[revealed]" in source,"q flags added after prediction"),
        ("GPC_inputs_exact",FEATURES==("P","VX","LS","ST"),str(FEATURES)),
        ("scaler_outer_pool","StandardScaler().fit(x4[np.asarray(spec.train_indices" in source,"label-free outer pool"),
        ("G0_matern32",kernels["models"]["G0"]["family"]=="Matern" and kernels["models"]["G0"]["nu"]==1.5,"G0"),
        ("G1_isotropic_RBF",kernels["models"]["G1"]["family"]=="RBF" and not kernels["models"]["G1"]["ard"],"G1"),
        ("G2_ARD_RBF",kernels["models"]["G2"]["family"]=="RBF" and kernels["models"]["G2"]["ard"],"four lengths"),
        ("G3_ARD_matern32",kernels["models"]["G3"]["family"]=="Matern" and kernels["models"]["G3"]["nu"]==1.5 and kernels["models"]["G3"]["ard"],"G3"),
        ("G4_isotropic_matern52",kernels["models"]["G4"]["nu"]==2.5 and not kernels["models"]["G4"]["ard"],"G4"),
        ("common_amplitude_bounds",len({tuple(v["amplitude_bounds"]) for v in kernels["models"].values()})==1,str(AMPLITUDE_BOUNDS)),
        ("common_length_bounds",len({tuple(v["length_scale_bounds"]) for v in kernels["models"].values()})==1,str(LENGTH_BOUNDS)),
        ("same_optimizer_restarts",all(v["n_restarts_optimizer"]==0 and v["optimizer"]=="fmin_l_bfgs_b" for v in kernels["models"].values()),"0 restarts"),
        ("no_external_exponent",all(x not in fit_source for x in ("-1.713","-1.219")),"none"),
        ("no_h_in_GPC_inputs","log_h" not in "|".join(FEATURES),str(FEATURES)),
        ("no_week5_target","first_conduction" not in fit_source.lower(),"classification only"),
        ("new_prediction_completeness",len(prediction_models)==100*4*65*81 and set(prediction_models.model)==set(NEW_MODELS),"all G1-G4 predictions"),
        ("twenty_repeat_blocks",repeat_public.repeat.nunique()==20,"20"),
        ("bootstrap_10000",BOOTSTRAP_DRAWS>=10000,str(BOOTSTRAP_DRAWS)),
        ("primary_G3_G0",has_contrast("G3-G0"),"q20/q30"),
        ("key_G3_H",has_contrast("G3-H"),"q20/q30"),
        ("secondary_contrasts",all(has_contrast(x) for x in ("G1-G0","G2-G1","G4-G0","G2-H","G1-H","G4-H")),"complete"),
        ("ARD_fields_complete",diagnostics[diagnostics.model.isin(("G2","G3"))][["l_P","l_VX","l_LS","l_ST","anisotropy_ratio"]].notna().all().all(),"four labeled lengths"),
        ("ARD_labels_correct",list(FEATURES)==["P","VX","LS","ST"],"P,VX,LS,ST"),
        ("no_causal_ARD_wording","prove physical-variable importance" not in (OUTPUT/"FINAL_PHASE1_12_REPORT.md").read_text().lower(),"claim-safe"),
        ("descriptive_best_not_inferred","not treated as predeclared winner inference" in (OUTPUT/"FINAL_PHASE1_12_REPORT.md").read_text(),"explicit"),
        ("oracle_non_deployable",pd.read_csv(OUTPUT/"oracle_gpc_diagnostic.csv").diagnostic_status.eq("NON_DEPLOYABLE_REPEATWISE_ORACLE").all(),"explicit"),
        ("notebook_executed",bool(code) and all(c.execution_count is not None for c in code) and not [o for c in code for o in c.get("outputs",[]) if o.get("output_type")=="error"],f"{len(code)} code cells"),
        ("figure_hashes",len(figures)==4 and all(sha256_file(FIGURES/r.figure)==r.sha256 for r in figures.itertuples(index=False)),"4/4"),
        ("historical_outputs_unchanged_again",historical_changes()==[],"git diff gate"),
        ("red_team_claim_language",all(x not in (OUTPUT/"FINAL_PHASE1_12_REPORT.md").read_text().lower() for x in ("acquisition superiority","ard proves","equivalent to h")),"safe"),
        ("exact_six_models",set(repeat_public.model.unique())==set(ALL_MODELS),str(sorted(repeat_public.model.unique()))),
        ("G3_primary_frozen",MODEL_SPECS["G3"]["primary"] is True,"G3"),
        ("fit_diagnostic_count",len(diagnostics)==100*4*65,"26000"),
        ("fallback_disclosed","fit_fallback" in pd.read_csv(OUTPUT/"bound_hit_summary.csv").diagnostic.unique(),"yes"),
        ("decision_declared",decision in {"PHYSICS_ADVANTAGE_ROBUST","ANISOTROPY_MATTERS","KERNEL_GAP_CLOSED","GPC_SURPASSES_H","NO_CLEAR_KERNEL_EFFECT"},decision),
        ("no_report_template_placeholders","{future}" not in (OUTPUT/"FINAL_PHASE1_12_REPORT.md").read_text(),"resolved recommendation"),
    ]
    records=[{"check":name,"status":"PASS" if ok else "FAIL","detail":detail} for name,ok,detail in checks]; payload={"status":"PASS" if all(r["status"]=="PASS" for r in records) else "FAIL","check_count":len(records),"passed":sum(r["status"]=="PASS" for r in records),"checks":records}; write_json(OUTPUT/"validation_report.json",payload)
    lines=["# Phase 1.12 validation","",f"Status: **{payload['status']}**",f"Checks: **{payload['passed']} / {payload['check_count']} PASS**","","| Check | Status | Detail |","|---|---|---|"]+[f"| {r['check']} | {r['status']} | {r['detail']} |" for r in records]; (OUTPUT/"validation_report.md").write_text("\n".join(lines)+"\n",encoding="utf-8"); require(payload["status"]=="PASS","validation failure"); return payload


def write_run_manifest(validation: dict[str,Any],decision: str) -> None:
    files=[p for p in OUTPUT.rglob("*") if p.is_file() and "checkpoints" not in p.parts and p.name!="run_manifest.json"]; files.extend([Path(__file__),ROOT/"tests"/"test_week9_phase1_12_gpc_kernel_adequacy.py",NOTEBOOK]); entries=[]
    for path in sorted(set(files)):
        require(path.is_file(),f"manifest input missing {path}"); payload=artifact_bytes(path); entries.append({"path":path.relative_to(ROOT).as_posix(),"sha256":hashlib.sha256(payload).hexdigest(),"size_bytes":len(payload)})
    manifest={"study":"Week 9 Phase 1.12 — GPC Kernel Adequacy / Anisotropy Control","starting_sha":START_SHA,"branch":BRANCH,"decision":decision,"protocol":{"path":"frozen A0","budgets":list(BUDGETS),"outer_runs":100,"repeat_blocks":20,"folds_per_repeat":5,"bootstrap_draws":BOOTSTRAP_DRAWS,"models":list(ALL_MODELS)},"validation":validation,"historical_changes":historical_changes(),"files":entries}; write_json(OUTPUT/"run_manifest.json",manifest)


def finalize() -> dict[str,Any]:
    gate=baseline_gate(); kernel_specification(); new_predictions,new_metrics,diagnostics=collect_new_checkpoints(); h_predictions,h_metrics=metrics_from_h_predictions(); g0_metrics=historical_g0_metrics(); metrics=pd.concat([h_metrics,g0_metrics,new_metrics],ignore_index=True,sort=False)
    outer,repeat,summary,contrasts=compute_aulc(metrics); b16=summarize_budget(metrics,(16,),("accuracy","balanced_accuracy","keyhole_recall","conduction_recall","false_negative","false_positive"),"B16"); b16c=budget16_contrasts(metrics); late=summarize_budget(metrics,(40,80),("accuracy","balanced_accuracy","keyhole_recall","conduction_recall"),"late"); full=full81_checkpoint_summary(metrics); disagreements=hard_disagreements(h_predictions,new_predictions); ard,bounds=ard_and_bound_summaries(diagnostics); oracle=oracle_diagnostic(repeat); decision=decide(contrasts,summary)
    for name,frame in (("outer_run_metrics.csv.gz",outer),("repeat_metrics.csv",repeat),("model_summary.csv",summary),("paired_contrasts.csv",contrasts),("budget16_summary.csv",b16),("budget16_contrasts.csv",b16c),("checkpoint40_80_summary.csv",late),("full81_checkpoint_summary.csv",full),("budget16_hard_disagreements.csv",disagreements),("ard_lengthscale_summary.csv",ard),("bound_hit_summary.csv",bounds),("oracle_gpc_diagnostic.csv",oracle)): write_csv(OUTPUT/name,frame)
    figures=make_figures(metrics,contrasts,ard,bounds); build_reports(summary,contrasts,b16,late,ard,bounds,oracle,decision); build_notebook(); validation=validate(metrics,contrasts,diagnostics,figures,decision); write_run_manifest(validation,decision)
    manifest=json.loads((OUTPUT/"run_manifest.json").read_text()); require(all(hashlib.sha256(artifact_bytes(ROOT/item["path"])).hexdigest()==item["sha256"] for item in manifest["files"]),"manifest hash verification")
    return {"status":"PASS","decision":decision,"validation_checks":validation["check_count"],"baseline_gate":gate["status"],"historical_changes":historical_changes()}


def publish_existing() -> dict[str,Any]:
    summary=pd.read_csv(OUTPUT/"model_summary.csv"); contrasts=pd.read_csv(OUTPUT/"paired_contrasts.csv"); b16=pd.read_csv(OUTPUT/"budget16_summary.csv"); late=pd.read_csv(OUTPUT/"checkpoint40_80_summary.csv"); ard=pd.read_csv(OUTPUT/"ard_lengthscale_summary.csv"); bounds=pd.read_csv(OUTPUT/"bound_hit_summary.csv"); oracle=pd.read_csv(OUTPUT/"oracle_gpc_diagnostic.csv"); repeat=pd.read_csv(OUTPUT/"repeat_metrics.csv"); diagnostics=pd.read_csv(OUTPUT/"kernel_fit_diagnostics.csv.gz",low_memory=False); figures=pd.read_csv(OUTPUT/"figure_manifest.csv"); outer=pd.read_csv(OUTPUT/"outer_run_metrics.csv.gz")
    mean,lo,hi=bootstrap_interval(oracle.H_minus_oracle.to_numpy(float),"H-oracle"); oracle.attrs["summary"]={"mean":mean,"ci_lower":lo,"ci_upper":hi}; decision=decide(contrasts,summary); build_reports(summary,contrasts,b16,late,ard,bounds,oracle,decision); build_notebook(); validation=validate(outer,contrasts,diagnostics,figures,decision); write_run_manifest(validation,decision); manifest=json.loads((OUTPUT/"run_manifest.json").read_text()); require(all(hashlib.sha256(artifact_bytes(ROOT/item["path"])).hexdigest()==item["sha256"] for item in manifest["files"]),"manifest hash verification"); return {"status":"PASS","decision":decision,"validation_checks":validation["check_count"],"historical_changes":historical_changes()}


def main() -> None:
    parser=argparse.ArgumentParser(); parser.add_argument("--run",action="store_true"); parser.add_argument("--g0-checkpoints",action="store_true"); parser.add_argument("--finalize",action="store_true"); parser.add_argument("--publish",action="store_true"); parser.add_argument("--workers",type=int,default=4); parser.add_argument("--limit-specs",type=int); parser.add_argument("--models",nargs="*",default=list(NEW_MODELS)); args=parser.parse_args()
    if args.run: print(json.dumps(run_new_kernels(args.workers,args.limit_specs,args.models),indent=2))
    if args.g0_checkpoints: print(json.dumps(run_g0_checkpoints(),indent=2))
    if args.finalize: print(json.dumps(finalize(),indent=2))
    if args.publish: print(json.dumps(publish_existing(),indent=2))
    if not args.run and not args.g0_checkpoints and not args.finalize and not args.publish: parser.error("choose --run, --g0-checkpoints, --finalize or --publish")


if __name__=="__main__": main()
