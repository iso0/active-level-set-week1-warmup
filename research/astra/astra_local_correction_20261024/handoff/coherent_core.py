"""Exact conditional rank-one correction; extracted unchanged from frozen v2."""
import numpy as np
from scipy.linalg import cho_factor,cho_solve,solve_triangular
from .local_core import matern,combine

def rankone_bank(x,paid,y,theta,gates,matches,meter=None):
    """Exact Woodbury update for each component, conditional on theta."""
    paid=np.asarray(paid,int);y=np.asarray(y,float);d=x.shape[1]
    if meter:meter('model_requests',2);meter('component_solves',1+2*len(gates))
    amp2,noise2=np.exp(2*np.asarray(theta)[d:]);ell=np.exp(theta[:d])
    cross=amp2*matern(x[paid],x,ell);c=cross[:,paid]+(noise2+1e-10)*np.eye(len(paid))
    fac=cho_factor(c,lower=True,check_finite=False);alpha=cho_solve(fac,y,check_finite=False)
    v=solve_triangular(fac[0],cross,lower=True,check_finite=False)
    mu0=cross.T@alpha;var0=np.maximum(amp2-np.sum(v*v,axis=0),1e-12)
    ld0=float(2*np.log(np.diag(fac[0])).sum());quad0=float(y@alpha)
    loge0=-.5*(ld0+quad0+len(paid)*np.log(2*np.pi))
    base={'mean':mu0,'variance':var0,'log_evidence':loge0,'logdet':ld0,'quadratic':quad0}
    count=len(gates);a=np.vstack([gates,np.sqrt(matches)[:,None]*np.ones((count,len(x)))])
    ap=a[:,paid];ci_a=cho_solve(fac,ap.T,check_finite=False)
    q=np.sum(ap*ci_a.T,axis=1);b=ap@alpha;vbeta=1/(1/.36+q)
    residual=a-(cross.T@ci_a).T
    means=mu0+residual*(vbeta*b)[:,None];variances=var0+residual**2*vbeta[:,None]
    logdet=ld0+np.log1p(.36*q);quad=quad0-vbeta*b*b
    all_cs=[{'mean':means[j],'variance':variances[j],
             'log_evidence':float(-.5*(logdet[j]+quad[j]+len(paid)*np.log(2*np.pi))),
             'logdet':float(logdet[j]),'quadratic':float(quad[j])} for j in range(2*count)]
    out={}
    for name,offset in [('coherent',0),('coherent_trace',count)]:
        cs=[base,*all_cs[offset:offset+count]];prior=np.r_[.5,np.full(count,.5/count)];p=combine(cs,prior)
        p['diagnostics']={'null_weight':float(p['weights'][0]),'effective_components':float(1/np.sum(p['weights']**2)),
                         'component_log_evidence':[float(z['log_evidence']) for z in cs],
                         'component_logdet':[z['logdet'] for z in cs],'component_quadratic':[z['quadratic'] for z in cs],
                         'weights':p['weights'].tolist(),'theta':list(theta),'gate_reference_trace':list(matches),
                         'beta_posterior_mean':(vbeta*b)[offset:offset+count].tolist(),
                         'beta_posterior_variance':vbeta[offset:offset+count].tolist()}
        out[name]=p
    return out,{'dense_factorizations':1,'rankone_updates':2*count,'base_log_evidence':loge0}
