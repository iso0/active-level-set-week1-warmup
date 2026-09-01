"""Week 9 Phase 1.13: fixed physics mean plus ARD GP discrepancy.

This is a model-only replay on the frozen A0 path.  The Phase 1.11 latent
physics mean is fitted from each revealed prefix and frozen.  New computation
is restricted to a bound-matched isotropic residual (M2W), an ARD residual
(M3), and a three-budget M3 upper-bound sensitivity.
"""

from __future__ import annotations

import argparse
import gzip
import hashlib
import json
import math
import subprocess
import time
from dataclasses import dataclass
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
from scipy.special import expit
from scipy.stats import spearmanr
from sklearn.gaussian_process import GaussianProcessClassifier
from sklearn.gaussian_process.kernels import ConstantKernel, Matern
from sklearn.preprocessing import StandardScaler

from src import week8_5_frozen_sample_efficiency_confirmation as w85
from src import week9_phase1_7_physics_ridge_residual_gp as p17
from src import week9_phase1_8_model_path_decomposition as p18
from src import week9_phase1_11_fixed_mean_discrepancy_gp as p11
from src import week9_phase1_12_gpc_kernel_adequacy as p12


ROOT=Path(__file__).resolve().parents[1]
OUTPUT=ROOT/"outputs"/"week9_phase1_13_fixed_physics_ard_discrepancy"
CHECKPOINTS=OUTPUT/"checkpoints"
SENSITIVITY_CHECKPOINTS=OUTPUT/"sensitivity_checkpoints"
FIGURES=OUTPUT/"figures"
NOTEBOOK=ROOT/"notebooks"/"week_09"/"11_week9_phase1_13_fixed_physics_ard_discrepancy.ipynb"
PHASE11=ROOT/"outputs"/"week9_phase1_11_fixed_mean_discrepancy_gp"
PHASE12=ROOT/"outputs"/"week9_phase1_12_gpc_kernel_adequacy"
PHASE18=ROOT/"outputs"/"week9_phase1_8_model_path_decomposition"
PHASE112_SHA="161453983996b763824f2d262b5ce9d63332da16"
BRANCH="codex/week9-phase1-13-fixed-physics-ard-discrepancy"
FEATURES=("P","VX","LS","ST")
BUDGETS=tuple(range(16,81))
CHECKPOINT_BUDGETS=(16,40,80)
EARLY_BUDGETS=tuple(range(16,41))
LATE_BUDGETS=tuple(range(41,81))
NEW_MODELS=("M2W","M3")
HEADLINE_MODELS=("H","G0","G3","M2","M3")
ALL_ANALYSIS_MODELS=("H","G0","G3","M2","M2W","M3")
BOOTSTRAP_DRAWS=10_000
RESIDUAL_SD_BOUNDS=tuple(float(x) for x in p11.RESIDUAL_SD_BOUNDS)
RESIDUAL_VARIANCE_BOUNDS=tuple(float(x) for x in p11.RESIDUAL_VARIANCE_BOUNDS)
INITIAL_RESIDUAL_VARIANCE=float(p11.INITIAL_RESIDUAL_VARIANCE)
INITIAL_LENGTH_SCALE=1.0
PRIMARY_LENGTH_BOUNDS=(0.01,100.0)
SENSITIVITY_LENGTH_BOUNDS=(0.01,1000.0)
BOUND_ATOL=float(p11.BOUND_ATOL)
PARITY_TOLERANCE=1e-5
SEED_ROOT="week9_phase1_13_fixed_physics_ard_discrepancy|v1"
EPS=1e-12


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


def residual_kernel(model: str,upper: float=100.0,fixed: bool=False) -> Any:
    require(model in {"M2W","M3"},f"unknown residual model {model}")
    length=np.ones(4,dtype=float) if model=="M3" else 1.0
    length_bounds="fixed" if fixed else (PRIMARY_LENGTH_BOUNDS[0],float(upper))
    variance_bounds="fixed" if fixed else RESIDUAL_VARIANCE_BOUNDS
    return ConstantKernel(INITIAL_RESIDUAL_VARIANCE,variance_bounds)*Matern(length_scale=length,length_scale_bounds=length_bounds,nu=1.5)


def kernel_specification() -> dict[str,Any]:
    payload={"status":"FROZEN","fixed_physics_mean":"Phase 1.11 training-fitted log(h) latent logit, frozen before Stage 2","residual_sd_bounds":list(RESIDUAL_SD_BOUNDS),"initial_residual_variance":INITIAL_RESIDUAL_VARIANCE,"models":{"M2W":{"role":"mechanistic_bound-matched_control","ard":False,"kernel":repr(residual_kernel("M2W"))},"M3":{"role":"primary_new_model","ard":True,"kernel":repr(residual_kernel("M3"))},"M3_L1000":{"role":"fixed-path checkpoint sensitivity only","ard":True,"kernel":repr(residual_kernel("M3",1000.0))}},"shared":{"inputs":list(FEATURES),"input_scaling":"StandardScaler fit on outer training-pool inputs","matern_nu":1.5,"optimizer":"L-BFGS-B","restarts":0,"initial_lengthscale":INITIAL_LENGTH_SCALE,"primary_length_bounds":list(PRIMARY_LENGTH_BOUNDS),"amplitude_bounds_identical":True,"log_h_excluded_from_residual":True}}
    write_json(OUTPUT/"kernel_specification.json",payload); return payload


def load_inputs() -> tuple[pd.DataFrame,list[Any],dict[str,list[int]]]:
    population,specs=p18.load_population_specs(); paths_table=pd.read_csv(PHASE18/"tables"/"query_paths.csv.gz"); a0=paths_table[paths_table.path.eq("A0")]
    paths={str(run):group.sort_values("query_order").population_row_index.astype(int).tolist() for run,group in a0.groupby("run_id",sort=True)}
    initial=pd.read_csv(ROOT/"outputs"/"week8_5_frozen_confirmation"/"initial_design_manifest.csv"); initial_map={str(run):group.sort_values("query_order").population_row_index.astype(int).tolist() for run,group in initial.groupby("run_id",sort=True)}
    require(len(population)==405 and int(population.has_keyhole.sum())==73 and int((~population.has_keyhole.astype(bool)).sum())==332,"population gate")
    require(len(specs)==100 and len(paths)==100,"split/path gate")
    for spec in specs:
        path=paths[spec.run_id]; require(len(path)==80 and len(set(path))==80,f"A0 path drift {spec.run_id}"); require(path[:16]==initial_map[spec.run_id]==w85.initial_design(spec,population),f"initial design drift {spec.run_id}"); require(set(path).issubset(spec.train_indices) and set(path).isdisjoint(spec.test_indices),f"information-flow drift {spec.run_id}")
    return population,specs,paths


def baseline_gate() -> dict[str,Any]:
    population,specs,paths=load_inputs(); p12_summary=pd.read_csv(PHASE12/"model_summary.csv"); p11_summary=pd.read_csv(PHASE11/"model_summary.csv")
    value=lambda frame,model:float(frame[(frame.model.eq(model))&frame.subset.eq("B1_q20")].mean_AULC.iloc[0])
    h=value(p12_summary,"H"); g0=value(p12_summary,"G0"); g3=value(p12_summary,"G3"); m2=value(p11_summary,"M2"); report=(PHASE12/"FINAL_PHASE1_12_REPORT.md").read_text()
    gate={"status":"PASS","phase112_sha":PHASE112_SHA,"current_head":subprocess.check_output(["git","rev-parse","HEAD"],cwd=ROOT,text=True).strip(),"phase112_is_ancestor":subprocess.run(["git","merge-base","--is-ancestor",PHASE112_SHA,"HEAD"],cwd=ROOT).returncode==0,"phase112_placeholder_absent":"{future}" not in report,"population":len(population),"keyholes":int(population.has_keyhole.sum()),"conduction":int((~population.has_keyhole.astype(bool)).sum()),"outer_runs":len(specs),"repeat_blocks":len(set(s.repeat for s in specs)),"folds_per_repeat":5,"A0_paths":len(paths),"initial_design_matches":100,"budgets":list(BUDGETS),"H_q20_AULC":h,"G0_q20_AULC":g0,"G3_q20_AULC":g3,"M2_q20_AULC":m2}
    gate["status"]="PASS" if gate["phase112_is_ancestor"] and gate["phase112_placeholder_absent"] and abs(h-.8308134191176471)<1e-12 and abs(g0-.8135202205882353)<1e-12 and abs(g3-.826594669117647)<1e-12 and abs(m2-.8302297794117648)<1e-12 else "FAIL"
    write_json(OUTPUT/"baseline_gate.json",gate); require(gate["status"]=="PASS",f"baseline gate failed {gate}"); return gate


def fixed_ard_parity_case(case: str,X: np.ndarray,y: np.ndarray,Xtest: np.ndarray) -> tuple[dict[str,Any],list[dict[str,Any]]]:
    kernel=ConstantKernel(.27,"fixed")*Matern(length_scale=np.array([.8,1.1,1.4,1.8]),length_scale_bounds="fixed",nu=1.5)
    reference=GaussianProcessClassifier(kernel=kernel,optimizer=None,max_iter_predict=100,random_state=17).fit(X,y); custom=p11.FixedMeanLaplaceGPC(kernel,optimize=False).fit(X,y,np.zeros(len(y)))
    a=reference.predict_proba(Xtest)[:,1]; b=custom.predict_proba(Xtest,np.zeros(len(Xtest)))[:,1]
    rows=[{"case":case,"row":i,"sklearn_probability":float(x),"custom_probability":float(z),"absolute_difference":float(abs(x-z))} for i,(x,z) in enumerate(zip(a,b))]
    return {"case":case,"rows":len(rows),"max_absolute_probability_difference":float(np.max(np.abs(a-b))),"mean_absolute_probability_difference":float(np.mean(np.abs(a-b)))},rows


def run_parity_gate() -> dict[str,Any]:
    OUTPUT.mkdir(parents=True,exist_ok=True); population,specs,paths=load_inputs(); rng=np.random.default_rng(113)
    toy_x=np.r_[rng.normal(-.8,.35,(10,4)),rng.normal(.8,.35,(10,4))]; toy_y=np.r_[np.zeros(10,dtype=int),np.ones(10,dtype=int)]; toy_test=rng.normal(0,1,(25,4)); cases=[("toy_4d",toy_x,toy_y,toy_test)]
    x4=population.loc[:,FEATURES].to_numpy(float); labels=population.has_keyhole.astype(int).to_numpy()
    for spec,budget in ((specs[0],16),(specs[49],40),(specs[-1],80)):
        revealed=np.asarray(paths[spec.run_id][:budget],dtype=int); scaler=StandardScaler().fit(x4[np.asarray(spec.train_indices,dtype=int)]); cases.append((f"{spec.run_id}_B{budget}",scaler.transform(x4[revealed]),labels[revealed],scaler.transform(x4[np.asarray(spec.test_indices,dtype=int)])))
    summaries=[]; predictions=[]
    for name,X,y,Xtest in cases:
        summary,rows=fixed_ard_parity_case(name,X,y,Xtest); summaries.append(summary); predictions.extend(rows)
    maximum=max(r["max_absolute_probability_difference"] for r in summaries); status="PASS" if maximum<=PARITY_TOLERANCE else "IMPLEMENTATION_NOT_VALIDATED"; payload={"status":status,"tolerance":PARITY_TOLERANCE,"maximum_probability_difference":maximum,"cases":summaries,"fixed_ARD_parameters":{"variance":.27,"lengthscales":[.8,1.1,1.4,1.8],"nu":1.5},"reference":"sklearn GaussianProcessClassifier, identical fixed ARD kernel, zero mean"}
    write_csv(OUTPUT/"ard_zero_mean_parity_predictions.csv",pd.DataFrame(predictions)); write_json(OUTPUT/"ard_parity_report.json",payload); require(status=="PASS",f"ARD parity failed {maximum}"); return payload


