"""Covariance-preserving uncertain depth sharing; standalone NumPy/SciPy.

No repository imports. fit receives paid outcomes only. All kernels and link
scales are fixed; the proper discrete rho hyperprior is integrated, not tuned.
"""
from dataclasses import asdict
from functools import lru_cache
import numpy as np
from numpy.polynomial.hermite import hermgauss
from scipy.linalg import cho_factor, cho_solve, solve_triangular
from scipy.optimize import minimize
from scipy.special import ndtr, log_ndtr, logsumexp
from v1_reference import Config, matern32, probit_terms, phi2


def matrix(x):
    x = np.asarray(x, float)
    if x.ndim == 1:
        x = x[:, None]
    if x.ndim != 2 or not np.isfinite(x).all():
        raise ValueError("Expected finite input matrix")
    return x


@lru_cache(None)
def gh(order):
    nodes, weights = hermgauss(order)
    return nodes*np.sqrt(2), weights/np.sqrt(np.pi)


def gaussian_sites(m, K, precision, natural):
    """Posterior from unnormalized Gaussian sites; stable covariance formula."""
    n = len(m)
    sw = np.sqrt(np.maximum(precision, 0))
    B = np.eye(n)+(sw[:, None]*K)*sw[None, :]
    chol = cho_factor(B, lower=True)
    R = sw[:, None]*cho_solve(chol, np.diag(sw))
    S = K-K@R@K
    S = (S+S.T)/2
    mu = m+S@(natural-precision*m)
    alpha = natural-precision*mu
    return mu, S, alpha, (R+R.T)/2, chol


def infer_probit(m, K, y, tau, method="ep"):
    """Fixed-prior inference. EP failure is explicit; caller owns fallback."""
    n = len(y)
    if not n:
        return dict(alpha=np.empty(0), R=np.empty((0,0)),
                    mean=m.copy(), cov=K.copy(), log_evidence=0.,
                    diagnostics={"method":method,"status":"prior","iterations":0})
    signs = 2*np.asarray(y)-1
    if method == "laplace":
        L = np.linalg.cholesky(K)
        def obj(v):
            h = m+L@v
            lp, rat, curv = probit_terms(signs*h/tau)
            W = curv/tau**2
            return (.5*v@v-lp.sum(), v-L.T@(signs*rat/tau),
                    np.eye(n)+(L.T*W)@L)
        fit = minimize(lambda v:obj(v)[0],np.zeros(n),
                       jac=lambda v:obj(v)[1],hess=lambda v:obj(v)[2],
                       method="trust-exact",options={"gtol":1e-9,"maxiter":200})
        value, gradient, Hess = obj(fit.x)
        grad = float(np.max(abs(gradient)))
        if not np.isfinite(value) or grad>2e-6:
            raise RuntimeError(f"Laplace stationarity failure {grad}")
        h = m+L@fit.x
        _, _, curv = probit_terms(signs*h/tau)
        W = curv/tau**2
        sw=np.sqrt(W)
        B=np.eye(n)+(sw[:,None]*K)*sw[None,:]
        ch=cho_factor(B,lower=True)
        R=sw[:,None]*cho_solve(ch,np.diag(sw))
        alpha=solve_triangular(L.T,fit.x,lower=False)
        S=K-K@R@K
        return dict(alpha=alpha,R=(R+R.T)/2,mean=h,cov=(S+S.T)/2,
                    log_evidence=float(-value-np.log(np.diag(ch[0])).sum()),
                    diagnostics={"method":"laplace","status":"accepted",
                      "optimizer_success":bool(fit.success),"gradient_inf":grad,
                      "iterations":int(fit.nit),"message":str(fit.message)})
    if method!="ep":
        raise ValueError(method)
    precision, natural = np.zeros(n), np.zeros(n)
    stable=0
    for iteration in range(1,201):
        mu,S,alpha,R,ch = gaussian_sites(m,K,precision,natural)
        cavity_precision=1/np.diag(S)-precision
        if np.min(cavity_precision)<=0:
            raise FloatingPointError("Nonpositive EP cavity precision")
        vc=1/cavity_precision
        mc=vc*(mu/np.diag(S)-natural)
        den=np.sqrt(tau*tau+vc)
        lp,rat,curv=probit_terms(signs*mc/den)
        mt=mc+signs*vc/den*rat
        vt=vc*(1-vc/(tau*tau+vc)*curv)
        if np.min(vt)<=0:
            raise FloatingPointError("Nonpositive EP tilted variance")
        pnew=np.maximum(1/vt-1/vc,0)
        nnew=mt/vt-mc/vc
        change=max(np.max(abs(pnew-precision)/(1+abs(precision))),
                   np.max(abs(nnew-natural)/(1+abs(natural))))
        precision=.5*precision+.5*pnew
        natural=.5*natural+.5*nnew
        stable=stable+1 if change<1e-8 else 0
        if stable>=3:
            break
    else:
        raise RuntimeError(f"EP did not converge: change={change}")
    mu,S,alpha,R,ch=gaussian_sites(m,K,precision,natural)
    vc=1/(1/np.diag(S)-precision)
    mc=vc*(mu/np.diag(S)-natural)
    logZi=log_ndtr(signs*mc/np.sqrt(tau*tau+vc))
    den=1+precision*vc
    log_site_integral=(-.5*np.log(den)-.5*precision*mc*mc/den+
                       natural*mc/den+.5*vc*natural*natural/den)
    site_constants=logZi-log_site_integral
    q=natural-precision*m
    log_integral=(-np.log(np.diag(ch[0])).sum()+natural@m-
                  .5*(precision*m)@m+.5*q@S@q)
    return dict(alpha=alpha,R=R,mean=mu,cov=S,
                log_evidence=float(log_integral+site_constants.sum()),
                diagnostics={"method":"ep","status":"accepted","iterations":iteration,
                  "relative_site_change":float(change),
                  "min_cavity_variance":float(vc.min()),
                  "min_posterior_variance":float(np.diag(S).min())})


