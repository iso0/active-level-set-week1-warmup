"""Independent dense calculations, unrelated toy inputs; loaded inside Slot."""
import numpy as np
from scipy.special import logsumexp,ndtr
from scipy.stats import multivariate_normal,norm
from joint_model import predict,objective,make_gates
from legacy_model import objective as null_objective
from control import ROOT,atomic,now

def dense(theta,x,paid,y,gates,tau2=.36):
    # Independent direct distance/kernel, solve and slogdet; no Woodbury helper.
    d=x.shape[1];ell=np.exp(theta[:d]);amp2,noise2=np.exp(2*theta[d:])
    distance=np.sqrt(np.sum(((x[:,None]-x[None,:])/ell)**2,axis=2))
    r=np.sqrt(3)*distance;k=amp2*(1+r)*np.exp(-r)
    priors=np.r_[.5,np.full(len(gates),.5/len(gates))]
    ms=[];cs=[];ls=[]
    for a in [np.zeros(len(x)),*gates]:
        kk=k+tau2*np.outer(a,a);c=kk[np.ix_(paid,paid)]+(noise2+1e-10)*np.eye(len(paid))
        cross=kk[:,paid];inv=np.linalg.inv(c)
        ms.append(cross@inv@y);cs.append(kk-cross@inv@cross.T)
        sign,ld=np.linalg.slogdet(c);assert sign==1
        ls.append(-.5*(y@inv@y+ld+len(y)*np.log(2*np.pi)))
    ls=np.array(ls);ms=np.array(ms);cs=np.array(cs)
    loge=logsumexp(np.log(priors)+ls);weights=np.exp(np.log(priors)+ls-loge)
    mean=weights@ms;diff=ms-mean
    cov=np.einsum('j,jik->ik',weights,cs)+np.einsum('j,ji,jk->ik',weights,diff,diff)
    pp=weights@ndtr(ms/np.sqrt(np.maximum(np.diagonal(cs,axis1=1,axis2=2),1e-12)))
    return dict(mean=mean,covariance=cov,probability=pp,weights=weights,log_evidence=float(loge))

def run_unit(u,q,slot):
    q.reserve(u['id'],'reference_solves',500,5000)
    rng=np.random.default_rng(726263);rows=[]
    for n in [3,8,16]:
        slot.check();x=rng.uniform(size=(24,4));paid=np.arange(n);y=rng.normal(size=n)
        gates,trace,_,_=make_gates(x[:6],x[6:]);gates=gates[:4]
        theta=np.log([.2,.45,.8,1.2,.7,.15])
        for label,a in [('local',gates),('trace',trace[:4])]:
            p=predict(theta,x,paid,y,a,full_cov=True);ref=dense(theta,x,paid,y,a)
            err=max(float(np.max(abs(p[k]-ref[k]))) for k in ['mean','covariance','probability','weights','log_evidence'])
            assert err<1e-8,(label,n,err)
            loss,grad=objective(theta,x[paid],y,a[:,paid]);fd=[]
            for k in range(len(theta)):
                delta=np.zeros(len(theta));delta[k]=1e-5
                plus=dense(theta+delta,x,paid,y,a)['log_evidence'];minus=dense(theta-delta,x,paid,y,a)['log_evidence']
                fd.append(-(plus-minus)/2e-5)
            graderr=float(np.max(abs(grad-np.array(fd))/(1+abs(np.array(fd)))))
            assert graderr<2e-5,(n,grad,fd)
            zero=predict(theta,x,paid,y,a,tau2=0,full_cov=True)
            null=predict(theta,x,paid,y,None,full_cov=True)
            zeroerr=max(float(np.max(abs(zero[k]-null[k]))) for k in ['mean','covariance','probability','log_evidence'])
            zloss,zgrad=objective(theta,x[paid],y,a[:,paid],tau2=0);nloss,ngrad=null_objective(theta,x[paid],y)
            zeroerr=max(zeroerr,abs(zloss-nloss),float(np.max(abs(zgrad-ngrad))))
            assert zeroerr<1e-8
            # Independent sequential Gaussian update + likelihood component weights.
            query=n;z=.37;noise2=np.exp(2*theta[-1])+1e-10
            means=[];covs=[];logw=[]
            for j in range(len(p['weights'])):
                mu=p['component_means'][j];cov=p['component_covariances'][j]
                vv=cov[query,query]+noise2;cross=cov[:,query]
                means.append(mu+cross*(z-mu[query])/vv)
                covs.append(cov-np.outer(cross,cross)/vv)
                logw.append(np.log(p['weights'][j])+norm.logpdf(z,mu[query],np.sqrt(vv)))
            ww=np.exp(logw-logsumexp(logw));means=np.array(means);covs=np.array(covs)
            mm=ww@means;diff=means-mm;cc=np.einsum('j,jik->ik',ww,covs)+np.einsum('j,ji,jk->ik',ww,diff,diff)
            direct=predict(theta,x,np.r_[paid,query],np.r_[y,z],a,full_cov=True)
            updateerr=max(float(np.max(abs(mm-direct['mean']))),float(np.max(abs(cc-direct['covariance']))),float(np.max(abs(ww-direct['weights']))))
            assert updateerr<1e-8
            rows.append({'n':n,'basis':label,'dense_error':err,'gradient_scaled_error':graderr,'zero_limit_error':zeroerr,'update_error':updateerr})
    result={'status':'PASS','utc':now().isoformat(),'rows':rows,'reference_solves_reserved':500,
            'scope':'Independent dense/inverse/logdet and finite differences; conditional on theta, not calibration or full Bayes.'}
    atomic(ROOT/'evidence/NUMERICAL_REFERENCES_V1.json',result);return result
