"""Deterministic correctness and independent quadrature references.

References integrate the non-Gaussian posterior, not an EP Gaussian. There
are no real observations or held-out parameter choices in this file.
"""
import os
for name in ("OMP_NUM_THREADS","OPENBLAS_NUM_THREADS","MKL_NUM_THREADS"):
    os.environ[name]="1"
from pathlib import Path
from dataclasses import replace
import hashlib, itertools, json, time
import numpy as np
from scipy.integrate import quad
from scipy.linalg import cho_factor,cho_solve
from scipy.special import ndtr,log_ndtr,logsumexp
from joint_model_v2 import JointModelV2,Component,infer_probit,gh
from v1_reference import Config,JointDepthLabelGP,phi2

ROOT=Path(__file__).resolve().parent


def prior_component(ref,xp,y,z,c,rho):
    obj=Component(ref,c,rho)
    obj.xp=np.asarray(xp,float);obj.yp=np.asarray(y)
    good=np.isfinite(z);obj.xo=obj.xp[good]
    if good.any():
        K=obj.kf(obj.xo,obj.xo)
        K.flat[::len(K)+1]+=c.response_noise_sd**2+c.jitter
        obj.zchol=cho_factor(K,lower=True)
        obj.za=cho_solve(obj.zchol,np.asarray(z)[good])
    return obj


def exact_quadrature(ref,xp,y,z,xt,c,order=80,rhos=(0.,.5,1.)):
    """Independent tensor Gaussian-prior integration, n_paid <= 2."""
    if len(y)>2:raise ValueError("Reference restricted to tractable dimension")
    u,w=gh(order)
    grids=list(itertools.product(range(order),repeat=len(y)))
    nodes=np.array([[u[j] for j in g] for g in grids])
    logw=np.array([sum(np.log(w[j]) for j in g) for g in grids])
    records=[]
    for rho in rhos:
        obj=prior_component(ref,xp,y,z,c,rho)
        mp,K=obj.prior_h(xp);K=K+c.jitter*np.eye(len(K))
        hp=mp+nodes@np.linalg.cholesky(K).T
        ll=log_ndtr((2*np.asarray(y)-1)*hp/c.probit_scale).sum(1)
        lZ=logsumexp(logw+ll)
        weights=np.exp(logw+ll-lZ)
        mf,cf=obj.response(xt);mh,ch=obj.prior_h(xt)
        _,cfp=obj.response(xt,xp);_,chp=obj.prior_h(xt,xp)
        cross=np.vstack([rho*cfp,chp])
        prior_cov=np.block([[cf,rho*cf],[rho*cf,ch]])
        gain=cho_solve(cho_factor(K,lower=True),cross.T).T
        condcov=prior_cov-gain@cross.T
        conditional=np.r_[mf,mh]+(hp-mp)@gain.T
        mean=weights@conditional
        diff=conditional-mean
        cov=condcov+(diff.T*weights)@diff
        M=len(xt);v=np.maximum(np.diag(condcov)[M:],0)
        aa=conditional[:,M:]/np.sqrt(c.probit_scale**2+v)
        p=weights@ndtr(aa)
        J=np.empty((M,M))
        for j in range(M):
            corr=condcov[M:,M+j]/np.sqrt((c.probit_scale**2+v)*(c.probit_scale**2+v[j]))
            J[:,j]=weights@phi2(aa,aa[:,j,None],corr[None,:])
        records.append({"logZ":lZ,"mean":mean,"cov":cov,"p":p,"J":J})
    logmass=np.array([r["logZ"] for r in records])-np.log(len(rhos))
    mass=np.exp(logmass-logsumexp(logmass))
    mean=sum(w*r["mean"] for w,r in zip(mass,records))
    cov=sum(w*(r["cov"]+np.outer(r["mean"]-mean,r["mean"]-mean)) for w,r in zip(mass,records))
    p=sum(w*r["p"] for w,r in zip(mass,records))
    J=sum(w*r["J"] for w,r in zip(mass,records))
    scores=np.mean((J-p[:,None]*p[None,:])**2,axis=0)/(p*(1-p))
    return {"weights":mass,"p":p,"mean":mean,"cov":cov,
            "label_scores":scores,"log_evidence":float(logsumexp(logmass))}


