"""Controlled reference checks, not a real-data benchmark or method search.

Run: python run_checks.py --output prototype_results.json
Only NumPy and SciPy are required; no repository data is imported.
Cases and comparisons are declared before the first fit in this file.
"""
import argparse
from dataclasses import replace, asdict
import hashlib
import json
from pathlib import Path
import platform
import time
import numpy as np
import scipy
from scipy.integrate import quad
from scipy.optimize import minimize
from scipy.special import expit, ndtr, log_ndtr
from joint_depth_label_gp import (Config, JointDepthLabelGP, fit_paid_prefix,
                                 phi2, probit_terms)


def metrics(y, p):
    y, p = np.asarray(y), np.asarray(p)
    yp = p >= .5
    ba = .5*(np.mean(yp[y==1])+np.mean(~yp[y==0])) if len(np.unique(y)) == 2 else None
    return {"BA": None if ba is None else float(ba), "Brier": float(np.mean((y-p)**2)),
            "log_loss": float(-np.mean(y*np.log(np.clip(p,1e-12,1))+(1-y)*np.log(np.clip(1-p,1e-12,1))))}


def plugin_threshold(z, y):
    """E1's scalar crossing rule, independently solved; not GP/ML-II parity."""
    z, y = np.asarray(z), np.asarray(y)
    kp, kn = z[y==1], z[y==0]
    if not len(kp) or not len(kn):
        return 0.0, {"branch": "E1_single_class_111um_fallback"}
    if max(kn) < min(kp):
        return .5*(max(kn)+min(kp)), {"branch": "midpoint"}
    def fun(ab):
        h = ab[0]+ab[1]*z
        p = expit(h)
        val = np.sum(np.logaddexp(0,h)-y*h)+.5e-6*ab[1]**2
        grad = np.array([np.sum(p-y), np.dot(p-y,z)+1e-6*ab[1]])
        return val, grad
    opt = minimize(fun, np.array([0.0,1.0]), jac=True, method="BFGS", options={"gtol":1e-9,"maxiter":1000})
    a,b = opt.x
    return (float(-a/b) if abs(b)>1e-12 else float("nan")), {"branch":"logistic", "a":float(a), "b":float(b), "gradient_inf":float(np.max(np.abs(opt.jac)))}


