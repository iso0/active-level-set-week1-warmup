"""Pure paid-data model. Import only after allocating a numerical Slot.

Shared-hyperparameter empirical Bayes; conditional mixture averaging is exact.
No evaluator labels, latent functions or region membership are accepted.
"""
import time
import numpy as np
from scipy.linalg import cho_factor,cho_solve,solve_triangular
from scipy.optimize import minimize
from scipy.special import logsumexp,ndtr
from legacy_model import matern,objective as null_objective

TAU2=.36
def make_gates(x_candidates,x_reference):
    x=np.vstack([x_candidates,x_reference]);nc=len(x_candidates)
    centers=np.random.default_rng(91612).choice(nc,min(32,nc),replace=False)
    gates=np.array([np.exp(-np.sum((x-x[j])**2,axis=1)/(2*(r/2)**2)) for r in (.45,.9) for j in centers])
    matches=np.mean(gates[:,nc:]**2,axis=1)
    return gates,np.sqrt(matches)[:,None]*np.ones_like(gates),centers,matches

def base_terms(theta,x,y):
    d=x.shape[1];ell=np.exp(theta[:d]);amp2,noise2=np.exp(2*theta[d:])
    q=(x[:,None]-x[None,:])**2/ell**2
    r=np.sqrt(3*np.maximum(q.sum(2),0));e=np.exp(-r)
    k=amp2*(1+r)*e;c=k+(noise2+1e-10)*np.eye(len(x))
    fac=cho_factor(c,lower=True,check_finite=False)
    inv=cho_solve(fac,np.eye(len(x)),check_finite=False);alpha=inv@y
    ell0=-.5*y@alpha-np.log(np.diag(fac[0])).sum()-.5*len(x)*np.log(2*np.pi)
    derivatives=np.concatenate([np.moveaxis(3*amp2*e[:,:,None]*q,2,0),
                               (2*k)[None],(2*noise2*np.eye(len(x)))[None]])
    return fac,inv,alpha,float(ell0),derivatives

def mixture_terms(theta,x,y,gates_paid,tau2=TAU2):
    fac,inv,alpha,ell0,derivatives=base_terms(theta,x,y)
    ap=np.asarray(gates_paid);u=inv@ap.T;q=np.sum(ap*u.T,axis=1);b=ap@alpha
    v=tau2/(1+tau2*q)
    ell=np.r_[ell0,ell0-.5*np.log1p(tau2*q)+.5*v*b*b]
    prior=np.r_[.5,np.full(len(ap),.5/len(ap))]
    ll=float(logsumexp(np.log(prior)+ell));weights=np.exp(np.log(prior)+ell-ll)
    alphas=np.vstack([alpha,alpha[None]-(v*b)[:,None]*u.T])
    inv_average=inv-np.einsum('j,ij,kj->ik',weights[1:]*v,u,u)
    w=inv_average-np.einsum('j,ji,jk->ik',weights,alphas,alphas)
    gradient=.5*np.einsum('ij,kij->k',w,derivatives)
    return {'fac':fac,'inverse':inv,'alpha':alpha,'ell0':ell0,'evidence':ell,
            'log_evidence':ll,'weights':weights,'u':u,'q':q,'b':b,'v':v,'gradient':gradient}

def objective(theta,x,y,gates_paid,meter=None,tau2=TAU2):
    if meter:meter('optimizer_evaluations');meter('rankone_updates',len(gates_paid))
    t=mixture_terms(theta,x,y,gates_paid,tau2)
    return -t['log_evidence'],t['gradient']

def structural_starts(d):
    initial=[np.full(d,v) for v in (.12,.45,1.2)]
    for axis in range(d):
        a=np.full(d,1.2);a[axis]=.08;initial.append(a)
    return [np.log(np.r_[ell,1.,noise]) for ell in initial for noise in (.06,.25)]