def exact_single_label_paired(ref,xp,y,z,xt,c,z_order=31,h_order=64):
    """True single-label posterior, integrating h_paid and future depth.

    Condition Gaussian priors on z and a fantasy Z. Integrate the existing
    probit label by independent quadrature; then value the next paired output.
    This deliberately does not condition a moment-matched posterior Gaussian.
    """
    if len(y)!=1:raise ValueError("One paid label required")
    rhos=(0.,.5,1.);prior=np.ones(3)/3
    M=len(xt);X=np.vstack([xt,xp]);sign=2*y[0]-1
    objects=[prior_component(ref,xp,y,z,c,r) for r in rhos]
    priors=[]
    for obj in objects:
        mf,cf=obj.response(X);mh,ch=obj.prior_h(X)
        Zold=ndtr(sign*mh[-1]/np.sqrt(c.probit_scale**2+ch[-1,-1]))
        # E[pi_i * old-label likelihood] is a bivariate normal probability.
        a=mh[:M]/np.sqrt(c.probit_scale**2+np.diag(ch)[:M])
        b=sign*mh[-1]/np.sqrt(c.probit_scale**2+ch[-1,-1])
        corr=sign*ch[:M,-1]/np.sqrt((c.probit_scale**2+np.diag(ch)[:M])*(c.probit_scale**2+ch[-1,-1]))
        numer=phi2(a,b,corr)
        priors.append(dict(mf=mf,cf=cf,mh=mh,ch=ch,fh=obj.rho*cf,Zold=Zold,numer=numer))
    Zall=sum(w*q["Zold"] for w,q in zip(prior,priors))
    base=sum(w*q["numer"] for w,q in zip(prior,priors))/Zall
    zn,zw=gh(z_order);hn,hw=gh(h_order)
    scores=[];normalizations=[]
    for j in range(M):
        fmeans=np.array([q["mf"][j] for q in priors])
        fvars=np.array([q["cf"][j,j]+c.response_noise_sd**2 for q in priors])
        zz=(fmeans[:,None]+np.sqrt(fvars[:,None])*zn).ravel()
        weights0=(prior[:,None]*zw).ravel()
        lw=np.log(prior)[:,None]-.5*(np.log(2*np.pi*fvars)[:,None]+(zz-fmeans[:,None])**2/fvars[:,None])
        wz=np.exp(lw-logsumexp(lw,axis=0))
        pks=[];Jks=[];oldps=[]
        for k,q in enumerate(priors):
            cross=q["fh"][j]
            C=q["ch"]-np.outer(cross,cross)/fvars[k]
            m=q["mh"][None,:]+(zz-fmeans[k])[:,None]*cross[None,:]/fvars[k]
            vold=C[-1,-1]
            oldp=ndtr(sign*m[:,-1]/np.sqrt(c.probit_scale**2+vold))
            hp=m[:,-1,None]+np.sqrt(vold)*hn
            likelihood=ndtr(sign*hp/c.probit_scale)
            conditional=m[:,:M,None]+(C[:M,-1]/vold)[None,:,None]*(hp-m[:,-1,None])[:,None,:]
            # Arrange fantasy x old-latent-node x test-input.
            conditional=conditional.transpose(0,2,1)
            V=C[:M,:M]-np.outer(C[:M,-1],C[:M,-1])/vold
            den=np.sqrt(c.probit_scale**2+np.maximum(np.diag(V),0))
            aa=conditional/den
            pp=np.einsum("gn,gnm,n->gm",likelihood,ndtr(aa),hw)/oldp[:,None]
            corr=V[:,j]/(den*den[j])
            JJ=phi2(aa,aa[:,:,j,None],corr[None,None,:])
            JJ=np.einsum("gn,gnm,n->gm",likelihood,JJ,hw)/oldp[:,None]
            pks.append(pp);Jks.append(JJ);oldps.append(oldp)
        oldps=np.array(oldps)
        A=np.sum(wz*oldps,axis=0)
        posterior_weights=wz*oldps/A
        pp=np.einsum("kg,kgm->gm",posterior_weights,np.array(pks))
        JJ=np.einsum("kg,kgm->gm",posterior_weights,np.array(Jks))
        q=pp[:,j]
        term=np.mean((pp-base)**2,axis=1)
        valid=(q>1e-10)&(q<1-1e-10)
        term[valid]+=np.mean((JJ[valid]-pp[valid]*q[valid,None])**2,axis=1)/(q[valid]*(1-q[valid]))
        integral_weights=weights0*A/Zall
        normalizations.append(float(integral_weights.sum()))
        scores.append(float(integral_weights@term))
    return {"p":base,"scores":np.array(scores),"normalizations":normalizations,
            "z_order":z_order,"h_order":h_order}


