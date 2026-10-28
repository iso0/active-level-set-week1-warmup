"""Conditional GP mixtures. Only public inputs and paid responses enter here."""
import hashlib
import math
import time
import numpy as np
from scipy.linalg import cho_factor, cho_solve, solve_triangular
from scipy.optimize import minimize
from scipy.spatial.distance import cdist
from scipy.special import logsumexp, ndtr

ARMS=('strong','compact','gated','trace_match')
RADII=(.45,.9)

def matern(x,z,ell):
    a=np.sqrt(3*np.maximum(cdist(x/ell,z/ell,'sqeuclidean'),0))
    return (1+a)*np.exp(-a)

def compact_distance(distance,radius):
    t=distance/radius
    return np.maximum(1-t,0)**5*(5*t+1)

def objective(theta,x,y,meter=None):
    if meter:meter('optimizer_evaluations')
    d=x.shape[1];ell=np.exp(theta[:d]);amp2,noise2=np.exp(2*theta[d:])
    q=(x[:,None]-x[None,:])**2/ell**2
    a=np.sqrt(3*np.maximum(q.sum(2),0));e=np.exp(-a)
    k=amp2*(1+a)*e;c=k+(noise2+1e-10)*np.eye(len(x))
    fac=cho_factor(c,lower=True,check_finite=False);alpha=cho_solve(fac,y,check_finite=False)
    loss=.5*y@alpha+np.log(np.diag(fac[0])).sum()+len(x)*.5*np.log(2*np.pi)
    w=cho_solve(fac,np.eye(len(x)),check_finite=False)-np.outer(alpha,alpha)
    grad=np.r_[.5*np.einsum('ij,ijd->d',w,3*amp2*e[:,:,None]*q),np.sum(w*k),noise2*np.trace(w)]
    return float(loss),grad

def learn_theta(x,y,previous=None,meter=None):
    d=x.shape[1];initial=[np.full(d,v) for v in (.12,.45,1.2)]
    for axis in range(d):
        ell=np.full(d,1.2);ell[axis]=.08;initial.append(ell)
    starts=[np.log(np.r_[ell,1.,noise]) for ell in initial for noise in (.06,.25)]
    if previous is not None:starts.insert(0,np.asarray(previous))
    bounds=[(np.log(.015),np.log(5.))]*d+[(np.log(.03),np.log(3.)),(np.log(.015),np.log(.6))]
    rr=[minimize(objective,t,args=(x,y,meter),jac=True,method='L-BFGS-B',bounds=bounds,
                 options={'maxiter':80,'ftol':1e-9,'gtol':1e-5,'maxls':20}) for t in starts]
    finite=[r for r in rr if np.isfinite(r.fun)]
    if not finite:raise ArithmeticError('No finite optimizer result')
    best=min(finite,key=lambda r:r.fun)
    return best.x,{'chosen_success':bool(best.success),'successes':sum(bool(r.success) for r in rr),
                  'starts':len(rr),'nll':float(best.fun),'gradient':float(np.abs(best.jac).max()),
                  'all_nll':[float(r.fun) for r in rr],'all_messages':[str(r.message) for r in rr]}

def condition(ktt,ktx,diagonal,noise2,y,meter=None):
    if meter:meter('component_solves')
    fac=cho_factor(ktt+(noise2+1e-10)*np.eye(len(y)),lower=True,check_finite=False)
    alpha=cho_solve(fac,y,check_finite=False)
    v=solve_triangular(fac[0],ktx,lower=True,check_finite=False)
    var=diagonal-np.sum(v*v,axis=0)
    if var.min() < -1e-8:raise ArithmeticError('Invalid latent variance')
    ld=float(2*np.log(np.diag(fac[0])).sum());quad=float(y@alpha)
    return {'mean':ktx.T@alpha,'variance':np.maximum(var,1e-12),
            'log_evidence':-.5*(ld+quad+len(y)*np.log(2*np.pi)),
            'logdet':ld,'quadratic':quad}

