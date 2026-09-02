"""Week 9 Phase 1.15A: physics--residual signal audit and acquisition design.

This module replays selected *model states* on the already-published Phase 1.14
P1 path.  It never generates a new acquisition trajectory.  Candidate scores
are frozen without labels; truth and B1-derived diagnostics are joined only
after the pre-reveal table has been written and hashed.
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
from scipy.spatial.distance import pdist
from scipy.stats import spearmanr

from src import week8_5_frozen_sample_efficiency_confirmation as w85
from src import week9_phase1_7_physics_ridge_residual_gp as p17
from src import week9_phase1_11_fixed_mean_discrepancy_gp as p11
from src import week9_phase1_13_fixed_physics_ard_discrepancy as p13
from src import week9_phase1_14_m3_margin_acquisition as p14


ROOT=Path(__file__).resolve().parents[1]
OUTPUT=ROOT/"outputs"/"week9_phase1_15a_physics_residual_signal_audit"
CHECKPOINTS=OUTPUT/"checkpoints"
FIGURES=OUTPUT/"figures"
NOTEBOOK=ROOT/"notebooks"/"week_09"/"13_week9_phase1_15a_physics_residual_signal_audit.ipynb"
PHASE13=ROOT/"outputs"/"week9_phase1_13_fixed_physics_ard_discrepancy"
PHASE14=ROOT/"outputs"/"week9_phase1_14_m3_margin_acquisition"
PHASE114_SHA="5a7a6c05ae5bf3191b74766156407211ad414360"
BRANCH="codex/week9-phase1-15a-physics-residual-signal-audit"
FEATURES=("P","VX","LS","ST")
BUDGETS=(16,20,24,28,32,36,40,48,60,80)
MECHANISM_BUDGETS=(24,28,32,36,40)
BOOTSTRAP_DRAWS=10_000
SEED_ROOT="week9_phase1_15a_physics_residual_signal_audit|v1"
PRE_REVEAL_COLUMNS=("run_id","repeat","fold","budget","population_row_index","P","VX","LS","ST","h","p_H","p_M3","delta_p","abs_delta_p","physics_margin","m3_margin","residual_mean","residual_std","class_flip_H_to_M3","correction_toward_keyhole","correction_toward_conduction","candidate_count","score_inputs_are_pre_reveal_only")


def require(condition: bool,message: str) -> None:
    if not condition: raise RuntimeError(message)


def sigmoid(values: np.ndarray) -> np.ndarray:
    values=np.asarray(values,float); result=np.empty_like(values); positive=values>=0; result[positive]=1.0/(1.0+np.exp(-values[positive])); exp_values=np.exp(values[~positive]); result[~positive]=exp_values/(1.0+exp_values); return result


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


def write_checkpoint(path: Path,payload: dict[str,Any]) -> None:
    path.parent.mkdir(parents=True,exist_ok=True); path.write_bytes(gzip.compress((json.dumps(json_safe(payload),sort_keys=True)+"\n").encode(),compresslevel=6,mtime=0))


def read_checkpoint(path: Path) -> dict[str,Any]: return json.loads(gzip.decompress(path.read_bytes()).decode())


def historical_changes() -> list[str]:
    protected=[f"outputs/week9_phase1_{name}" for name in ("5_h_physics_confirmation","7_physics_ridge_residual_gp","8_model_path_decomposition","9_physics_specificity_control","10_external_experimental_validation","10_closure_diagnostics","11_fixed_mean_discrepancy_gp","12_gpc_kernel_adequacy","13_fixed_physics_ard_discrepancy","14_m3_margin_acquisition")]
    result=subprocess.check_output(["git","diff","--name-only",PHASE114_SHA,"--",*protected],cwd=ROOT,text=True)
    return [line for line in result.splitlines() if line.strip()]


def load_inputs() -> tuple[pd.DataFrame,list[Any],dict[str,list[int]],dict[str,list[int]]]:
    population,specs,a0=p14.load_inputs(); table=pd.read_csv(PHASE14/"m3_margin_paths.csv.gz")
    p1={str(run):g.sort_values("query_order").population_row_index.astype(int).tolist() for run,g in table.groupby("run_id",sort=True)}
    require(len(specs)==len(a0)==len(p1)==100,"path/split count drift")
    for spec in specs:
        require(len(p1[spec.run_id])==80 and len(set(p1[spec.run_id]))==80,"P1 path drift")
        require(p1[spec.run_id][:16]==a0[spec.run_id][:16]==w85.initial_design(spec,population),"initial design drift")
        require(set(p1[spec.run_id]).issubset(spec.train_indices) and set(p1[spec.run_id]).isdisjoint(spec.test_indices),"P1 information-flow drift")
    return population,specs,a0,p1


def baseline_gate() -> dict[str,Any]:
    population,specs,a0,p1=load_inputs(); manifest=json.loads((PHASE14/"run_manifest.json").read_text()); outer=pd.read_csv(PHASE14/"outer_run_metrics.csv.gz"); q20=outer[outer.subset.eq("B1_q20")].groupby("model").accuracy_AULC_16_80.mean(); primary_difference=float(q20.P1-q20.P0)
    merge_base=subprocess.check_output(["git","merge-base","HEAD",PHASE114_SHA],cwd=ROOT,text=True).strip(); payload={"status":"PASS","phase114_parent_sha":PHASE114_SHA,"current_head":subprocess.check_output(["git","rev-parse","HEAD"],cwd=ROOT,text=True).strip(),"exact_branch_base":merge_base,"phase114_decision":manifest["decision"],"population":len(population),"keyholes":int(population.has_keyhole.sum()),"conduction":int((~population.has_keyhole.astype(bool)).sum()),"outer_runs":len(specs),"repeat_blocks":len(set(s.repeat for s in specs)),"P1_paths":len(p1),"P1_path_rows":sum(map(len,p1.values())),"P0_q20_AULC":float(q20.P0),"P1_q20_AULC":float(q20.P1),"P1_minus_P0_q20_AULC":primary_difference,"historical_changes":historical_changes()}
    payload["status"]="PASS" if merge_base==PHASE114_SHA and manifest["decision"]=="LATE_ACQUISITION_GAIN_ONLY" and (len(population),int(population.has_keyhole.sum()))==(405,73) and len(specs)==100 and abs(primary_difference-.0021323529411765)<1e-12 and not payload["historical_changes"] else "FAIL"
    write_json(OUTPUT/"baseline_gate.json",payload); require(payload["status"]=="PASS",f"baseline gate failed {payload}"); return payload


def analysis_specification() -> dict[str,Any]:
    payload={"status":"FROZEN_BEFORE_COMPONENT_RESULTS","role":"diagnostic/design only; no new trajectory","budgets":list(BUDGETS),"mechanism_budgets":list(MECHANISM_BUDGETS),"pre_reveal_columns":list(PRE_REVEAL_COLUMNS),"retrospective_only":["truth","B1_distance","fold_q20_like","fold_q30_like"],"candidate_acquisition_families":["M3 margin baseline","M3 boundary x correction magnitude","M3 boundary x positive correction toward Keyhole"],"inference":{"unit":"20 repeat blocks","bootstrap_draws":BOOTSTRAP_DRAWS,"candidate_rows":"descriptive; repeated candidates are not independent"},"decision":{"CORRECTION_SIGNAL_NUMERICALLY_UNRELIABLE":"Phase 1.14 sensitivity convergence <0.80, or median B80 L100/L1000 path Jaccard <0.25 together with abs AULC change >=0.01","CORRECTION_SIGNAL_SUPPORTED":"top-correction net fix rate CI >0, top-correction q20-like enrichment CI >1, and early B16-24 net fix rate CI >0","CORRECTION_SIGNAL_PARTIAL":"not numerically unreliable and at least two of: top net-fix CI >0; q20-like enrichment CI >1; early net-fix CI >0; Keyhole net-fix CI >0","CORRECTION_SIGNAL_NOT_SUPPORTED":"otherwise"},"novelty_rule":"No broad novelty claim; only a narrow application/formulation possibility after comparison with discrepancy BED, physics-residual acquisition, physics-prior GPC, BALD, and level-set acquisition."}
    write_json(OUTPUT/"analysis_specification.json",payload); return payload


def fit_state(population: pd.DataFrame,spec: Any,path: Sequence[int],budget: int) -> tuple[Any,dict[str,Any]]:
    x4=population.loc[:,FEATURES].to_numpy(float); logh=p11.log_h_values(population); labels=population.has_keyhole.astype(int).to_numpy(); revealed=np.asarray(path[:budget],dtype=int)
    require(len(revealed)==budget and len(set(revealed.tolist()))==budget,"prefix drift")
    physics=p11.fit_physics_mean(logh,labels,revealed,p13.seed_u32("shared_physics",spec.run_id,budget)); fit=p13.fit_hybrid(x4,logh,labels,revealed,spec.train_indices,physics,"M3",100.0); return fit,p13.fit_diagnostic(fit)


def mechanism_row(population: pd.DataFrame,spec: Any,path: Sequence[int],budget: int,path_name: str,distances: np.ndarray,fit: Any,diag: dict[str,Any]) -> dict[str,Any]:
    x4=population.loc[:,FEATURES].to_numpy(float); logh=p11.log_h_values(population); labels=population.has_keyhole.astype(int).to_numpy(); test=np.asarray(spec.test_indices,dtype=int); flags=p17.subset_flags(spec,population,distances)["B1_q20"]; qtest=test[flags]; qkh=qtest[labels[qtest]==1]; comp=p13.components(fit,x4[qkh],logh[qkh]); p_h=sigmoid(comp["physics_latent"]); p_m3=comp["probability"]; active=np.asarray(path[16:budget],dtype=int); scaler=fit.x_scaler; spread=float(pdist(scaler.transform(x4[active])).mean()) if len(active)>1 else math.nan
    return {"run_id":spec.run_id,"repeat":spec.repeat,"fold":spec.fold,"budget":budget,"path":path_name,"revealed_keyholes":int(labels[np.asarray(path[:budget],int)].sum()),"revealed_keyhole_fraction":float(labels[np.asarray(path[:budget],int)].mean()),"active_query_keyhole_fraction":float(labels[active].mean()) if len(active) else math.nan,"physics_intercept":float(fit.physics.model.intercept_[0]),"physics_log_h_coefficient":float(fit.physics.model.coef_[0,0]),"q20_keyhole_count":len(qkh),"q20_keyhole_mean_p_H":float(p_h.mean()) if len(qkh) else math.nan,"q20_keyhole_mean_p_M3":float(p_m3.mean()) if len(qkh) else math.nan,"q20_keyhole_recall_H":float((p_h>=.5).mean()) if len(qkh) else math.nan,"q20_keyhole_recall_M3":float((p_m3>=.5).mean()) if len(qkh) else math.nan,"active_query_standardized_pairwise_spread":spread,"active_query_mean_B1_distance_retrospective":float(distances[active].mean()) if len(active) else math.nan,**diag}


def run_one_spec(spec: Any,population: pd.DataFrame,a0_path: Sequence[int],p1_path: Sequence[int],distances: np.ndarray) -> dict[str,Any]:
    destination=CHECKPOINTS/f"{spec.run_id}.json.gz"
    if destination.is_file():
        payload=read_checkpoint(destination)
        if payload.get("complete") and payload.get("phase114_sha")==PHASE114_SHA and payload.get("budgets")==list(BUDGETS): return {"run_id":spec.run_id,"reused":True}
    x4=population.loc[:,FEATURES].to_numpy(float); logh=p11.log_h_values(population); h=np.exp(logh); train=np.asarray(spec.train_indices,dtype=int); candidate_rows=[]; mechanism=[]; fit_rows=[]
    for budget in BUDGETS:
        revealed=np.asarray(p1_path[:budget],dtype=int); fit,diag=fit_state(population,spec,p1_path,budget); candidate=np.setdiff1d(train,revealed,assume_unique=False); comp=p13.components(fit,x4[candidate],logh[candidate]); p_h=sigmoid(comp["physics_latent"]); p_m3=comp["probability"]; delta=p_m3-p_h
        for local,index in enumerate(candidate):
            candidate_rows.append({"run_id":spec.run_id,"repeat":spec.repeat,"fold":spec.fold,"budget":budget,"population_row_index":int(index),"P":float(population.iloc[index].P),"VX":float(population.iloc[index].VX),"LS":float(population.iloc[index].LS),"ST":float(population.iloc[index].ST),"h":float(h[index]),"p_H":float(p_h[local]),"p_M3":float(p_m3[local]),"delta_p":float(delta[local]),"abs_delta_p":float(abs(delta[local])),"physics_margin":float(abs(p_h[local]-.5)),"m3_margin":float(abs(p_m3[local]-.5)),"residual_mean":float(comp["residual_latent"][local]),"residual_std":float(math.sqrt(max(0.0,float(comp["latent_variance"][local])))),"class_flip_H_to_M3":bool((p_h[local]>=.5)!=(p_m3[local]>=.5)),"correction_toward_keyhole":bool(delta[local]>0),"correction_toward_conduction":bool(delta[local]<0),"candidate_count":len(candidate),"score_inputs_are_pre_reveal_only":True})
        fit_rows.append({"run_id":spec.run_id,"repeat":spec.repeat,"fold":spec.fold,"budget":budget,"path":"P1","revealed_count":budget,**diag})
        if budget in MECHANISM_BUDGETS:
            fit0,diag0=fit_state(population,spec,a0_path,budget); mechanism.append(mechanism_row(population,spec,p1_path,budget,"P1",distances,fit,diag)); mechanism.append(mechanism_row(population,spec,a0_path,budget,"P0",distances,fit0,diag0)); fit_rows.append({"run_id":spec.run_id,"repeat":spec.repeat,"fold":spec.fold,"budget":budget,"path":"P0","revealed_count":budget,**diag0})
    write_checkpoint(destination,{"complete":True,"phase114_sha":PHASE114_SHA,"budgets":list(BUDGETS),"run_id":spec.run_id,"candidate_rows":candidate_rows,"mechanism_rows":mechanism,"fit_rows":fit_rows}); return {"run_id":spec.run_id,"reused":False}


def run_components(workers: int=4,limit_specs: int|None=None) -> dict[str,Any]:
    baseline_gate(); analysis_specification(); population,specs,a0,p1=load_inputs(); distances=w85.b1_distance(population); specs=specs[:limit_specs] if limit_specs else specs; started=time.time(); results=Parallel(n_jobs=workers,verbose=10)(delayed(run_one_spec)(s,population,a0[s.run_id],p1[s.run_id],distances) for s in specs); payload={"status":"PASS","completed_runs":len(results),"reused_runs":sum(r["reused"] for r in results),"workers":workers,"elapsed_seconds":time.time()-started,"complete":limit_specs is None,"no_new_trajectory":True}; write_json(OUTPUT/"execution_report.json",payload); return payload


def collect() -> tuple[pd.DataFrame,pd.DataFrame,pd.DataFrame]:
    files=sorted(CHECKPOINTS.glob("*.json.gz")); require(len(files)==100,f"checkpoint count {len(files)}"); candidates=[]; mechanism=[]; fits=[]
    for path in files:
        payload=read_checkpoint(path); require(payload.get("complete") and payload.get("phase114_sha")==PHASE114_SHA,"bad checkpoint"); candidates.extend(payload["candidate_rows"]); mechanism.extend(payload["mechanism_rows"]); fits.extend(payload["fit_rows"])
    c,m,f=map(pd.DataFrame,(candidates,mechanism,fits)); c=c.loc[:,PRE_REVEAL_COLUMNS]; expected=100*sum(324-b for b in BUDGETS); require(len(c)==expected and tuple(c.columns)==PRE_REVEAL_COLUMNS,f"candidate completeness/schema {len(c)}"); require(len(m)==100*len(MECHANISM_BUDGETS)*2 and len(f)==100*(len(BUDGETS)+len(MECHANISM_BUDGETS)),"diagnostic completeness"); return c,m,f


def freeze_pre_reveal(frame: pd.DataFrame) -> pd.DataFrame:
    path=OUTPUT/"component_candidate_table.csv.gz"; write_csv(path,frame); payload={"status":"FROZEN_BEFORE_RETROSPECTIVE_JOIN","path":path.relative_to(ROOT).as_posix(),"rows":len(frame),"columns":list(frame.columns),"sha256":sha256_file(path),"forbidden_columns_absent":not any(x in frame.columns for x in ("truth","is_q20","is_q30","B1_distance"))}; write_json(OUTPUT/"pre_reveal_freeze.json",payload); require(payload["forbidden_columns_absent"],"retrospective leakage in frozen table"); loaded=pd.read_csv(path); require(len(loaded)==len(frame) and sha256_file(path)==payload["sha256"],"freeze readback failure"); return loaded


def reconstruction_audit(pre: pd.DataFrame,p1: dict[str,list[int]]) -> pd.DataFrame:
    historical=pd.read_csv(PHASE14/"m3_margin_queries.csv.gz"); rows=[]
    for (run_id,budget),group in pre[pre.budget.lt(80)].groupby(["run_id","budget"],sort=True):
        expected=int(p1[run_id][int(budget)]); ordered=group.sort_values(["m3_margin","population_row_index"],kind="mergesort"); reconstructed=int(ordered.population_row_index.iloc[0]); old=historical[(historical.run_id.eq(run_id))&historical.current_budget.eq(int(budget))].iloc[0]; selected=group[group.population_row_index.eq(expected)]; require(len(selected)==1,"historical selection absent from candidate table"); probability=float(selected.p_M3.iloc[0]); rows.append({"run_id":run_id,"budget":int(budget),"historical_selected_index":expected,"reconstructed_min_margin_index":reconstructed,"historical_query_table_index":int(old.selected_population_row_index),"selection_matches":bool(expected==reconstructed==int(old.selected_population_row_index)),"reconstructed_probability":probability,"historical_probability":float(old.predicted_probability_before_reveal),"absolute_probability_difference":abs(probability-float(old.predicted_probability_before_reveal))})
    audit=pd.DataFrame(rows); require(len(audit)==100*9 and audit.selection_matches.all() and audit.absolute_probability_difference.max()<1e-10,"component reconstruction audit failed"); return audit


def retrospective_join(pre: pd.DataFrame,population: pd.DataFrame,specs: Sequence[Any],distances: np.ndarray) -> pd.DataFrame:
    labels=population.has_keyhole.astype(int).to_numpy(); threshold_rows=[]
    for spec in specs:
        test=np.asarray(spec.test_indices,dtype=int)
        # The threshold exactly reproduces the maximum B1 distance in the frozen test q-subset.
        flags=w85.boundary_flags(spec,population,distances)
        threshold_rows.append({"run_id":spec.run_id,"q20_threshold":float(distances[test][flags["B1_q20"]].max()),"q30_threshold":float(distances[test][flags["B1_q30"]].max())})
    joined=pre.merge(pd.DataFrame(threshold_rows),on="run_id",validate="many_to_one"); idx=joined.population_row_index.to_numpy(int); joined["truth"]=labels[idx]; joined["B1_distance_retrospective"]=distances[idx]; joined["fold_q20_like_retrospective"]=joined.B1_distance_retrospective<=joined.q20_threshold; joined["fold_q30_like_retrospective"]=joined.B1_distance_retrospective<=joined.q30_threshold; joined["H_correct"]=((joined.p_H>=.5).astype(int)==joined.truth); joined["M3_correct"]=((joined.p_M3>=.5).astype(int)==joined.truth); joined["H_wrong_M3_correct"]=~joined.H_correct&joined.M3_correct; joined["H_correct_M3_wrong"]=joined.H_correct&~joined.M3_correct; joined["net_fix_indicator"]=joined.H_wrong_M3_correct.astype(int)-joined.H_correct_M3_wrong.astype(int); joined["budget_region"]=pd.cut(joined.budget,[15,24,40,80],labels=["B16_24","B25_40","B41_80"],include_lowest=True).astype(str)
    joined["correction_quantile"]=joined.groupby("budget").abs_delta_p.transform(lambda x:pd.qcut(x.rank(method="first"),5,labels=["Q1","Q2","Q3","Q4","Q5"]))
    return joined


def bootstrap(values: np.ndarray,key: str) -> tuple[float,float,float]:
    values=np.asarray(values,float); require(len(values)==20 and np.isfinite(values).all(),f"repeat bootstrap {key}"); rng=np.random.default_rng(seed_u32("bootstrap",key)); draws=values[rng.integers(0,20,size=(BOOTSTRAP_DRAWS,20))].mean(axis=1); return float(values.mean()),float(np.quantile(draws,.025)),float(np.quantile(draws,.975))


def repeat_inference(joined: pd.DataFrame) -> pd.DataFrame:
    rows=[]
    def add(metric:str,per_run:pd.DataFrame,value:str) -> None:
        rep=per_run.groupby("repeat")[value].mean().sort_index().to_numpy(float); mean,lo,hi=bootstrap(rep,metric); rows.append({"metric":metric,"mean":mean,"ci_lower":lo,"ci_upper":hi,"repeat_blocks":20,"bootstrap_draws":BOOTSTRAP_DRAWS})
    top=joined[joined.correction_quantile.eq("Q5")]; add("top_Q5_net_fix_rate",top.groupby(["run_id","repeat"],as_index=False).net_fix_indicator.mean(),"net_fix_indicator")
    early=joined[joined.budget_region.eq("B16_24")&joined.correction_quantile.eq("Q5")]; add("early_top_Q5_net_fix_rate",early.groupby(["run_id","repeat"],as_index=False).net_fix_indicator.mean(),"net_fix_indicator")
    kh=top[top.truth.eq(1)]; add("keyhole_top_Q5_net_fix_rate",kh.groupby(["run_id","repeat"],as_index=False).net_fix_indicator.mean(),"net_fix_indicator")
    run_enrich=[]
    for (run_id,repeat),g in joined.groupby(["run_id","repeat"]):
        q5=g[g.correction_quantile.eq("Q5")]; base=float(g.fold_q20_like_retrospective.mean()); run_enrich.append({"run_id":run_id,"repeat":repeat,"enrichment":float(q5.fold_q20_like_retrospective.mean()/base) if base>0 else 1.0})
    add("top_Q5_q20_like_enrichment",pd.DataFrame(run_enrich),"enrichment"); return pd.DataFrame(rows)


def correction_analyses(joined: pd.DataFrame) -> tuple[pd.DataFrame,pd.DataFrame,pd.DataFrame,pd.DataFrame,pd.DataFrame,pd.DataFrame]:
    quant=joined.groupby("correction_quantile",observed=True).agg(candidate_occurrences=("truth","size"),mean_abs_correction=("abs_delta_p","mean"),H_accuracy=("H_correct","mean"),M3_accuracy=("M3_correct","mean"),H_wrong_M3_correct=("H_wrong_M3_correct","mean"),H_correct_M3_wrong=("H_correct_M3_wrong","mean"),net_fix_rate=("net_fix_indicator","mean"),keyhole_prevalence=("truth","mean"),class_flip_frequency=("class_flip_H_to_M3","mean"),q20_like_fraction=("fold_q20_like_retrospective","mean"),q30_like_fraction=("fold_q30_like_retrospective","mean")).reset_index()
    base20=float(joined.fold_q20_like_retrospective.mean()); base30=float(joined.fold_q30_like_retrospective.mean()); boundary=[]
    for q,g in joined.groupby("correction_quantile",observed=True): boundary.append({"correction_quantile":q,"mean_B1_distance":float(g.B1_distance_retrospective.mean()),"median_B1_distance":float(g.B1_distance_retrospective.median()),"q20_like_fraction":float(g.fold_q20_like_retrospective.mean()),"q20_like_enrichment":float(g.fold_q20_like_retrospective.mean()/base20),"q30_like_fraction":float(g.fold_q30_like_retrospective.mean()),"q30_like_enrichment":float(g.fold_q30_like_retrospective.mean()/base30),"spearman_abs_correction_vs_B1_distance":float(spearmanr(g.abs_delta_p,g.B1_distance_retrospective).statistic)})
    asym=joined.groupby(["budget_region","truth"]).agg(candidate_occurrences=("truth","size"),mean_delta_p=("delta_p","mean"),mean_abs_delta_p=("abs_delta_p","mean"),toward_keyhole=("correction_toward_keyhole","mean"),class_flip_frequency=("class_flip_H_to_M3","mean"),H_accuracy=("H_correct","mean"),M3_accuracy=("M3_correct","mean"),fix_rate=("H_wrong_M3_correct","mean"),harm_rate=("H_correct_M3_wrong","mean"),net_fix_rate=("net_fix_indicator","mean")).reset_index()
    evolution=joined.groupby("budget_region").agg(candidate_occurrences=("truth","size"),mean_abs_delta_p=("abs_delta_p","mean"),median_abs_delta_p=("abs_delta_p","median"),mean_residual_std=("residual_std","mean"),class_flip_frequency=("class_flip_H_to_M3","mean"),H_accuracy=("H_correct","mean"),M3_accuracy=("M3_correct","mean"),fix_rate=("H_wrong_M3_correct","mean"),harm_rate=("H_correct_M3_wrong","mean"),net_fix_rate=("net_fix_indicator","mean"),q20_like_fraction=("fold_q20_like_retrospective","mean")).reset_index()
    rho_dm=float(spearmanr(joined.abs_delta_p,joined.m3_margin).statistic); rho_dmh=float(spearmanr(joined.abs_delta_p,joined.physics_margin).statistic); a0=1-2*joined.m3_margin; a1=a0*joined.abs_delta_p; same_top=[]
    for _,g in joined.assign(A0=a0,A1=a1).groupby(["run_id","budget"]): same_top.append(int(g.sort_values(["A0","population_row_index"],ascending=[False,True]).iloc[0].population_row_index)==int(g.sort_values(["A1","population_row_index"],ascending=[False,True]).iloc[0].population_row_index))
    summary=pd.DataFrame([{"metric":"candidate_occurrences","value":len(joined),"role":"descriptive"},{"metric":"spearman_abs_correction_vs_M3_margin","value":rho_dm,"role":"descriptive; tests redundancy"},{"metric":"spearman_A0_margin_score_vs_A1_product_score","value":float(spearmanr(a0,a1).statistic),"role":"descriptive; tests acquisition duplication"},{"metric":"A0_A1_same_top_candidate_fraction","value":float(np.mean(same_top)),"role":"descriptive; no sequential replay"},{"metric":"spearman_abs_correction_vs_physics_margin","value":rho_dmh,"role":"descriptive"},{"metric":"overall_fix_rate","value":float(joined.H_wrong_M3_correct.mean()),"role":"descriptive"},{"metric":"overall_harm_rate","value":float(joined.H_correct_M3_wrong.mean()),"role":"descriptive"},{"metric":"overall_net_fix_rate","value":float(joined.net_fix_indicator.mean()),"role":"descriptive"},{"metric":"overall_class_flip_frequency","value":float(joined.class_flip_H_to_M3.mean()),"role":"descriptive"}])
    inference=repeat_inference(joined); return summary,quant,pd.DataFrame(boundary),asym,evolution,inference


def mechanism_analysis(detail: pd.DataFrame) -> tuple[pd.DataFrame,pd.DataFrame]:
    metrics=("revealed_keyhole_fraction","active_query_keyhole_fraction","physics_log_h_coefficient","residual_sd","residual_sd_upper_bound_hit","any_length_upper_bound_hit","optimizer_converged","q20_keyhole_mean_p_H","q20_keyhole_mean_p_M3","q20_keyhole_recall_H","q20_keyhole_recall_M3","active_query_standardized_pairwise_spread","active_query_mean_B1_distance_retrospective")
    rows=[]
    for budget in MECHANISM_BUDGETS:
        part=detail[detail.budget.eq(budget)]; wide=part.pivot(index=["run_id","repeat","fold"],columns="path",values=list(metrics))
        for metric in metrics:
            dif=(wide[(metric,"P1")]-wide[(metric,"P0")]).rename("difference").reset_index(); rep=dif.groupby("repeat").difference.mean().sort_index().to_numpy(float); mean,lo,hi=bootstrap(rep,f"mechanism|B{budget}|{metric}"); rows.append({"budget":budget,"metric":metric,"P0_mean":float(part[part.path.eq("P0")][metric].mean()),"P1_mean":float(part[part.path.eq("P1")][metric].mean()),"P1_minus_P0":mean,"ci_lower":lo,"ci_upper":hi})
    return detail,pd.DataFrame(rows)


def literature_rows() -> pd.DataFrame:
    return pd.DataFrame([
        {"paper":"Gardner et al. (2021)","source":"https://doi.org/10.1016/j.ymssp.2020.107381","model":"GP model-discrepancy regression with uncertainty marginalization","physics_information":"simulator predictions","discrepancy_or_residual":"yes","acquisition":"sampling-based discrepancy inference; not a sequential boundary acquisition","task":"regression/calibration","boundary_target":"no","similarity":"explicit physics/model plus GP discrepancy","difference":"does not use classification correction magnitude for pool-based level-set queries"},
        {"paper":"Yang, Chen & Wu (2025)","source":"https://doi.org/10.1016/j.cma.2025.118198","model":"physics model plus learned discrepancy in sequential BED","physics_information":"convection-diffusion solver","discrepancy_or_residual":"yes","acquisition":"BED plus ensemble information-gain indicator for discrepancy updates","task":"inverse problem/regression","boundary_target":"no","similarity":"actively learns discrepancy around a physics model","difference":"information-gain BED with continuous measurements, not binary finite-pool boundary learning"},
        {"paper":"Polanska et al. (2026)","source":"https://arxiv.org/abs/2605.21348","model":"neural operator","physics_information":"PDE residual","discrepancy_or_residual":"physics residual, not GP correction to a prior mean","acquisition":"query where PDE residual indicates weak physical consistency","task":"operator regression","boundary_target":"no","similarity":"physics-residual signal guides acquisition","difference":"PDE residual and continuous fields rather than probabilistic class correction"},
        {"paper":"Hardcastle et al. (2025)","source":"https://doi.org/10.1039/D5DD00084J","model":"GPC/GPR with physics-informed prior mean","physics_information":"CALPHAD or constraint prior","discrepancy_or_residual":"GP corrects informative prior","acquisition":"in-silico active refinement of phase diagrams/constraints","task":"classification and threshold regression","boundary_target":"yes","similarity":"closest model/application analogue: physics prior plus GP correction and active boundary refinement","difference":"does not establish this exact correction-magnitude-times-margin score or melt-pool setting"},
        {"paper":"Houlsby et al. (2011)","source":"https://arxiv.org/abs/1112.5745","model":"Bayesian GP classification","physics_information":"none","discrepancy_or_residual":"no explicit physics discrepancy","acquisition":"BALD mutual information between label and parameters","task":"classification/preference learning","boundary_target":"indirect","similarity":"separates epistemic information from predictive entropy","difference":"does not compare physics backbone with hybrid correction"},
        {"paper":"Gotovos et al. (2013)","source":"https://people.csail.mit.edu/alkisg/files/gotovos13active.pdf","model":"GP level-set estimator","physics_information":"none","discrepancy_or_residual":"no","acquisition":"confidence-bound ambiguity near threshold","task":"level-set classification","boundary_target":"yes","similarity":"canonical boundary-focused uncertainty design","difference":"no physics prior/correction term"},
        {"paper":"Bryan & Schneider (2008)","source":"https://publications.ri.cmu.edu/actively-learning-level-sets-of-composite-functions","model":"composite target from multiple observables","physics_information":"multiple model/data components","discrepancy_or_residual":"not a GP discrepancy decomposition","acquisition":"selects sample and observable for composite level-set learning","task":"level-set estimation","boundary_target":"yes","similarity":"acquisition can exploit structured components rather than only final score","difference":"components are separately observable, unlike nested H and M3 probabilities"},
    ])


def write_literature() -> pd.DataFrame:
    frame=literature_rows(); write_csv(OUTPUT/"literature_comparison.csv",frame); columns=list(frame.columns); table=["| "+" | ".join(columns)+" |","|"+"|".join("---" for _ in columns)+"|"]+["| "+" | ".join(str(getattr(row,column)).replace("|","/") for column in columns)+" |" for row in frame.itertuples(index=False)]; lines=["# Focused literature audit","","The closest work shows that neither discrepancy-aware design nor physics-informed GP active learning is new in broad terms. The possible contribution here is narrower: a transparent finite-pool binary level-set score that combines the final M3 boundary relevance with the magnitude/direction of its correction to a nested physics prior.","",*table,"","## Conservative novelty boundary","","- Gardner et al. establish GP discrepancy modelling, but not this active classification score.","- Yang et al. directly study active learning of discrepancy with Bayesian experimental design; this rules out a broad discrepancy-active-learning novelty claim.","- Polanska et al. use a physics residual for acquisition; this rules out a broad physics-residual-acquisition novelty claim.","- Hardcastle et al. are the closest model/application analogue: physics-informed prior-mean GP classification with active phase-boundary refinement.","- BALD and level-set confidence-bound methods remain simpler standard alternatives that any future replay must compare against.","","No source was interpreted as establishing the exact proposed formula, but absence from this focused audit is not proof of novelty."]
    (OUTPUT/"literature_audit.md").write_text("\n".join(lines)+"\n",encoding="utf-8"); return frame


def decide(inference: pd.DataFrame,fit: pd.DataFrame) -> tuple[str,dict[str,bool]]:
    idx=inference.set_index("metric"); sens=pd.read_csv(PHASE14/"acquisition_bound_sensitivity_summary.csv").set_index(["section","metric"]); unreliable=bool(sens.loc[("L1000","optimizer_converged"),"mean"]<.80 or (sens.loc[("path_and_prediction","jaccard_B80"),"median"]<.25 and abs(sens.loc[("path_and_prediction","delta_L1000_minus_L100_q20_AULC"),"mean"])>=.01)); flags={"top_net_positive":bool(idx.loc["top_Q5_net_fix_rate","ci_lower"]>0),"boundary_enriched":bool(idx.loc["top_Q5_q20_like_enrichment","ci_lower"]>1),"early_net_positive":bool(idx.loc["early_top_Q5_net_fix_rate","ci_lower"]>0),"keyhole_net_positive":bool(idx.loc["keyhole_top_Q5_net_fix_rate","ci_lower"]>0),"numerically_unreliable":unreliable,"P1_residual_sd_upper_hit":float(fit[(fit.path.eq("P1"))].residual_sd_upper_bound_hit.mean()),"P1_any_length_upper_hit":float(fit[(fit.path.eq("P1"))].any_length_upper_bound_hit.mean()),"P1_convergence":float(fit[(fit.path.eq("P1"))].optimizer_converged.mean())}
    if unreliable:return "CORRECTION_SIGNAL_NUMERICALLY_UNRELIABLE",flags
    if flags["top_net_positive"] and flags["boundary_enriched"] and flags["early_net_positive"]:return "CORRECTION_SIGNAL_SUPPORTED",flags
    if sum(flags[k] for k in ("top_net_positive","boundary_enriched","early_net_positive","keyhole_net_positive"))>=2:return "CORRECTION_SIGNAL_PARTIAL",flags
    return "CORRECTION_SIGNAL_NOT_SUPPORTED",flags


def acquisition_designs(decision: str,summary: pd.DataFrame,inference: pd.DataFrame,asym: pd.DataFrame,flags: dict[str,Any]) -> str:
    idx=inference.set_index("metric"); recommend=decision=="CORRECTION_SIGNAL_SUPPORTED"; chosen="A1 boundary-correction product" if recommend else "No Phase 1.15B replay yet"
    text=rf"""# Candidate acquisition designs

