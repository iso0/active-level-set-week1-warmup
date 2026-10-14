"""Only the checks frozen in AMENDMENT_01_DIAGNOSTICS.md."""
import os
for key in ("OMP_NUM_THREADS","OPENBLAS_NUM_THREADS","MKL_NUM_THREADS"):
    os.environ[key]="1"
from pathlib import Path
import hashlib,json,pickle,time
import numpy as np
from scipy.special import log_ndtr,ndtr
import joint_model_v2 as V
from v1_reference import Config,JointDepthLabelGP
from controlled_worlds import make_world,config
from run_controlled import clean,save,ROOT


def ess_chain(m,K,y,tau,seed,burn=2000,keep=8000):
    rng=np.random.default_rng(seed)
    L=np.linalg.cholesky(K)
    v=2*rng.normal(size=len(y))
    signs=2*y-1
    def loglike(v):
        return float(log_ndtr(signs*(m+L@v)/tau).sum())
    ll=loglike(v);draws=[];evaluations=1
    for step in range(burn+keep):
        direction=rng.normal(size=len(y))
        threshold=ll+np.log(rng.uniform())
        angle=rng.uniform(0,2*np.pi);lo=angle-2*np.pi;hi=angle
        for _ in range(10000):
            candidate=v*np.cos(angle)+direction*np.sin(angle)
            proposal=loglike(candidate);evaluations+=1
            if proposal>=threshold:
                v=candidate;ll=proposal;break
            if angle<0:lo=angle
            else:hi=angle
            angle=rng.uniform(lo,hi)
        else:
            raise RuntimeError("Elliptical slice bracket exhausted")
        if step>=burn:draws.append(m+L@v)
    return np.array(draws),evaluations


