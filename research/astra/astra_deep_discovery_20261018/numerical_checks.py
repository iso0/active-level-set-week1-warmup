"""Independent dense conditioning and adaptive-integration references.

These are numerical validation, not held-out scientific performance results.
"""
import hashlib
import json
import math
import pickle
import time
import numpy as np
from scipy.integrate import quad
from scipy.special import ndtr
from scipy.stats import norm
from model import MixtureGP
from acquisition import gaussian_error_reduction, information_fraction, sur_scores
from policy import Policy, boundary_contradiction
from worlds import World
import ledger
from coordination import HERE, now


def run(slot, unit, attempt):
    tests=[]
    def record(name, error, tol=1e-8, **extra):
        passed=bool(error<=tol)
        tests.append({'name':name,'error':float(error),'tolerance':tol,'pass':passed,**extra})
        ledger.atomic_json(HERE/'results'/'NUMERICAL_CHECKS.json',{'status':'RUNNING' if passed else 'FAILED','checks':tests})
        if not passed:
            raise AssertionError(name+': '+str(error)+' > '+str(tol))
    def fit(kind,x,y,ids,channels=1):
        slot.check()
        model=MixtureGP(kind,channels)
        ledger.reserve('reference',len(model.components),unit,attempt)
        return model.fit(x,y,ids)

    # Independent integral over future standardized observation; no Owen-T call.
    errors=[]
    for a in (0.,.2,1.,3.,-1.):
        for rho in (0.,.01,.2,.7,.99,1.):
            if rho==0: exact=0.
            elif rho==1: exact=float(ndtr(-abs(a)))
            else:
                cut=-a/rho
                fun=lambda z: norm.pdf(z)*ndtr(-abs(a+rho*z)/math.sqrt(1-rho*rho))
                # Splitting an infinite interval at z=-100 can miss all Gaussian
                # mass. Bound at +/-12 (tail <4e-33), split at 0 and the kink.
                points=sorted(set([-12.,0.,12.]+([cut] if -12<cut<12 else [])))
                after=sum(quad(fun,lo,hi,epsabs=2e-12)[0] for lo,hi in zip(points[:-1],points[1:]))
                exact=float(ndtr(-abs(a))-after)
            errors.append(abs(exact-float(gaussian_error_reduction(a,rho*rho))))
    record('Gaussian level-set risk reduction vs independent adaptive integration',max(errors),1e-8,cases=len(errors))
    r=np.array([0,.1,.5,.9,1.])
    record('zero-mean arcsine identity',np.max(np.abs(gaussian_error_reduction(0,r*r)-np.arcsin(r)/np.pi)))

    rng=np.random.default_rng(17731)
    x=rng.uniform(size=(7,4)); q=rng.uniform(size=(9,4)); ref=rng.uniform(size=(11,4))
    y=[[float(v)] for v in np.sin(4*x[:,0])-.4]
    m=fit('simple',x,y,list(range(7)))
    # Independent kernel and dense inverse, not Component.kernel or Cholesky code.
    def kernel(a,b):
        d=np.sqrt(((a[:,None]-b[None,:])**2).sum(-1))*math.sqrt(3)/.45
        return (1+d)*np.exp(-d)
    k=kernel(x,x)+np.eye(len(x))*(.06**2+1e-10)
    inv=np.linalg.inv(k)
    mean=kernel(q,x)@inv@np.array(y)[:,0]
    variance=1-np.einsum('ij,ji->i',kernel(q,x)@inv,kernel(x,q))
    pm,pv,_=m.predict(q)
    record('GP mean dense independent reference',np.max(abs(pm-mean)))
    record('GP latent variance dense independent reference',np.max(abs(pv-variance)))
    snap=m.snapshot(q,ref)
    cc=kernel(ref,q)-kernel(ref,x)@inv@kernel(x,q)
    record('GP cross-covariance dense independent reference',np.max(abs(snap.cross_cov[:,:,0]-cc)))

    # WhiteKernel contributes observation variance on sklearn's query diagonal.
    from sklearn.gaussian_process import GaussianProcessRegressor
    from sklearn.gaussian_process.kernels import ConstantKernel,Matern,WhiteKernel
    ledger.reserve('reference',1,unit,attempt)
    gp=GaussianProcessRegressor(kernel=ConstantKernel(1.,'fixed')*Matern(.45,'fixed',nu=1.5)
        +WhiteKernel(.06**2,'fixed'),alpha=1e-10,normalize_y=False,optimizer=None).fit(x,np.array(y)[:,0])
    wm,ws=gp.predict(q,return_std=True)
    record('sklearn WhiteKernel std squared = latent variance + noise',max(np.max(abs(wm-mean)),np.max(abs(ws*ws-variance-.06**2))))
    tests.append({'name':'historical variance interpretation','observation':'adding noise to ws squared double-counts it in this fixture',
                  'historical_query_ranking_effect':'not identified without complete pre-query reconstruction'})

    ym=[[float(v),float(.7*v+.15*np.cos(5*z))] for v,z in zip(np.array(y)[:,0],x[:,1])]
    mm=fit('mixture',x,ym,list(range(7)),2)
    ps=mm.snapshot(q,ref)
    r1=information_fraction(ps,1); rb=information_fraction(ps,3)
    # Direct joint covariance inversion independently at every candidate.
    direct=[]
    for i in range(len(q)):
        v=ps.latent_cov[i]+ps.noise_cov[i]
        direct.append(np.diag(ps.cross_cov[:,i]@np.linalg.solve(v,ps.cross_cov[:,i].T))/ps.ref_variance)
    record('paired information fraction dense reference',np.max(abs(rb-np.array(direct).T)),1e-8)
    record('adding a paid correlated channel cannot reduce Gaussian information',max(0,float(np.max(r1-rb))),1e-8)
    try:
        ps.mean[0,0]=999
        readonly=False
    except ValueError:
        readonly=True
    record('pre-query snapshot immutable',0 if readonly else 1,0)

    # Structural bank: dense covariance/evidence reference with independent
    # coordinate scaling, including explicit nonuniform kernel prior weights.
    st=fit('structure',x,ym,list(range(7)),2)
    direct_means=[]; direct_vars=[]; evidence=[]
    xp=np.repeat(x,2,axis=0); outputs=np.tile([0,1],len(x)); yy=np.asarray(ym).ravel()
    for comp in st.components:
        sp=comp.spec
        def spatial(a,b):
            def mat(length):
                rr=np.sqrt(np.sum(((a[:,None,:]-b[None,:,:])/length)**2,axis=2))*np.sqrt(3.)
                return (1+rr)*np.exp(-rr)
            if sp.short_axis>=0:
                ell=np.full(4,1.2);ell[sp.short_axis]=.08
                return mat(ell)
            return .8*mat(.45)+.2*mat(.12) if sp.multiscale else mat(.45)
        kk=spatial(xp,xp)*np.where(outputs[:,None]==outputs[None,:],1.,sp.correlation)
        kk+=np.eye(len(xp))*(sp.noise_sd**2+1e-10)
        kq=spatial(q,xp)*np.where(outputs[None,:]==0,1.,sp.correlation)
        ki=np.linalg.inv(kk)
        dm=kq@ki@yy;dv=1-np.einsum('ij,ji->i',kq@ki,kq.T)
        direct_means.append(dm);direct_vars.append(dv)
        evidence.append(-.5*yy@ki@yy-.5*np.linalg.slogdet(kk)[1]-.5*len(yy)*np.log(2*np.pi))
    from scipy.special import softmax
    ww=softmax(np.asarray(evidence)+np.log(st.prior_weights))
    direct_means=np.asarray(direct_means);direct_vars=np.asarray(direct_vars)
    dm=ww@direct_means;dv=ww@(direct_vars+direct_means**2)-dm**2
    sm,sv,_=st.predict(q)
    record('structured mixture independent dense posterior/evidence',
           max(np.max(abs(sm-dm)),np.max(abs(sv-dv)),np.max(abs(st.weights-ww))),1e-8)
    record('structured kernel group prior weights',max(abs(st.prior_weights[:12].sum()-.5),abs(st.prior_weights[12:].sum()-.5)),1e-12)

    # Scalar sign reversal can be scientifically relevant below a z=2.5 gate.
    from types import SimpleNamespace
    pp=SimpleNamespace(mean=np.array([[-.4]]),latent_cov=np.array([[[.09]]]),
                       noise_cov=np.array([[[.0036]]]),probability=np.array([ndtr(-.4/.3)]))
    direction,oldp,newp=boundary_contradiction(pp,0,.2)
    inverse=np.linalg.inv(np.array([[.09,.09],[.09,.0936]]))
    conditional_variance=1/inverse[0,0]
    conditional_mean=-.4-inverse[0,1]/inverse[0,0]*(.2+.4)
    refp=ndtr(conditional_mean/np.sqrt(conditional_variance))
    record('boundary gate scalar update independent precision reference',abs(newp-refp),1e-12)
    record('decision contradiction detected below raw z threshold',0 if direction==1 and .6/np.sqrt(.0936)<2.5 else 1,0)
    pp.noise_cov=np.array([[[.5]]])
    record('high observation noise suppresses sign confidence',0 if boundary_contradiction(pp,0,.2)[0]==0 else 1,0)
    # Persist an actual triggered episode and a pending query, not only a path
    # on which no gate acts. Synthetic moment fixture is explicitly not a world.
    from dataclasses import replace
    from policy import PaidObservation
    gatep=replace(ps,paid_count=2,mean=np.tile([-.4,0.],(len(q),1)),
        latent_cov=np.tile(np.diag([.09,.09]),(len(q),1,1)),
        noise_cov=np.tile(np.diag([.0036,.0036]),(len(q),1,1)),
        probability=np.full(len(q),ndtr(-.4/.3)))
    gate_policy=Policy(q,[0,1],'boundary_regional',713019)
    gate_choice=gate_policy.ask(gatep)
    pending_copy=pickle.loads(pickle.dumps(gate_policy,protocol=5))
    ob=PaidObservation(gate_choice['paid_id'],(.2,0.),(True,True))
    gate_event=gate_policy.tell(ob);copy_event=pending_copy.tell(ob)
    after_copy=pickle.loads(pickle.dumps(gate_policy,protocol=5))
    record('pending query and triggered boundary episode survive checkpoint',0 if
        gate_event==copy_event and gate_event['triggered'] and
        after_copy.episode['reference'].digest()==gatep.digest() and
        after_copy.episode['sign']==1 else 1,0)

    # Numerical cloud replacement must leave every realized oracle outcome and
    # startup untouched. These are development/reference fixtures, never TEST.
    wi=World('island_large_seen',17733)
    wq=World('island_large_seen',17733,ref_size=1024,reference_rule='sobol')
    record('Sobol replacement preserves realized world and startup',0 if wi.hash==wq.hash and wi.startup==wq.startup else 1,0)

    # Actual finite-mixture one-dimensional lookahead, with posterior weights
    # updated separately at every possible observed y. Adaptive quadrature handles
    # the decision kink. This is independent of moment-Gaussian SUR.
    mix=fit('mixture',x,y,list(range(7)))
    ms=mix.snapshot(q[:4],ref[:5])
    exact_scores=[]; integration_errors=[]
    for i in range(4):
        cm=[]; cv=[]; rm=[]; rv=[]; cr=[]
        for comp in mix.components:
            mq,vq=comp.project(q[i:i+1],np.zeros(1,int))
            mr,vr=comp.project(ref[:5],np.zeros(5,int))
            cm.append(mq[0]); cv.append(1-float((vq*vq).sum())+comp.spec.noise_sd**2)
            rm.append(mr); rv.append(1-(vr*vr).sum(0))
            cr.append((comp.kernel(ref[:5],np.zeros(5,int),q[i:i+1],np.zeros(1,int))-vr.T@vq)[:,0])
        cm,cv,rm,rv,cr=map(np.array,(cm,cv,rm,rv,cr))
        w=mix.weights
        cur=float(np.minimum(ms.ref_probability,1-ms.ref_probability).mean())
        def expected_density(obs):
            weighted=w*norm.pdf(obs,cm,np.sqrt(cv))
            density=weighted.sum()
            if density < 1e-290: return 0.
            future_m=rm+cr*((obs-cm)/cv)[:,None]
            future_v=np.maximum(rv-cr*cr/cv[:,None],1e-12)
            prob=(weighted/density)@ndtr(future_m/np.sqrt(future_v))
            return float(density*np.minimum(prob,1-prob).mean())
        result,err=quad(expected_density,-np.inf,np.inf,epsabs=1e-8,limit=300)
        exact_scores.append((cur-result)*(1-ms.availability_weights[0]))
        integration_errors.append(err)
    record('exact mixture quadrature convergence diagnostic',max(integration_errors),1e-6)
    approx=sur_scores(ms)
    exact=np.array(exact_scores)
    tests.append({'name':'moment approximation is measured, not called exact','exact_scores':exact.tolist(),
        'approximate_scores':approx.tolist(),'maximum_absolute_error':float(np.max(abs(approx-exact))),
        'exact_best':int(exact.argmax()),'approximate_best':int(approx.argmax()),
        'exact_regret_of_approximate_choice':float(exact.max()-exact[approx.argmax()]),
        'future_component_reweighting':'exact in reference; omitted only in moment acquisition; restored on every actual fit'})

    # Random-cloud integration convergence/rank diagnostic without using held-out
    # scientific metrics to pick a favorable cloud size.
    cloud=rng.uniform(size=(2048,4))
    cloud_rows=[]
    for n in (128,512,2048):
        ss=sur_scores(mix.snapshot(q,cloud[:n]))
        cloud_rows.append({'n':n,'scores':ss.tolist(),'best':int(ss.argmax()),'top_two_gap':float(np.diff(np.sort(ss))[-1])})
    tests.append({'name':'public reference cloud sensitivity; fixed 128 retained','rows':cloud_rows,
                  'Monte_Carlo_ESS':'not applicable: independent uniform integration points; no importance weights or posterior particles'})

    # A selected observation cannot affect its saved pre-query posterior. Test
    # deterministic checkpoint continuation against an uninterrupted path.
    fixture=World('smooth',17732,pool_size=48,eval_size=32,ref_size=24,startup=4)
    def path(interrupt):
        paid=list(fixture.startup); obs=[list(fixture.pay(i).values) for i in paid]
        pol=Policy(fixture.x,paid,'regional',19)
        for step in range(6):
            fm=fit('simple',fixture.x[paid],obs,paid)
            sp=fm.snapshot(fixture.x,fixture.ref_x)
            old_hash=sp.digest()
            choice=pol.ask(sp); out=fixture.pay(choice['paid_id']); ev=pol.tell(out)
            if ev['prequery_hash']!=old_hash or sp.digest()!=old_hash:
                raise AssertionError('pre-query posterior mutated')
            paid.append(out.paid_id); obs.append(list(out.values))
            if interrupt and step==2:
                paid,obs,pol=pickle.loads(pickle.dumps((paid,obs,pol),protocol=5))
        return paid,pol.events
    a=path(False); b=path(True)
    record('identical uninterrupted and checkpoint-resumed query path',0 if a==b else 1,0)
    # Feature generator feasibility, paid quality, and an unseen observation not
    # being exposed to selectors; no performance scores are used here.
    generator=[]
    for family in ('island_small_seen','island_small_unseen','island_large_seen','island_large_unseen'):
        fw=World(family,17733)
        generator.append({'family':family,**fw.evaluator_provenance()})
        record('controlled startup '+family,0 if fw.evaluator_provenance()['startup_contains_island']==family.endswith('_seen') else 1,0)
    tests.append({'name':'generator feasibility fixtures','rows':generator})
    result={'status':'PASS','utc':now().isoformat(),'checks':tests,
            'scope':'Numerical references and software invariants only; controlled campaign scores are separate.'}
    ledger.atomic_json(HERE/'results'/'NUMERICAL_CHECKS.json',result)
    ledger.atomic_json(HERE/'results'/'references'/(unit+'.json'),result)
    return {'path':'results/NUMERICAL_CHECKS.json','status':'PASS','checks':len(tests)}