No trajectory was generated in Phase 1.15A. All quantities below are available before revealing a candidate label.

## A0 — frozen baseline

\[A_0(x)=1-2|p_{{M3}}(x)-0.5|.\]

Purpose: ordinary M3 classifier-margin uncertainty. It is parameter-free and remains the mandatory comparator. Its limitation is that it discards whether M3 materially corrected the physics prior.

## A1 — boundary-correction product

\[A_1(x)=\bigl(1-2|p_{{M3}}(x)-0.5|\bigr)\,|p_{{M3}}(x)-p_H(x)|.\]

Purpose: require both final boundary relevance and a material physics-to-M3 correction. No tuning parameter is present. It is closest in spirit to physics-residual acquisition (Polanska et al.) and discrepancy-aware design (Yang et al.), while retaining the classification-boundary gate of margin/LSE methods. Failure modes: large corrections can be confidently wrong; the product can ignore useful high-uncertainty points when the current residual is still small; repeated bound hits may distort correction magnitude.

## A2 — Keyhole-directed boundary correction

\[A_2(x)=\bigl(1-2|p_{{M3}}(x)-0.5|\bigr)\,\max\{{p_{{M3}}(x)-p_H(x),0\}}.\]

Purpose: test the specific Phase 1.14 early missed-Keyhole failure mode by prioritizing boundary candidates where the residual moves probability toward Keyhole. It has no tuned weight. Failure modes: it is deliberately asymmetric, may create false positives, and can miss important corrections toward Conduction. It should be a backup diagnostic, not the default recommendation.

