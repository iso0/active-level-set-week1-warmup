"""Independent root-partitioned dense integral for the extra one-step control."""
import argparse
import json
import math
import os
from coordination import ROOT, Slot
from ledger import Meter, add_units, claim, finish, atomic_json
import psutil


def run():
    import numpy as np
    from scipy.integrate import quad
    from scipy.optimize import brentq
    from scipy.special import ndtr
    import posterior
    from mixture_acquisition import current_risk, integrated_scores, truncate
    rng=np.random.default_rng(620202)
    a=rng.normal(size=(2,6,6))
    c=a@a.transpose(0,2,1)/20+np.eye(6)[None]*.06
    m=rng.normal(0,.35,(2,6))
    weights=np.array([.55,.45])
    noise=np.array([[.01,.03,.02],[.08,.02,.05]])
    s={"ref_mean":m[:,:3],"ref_variance":np.diagonal(c,axis1=1,axis2=2)[:,:3],
       "candidate_mean":m[:,3:],"candidate_variance":np.diagonal(c,axis1=1,axis2=2)[:,3:],
       "cross":c[:,:3,3:],"noise":noise,"weights":weights}
    dense, bounds, root_counts=[],[],[]
    for i in range(3):
        v=c[:,i+3,i+3]+noise[:,i]
        lo=float(min(m[:,i+3]-10*np.sqrt(v))); hi=float(max(m[:,i+3]+10*np.sqrt(v)))
        reference_losses, errors, counts=[],[],[]
        for r in range(3):
            vr=c[:,r,r]-c[:,r,i+3]**2/v
            def joint(y):
                density=weights*np.exp(-.5*(y-m[:,i+3])**2/v)/np.sqrt(2*np.pi*v)
                positive=ndtr((m[:,r]+c[:,r,i+3]*(y-m[:,i+3])/v)/np.sqrt(vr))
                return float(density@positive), float(density@(1-positive))
            grid=np.linspace(lo,hi,501)
            signed=[joint(y)[0]-joint(y)[1] for y in grid]
            roots=[brentq(lambda y: joint(y)[0]-joint(y)[1],grid[k],grid[k+1],xtol=1e-13)
                   for k in range(len(grid)-1) if signed[k]*signed[k+1]<0]
            val,err=quad(lambda y: min(joint(y)),lo,hi,points=roots,epsabs=1e-10,epsrel=1e-10,limit=200)
            reference_losses.append(val); errors.append(err); counts.append(len(roots))
        dense.append(current_risk(s)-float(np.mean(reference_losses)))
        bounds.append(max(errors)); root_counts.append(counts)
    orders={}
    for order in (17,33,65,129):
        scores, diag=integrated_scores(s,order)
        orders[str(order)]={"scores":scores.tolist(),"diagnostics":diag,
                           "max_abs_error":float(np.max(abs(scores-dense)))}
    split,_=integrated_scores(s,65,component_quadrature=True)
    single={key:value[:1] for key,value in s.items()}; single["weights"]=np.ones(1)
    analytic,_=integrated_scores(single,17)
    identical={key:np.repeat(value,2,axis=0) for key,value in single.items()}
    identical["weights"]=np.array([.3,.7])
    identical_scores,_=integrated_scores(identical,129)
    assert max(bounds)<1e-8
    assert orders["129"]["max_abs_error"]<.002
    assert np.max(abs(analytic-identical_scores))<.002
    # Exact mass-pruning accounting, independent of the scientific score.
    prune={key:np.concatenate([value[:1],value[1:2]],axis=0) for key,value in s.items()}
    prune["weights"]=np.array([1-1e-10,1e-10])
    kept,mass=truncate(prune)
    assert len(kept["weights"])==1 and abs(mass-1e-10)<1e-20
    return {"status":"PASS_IMPLEMENTATION_WITH_BOUNDED_INTEGRATION",
       "dense_scores":dense,"dense_estimated_errors":bounds,"root_counts":root_counts,
       "importance_GH":orders,"stratified_GH65_scores":split.tolist(),
       "analytic_single_component_vs_identical_mixture_max_error":float(np.max(abs(analytic-identical_scores))),
       "truncation_mass":mass,"bounded_loss_score_error_bound":2*mass,
       "interpretation":"A working numerical control, not proof of all-state integration accuracy or scientific gain."}


if __name__=="__main__":
    p=argparse.ArgumentParser();p.add_argument("--threads",type=int,choices=[1],required=True);p.parse_args()
    unit={"id":"reference_mixture_control_v1","kind":"reference"}
    add_units([unit],"REFERENCE")
    if not (ROOT/"results/MIXTURE_CONTROL_CHECKS.json").exists():
        with Slot():
            selected=claim(unit["id"],os.getpid(),psutil.Process().create_time())
            if selected:
                attempt,_=selected
                import posterior
                posterior.METER=Meter(attempt,reference=True)
                try:
                    result=run(); result["actual_budget"]=posterior.METER.actual
                    atomic_json(ROOT/"results/MIXTURE_CONTROL_CHECKS.json",result)
                    finish(unit["id"],attempt,"COMPLETE","results/MIXTURE_CONTROL_CHECKS.json")
                    print(json.dumps(result,indent=2))
                except Exception as exc:
                    finish(unit["id"],attempt,"FAILED",note=repr(exc));raise