def fit_theta(x,y,gates_paid,base_theta,previous=None,meter=None,
              null_control=False,cpu_target=None,joint_start=None,seed=726262):
    """Training-only objective, fixed starts, tolerance and bounded CPU control."""
    d=x.shape[1];starts=[np.asarray(base_theta),*structural_starts(d)]
    if previous is not None:starts.insert(0,np.asarray(previous))
    if joint_start is not None:starts.append(np.asarray(joint_start))
    rng=np.random.default_rng(seed)
    bounds=[(np.log(.015),np.log(5.))]*d+[(np.log(.03),np.log(3.)),(np.log(.015),np.log(.6))]
    lo,hi=np.array(bounds).T;logs=[];best=None;start=time.process_time();wall=time.perf_counter()
    fun=(lambda t:null_objective(t,x,y,meter)) if null_control else (lambda t:objective(t,x,y,gates_paid,meter))
    for i in range(128 if null_control else len(starts)):
        if i>=len(starts) and (cpu_target is None or time.process_time()-start>=cpu_target):break
        initial=starts[i] if i<len(starts) else rng.uniform(lo,hi)
        t0=time.process_time()
        result=minimize(fun,initial,jac=True,method='L-BFGS-B',bounds=bounds,
                        options={'maxiter':80,'ftol':1e-9,'gtol':1e-5,'maxls':20})
        logs.append({'start':initial.tolist(),'theta':result.x.tolist(),'nll':float(result.fun),
                     'success':bool(result.success),'message':str(result.message),'nfev':int(result.nfev),
                     'nit':int(result.nit),'gradient_max':float(np.max(abs(result.jac))),
                     'cpu_seconds':time.process_time()-t0})
        if np.isfinite(result.fun) and (best is None or result.fun<best.fun):best=result
    if best is None:raise ArithmeticError('No finite optimizer result')
    cpu=time.process_time()-start
    return best.x,{'objective':'null' if null_control else 'mixture','starts':len(logs),
                  'cpu_seconds':cpu,'wall_seconds':time.perf_counter()-wall,
                  'cpu_target':cpu_target,'cpu_target_covered':cpu_target is None or cpu>=cpu_target,
                  'cap_reached':len(logs)==128,'nll':float(best.fun),'chosen_success':bool(best.success),
                  'theta':best.x.tolist(),'all_starts':logs}

def predict(theta,x,paid,y,gates=None,tau2=TAU2,full_cov=False,meter=None):
    """Full posterior of TOTAL f; observation noise excluded from latent variance."""
    if meter:meter('model_requests')
    paid=np.asarray(paid,int);y=np.asarray(y,float);d=x.shape[1]
    amp2,noise2=np.exp(2*np.asarray(theta)[d:]);ell=np.exp(theta[:d])
    if gates is None:
        fac,inv,alpha,ell0,_=base_terms(theta,x[paid],y)
        t=None;weights=np.ones(1)
    else:
        t=mixture_terms(theta,x[paid],y,gates[:,paid],tau2)
        fac,inv,alpha,ell0=t['fac'],t['inverse'],t['alpha'],t['ell0'];weights=t['weights']
        if meter:meter('rankone_updates',len(gates))
    cross=amp2*matern(x[paid],x,ell);vv=solve_triangular(fac[0],cross,lower=True,check_finite=False)
    mean0=cross.T@alpha;var0=amp2-np.sum(vv*vv,axis=0)
    if var0.min() < -1e-8:raise ArithmeticError('Invalid latent variance')
    var0=np.maximum(var0,1e-12)
    if t is None:means=mean0[None];variances=var0[None]
    else:
        residual=gates-(cross.T@t['u']).T
        means=np.vstack([mean0,mean0[None]+residual*(t['v']*t['b'])[:,None]])
        variances=np.vstack([var0,var0[None]+residual**2*t['v'][:,None]])
    mean=weights@means;within=weights@variances
    between=weights@((means-mean)**2)
    out={'mean':mean,'variance':within+between,'within':within,'between':between,
         'probability':weights@ndtr(means/np.sqrt(variances)),'weights':weights,
         'component_means':means,'component_variances':variances,'noise_variance':float(noise2),
         'log_evidence':ell0 if t is None else t['log_evidence']}
    if full_cov:
        basecov=amp2*matern(x,x,ell)-vv.T@vv
        covs=basecov[None] if t is None else np.concatenate([basecov[None],basecov[None]+np.einsum('j,ji,jk->jik',t['v'],residual,residual)])
        diff=means-mean
        out['covariance']=np.einsum('j,jik->ik',weights,covs)+np.einsum('j,ji,jk->ik',weights,diff,diff)
        out['component_covariances']=covs
    out['diagnostics']={'theta':np.asarray(theta).tolist(),'null_weight':float(weights[0]),
       'weights':weights.tolist(),'log_evidence':out['log_evidence'],'noise_variance':float(noise2),
       'effective_components':float(1/np.sum(weights**2))}
    if t is not None:
        localw=weights[1:]/max(1-weights[0],1e-300)
        out['diagnostics'].update(lambda_information=(tau2*t['q']).tolist(),
            whitened_residual=(t['b']/np.sqrt(np.maximum(t['q'],1e-300))).tolist(),
            beta_mean=(t['v']*t['b']).tolist(),beta_variance=t['v'].tolist(),
            component_log_evidence=t['evidence'].tolist(),
            location_entropy=float(-np.sum(localw*np.log(np.maximum(localw,1e-300)))))
    return out