class Component:
    def __init__(self,x_ref,config,rho):
        self.x_ref=matrix(x_ref).copy()
        self.c=config
        self.rho=float(rho)
        if not 0<=rho<=1:
            raise ValueError("rho must lie in [0,1]")
        if config.f_mean!=0:
            raise ValueError("This specification fixes response and independent GP means to zero")
        self.kdbar=float(self.kd_raw(self.x_ref,self.x_ref).mean())

    def kf(self,x,z):
        return matern32(x,z,self.c.f_amplitude,self.c.f_lengthscale)

    def kd_raw(self,x,z):
        return matern32(x,z,self.c.discrepancy_amplitude,self.c.discrepancy_lengthscale)

    def kd(self,x,z):
        return (self.kd_raw(x,z)-self.kd_raw(x,self.x_ref).mean(1)[:,None]
                -self.kd_raw(self.x_ref,z).mean(0)[None,:]+self.kdbar)

    def response(self,x,z=None):
        x=matrix(x); z=x if z is None else matrix(z)
        mean=np.zeros(len(x));cov=self.kf(x,z)
        if len(self.xo):
            k=self.kf(x,self.xo)
            mean=k@self.za
            cov=cov-k@cho_solve(self.zchol,self.kf(self.xo,z))
        return mean,cov

    def prior_h(self,x,z=None):
        z=x if z is None else z
        mf,cf=self.response(x,z)
        r=self.rho
        return r*mf-self.c.threshold_mean, r*r*cf+(1-r*r)*self.kf(x,z)+self.kd(x,z)+self.c.threshold_sd**2

    def fit(self,x,y,z,method):
        self.xp=matrix(x).copy()
        self.yp=np.asarray(y,int).copy()
        good=np.isfinite(z)
        self.xo=self.xp[good]
        zz=np.asarray(z)[good]
        if len(zz):
            K=self.kf(self.xo,self.xo)
            K.flat[::len(K)+1]+=self.c.response_noise_sd**2+self.c.jitter
            self.zchol=cho_factor(K,lower=True)
            self.za=cho_solve(self.zchol,zz)
        m,K=self.prior_h(self.xp)
        K=(K+K.T)/2
        if len(K):
            K.flat[::len(K)+1]+=self.c.jitter
        self.hp_prior=(m,K)
        self.inf=infer_probit(m,K,self.yp,self.c.probit_scale,method)
        return self

    def posterior(self,x,full=False):
        x=matrix(x);n=len(x);r=self.rho;s=np.sqrt(1-r*r);c=self.c
        mf,cf=self.response(x)
        mh,ch=self.prior_h(x)
        _,cfp=self.response(x,self.xp)
        _,chp=self.prior_h(x,self.xp)
        gp=s*self.kf(x,self.xp)
        dp=self.kd(x,self.xp)
        tp=np.full((1,len(self.xp)),-c.threshold_sd**2)
        a,R=self.inf["alpha"],self.inf["R"]
        fmean=mf+cfp*r@a
        hmean=mh+chp@a
        fc=cf-(r*cfp)@R@(r*cfp).T
        hc=ch-chp@R@chp.T
        fh=r*cf-(r*cfp)@R@chp.T
        q={"f_mean":fmean,"h_mean":hmean,"f_cov":(fc+fc.T)/2,
           "h_cov":(hc+hc.T)/2,"f_h_cov":fh,
           "theta_mean":float(c.threshold_mean+(tp@a)[0]),
           "theta_var":float(c.threshold_sd**2-(tp@R@tp.T)[0,0])}
        if np.min(np.diag(hc),initial=0)<-1e-7 or np.min(np.diag(fc),initial=0)<-1e-7:
            raise FloatingPointError("Negative component variance")
        if full:
            # [f(x), g(x), delta(x), theta], with h=rho*f+sqrt(1-rho²)*g+delta-theta.
            D=3*n+1
            mean=np.r_[mf,np.zeros(2*n),c.threshold_mean]
            cov=np.zeros((D,D))
            cov[:n,:n]=cf
            cov[n:2*n,n:2*n]=self.kf(x,x)
            cov[2*n:3*n,2*n:3*n]=self.kd(x,x)
            cov[-1,-1]=c.threshold_sd**2
            cross=np.vstack([r*cfp,gp,dp,tp])
            q["joint_mean"]=mean+cross@a
            q["joint_cov"]=cov-cross@R@cross.T
            H=np.c_[r*np.eye(n),s*np.eye(n),np.eye(n),-np.ones((n,1))]
            q["H"]=H
        return q