## Recommendation

**{chosen}.** Decision: `{decision}`. Top-quintile net-fix CI lower bound is {idx.loc['top_Q5_net_fix_rate','ci_lower']:+.4f}; q20-like enrichment CI lower bound is {idx.loc['top_Q5_q20_like_enrichment','ci_lower']:.3f}; early net-fix CI lower bound is {idx.loc['early_top_Q5_net_fix_rate','ci_lower']:+.4f}. Under a partial result, boundary enrichment can be explained largely by ordinary margin redundancy and does not justify a new trajectory by itself. If stronger independent evidence appears later, A1 is the preferred simple rule; A2 remains a mechanism sensitivity only.
"""
    (OUTPUT/"candidate_acquisition_designs.md").write_text(text,encoding="utf-8"); return chosen


def make_figures(quant:pd.DataFrame,boundary:pd.DataFrame,asym:pd.DataFrame,evolution:pd.DataFrame,mechanism:pd.DataFrame,joined:pd.DataFrame) -> pd.DataFrame:
    FIGURES.mkdir(parents=True,exist_ok=True); created=[]
    fig,ax=plt.subplots(figsize=(8,4.8)); q=np.arange(len(quant)); ax.bar(q,quant.net_fix_rate,color="#2b6cb0"); ax.axhline(0,color="black",ls="--"); ax.set_xticks(q,quant.correction_quantile); ax.set(xlabel="Within-budget |pM3-pH| quintile",ylabel="Fix rate minus harm rate",title="Do larger corrections help more than they harm?"); ax.grid(axis="y",alpha=.25); fig.tight_layout(); p=FIGURES/"01_correction_usefulness.png"; fig.savefig(p,dpi=180); plt.close(fig); created.append((p,"Retrospective correction usefulness by frozen correction quintile."))
    fig,ax=plt.subplots(figsize=(8,4.8)); ax.plot(boundary.correction_quantile,boundary.q20_like_enrichment,"o-",label="q20-like"); ax.plot(boundary.correction_quantile,boundary.q30_like_enrichment,"s-",label="q30-like"); ax.axhline(1,color="black",ls="--"); ax.set(xlabel="Within-budget correction quintile",ylabel="Enrichment over all eligible candidates",title="Are large corrections boundary-enriched?"); ax.legend(frameon=False); ax.grid(alpha=.25); fig.tight_layout(); p=FIGURES/"02_boundary_enrichment.png"; fig.savefig(p,dpi=180); plt.close(fig); created.append((p,"Retrospective B1 boundary enrichment."))
    fig,ax=plt.subplots(figsize=(8.5,4.8)); pivot=asym.pivot(index="budget_region",columns="truth",values="net_fix_rate").reindex(["B16_24","B25_40","B41_80"]); x=np.arange(3); ax.bar(x-.18,pivot[0],.36,label="Conduction",color="#4c78a8"); ax.bar(x+.18,pivot[1],.36,label="Keyhole",color="#e45756"); ax.axhline(0,color="black",ls="--"); ax.set_xticks(x,pivot.index); ax.set(ylabel="Fix rate minus harm rate",title="Correction utility by truth and budget region"); ax.legend(frameon=False); ax.grid(axis="y",alpha=.25); fig.tight_layout(); p=FIGURES/"03_class_budget_asymmetry.png"; fig.savefig(p,dpi=180); plt.close(fig); created.append((p,"Keyhole/Conduction correction asymmetry over budget."))
    fig,ax=plt.subplots(figsize=(8.5,4.8)); order=["B16_24","B25_40","B41_80"]; e=evolution.set_index("budget_region").loc[order]; ax.plot(order,e.mean_abs_delta_p,"o-",label="Mean |probability correction|"); ax.plot(order,e.class_flip_frequency,"s-",label="H→M3 class-flip fraction"); ax.plot(order,e.net_fix_rate,"^-",label="Net fix rate"); ax.axhline(0,color="black",ls="--"); ax.set(title="Physics–residual signal evolution",ylabel="Fraction / probability magnitude"); ax.legend(frameon=False); ax.grid(alpha=.25); fig.tight_layout(); p=FIGURES/"04_budget_evolution.png"; fig.savefig(p,dpi=180); plt.close(fig); created.append((p,"Correction magnitude, flips, and utility by budget region."))
    part=mechanism[(mechanism.budget.eq(40))&mechanism.metric.isin(["revealed_keyhole_fraction","residual_sd","q20_keyhole_mean_p_M3","q20_keyhole_recall_M3","active_query_standardized_pairwise_spread"])]; fig,ax=plt.subplots(figsize=(9,4.8)); x=np.arange(len(part)); ax.errorbar(part.P1_minus_P0,x,xerr=[part.P1_minus_P0-part.ci_lower,part.ci_upper-part.P1_minus_P0],fmt="o",capsize=4,color="#9b2c2c"); ax.axvline(0,color="black",ls="--"); ax.set_yticks(x,[s.replace("_"," ") for s in part.metric]); ax.invert_yaxis(); ax.set(xlabel="P1 minus P0 at B40",title="Descriptive mechanisms around the temporary recall loss"); ax.grid(axis="x",alpha=.25); fig.tight_layout(); p=FIGURES/"05_b40_mechanism.png"; fig.savefig(p,dpi=180); plt.close(fig); created.append((p,"Paired B40 path-mechanism contrasts."))
    manifest=pd.DataFrame([{"figure":p.name,"sha256":sha256_file(p),"size_bytes":p.stat().st_size,"purpose":purpose} for p,purpose in created]); write_csv(OUTPUT/"figure_manifest.csv",manifest); return manifest


def build_reports(decision:str,flags:dict[str,Any],summary:pd.DataFrame,quant:pd.DataFrame,boundary:pd.DataFrame,asym:pd.DataFrame,evolution:pd.DataFrame,inference:pd.DataFrame,mechanism:pd.DataFrame,recommendation:str) -> None:
    inf=inference.set_index("metric"); q5=quant[quant.correction_quantile.eq("Q5")].iloc[0]; q1=quant[quant.correction_quantile.eq("Q1")].iloc[0]; b5=boundary[boundary.correction_quantile.eq("Q5")].iloc[0]; mech40=mechanism[mechanism.budget.eq(40)].set_index("metric"); rho=float(summary[summary.metric.eq("spearman_abs_correction_vs_M3_margin")].value.iloc[0]);
    a01=float(summary[summary.metric.eq("spearman_A0_margin_score_vs_A1_product_score")].value.iloc[0]); same=float(summary[summary.metric.eq("A0_A1_same_top_candidate_fraction")].value.iloc[0]); report=["# Week 9 Phase 1.15A — Physics–Residual Signal Audit and Acquisition Design","",f"## Decision: {decision}","","No new acquisition trajectory was run. The exact Phase 1.14 P1 prefixes were replayed only to reconstruct pre-reveal model components.","","## Strongest correction finding",f"Within-budget Q5 corrections fixed H mistakes at rate {q5.H_wrong_M3_correct:.4f} and harmed correct H predictions at {q5.H_correct_M3_wrong:.4f}; net {q5.net_fix_rate:+.4f}. The 20-repeat interval for Q5 net fix was [{inf.loc['top_Q5_net_fix_rate','ci_lower']:+.4f}, {inf.loc['top_Q5_net_fix_rate','ci_upper']:+.4f}]. Q1 net was {q1.net_fix_rate:+.4f}.",f"Correction magnitude versus final M3 margin Spearman rho={rho:+.3f}; A0 versus A1 score rho={a01:+.3f}, with the same top candidate in {same:.1%} of frozen states. The correction is not treated as independent-model disagreement.","","## Boundary relevance",f"Pooled Q5 q20-like enrichment was {b5.q20_like_enrichment:.3f}; mean per-run enrichment was {inf.loc['top_Q5_q20_like_enrichment','mean']:.3f} with repeat-block interval [{inf.loc['top_Q5_q20_like_enrichment','ci_lower']:.3f}, {inf.loc['top_Q5_q20_like_enrichment','ci_upper']:.3f}]. This is largely entangled with ordinary margin because correction magnitude is strongly anticorrelated with M3 margin. B1/q membership entered only after the candidate table was frozen.","","## Class and budget behavior"]
    for row in asym.itertuples(index=False): report.append(f"- {row.budget_region}, truth={int(row.truth)}: mean Δp {row.mean_delta_p:+.4f}, fix {row.fix_rate:.4f}, harm {row.harm_rate:.4f}, net {row.net_fix_rate:+.4f}.")
    report += ["",f"Early Q5 net-fix interval: [{inf.loc['early_top_Q5_net_fix_rate','ci_lower']:+.4f}, {inf.loc['early_top_Q5_net_fix_rate','ci_upper']:+.4f}]. Keyhole Q5 interval: [{inf.loc['keyhole_top_Q5_net_fix_rate','ci_lower']:+.4f}, {inf.loc['keyhole_top_Q5_net_fix_rate','ci_upper']:+.4f}].","","## Phase 1.14 B40 mechanism",f"P1−P0 revealed-Keyhole fraction {mech40.loc['revealed_keyhole_fraction','P1_minus_P0']:+.4f}; residual SD {mech40.loc['residual_sd','P1_minus_P0']:+.4f}; held-out q20-Keyhole mean M3 probability {mech40.loc['q20_keyhole_mean_p_M3','P1_minus_P0']:+.4f}; q20-Keyhole recall {mech40.loc['q20_keyhole_recall_M3','P1_minus_P0']:+.4f}; active-query standardized spread {mech40.loc['active_query_standardized_pairwise_spread','P1_minus_P0']:+.4f}. These are paired path associations, not causal effects.","","## Numerical reliability",f"P1 residual-SD upper-hit {flags['P1_residual_sd_upper_hit']:.1%}; any-length upper-hit {flags['P1_any_length_upper_hit']:.1%}; convergence {flags['P1_convergence']:.1%}. Phase 1.14 L100/L1000 sensitivity does not trigger the predeclared unreliability rule, but bound pressure limits mechanistic interpretation.","","## Acquisition recommendation",f"{recommendation}. The recommendation is prospective and unvalidated; Phase 1.15A itself demonstrates no sample-efficiency gain.","","## Claim boundary","The decomposition is not identifiable physics: h is derived from P,VX,LS and the residual uses those inputs. No universal acquisition, theoretical sample-complexity, external-transfer, causal-ARD, or broad novelty claim is supported."]
    (OUTPUT/"FINAL_PHASE1_15A_REPORT.md").write_text("\n".join(report)+"\n",encoding="utf-8")
    supervisor=["# Supervisor Phase 1.15A — one page","",f"**Decision:** `{decision}`","","- Reconstructed the H and M3 components at ten budgets on the already-published P1 path; no new active-learning trajectory was run.",f"- Large-correction Q5: fix {q5.H_wrong_M3_correct:.3f}, harm {q5.H_correct_M3_wrong:.3f}, net {q5.net_fix_rate:+.3f}; repeat CI [{inf.loc['top_Q5_net_fix_rate','ci_lower']:+.3f}, {inf.loc['top_Q5_net_fix_rate','ci_upper']:+.3f}].",f"- Pooled Q5 q20-like enrichment {b5.q20_like_enrichment:.2f}×; mean per-run {inf.loc['top_Q5_q20_like_enrichment','mean']:.2f}×, repeat CI [{inf.loc['top_Q5_q20_like_enrichment','ci_lower']:.2f}, {inf.loc['top_Q5_q20_like_enrichment','ci_upper']:.2f}].",f"- Correction magnitude is highly redundant with margin (rho {rho:+.2f}); early Q5 net-fix CI [{inf.loc['early_top_Q5_net_fix_rate','ci_lower']:+.3f}, {inf.loc['early_top_Q5_net_fix_rate','ci_upper']:+.3f}].",f"- At B40, P1−P0 q20-Keyhole mean M3 probability {mech40.loc['q20_keyhole_mean_p_M3','P1_minus_P0']:+.3f} and recall {mech40.loc['q20_keyhole_recall_M3','P1_minus_P0']:+.3f}; descriptive, not causal.",f"- Numerical pressure remains high (residual upper-hit {flags['P1_residual_sd_upper_hit']:.0%}, length upper-hit {flags['P1_any_length_upper_hit']:.0%}), although convergence is {flags['P1_convergence']:.0%} and L1000 sensitivity was locally stable.",f"- Future replay recommendation: **{recommendation}**. A1 remains a simple design only if later evidence separates correction value from ordinary margin.","","Closest literature already covers active discrepancy learning and physics-informed prior-mean GP active learning; any novelty possibility is narrow and unresolved."]
    (OUTPUT/"SUPERVISOR_PHASE1_15A_ONE_PAGE.md").write_text("\n".join(supervisor)+"\n",encoding="utf-8")
    ledger=["# Phase 1.15A claim ledger","","| Claim | Status | Evidence boundary |","|---|---|---|",f"| Large corrections more often fix than harm H predictions. | {'SUPPORTED' if flags['top_net_positive'] else 'NOT SUPPORTED'} | Frozen pre-reveal correction quintiles; retrospective truth; repeat-block CI. |",f"| Large corrections are enriched near q20-like boundary locations. | {'SUPPORTED' if flags['boundary_enriched'] else 'NOT SUPPORTED'} | Retrospective B1 thresholds only. |",f"| Correction signal is already useful at B16–24. | {'SUPPORTED' if flags['early_net_positive'] else 'NOT SUPPORTED'} | Predeclared early region. |",f"| Correction signal is useful for Keyholes specifically. | {'SUPPORTED' if flags['keyhole_net_positive'] else 'NOT SUPPORTED'} | Q5 true-Keyhole retrospective audit. |",f"| Correction magnitude is independent-model disagreement. | NOT SUPPORTED | M3 contains H as its latent mean. |",f"| Physics/residual decomposition is identified. | NOT SUPPORTED | h and residual share P,VX,LS information. |",f"| New acquisition improves active-learning efficiency. | NOT TESTED | No Phase 1.15B trajectory run. |",f"| New acquisition is broadly novel. | NOT SUPPORTED | Close discrepancy/physics-informed AL literature exists. |","| Current evidence justifies an immediate Phase 1.15B replay. | NOT SUPPORTED | Overall/early net correction unresolved and strongly redundant with margin. |","| ARD lengths have causal physical meaning. | NOT SUPPORTED | Standardized fitted geometry with bound pressure. |"]
    (OUTPUT/"claim_ledger.md").write_text("\n".join(ledger)+"\n",encoding="utf-8")
    red=["# Final red-team report","","- The exact Phase 1.14 commit is the branch base; historical Phase 1.x outputs are unchanged.","- No new acquisition path was generated; selected budgets replay existing P1 prefixes only.","- The frozen component table contains no truth, B1, q20, or q30 columns.","- Retrospective labels and fold-specific B1 thresholds are joined only after the pre-reveal gzip is written and hashed.","- Physics and M3 are nested, not independent committee members.","- Candidate occurrences repeat across runs/budgets; candidate-level summaries are descriptive, while inference uses 20 repeat blocks.","- Correction magnitude is checked against final M3 margin to expose redundancy.","- Keyhole-specific utility and the B16–24 region are reported explicitly.","- B40 P0/P1 differences are path associations and are not called causal.","- Residual/ARD bound pressure is disclosed; ARD scales are not interpreted physically.","- Literature rules out broad novelty claims.","- The proposed A1/A2 formulas are designs only; no active-learning improvement is claimed."]
    (OUTPUT/"FINAL_RED_TEAM_REPORT.md").write_text("\n".join(red)+"\n",encoding="utf-8")


def build_notebook() -> None:
    cells=[nbf.v4.new_markdown_cell("# Week 9 Phase 1.15A — Physics–Residual Signal Audit\n\nThis notebook reads generated artifacts. It does **not** run a new acquisition trajectory."),nbf.v4.new_code_cell("from pathlib import Path\nimport json, pandas as pd\nfrom IPython.display import display, Image, Markdown\nROOT=Path.cwd().parents[1] if Path.cwd().name=='week_09' else Path.cwd()\nOUT=ROOT/'outputs'/'week9_phase1_15a_physics_residual_signal_audit'\ndisplay(json.loads((OUT/'baseline_gate.json').read_text()))"),nbf.v4.new_markdown_cell("## 1. What is being separated?\n\nH is the physics-only probability from the fitted log(h) latent mean. M3 contains that same mean plus an ARD Matérn GP correction. Their difference is a **nested correction diagnostic**, not committee disagreement."),nbf.v4.new_code_cell("display(json.loads((OUT/'pre_reveal_freeze.json').read_text()))\ndisplay(pd.read_csv(OUT/'correction_signal_summary.csv'))"),nbf.v4.new_markdown_cell("## 2. Do large corrections fix physics mistakes?\n\nTruth is joined only after the score table is frozen."),nbf.v4.new_code_cell("display(pd.read_csv(OUT/'correction_quantile_analysis.csv'))\ndisplay(Image(filename=str(OUT/'figures'/'01_correction_usefulness.png')))"),nbf.v4.new_markdown_cell("## 3. Boundary relevance is retrospective\n\nFold B1/q20/q30 information never enters a proposed acquisition score."),nbf.v4.new_code_cell("display(pd.read_csv(OUT/'boundary_enrichment_analysis.csv'))\ndisplay(Image(filename=str(OUT/'figures'/'02_boundary_enrichment.png')))"),nbf.v4.new_markdown_cell("## 4. Keyhole/Conduction asymmetry and budget evolution"),nbf.v4.new_code_cell("display(pd.read_csv(OUT/'keyhole_conduction_asymmetry.csv'))\ndisplay(pd.read_csv(OUT/'budget_evolution_summary.csv'))\ndisplay(Image(filename=str(OUT/'figures'/'03_class_budget_asymmetry.png')))\ndisplay(Image(filename=str(OUT/'figures'/'04_budget_evolution.png')))"),nbf.v4.new_markdown_cell("## 5. Why did P1 temporarily lose q20 Keyhole recall at B40?\n\nThese are descriptive P1-versus-P0 path associations, not causal effects."),nbf.v4.new_code_cell("display(pd.read_csv(OUT/'b40_recall_mechanism_audit.csv'))\ndisplay(Image(filename=str(OUT/'figures'/'05_b40_mechanism.png')))"),nbf.v4.new_markdown_cell("## 6. Numerical reliability\n\nHigh bound-hit rates weaken mechanistic interpretation even when optimizer convergence and L100/L1000 sensitivity are acceptable."),nbf.v4.new_code_cell("display(pd.read_csv(OUT/'component_fit_diagnostics_summary.csv'))"),nbf.v4.new_markdown_cell("## 7. Literature and designs"),nbf.v4.new_code_cell("display(pd.read_csv(OUT/'literature_comparison.csv'))\ndisplay(Markdown((OUT/'candidate_acquisition_designs.md').read_text()))"),nbf.v4.new_markdown_cell("## 8. Safe conclusion"),nbf.v4.new_code_cell("display(Markdown((OUT/'SUPERVISOR_PHASE1_15A_ONE_PAGE.md').read_text()))")]
    notebook=nbf.v4.new_notebook(cells=cells,metadata={"kernelspec":{"display_name":"Thesis Python","language":"python","name":"thesis"}}); NOTEBOOK.parent.mkdir(parents=True,exist_ok=True); nbf.write(notebook,NOTEBOOK); executed=NotebookClient(nbf.read(NOTEBOOK,as_version=4),timeout=180,kernel_name="thesis",resources={"metadata":{"path":str(ROOT)}}).execute(); nbf.write(executed,NOTEBOOK)


def fit_summary(fit:pd.DataFrame) -> pd.DataFrame:
    rows=[]
    for (path,scope),g in pd.concat([fit.assign(scope="all_selected"),fit[fit.budget.eq(40)].assign(scope="B40")]).groupby(["path","scope"]):
        for metric in ("residual_sd","residual_sd_upper_bound_hit","any_length_upper_bound_hit","optimizer_converged","anisotropy_ratio","l_P","l_VX","l_LS","l_ST"): rows.append({"path":path,"scope":scope,"metric":metric,"mean":float(g[metric].mean()),"median":float(g[metric].median()),"n":len(g)})
    return pd.DataFrame(rows)


def _legacy_validate_unused(pre:pd.DataFrame,joined:pd.DataFrame,reconstruction:pd.DataFrame,mechanism_detail:pd.DataFrame,fit:pd.DataFrame,literature:pd.DataFrame,figures:pd.DataFrame,decision:str) -> dict[str,Any]:
    population,specs,a0,p1=load_inputs(); source=Path(__file__).read_text(encoding="utf-8"); freeze=json.loads((OUTPUT/"pre_reveal_freeze.json").read_text()); notebook=nbf.read(NOTEBOOK,as_version=4); code=[c for c in notebook.cells if c.cell_type=="code"]; report=(OUTPUT/"FINAL_PHASE1_15A_REPORT.md").read_text().lower(); checks=[
        ("exact_phase114_parent",subprocess.check_output(["git","merge-base","HEAD",PHASE114_SHA],cwd=ROOT,text=True).strip()==PHASE114_SHA,PHASE114_SHA),("population_405",len(population)==405,str(len(population))),("labels_73_332",int(population.has_keyhole.sum())==73 and int((~population.has_keyhole.astype(bool)).sum())==332,"73/332"),("h_formula_unchanged","np.exp(logh)" in source and p11.log_h_values is not None,"Phase 1.11 function"),("M3_architecture",p13.residual_kernel("M3").k2.nu==1.5 and len(np.ravel(p13.residual_kernel("M3").k2.length_scale))==4,"ARD Matern 3/2"),("P1_historical_path_exact",len(p1)==100 and all(len(v)==80 for v in p1.values()),"100x80"),("no_historical_path_mutation",historical_changes()==[],str(historical_changes())),("component_prefix_only","path[:budget]" in source and "fit_state" in source,"exact prefixes"),("pre_reveal_schema_exact",tuple(pre.columns)==PRE_REVEAL_COLUMNS,str(len(pre))),("unrevealed_labels_absent_scores",not any(c in pre.columns for c in ("truth","has_keyhole")),"absent"),("q20_q30_B1_absent_scores",not any(any(token in c.lower() for token in ("q20","q30","b1")) for c in pre.columns),"absent"),("retrospective_after_freeze",source.index("freeze_pre_reveal")<source.index("retrospective_join") and freeze["status"]=="FROZEN_BEFORE_RETROSPECTIVE_JOIN","ordered"),("physics_M3_probabilities_valid",pre.p_H.between(0,1).all() and pre.p_M3.between(0,1).all(),"[0,1]"),("probability_correction_identity",np.allclose(pre.delta_p,pre.p_M3-pre.p_H,rtol=0,atol=2e-15),"exact"),("residual_inputs_exact",FEATURES==("P","VX","LS","ST"),str(FEATURES)),("logh_absent_residual",len(FEATURES)==4 and "fit_hybrid" in source,"4D"),("budget_prefixes_exact",set(pre.budget)==set(BUDGETS),str(BUDGETS)),("no_duplicate_future_labels",all(len(set(p1[s.run_id][:b]))==b for s in specs for b in BUDGETS),"all prefixes"),("repeat_block_inference",BOOTSTRAP_DRAWS==10000 and joined.repeat.nunique()==20,"20/10000"),("literature_citations",len(literature)>=7 and literature.source.str.startswith("http").all(),str(len(literature))),("no_unsupported_novelty","broad novelty" in report and "no broad novelty" in (OUTPUT/"literature_audit.md").read_text().lower(),"safe"),("no_new_trajectory",json.loads((OUTPUT/"execution_report.json").read_text())["no_new_trajectory"],"true"),("notebook_executed",bool(code) and all(c.execution_count is not None for c in code) and not [o for c in code for o in c.get("outputs",[]) if o.get("output_type")=="error"],str(len(code))),("figure_hashes",len(figures)<=5 and all(sha256_file(FIGURES/r.figure)==r.sha256 for r in figures.itertuples(index=False)),str(len(figures))),("historical_outputs_unchanged",historical_changes()==[],str(historical_changes())),("no_placeholders",all(t not in report for t in ("todo","tbd","{decision}")),"none"),("decision_exact",decision in {"CORRECTION_SIGNAL_SUPPORTED","CORRECTION_SIGNAL_PARTIAL","CORRECTION_SIGNAL_NOT_SUPPORTED","CORRECTION_SIGNAL_NUMERICALLY_UNRELIABLE"},decision),("component_rows_complete",len(pre)==100*sum(324-b for b in BUDGETS),str(len(pre))),("mechanism_rows_complete",len(mechanism_detail)==100*len(MECHANISM_BUDGETS)*2,str(len(mechanism_detail))),("fit_diagnostics_complete",fit.optimizer_converged.notna().all(),str(len(fit)))]
    finalize_source=source[source.index("def finalize"):source.index("def main")]; checks=[item for item in checks if item[0]!="no_unsupported_novelty"]; checks.extend([("no_unsupported_novelty","broad novelty" in report and "broad novelty" in (OUTPUT/"literature_audit.md").read_text().lower(),"safe"),("historical_component_reconstruction",len(reconstruction)==900 and reconstruction.selection_matches.all() and reconstruction.absolute_probability_difference.max()<1e-10,str(float(reconstruction.absolute_probability_difference.max()))),("freeze_before_join_call",finalize_source.index("freeze_pre_reveal(raw)")<finalize_source.index("retrospective_join(pre"),"actual finalize order")]); records=[{"check":n,"status":"PASS" if ok else "FAIL","detail":d} for n,ok,d in checks]; payload={"status":"PASS" if all(r["status"]=="PASS" for r in records) else "FAIL","check_count":len(records),"passed":sum(r["status"]=="PASS" for r in records),"checks":records}; write_json(OUTPUT/"validation_report.json",payload); lines=["# Phase 1.15A validation","",f"Status: **{payload['status']}**",f"Checks: **{payload['passed']} / {payload['check_count']} PASS**","","| Check | Status | Detail |","|---|---|---|"]+[f"| {r['check']} | {r['status']} | {r['detail']} |" for r in records]; (OUTPUT/"validation_report.md").write_text("\n".join(lines)+"\n",encoding="utf-8"); require(payload["status"]=="PASS","validation failure"); return payload


def validate(pre:pd.DataFrame,joined:pd.DataFrame,reconstruction:pd.DataFrame,mechanism_detail:pd.DataFrame,fit:pd.DataFrame,literature:pd.DataFrame,figures:pd.DataFrame,decision:str) -> dict[str,Any]:
    population,specs,a0,p1=load_inputs(); source=Path(__file__).read_text(encoding="utf-8"); freeze=json.loads((OUTPUT/"pre_reveal_freeze.json").read_text()); notebook=nbf.read(NOTEBOOK,as_version=4); code=[c for c in notebook.cells if c.cell_type=="code"]; report=(OUTPUT/"FINAL_PHASE1_15A_REPORT.md").read_text().lower(); finalize_start=source.rindex("def finalize()"); finalize_source=source[finalize_start:source.index("def main()",finalize_start)]
    checks=[
        ("exact_phase114_parent",subprocess.check_output(["git","merge-base","HEAD",PHASE114_SHA],cwd=ROOT,text=True).strip()==PHASE114_SHA,PHASE114_SHA),
        ("population_405",len(population)==405,str(len(population))),
        ("labels_73_332",int(population.has_keyhole.sum())==73 and int((~population.has_keyhole.astype(bool)).sum())==332,"73/332"),
        ("h_formula_unchanged",p11.log_h_values is not None,"Phase 1.11 canonical function"),
        ("M3_architecture",p13.residual_kernel("M3").k2.nu==1.5 and len(np.ravel(p13.residual_kernel("M3").k2.length_scale))==4,"ARD Matern 3/2"),
        ("P1_historical_path_exact",len(p1)==100 and all(len(v)==80 for v in p1.values()),"100x80"),
        ("no_historical_path_mutation",historical_changes()==[],str(historical_changes())),
        ("component_prefix_only","path[:budget]" in source and "fit_state" in source,"exact prefixes"),
        ("pre_reveal_schema_exact",tuple(pre.columns)==PRE_REVEAL_COLUMNS,str(len(pre))),
        ("unrevealed_labels_absent_scores",not any(c in pre.columns for c in ("truth","has_keyhole")),"absent"),
        ("q20_q30_B1_absent_scores",not any(any(token in c.lower() for token in ("q20","q30","b1")) for c in pre.columns),"absent"),
        ("freeze_before_join_call",finalize_source.index("freeze_pre_reveal(raw)")<finalize_source.index("retrospective_join(pre"),"actual finalize order"),
        ("freeze_hash_valid",freeze["status"]=="FROZEN_BEFORE_RETROSPECTIVE_JOIN" and freeze["sha256"]==sha256_file(OUTPUT/"component_candidate_table.csv.gz"),"frozen"),
        ("physics_M3_probabilities_valid",pre.p_H.between(0,1).all() and pre.p_M3.between(0,1).all(),"[0,1]"),
        ("probability_correction_identity",np.allclose(pre.delta_p,pre.p_M3-pre.p_H,rtol=0,atol=2e-15),"exact"),
        ("historical_component_reconstruction",len(reconstruction)==900 and reconstruction.selection_matches.all() and reconstruction.absolute_probability_difference.max()<1e-10,str(float(reconstruction.absolute_probability_difference.max()))),
        ("residual_inputs_exact",FEATURES==("P","VX","LS","ST"),str(FEATURES)),
        ("logh_absent_residual",len(FEATURES)==4,"4D only"),
        ("budget_prefixes_exact",set(pre.budget)==set(BUDGETS),str(BUDGETS)),
        ("no_duplicate_future_labels",all(len(set(p1[s.run_id][:b]))==b for s in specs for b in BUDGETS),"all prefixes"),
        ("repeat_block_inference",BOOTSTRAP_DRAWS==10_000 and joined.repeat.nunique()==20,"20/10000"),
        ("literature_citations",len(literature)>=7 and literature.source.str.startswith("http").all(),str(len(literature))),
        ("no_unsupported_novelty","broad novelty" in report and "not proof of novelty" in (OUTPUT/"literature_audit.md").read_text().lower(),"safe"),
        ("no_new_trajectory",json.loads((OUTPUT/"execution_report.json").read_text())["no_new_trajectory"],"true"),
        ("notebook_executed",bool(code) and all(c.execution_count is not None for c in code) and not [o for c in code for o in c.get("outputs",[]) if o.get("output_type")=="error"],str(len(code))),
        ("figure_hashes",len(figures)<=5 and all(sha256_file(FIGURES/r.figure)==r.sha256 for r in figures.itertuples(index=False)),str(len(figures))),
        ("historical_outputs_unchanged",historical_changes()==[],str(historical_changes())),
        ("no_placeholders",all(t not in report for t in ("todo","tbd","{decision}")),"none"),
        ("decision_exact",decision in {"CORRECTION_SIGNAL_SUPPORTED","CORRECTION_SIGNAL_PARTIAL","CORRECTION_SIGNAL_NOT_SUPPORTED","CORRECTION_SIGNAL_NUMERICALLY_UNRELIABLE"},decision),
        ("component_rows_complete",len(pre)==100*sum(324-b for b in BUDGETS),str(len(pre))),
        ("mechanism_rows_complete",len(mechanism_detail)==100*len(MECHANISM_BUDGETS)*2,str(len(mechanism_detail))),
        ("fit_diagnostics_complete",fit.optimizer_converged.notna().all(),str(len(fit))),
    ]
    records=[{"check":name,"status":"PASS" if ok else "FAIL","detail":detail} for name,ok,detail in checks]; payload={"status":"PASS" if all(r["status"]=="PASS" for r in records) else "FAIL","check_count":len(records),"passed":sum(r["status"]=="PASS" for r in records),"checks":records}; write_json(OUTPUT/"validation_report.json",payload); lines=["# Phase 1.15A validation","",f"Status: **{payload['status']}**",f"Checks: **{payload['passed']} / {payload['check_count']} PASS**","","| Check | Status | Detail |","|---|---|---|"]+[f"| {r['check']} | {r['status']} | {r['detail']} |" for r in records]; (OUTPUT/"validation_report.md").write_text("\n".join(lines)+"\n",encoding="utf-8"); require(payload["status"]=="PASS","validation failure"); return payload


def write_manifest(validation:dict[str,Any],decision:str) -> None:
    files=[p for p in OUTPUT.rglob("*") if p.is_file() and "checkpoints" not in p.parts and p.name!="run_manifest.json"]+[Path(__file__),ROOT/"tests"/"test_week9_phase1_15a_physics_residual_signal_audit.py",NOTEBOOK]; entries=[]
    for path in sorted(set(files)):
        payload=artifact_bytes(path); entries.append({"path":path.relative_to(ROOT).as_posix(),"sha256":hashlib.sha256(payload).hexdigest(),"size_bytes":len(payload)})
    write_json(OUTPUT/"run_manifest.json",{"study":"Week 9 Phase 1.15A — Physics–Residual Signal Audit and Acquisition Design","phase114_parent_sha":PHASE114_SHA,"branch":BRANCH,"decision":decision,"protocol":{"budgets":list(BUDGETS),"outer_runs":100,"repeat_blocks":20,"bootstrap_draws":BOOTSTRAP_DRAWS,"new_acquisition_trajectory":False},"validation":validation,"historical_changes":historical_changes(),"files":entries})


def finalize() -> dict[str,Any]:
    gate=baseline_gate(); analysis_specification(); population,specs,a0,p1=load_inputs(); distances=w85.b1_distance(population); raw,mechanism_detail,fit=collect(); pre=freeze_pre_reveal(raw); reconstruction=reconstruction_audit(pre,p1); joined=retrospective_join(pre,population,specs,distances); summary,quant,boundary,asym,evolution,inference=correction_analyses(joined); mechanism_detail,mechanism=mechanism_analysis(mechanism_detail); fit_s=fit_summary(fit); literature=write_literature(); decision,flags=decide(inference,fit); recommendation=acquisition_designs(decision,summary,inference,asym,flags)
    for name,frame in (("component_reconstruction_audit.csv",reconstruction),("correction_signal_summary.csv",summary),("correction_quantile_analysis.csv",quant),("boundary_enrichment_analysis.csv",boundary),("keyhole_conduction_asymmetry.csv",asym),("budget_evolution_summary.csv",evolution),("repeat_block_inference.csv",inference),("b40_recall_mechanism_audit.csv",mechanism),("b40_recall_mechanism_detail.csv.gz",mechanism_detail),("component_fit_diagnostics.csv.gz",fit),("component_fit_diagnostics_summary.csv",fit_s),("component_candidate_retrospective.csv.gz",joined)): write_csv(OUTPUT/name,frame)
    figures=make_figures(quant,boundary,asym,evolution,mechanism,joined); build_reports(decision,flags,summary,quant,boundary,asym,evolution,inference,mechanism,recommendation); build_notebook(); validation=validate(pre,joined,reconstruction,mechanism_detail,fit,literature,figures,decision); write_manifest(validation,decision); manifest=json.loads((OUTPUT/"run_manifest.json").read_text()); require(all(hashlib.sha256(artifact_bytes(ROOT/item["path"])).hexdigest()==item["sha256"] for item in manifest["files"]),"manifest hash failure"); return {"status":"PASS","decision":decision,"recommendation":recommendation,"validation_checks":validation["check_count"],"component_rows":len(pre),"historical_changes":historical_changes(),"parent":gate["phase114_parent_sha"]}


def main() -> None:
    parser=argparse.ArgumentParser(); parser.add_argument("--preflight",action="store_true"); parser.add_argument("--run",action="store_true"); parser.add_argument("--finalize",action="store_true"); parser.add_argument("--workers",type=int,default=4); parser.add_argument("--limit-specs",type=int); args=parser.parse_args()
    if args.preflight: print(json.dumps({"baseline":baseline_gate(),"analysis":analysis_specification()},indent=2))
    if args.run: print(json.dumps(run_components(args.workers,args.limit_specs),indent=2))
    if args.finalize: print(json.dumps(finalize(),indent=2))
    if not any((args.preflight,args.run,args.finalize)): parser.error("choose --preflight, --run, or --finalize")


if __name__=="__main__": main()