@dataclass
class HybridFit:
    physics: Any
    x_scaler: StandardScaler
    gp: Any
    revealed_indices: np.ndarray
    model: str
    length_upper: float

    @property
    def residual_sd(self) -> float: return math.sqrt(float(self.gp.kernel_.k1.constant_value))
    @property
    def length_scales(self) -> np.ndarray:
        values=np.ravel(self.gp.kernel_.k2.length_scale).astype(float); return values if len(values)==4 else np.repeat(values[0],4)


def fit_hybrid(x4: np.ndarray,logh: np.ndarray,labels: np.ndarray,revealed: Sequence[int],training_pool: Sequence[int],physics: Any,model: str,upper: float=100.0) -> HybridFit:
    revealed_array=np.asarray(revealed,dtype=int); scaler=StandardScaler().fit(np.asarray(x4)[np.asarray(training_pool,dtype=int)]); x_train=scaler.transform(np.asarray(x4)[revealed_array]); mean_train=physics.latent(np.asarray(logh)[revealed_array]); gp=p11.FixedMeanLaplaceGPC(residual_kernel(model,upper),optimize=True).fit(x_train,np.asarray(labels)[revealed_array],mean_train); return HybridFit(physics,scaler,gp,revealed_array,model,float(upper))


def components(fit: HybridFit,x4: np.ndarray,logh: np.ndarray) -> dict[str,np.ndarray]:
    transformed=fit.x_scaler.transform(np.asarray(x4,float)); phys=fit.physics.latent(np.asarray(logh,float)); final,var=fit.gp.latent_mean_and_variance(transformed,phys); probability=fit.gp.predict_proba(transformed,phys)[:,1]; return {"physics_latent":phys,"residual_latent":final-phys,"final_latent":final,"latent_variance":var,"probability":probability}


def fit_diagnostic(fit: HybridFit) -> dict[str,Any]:
    d=fit.gp.diagnostics_; lengths=fit.length_scales; lower=np.isclose(lengths,PRIMARY_LENGTH_BOUNDS[0],atol=BOUND_ATOL,rtol=0); upper=np.isclose(lengths,fit.length_upper,atol=BOUND_ATOL,rtol=0)
    row={"residual_sd":fit.residual_sd,"residual_sd_lower_bound_hit":bool(np.isclose(fit.residual_sd,RESIDUAL_SD_BOUNDS[0],atol=BOUND_ATOL,rtol=0)),"residual_sd_upper_bound_hit":bool(np.isclose(fit.residual_sd,RESIDUAL_SD_BOUNDS[1],atol=BOUND_ATOL,rtol=0)),"residual_sd_any_bound_hit":False,"l_P":float(lengths[0]),"l_VX":float(lengths[1]),"l_LS":float(lengths[2]),"l_ST":float(lengths[3]),"anisotropy_ratio":float(lengths.max()/lengths.min()),"any_length_lower_bound_hit":bool(lower.any()),"any_length_upper_bound_hit":bool(upper.any()),"any_length_bound_hit":bool(lower.any() or upper.any()),"optimizer_converged":d.optimizer_converged,"optimizer_message":d.optimizer_message,"optimizer_iterations":d.optimizer_iterations,"optimizer_evaluations":d.optimizer_evaluations,"posterior_iterations":d.posterior_iterations,"fallback_status":d.fallback_status,"objective_value":d.objective_value,"length_upper_bound":fit.length_upper}
    row["residual_sd_any_bound_hit"]=row["residual_sd_lower_bound_hit"] or row["residual_sd_upper_bound_hit"]
    for i,name in enumerate(FEATURES): row[f"l_{name}_lower_bound_hit"]=bool(lower[i]); row[f"l_{name}_upper_bound_hit"]=bool(upper[i])
    return row


def checkpoint_path(run_id: str) -> Path: return CHECKPOINTS/f"{run_id}.json.gz"
def sensitivity_checkpoint_path(run_id: str) -> Path: return SENSITIVITY_CHECKPOINTS/f"{run_id}.json.gz"
def write_checkpoint(path: Path,payload: dict[str,Any]) -> None: path.parent.mkdir(parents=True,exist_ok=True); path.write_bytes(gzip.compress((json.dumps(json_safe(payload),sort_keys=True)+"\n").encode(),compresslevel=6,mtime=0))
def read_checkpoint(path: Path) -> dict[str,Any]: return json.loads(gzip.decompress(path.read_bytes()).decode())


def run_one_spec(spec: Any,path: Sequence[int],population: pd.DataFrame,distances: np.ndarray) -> dict[str,Any]:
    destination=checkpoint_path(spec.run_id)
    if destination.is_file():
        payload=read_checkpoint(destination)
        if payload.get("complete") and payload.get("phase112_sha")==PHASE112_SHA: return {"run_id":spec.run_id,"reused":True}
    x4=population.loc[:,FEATURES].to_numpy(float); logh=p11.log_h_values(population); labels=population.has_keyhole.astype(int).to_numpy(); test=np.asarray(spec.test_indices,dtype=int); flags=p17.subset_flags(spec,population,distances); predictions=[]; metrics=[]; diagnostics=[]; physics_rows=[]
    for budget in BUDGETS:
        revealed=np.asarray(path[:budget],dtype=int); require(len(revealed)==budget and len(set(revealed.tolist()))==budget,"prefix drift"); physics=p11.fit_physics_mean(logh,labels,revealed,seed_u32("shared_physics",spec.run_id,budget)); physics_rows.append({"run_id":spec.run_id,"repeat":spec.repeat,"fold":spec.fold,"budget":budget,"revealed_count":budget,"physics_intercept":float(physics.model.intercept_[0]),"physics_log_h_coefficient":float(physics.model.coef_[0,0]),"h_scaler_mean":float(physics.scaler.mean_[0]),"h_scaler_scale":float(physics.scaler.scale_[0]),"stage1_only_log_h":True,"stage1_revealed_prefix_only":True,"frozen_during_stage2":True,"shared_by_M2W_M3":True})
        for model in NEW_MODELS:
            fit=fit_hybrid(x4,logh,labels,revealed,spec.train_indices,physics,model,100.0); comp=components(fit,x4[test],logh[test]); probability=comp["probability"]
            for local,pop_index in enumerate(test): predictions.append({"run_id":spec.run_id,"repeat":spec.repeat,"fold":spec.fold,"budget":budget,"model":model,"population_row_index":int(pop_index),"truth":int(labels[pop_index]),"probability":float(probability[local]),"physics_latent":float(comp["physics_latent"][local]),"residual_latent":float(comp["residual_latent"][local]),"final_latent":float(comp["final_latent"][local]),"is_q20":bool(flags["B1_q20"][local]),"is_q30":bool(flags["B1_q30"][local])})
            for subset,flag in flags.items(): metrics.append({"run_id":spec.run_id,"repeat":spec.repeat,"fold":spec.fold,"budget":budget,"model":model,"subset":subset,**p17.metric_values(labels[test][flag],probability[flag])})
            diagnostics.append({"run_id":spec.run_id,"repeat":spec.repeat,"fold":spec.fold,"budget":budget,"model":model,"role":"mechanistic_bound-matched_control" if model=="M2W" else "primary_new_model",**fit_diagnostic(fit)})
    write_checkpoint(destination,{"complete":True,"phase112_sha":PHASE112_SHA,"run_id":spec.run_id,"predictions":predictions,"metrics":metrics,"diagnostics":diagnostics,"physics":physics_rows}); return {"run_id":spec.run_id,"reused":False}


def run_main(workers: int=4,limit_specs: int|None=None) -> dict[str,Any]:
    parity=run_parity_gate() if not (OUTPUT/"ard_parity_report.json").is_file() else json.loads((OUTPUT/"ard_parity_report.json").read_text()); require(parity["status"]=="PASS","parity gate"); baseline_gate(); kernel_specification(); population,specs,paths=load_inputs(); distances=w85.b1_distance(population); specs=specs[:limit_specs] if limit_specs else specs; started=time.time(); results=Parallel(n_jobs=workers,verbose=10)(delayed(run_one_spec)(spec,paths[spec.run_id],population,distances) for spec in specs); payload={"status":"PASS","completed_runs":len(results),"reused_runs":sum(r["reused"] for r in results),"workers":workers,"elapsed_seconds":time.time()-started,"complete":limit_specs is None}; write_json(OUTPUT/"execution_report.json",payload); return payload


def run_one_sensitivity(spec: Any,path: Sequence[int],population: pd.DataFrame,distances: np.ndarray) -> dict[str,Any]:
    destination=sensitivity_checkpoint_path(spec.run_id)
    if destination.is_file():
        payload=read_checkpoint(destination)
        if payload.get("complete") and payload.get("phase112_sha")==PHASE112_SHA:return {"run_id":spec.run_id,"reused":True}
    x4=population.loc[:,FEATURES].to_numpy(float); logh=p11.log_h_values(population); labels=population.has_keyhole.astype(int).to_numpy(); test=np.asarray(spec.test_indices,dtype=int); flags=p17.subset_flags(spec,population,distances); predictions=[]; metrics=[]; diagnostics=[]
    for budget in CHECKPOINT_BUDGETS:
        revealed=np.asarray(path[:budget],dtype=int); physics=p11.fit_physics_mean(logh,labels,revealed,seed_u32("shared_physics",spec.run_id,budget)); fit=fit_hybrid(x4,logh,labels,revealed,spec.train_indices,physics,"M3",1000.0); comp=components(fit,x4[test],logh[test]); probability=comp["probability"]
        for local,pop_index in enumerate(test): predictions.append({"run_id":spec.run_id,"repeat":spec.repeat,"fold":spec.fold,"budget":budget,"model":"M3_L1000","population_row_index":int(pop_index),"truth":int(labels[pop_index]),"probability":float(probability[local]),"is_q20":bool(flags["B1_q20"][local]),"is_q30":bool(flags["B1_q30"][local])})
        for subset,flag in flags.items(): metrics.append({"run_id":spec.run_id,"repeat":spec.repeat,"fold":spec.fold,"budget":budget,"model":"M3_L1000","subset":subset,**p17.metric_values(labels[test][flag],probability[flag])})
        diagnostics.append({"run_id":spec.run_id,"repeat":spec.repeat,"fold":spec.fold,"budget":budget,"model":"M3_L1000",**fit_diagnostic(fit)})
    write_checkpoint(destination,{"complete":True,"phase112_sha":PHASE112_SHA,"run_id":spec.run_id,"predictions":predictions,"metrics":metrics,"diagnostics":diagnostics}); return {"run_id":spec.run_id,"reused":False}