def decision_counterexample():
    """Exact finite-pool expected BA; no threshold optimized on held-out labels."""
    eta=np.array([.10,.65,.75,.85,.90,.95])
    n=len(eta)
    worlds=np.array(list(itertools.product([0,1],repeat=n)),int)
    probability=np.prod(np.where(worlds==1,eta,1-eta),axis=1)
    counts=worlds.sum(1);valid=(counts>0)&(counts<n)
    worlds=worlds[valid];probability=probability[valid];counts=counts[valid]
    retained=float(probability.sum());probability/=retained
    positive_weight=probability@(worlds/counts[:,None])
    negative_weight=probability@((1-worlds)/(n-counts[:,None]))
    exact=positive_weight>=negative_weight
    half=eta>=.5;prev=eta>=eta.mean()
    def utility(pred):
        sens=(worlds*pred).sum(1)/counts
        spec=((1-worlds)*(1-pred)).sum(1)/(n-counts)
        return float(probability@(.5*(sens+spec)))
    # The paid sample overrepresents high-probability inputs; its fraction is
    # not the feature-pool prevalence and can degenerate to one.
    return {"eta":eta,"pool_expected_prevalence":float(eta.mean()),
            "paid_ids":[3,4,5],"paid_labels":[1,1,1],"paid_fraction":1.,
            "retained_two_class_probability":retained,
            "decision_half":half,"decision_prevalence_plugin":prev,
            "decision_exact_finite_pool":exact,
            "expected_BA_half":utility(half),
            "expected_BA_prevalence_plugin":utility(prev),
            "expected_BA_exact":utility(exact),
            "note":"Exact probabilities can need a different BA decision. This is not evidence that C3 is solely a calibration or threshold problem."}