def rhat(chains):
    # Conventional split R-hat; not rank-normalized.
    halves=np.concatenate([chains[:,:chains.shape[1]//2],chains[:,chains.shape[1]//2:]],axis=0)
    n=halves.shape[1]
    W=halves.var(axis=1,ddof=1).mean(axis=0)
    B=n*halves.mean(axis=1).var(axis=0,ddof=1)
    return np.sqrt(((n-1)/n*W+B/n)/W)


def run():
    start=time.perf_counter()
    X=np.linspace(-1,1,61)[:,None];paid=np.arange(0,61,5)
    yp=np.ones(13,dtype=int);yp[-2]=0
    z=.55*X[:,0]+.3;xp=X[paid];zp=z[paid];c=Config()
    v1=JointDepthLabelGP(X,c).fit(xp,yp,zp)
    ep=V.JointModelV2(X,c,rhos=(1.,)).fit(xp,yp,zp)
    mix=V.JointModelV2(X,c).fit(xp,yp,zp)
    count=1+ep.solve_count+mix.solve_count
    predictions={name:float(model.predict_proba(xp[-2:-1])[0])
                 for name,model in [("V1_Laplace",v1),("rho1_EP",ep),("V2_EP_mixture",mix)]}
    m,K=ep.components[0].hp_prior
    chains=[];evaluations=[]
    for seed in (4301,4302,4303,4304):
        samples,evals=ess_chain(m,K,yp,c.probit_scale,seed)
        chains.append(samples);evaluations.append(evals)
    chains=np.array(chains)
    pp=ndtr(chains[:,:,-2]/c.probit_scale)
    batches=pp.reshape(4,32,250).mean(2).ravel()
    mcse=float(batches.std(ddof=1)/np.sqrt(len(batches)))
    rh=float(np.max(rhat(chains)))
    prh=float(rhat(pp[:,:,None])[0])
    cov=np.cov(chains.reshape(-1,len(yp)),rowvar=False)
    approx=ep.components[0].inf["cov"]
    sample_path=ROOT/"V1_SPARSE_REFERENCE_SAMPLES.npz"
    np.savez_compressed(sample_path,h_paid=chains,paid_ids=paid)
    reference={"target":"Fixed rho=1 V1 posterior; not the V2 mixture",
        "seeds":[4301,4302,4303,4304],"warmup_per_chain":2000,
        "retained_per_chain":8000,"likelihood_evaluations":evaluations,
        "probability_mean":float(pp.mean()),"batch_MCSE":mcse,
        "probability_split_Rhat":prh,"maximum_latent_split_Rhat":rh,
        "chain_probability_means":pp.mean(1),
        "EP_probability_error":abs(predictions["rho1_EP"]-pp.mean()),
        "Laplace_probability_error":abs(predictions["V1_Laplace"]-pp.mean()),
        "EP_paid_covariance_max_error":float(np.max(abs(cov-approx))),
        "status":"accepted_reference" if rh<=1.05 and mcse<=.01 else "inconclusive_reference",
        "samples_sha256":hashlib.sha256(sample_path.read_bytes()).hexdigest()}
    # Actual runner data boundary: same stored world and paid prefix, corrupt all
    # other outcomes before extracting the paid arrays.
    w=make_world("informative_depth",1301)
    prefix=w["path"][:16]
    original=pickle.loads((ROOT/"checkpoints/static_informative_depth_1301_B16_V2_EP_mixture.pkl").read_bytes())
    corrupt=np.ones(len(w["y"]),bool);corrupt[prefix]=False
    w["y"][corrupt]=1-w["y"][corrupt];w["z"][corrupt]=12345.
    repeated=V.JointModelV2(w["X"][w["pool"]],config()).fit(w["X"][prefix],w["y"][prefix],w["z"][prefix])
    count+=repeated.solve_count
    prob_error=float(np.max(abs(original.predict_proba(w["X"])-repeated.predict_proba(w["X"]))))
    candidates=np.array([i for i in w["pool"] if i not in prefix])
    score_error=float(np.max(abs(original.acquisition(w["X"][candidates])["score"]-
                                 repeated.acquisition(w["X"][candidates])["score"])))
    # Deliberately trigger the documented numerical fallback; no experimental
    # outcome is consulted and no actual experiment needed fallback.
    saved=V.infer_probit
    def forced(m,K,y,tau,method):
        if method=="ep":raise RuntimeError("Injected EP failure for policy test")
        return saved(m,K,y,tau,method)
    V.infer_probit=forced
    try:
        fallback=V.JointModelV2(X,c).fit(xp,yp,zp)
    finally:
        V.infer_probit=saved
    count+=fallback.solve_count
    fallback_ok=(fallback.diagnostics["fallback"] and len(fallback.components)==3 and
                 all(q["method"]=="laplace" for q in fallback.diagnostics["components"]))
    result={"status":"PASS" if prob_error<1e-12 and score_error<1e-12 and fallback_ok else "FAIL",
        "amendment":"AMENDMENT_01_DIAGNOSTICS.md","controlled_requests":5,
        "component_solves":count,"numerical_reference_chains":4,
        "V1_sparse_case":{"X":X,"paid_ids":paid,"paid_y":yp,"paid_z":zp,
          "probabilities":predictions,"V2_rho_weights":mix.weights,"reference":reference},
        "leakage_check":{"max_probability_change":prob_error,"max_acquisition_change":score_error},
        "injected_fallback_check":{"passed":fallback_ok,"diagnostics":fallback.diagnostics},
        "seconds":time.perf_counter()-start,
        "source_sha256":{name:hashlib.sha256((ROOT/name).read_bytes()).hexdigest()
           for name in ["supplemental_diagnostics.py","AMENDMENT_01_DIAGNOSTICS.md","joint_model_v2.py"]}}
    save(ROOT/"SUPPLEMENTAL_DIAGNOSTICS.json",result)
    print(json.dumps(clean({k:v for k,v in result.items() if k!="V1_sparse_case"}),indent=2))
    print(json.dumps(clean({"sparse_predictions":predictions,"reference":reference}),indent=2))


if __name__=="__main__":run()