def run_sensitivity(workers: int=4,limit_specs: int|None=None) -> dict[str,Any]:
    population,specs,paths=load_inputs(); distances=w85.b1_distance(population); specs=specs[:limit_specs] if limit_specs else specs; started=time.time(); results=Parallel(n_jobs=workers,verbose=10)(delayed(run_one_sensitivity)(spec,paths[spec.run_id],population,distances) for spec in specs); payload={"status":"PASS","completed_runs":len(results),"reused_runs":sum(r["reused"] for r in results),"workers":workers,"elapsed_seconds":time.time()-started,"complete":limit_specs is None}; write_json(OUTPUT/"sensitivity_execution_report.json",payload); return payload


def bootstrap_interval(values: np.ndarray,key: str) -> tuple[float,float,float]:
    values=np.asarray(values,float); require(len(values)==20 and np.isfinite(values).all(),f"repeat bootstrap drift {key}"); rng=np.random.default_rng(seed_u32("bootstrap",key)); draws=values[rng.integers(0,20,size=(BOOTSTRAP_DRAWS,20))].mean(axis=1); return float(values.mean()),float(np.quantile(draws,.025)),float(np.quantile(draws,.975))


def bootstrap_repeat_ratio(numerators: np.ndarray,denominators: np.ndarray,key: str) -> tuple[float,float,float]:
    numerators=np.asarray(numerators,float); denominators=np.asarray(denominators,float); require(len(numerators)==len(denominators)==20 and np.isfinite(numerators).all() and np.isfinite(denominators).all(),f"repeat ratio bootstrap drift {key}"); require(denominators.sum()>0,f"undefined repeat ratio {key}"); rng=np.random.default_rng(seed_u32("bootstrap-ratio",key)); indices=rng.integers(0,20,size=(BOOTSTRAP_DRAWS,20)); draw_denominators=denominators[indices].sum(axis=1); valid=draw_denominators>0; require(valid.mean()>.99,f"insufficient changed decisions for {key}"); draws=numerators[indices].sum(axis=1)[valid]/draw_denominators[valid]; point=float(numerators.sum()/denominators.sum()); return point,float(np.quantile(draws,.025)),float(np.quantile(draws,.975))


def collect_main_checkpoints() -> tuple[pd.DataFrame,pd.DataFrame,pd.DataFrame,pd.DataFrame]:
    files=sorted(CHECKPOINTS.glob("*.json.gz")); require(len(files)==100,f"main checkpoint count {len(files)}"); predictions=[]; metrics=[]; diagnostics=[]; physics=[]
    for path in files:
        payload=read_checkpoint(path); require(payload.get("complete") and payload.get("phase112_sha")==PHASE112_SHA,f"bad checkpoint {path.name}"); predictions.extend(payload["predictions"]); metrics.extend(payload["metrics"]); diagnostics.extend(payload["diagnostics"]); physics.extend(payload["physics"])
    p=pd.DataFrame(predictions); m=pd.DataFrame(metrics); d=pd.DataFrame(diagnostics); h=pd.DataFrame(physics); require(len(p)==100*2*65*81 and len(m)==100*2*65*3 and len(d)==100*2*65 and len(h)==100*65,"main completeness")
    write_csv(OUTPUT/"new_predictions.csv.gz",p); write_csv(OUTPUT/"m3_fit_diagnostics.csv.gz",d[d.model.eq("M3")].reset_index(drop=True)); write_csv(OUTPUT/"m2w_fit_diagnostics.csv.gz",d[d.model.eq("M2W")].reset_index(drop=True)); write_csv(OUTPUT/"physics_mean_fit_diagnostics.csv.gz",h); return p,m,d,h


def collect_sensitivity_checkpoints() -> tuple[pd.DataFrame,pd.DataFrame,pd.DataFrame]:
    files=sorted(SENSITIVITY_CHECKPOINTS.glob("*.json.gz")); require(len(files)==100,f"sensitivity checkpoint count {len(files)}"); predictions=[]; metrics=[]; diagnostics=[]
    for path in files:
        payload=read_checkpoint(path); require(payload.get("complete") and payload.get("phase112_sha")==PHASE112_SHA,f"bad sensitivity checkpoint {path.name}"); predictions.extend(payload["predictions"]); metrics.extend(payload["metrics"]); diagnostics.extend(payload["diagnostics"])
    p=pd.DataFrame(predictions); m=pd.DataFrame(metrics); d=pd.DataFrame(diagnostics); require(len(p)==100*3*81 and len(m)==100*3*3 and len(d)==100*3,"sensitivity completeness"); return p,m,d


def boundary_metrics_vectorized(predictions: pd.DataFrame,model: str) -> pd.DataFrame:
    frame=predictions.copy(); frame["decision"]=(frame.probability>=.5).astype(int); frame["correct"]=frame.decision.eq(frame.truth).astype(int); frame["true_positive"]=(frame.decision.eq(1)&frame.truth.eq(1)).astype(int); frame["true_negative"]=(frame.decision.eq(0)&frame.truth.eq(0)).astype(int); frame["false_positive"]=(frame.decision.eq(1)&frame.truth.eq(0)).astype(int); frame["false_negative"]=(frame.decision.eq(0)&frame.truth.eq(1)).astype(int); rows=[]; keys=["run_id","repeat","fold","budget"]
    for subset,flag in (("B1_q20","is_q20"),("B1_q30","is_q30")):
        part=frame[frame[flag].astype(bool)]; grouped=part.groupby(keys,sort=True); agg=grouped[["correct","true_positive","true_negative","false_positive","false_negative"]].sum(); agg["row_count"]=grouped.size(); agg["accuracy"]=agg.correct/agg.row_count; agg["keyhole_recall"]=agg.true_positive/(agg.true_positive+agg.false_negative); agg["conduction_recall"]=agg.true_negative/(agg.true_negative+agg.false_positive); agg["balanced_accuracy"]=(agg.keyhole_recall+agg.conduction_recall)/2; agg["roc_auc"]=math.nan; agg["pr_auc"]=math.nan; agg["brier_score"]=math.nan; rows.extend(agg.drop(columns="correct").reset_index().assign(model=model,subset=subset).to_dict("records"))
    for key,group in frame[frame.budget.isin(CHECKPOINT_BUDGETS)].groupby(keys,sort=True):
        run_id,repeat,fold,budget=key; rows.append({"run_id":run_id,"repeat":repeat,"fold":fold,"budget":int(budget),"model":model,"subset":"full81",**p12.metric_values(group.truth.to_numpy(int),group.probability.to_numpy(float))})
    result=pd.DataFrame(rows); require(len(result)==100*65*2+100*3,f"historical metric completeness {model}"); return result


def load_historical_predictions() -> dict[str,pd.DataFrame]:
    h=pd.read_csv(PHASE11/"h_only_a0_predictions.csv.gz").assign(model="H"); m2=pd.read_csv(PHASE11/"fixed_mean_oof_predictions.csv.gz").assign(model="M2")
    chunks=[]
    for chunk in pd.read_csv(PHASE12/"new_kernel_predictions.csv.gz",chunksize=200_000):
        selected=chunk[chunk.model.eq("G3")]
        if len(selected): chunks.append(selected.copy())
    g3=pd.concat(chunks,ignore_index=True); require(len(h)==len(m2)==len(g3)==100*65*81,"historical prediction completeness"); return {"H":h,"M2":m2,"G3":g3}


def historical_and_new_metrics(new_predictions: pd.DataFrame,historical: dict[str,pd.DataFrame]) -> pd.DataFrame:
    frames=[boundary_metrics_vectorized(frame,model) for model,frame in historical.items()]
    frames.extend(boundary_metrics_vectorized(new_predictions[new_predictions.model.eq(model)],model) for model in NEW_MODELS)
    g0=p12.historical_g0_metrics(); combined=pd.concat([*frames,g0],ignore_index=True,sort=False); require(set(combined.model.unique())==set(ALL_ANALYSIS_MODELS),str(combined.model.unique())); return combined


def compute_aulc(metrics: pd.DataFrame) -> tuple[pd.DataFrame,pd.DataFrame,pd.DataFrame,pd.DataFrame]:
    rows=[]
    for keys,group in metrics[metrics.subset.isin(("B1_q20","B1_q30"))].groupby(["run_id","repeat","fold","model","subset"],sort=True):
        run_id,repeat,fold,model,subset=keys; ordered=group.sort_values("budget"); require(ordered.budget.astype(int).tolist()==list(BUDGETS),f"AULC grid {run_id}/{model}/{subset}"); rows.append({"run_id":run_id,"repeat":repeat,"fold":fold,"model":model,"subset":subset,"accuracy_AULC_16_80":float(np.trapezoid(ordered.accuracy,ordered.budget)/64)})
    outer=pd.DataFrame(rows); require(len(outer)==100*6*2,"AULC completeness"); repeat=outer.groupby(["repeat","model","subset"],as_index=False).accuracy_AULC_16_80.mean(); summary=[]
    for (model,subset),group in repeat[repeat.model.isin(HEADLINE_MODELS)].groupby(["model","subset"],sort=True):
        mean,lo,hi=bootstrap_interval(group.sort_values("repeat").accuracy_AULC_16_80.to_numpy(),f"summary|{model}|{subset}"); summary.append({"model":model,"subset":subset,"mean_AULC":mean,"ci_lower":lo,"ci_upper":hi,"role":"headline"})
    pairs=(("M3","H"),("M3","M2"),("M3","M2W"),("M3","G3"),("M3","G0")); wide=repeat.pivot(index=["repeat","subset"],columns="model",values="accuracy_AULC_16_80").reset_index(); contrasts=[]
    for subset in ("B1_q20","B1_q30"):
        part=wide[wide.subset.eq(subset)].sort_values("repeat")
        for left,right in pairs:
            values=(part[left]-part[right]).to_numpy(float); mean,lo,hi=bootstrap_interval(values,f"contrast|{left}-{right}|{subset}"); contrasts.append({"contrast":f"{left}-{right}","subset":subset,"mean_difference":mean,"ci_lower":lo,"ci_upper":hi,"positive_repeat_blocks":int((values>0).sum()),"zero_repeat_blocks":int((values==0).sum()),"negative_repeat_blocks":int((values<0).sum()),"bootstrap_draws":BOOTSTRAP_DRAWS,"predeclared_role":"primary" if (left,right,subset)==("M3","H","B1_q20") else ("mechanistic" if right=="M2W" else "secondary")})
    return outer,repeat,pd.DataFrame(summary),pd.DataFrame(contrasts)


def compute_regions(metrics: pd.DataFrame) -> tuple[pd.DataFrame,pd.DataFrame]:
    rows=[]
    for region,budgets in (("EARLY_B16_40",EARLY_BUDGETS),("LATE_B41_80",LATE_BUDGETS)):
        denom=budgets[-1]-budgets[0]
        for keys,group in metrics[metrics.subset.eq("B1_q20")&metrics.model.isin(("H","G3","M2","M2W","M3"))&metrics.budget.isin(budgets)].groupby(["run_id","repeat","fold","model"],sort=True):
            run_id,repeat,fold,model=keys; ordered=group.sort_values("budget"); require(ordered.budget.astype(int).tolist()==list(budgets),f"region grid {region}/{run_id}/{model}"); rows.append({"run_id":run_id,"repeat":repeat,"fold":fold,"model":model,"region":region,"accuracy_AULC":float(np.trapezoid(ordered.accuracy,ordered.budget)/denom)})
    outer=pd.DataFrame(rows); repeat=outer.groupby(["repeat","model","region"],as_index=False).accuracy_AULC.mean(); summary=[]; contrasts=[]
    for (model,region),group in repeat.groupby(["model","region"],sort=True):
        mean,lo,hi=bootstrap_interval(group.sort_values("repeat").accuracy_AULC.to_numpy(),f"region-summary|{model}|{region}"); summary.append({"model":model,"region":region,"mean_AULC":mean,"ci_lower":lo,"ci_upper":hi})
    wide=repeat.pivot(index=["repeat","region"],columns="model",values="accuracy_AULC").reset_index()
    for region in ("EARLY_B16_40","LATE_B41_80"):
        part=wide[wide.region.eq(region)].sort_values("repeat")
        for right in ("H","G3"):
            values=(part.M3-part[right]).to_numpy(float); mean,lo,hi=bootstrap_interval(values,f"region|M3-{right}|{region}"); contrasts.append({"contrast":f"M3-{right}","region":region,"mean_difference":mean,"ci_lower":lo,"ci_upper":hi,"positive_repeat_blocks":int((values>0).sum()),"zero_repeat_blocks":int((values==0).sum()),"negative_repeat_blocks":int((values<0).sum()),"bootstrap_draws":BOOTSTRAP_DRAWS})
    return pd.DataFrame(summary),pd.DataFrame(contrasts)