def main(output):
    start = time.perf_counter()
    cfg = Config()
    X = np.linspace(-1,1,61)[:,None]
    paid = np.linspace(0,60,13,dtype=int)
    held = np.setdiff1d(np.arange(len(X)),paid)
    xp = X[paid]
    f = .65*X[:,0]
    y = (f>=0).astype(int)
    result = {"status":"RUNNING", "scope":"Controlled synthetic correctness and mechanism checks only; no SPH inference", "config":asdict(cfg), "checks":{}, "cases":{}, "seed":20261012}
    C, cases = result["checks"], result["cases"]
    def require(name, condition, **values):
        C[name] = {"passed":bool(condition), **values}
        if not condition:
            raise AssertionError(f"{name}: {values}")
    fits = []
    def fit(config, xx=xp, yy=y[paid], zz=f[paid], **kwargs):
        obj = JointDepthLabelGP(X,config).fit(xx,yy,zz,**kwargs)
        fits.append(obj.diagnostics)
        return obj

    # 1. Analytic fixed-threshold and binary-only limits.
    known_cfg = replace(cfg,threshold_sd=0,discrepancy_amplitude=0,probit_scale=1e-6)
    known = fit(known_cfg,use_labels=False)
    q = known.posterior(X)
    plug_p = ndtr(q["f_mean"]/np.sqrt(np.diag(q["f_cov"])))
    err = float(np.max(np.abs(known.predict_proba(X)-plug_p)))
    require("known_threshold_E1_predictive_limit",err<1e-7,max_abs_error=err,
            qualifications="Same fixed-kernel response GP; labels disabled, discrepancy/threshold variance zero, tau near zero. Not hyperparameter-parity with repository E1.")
    cases["known_threshold"] = {"predictions":known.predict_proba(X).tolist(),"plugin_predictions":plug_p.tolist()}
    binary = fit(cfg,use_response=False)
    binary_other_z = fit(cfg,zz=np.linspace(-20,20,len(paid)),use_response=False)
    err = float(np.max(np.abs(binary.predict_proba(X)-binary_other_z.predict_proba(X))))
    require("binary_only_ignores_depth",err==0,max_abs_error=err)

    # 2. Threshold uncertainty before and after labels; joint covariance.
    uncertain = fit(cfg,use_labels=False)
    soft_known = fit(replace(cfg,threshold_sd=0),use_labels=False)
    pu,pk = uncertain.predict_proba(X),soft_known.predict_proba(X)
    require("threshold_uncertainty_softens_predictions",np.max(np.abs(pu-.5)-np.abs(pk-.5))<1e-12,
            max_probability_change=float(np.max(np.abs(pu-pk))))
    joint = fit(cfg)
    jq = joint.posterior(X)
    recon = (np.diag(jq["f_cov"])+jq["theta_var"]+np.diag(jq["delta_cov"])
             -2*jq["f_theta_cov"]+2*np.diag(jq["f_delta_cov"])-2*jq["delta_theta_cov"])
    recerr = float(np.max(np.abs(recon-np.diag(jq["h_cov"]))))
    require("joint_covariance_reconstruction",recerr<1e-10,max_abs_error=recerr)
    center_mean = float(abs(np.mean(jq["delta_mean"])))
    center_var = float(abs(np.mean(jq["delta_cov"])))
    require("discrepancy_exact_pool_centering",center_mean<1e-12 and center_var<1e-12,mean=center_mean,variance_of_pool_mean=center_var)
    independent_v = np.diag(jq["f_cov"])+jq["theta_var"]+np.diag(jq["delta_cov"])
    pind = ndtr(jq["h_mean"]/np.sqrt(cfg.probit_scale**2+independent_v))
    covdiff = float(np.max(np.abs(pind-joint.predict_proba(X))))
    require("posterior_independence_is_false",np.max(np.abs(jq["f_theta_cov"]))>1e-8 and covdiff>1e-5,
            max_abs_f_theta_cov=float(np.max(np.abs(jq["f_theta_cov"]))),max_probability_error_if_covariances_dropped=covdiff)
    require("labels_reduce_threshold_variance",jq["theta_var"]<cfg.threshold_sd**2,
            prior_sd=cfg.threshold_sd,posterior_sd=float(np.sqrt(jq["theta_var"])))
    cases["uncertain_threshold"] = {"posterior_theta_mean":jq["theta_mean"],"posterior_theta_sd":float(np.sqrt(jq["theta_var"])),
                                   "prior_probability":pu.tolist(),"posterior_probability":joint.predict_proba(X).tolist(),
                                   "response_only_mean":uncertain.posterior(X)["f_mean"].tolist(),"joint_mean":jq["f_mean"].tolist()}
    rng = np.random.default_rng(20261012)
    subset = np.arange(0,61,6)
    cov = jq["h_cov"][np.ix_(subset,subset)]
    eig, U = np.linalg.eigh((cov+cov.T)/2)
    draws = jq["h_mean"][subset]+rng.standard_normal((50000,len(subset)))@(U*np.sqrt(np.maximum(eig,0))).T
    pmc = ndtr(draws/cfg.probit_scale).mean(axis=0)
    mcerr = float(np.max(np.abs(pmc-joint.predict_proba(X[subset]))))
    require("marginal_probit_probability_matches_MC",mcerr<.005,max_abs_error=mcerr,n_draws=50000)

    # Expose approximation error against an exact one-dimensional posterior.
    scalar_cfg=replace(cfg,f_amplitude=0,discrepancy_amplitude=0)
    sy=np.array([1,1,1,1,1,0])
    scalar=fit(scalar_cfg,xx=np.linspace(-1,1,6)[:,None],yy=sy,zz=np.zeros(6))
    def density(theta):
        return np.exp(-.5*(theta/cfg.threshold_sd)**2+5*log_ndtr(-theta/cfg.probit_scale)+log_ndtr(theta/cfg.probit_scale))
    norm=quad(density,-np.inf,np.inf,epsabs=1e-12)[0]
    exact_mean=quad(lambda t:t*density(t),-np.inf,np.inf,epsabs=1e-12)[0]/norm
    exact_second=quad(lambda t:t*t*density(t),-np.inf,np.inf,epsabs=1e-12)[0]/norm
    exact_p=quad(lambda t:ndtr(-t/cfg.probit_scale)*density(t),-np.inf,np.inf,epsabs=1e-12)[0]/norm
    sq=scalar.posterior([[0]])
    cases["exact_scalar_threshold_reference"]={"exact_theta_mean":exact_mean,"Laplace_theta_mean":sq["theta_mean"],
                                               "exact_theta_sd":float(np.sqrt(exact_second-exact_mean**2)),"Laplace_theta_sd":float(np.sqrt(sq["theta_var"])),
                                               "exact_p":exact_p,"Laplace_p":float(scalar.predict_proba([[0]])[0]),
                                               "absolute_probability_error":abs(float(scalar.predict_proba([[0]])[0])-exact_p)}
    require("scalar_posterior_reference_finite",norm>0 and 0<exact_p<1,**cases["exact_scalar_threshold_reference"])

    # 3. Same depth, systematic input-dependent labels. Fixed case, no tuning.
    zflat = np.full(len(X),.15)
    delta_true = -.9*np.exp(-((X[:,0]-.5)/.25)**2)
    ym = (zflat+delta_true>=0).astype(int)
    mismatch = fit(cfg,yy=ym[paid],zz=zflat[paid])
    no_delta = fit(replace(cfg,discrepancy_amplitude=0),yy=ym[paid],zz=zflat[paid])
    binary_mismatch = fit(cfg,yy=ym[paid],zz=zflat[paid],use_response=False)
    all_preds = {"joint":mismatch.predict_proba(X),"without_discrepancy":no_delta.predict_proba(X),"binary_only":binary_mismatch.predict_proba(X)}
    r,rd = plugin_threshold(zflat[paid],ym[paid])
    rmodel = fit(cfg,yy=ym[paid],zz=zflat[paid],use_labels=False)
    rq = rmodel.posterior(X)
    pp = ndtr((rq["f_mean"]-r)/np.sqrt(np.diag(rq["f_cov"]))) if np.isfinite(r) else np.full(len(X),np.nan)
    cases["depth_label_mismatch"] = {"heldout_metrics":{k:metrics(ym[held],v[held]) for k,v in all_preds.items()},
                                     "predictions":{k:v.tolist() for k,v in all_preds.items()},
                                     "labels":ym.tolist(),"response":zflat.tolist(),"plugin_threshold":r if np.isfinite(r) else None,"plugin_details":rd,
                                     "plugin_heldout_metrics":metrics(ym[held],pp[held]) if np.isfinite(pp).all() else None}
    require("mismatch_representable",np.ptp(all_preds["joint"])>.2,
            probability_span=float(np.ptp(all_preds["joint"])),not_a_performance_gate=True)

    # 4. Sparse negatives, including none; deliberately report sensitivity.
    zs = .55*X[:,0]+.3
    ys = np.ones(len(paid),dtype=int); ys[-2]=0
    sparse = fit(cfg,yy=ys,zz=zs[paid])
    single = fit(cfg,yy=np.ones(len(paid)),zz=zs[paid])
    sp = sparse.posterior(X)
    sens = []
    for ts,ds in [(.15,.10),(.15,.60),(.70,.10),(.70,.60)]:
        model = fit(replace(cfg,threshold_sd=ts,discrepancy_amplitude=ds),yy=ys,zz=zs[paid])
        post = model.posterior(X)
        sens.append({"threshold_prior_sd":ts,"discrepancy_prior_sd":ds,"p_at_paid_negative":float(model.predict_proba(xp[-2: -1])[0]),
                     "posterior_theta_mean":post["theta_mean"],"posterior_theta_sd":float(np.sqrt(post["theta_var"]))})
    require("one_class_and_sparse_posteriors_finite",np.isfinite(sparse.predict_proba(X)).all() and np.isfinite(single.predict_proba(X)).all() and sp["theta_var"]>0,
            one_class_theta=single.posterior(X)["theta_mean"],one_negative_theta=sp["theta_mean"])
    cases["sparse_negatives"] = {"primary_p_at_paid_negative":float(sparse.predict_proba(xp[-2: -1])[0]),"sensitivity":sens,
                                  "note":"Sensitivity configurations expose assumptions; no winner is selected.","single_class_predictions":single.predict_proba(X).tolist()}

    # Structural failure: wrong depth bridge, and indistinguishable inputs.
    ya = (X[:,0]<0).astype(int)
    anti = fit(cfg,yy=ya[paid],zz=f[paid])
    anti_binary = fit(cfg,yy=ya[paid],zz=f[paid],use_response=False)
    cases["adverse_depth_bridge"] = {"joint":metrics(ya[held],anti.predict_proba(X[held])),
                                    "binary_only":metrics(ya[held],anti_binary.predict_proba(X[held])),
                                    "note":"Imposed positive depth effect can hurt under an anti-aligned true label law."}
    same = fit(cfg,xx=np.zeros((2,1)),yy=np.array([0,1]),zz=np.array([.1,.1]))
    ps = same.predict_proba(np.zeros((2,1)))
    require("identical_inputs_cannot_receive_distinct_probabilities",ps[0]==ps[1],probabilities=ps.tolist(),
            scope="Constructed identical-input case only; real matched depth traces have different four-input vectors.")

    # 5. Missing response retains canonical label and no unqueried-output leak.
    missing = f[paid].copy(); missing[2]=np.nan
    missing_model = fit(cfg,zz=missing)
    require("missing_response_preserves_label",missing_model.diagnostics["n_response"]==12 and missing_model.diagnostics["n_labels"]==13,
            diagnostics=missing_model.diagnostics)
    original = fit_paid_prefix(X,y,f,paid,cfg)
    fake_y,fake_z=y.copy(),f.copy();fake_y[held]=1-fake_y[held];fake_z[held]=1e3
    corrupted = fit_paid_prefix(X,fake_y,fake_z,paid,cfg)
    err = float(np.max(np.abs(original.predict_proba(X)-corrupted.predict_proba(X))))
    require("unpaid_output_corruption_no_effect",err==0,max_prediction_difference=err)
    ref_pred = joint.predict_proba(X[[12,40]])
    with_other_test = joint.predict_proba(np.vstack([X[[12,40]],[[5],[8]]]))[:2]
    require("test_batch_does_not_recenter_discrepancy",np.max(abs(ref_pred-with_other_test))<1e-12)

    # 6. Acquisition identity/convergence/bounds and useful paired information.
    cand = X[held[::5]]
    a15 = joint.acquisition(cand,gh_order=15,cdf_order=48)
    a31 = joint.acquisition(cand,gh_order=31,cdf_order=64)
    al = joint.acquisition(cand,observe_response=False,gh_order=31,cdf_order=64)
    az = joint.acquisition(cand,observe_label=False,gh_order=31,cdf_order=64)
    vs = float(joint.integrated_probability_variance(X).mean())
    err = float(np.max(abs(a15["score"]-a31["score"])))
    require("acquisition_quadrature_convergence",err<2e-5,max_abs_15_vs_31=err)
    require("acquisition_nonnegative_and_variance_bounded",np.min(a31["score"])>=0 and np.max(a31["score"])<=vs+2e-5,
            max_score=float(np.max(a31["score"])),current_integrated_variance=vs)
    require("joint_observation_contains_each_channel",np.min(a31["score"]-al["score"])>=-2e-5 and np.min(a31["score"]-az["score"])>=-2e-5,
            min_gain_over_label_only=float(np.min(a31["score"]-al["score"])),min_gain_over_depth_only=float(np.min(a31["score"]-az["score"])))
    leakscore = corrupted.acquisition(cand)["score"]
    origscore = original.acquisition(cand)["score"]
    require("unpaid_output_corruption_no_acquisition_effect",np.max(abs(leakscore-origscore))==0)
    # Known pi=.5 has zero epistemic value despite maximal Bernoulli entropy.
    null_cfg = replace(cfg,f_amplitude=0,discrepancy_amplitude=0,threshold_sd=0)
    null = fit(null_cfg,xx=np.empty((0,1)),yy=np.array([]),zz=np.array([]))
    nul = null.acquisition(cand)
    require("known_half_probability_has_zero_acquisition",np.all(null.predict_proba(cand)==.5) and np.max(abs(nul["score"]))<1e-15,
            max_score=float(np.max(nul["score"])))
    global_threshold=fit(replace(cfg,f_amplitude=0,discrepancy_amplitude=0),xx=np.empty((0,1)),yy=np.array([]),zz=np.array([]))
    rho=cfg.threshold_sd**2/(cfg.threshold_sd**2+cfg.probit_scale**2)
    analytic_score=4*(np.arcsin(rho)/(2*np.pi))**2
    computed=global_threshold.acquisition(cand)["score"]
    require("threshold_only_acquisition_analytic_identity",np.max(abs(computed-analytic_score))<1e-12,
            analytic_score=float(analytic_score),max_abs_error=float(np.max(abs(computed-analytic_score))))
    result["acquisition"]={"candidate_x":cand[:,0].tolist(),"joint":a31["score"].tolist(),"label_only":al["score"].tolist(),"depth_only":az["score"].tolist(),
                           "response_component":a31["response_component"].tolist(),"label_component":a31["label_component"].tolist(),
                           "selected_x":float(cand[int(np.argmax(a31["score"])),0]),"tie_rule":"first candidate in fixed ordered list"}
    # One paid update, counting one simulation, refitting original data once.
    new_i = int(held[::5][int(np.argmax(a31["score"]))])
    updated_ids=np.r_[paid,new_i]
    updated=fit(cfg,xx=X[updated_ids],yy=y[updated_ids],zz=f[updated_ids])
    result["one_query_update"]={"before_n":len(paid),"after_n":len(updated_ids),"paid_index":new_i,"Y":int(y[new_i]),"z":float(f[new_i]),
                                "theta_sd_before":float(np.sqrt(jq["theta_var"])),"theta_sd_after":float(np.sqrt(updated.posterior(X)["theta_var"])),
                                "integrated_variance_before":vs,"integrated_variance_after":float(updated.integrated_probability_variance(X).mean())}

    # Numerical special functions verified against independent integration.
    errs=[]
    for aa,bb,rr in [(-2,.3,.9),(.1,-.5,-.8),(0,0,.999999),(2,2,.9999),(-3,-2,.75)]:
        angle=np.arcsin(rr)
        val=ndtr(aa)*ndtr(bb)+quad(lambda t:np.exp(-(aa*aa-2*np.sin(t)*aa*bb+bb*bb)/(2*np.cos(t)**2)),0,angle,epsabs=1e-12)[0]/(2*np.pi)
        errs.append(abs(float(phi2(aa,bb,rr,64))-val))
    require("bivariate_CDF_independent_quadrature",max(errs)<1e-8,max_abs_error=max(errs))
    boundary_error=max(abs(float(phi2(0,.01,1))-.5),abs(float(phi2(0,.01,-1))-(ndtr(.01)-.5)),
                       abs(float(phi2(0,.01,1-1e-12))-.5))
    require("bivariate_CDF_near_singular_guard",boundary_error<1e-9,max_abs_error=boundary_error)
    narrow_errors=[]
    for bb in [-1e-5,1e-5]:
        for rr in [-1+1e-12,1-1e-12]:
            value=float(phi2(0,bb,rr))
            limit=min(.5,ndtr(bb)) if rr>0 else max(0,ndtr(bb)-.5)
            narrow_errors.append(abs(value-limit))
    require("bivariate_CDF_narrow_endpoint_guard",max(narrow_errors)<1e-9,max_abs_error=max(narrow_errors))
    tt=np.array([-1e5,-1e4,-100,-31,-30,-10,0,10],float)
    lp,ratio,curv=probit_terms(tt)
    require("probit_tail_curvature",np.isfinite(ratio).all() and np.all((curv>=0)&(curv<=1)) and abs(curv[0]-1)<1e-8,curvature=curv.tolist())
    t0=np.array([-5,-1,.1,2]);eps=1e-5
    l0,r0,k0=probit_terms(t0)
    lplus,rplus,_=probit_terms(t0+eps);lminus,rminus,_=probit_terms(t0-eps)
    derr=max(float(np.max(abs((lplus-lminus)/(2*eps)-r0))),float(np.max(abs(-(rplus-rminus)/(2*eps)-k0))))
    require("probit_derivatives_finite_difference",derr<1e-6,max_abs_error=derr)

    fits.extend([original.diagnostics, corrupted.diagnostics])
    result["fits"]=fits
    result["n_model_fits"]=len(fits)
    result["grid"]={"x":X[:,0].tolist(),"paid_indices":paid.tolist(),"heldout_indices":held.tolist()}
    result["environment"]={"python":platform.python_version(),"numpy":np.__version__,"scipy":scipy.__version__}
    result["seconds"]=time.perf_counter()-start
    result["status"]="PASS" if all(v["passed"] for v in C.values()) else "FAIL"
    result["source_sha256"]={p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in [Path(__file__),Path(__file__).with_name("joint_depth_label_gp.py"),Path(__file__).with_name("SELECTION_RECORD.json")]}
    Path(output).write_text(json.dumps(result,indent=2,allow_nan=False),encoding="utf-8")
    print(json.dumps({"status":result["status"],"n_checks":len(C),"n_model_fits":result["n_model_fits"],"seconds":result["seconds"],
                      "mismatch":cases["depth_label_mismatch"]["heldout_metrics"],"adverse":cases["adverse_depth_bridge"],
                      "sparse_p":cases["sparse_negatives"]["primary_p_at_paid_negative"],"scalar_reference":cases["exact_scalar_threshold_reference"],
                      "acquisition_selected_x":result["acquisition"]["selected_x"],"update":result["one_query_update"]},indent=2))


if __name__ == "__main__":
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output",default=str(Path(__file__).with_name("prototype_results.json")))
    main(parser.parse_args().output)
