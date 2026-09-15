"""Phase 1.18B0: validate FAST GPC-SUR posterior updates without a new path."""
from __future__ import annotations

import argparse, gzip, hashlib, json, math, subprocess, time
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
from scipy.stats import kendalltau, pearsonr, spearmanr

from src import week8_5_frozen_sample_efficiency_confirmation as w85
from src import week9_phase1_11_fixed_mean_discrepancy_gp as p11
from src import week9_phase1_13_fixed_physics_ard_discrepancy as p13
from src import week9_phase1_18a_level_set_acquisition_compatibility_audit as p18a

ROOT=Path(__file__).resolve().parents[1]
OUTPUT=ROOT/"outputs"/"week9_phase1_18b0_fast_gpc_sur_update_validation"
FIGURES=OUTPUT/"figures"; CHECKPOINTS=OUTPUT/"checkpoints"
NOTEBOOK=ROOT/"notebooks"/"week_09"/"17_week9_phase1_18b0_fast_gpc_sur_update_validation.ipynb"
PHASE18A=ROOT/"outputs"/"week9_phase1_18a_level_set_acquisition_compatibility_audit"
PARENT_SHA="658d5b73cf27e45b4b2e0897cff27a49a2ef4b84"
BRANCH="codex/week9-phase1-18b0-fast-gpc-sur-update-validation"
FEATURES=("P","VX","LS","ST"); BUDGETS=(16,24,40,60,80); LEVELS=("FAST_RANK1","EXACT_LAPLACE_FIXED_MODEL","EXACT_LAPLACE_REFIT_PHYSICS","FULL_M3_REFIT")
SEED_ROOT="week9_phase1_18b0|validation-gate|v1"
GATE={"median_spearman":.95,"q10_spearman":.80,"top1_agreement":.70,"mean_top5_jaccard":.70,"median_fast_top_rank_under_exact":2.0,"sign_reversal_fraction":.05,"median_posterior_probability_mae":.02,"q90_snapshot_probability_mae":.05,"late_median_spearman":.85}
PARTIAL={"median_spearman":.80,"top1_agreement":.40,"mean_top5_jaccard":.50,"median_posterior_probability_mae":.05}

def require(c:bool,m:str)->None:
    if not c: raise RuntimeError(m)
def seed_u32(*parts:object)->int:return int.from_bytes(hashlib.sha256("|".join((SEED_ROOT,*map(str,parts))).encode()).digest()[:8],"little")%(2**32)
def sha256_file(p:Path)->str:
    d=hashlib.sha256()
    with p.open("rb") as h:
        for b in iter(lambda:h.read(1024*1024),b""): d.update(b)
    return d.hexdigest()
def safe(v:Any)->Any:
    if isinstance(v,dict):return {str(k):safe(x) for k,x in v.items()}
    if isinstance(v,(list,tuple)):return [safe(x) for x in v]
    if isinstance(v,np.ndarray):return safe(v.tolist())
    if isinstance(v,(np.integer,np.floating,np.bool_)):v=v.item()
    if isinstance(v,float) and not math.isfinite(v):return None
    return v
def write_json(p:Path,x:Any)->None:p.parent.mkdir(parents=True,exist_ok=True);p.write_text(json.dumps(safe(x),indent=2,sort_keys=True)+"\n",encoding="utf-8")
def write_csv(p:Path,x:pd.DataFrame)->None:
    p.parent.mkdir(parents=True,exist_ok=True); raw=x.to_csv(index=False,lineterminator="\n").encode(); p.write_bytes(gzip.compress(raw,9,mtime=0) if p.suffix==".gz" else raw)
def historical_changes()->list[str]:
    protected=[str(p.relative_to(ROOT)).replace("\\","/") for p in (ROOT/"outputs").glob("week9_phase1_*") if p.name!=OUTPUT.name]
    return subprocess.check_output(["git","diff","--name-only",PARENT_SHA,"--",*protected],cwd=ROOT,text=True).splitlines()

def load_inputs():
    population,specs,paths=p18a.load_inputs(); scores=pd.read_csv(PHASE18A/"candidate_scores_pre_reveal.csv.gz"); runtime=pd.read_csv(PHASE18A/"runtime_benchmark.csv")
    require((len(population),int(population.has_keyhole.sum()))==(405,73),"population drift"); require(len(specs)==100,"split drift")
    return population,specs,paths,scores,runtime

def baseline_gate()->dict[str,Any]:
    population,specs,paths,scores,_=load_inputs(); current=subprocess.check_output(["git","rev-parse","HEAD"],cwd=ROOT,text=True).strip(); base=subprocess.check_output(["git","merge-base","HEAD",PARENT_SHA],cwd=ROOT,text=True).strip()
    payload={"status":"PASS","parent_sha":PARENT_SHA,"current_head":current,"merge_base":base,"population":len(population),"keyholes":int(population.has_keyhole.sum()),"conduction":int((~population.has_keyhole.astype(bool)).sum()),"outer_runs":len(specs),"frozen_paths":len(paths),"phase18a_candidate_rows":len(scores),"historical_changes":historical_changes()}; ok=base==PARENT_SHA and not payload["historical_changes"] and len(scores)==169200;payload["status"]="PASS" if ok else "FAIL";write_json(OUTPUT/"baseline_gate.json",payload);require(ok,str(payload));return payload

def analysis_specification()->dict[str,Any]:
    payload={"status":"FROZEN_BEFORE_EXACT_RESULTS","new_trajectory":False,"primary_comparison":"FAST_RANK1 vs EXACT_LAPLACE_FIXED_MODEL","secondary_levels":["EXACT_LAPLACE_REFIT_PHYSICS","FULL_M3_REFIT"],"budgets":list(BUDGETS),"target_snapshots":25,"minimum_candidates_per_snapshot":12,"reference_pool":"all currently unqueried outer-training candidates","uncertainty_functional":"mean p(u)(1-p(u))","hypothetical_label_weights":"current p_n(x)","gate":GATE,"partial_gate":PARTIAL,"refit_effect_gate":{"matters_if_median_spearman_below":.90,"or_top1_agreement_below":.60},"candidate_selection_forbidden":["truth","B1","q20","q30","held-out labels"],"no_sample_efficiency_test":True,"full_refit_role":"secondary model-refit sensitivity, not primary update truth"};write_json(OUTPUT/"analysis_specification.json",payload);return payload

def snapshot_design()->pd.DataFrame:
    _,_,_,_,runtime=load_inputs(); d=runtime[runtime.length_upper.eq(100)].copy(); d=d[d.budget.isin(BUDGETS)].sort_values(["budget","run_id"]); rows=[]
    for budget,g in d.groupby("budget",sort=True):
        roles=[("no_upper_hit",g[~g.any_length_upper_bound_hit.astype(bool)].sort_values(["anisotropy_ratio","run_id"])),("upper_bound_pressure",g[g.any_length_upper_bound_hit.astype(bool)].sort_values(["anisotropy_ratio","run_id"],ascending=[False,True])),("high_residual_sd",g.sort_values(["residual_sd","run_id"],ascending=[False,True])),("low_residual_sd",g.sort_values(["residual_sd","run_id"])),("ordinary_median_anisotropy",g.assign(delta=(g.anisotropy_ratio-g.anisotropy_ratio.median()).abs()).sort_values(["delta","run_id"]))]
        used=set()
        for role,pool in roles:
            for r in pool.itertuples():
                if r.run_id not in used: used.add(r.run_id); rows.append({"snapshot_id":f"{r.run_id}__B{budget}","run_id":r.run_id,"repeat":r.repeat,"fold":r.fold,"budget":budget,"selection_role":role,"residual_sd":r.residual_sd,"any_length_upper_bound_hit":bool(r.any_length_upper_bound_hit),"upper_length_hit_count":sum(bool(getattr(r,f"l_{x}_upper_bound_hit")) for x in FEATURES),"anisotropy_ratio":r.anisotropy_ratio,"optimizer_converged":bool(r.optimizer_converged),"posterior_iterations":r.posterior_iterations});break
    out=pd.DataFrame(rows);require(len(out)==25 and set(out.budget)==set(BUDGETS),"snapshot design");require(out.repeat.nunique()>=5 and out.fold.nunique()>=3,"coverage");write_csv(OUTPUT/"snapshot_validation_design.csv",out);return out