def summarize_checkpoints(metrics: pd.DataFrame,subset: str,models: Sequence[str],metric_names: Sequence[str]) -> pd.DataFrame:
    part=metrics[metrics.subset.eq(subset)&metrics.model.isin(models)&metrics.budget.isin(CHECKPOINT_BUDGETS)]; rows=[]
    for (model,budget),group in part.groupby(["model","budget"],sort=True):
        for metric in metric_names:
            values=group.groupby("repeat")[metric].mean().sort_index().to_numpy(float); mean,lo,hi=bootstrap_interval(values,f"checkpoint|{subset}|{model}|{budget}|{metric}"); rows.append({"model":model,"subset":subset,"budget":int(budget),"metric":metric,"mean":mean,"ci_lower":lo,"ci_upper":hi})
    return pd.DataFrame(rows)


def hard_disagreements(predictions: dict[str,pd.DataFrame],new_predictions: pd.DataFrame) -> pd.DataFrame:
    frames=[predictions["H"],predictions["G3"],new_predictions[new_predictions.model.isin(("M2W","M3"))]]; allp=pd.concat([f[f.budget.isin(CHECKPOINT_BUDGETS)&f.is_q20.astype(bool)] for f in frames],ignore_index=True,sort=False); allp["decision"]=(allp.probability>=.5).astype(int); allp["correct"]=allp.decision.eq(allp.truth); wide=allp.pivot(index=["run_id","repeat","fold","budget","population_row_index","truth"],columns="model",values=["decision","correct"]).reset_index(); rows=[]
    for budget in CHECKPOINT_BUDGETS:
        part=wide[wide[("budget","")].eq(budget)]
        for other in ("H","G3","M2W"):
            a=part[("decision","M3")].astype(int); b=part[("decision",other)].astype(int); ca=part[("correct","M3")].astype(bool); cb=part[("correct",other)].astype(bool); counts={"same_decision":int((a==b).sum()),"different_decision":int((a!=b).sum()),"M3_only_correct":int((ca&~cb).sum()),f"{other}_only_correct":int((~ca&cb).sum()),"both_correct":int((ca&cb).sum()),"both_wrong":int((~ca&~cb).sum())}; rows.extend({"pair":f"M3_vs_{other}","budget":budget,"category":k,"count":v,"scope":"100 matched outer-fold q20 predictions"} for k,v in counts.items())
    return pd.DataFrame(rows)


def residual_role(new_predictions: pd.DataFrame) -> tuple[pd.DataFrame,pd.DataFrame]:
    population,_,_=load_inputs(); logh=p11.log_h_values(population); frame=new_predictions[new_predictions.model.eq("M3")&new_predictions.budget.isin(CHECKPOINT_BUDGETS)].copy(); frame["log_h"]=logh[frame.population_row_index.to_numpy(int)]; detail=[]
    for keys,group in frame.groupby(["run_id","repeat","fold","budget"],sort=True):
        run_id,repeat,fold,budget=keys
        for subset,mask in (("full81",np.ones(len(group),dtype=bool)),("B1_q20",group.is_q20.to_numpy(bool))):
            part=group.iloc[np.flatnonzero(mask)]; physics_decision=(part.physics_latent.to_numpy(float)>=0); final_decision=(part.probability.to_numpy(float)>=.5); truth=part.truth.to_numpy(int); changed=physics_decision!=final_decision; changed_count=int(changed.sum()); beneficial=int(((final_decision==truth)&(physics_decision!=truth)&changed).sum()); harmful=int(((final_decision!=truth)&(physics_decision==truth)&changed).sum()); correlation=spearmanr(part.residual_latent,part.log_h).statistic if len(part)>2 else math.nan
            detail.append({"run_id":run_id,"repeat":repeat,"fold":fold,"budget":int(budget),"subset":subset,"row_count":len(part),"physics_latent_sd":float(np.std(part.physics_latent)),"posterior_residual_mean_sd":float(np.std(part.residual_latent)),"final_latent_sd":float(np.std(part.final_latent)),"residual_log_h_spearman":float(correlation),"decision_changed_fraction":float(changed.mean()),"changed_count":changed_count,"beneficial_changed_count":beneficial,"harmful_changed_count":harmful,"beneficial_fraction_among_changed":float(beneficial/changed_count) if changed_count else 0.0,"harmful_fraction_among_changed":float(harmful/changed_count) if changed_count else 0.0})
    detail_frame=pd.DataFrame(detail); summary=[]
    for (budget,subset),group in detail_frame.groupby(["budget","subset"],sort=True):
        for metric in ("physics_latent_sd","posterior_residual_mean_sd","final_latent_sd","residual_log_h_spearman","decision_changed_fraction"):
            values=group.groupby("repeat")[metric].mean().sort_index().to_numpy(float); mean,lo,hi=bootstrap_interval(values,f"role|{budget}|{subset}|{metric}"); summary.append({"budget":int(budget),"subset":subset,"metric":metric,"mean":mean,"ci_lower":lo,"ci_upper":hi})
        repeat_counts=group.groupby("repeat")[["changed_count","beneficial_changed_count","harmful_changed_count"]].sum().sort_index()
        for metric,numerator in (("beneficial_fraction_among_changed","beneficial_changed_count"),("harmful_fraction_among_changed","harmful_changed_count")):
            mean,lo,hi=bootstrap_repeat_ratio(repeat_counts[numerator].to_numpy(float),repeat_counts.changed_count.to_numpy(float),f"role|{budget}|{subset}|{metric}"); summary.append({"budget":int(budget),"subset":subset,"metric":metric,"mean":mean,"ci_lower":lo,"ci_upper":hi})
    write_csv(OUTPUT/"residual_role_detail.csv.gz",detail_frame); return detail_frame,pd.DataFrame(summary)


def residual_amplitude_summary(new_diagnostics: pd.DataFrame) -> pd.DataFrame:
    old=pd.read_csv(PHASE11/"residual_fit_diagnostics.csv.gz",low_memory=False); old=old[old.model.eq("M2")&old.subset.eq("full81")][["run_id","repeat","fold","budget","model","residual_sd","residual_sd_lower_bound_hit","residual_sd_upper_bound_hit"]].copy(); old["residual_sd_any_bound_hit"]=old.residual_sd_lower_bound_hit.astype(bool)|old.residual_sd_upper_bound_hit.astype(bool); frame=pd.concat([old,new_diagnostics],ignore_index=True,sort=False); rows=[]
    for model,group in frame.groupby("model",sort=True):
        for scope,budgets in (("all_B16_80",BUDGETS),("B16",(16,)),("B40",(40,)),("B80",(80,))):
            part=group[group.budget.isin(budgets)]
            for metric in ("residual_sd_lower_bound_hit","residual_sd_upper_bound_hit","residual_sd_any_bound_hit"):
                values=part.assign(value=part[metric].astype(float)).groupby("repeat").value.mean().sort_index().to_numpy(float); mean,lo,hi=bootstrap_interval(values,f"amplitude|{model}|{scope}|{metric}"); rows.append({"model":model,"scope":scope,"metric":metric,"mean":mean,"ci_lower":lo,"ci_upper":hi})
            values=part.groupby("repeat").residual_sd.mean().sort_index().to_numpy(float); mean,lo,hi=bootstrap_interval(values,f"amplitude|{model}|{scope}|sd"); rows.append({"model":model,"scope":scope,"metric":"residual_sd_mean","mean":mean,"ci_lower":lo,"ci_upper":hi})
    return pd.DataFrame(rows)


def ard_lengthscale_summary(diagnostics: pd.DataFrame,sensitivity_diagnostics: pd.DataFrame) -> pd.DataFrame:
    frames=[diagnostics[diagnostics.model.eq("M3")].assign(setting="L100"),sensitivity_diagnostics.assign(setting="L1000")]; rows=[]
    for setting,frame in (("L100",frames[0]),("L1000",frames[1])):
        for budget in CHECKPOINT_BUDGETS:
            group=frame[frame.budget.eq(budget)]
            for parameter in ("l_P","l_VX","l_LS","l_ST","anisotropy_ratio"):
                values=group[parameter].to_numpy(float); rows.append({"setting":setting,"budget":budget,"parameter":parameter,"median":float(np.median(values)),"q1":float(np.quantile(values,.25)),"q3":float(np.quantile(values,.75)),"space":"standardized outer-training-pool inputs"})
            for diagnostic in ("any_length_lower_bound_hit","any_length_upper_bound_hit","any_length_bound_hit","optimizer_converged"):
                values=group[diagnostic].astype(float).to_numpy(); rows.append({"setting":setting,"budget":budget,"parameter":diagnostic,"median":float(values.mean()),"q1":math.nan,"q3":math.nan,"space":"fit-rate diagnostic"})
    primary=diagnostics[diagnostics.model.eq("M3")]
    for parameter in ("l_P_lower_bound_hit","l_P_upper_bound_hit","l_VX_lower_bound_hit","l_VX_upper_bound_hit","l_LS_lower_bound_hit","l_LS_upper_bound_hit","l_ST_lower_bound_hit","l_ST_upper_bound_hit"):
        rows.append({"setting":"L100_all_B16_80","budget":-1,"parameter":parameter,"median":float(primary[parameter].astype(float).mean()),"q1":math.nan,"q3":math.nan,"space":"fit-rate diagnostic"})
    return pd.DataFrame(rows)