class JointModelV2:
    def __init__(self,x_ref,config=None,rhos=(0.,.5,1.),prior_weights=None,
                 inference="ep",allow_fallback=True):
        self.x_ref=matrix(x_ref).copy()
        self.c=config or Config()
        self.rhos=tuple(float(r) for r in rhos)
        self.prior_weights=np.ones(len(rhos))/len(rhos) if prior_weights is None else np.asarray(prior_weights,float)
        if np.any(self.prior_weights<=0) or not np.isclose(self.prior_weights.sum(),1):
            raise ValueError("Proper positive mixture masses required")
        self.inference=inference
        self.allow_fallback=allow_fallback

    def fit(self,x_paid,y_paid,z_paid,use_response=True):
        x=matrix(x_paid);y=np.asarray(y_paid,float);z=np.asarray(z_paid,float).copy()
        if y.shape!=(len(x),) or z.shape!=(len(x),) or not np.isin(y,[0,1]).all() or np.isinf(z).any():
            raise ValueError("Paid arrays invalid; missing response must be NaN")
        self.use_response=bool(use_response)
        if not use_response:
            z[:]=np.nan
        self.solve_count=0;self.failures=[]
        components=[]
        # No continuous data: all rho values induce the same classifier law.
        actual_rhos=self.rhos if np.isfinite(z).any() else self.rhos[:1]
        for method in ([self.inference,"laplace"] if self.inference=="ep" and self.allow_fallback else [self.inference]):
            try:
                components=[]
                for rho in actual_rhos:
                    self.solve_count+=1
                    components.append(Component(self.x_ref,self.c,rho).fit(x,y,z,method))
                break
            except (RuntimeError,FloatingPointError,np.linalg.LinAlgError) as ex:
                self.failures.append({"method":method,"error":str(ex)})
                if method=="laplace" or not self.allow_fallback:
                    raise
        if len(components)!=len(actual_rhos):
            raise RuntimeError("Incomplete mixture")
        if len(actual_rhos)==1 and len(self.rhos)>1:
            # Retain each rho's cross-output prior, despite identical h fit.
            prototype=components[0]
            components=[]
            for rho in self.rhos:
                obj=Component(self.x_ref,self.c,rho)
                obj.xp=prototype.xp;obj.yp=prototype.yp;obj.xo=prototype.xo
                obj.hp_prior=prototype.hp_prior;obj.inf=prototype.inf
                components.append(obj)
        self.components=components
        logZ=np.array([c.inf["log_evidence"] for c in components])
        self.weights=np.exp(np.log(self.prior_weights)+logZ-logsumexp(np.log(self.prior_weights)+logZ))
        self.diagnostics={"n_paid":len(y),"n_negative":int((y==0).sum()),
                          "n_response":int(np.isfinite(z).sum()),
                          "component_solves":self.solve_count,"fallback":bool(self.failures),
                          "failures":self.failures,"rho_values":list(self.rhos),
                          "rho_weights":self.weights.tolist(),"log_evidence":logZ.tolist(),
                          "components":[c.inf["diagnostics"] for c in components]}
        return self

    def component_posteriors(self,x,full=False):
        return [c.posterior(x,full) for c in self.components]

    def predict_proba(self,x):
        out=self.component_posteriors(x)
        return sum(w*ndtr(q["h_mean"]/np.sqrt(self.c.probit_scale**2+np.maximum(np.diag(q["h_cov"]),0)))
                   for w,q in zip(self.weights,out))

    def posterior(self,x):
        qs=self.component_posteriors(x)
        ans={}
        for name in ["h","f"]:
            means=np.array([q[name+"_mean"] for q in qs])
            mu=self.weights@means
            cov=sum(w*(q[name+"_cov"]+np.outer(m-mu,m-mu))
                    for w,q,m in zip(self.weights,qs,means))
            ans[name+"_mean"]=mu;ans[name+"_cov"]=cov
        ans["f_h_cov"]=sum(w*(q["f_h_cov"]+
            np.outer(q["f_mean"]-ans["f_mean"],q["h_mean"]-ans["h_mean"]))
            for w,q in zip(self.weights,qs))
        tm=sum(w*q["theta_mean"] for w,q in zip(self.weights,qs))
        ans["theta_mean"]=tm
        ans["theta_var"]=sum(w*(q["theta_var"]+(q["theta_mean"]-tm)**2) for w,q in zip(self.weights,qs))
        return ans

    def probability_interval(self,x,level=.90):
        qs=self.component_posteriors(x)
        means=np.array([q["h_mean"] for q in qs])
        sd=np.sqrt(np.maximum(np.array([np.diag(q["h_cov"]) for q in qs]),1e-16))
        lo=np.min(means-10*sd,axis=0);hi=np.max(means+10*sd,axis=0)
        bounds=[]
        for target in [(1-level)/2,(1+level)/2]:
            a,b=lo.copy(),hi.copy()
            for _ in range(60):
                mid=(a+b)/2
                cdf=self.weights@ndtr((mid-means)/sd)
                a=np.where(cdf<target,mid,a)
                b=np.where(cdf<target,b,mid)
            bounds.append(ndtr((a+b)/(2*self.c.probit_scale)))
        return np.array(bounds)

    def integrated_probability_variance(self,x):
        qs=self.component_posteriors(x);moment1=0.;moment2=0.
        for w,q in zip(self.weights,qs):
            v=np.maximum(np.diag(q["h_cov"]),0)
            a=q["h_mean"]/np.sqrt(self.c.probit_scale**2+v)
            moment1=moment1+w*ndtr(a)
            moment2=moment2+w*phi2(a,a,v/(self.c.probit_scale**2+v))
        return moment2-moment1**2

    def acquisition(self,x_query,x_integrate=None,gh_order=15,cdf_order=48,
                    observe_response=True,observe_label=True):
        """Exact mixture conditioning of Gaussian component approximations.

        Both future response and label reweight components. Averaging V1
        component utilities would omit learning which coupling is plausible.
        """
        xq=matrix(x_query);xi=self.x_ref if x_integrate is None else matrix(x_integrate)
        ni,nq=len(xi),len(xq)
        qs=self.component_posteriors(np.vstack([xi,xq]))
        tau2=self.c.probit_scale**2
        base=sum(w*ndtr(q["h_mean"][:ni]/np.sqrt(tau2+np.diag(q["h_cov"])[:ni]))
                 for w,q in zip(self.weights,qs))
        observe_response=bool(observe_response and self.use_response)
        nodes,ghweights=gh(gh_order)
        response=np.zeros(nq);label=np.zeros(nq);tails=np.zeros(nq)
        for j in range(nq):
            jj=ni+j;ids=np.r_[np.arange(ni),jj]
            vz=np.array([max(q["f_cov"][jj,jj],0)+self.c.response_noise_sd**2 for q in qs])
            mf=np.array([q["f_mean"][jj] for q in qs])
            if observe_response:
                z=(mf[:,None]+np.sqrt(vz[:,None])*nodes).ravel()
                zw=(self.weights[:,None]*ghweights).ravel()
                logw=np.log(self.weights)[:,None]-.5*(np.log(2*np.pi*vz)[:,None]+(z-mf[:,None])**2/vz[:,None])
                postw=np.exp(logw-logsumexp(logw,axis=0))
            else:
                z=np.array([0.]);zw=np.array([1.])
                postw=self.weights[:,None]
            pis=[];qjs=[];joints=[]
            for k,q in enumerate(qs):
                mm=q["h_mean"][ids]
                C=q["h_cov"][np.ix_(ids,ids)]
                if observe_response:
                    cross=q["f_h_cov"][jj,ids]
                    C=C-np.outer(cross,cross)/vz[k]
                    means=mm[None,:]+(z-mf[k])[:,None]*cross[None,:]/vz[k]
                else:
                    means=mm[None,:]
                if np.min(np.diag(C)) < -1e-7:
                    raise FloatingPointError("Negative response-conditioned variance")
                den=np.sqrt(tau2+np.maximum(np.diag(C),0))
                aa=means/den
                pis.append(ndtr(aa[:,:-1]));qjs.append(ndtr(aa[:,-1]))
                if observe_label:
                    corr=C[:-1,-1]/(den[:-1]*den[-1])
                    joints.append(phi2(aa[:,:-1],aa[:,-1,None],corr[None,:],order=cdf_order))
            pz=np.einsum("kg,kgm->gm",postw,np.asarray(pis))
            qz=np.einsum("kg,kg->g",postw,np.asarray(qjs))
            response[j]=float(zw@np.mean((pz-base)**2,axis=1))
            if observe_label:
                J=np.einsum("kg,kgm->gm",postw,np.asarray(joints))
                valid=(qz>1e-12)&(qz<1-1e-12)
                term=np.zeros(len(z))
                term[valid]=np.mean((J[valid]-pz[valid]*qz[valid,None])**2/
                                   (qz[valid,None]*(1-qz[valid,None])),axis=1)
                label[j]=float(zw@term)
                tails[j]=float(zw[~valid].sum()*1e-12)
        return {"score":response+label,"response_component":response,
                "label_component":label,"omitted_tail_bound":tails,
                "gh_order":gh_order,"cdf_order":cdf_order}