def combine(components,prior):
    logw=np.log(prior)+np.array([c['log_evidence'] for c in components])
    w=np.exp(logw-logsumexp(logw));mm=np.stack([c['mean'] for c in components]);vv=np.stack([c['variance'] for c in components])
    mean=w@mm;within=w@vv;between=w@(mm*mm)-mean*mean
    return {'mean':mean,'variance':np.maximum(within+between,1e-12),'within':within,
            'between':np.maximum(between,0),'probability':w@ndtr(mm/np.sqrt(vv)),
            'weights':w,'log_evidence':float(logsumexp(logw))}

class ModelFamily:
    def __init__(self,x_candidates,x_reference,center_seed=91612,meter=None):
        self.x=np.vstack([x_candidates,x_reference]);self.nc=len(x_candidates);self.meter=meter
        rng=np.random.default_rng(center_seed)
        self.centers=rng.choice(self.nc,size=min(32,self.nc),replace=False)
        distance=np.sqrt(cdist(self.x,self.x,'sqeuclidean'))
        self.w=[compact_distance(distance,r) for r in RADII]
        self.gates=[np.exp(-np.sum((self.x-self.x[j])**2,axis=1)/(2*(r/2)**2))
                    for r in RADII for j in self.centers]
        self.matches=[float(np.mean(a[self.nc:]**2)) for a in self.gates]
        self.theta=None;self.theta_budget=None;self.optimizer=[]

    def restore(self,state):
        self.theta=np.array(state['theta']) if state.get('theta') else None
        self.theta_budget=state.get('theta_budget');self.optimizer=state.get('optimizer',[])

    def state(self):
        return {'theta':None if self.theta is None else self.theta.tolist(),
                'theta_budget':self.theta_budget,'optimizer':self.optimizer}

    def fit(self,paid,y,all_models=True):
        paid=np.asarray(paid,int);y=np.asarray(y,float);assert len(set(paid))==len(paid)
        assert len(paid)==len(y) and np.isfinite(y).all()
        if self.meter:self.meter('model_requests',4 if all_models else 1)
        if self.theta is None or len(paid)-self.theta_budget>=4:
            self.theta,log=learn_theta(self.x[paid],y,self.theta,self.meter)
            self.theta_budget=len(paid);self.optimizer.append({'budget':len(paid),**log})
        d=self.x.shape[1];amp2,noise2=np.exp(2*self.theta[d:]);ell=np.exp(self.theta[:d])
        ktx=amp2*matern(self.x[paid],self.x,ell);ktt=ktx[:,paid];diag=np.full(len(self.x),amp2)
        base=condition(ktt,ktx,diag,noise2,y,self.meter)
        out={'strong':combine([base],np.ones(1))};components={'strong':[base]}
        if all_models:
            compact_cs=[base];gated=[base];matched=[base]
            for ri,r in enumerate(RADII):
                local=.36*self.w[ri][paid]
                compact_cs.append(condition(ktt+local[:,paid],ktx+local,diag+.36,noise2,y,self.meter))
                for j in range(len(self.centers)):
                    ix=ri*len(self.centers)+j;a=self.gates[ix];m=self.matches[ix]
                    lc=local*a[paid,None]*a[None,:]
                    gated.append(condition(ktt+lc[:,paid],ktx+lc,diag+.36*a*a,noise2,y,self.meter))
                    matched.append(condition(ktt+m*local[:,paid],ktx+m*local,diag+.36*m,noise2,y,self.meter))
            for name,cs in [('compact',compact_cs),('gated',gated),('trace_match',matched)]:
                components[name]=cs;out[name]=combine(cs,np.r_[.5,np.full(len(cs)-1,.5/(len(cs)-1))])
        for name,p in out.items():
            cs=components[name]
            p['noise_variance']=float(noise2)
            p['diagnostics']={'null_weight':float(p['weights'][0]),'effective_components':float(1/np.sum(p['weights']**2)),
                'component_log_evidence':[float(c['log_evidence']) for c in cs],
                'component_logdet':[c['logdet'] for c in cs],'component_quadratic':[c['quadratic'] for c in cs],
                'weights':p['weights'].tolist(),'theta':self.theta.tolist(),
                'gate_reference_trace':self.matches if name in ('gated','trace_match') else None}
        return out