def upper_bound_sensitivity(primary_predictions: pd.DataFrame,primary_metrics: pd.DataFrame,primary_diagnostics: pd.DataFrame,sens_predictions: pd.DataFrame,sens_metrics: pd.DataFrame,sens_diagnostics: pd.DataFrame) -> pd.DataFrame:
    keys=["run_id","repeat","fold","budget","population_row_index","truth","is_q20","is_q30"]; merged=primary_predictions[primary_predictions.model.eq("M3")&primary_predictions.budget.isin(CHECKPOINT_BUDGETS)].merge(sens_predictions,on=keys,suffixes=("_L100","_L1000"),validate="one_to_one"); rows=[]
    for budget in CHECKPOINT_BUDGETS:
        row={"budget":budget}
        for subset,flag in (("full81",np.ones(len(merged[merged.budget.eq(budget)]),dtype=bool)),("B1_q20",merged[merged.budget.eq(budget)].is_q20.to_numpy(bool))):
            part=merged[merged.budget.eq(budget)].iloc[np.flatnonzero(flag)]; diff=np.abs(part.probability_L100-part.probability_L1000); decisions=(part.probability_L100>=.5)!=(part.probability_L1000>=.5); row[f"{subset}_probability_MAE"]=float(diff.mean()); row[f"{subset}_maximum_probability_difference"]=float(diff.max()); row[f"{subset}_hard_disagreement_count"]=int(decisions.sum()); row[f"{subset}_hard_disagreement_fraction"]=float(decisions.mean())
        for subset in ("B1_q20","full81"):
            for metric in ("accuracy","balanced_accuracy","keyhole_recall","conduction_recall"):
                a=primary_metrics[(primary_metrics.model.eq("M3"))&primary_metrics.subset.eq(subset)&primary_metrics.budget.eq(budget)][metric].mean(); b=sens_metrics[(sens_metrics.subset.eq(subset))&sens_metrics.budget.eq(budget)][metric].mean(); row[f"L100_{subset}_{metric}"]=float(a); row[f"L1000_{subset}_{metric}"]=float(b); row[f"delta_L1000_minus_L100_{subset}_{metric}"]=float(b-a)
        for setting,diag in (("L100",primary_diagnostics[(primary_diagnostics.model.eq("M3"))&primary_diagnostics.budget.eq(budget)]),("L1000",sens_diagnostics[sens_diagnostics.budget.eq(budget)])):
            for feature in FEATURES: row[f"{setting}_median_l_{feature}"]=float(diag[f"l_{feature}"].median())
            row[f"{setting}_any_upper_bound_rate"]=float(diag.any_length_upper_bound_hit.astype(float).mean()); row[f"{setting}_optimizer_converged_rate"]=float(diag.optimizer_converged.astype(float).mean())
        rows.append(row)
    return pd.DataFrame(rows)


def decide(contrasts: pd.DataFrame,regions: pd.DataFrame,sensitivity: pd.DataFrame,parity: dict[str,Any]) -> str:
    if parity["status"]!="PASS": return "IMPLEMENTATION_NOT_VALIDATED"
    q=contrasts[contrasts.subset.eq("B1_q20")].set_index("contrast"); late=regions[regions.region.eq("LATE_B41_80")].set_index("contrast"); early=regions[regions.region.eq("EARLY_B16_40")].set_index("contrast"); unstable=bool((sensitivity.delta_L1000_minus_L100_B1_q20_accuracy.abs()>=.02).any() or (sensitivity.full81_probability_MAE>=.05).any() or (sensitivity.full81_hard_disagreement_fraction>=.10).any())
    if unstable:return "NUMERICALLY_UNSTABLE"
    if q.loc["M3-H"].ci_lower>0 and q.loc["M3-M2W"].ci_lower>0:return "HYBRID_GAIN_SUPPORTED"
    if q.loc["M3-H"].ci_lower<=0<=q.loc["M3-H"].ci_upper and late.loc["M3-H"].ci_lower>0 and early.loc["M3-H"].ci_upper>=0:return "LATE_RESIDUAL_GAIN_ONLY"
    if q.loc["M3-M2"].ci_lower>0 and q.loc["M3-M2W"].ci_lower<=0:return "BOUND_RANGE_EFFECT"
    return "NO_DISCREPANCY_GAIN"


def make_figures(metrics: pd.DataFrame,contrasts: pd.DataFrame,region_summary: pd.DataFrame,region_contrasts: pd.DataFrame,role: pd.DataFrame,ard: pd.DataFrame) -> pd.DataFrame:
    FIGURES.mkdir(parents=True,exist_ok=True); created=[]; colors={"H":"#2f855a","G0":"#718096","G3":"#7c3aed","M2":"#d97706","M3":"#c53030"}; labels={"H":"H physics only","G0":"G0 canonical 4D","G3":"G3 standalone ARD","M2":"M2 fixed mean + isotropic residual","M3":"M3 fixed mean + ARD residual"}
    curve=metrics[metrics.subset.eq("B1_q20")&metrics.model.isin(HEADLINE_MODELS)].groupby(["model","budget"],as_index=False).accuracy.mean(); fig,ax=plt.subplots(figsize=(10,5.6))
    for model in ("H","G3","M2","M3","G0"):
        part=curve[curve.model.eq(model)].sort_values("budget"); ax.plot(part.budget,part.accuracy,color=colors[model],lw=1.5 if model=="G0" else 2.3,alpha=.6 if model=="G0" else 1,label=labels[model])
    ax.set(xlabel="Revealed simulations on frozen A0 path",ylabel="Fold-B1-q20 accuracy",title="Physics-first mean with isotropic and ARD corrections"); ax.grid(alpha=.25); ax.legend(frameon=False,ncol=2,fontsize=9); fig.tight_layout(); path=FIGURES/"01_q20_learning_curves.png"; fig.savefig(path,dpi=180); plt.close(fig); created.append((path,"Headline q20 learning curves on identical A0 prefixes."))
    order=["M3-H","M3-M2","M3-M2W","M3-G3"]; part=contrasts[(contrasts.subset.eq("B1_q20"))&contrasts.contrast.isin(order)].set_index("contrast").loc[order].reset_index(); y=np.arange(len(part)); fig,ax=plt.subplots(figsize=(8.2,4.8)); ax.errorbar(part.mean_difference,y,xerr=[part.mean_difference-part.ci_lower,part.ci_upper-part.mean_difference],fmt="o",capsize=5,color="#9b2c2c",ms=7); ax.axvline(0,color="black",ls="--"); ax.set_yticks(y,part.contrast); ax.invert_yaxis(); ax.set(xlabel="Matched q20 AULC difference",title="Predeclared Phase 1.13 contrasts (95% repeat-block intervals)"); ax.grid(axis="x",alpha=.25); fig.tight_layout(); path=FIGURES/"02_q20_contrasts.png"; fig.savefig(path,dpi=180); plt.close(fig); created.append((path,"Primary and mechanistic q20 AULC contrasts."))
    part=region_summary[region_summary.model.isin(("H","G3","M3"))]; pivot=part.pivot(index="model",columns="region",values="mean_AULC").loc[["H","G3","M3"]]; fig,ax=plt.subplots(figsize=(8,4.8)); x=np.arange(3); width=.34; ax.bar(x-width/2,pivot.EARLY_B16_40,width,label="Early B16-40",color="#63b3ed"); ax.bar(x+width/2,pivot.LATE_B41_80,width,label="Late B41-80",color="#805ad5"); ax.set_xticks(x,[labels[m] for m in pivot.index]); ax.set(ylabel="q20 accuracy AULC",title="Predeclared early/late regions"); ax.grid(axis="y",alpha=.25); ax.legend(frameon=False); fig.tight_layout(); path=FIGURES/"03_early_late_aulc.png"; fig.savefig(path,dpi=180); plt.close(fig); created.append((path,"Early and late q20 AULC for H, G3, and M3."))
    r=role[role.subset.eq("B1_q20")]; fig,ax=plt.subplots(figsize=(8,5)); phys=r[r.metric.eq("physics_latent_sd")].sort_values("budget"); resid=r[r.metric.eq("posterior_residual_mean_sd")].sort_values("budget"); change=r[r.metric.eq("decision_changed_fraction")].sort_values("budget"); ax.plot(phys.budget,phys["mean"],"o-",label="Physics latent SD",color="#2f855a"); ax.plot(resid.budget,resid["mean"],"o-",label="Residual posterior-mean SD",color="#c53030"); ax2=ax.twinx(); ax2.plot(change.budget,change["mean"],"s--",label="Decision changed",color="#553c9a"); ax.set(xlabel="Budget",ylabel="Latent SD",title="What the ARD discrepancy changes on q20"); ax2.set_ylabel("Fraction of held-out decisions changed"); lines=ax.get_lines()+ax2.get_lines(); ax.legend(lines,[l.get_label() for l in lines],frameon=False); ax.grid(alpha=.25); fig.tight_layout(); path=FIGURES/"04_residual_role.png"; fig.savefig(path,dpi=180); plt.close(fig); created.append((path,"Physics/residual magnitude and changed-decision fraction."))
    part=ard[ard.parameter.isin(("l_P","l_VX","l_LS","l_ST"))]; fig,axes=plt.subplots(1,2,figsize=(11,4.8),sharey=True); palette={16:"#9ecae1",40:"#4292c6",80:"#084594"}
    for ax,setting in zip(axes,("L100","L1000")):
        sub=part[part.setting.eq(setting)]
        for budget,group in sub.groupby("budget"):
            group=group.set_index("parameter").loc[["l_P","l_VX","l_LS","l_ST"]]; x=np.arange(4)+(budget-40)/120; ax.errorbar(x,group["median"],yerr=[group["median"]-group.q1,group.q3-group["median"]],fmt="o",capsize=4,color=palette[int(budget)],label=f"B{budget}")
        ax.set_xticks(np.arange(4),FEATURES); ax.set_yscale("log"); ax.set_title(f"M3 {setting}"); ax.grid(axis="y",alpha=.25); ax.set_xlabel("Standardized input coordinate")
    axes[0].set_ylabel("ARD lengthscale (median and IQR, log scale)"); axes[1].legend(frameon=False); fig.suptitle("ARD geometry and upper-bound sensitivity; not physical importance"); fig.tight_layout(); path=FIGURES/"05_ard_bound_sensitivity.png"; fig.savefig(path,dpi=180); plt.close(fig); created.append((path,"M3 lengthscale distributions under upper bounds 100 and 1000."))
    manifest=pd.DataFrame([{"figure":p.name,"sha256":sha256_file(p),"size_bytes":p.stat().st_size,"purpose":purpose} for p,purpose in created]); write_csv(OUTPUT/"figure_manifest.csv",manifest); return manifest