def run():
    start=time.perf_counter();checks={};diagnostics={};count=0
    def check(name,condition,**details):
        checks[name]={"passed":bool(condition),**details}
        if not condition:raise AssertionError(name)
    def fit(ref,X,y,z,**kwargs):
        nonlocal count
        obj=JointModelV2(ref,**kwargs).fit(X,y,z)
        count+=obj.solve_count
        return obj
    c=Config();ref=np.linspace(-1,1,17)[:,None]
    xp=ref[[2,8,14]];y=np.array([0,1,1]);z=np.array([-.4,.05,.5])
    v1=JointDepthLabelGP(ref,c).fit(xp,y,z);count+=1
    endpoint=fit(ref,xp,y,z,config=c,rhos=(1.,),inference="laplace")
    error=float(np.max(abs(v1.predict_proba(ref)-endpoint.predict_proba(ref))))
    check("rho1_Laplace_matches_immutable_V1",error<2e-7,max_abs_error=error)
    mix=fit(ref,xp,y,z,config=c)
    check("proper_component_weights",abs(mix.weights.sum()-1)<1e-12 and np.all(mix.weights>0),weights=mix.weights.tolist())
    for k,q in enumerate(mix.component_posteriors(ref,full=True)):
        err=max(np.max(abs(q["H"]@q["joint_mean"]-q["h_mean"])),
                np.max(abs(q["H"]@q["joint_cov"]@q["H"].T-q["h_cov"])))
        check(f"component_{k}_joint_covariance_identity",err<1e-9,error=float(err))
    binary=JointModelV2(ref,c).fit(xp,y,z,use_response=False);count+=binary.solve_count
    zerobridge=fit(ref,xp,y,z,config=c,rhos=(0.,))
    check("rho0_equals_binary",np.max(abs(binary.predict_proba(ref)-zerobridge.predict_proba(ref)))<1e-9)
    check("binary_weights_remain_prior",np.max(abs(binary.weights-binary.prior_weights))<1e-12)
    altered=fit(ref,xp,y,z+2,config=c,rhos=(0.,))
    check("rho0_ignores_depth_values",np.max(abs(altered.predict_proba(ref)-zerobridge.predict_proba(ref)))<1e-9)
    missing=z.copy();missing[1]=np.nan
    missingfit=fit(ref,xp,y,missing,config=c,rhos=(1.,))
    check("missing_response_retains_label",missingfit.diagnostics["n_paid"]==3 and missingfit.diagnostics["n_response"]==2)
    q=mix.posterior(ref)
    manual=sum(w*(v["h_cov"]+np.outer(v["h_mean"]-q["h_mean"],v["h_mean"]-q["h_mean"]))
               for w,v in zip(mix.weights,mix.component_posteriors(ref)))
    check("mixture_between_component_covariance",np.max(abs(q["h_cov"]-manual))<1e-10)
    a=endpoint.acquisition(ref[4:7])
    b=v1.acquisition(ref[4:7])
    check("single_component_acquisition_V1_identity",np.max(abs(a["score"]-b["score"]))<1e-8,
          error=float(np.max(abs(a["score"]-b["score"]))))
    acq=mix.acquisition(ref[4:7])
    fine=mix.acquisition(ref[4:7],gh_order=31,cdf_order=64)
    total=float(mix.integrated_probability_variance(ref).mean())
    check("mixture_acquisition_variance_bound",np.min(acq["score"])>=0 and np.max(acq["score"])<=total+1e-7)
    check("quadrature_on_checked_case",np.max(abs(fine["score"]-acq["score"]))<1e-5,
          error=float(np.max(abs(fine["score"]-acq["score"]))))
    # A single probit factor has analytically exact Gaussian tilted moments.
    m=np.array([.4]);K=np.array([[.3]])
    ep=infer_probit(m,K,np.array([0]),.15,"ep");count+=1
    den=np.sqrt(.15**2+.3);t=-.4/den
    rat=np.exp(-t*t/2-.5*np.log(2*np.pi)-log_ndtr(t))
    exactmean=.4-.3/den*rat
    exactvar=.3-.3**2/den**2*rat*(rat+t)
    check("EP_single_factor_exact_moments",abs(ep["mean"][0]-exactmean)<1e-8 and abs(ep["cov"][0,0]-exactvar)<1e-8)
    check("EP_single_factor_exact_evidence",abs(ep["log_evidence"]-log_ndtr(t))<1e-8)
    # V1's scalar uncertain-threshold example; numerical reference, not a fit.
    scalar=replace(c,f_amplitude=0.,discrepancy_amplitude=0.)
    X=np.zeros((6,1));Y=np.array([1,1,1,1,1,0]);Z=np.full(6,np.nan)
    se=fit(np.zeros((1,1)),X,Y,Z,config=scalar,rhos=(1.,))
    sl=fit(np.zeros((1,1)),X,Y,Z,config=scalar,rhos=(1.,),inference="laplace")
    def density(theta):
        ll=5*log_ndtr(-theta/.15)+log_ndtr(theta/.15)
        return np.exp(ll-theta*theta/(2*.35**2))/(np.sqrt(2*np.pi)*.35)
    norm=quad(density,-3,3,epsabs=1e-12)[0]
    mean=quad(lambda t:t*density(t),-3,3,epsabs=1e-12)[0]/norm
    var=quad(lambda t:(t-mean)**2*density(t),-3,3,epsabs=1e-12)[0]/norm
    prob=quad(lambda t:ndtr(-t/.15)*density(t),-3,3,epsabs=1e-12)[0]/norm
    diagnostics["scalar_threshold"]={"exact_probability":prob,"exact_theta_mean":mean,"exact_theta_variance":var}
    for label,obj in [("EP",se),("Laplace",sl)]:
        q=obj.posterior(np.zeros((1,1)))
        p=float(obj.predict_proba(np.zeros((1,1)))[0])
        diagnostics["scalar_threshold"][label]={"probability":p,"probability_error":abs(p-prob),
            "theta_mean":q["theta_mean"],"theta_variance":q["theta_var"],
            "variance_error":abs(q["theta_var"]-var)}
    # Independent two-dimensional integration validates weights, covariances,
    # predictions and label-only acquisition under the true non-Gaussian law.
    xt=np.array([[-.4],[.45],[.85]]);xx=np.array([[-.7],[.1]])
    yy=np.array([0,1]);zz=np.array([-.15,.35])
    mm=fit(ref,xx,yy,zz,config=c)
    exact=exact_quadrature(ref,xx,yy,zz,xt,c,80)
    exact2=exact_quadrature(ref,xx,yy,zz,xt,c,120)
    q=mm.posterior(xt)
    cov=np.block([[q["f_cov"],q["f_h_cov"]],[q["f_h_cov"].T,q["h_cov"]]])
    la=mm.acquisition(xt,x_integrate=xt,observe_response=False)
    diagnostics["two_label_reference"]={
        "quadrature_p_difference":float(np.max(abs(exact["p"]-exact2["p"]))),
        "probability_max_error":float(np.max(abs(mm.predict_proba(xt)-exact2["p"]))),
        "joint_covariance_max_error":float(np.max(abs(cov-exact2["cov"]))),
        "weight_max_error":float(np.max(abs(mm.weights-exact2["weights"]))),
        "EP_weights":mm.weights,"reference_weights":exact2["weights"],
        "EP_label_scores":la["score"],"reference_label_scores":exact2["label_scores"],
        "EP_selected":int(np.argmax(la["score"])),"reference_selected":int(np.argmax(exact2["label_scores"]))}
    check("two_label_quadrature_convergence",diagnostics["two_label_reference"]["quadrature_p_difference"]<2e-4)
    # Paired acquisition is also checked against a non-Gaussian posterior.
    xx=xx[:1];yy=np.array([0]);zz=np.array([.25])
    single=fit(ref,xx,yy,zz,config=c)
    e1=exact_single_label_paired(ref,xx,yy,zz,xt,c,31,64)
    e2=exact_single_label_paired(ref,xx,yy,zz,xt,c,63,96)
    aa=single.acquisition(xt,x_integrate=xt,gh_order=63,cdf_order=64)
    diagnostics["single_label_paired_reference"]={
        "reference_score_convergence":float(np.max(abs(e1["scores"]-e2["scores"]))),
        "reference_mass_error":float(np.max(abs(np.array(e2["normalizations"])-1))),
        "probability_error":float(np.max(abs(single.predict_proba(xt)-e2["p"]))),
        "score_max_error":float(np.max(abs(aa["score"]-e2["scores"]))),
        "EP_scores":aa["score"],"reference_scores":e2["scores"],
        "EP_selected":int(np.argmax(aa["score"])),"reference_selected":int(np.argmax(e2["scores"]))}
    check("paired_reference_quadrature_convergence",diagnostics["single_label_paired_reference"]["reference_score_convergence"]<1e-4)
    diagnostics["decision_counterexample"]=decision_counterexample()
    from run_controlled import clean
    result={"status":"PASS","checks":checks,"diagnostics":diagnostics,
            "correctness_component_solves":count,
            "separately_counted_reference_evaluations":7,
            "seconds":time.perf_counter()-start,
            "source_sha256":{p.name:hashlib.sha256(p.read_bytes()).hexdigest()
              for p in [Path(__file__),ROOT/"joint_model_v2.py",ROOT/"v1_reference.py"]}}
    (ROOT/"NUMERICAL_REFERENCES.json").write_text(json.dumps(clean(result),indent=2),encoding="utf-8")
    print(json.dumps(clean(result),indent=2),flush=True)


if __name__=="__main__":
    run()
