"""Independent portable check: no fitting, no schedule, no campaign import.

The caller must allocate a worker before numerical imports. When executed as a
standalone file this script assumes that allocation and fixes BLAS to one.
"""
import os
for key in ('OMP_NUM_THREADS','OPENBLAS_NUM_THREADS','MKL_NUM_THREADS','NUMEXPR_NUM_THREADS'):
    os.environ[key]='1'
import json
from pathlib import Path

def run(root=None):
    import numpy as np
    from scipy.special import logsumexp,ndtr
    from handoff_api import JointLocalLearner
    from joint_model import predict
    root=Path(root) if root is not None else Path(__file__).resolve().parent
    fixture=json.loads((root/'results/finishing/ASK_TELL_FIXTURE.json').read_text())
    state=fixture['snapshot'];a=JointLocalLearner.restore(state);b=JointLocalLearner.restore(a.snapshot())
    pa=a._posterior();assert a.ask()==b.ask()
    x=a.x;dd=[r['index'] for r in a.records];y=np.array([r['monitor'] for r in a.records]);theta=np.array(a.theta)
    # Independent full covariance for every component, no Woodbury reuse.
    r=np.sqrt(3*np.sum(((x[:,None]-x[None])/np.exp(theta[:4]))**2,axis=2))
    kernel=np.exp(2*theta[4])*(1+r)*np.exp(-r);noise=np.exp(2*theta[-1]);means=[];covs=[];ells=[]
    for basis in [np.zeros(len(x)),*a.gates]:
        kk=kernel+.36*np.outer(basis,basis);c=kk[np.ix_(dd,dd)]+(noise+1e-10)*np.eye(len(dd));cross=kk[:,dd]
        means.append(cross@np.linalg.solve(c,y));covs.append(kk-cross@np.linalg.solve(c,cross.T))
        sign,ld=np.linalg.slogdet(c);assert sign>0
        ells.append(-.5*(y@np.linalg.solve(c,y)+ld+len(y)*np.log(2*np.pi)))
    prior=np.r_[.5,np.full(len(a.gates),.5/len(a.gates))];loge=logsumexp(np.log(prior)+ells)
    weights=np.exp(np.log(prior)+ells-loge);mm=np.array(means);cc=np.array(covs);mean=weights@mm
    total=np.einsum('j,jik->ik',weights,cc)+np.einsum('j,ji,jk->ik',weights,mm-mean,mm-mean)
    prob=weights@ndtr(mm/np.sqrt(np.maximum(np.diagonal(cc,axis1=1,axis2=2),1e-12)))
    full=predict(theta,x,dd,y,a.gates,full_cov=True)
    err=max(float(np.max(abs(mean-full['mean']))),float(np.max(abs(total-full['covariance']))),
            float(np.max(abs(weights-full['weights']))),float(np.max(abs(prob-full['probability']))),abs(float(loge)-full['log_evidence']))
    assert err<1e-8
    zero=predict(theta,x,dd,y,a.gates,tau2=0,full_cov=True);null=predict(theta,x,dd,y,None,full_cov=True)
    ze=max(float(np.max(abs(zero[k]-null[k]))) for k in ('mean','covariance','probability'))
    assert ze<1e-8 and np.array_equal(pa['probability'],b._posterior()['probability'])
    return {'status':'PASS','dense_error':err,'zero_limit_error':ze,'restored_ask_identical':True,
            'no_fits':True,'component_factorizations':len(a.gates)+1,'scope':'Portable conditional numerical check, not performance'}

if __name__=='__main__':print(json.dumps(run(),indent=2))