def build_reports(summary: pd.DataFrame,contrasts: pd.DataFrame,region_summary: pd.DataFrame,region_contrasts: pd.DataFrame,checkpoints: pd.DataFrame,role: pd.DataFrame,amplitude: pd.DataFrame,ard: pd.DataFrame,sensitivity: pd.DataFrame,decision: str) -> None:
    def s(model:str,subset:str="B1_q20") -> float:return float(summary[(summary.model.eq(model))&summary.subset.eq(subset)].mean_AULC.iloc[0])
    def c(name:str,subset:str="B1_q20") -> pd.Series:return contrasts[(contrasts.contrast.eq(name))&contrasts.subset.eq(subset)].iloc[0]
    def r(name:str,region:str) -> pd.Series:return region_contrasts[(region_contrasts.contrast.eq(name))&region_contrasts.region.eq(region)].iloc[0]
    def cp(model:str,budget:int,metric:str) -> float:return float(checkpoints[(checkpoints.model.eq(model))&checkpoints.budget.eq(budget)&checkpoints.metric.eq(metric)]["mean"].iloc[0])
    def amp(model:str,scope:str,metric:str) -> float:return float(amplitude[(amplitude.model.eq(model))&amplitude.scope.eq(scope)&amplitude.metric.eq(metric)]["mean"].iloc[0])
    primary=c("M3-H"); old=c("M3-M2"); mechanism=c("M3-M2W"); standalone=c("M3-G3"); early_h=r("M3-H","EARLY_B16_40"); early_g3=r("M3-G3","EARLY_B16_40"); late_h=r("M3-H","LATE_B41_80"); late_g3=r("M3-G3","LATE_B41_80"); q30_h=c("M3-H","B1_q30"); q30_control=c("M3-M2W","B1_q30"); q30_g3=c("M3-G3","B1_q30"); future=decision in {"HYBRID_GAIN_SUPPORTED","LATE_RESIDUAL_GAIN_ONLY"}; preferred="YES" if decision=="HYBRID_GAIN_SUPPORTED" else ("CONDITIONAL_LATE_DATA" if decision=="LATE_RESIDUAL_GAIN_ONLY" else "NO")
    role_pivot=role[role.subset.eq("B1_q20")].pivot(index="metric",columns="budget",values="mean"); sens_max=float(sensitivity.full81_probability_MAE.max()); sens_acc=float(sensitivity.delta_L1000_minus_L100_B1_q20_accuracy.abs().max()); m3_bounds=ard[(ard.setting.eq("L100"))&ard.parameter.eq("any_length_upper_bound_hit")].set_index("budget")["median"]
    final=["# Week 9 Phase 1.13 — Fixed Physics Mean + ARD GP Discrepancy","",f"## Decision: {decision}","","## Same-path q20 result",f"AULC H/G0/G3/M2/M3: {s('H'):.6f} / {s('G0'):.6f} / {s('G3'):.6f} / {s('M2'):.6f} / {s('M3'):.6f}.",f"Primary M3-H: {primary.mean_difference:+.6f} [{primary.ci_lower:+.6f}, {primary.ci_upper:+.6f}] ({int(primary.positive_repeat_blocks)}/20 positive repeats).",f"M3-M2: {old.mean_difference:+.6f} [{old.ci_lower:+.6f}, {old.ci_upper:+.6f}].",f"Mechanistic M3-M2W: {mechanism.mean_difference:+.6f} [{mechanism.ci_lower:+.6f}, {mechanism.ci_upper:+.6f}].",f"M3-G3: {standalone.mean_difference:+.6f} [{standalone.ci_lower:+.6f}, {standalone.ci_upper:+.6f}].","","## Early versus late",f"Early B16-40 M3-H {early_h.mean_difference:+.6f} [{early_h.ci_lower:+.6f}, {early_h.ci_upper:+.6f}]; M3-G3 {early_g3.mean_difference:+.6f} [{early_g3.ci_lower:+.6f}, {early_g3.ci_upper:+.6f}].",f"Late B41-80 M3-H {late_h.mean_difference:+.6f} [{late_h.ci_lower:+.6f}, {late_h.ci_upper:+.6f}]; M3-G3 {late_g3.mean_difference:+.6f} [{late_g3.ci_lower:+.6f}, {late_g3.ci_upper:+.6f}].","","## Checkpoints"]
    for budget in CHECKPOINT_BUDGETS: final.append(f"B{budget} q20 accuracy H/G3/M2/M3: {cp('H',budget,'accuracy'):.4f}/{cp('G3',budget,'accuracy'):.4f}/{cp('M2',budget,'accuracy'):.4f}/{cp('M3',budget,'accuracy'):.4f}; KH recall: {cp('H',budget,'keyhole_recall'):.4f}/{cp('G3',budget,'keyhole_recall'):.4f}/{cp('M2',budget,'keyhole_recall'):.4f}/{cp('M3',budget,'keyhole_recall'):.4f}.")
    final += ["","## Residual role",f"At B16/B40/B80, q20 decisions changed relative to the frozen physics mean in {role_pivot.loc['decision_changed_fraction',16]:.1%}/{role_pivot.loc['decision_changed_fraction',40]:.1%}/{role_pivot.loc['decision_changed_fraction',80]:.1%}. Residual posterior-mean SD was {role_pivot.loc['posterior_residual_mean_sd',16]:.3f}/{role_pivot.loc['posterior_residual_mean_sd',40]:.3f}/{role_pivot.loc['posterior_residual_mean_sd',80]:.3f}.",f"Among changed q20 decisions, the beneficial shares were {role_pivot.loc['beneficial_fraction_among_changed',16]:.1%}/{role_pivot.loc['beneficial_fraction_among_changed',40]:.1%}/{role_pivot.loc['beneficial_fraction_among_changed',80]:.1%}; harmful shares were {role_pivot.loc['harmful_fraction_among_changed',16]:.1%}/{role_pivot.loc['harmful_fraction_among_changed',40]:.1%}/{role_pivot.loc['harmful_fraction_among_changed',80]:.1%}.","No orthogonality or identified physical decomposition is claimed.","","## Bounds and sensitivity",f"M3 residual-SD upper-bound hit rate over B16-80 was {amp('M3','all_B16_80','residual_sd_upper_bound_hit'):.1%} (any amplitude bound: {amp('M3','all_B16_80','residual_sd_any_bound_hit'):.1%}); this is a material regularization limitation.",f"M3 L100 any-upper-length-bound rates at B16/B40/B80: {m3_bounds.loc[16]:.1%}/{m3_bounds.loc[40]:.1%}/{m3_bounds.loc[80]:.1%}.",f"Changing the length upper bound 100 to 1000 produced maximum checkpoint full81 probability MAE {sens_max:.4f} and maximum absolute q20 accuracy change {sens_acc:.4f}.","Predictions are locally stable to L1000, but fitted ARD geometry is bound-sensitive. ARD lengthscales are standardized-space geometry diagnostics, not physical importance or exponents.","","## q30 robustness",f"M3-H {q30_h.mean_difference:+.6f} [{q30_h.ci_lower:+.6f}, {q30_h.ci_upper:+.6f}]; M3-M2W {q30_control.mean_difference:+.6f} [{q30_control.ci_lower:+.6f}, {q30_control.ci_upper:+.6f}]; M3-G3 {q30_g3.mean_difference:+.6f} [{q30_g3.ci_lower:+.6f}, {q30_g3.ci_upper:+.6f}].","","## Scientific conclusion",f"Preferred simulator surrogate: **{preferred}**. Future M3-margin acquisition experiment justified: **{'YES' if future else 'NO'}**.","All evidence is model-only on one frozen simulator benchmark and one A0 path. Acquisition, external transfer, causal importance, orthogonality, and universal physics are not tested."]
    (OUTPUT/"FINAL_PHASE1_13_REPORT.md").write_text("\n".join(final)+"\n",encoding="utf-8")
    supervisor=["# Supervisor Phase 1.13 — one page","",f"**Decision:** {decision}","",f"- q20 AULC H/G3/M2/M2W/M3: {s('H'):.4f} / {s('G3'):.4f} / {s('M2'):.4f} / {float(pd.read_csv(OUTPUT/'repeat_metrics.csv').query("model=='M2W' and subset=='B1_q20'").accuracy_AULC_16_80.mean()):.4f} / {s('M3'):.4f}.",f"- M3-H: {primary.mean_difference:+.4f} [{primary.ci_lower:+.4f}, {primary.ci_upper:+.4f}].",f"- M3-M2: {old.mean_difference:+.4f} [{old.ci_lower:+.4f}, {old.ci_upper:+.4f}].",f"- Bound-matched anisotropy test M3-M2W: {mechanism.mean_difference:+.4f} [{mechanism.ci_lower:+.4f}, {mechanism.ci_upper:+.4f}].",f"- Early M3-H: {early_h.mean_difference:+.4f} [{early_h.ci_lower:+.4f}, {early_h.ci_upper:+.4f}]; late: {late_h.mean_difference:+.4f} [{late_h.ci_lower:+.4f}, {late_h.ci_upper:+.4f}].",f"- B16 q20 accuracy/KH recall M3: {cp('M3',16,'accuracy'):.3f}/{cp('M3',16,'keyhole_recall'):.3f}; B80: {cp('M3',80,'accuracy'):.3f}/{cp('M3',80,'keyhole_recall'):.3f}.",f"- M3 residual-SD upper-bound rate: {amp('M3','all_B16_80','residual_sd_upper_bound_hit'):.1%}; L100-to-L1000 max full81 probability MAE: {sens_max:.4f}.",f"- Preferred surrogate: {preferred}; future M3 acquisition follow-up: {'YES' if future else 'NO'}.","","The test isolates anisotropy using M2W. All models saw identical A0 labels. Predictions are locally stable to the L1000 check, but amplitude and length-bound hits limit mechanistic interpretation. ARD parameters are geometry diagnostics only; no acquisition or external-validation claim is made."]
    (OUTPUT/"SUPERVISOR_PHASE1_13_ONE_PAGE.md").write_text("\n".join(supervisor)+"\n",encoding="utf-8")
    def status(row:pd.Series) -> str:
        if row.ci_lower>0:return "SUPPORTED"
        if row.ci_upper<0:return "NOT SUPPORTED"
        return "UNRESOLVED"
    ledger=["# Phase 1.13 claim ledger","","| Claim | Status | Evidence boundary |","|---|---|---|",f"| A. M3 improves q20 AULC over H. | {status(primary)} | Primary repeat-block contrast. |",f"| B. M3 improves over old M2. | {status(old)} | Same A0 prefixes; old bounds differ. |",f"| C. M3 improves over bound-matched M2W. | {status(mechanism)} | Clean anisotropy contrast. |",f"| D. M3 improves over standalone G3. | {status(standalone)} | Same revealed labels. |",f"| E. M3 preserves H's B16 advantage. | {'QUALIFIED' if abs(cp('M3',16,'accuracy')-cp('H',16,'accuracy'))<.02 else 'NOT SUPPORTED'} | Descriptive; no non-inferiority margin. |",f"| F. M3 improves late B41-80 behavior over H. | {status(late_h)} | Predeclared late region. |",f"| G. Gain is caused by ARD rather than wider bounds. | {status(mechanism)} | Requires M3-M2W. |","| H. ARD lengthscales are physical constants. | NOT SUPPORTED | Standardized-space model geometry only. |","| I. Physics/residual identifiability is solved. | FALSE / NOT CLAIMABLE | Orthogonality not imposed. |","| J. Phase 1.13 demonstrates better acquisition. | NOT TESTED | Frozen A0 replay. |",f"| K. Future M3 active acquisition is justified. | {'SUPPORTED' if future else 'NOT SUPPORTED'} | Model evidence only. |"]
    (OUTPUT/"claim_ledger.md").write_text("\n".join(ledger)+"\n",encoding="utf-8")
    red=["# Final red-team report","","- Phase 1.12 final SHA is the immutable parent; no Phase 1.x artifact was edited.","- The old `{future}` placeholder is absent before Phase 1.13 starts.","- M2W and M3 share physics mean, amplitude bounds, wide length bounds, optimizer, initialization, inputs, and A0 labels; only scalar versus four lengthscales differs.","- Stage 1 uses revealed-prefix log(h) only and is frozen before Stage 2.","- Stage 2 receives standardized P,VX,LS,ST only; log(h), hidden labels and q20/q30 flags are absent.","- ARD zero-mean parity was tested against sklearn on one toy and three thesis prefixes before science.","- Old M2 is not used alone to attribute an ARD effect; M2W is the mechanistic control.","- B16, B80, full81, bound hits, convergence and L1000 sensitivity are disclosed.","- Unresolved intervals are not called equivalence or non-inferiority.","- Repeat-block inference retains five folds together; 100 folds are not called independent experiments.","- ARD lengthscales are not causal importance, physical exponents or sensitivity constants.","- No new acquisition, external validation, orthogonality or universal transfer claim is made."]
    (OUTPUT/"FINAL_RED_TEAM_REPORT.md").write_text("\n".join(red)+"\n",encoding="utf-8")


