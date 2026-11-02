"""Independent dense algebra checks; never chooses settings by scientific score."""
import numpy as np
from scipy.special import ndtr
from scipy.stats import multivariate_normal
from control import ROOT,atomic,now
from research_v1.model import condition,combine,matern,compact_distance,objective,ModelFamily

def run_reference(u,q,slot):
    rng=np.random.default_rng(716290);q.reserve(u['id'],'reference_solves',100,2000)
    x=rng.uniform(size=(15,4));train=x[:7];test=x[7:];y=rng.normal(size=7);noise2=.03
    theta=np.log([.3,.7,1.2,.4,.9,.2]);eps=1e-5
    loss,grad=objective(theta,train,y)
    fd=np.array([(objective(theta+np.eye(6)[j]*eps,train,y)[0]-objective(theta-np.eye(6)[j]*eps,train,y)[0])/(2*eps) for j in range(6)])
    grad_error=float(np.max(np.abs(grad-fd)/(1+np.abs(fd))))
    assert grad_error<1e-4
    distance=np.linalg.norm(x[:,None]-x[None,:],axis=2);w=compact_distance(distance,.9)
    a=np.exp(-np.sum((x-.4)**2,axis=1)/(2*.3**2));gate=.36*a[:,None]*a[None,:]*w
    k=.9**2*matern(x,x,np.exp(theta[:4]))+gate
    ans=condition(k[:7,:7],k[:7,7:],np.diag(k)[7:],noise2,y)
    c=k[:7,:7]+(noise2+1e-10)*np.eye(7);dense_inverse=np.linalg.inv(c)
    mu=k[7:,:7]@dense_inverse@y;cov=k[7:,7:]-k[7:,:7]@dense_inverse@k[:7,7:]
    dense_error=max(float(np.max(np.abs(mu-ans['mean']))),float(np.max(np.abs(np.diag(cov)-ans['variance']))))
    evidence_error=abs(float(multivariate_normal.logpdf(y,mean=np.zeros(7),cov=c))-ans['log_evidence'])
    assert dense_error<1e-8 and evidence_error<1e-8
    # Independent block conditioning versus a direct augmented dense solve.
    z=.51;s2=cov[0,0]+noise2+1e-10
    updated_mean=mu[1:]+cov[1:,0]/s2*(z-mu[0]);updated_cov=cov[1:,1:]-np.outer(cov[1:,0],cov[0,1:])/s2
    cc=k[:8,:8]+(noise2+1e-10)*np.eye(8);kr=k[8:,:8]
    direct_mean=kr@np.linalg.solve(cc,np.r_[y,z]);direct_cov=k[8:,8:]-kr@np.linalg.solve(cc,k[:8,8:])
    update_error=max(float(np.max(np.abs(updated_mean-direct_mean))),float(np.max(np.abs(updated_cov-direct_cov))))
    assert update_error<1e-8
    eig=float(np.linalg.eigvalsh(gate).min());assert eig>=-1e-10
    trace_error=abs(float(np.diag(gate).mean()-.36*np.mean(a*a)));assert trace_error<1e-12
    zero=condition(k[:7,:7]-gate[:7,:7],k[:7,7:]-gate[:7,7:],np.diag(k)[7:]-np.diag(gate)[7:],noise2,y)
    mix=combine([ans,zero],np.array([.5,.5]));weights=np.exp(np.array([ans['log_evidence'],zero['log_evidence']])-max(ans['log_evidence'],zero['log_evidence']));weights/=weights.sum()
    p=weights[0]*ndtr(ans['mean']/np.sqrt(ans['variance']))+weights[1]*ndtr(zero['mean']/np.sqrt(zero['variance']))
    mixture_error=float(np.max(np.abs(p-mix['probability'])));assert mixture_error<1e-12
    # The unknown location model is a likelihood mixture, with the full prior
    # location penalty; its exact finite-mixture expectation is not log-E[BF].
    rows=[]
    for n in (1,8,24):
        for amplitude in (0.,1.,3.):
            s2=.25;t2=1.;r=t2/s2;e=np.zeros(n);e[0]=amplitude
            formula=-n/2*np.log1p(r)+r/(2*(1+r))*float(e@e)/s2
            exact=multivariate_normal.logpdf(e,cov=(s2+t2)*np.eye(n))-multivariate_normal.logpdf(e,cov=s2*np.eye(n))
            known=-.5*np.log1p(r)+r/(2*(1+r))*amplitude**2/s2
            location_bf=np.exp(-.5*np.log1p(r)+r/(2*(1+r))*e**2/s2)
            rows.append({'n':n,'amplitude':amplitude,'global_log_bf':float(exact),'known_location_log_bf':float(known),
                         'unknown_location_log_bf':float(np.log(location_bf.mean())),
                         'expected_global_log_bf':float(-n/2*np.log1p(r)+r/(2*(1+r))*(n+amplitude**2/s2)),
                         'formula_error':float(abs(formula-exact))})
    assert max(r['formula_error'] for r in rows)<1e-8
    # Actual 32-center factory uses only public inputs and matches every trace.
    model=ModelFamily(rng.uniform(size=(40,4)),rng.uniform(size=(70,4)))
    actual_trace_error=max(abs(float(np.mean(.36*a[40:]**2))-.36*m) for a,m in zip(model.gates,model.matches))
    assert actual_trace_error<1e-12
    result={'status':'PASS','utc':now().isoformat(),'kind':'INDEPENDENT_NUMERICAL_REFERENCE',
            'gradient_relative_error':grad_error,'dense_posterior_error':dense_error,'evidence_error':evidence_error,
            'update_error':update_error,'minimum_gated_eigenvalue':eig,'trace_error':trace_error,
            'actual_factory_trace_error':actual_trace_error,'mixture_probability_error':mixture_error,
            'analytical_examples':rows,'reference_solves_reserved':100,
            'scope':'Exact finite Gaussian checks, not validation of empirical-Bayes calibration or scientific performance.'}
    atomic(ROOT/'evidence/MODEL_NUMERICAL_CHECKS_V1.json',result)
    return result