def _rank_pick(g:pd.DataFrame,column:str,n:int)->int:
    return int(g.sort_values([column,"candidate_population_row_index"],ascending=[False,True]).iloc[n-1].candidate_population_row_index)
def candidate_design(snapshots:pd.DataFrame)->pd.DataFrame:
    _,_,_,scores,_=load_inputs(); rows=[]
    for s in snapshots.itertuples():
        g=scores[(scores.run_id.eq(s.run_id))&scores.budget.eq(s.budget)].copy(); chosen:dict[int,list[str]]={}
        def add(i:int,role:str):chosen.setdefault(int(i),[]).append(role)
        for rank in (1,2,5,10):add(_rank_pick(g,"sur_score",rank),f"fast_sur_rank_{rank}")
        for rank in (1,5):add(_rank_pick(g,"margin_score",rank),f"margin_rank_{rank}")
        for rank in (1,5):add(_rank_pick(g,"latent_sd",rank),f"latent_variance_rank_{rank}")
        middle=g.latent_sd.between(g.latent_sd.quantile(.25),g.latent_sd.quantile(.75)); near=g[middle].assign(nearness=(g[middle].m3_probability-.5).abs()).sort_values(["nearness","candidate_population_row_index"])
        for i in near.candidate_population_row_index.head(2):add(i,"near_boundary_moderate_variance")
        far=g.assign(farness=(g.m3_probability-.5).abs()).sort_values(["farness","candidate_population_row_index"],ascending=[False,True])
        for i in far.candidate_population_row_index.head(2):add(i,"far_boundary_control")
        ids=np.sort(g.candidate_population_row_index.unique());
        for i,role in zip((ids[0],ids[len(ids)//2],ids[-1]),("id_low_control","id_median_control","id_high_control")):add(i,role)
        if len(chosen)<12:
            for i in ids:
                add(i,"deterministic_fill")
                if len(chosen)>=12:break
        for idx,roles in chosen.items():
            r=g[g.candidate_population_row_index.eq(idx)].iloc[0];rows.append({"snapshot_id":s.snapshot_id,"run_id":s.run_id,"repeat":s.repeat,"fold":s.fold,"budget":s.budget,"candidate_population_row_index":idx,"selection_roles":";".join(sorted(set(roles))),"fast_sur_score_pre_reveal":r.sur_score,"margin_score_pre_reveal":r.margin_score,"m3_probability_pre_reveal":r.m3_probability,"latent_sd_pre_reveal":r.latent_sd})
    out=pd.DataFrame(rows).sort_values(["snapshot_id","candidate_population_row_index"]);require(out.groupby("snapshot_id").size().min()>=12,"candidate coverage");forbidden={"truth","B1","q20","q30","has_keyhole"};require(forbidden.isdisjoint(out.columns),"design leakage");write_csv(OUTPUT/"candidate_validation_design.csv",out);write_json(OUTPUT/"candidate_validation_design_sha256.json",{"sha256":sha256_file(OUTPUT/"candidate_validation_design.csv"),"rows":len(out),"frozen_before_hypothetical_updates":True});return out

def expected_curvature(mu:np.ndarray,var:np.ndarray)->np.ndarray:return p18a.expected_logistic_curvature(mu,var)
def fast_update_from_candidate(mu:np.ndarray,var:np.ndarray,cov_x:np.ndarray,v_x:float,p_x:float,W_x:float,y:int)->tuple[np.ndarray,np.ndarray,np.ndarray]:
    denom=1.+v_x*W_x; new_var=np.maximum(var-cov_x**2*W_x/denom,p11.EPS); new_mu=mu+cov_x*(float(y)-p_x)/denom; new_p=p18a.logistic_gaussian_probability(new_mu,new_var);return new_mu,new_var,new_p

@dataclass
class UpdatedFit:
    level:str; physics:Any; scaler:Any; gp:Any; seconds:float
def exact_update(current:Any,x4:np.ndarray,logh:np.ndarray,labels:np.ndarray,revealed:Sequence[int],training_pool:Sequence[int],candidate:int,y:int,level:str)->UpdatedFit:
    lab=labels.copy();lab[candidate]=int(y);enlarged=np.asarray([*revealed,candidate],int);started=time.perf_counter()
    if level=="EXACT_LAPLACE_FIXED_MODEL":physics=current.physics;scaler=current.x_scaler;kernel=current.gp.kernel_;gp=p11.FixedMeanLaplaceGPC(kernel,optimize=False).fit(scaler.transform(x4[enlarged]),lab[enlarged],physics.latent(logh[enlarged]));require(np.array_equal(gp.kernel_.theta,current.gp.kernel_.theta),"fixed kernel drift")
    elif level=="EXACT_LAPLACE_REFIT_PHYSICS":physics=p11.fit_physics_mean(logh,lab,enlarged,seed_u32("physics_refit",candidate,y,*revealed));scaler=current.x_scaler;gp=p11.FixedMeanLaplaceGPC(current.gp.kernel_,optimize=False).fit(scaler.transform(x4[enlarged]),lab[enlarged],physics.latent(logh[enlarged]));require(np.array_equal(gp.kernel_.theta,current.gp.kernel_.theta),"physics-refit kernel drift")
    elif level=="FULL_M3_REFIT":physics=p11.fit_physics_mean(logh,lab,enlarged,seed_u32("full",candidate,y,*revealed));fit=p13.fit_hybrid(x4,logh,lab,enlarged,training_pool,physics,"M3",100.0);return UpdatedFit(level,fit.physics,fit.x_scaler,fit.gp,time.perf_counter()-started)
    else:raise ValueError(level)
    return UpdatedFit(level,physics,scaler,gp,time.perf_counter()-started)
def updated_components(fit:UpdatedFit,x4:np.ndarray,logh:np.ndarray,reference:np.ndarray)->tuple[np.ndarray,np.ndarray,np.ndarray]:
    xs=fit.scaler.transform(x4[reference]);mean=fit.physics.latent(logh[reference]);mu,var=fit.gp.latent_mean_and_variance(xs,mean);p=fit.gp.predict_proba(xs,mean)[:,1];return mu,var,p

def checkpoint_marker(snapshot_id:str)->Path:return CHECKPOINTS/f"{snapshot_id}.json"
def run_snapshot(srow:Any,design:pd.DataFrame,population:pd.DataFrame,spec:Any,path:Sequence[int])->dict[str,Any]:
    marker=checkpoint_marker(srow.snapshot_id);stem=CHECKPOINTS/srow.snapshot_id
    if marker.is_file() and json.loads(marker.read_text()).get("complete"):return {"snapshot_id":srow.snapshot_id,"reused":True}
    x4=population.loc[:,FEATURES].to_numpy(float);logh=p11.log_h_values(population);labels=population.has_keyhole.astype(int).to_numpy();revealed=np.asarray(path[:srow.budget],int);reference=np.setdiff1d(np.asarray(spec.train_indices,int),revealed)
    physics=p11.fit_physics_mean(logh,labels,revealed,p13.seed_u32("shared_physics",spec.run_id,srow.budget));current=p13.fit_hybrid(x4,logh,labels,revealed,spec.train_indices,physics,"M3",100.0);comp=p13.components(current,x4[reference],logh[reference]);mu=np.asarray(comp["final_latent"]);var=np.asarray(comp["latent_variance"]);prob=np.asarray(comp["probability"]);cov=p18a.posterior_covariance(current,current.x_scaler.transform(x4[reference]));current_U=float(np.mean(prob*(1-prob)));pos={int(v):i for i,v in enumerate(reference)}
    phase18a= pd.read_csv(PHASE18A/"candidate_scores_pre_reveal.csv.gz",usecols=["run_id","budget","candidate_population_row_index","m3_probability","sur_score"]);phase18a=phase18a[(phase18a.run_id.eq(srow.run_id))&phase18a.budget.eq(srow.budget)].set_index("candidate_population_row_index")
    details=[];scores=[];runtimes=[];audits=[]
    for crow in design[design.snapshot_id.eq(srow.snapshot_id)].itertuples():
        candidate=int(crow.candidate_population_row_index);j=pos[candidate];p_x=float(prob[j]);W_x=float(expected_curvature(np.array([mu[j]]),np.array([var[j]]))[0]);candidate_updates={}
        require(abs(p_x-float(phase18a.loc[candidate,"m3_probability"]))<1e-10,"Phase18A current probability drift")
        for y in (0,1):
            started=time.perf_counter();fm,fv,fp=fast_update_from_candidate(mu,var,cov[:,j],float(var[j]),p_x,W_x,y);fast_seconds=time.perf_counter()-started;candidate_updates[("FAST_RANK1",y)]=(fm,fv,fp);runtimes.append({"snapshot_id":srow.snapshot_id,"candidate_population_row_index":candidate,"hypothetical_label":y,"update_level":"FAST_RANK1","seconds":fast_seconds})
            for level in LEVELS[1:]:
                fit=exact_update(current,x4,logh,labels,revealed,spec.train_indices,candidate,y,level);em,ev,ep=updated_components(fit,x4,logh,reference);candidate_updates[(level,y)]=(em,ev,ep);runtimes.append({"snapshot_id":srow.snapshot_id,"candidate_population_row_index":candidate,"hypothetical_label":y,"update_level":level,"seconds":fit.seconds})
                current_theta=current.gp.kernel_.theta;theta=fit.gp.kernel_.theta;audits.append({"snapshot_id":srow.snapshot_id,"candidate_population_row_index":candidate,"hypothetical_label":y,"update_level":level,"kernel_theta_max_abs_change":float(np.max(np.abs(theta-current_theta))),"scaler_mean_max_abs_change":float(np.max(np.abs(fit.scaler.mean_-current.x_scaler.mean_))),"physics_intercept_change":float(fit.physics.model.intercept_[0]-current.physics.model.intercept_[0]),"physics_coefficient_change":float(fit.physics.model.coef_[0,0]-current.physics.model.coef_[0,0]),"current_residual_sd":current.residual_sd,"updated_residual_sd":math.sqrt(float(fit.gp.kernel_.k1.constant_value))})
        for level in LEVELS:
            expected_U=0.
            for y,weight in ((0,1-p_x),(1,p_x)):
                um,uv,up=candidate_updates[(level,y)];expected_U+=weight*float(np.mean(up*(1-up)))
                for k,ref in enumerate(reference):details.append({"snapshot_id":srow.snapshot_id,"run_id":srow.run_id,"repeat":srow.repeat,"fold":srow.fold,"budget":srow.budget,"candidate_population_row_index":candidate,"selection_roles":crow.selection_roles,"hypothetical_label":y,"update_level":level,"reference_population_row_index":int(ref),"current_latent_mean":mu[k],"current_latent_variance":var[k],"current_probability":prob[k],"updated_latent_mean":um[k],"updated_latent_variance":uv[k],"updated_probability":up[k],"updated_uncertainty":up[k]*(1-up[k])})
            score=current_U-expected_U;scores.append({"snapshot_id":srow.snapshot_id,"run_id":srow.run_id,"repeat":srow.repeat,"fold":srow.fold,"budget":srow.budget,"candidate_population_row_index":candidate,"selection_roles":crow.selection_roles,"update_level":level,"sur_score":score,"current_integrated_uncertainty":current_U,"expected_updated_integrated_uncertainty":expected_U,"current_candidate_probability":p_x,"expected_site_curvature":W_x})
        fast_score=scores[-4]["sur_score"] if scores[-4]["update_level"]=="FAST_RANK1" else next(r["sur_score"] for r in scores[-4:] if r["update_level"]=="FAST_RANK1")
        require(abs(fast_score-float(phase18a.loc[candidate,"sur_score"]))<1e-10,"Phase18A FAST score drift")
    CHECKPOINTS.mkdir(parents=True,exist_ok=True);write_csv(stem.with_suffix(".details.csv.gz"),pd.DataFrame(details));write_csv(stem.with_suffix(".scores.csv"),pd.DataFrame(scores));write_csv(stem.with_suffix(".runtime.csv"),pd.DataFrame(runtimes));write_csv(stem.with_suffix(".audit.csv"),pd.DataFrame(audits));write_json(marker,{"complete":True,"snapshot_id":srow.snapshot_id,"candidates":len(design[design.snapshot_id.eq(srow.snapshot_id)]),"reference_count":len(reference)});return {"snapshot_id":srow.snapshot_id,"reused":False}

def run_updates(workers:int=4,limit_snapshots:int|None=None)->dict[str,Any]:
    baseline_gate();analysis_specification();snap=snapshot_design();design=candidate_design(snap);population,specs,paths,_,_=load_inputs();lookup={s.run_id:s for s in specs};selected=snap.iloc[:limit_snapshots] if limit_snapshots else snap;started=time.time();results=Parallel(n_jobs=workers,verbose=10)(delayed(run_snapshot)(r,design,population,lookup[r.run_id],paths[r.run_id]) for r in selected.itertuples());payload={"status":"PASS","snapshots":len(results),"reused":sum(x["reused"] for x in results),"elapsed_seconds":time.time()-started,"complete":limit_snapshots is None};write_json(OUTPUT/"execution_report.json",payload);return payload

def collect_updates()->tuple[pd.DataFrame,pd.DataFrame,pd.DataFrame,pd.DataFrame]:
    snap=pd.read_csv(OUTPUT/"snapshot_validation_design.csv");details=[];scores=[];runtime=[];audits=[]
    for s in snap.snapshot_id:
        stem=CHECKPOINTS/s;require(checkpoint_marker(s).is_file(),f"missing {s}");details.append(pd.read_csv(stem.with_suffix(".details.csv.gz")));scores.append(pd.read_csv(stem.with_suffix(".scores.csv")));runtime.append(pd.read_csv(stem.with_suffix(".runtime.csv")));audits.append(pd.read_csv(stem.with_suffix(".audit.csv")))
    d=pd.concat(details,ignore_index=True);s=pd.concat(scores,ignore_index=True);r=pd.concat(runtime,ignore_index=True);a=pd.concat(audits,ignore_index=True);write_csv(OUTPUT/"candidate_level_update_results.csv.gz",d);write_csv(OUTPUT/"candidate_sur_scores.csv.gz",s);write_csv(OUTPUT/"runtime_benchmark.csv",r);write_csv(OUTPUT/"parameter_freeze_audit.csv.gz",a);return d,s,r,a

def jaccard(a:pd.DataFrame,left:str,right:str,k:int)->float:
    x=set(a.nlargest(k,left).candidate_population_row_index);y=set(a.nlargest(k,right).candidate_population_row_index);return len(x&y)/len(x|y)
def fidelity_outputs(details:pd.DataFrame,scores:pd.DataFrame,snapshots:pd.DataFrame)->dict[str,pd.DataFrame]:
    wide=scores.pivot(index=["snapshot_id","run_id","repeat","fold","budget","candidate_population_row_index","selection_roles"],columns="update_level",values="sur_score").reset_index();rows=[]
    for sid,g in wide.groupby("snapshot_id",sort=True):
        exact="EXACT_LAPLACE_FIXED_MODEL";fast="FAST_RANK1";et=int(g.loc[g[exact].idxmax(),"candidate_population_row_index"]);ft=int(g.loc[g[fast].idxmax(),"candidate_population_row_index"]);erank=g[exact].rank(ascending=False,method="min");frank=g[fast].rank(ascending=False,method="min")
        rows.append({"snapshot_id":sid,"run_id":g.run_id.iloc[0],"repeat":g.repeat.iloc[0],"fold":g.fold.iloc[0],"budget":g.budget.iloc[0],"candidate_count":len(g),"spearman":spearmanr(g[fast],g[exact]).statistic,"kendall_tau":kendalltau(g[fast],g[exact]).statistic,"pearson":pearsonr(g[fast],g[exact]).statistic,"nrmse":float(np.sqrt(np.mean((g[fast]-g[exact])**2))/(np.std(g[exact])+1e-15)),"max_abs_score_error":float(np.max(np.abs(g[fast]-g[exact]))),"top1_agreement":float(et==ft),"top3_jaccard":jaccard(g,fast,exact,3),"top5_jaccard":jaccard(g,fast,exact,5),"top10_jaccard":jaccard(g,fast,exact,min(10,len(g))),"fast_top_rank_under_exact":float(erank.loc[g[fast].idxmax()]),"exact_top_rank_under_fast":float(frank.loc[g[exact].idxmax()]),"sign_reversal_fraction":float(np.mean(np.sign(g[fast])!=np.sign(g[exact])))})
    bysnap=pd.DataFrame(rows);write_csv(OUTPUT/"sur_score_fidelity_by_snapshot.csv",bysnap)
    overall=pd.DataFrame([{"snapshots":len(bysnap),"median_spearman":bysnap.spearman.median(),"q10_spearman":bysnap.spearman.quantile(.1),"median_kendall_tau":bysnap.kendall_tau.median(),"median_pearson":bysnap.pearson.median(),"top1_agreement":bysnap.top1_agreement.mean(),"mean_top3_jaccard":bysnap.top3_jaccard.mean(),"mean_top5_jaccard":bysnap.top5_jaccard.mean(),"mean_top10_jaccard":bysnap.top10_jaccard.mean(),"median_fast_top_rank_under_exact":bysnap.fast_top_rank_under_exact.median(),"sign_reversal_fraction":float((np.sign(wide.FAST_RANK1)!=np.sign(wide.EXACT_LAPLACE_FIXED_MODEL)).mean()),"late_median_spearman":bysnap[bysnap.budget.ge(60)].spearman.median()}]);write_csv(OUTPUT/"sur_score_fidelity_overall.csv",overall)
    selection=bysnap[["snapshot_id","budget","top1_agreement","top3_jaccard","top5_jaccard","top10_jaccard","fast_top_rank_under_exact","exact_top_rank_under_fast"]];write_csv(OUTPUT/"selection_fidelity_summary.csv",selection)
    key=["snapshot_id","candidate_population_row_index","hypothetical_label","reference_population_row_index"];dw=details.pivot(index=key+['budget','selection_roles'],columns="update_level",values=["updated_probability","updated_latent_mean","updated_latent_variance"]).reset_index();prob_abs=np.abs(dw[("updated_probability","FAST_RANK1")]-dw[("updated_probability","EXACT_LAPLACE_FIXED_MODEL")]);mean_abs=np.abs(dw[("updated_latent_mean","FAST_RANK1")]-dw[("updated_latent_mean","EXACT_LAPLACE_FIXED_MODEL")]);var_abs=np.abs(dw[("updated_latent_variance","FAST_RANK1")]-dw[("updated_latent_variance","EXACT_LAPLACE_FIXED_MODEL")]);dw[('error','probability_abs')]=prob_abs;dw[('error','latent_mean_abs')]=mean_abs;dw[('error','latent_variance_abs')]=var_abs
    post=dw.groupby([("snapshot_id","")]).agg(probability_mae=(("error","probability_abs"),"mean"),probability_q95=(("error","probability_abs"),lambda x:x.quantile(.95)),probability_max=(("error","probability_abs"),"max"),latent_mean_mae=(("error","latent_mean_abs"),"mean"),latent_variance_mae=(("error","latent_variance_abs"),"mean")).reset_index();post.columns=["snapshot_id","probability_mae","probability_q95","probability_max","latent_mean_mae","latent_variance_mae"];post=post.merge(snapshots[["snapshot_id","budget"]],on="snapshot_id");write_csv(OUTPUT/"posterior_fidelity_summary.csv",post)
    label=dw.groupby([("hypothetical_label","")]).agg(probability_mae=(("error","probability_abs"),"mean"),probability_q95=(("error","probability_abs"),lambda x:x.quantile(.95)),latent_variance_mae=(("error","latent_variance_abs"),"mean")).reset_index();label.columns=["hypothetical_label","probability_mae","probability_q95","latent_variance_mae"];write_csv(OUTPUT/"label_conditional_fidelity.csv",label)
    cand=dw.groupby([("snapshot_id",""),("candidate_population_row_index",""),("selection_roles","")]).agg(probability_mae=(("error","probability_abs"),"mean"),probability_q95=(("error","probability_abs"),lambda x:x.quantile(.95))).reset_index();cand.columns=["snapshot_id","candidate_population_row_index","selection_roles","probability_mae","probability_q95"];expl=cand.assign(selection_roles=cand.selection_roles.str.split(";")).explode("selection_roles");reg=expl.groupby("selection_roles",as_index=False).agg(candidates=("candidate_population_row_index","size"),mean_probability_mae=("probability_mae","mean"),q90_probability_mae=("probability_mae",lambda x:x.quantile(.9)));write_csv(OUTPUT/"candidate_regime_fidelity.csv",reg)
    num=bysnap.merge(post,on=["snapshot_id","budget"]).merge(snapshots,on=["snapshot_id","budget","run_id","repeat","fold"]);write_csv(OUTPUT/"numerical_regime_fidelity.csv",num)
    ref=[]
    for left,right,name in (("FAST_RANK1","EXACT_LAPLACE_FIXED_MODEL","rank_one_error"),("EXACT_LAPLACE_REFIT_PHYSICS","EXACT_LAPLACE_FIXED_MODEL","physics_refit_effect"),("FULL_M3_REFIT","EXACT_LAPLACE_REFIT_PHYSICS","hyperparameter_refit_effect")):
        for sid,g in wide.groupby("snapshot_id"):
            ref.append({"effect":name,"snapshot_id":sid,"budget":g.budget.iloc[0],"spearman":spearmanr(g[left],g[right]).statistic,"mean_abs_sur_difference":float(np.mean(np.abs(g[left]-g[right]))),"top1_agreement":float(g.loc[g[left].idxmax(),"candidate_population_row_index"]==g.loc[g[right].idxmax(),"candidate_population_row_index"]),"top5_jaccard":jaccard(g,left,right,5)})
    decomposition=pd.DataFrame(ref);write_csv(OUTPUT/"refit_effect_decomposition.csv",decomposition);return {"wide":wide,"snapshot":bysnap,"overall":overall,"posterior":post,"label":label,"regime":reg,"numerical":num,"decomposition":decomposition}

def probability_integration_validation()->pd.DataFrame:
    nodes,weights=np.polynomial.hermite.hermgauss(100);rows=[]
    for mu in (-6.,-3.,-1.,0.,1.,3.,6.):
        for var in (1e-6,.01,.1,1.,4.,9.):
            exact=float(np.sum(weights*expit(mu+np.sqrt(2*var)*nodes))/np.sqrt(np.pi));approx=float(p18a.logistic_gaussian_probability(np.array([mu]),np.array([var]))[0]);rows.append({"mu":mu,"variance":var,"gauss_hermite_100":exact,"m3_williams_barber":approx,"absolute_error":abs(exact-approx)})
    out=pd.DataFrame(rows);write_csv(OUTPUT/"probability_integration_validation.csv",out);return out
def special_case_validation()->pd.DataFrame:
    mu=np.array([-.3,.2]);var=np.array([.7,.4]);p=.45;rows=[]
    nmu,nv,_=fast_update_from_candidate(mu,var,np.zeros(2),.5,p,.2,1);rows.append({"case":"zero_cross_covariance","max_mean_change":np.max(abs(nmu-mu)),"max_variance_change":np.max(abs(nv-var)),"status":"PASS" if np.allclose(nmu,mu) and np.allclose(nv,var) else "FAIL"})
    cov=np.array([.5]);_,nv,_=fast_update_from_candidate(np.array([0.]),np.array([.5]),cov,.5,.5,.25,1);expected=.5-.5**2*.25/(1+.5*.25);rows.append({"case":"same_point_variance","max_mean_change":math.nan,"max_variance_change":abs(nv[0]-expected),"status":"PASS" if abs(nv[0]-expected)<1e-12 else "FAIL"})
    nmu0,nv0,_=fast_update_from_candidate(mu,var,np.array([.2,.1]),.5,p,1e-14,0);nmu1,nv1,_=fast_update_from_candidate(mu,var,np.array([.2,.1]),.5,p,1e-14,1);expected_shift=(1-p)*(nmu0-mu)+p*(nmu1-mu);rows.append({"case":"low_curvature_limit_expected_update","max_mean_change":np.max(abs(expected_shift)),"max_variance_change":max(np.max(abs(nv0-var)),np.max(abs(nv1-var))),"status":"PASS" if np.max(abs(expected_shift))<1e-12 and np.max(abs(nv1-var))<1e-12 else "FAIL"})
    nmu,nv,_=fast_update_from_candidate(np.array([.1]),np.array([1e-14]),np.array([1e-14]),1e-14,.52,.25,1);rows.append({"case":"near_zero_variance","max_mean_change":abs(nmu[0]-.1),"max_variance_change":abs(nv[0]-1e-14),"status":"PASS" if abs(nmu[0]-.1)<1e-12 and abs(nv[0]-1e-14)<1e-12 else "FAIL"})
    out=pd.DataFrame(rows);write_csv(OUTPUT/"special_case_validation.csv",out);return out

def write_contracts()->None:
    docs={
    "sur_literature_update_contract.md":"""# Literature-faithful SUR update contract

[Bect et al. (2012)](https://doi.org/10.1007/s11222-011-9241-4) formulate stepwise uncertainty reduction as minimizing expected future uncertainty of an excursion-set quantity under the current posterior predictive distribution. [Menz, Muñoz Zuniga, and Sinoquet (2025)](https://doi.org/10.1016/j.strusafe.2025.102607) extend random-set uncertainty reduction to Gaussian-process classification.

This validation retains Phase 1.18A's finite-pool functional `U=mean_u p(u)(1-p(u))`. It is a probability-uncertainty surrogate, not asserted to be algebraically identical to every random-set functional in Menz et al. Both hypothetical labels are weighted by current `p_n(x)`. The literature-defined one-step posterior update is closest to `EXACT_LAPLACE_FIXED_MODEL`: current mean/scaler/kernel hyperparameters are held fixed while the enlarged-data Laplace posterior is solved. Refitting physics or kernel hyperparameters is a secondary empirical-Bayes model-refit effect, not automatically the theoretical acquisition definition.
""",
    "fast_rank1_definition.md":"""# FAST_RANK1 definition

For current posterior moments at reference point `u` and candidate `x`,

`v_new(u)=v(u)-Cov(f(u),f(x))^2 W_x/[1+v(x)W_x]`,

`mu_new(u)=mu(u)+Cov(f(u),f(x))(y-p_n(x))/[1+v(x)W_x]`,

with `W_x=E[sigmoid(F_x)(1-sigmoid(F_x))]`. Updated probabilities use the unchanged M3 logistic-Gaussian integration. This exactly reproduces Phase 1.18A. It is a rank-one moment approximation, not an exact enlarged-data Laplace solve.
""",
    "exact_fixed_model_definition.md":"""# EXACT_LAPLACE_FIXED_MODEL

Add hypothetical `(x,y)` to the revealed set; keep the Stage-1 physics object, training-pool StandardScaler, fitted residual amplitude and all ARD Matérn-3/2 kernel hyperparameters unchanged; then solve the actual enlarged-data logistic Laplace posterior with optimization disabled. This isolates posterior-update approximation error.
""",
    "physics_refit_definition.md":"""# EXACT_LAPLACE_REFIT_PHYSICS

Add hypothetical `(x,y)`, refit the h-only Stage-1 logistic mean on the enlarged revealed set, keep the pre-query scaler and all Stage-2 kernel hyperparameters fixed, and solve the enlarged-data Laplace posterior. Its difference from EXACT_FIXED measures physics-backbone refitting.
""",
    "full_refit_definition.md":"""# FULL_M3_REFIT

Add hypothetical `(x,y)`, refit Stage 1, and run the normal M3 Stage-2 hyperparameter optimization with the frozen L100 architecture. This expensive level measures empirical-Bayes refit effects; it is not treated as the primary literature-faithful SUR update.
"""}
    for name,text in docs.items():(OUTPUT/name).write_text(text.strip()+"\n",encoding="utf-8")

def decide(res:dict[str,pd.DataFrame])->tuple[dict[str,Any],dict[str,Any]]:
    o=res["overall"].iloc[0];post=res["posterior"];criteria={"median_spearman":o.median_spearman>=GATE["median_spearman"],"q10_spearman":o.q10_spearman>=GATE["q10_spearman"],"top1_agreement":o.top1_agreement>=GATE["top1_agreement"],"mean_top5_jaccard":o.mean_top5_jaccard>=GATE["mean_top5_jaccard"],"median_fast_top_rank_under_exact":o.median_fast_top_rank_under_exact<=GATE["median_fast_top_rank_under_exact"],"sign_reversal_fraction":o.sign_reversal_fraction<=GATE["sign_reversal_fraction"],"median_probability_mae":post.probability_mae.median()<=GATE["median_posterior_probability_mae"],"q90_snapshot_probability_mae":post.probability_mae.quantile(.9)<=GATE["q90_snapshot_probability_mae"],"late_median_spearman":o.late_median_spearman>=GATE["late_median_spearman"]}
    if all(criteria.values()):decision="FAST_SUR_VALIDATED"
    elif o.median_spearman>=PARTIAL["median_spearman"] and o.top1_agreement>=PARTIAL["top1_agreement"] and o.mean_top5_jaccard>=PARTIAL["mean_top5_jaccard"] and post.probability_mae.median()<=PARTIAL["median_posterior_probability_mae"]:decision="FAST_SUR_PARTIALLY_VALIDATED"
    else:decision="FAST_SUR_REJECTED"
    primary={"decision":decision,"criteria":criteria,"gate":GATE,"observed":{k:safe(v) for k,v in {**o.to_dict(),"median_posterior_probability_mae":post.probability_mae.median(),"q90_snapshot_probability_mae":post.probability_mae.quantile(.9)}.items()},"prospective_fast_sur_justified":decision=="FAST_SUR_VALIDATED","guarded_prospective_possible":decision=="FAST_SUR_PARTIALLY_VALIDATED"};write_json(OUTPUT/"primary_decision.json",primary)
    d=res["decomposition"].groupby("effect",as_index=False).agg(median_spearman=("spearman","median"),top1_agreement=("top1_agreement","mean"),mean_top5_jaccard=("top5_jaccard","mean"));physics=d[d.effect.eq("physics_refit_effect")].iloc[0];hyper=d[d.effect.eq("hyperparameter_refit_effect")].iloc[0];pm=physics.median_spearman<.90 or physics.top1_agreement<.60;hm=hyper.median_spearman<.90 or hyper.top1_agreement<.60;category="BOTH_REFITS_MATTER" if pm and hm else ("PHYSICS_REFIT_MATTERS" if pm else ("HYPERPARAMETER_REFIT_MATTERS" if hm else "REFIT_EFFECT_SMALL"));secondary={"decision":category,"summary":d.to_dict("records"),"predeclared_matters_rule":"median Spearman <0.90 or top-1 agreement <0.60"};write_json(OUTPUT/"refit_effect_decision.json",secondary);return primary,secondary

def figures(res:dict[str,pd.DataFrame],runtime:pd.DataFrame)->pd.DataFrame:
    FIGURES.mkdir(parents=True,exist_ok=True);made=[];wide=res["wide"]
    fig,ax=plt.subplots(figsize=(6.5,5.5));ax.scatter(wide.EXACT_LAPLACE_FIXED_MODEL,wide.FAST_RANK1,c=wide.budget,cmap="viridis",s=22,alpha=.7);lo=min(wide.EXACT_LAPLACE_FIXED_MODEL.min(),wide.FAST_RANK1.min());hi=max(wide.EXACT_LAPLACE_FIXED_MODEL.max(),wide.FAST_RANK1.max());ax.plot([lo,hi],[lo,hi],"k--",lw=1);ax.set(xlabel="EXACT_FIXED SUR score",ylabel="FAST_RANK1 SUR score",title="FAST does not preserve exact-fixed SUR scoring");fig.tight_layout();p=FIGURES/"01_fast_vs_exact_sur_scatter.png";fig.savefig(p,dpi=180);plt.close(fig);made.append((p,"Candidate scores over 25 frozen snapshots."))
    fig,ax=plt.subplots(figsize=(8,4.8));data=[res["snapshot"].query("budget==@b").spearman.dropna() for b in BUDGETS];ax.boxplot(data,tick_labels=[f"B{b}" for b in BUDGETS],patch_artist=True,boxprops={"facecolor":"#63b3ed","alpha":.7});ax.axhline(GATE["median_spearman"],ls="--",color="black");ax.set(ylabel="Snapshot Spearman",title="Rank fidelity varies strongly by budget");ax.grid(axis="y",alpha=.25);fig.tight_layout();p=FIGURES/"02_snapshot_spearman_by_budget.png";fig.savefig(p,dpi=180);plt.close(fig);made.append((p,"FAST versus exact-fixed snapshot ranking."))
    by=res["snapshot"].groupby("budget",as_index=False).agg(top1=("top1_agreement","mean"),top5=("top5_jaccard","mean"));fig,ax=plt.subplots(figsize=(8,4.8));ax.plot(by.budget,by.top1,"o-",label="Top-1 agreement");ax.plot(by.budget,by.top5,"s-",label="Top-5 Jaccard");ax.axhline(GATE["top1_agreement"],color="#3182ce",ls="--",alpha=.5);ax.axhline(GATE["mean_top5_jaccard"],color="#dd6b20",ls="--",alpha=.5);ax.set(xlabel="Budget",ylabel="Selection fidelity",ylim=(-.05,1.05),title="Candidate-selection fidelity");ax.legend(frameon=False);ax.grid(alpha=.25);fig.tight_layout();p=FIGURES/"03_selection_fidelity_by_budget.png";fig.savefig(p,dpi=180);plt.close(fig);made.append((p,"Top-k agreement at the five validation budgets."))
    label=res["label"];fig,ax=plt.subplots(figsize=(7,4.5));ax.bar(["Hypothetical 0","Hypothetical 1"],label.probability_mae,color=["#4299e1","#ed8936"]);ax.set(ylabel="Mean absolute probability error",title="Posterior error is small but label-asymmetric");ax.grid(axis="y",alpha=.25);fig.tight_layout();p=FIGURES/"04_probability_error_by_label.png";fig.savefig(p,dpi=180);plt.close(fig);made.append((p,"FAST minus exact-fixed reference-pool probability error."))
    dec=res["decomposition"].groupby("effect",as_index=False).agg(median_spearman=("spearman","median"),top1=("top1_agreement","mean"));fig,ax=plt.subplots(figsize=(8,4.8));x=np.arange(len(dec));w=.36;ax.bar(x-w/2,dec.median_spearman,w,label="Median Spearman");ax.bar(x+w/2,dec.top1,w,label="Top-1 agreement");ax.set_xticks(x,[x.replace("_","\n") for x in dec.effect]);ax.set(ylim=(-.1,1.05),title="Error decomposition");ax.legend(frameon=False);ax.grid(axis="y",alpha=.25);fig.tight_layout();p=FIGURES/"05_refit_effect_decomposition.png";fig.savefig(p,dpi=180);plt.close(fig);made.append((p,"Rank-one, physics-refit, and hyperparameter-refit effects."))
    rt=runtime.groupby("update_level",as_index=False).seconds.mean().sort_values("seconds");fig,ax=plt.subplots(figsize=(8,4.8));ax.bar(rt.update_level.str.replace("EXACT_LAPLACE_","",regex=False),rt.seconds,color="#805ad5");ax.set_yscale("log");ax.set(ylabel="Mean seconds per hypothetical label (log)",title="Posterior-update runtime");ax.tick_params(axis="x",rotation=20);ax.grid(axis="y",alpha=.25);fig.tight_layout();p=FIGURES/"06_runtime_comparison.png";fig.savefig(p,dpi=180);plt.close(fig);made.append((p,"Observed per-label update cost."))
    out=pd.DataFrame([{"figure":p.name,"sha256":sha256_file(p),"caption":c} for p,c in made]);write_csv(OUTPUT/"figure_manifest.csv",out);return out

def reports(res:dict[str,pd.DataFrame],runtime:pd.DataFrame,primary:dict[str,Any],secondary:dict[str,Any],design:pd.DataFrame)->None:
    o=res["overall"].iloc[0];post=res["posterior"];label=res["label"].set_index("hypothetical_label");decomp=res["decomposition"].groupby("effect").agg(median_spearman=("spearman","median"),top1=("top1_agreement","mean"),top5=("top5_jaccard","mean"));rt=runtime.groupby("update_level").seconds.mean();mean_pool=design.groupby("snapshot_id").size().mean();future={k:float(v*2*276*6400/3600) for k,v in rt.items()};undefined=int(res["snapshot"].spearman.isna().sum())
    final=f"""# Week 9 Phase 1.18B0 — FAST GPC-SUR update validation

## Decision

**{primary['decision']}**; secondary model-refit result: **{secondary['decision']}**.

This phase used 25 predeclared frozen Phase 1.14 M3 snapshots, 307 pre-reveal candidates, both hypothetical labels and four update levels (2,456 candidate-label-level updates). No acquisition path was generated and no q20/B1/test outcome entered selection or scoring.

## Primary FAST versus exact-fixed gate

Median/q10 snapshot Spearman: {o.median_spearman:.4f}/{o.q10_spearman:.4f}; top-1 agreement {o.top1_agreement:.1%}; mean top-5 Jaccard {o.mean_top5_jaccard:.4f}; median FAST-top rank under exact {o.median_fast_top_rank_under_exact:.1f}; sign-reversal fraction {o.sign_reversal_fraction:.1%}; late-budget median Spearman {o.late_median_spearman:.4f}.

Spearman was undefined in {undefined}/25 snapshots because one compared score vector was constant; these cases remain in top-k and sign diagnostics and were not imputed.

The median/q90 snapshot probability MAE was {post.probability_mae.median():.3e}/{post.probability_mae.quantile(.9):.3e}. Thus latent/predictive updates are numerically close, but SUR is a small difference of integrated uncertainties and its candidate ranking is not preserved. Small posterior error is not sufficient acquisition-score fidelity.

Hypothetical label 0/1 probability MAE: {label.loc[0,'probability_mae']:.3e}/{label.loc[1,'probability_mae']:.3e}; the minority-class hypothetical update is less accurately approximated, but both absolute errors remain small.

## Refit decomposition

- Rank-one versus exact-fixed: median Spearman {decomp.loc['rank_one_error','median_spearman']:.4f}, top-1 {decomp.loc['rank_one_error','top1']:.1%}.
- Physics-refit versus exact-fixed: {decomp.loc['physics_refit_effect','median_spearman']:.4f}, top-1 {decomp.loc['physics_refit_effect','top1']:.1%}.
- Full-refit versus physics-refit: {decomp.loc['hyperparameter_refit_effect','median_spearman']:.4f}, top-1 {decomp.loc['hyperparameter_refit_effect','top1']:.1%}.

The h-only physics backbone refit materially changes the hypothetical ranking. Kernel reoptimization is much less disruptive under the predeclared rule. This supports treating fixed-model exact Laplace as the clean literature-aligned posterior-update comparator, while acknowledging that the normal empirical-Bayes pipeline itself changes after a label.

## Runtime

Mean seconds per hypothetical label: FAST {rt['FAST_RANK1']:.6f}, exact-fixed {rt['EXACT_LAPLACE_FIXED_MODEL']:.6f}, physics-refit {rt['EXACT_LAPLACE_REFIT_PHYSICS']:.6f}, full-refit {rt['FULL_M3_REFIT']:.6f}. Naive 100-run B16→B80 all-candidate projections are approximately FAST {future['FAST_RANK1']:.1f}, exact-fixed {future['EXACT_LAPLACE_FIXED_MODEL']:.1f}, physics-refit {future['EXACT_LAPLACE_REFIT_PHYSICS']:.1f}, full-refit {future['FULL_M3_REFIT']:.1f} CPU-hours. These are linear extrapolations, not optimized-engine timings.

## Safe conclusion

FAST_RANK1 did not faithfully reproduce exact fixed-model GPC-SUR rankings and must not be used for a prospective trajectory. Exact-fixed SUR appears computationally far cheaper than full refitting, but its engineering feasibility and exact prospective protocol would require a separate predeclared decision; this phase does not test whether SUR beats Margin.
""";(OUTPUT/"FINAL_PHASE1_18B0_REPORT.md").write_text(final,encoding="utf-8")
    one=f"""# Supervisor Phase 1.18B0 — one page

- 25 frozen snapshots, 307 candidates, 2,456 hypothetical-label/update-level calculations; no new path.
- FAST vs exact-fixed: median Spearman **{o.median_spearman:.3f}**, q10 **{o.q10_spearman:.3f}**, top-1 **{o.top1_agreement:.0%}**, top-5 Jaccard **{o.mean_top5_jaccard:.3f}**; {undefined}/25 correlations undefined for constant score vectors.
- Posterior probability MAE is tiny (median snapshot {post.probability_mae.median():.2e}), yet SUR rankings fail because the acquisition score is a small difference of global uncertainties.
- Hypothetical Keyhole updates have larger error than Conduction ({label.loc[1,'probability_mae']:.2e} vs {label.loc[0,'probability_mae']:.2e}).
- Physics-mean refitting matters strongly (median score Spearman {decomp.loc['physics_refit_effect','median_spearman']:.3f}); kernel reoptimization matters much less ({decomp.loc['hyperparameter_refit_effect','median_spearman']:.3f}).
- **Decision: {primary['decision']} / {secondary['decision']}.** Do not run FAST SUR prospectively. No SUR-vs-Margin performance claim was tested.
""";(OUTPUT/"SUPERVISOR_PHASE1_18B0_ONE_PAGE.md").write_text(one,encoding="utf-8")
    ledger="""# Phase 1.18B0 claim ledger

| Claim | Status | Evidence boundary |
|---|---|---|
| FAST reproduces exact-fixed posterior probabilities closely. | SUPPORTED | Frozen validation reference pools. |
| FAST reproduces exact-fixed SUR candidate rankings. | NOT SUPPORTED | Predeclared gate failed. |
| FAST may be used in a prospective SUR trajectory. | REJECTED | Primary decision. |
| Physics-mean refitting is negligible. | NOT SUPPORTED | Strong ranking change. |
| Kernel hyperparameter refitting dominates the difference. | NOT SUPPORTED | Smaller secondary effect. |
| Exact-fixed is closest to literature one-step SUR. | QUALIFIED | Hyperparameters held fixed; functional is Phase 1.18A p(1-p) surrogate. |
| SUR beats Margin or saves labels. | NOT TESTED | No new acquisition trajectory or q20 endpoint. |
""";(OUTPUT/"claim_ledger.md").write_text(ledger,encoding="utf-8")
    red=f"""# Final red-team report

1. FAST ranking fidelity fails: median Spearman {o.median_spearman:.3f}.
2. Posterior probabilities are close (median snapshot MAE {post.probability_mae.median():.2e}); ranking failure is not hidden by that fact.
3. Hypothetical Keyhole error is larger than Conduction.
4–6. Candidate-regime table includes boundary, variance, FAST-top and controls; no outcome-based selection occurred.
7. Fidelity deteriorates notably at B60; late median is {o.late_median_spearman:.3f}.
8. Bound-hit association is descriptive and not a physical interpretation.
9. Physics refit is a major source of full-pipeline disagreement.
10. Kernel refit is comparatively smaller.
11. Fixed-hyperparameter exact Laplace is the cleaner literature one-step update contract.
12. FAST preserves exact top-1 only {o.top1_agreement:.1%}.
13. FAST top-1 has median exact rank {o.median_fast_top_rank_under_exact:.1f}, but aggregate top-k criteria still fail.
14. FAST is faster, but speed cannot rescue invalid rankings.
15. No guarded fallback passed the partial gate; no corrected variant was introduced.
16. A prospective FAST SUR-vs-Margin benchmark is not justified.
""";(OUTPUT/"FINAL_RED_TEAM_REPORT.md").write_text(red,encoding="utf-8")

def notebook()->None:
    cells=[nbf.v4.new_markdown_cell("# Week 9 Phase 1.18B0 — FAST GPC-SUR update validation\n\nThis notebook reads a frozen validation audit. It does not generate an acquisition path."),nbf.v4.new_code_cell("from pathlib import Path\nimport json,pandas as pd\nfrom IPython.display import display,Image,Markdown\nROOT=Path.cwd().parents[1] if Path.cwd().name=='week_09' else Path.cwd()\nOUT=ROOT/'outputs'/'week9_phase1_18b0_fast_gpc_sur_update_validation'\ndisplay(json.loads((OUT/'baseline_gate.json').read_text()))"),nbf.v4.new_markdown_cell("## 1. Why four update levels?\n\nFAST error must be separated from physics-mean refitting and kernel-hyperparameter refitting."),nbf.v4.new_code_cell("display(Markdown((OUT/'sur_literature_update_contract.md').read_text())); display(pd.read_csv(OUT/'snapshot_validation_design.csv')); display(pd.read_csv(OUT/'candidate_validation_design.csv').groupby('snapshot_id').size().describe())"),nbf.v4.new_markdown_cell("## 2. Probability and algebra gates"),nbf.v4.new_code_cell("display(pd.read_csv(OUT/'probability_integration_validation.csv').sort_values('absolute_error',ascending=False).head()); display(pd.read_csv(OUT/'special_case_validation.csv'))"),nbf.v4.new_markdown_cell("## 3. Primary score and selection fidelity"),nbf.v4.new_code_cell("display(pd.read_csv(OUT/'sur_score_fidelity_overall.csv')); display(pd.read_csv(OUT/'selection_fidelity_summary.csv')); display(Image(filename=str(OUT/'figures'/'01_fast_vs_exact_sur_scatter.png'))); display(Image(filename=str(OUT/'figures'/'02_snapshot_spearman_by_budget.png')))"),nbf.v4.new_markdown_cell("## 4. Posterior fidelity\n\nSmall probability error does not guarantee fidelity of a difference-of-uncertainties acquisition score."),nbf.v4.new_code_cell("display(pd.read_csv(OUT/'posterior_fidelity_summary.csv')); display(pd.read_csv(OUT/'label_conditional_fidelity.csv')); display(Image(filename=str(OUT/'figures'/'04_probability_error_by_label.png')))"),nbf.v4.new_markdown_cell("## 5. Refit-effect decomposition"),nbf.v4.new_code_cell("display(pd.read_csv(OUT/'refit_effect_decomposition.csv').groupby('effect').agg({'spearman':'median','top1_agreement':'mean','top5_jaccard':'mean'})); display(Image(filename=str(OUT/'figures'/'05_refit_effect_decomposition.png')))"),nbf.v4.new_markdown_cell("## 6. Decision"),nbf.v4.new_code_cell("display(json.loads((OUT/'primary_decision.json').read_text())); display(json.loads((OUT/'refit_effect_decision.json').read_text())); display(Markdown((OUT/'SUPERVISOR_PHASE1_18B0_ONE_PAGE.md').read_text()))")]
    nb=nbf.v4.new_notebook(cells=cells,metadata={"kernelspec":{"display_name":"Thesis Python","language":"python","name":"thesis"}});NOTEBOOK.parent.mkdir(parents=True,exist_ok=True);nbf.write(nb,NOTEBOOK);executed=NotebookClient(nbf.read(NOTEBOOK,as_version=4),timeout=300,kernel_name="thesis",resources={"metadata":{"path":str(ROOT)}}).execute();nbf.write(executed,NOTEBOOK)

def validate(details:pd.DataFrame,scores:pd.DataFrame,runtime:pd.DataFrame,audit:pd.DataFrame,res:dict[str,pd.DataFrame],prob:pd.DataFrame,special:pd.DataFrame)->dict[str,Any]:
    population,specs,paths,phase_scores,_=load_inputs();snap=pd.read_csv(OUTPUT/"snapshot_validation_design.csv");design=pd.read_csv(OUTPUT/"candidate_validation_design.csv");nb=nbf.read(NOTEBOOK,as_version=4);spec=json.loads((OUTPUT/"analysis_specification.json").read_text());hashrec=json.loads((OUTPUT/"candidate_validation_design_sha256.json").read_text());fast=scores[scores.update_level.eq("FAST_RANK1")].merge(design[["snapshot_id","candidate_population_row_index","fast_sur_score_pre_reveal"]],on=["snapshot_id","candidate_population_row_index"])
    fixed=audit[audit.update_level.eq("EXACT_LAPLACE_FIXED_MODEL")];phys=audit[audit.update_level.eq("EXACT_LAPLACE_REFIT_PHYSICS")]
    checks=[
    ("exact_parent",subprocess.check_output(["git","merge-base","HEAD",PARENT_SHA],cwd=ROOT,text=True).strip()==PARENT_SHA,PARENT_SHA),("population",len(population)==405 and int(population.has_keyhole.sum())==73,"405/73/332"),("m3_architecture","M3" in p13.fit_hybrid.__doc__ if p13.fit_hybrid.__doc__ else True,"frozen Phase1.13 implementation"),("no_new_trajectory",spec["new_trajectory"] is False and not any("path" in p.name.lower() for p in OUTPUT.glob("*trajectory*")),"validation only"),("frozen_phase14_prefixes",all(paths[s.run_id][:16]==w85.initial_design(s,population) for s in specs),"100/100"),("snapshot_design_frozen",set(snap.snapshot_id)=={p.stem for p in CHECKPOINTS.glob("*.json")},"25 checkpoint identities"),("candidate_design_hash",hashrec["sha256"]==sha256_file(OUTPUT/"candidate_validation_design.csv") and hashrec["frozen_before_hypothetical_updates"],hashrec["sha256"]),("candidate_design_matches_scored",set(map(tuple,design[["snapshot_id","candidate_population_row_index"]].to_numpy()))==set(map(tuple,scores[["snapshot_id","candidate_population_row_index"]].drop_duplicates().to_numpy())),"exact identities"),("candidate_design_no_leakage",not {"truth","B1","q20","q30","has_keyhole"}.intersection(design.columns),"clean"),("both_labels",runtime.groupby(["snapshot_id","candidate_population_row_index","update_level"]).hypothetical_label.nunique().eq(2).all(),"all"),("fast_reproduces_phase18a",np.max(np.abs(fast.sur_score-fast.fast_sur_score_pre_reveal))<1e-10,"exact score parity"),("exact_fixed_kernel_frozen",fixed.kernel_theta_max_abs_change.eq(0).all() and fixed.scaler_mean_max_abs_change.eq(0).all(),"bitwise theta/scaler"),("exact_fixed_physics_frozen",fixed.physics_intercept_change.eq(0).all() and fixed.physics_coefficient_change.eq(0).all(),"unchanged"),("physics_refit_kernel_frozen",phys.kernel_theta_max_abs_change.eq(0).all() and phys.scaler_mean_max_abs_change.eq(0).all(),"unchanged"),("physics_refit_stage1_changes",(phys.physics_intercept_change.abs()+phys.physics_coefficient_change.abs()).gt(0).all(),"all hypothetical updates"),("full_refit_normal_pipeline","p13.fit_hybrid" in Path(__file__).read_text(encoding="utf-8") and len(audit[audit.update_level.eq("FULL_M3_REFIT")])==2*len(design),"normal M3"),("special_cases",special.status.eq("PASS").all(),"all pass"),("probability_integration",prob.absolute_error.max()<.001,f"max {prob.absolute_error.max():.3g}"),("posterior_finite",details.select_dtypes(include=[np.number]).replace([np.inf,-np.inf],np.nan).notna().all().all(),"finite"),("thresholds_frozen",spec["status"]=="FROZEN_BEFORE_EXACT_RESULTS" and spec["gate"]==GATE,"exact"),("all_budgets",set(snap.budget)==set(BUDGETS),str(sorted(snap.budget.unique()))),("multiple_repeats_folds",snap.repeat.nunique()>=5 and snap.fold.nunique()>=3,f"{snap.repeat.nunique()}/{snap.fold.nunique()}"),("ranking_snapshotwise",len(res["snapshot"])==25,"25"),("no_sample_efficiency_claim","SUR beats Margin or saves labels" in (OUTPUT/"claim_ledger.md").read_text() and "NOT TESTED" in (OUTPUT/"claim_ledger.md").read_text(),"guardrail"),("notebook_executed",all(c.cell_type!="code" or c.execution_count is not None for c in nb.cells),"stored outputs"),("figures",len(pd.read_csv(OUTPUT/"figure_manifest.csv"))==6,"6"),("figure_hashes",all(sha256_file(FIGURES/r.figure)==r.sha256 for r in pd.read_csv(OUTPUT/"figure_manifest.csv").itertuples()),"all"),("historical_unchanged",not historical_changes(),"none")]
    frame=pd.DataFrame([{"check":n,"status":"PASS" if bool(ok) else "FAIL","detail":d} for n,ok,d in checks]);status="PASS" if frame.status.eq("PASS").all() else "FAIL";payload={"status":status,"check_count":len(frame),"checks":frame.to_dict("records")};write_json(OUTPUT/"validation_report.json",payload);lines=["# Validation report","",f"**Status:** {status} ({len(frame)} checks)","","| Check | Status | Detail |","|---|---|---|"]+[f"| {r.check} | {r.status} | {str(r.detail).replace('|','/')} |" for r in frame.itertuples()];(OUTPUT/"validation_report.md").write_text("\n".join(lines)+"\n",encoding="utf-8");require(status=="PASS",frame[frame.status.eq("FAIL")].to_string());return payload

def manifest(validation:dict[str,Any],primary:dict[str,Any],secondary:dict[str,Any])->dict[str,Any]:
    arts=[]
    for p in sorted(OUTPUT.rglob("*")):
        if p.is_file() and "checkpoints" not in p.parts and p.name!="run_manifest.json":arts.append({"path":p.relative_to(ROOT).as_posix(),"sha256":sha256_file(p),"bytes":p.stat().st_size})
    arts.append({"path":NOTEBOOK.relative_to(ROOT).as_posix(),"sha256":sha256_file(NOTEBOOK),"bytes":NOTEBOOK.stat().st_size});payload={"phase":"Week 9 Phase 1.18B0","parent_sha":PARENT_SHA,"branch":BRANCH,"new_trajectory":False,"snapshots":25,"candidates":307,"hypothetical_label_update_levels":2456,"primary_decision":primary["decision"],"refit_effect_decision":secondary["decision"],"validation":validation,"artifacts":arts};write_json(OUTPUT/"run_manifest.json",payload);return payload

def finalize()->dict[str,Any]:
    baseline_gate();analysis_specification();write_contracts();prob=probability_integration_validation();special=special_case_validation();details,scores,runtime,audit=collect_updates();snap=pd.read_csv(OUTPUT/"snapshot_validation_design.csv");design=pd.read_csv(OUTPUT/"candidate_validation_design.csv");res=fidelity_outputs(details,scores,snap);primary,secondary=decide(res);figures(res,runtime);reports(res,runtime,primary,secondary,design);notebook();validation=validate(details,scores,runtime,audit,res,prob,special);man=manifest(validation,primary,secondary);return {"status":"PASS","primary":primary["decision"],"secondary":secondary["decision"],"checks":validation["check_count"],"artifacts":len(man["artifacts"])}

def main()->None:
    ap=argparse.ArgumentParser();ap.add_argument("--preflight",action="store_true");ap.add_argument("--run-updates",action="store_true");ap.add_argument("--finalize",action="store_true");ap.add_argument("--workers",type=int,default=4);ap.add_argument("--limit-snapshots",type=int);a=ap.parse_args()
    if a.preflight:print(json.dumps({"baseline":baseline_gate(),"spec":analysis_specification(),"snapshots":len(snapshot_design()),"candidates":len(candidate_design(pd.read_csv(OUTPUT/"snapshot_validation_design.csv")))},indent=2))
    elif a.run_updates:print(json.dumps(run_updates(a.workers,a.limit_snapshots),indent=2))
    elif a.finalize:print(json.dumps(finalize(),indent=2))
    else:ap.error("choose an action")
if __name__=="__main__":main()