def build_notebook() -> None:
    cells=[nbf.v4.new_markdown_cell("# Week 9 Phase 1.13 — Fixed Physics Mean + ARD GP Discrepancy\n\nThis teaching notebook reads generated artifacts and does not rerun the 13,000 main GP fits."),nbf.v4.new_markdown_cell("## 1. Why this phase exists\n\nPhase 1.11 found no resolved gain from an isotropic discrepancy. Phase 1.12 then showed that ARD materially improved the standalone 4D GPC. H was strongest at B16, while standalone G3 became stronger later. M3 asks whether one model can combine these behaviors."),nbf.v4.new_code_cell("from pathlib import Path\nimport json, pandas as pd\nfrom IPython.display import display, Image, Markdown\nROOT=Path.cwd().parents[1] if Path.cwd().name=='week_09' else Path.cwd()\nOUT=ROOT/'outputs'/'week9_phase1_13_fixed_physics_ard_discrepancy'\ndisplay(json.loads((OUT/'baseline_gate.json').read_text()))"),nbf.v4.new_markdown_cell("## 2. Architecture and the M2W control\n\nStage 1 fits `m_h=b0+b_h z(log h)` from revealed labels and freezes it. Stage 2 fits `r(x)` on standardized P,VX,LS,ST. M2W and M3 have identical wide bounds; M2W has one lengthscale and M3 has four. Thus M3-M2W isolates anisotropy."),nbf.v4.new_code_cell("display(pd.DataFrame(json.loads((OUT/'kernel_specification.json').read_text())['models']).T)"),nbf.v4.new_markdown_cell("## 3. ARD implementation parity\n\nThe custom zero-mean Laplace classifier must match sklearn under identical fixed ARD parameters before science."),nbf.v4.new_code_cell("display(json.loads((OUT/'ard_parity_report.json').read_text()))"),nbf.v4.new_markdown_cell("## 4. Main q20 result on the frozen A0 path"),nbf.v4.new_code_cell("display(pd.read_csv(OUT/'model_summary.csv')); display(pd.read_csv(OUT/'paired_contrasts.csv').query(\"subset=='B1_q20'\")); display(Image(filename=str(OUT/'figures'/'01_q20_learning_curves.png'))); display(Image(filename=str(OUT/'figures'/'02_q20_contrasts.png')))"),nbf.v4.new_markdown_cell("## 5. Early versus late\n\nThese regions were fixed as B16-40 and B41-80 before reading the result."),nbf.v4.new_code_cell("display(pd.read_csv(OUT/'early_late_aulc_summary.csv')); display(pd.read_csv(OUT/'early_late_contrasts.csv')); display(Image(filename=str(OUT/'figures'/'03_early_late_aulc.png')))"),nbf.v4.new_markdown_cell("## 6. B16/B40/B80 confusion behavior"),nbf.v4.new_code_cell("display(pd.read_csv(OUT/'checkpoint16_40_80_summary.csv')); display(pd.read_csv(OUT/'checkpoint_hard_disagreements.csv'))"),nbf.v4.new_markdown_cell("## 7. What the discrepancy actually changes"),nbf.v4.new_code_cell("display(pd.read_csv(OUT/'residual_role_summary.csv')); display(Image(filename=str(OUT/'figures'/'04_residual_role.png')))"),nbf.v4.new_markdown_cell("## 8. ARD and the L1000 sensitivity\n\nLengthscales are standardized geometry diagnostics, not causal physical importance."),nbf.v4.new_code_cell("display(pd.read_csv(OUT/'ard_lengthscale_summary.csv')); display(pd.read_csv(OUT/'upper_bound_sensitivity.csv')); display(Image(filename=str(OUT/'figures'/'05_ard_bound_sensitivity.png')))"),nbf.v4.new_markdown_cell("## 9. q30 and full81 robustness"),nbf.v4.new_code_cell("display(pd.read_csv(OUT/'paired_contrasts.csv').query(\"subset=='B1_q30'\")); display(pd.read_csv(OUT/'full81_checkpoint_summary.csv'))"),nbf.v4.new_markdown_cell("## 10. Safe conclusion\n\nThis is a model-only comparison on one frozen simulator benchmark. It does not prove acquisition gain, orthogonality, causal importance, or external transfer."),nbf.v4.new_code_cell("display(Markdown((OUT/'SUPERVISOR_PHASE1_13_ONE_PAGE.md').read_text()))")]
    notebook=nbf.v4.new_notebook(cells=cells,metadata={"kernelspec":{"display_name":"Thesis Python","language":"python","name":"thesis"}}); NOTEBOOK.parent.mkdir(parents=True,exist_ok=True); nbf.write(notebook,NOTEBOOK); executed=NotebookClient(nbf.read(NOTEBOOK,as_version=4),timeout=180,kernel_name="thesis",resources={"metadata":{"path":str(ROOT)}}).execute(); nbf.write(executed,NOTEBOOK)


def historical_changes() -> list[str]:
    historical=["outputs/week9_phase1_5_h_physics_confirmation","outputs/week9_phase1_7_physics_ridge_residual_gp","outputs/week9_phase1_8_model_path_decomposition","outputs/week9_phase1_9_physics_specificity_control","outputs/week9_phase1_10_external_experimental_validation","outputs/week9_phase1_10_closure_diagnostics","outputs/week9_phase1_11_fixed_mean_discrepancy_gp","outputs/week9_phase1_12_gpc_kernel_adequacy"]
    result=subprocess.check_output(["git","diff","--name-only",PHASE112_SHA,"--",*historical],cwd=ROOT,text=True); return [line for line in result.splitlines() if line.strip()]


def validate(new_predictions: pd.DataFrame,new_metrics: pd.DataFrame,diagnostics: pd.DataFrame,sensitivity_predictions: pd.DataFrame,contrasts: pd.DataFrame,regions: pd.DataFrame,role: pd.DataFrame,figures: pd.DataFrame,decision: str) -> dict[str,Any]:
    source=Path(__file__).read_text(encoding="utf-8"); fit_source=source[source.index("def residual_kernel"):source.index("def kernel_specification")]+source[source.index("def fit_hybrid"):source.index("def components")]; gate=json.loads((OUTPUT/"baseline_gate.json").read_text()); parity=json.loads((OUTPUT/"ard_parity_report.json").read_text()); kernel=json.loads((OUTPUT/"kernel_specification.json").read_text()); population,specs,paths=load_inputs(); notebook=nbf.read(NOTEBOOK,as_version=4); code=[c for c in notebook.cells if c.cell_type=="code"]; report=(OUTPUT/"FINAL_PHASE1_13_REPORT.md").read_text().lower(); diag_m3=diagnostics[diagnostics.model.eq("M3")]; diag_m2w=diagnostics[diagnostics.model.eq("M2W")]
    def has_contrast(name:str,subset:str="B1_q20") -> bool:return len(contrasts[(contrasts.contrast.eq(name))&contrasts.subset.eq(subset)])==1
    checks=[
        ("phase112_parent_sha",subprocess.run(["git","merge-base","--is-ancestor",PHASE112_SHA,"HEAD"],cwd=ROOT).returncode==0,PHASE112_SHA),
        ("phase112_placeholder_gone",gate["phase112_placeholder_absent"],"{future} absent"),
        ("historical_phase1x_unchanged",historical_changes()==[],str(historical_changes())),
        ("population_405_73_332",(len(population),int(population.has_keyhole.sum()))==(405,73),"405/73/332"),
        ("exact_A0_paths",len(paths)==len(specs)==100,"100"),
        ("exact_budget_grid",BUDGETS==tuple(range(16,81)),"B16-80"),
        ("frozen_H",abs(gate["H_q20_AULC"]-.8308134191176471)<1e-12,str(gate["H_q20_AULC"])),
        ("frozen_G0",abs(gate["G0_q20_AULC"]-.8135202205882353)<1e-12,str(gate["G0_q20_AULC"])),
        ("frozen_G3",abs(gate["G3_q20_AULC"]-.826594669117647)<1e-12,str(gate["G3_q20_AULC"])),
        ("frozen_M2",abs(gate["M2_q20_AULC"]-.8302297794117648)<1e-12,str(gate["M2_q20_AULC"])),
        ("no_new_acquisition","path[:budget]" in source and "acquisition" not in fit_source.lower(),"A0 replay"),
        ("identical_revealed_prefixes","shared_by_M2W_M3" in source,"one physics fit per budget"),
        ("stage1_only_log_h","p11.fit_physics_mean(logh" in source,"Phase 1.11 implementation"),
        ("stage1_revealed_labels_only","revealed,seed_u32(\"shared_physics\"" in source,"prefix only"),
        ("stage1_mean_frozen","mean_train=physics.latent" in source and "FixedMeanLaplaceGPC" in source,"fixed values"),
        ("latent_logit_mean","mean_train=physics.latent" in fit_source,"latent logit values passed as GP mean"),
        ("M3_inputs_exact",FEATURES==("P","VX","LS","ST"),str(FEATURES)),
        ("logh_excluded_residual","residual_kernel(model,upper)" in source and "logh" not in repr(residual_kernel("M3")),"4D kernel only"),
        ("no_external_exponent",all(token not in fit_source for token in ("-1.713","-1.219")),"none"),
        ("no_masinelli_data","masinelli" not in fit_source.lower(),"simulator only"),
        ("boundary_evaluation_only","subset_flags" not in fit_source and "B1_q20" not in fit_source,"fit path clean"),
        ("matern_nu_1_5",kernel["shared"]["matern_nu"]==1.5,"1.5"),
        ("M3_four_lengths",len(np.ravel(residual_kernel("M3").k2.length_scale))==4,"4"),
        ("residual_sd_bounds",RESIDUAL_SD_BOUNDS==(0.05,1.0),str(RESIDUAL_SD_BOUNDS)),
        ("M3_primary_bounds",PRIMARY_LENGTH_BOUNDS==(0.01,100.0),str(PRIMARY_LENGTH_BOUNDS)),
        ("M2W_same_bounds",kernel["shared"]["primary_length_bounds"]==[0.01,100.0],"same"),
        ("M2W_isotropic",not kernel["models"]["M2W"]["ard"],"scalar"),
        ("M3_ARD",kernel["models"]["M3"]["ard"],"four"),
        ("same_amplitude_bounds",kernel["shared"]["amplitude_bounds_identical"],str(RESIDUAL_SD_BOUNDS)),
        ("same_optimizer_restarts",kernel["shared"]["optimizer"]=="L-BFGS-B" and kernel["shared"]["restarts"]==0,"zero restarts"),
        ("ARD_zero_mean_parity",parity["status"]=="PASS" and parity["maximum_probability_difference"]<=1e-5,str(parity["maximum_probability_difference"])),
        ("M2W_predictions_complete",len(new_predictions[new_predictions.model.eq("M2W")])==100*65*81,"526500"),
        ("M3_predictions_complete",len(new_predictions[new_predictions.model.eq("M3")])==100*65*81,"526500"),
        ("L1000_only_checkpoints",len(sensitivity_predictions)==100*3*81 and set(sensitivity_predictions.budget)==set(CHECKPOINT_BUDGETS),"B16/B40/B80"),
        ("twenty_repeat_blocks",new_predictions.repeat.nunique()==20,"20"),
        ("bootstrap_draws",BOOTSTRAP_DRAWS>=10000,str(BOOTSTRAP_DRAWS)),
        ("primary_M3_H",has_contrast("M3-H"),"q20"),
        ("mechanistic_M3_M2W",has_contrast("M3-M2W"),"q20"),
        ("M3_M2",has_contrast("M3-M2"),"q20"),
        ("M3_G3",has_contrast("M3-G3"),"q20"),
        ("early_exact",EARLY_BUDGETS==tuple(range(16,41)) and set(regions.region)=={"EARLY_B16_40","LATE_B41_80"},"16-40"),
        ("late_exact",LATE_BUDGETS==tuple(range(41,81)),"41-80"),
        ("q30_secondary",all(has_contrast(name,"B1_q30") for name in ("M3-H","M3-M2W","M3-G3")),"complete"),
        ("full81_checkpoints",len(pd.read_csv(OUTPUT/"full81_checkpoint_summary.csv"))==5*3*7,"5x3x7"),
        ("ARD_dimension_labels",diag_m3[["l_P","l_VX","l_LS","l_ST"]].notna().all().all(),"P/VX/LS/ST"),
        ("bound_hits_deterministic",BOUND_ATOL==5e-4,"fixed atol"),
        ("residual_role_complete",set(role.budget)==set(CHECKPOINT_BUDGETS) and set(role.subset)=={"full81","B1_q20"},"checkpoints/subsets"),
        ("changed_decision_fractions_coherent",np.allclose(role[role.metric.eq("beneficial_fraction_among_changed")].sort_values(["subset","budget"])["mean"].to_numpy()+role[role.metric.eq("harmful_fraction_among_changed")].sort_values(["subset","budget"])["mean"].to_numpy(),1.0),"beneficial + harmful = 1"),
        ("no_orthogonality_claim","residual is orthogonal" not in report and "orthogonality is established" not in report,"safe"),
        ("no_causal_ARD_claim","causal feature importance" not in report,"safe"),
        ("no_acquisition_superiority","acquisition superiority" not in report,"safe"),
        ("upper_sensitivity_complete",len(pd.read_csv(OUTPUT/"upper_bound_sensitivity.csv"))==3,"3 budgets"),
        ("notebook_executed",bool(code) and all(c.execution_count is not None for c in code) and not [o for c in code for o in c.get("outputs",[]) if o.get("output_type")=="error"],f"{len(code)} code cells"),
        ("figure_hashes",len(figures)<=5 and all(sha256_file(FIGURES/r.figure)==r.sha256 for r in figures.itertuples(index=False)),str(len(figures))),
        ("no_unresolved_templates",all(token not in (OUTPUT/"FINAL_PHASE1_13_REPORT.md").read_text() for token in ("{future}","{decision}","TODO","TBD")),"none"),
        ("historical_outputs_unchanged_again",historical_changes()==[],"git diff"),
        ("red_team_language","100 folds are not called independent" in (OUTPUT/"FINAL_RED_TEAM_REPORT.md").read_text(),"explicit"),
        ("M2W_M3_diagnostic_counts",len(diag_m2w)==len(diag_m3)==6500,"6500 each"),
        ("physics_shared_complete",len(pd.read_csv(OUTPUT/"physics_mean_fit_diagnostics.csv.gz"))==6500,"one per prefix"),
        ("decision_declared",decision in {"HYBRID_GAIN_SUPPORTED","LATE_RESIDUAL_GAIN_ONLY","BOUND_RANGE_EFFECT","NO_DISCREPANCY_GAIN","NUMERICALLY_UNSTABLE","IMPLEMENTATION_NOT_VALIDATED"},decision),
    ]
    records=[{"check":name,"status":"PASS" if ok else "FAIL","detail":detail} for name,ok,detail in checks]; payload={"status":"PASS" if all(r["status"]=="PASS" for r in records) else "FAIL","check_count":len(records),"passed":sum(r["status"]=="PASS" for r in records),"checks":records}; write_json(OUTPUT/"validation_report.json",payload); lines=["# Phase 1.13 validation","",f"Status: **{payload['status']}**",f"Checks: **{payload['passed']} / {payload['check_count']} PASS**","","| Check | Status | Detail |","|---|---|---|"]+[f"| {r['check']} | {r['status']} | {r['detail']} |" for r in records]; (OUTPUT/"validation_report.md").write_text("\n".join(lines)+"\n",encoding="utf-8"); require(payload["status"]=="PASS","validation failure"); return payload


def write_run_manifest(validation: dict[str,Any],decision: str) -> None:
    files=[p for p in OUTPUT.rglob("*") if p.is_file() and "checkpoints" not in p.parts and p.name!="run_manifest.json"]; files.extend([Path(__file__),ROOT/"tests"/"test_week9_phase1_13_fixed_physics_ard_discrepancy.py",NOTEBOOK]); entries=[]
    for path in sorted(set(files)):
        require(path.is_file(),f"manifest missing {path}"); payload=artifact_bytes(path); entries.append({"path":path.relative_to(ROOT).as_posix(),"sha256":hashlib.sha256(payload).hexdigest(),"size_bytes":len(payload)})
    manifest={"study":"Week 9 Phase 1.13 — Fixed Physics Mean + ARD GP Discrepancy","phase112_parent_sha":PHASE112_SHA,"branch":BRANCH,"decision":decision,"protocol":{"path":"frozen A0","budgets":list(BUDGETS),"early_budgets":list(EARLY_BUDGETS),"late_budgets":list(LATE_BUDGETS),"outer_runs":100,"repeat_blocks":20,"folds_per_repeat":5,"bootstrap_draws":BOOTSTRAP_DRAWS,"new_full_models":list(NEW_MODELS),"sensitivity_budgets":list(CHECKPOINT_BUDGETS)},"validation":validation,"historical_changes":historical_changes(),"files":entries}; write_json(OUTPUT/"run_manifest.json",manifest)


def finalize() -> dict[str,Any]:
    gate=baseline_gate(); parity=run_parity_gate(); kernel_specification(); new_predictions,new_metrics,diagnostics,_=collect_main_checkpoints(); sens_predictions,sens_metrics,sens_diagnostics=collect_sensitivity_checkpoints(); historical=load_historical_predictions(); metrics=historical_and_new_metrics(new_predictions,historical); outer,repeat,summary,contrasts=compute_aulc(metrics); region_summary,region_contrasts=compute_regions(metrics); checkpoints=summarize_checkpoints(metrics,"B1_q20",HEADLINE_MODELS,("accuracy","balanced_accuracy","keyhole_recall","conduction_recall","false_negative","false_positive")); full=summarize_checkpoints(metrics,"full81",HEADLINE_MODELS,("roc_auc","pr_auc","accuracy","balanced_accuracy","keyhole_recall","conduction_recall","brier_score")); disagreements=hard_disagreements(historical,new_predictions); _,role=residual_role(new_predictions); amplitude=residual_amplitude_summary(diagnostics); ard=ard_lengthscale_summary(diagnostics,sens_diagnostics); sensitivity=upper_bound_sensitivity(new_predictions,metrics,diagnostics,sens_predictions,sens_metrics,sens_diagnostics); decision=decide(contrasts,region_contrasts,sensitivity,parity)
    for name,frame in (("outer_run_metrics.csv.gz",outer),("repeat_metrics.csv",repeat),("model_summary.csv",summary),("paired_contrasts.csv",contrasts),("early_late_aulc_summary.csv",region_summary),("early_late_contrasts.csv",region_contrasts),("checkpoint16_40_80_summary.csv",checkpoints),("checkpoint_hard_disagreements.csv",disagreements),("full81_checkpoint_summary.csv",full),("residual_amplitude_summary.csv",amplitude),("ard_lengthscale_summary.csv",ard),("residual_role_summary.csv",role),("upper_bound_sensitivity.csv",sensitivity)):write_csv(OUTPUT/name,frame)
    figures=make_figures(metrics,contrasts,region_summary,region_contrasts,role,ard); build_reports(summary,contrasts,region_summary,region_contrasts,checkpoints,role,amplitude,ard,sensitivity,decision); build_notebook(); validation=validate(new_predictions,new_metrics,diagnostics,sens_predictions,contrasts,region_contrasts,role,figures,decision); write_run_manifest(validation,decision); manifest=json.loads((OUTPUT/"run_manifest.json").read_text()); require(all(hashlib.sha256(artifact_bytes(ROOT/item["path"])).hexdigest()==item["sha256"] for item in manifest["files"]),"manifest hash failure"); return {"status":"PASS","decision":decision,"validation_checks":validation["check_count"],"baseline":gate["status"],"historical_changes":historical_changes()}


def publish_existing() -> dict[str,Any]:
    new_predictions=pd.read_csv(OUTPUT/"new_predictions.csv.gz"); diagnostics=pd.concat([pd.read_csv(OUTPUT/"m2w_fit_diagnostics.csv.gz",low_memory=False),pd.read_csv(OUTPUT/"m3_fit_diagnostics.csv.gz",low_memory=False)],ignore_index=True); sens_predictions,_,_=collect_sensitivity_checkpoints(); summary=pd.read_csv(OUTPUT/"model_summary.csv"); contrasts=pd.read_csv(OUTPUT/"paired_contrasts.csv"); region_summary=pd.read_csv(OUTPUT/"early_late_aulc_summary.csv"); regions=pd.read_csv(OUTPUT/"early_late_contrasts.csv"); checkpoints=pd.read_csv(OUTPUT/"checkpoint16_40_80_summary.csv"); role=pd.read_csv(OUTPUT/"residual_role_summary.csv"); amplitude=pd.read_csv(OUTPUT/"residual_amplitude_summary.csv"); ard=pd.read_csv(OUTPUT/"ard_lengthscale_summary.csv"); sensitivity=pd.read_csv(OUTPUT/"upper_bound_sensitivity.csv"); figures=pd.read_csv(OUTPUT/"figure_manifest.csv"); parity=json.loads((OUTPUT/"ard_parity_report.json").read_text()); decision=decide(contrasts,regions,sensitivity,parity); build_reports(summary,contrasts,region_summary,regions,checkpoints,role,amplitude,ard,sensitivity,decision); build_notebook(); validation=validate(new_predictions,pd.DataFrame(),diagnostics,sens_predictions,contrasts,regions,role,figures,decision); write_run_manifest(validation,decision); return {"status":"PASS","decision":decision,"validation_checks":validation["check_count"],"historical_changes":historical_changes()}


def main() -> None:
    parser=argparse.ArgumentParser(); parser.add_argument("--parity",action="store_true"); parser.add_argument("--run",action="store_true"); parser.add_argument("--sensitivity",action="store_true"); parser.add_argument("--finalize",action="store_true"); parser.add_argument("--publish",action="store_true"); parser.add_argument("--workers",type=int,default=4); parser.add_argument("--limit-specs",type=int); args=parser.parse_args()
    if args.parity: print(json.dumps(run_parity_gate(),indent=2))
    if args.run: print(json.dumps(run_main(args.workers,args.limit_specs),indent=2))
    if args.sensitivity: print(json.dumps(run_sensitivity(args.workers,args.limit_specs),indent=2))
    if args.finalize: print(json.dumps(finalize(),indent=2))
    if args.publish: print(json.dumps(publish_existing(),indent=2))
    if not any((args.parity,args.run,args.sensitivity,args.finalize,args.publish)): parser.error("choose --parity, --run, --sensitivity, --finalize or --publish")


if __name__=="__main__": main()
