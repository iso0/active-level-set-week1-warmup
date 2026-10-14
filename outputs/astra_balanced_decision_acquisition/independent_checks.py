"""Independent exact enumeration and tensor quadrature; no scientific tuning.

The tiny Gaussian fixtures validate computation, not EP accuracy. A separate
one-observation V2 reference quantifies EP error against a non-Gaussian posterior.
"""
import runtime as rt
import itertools
import math
from types import SimpleNamespace
import numpy as np
from scipy.special import ndtr,log_ndtr,logsumexp
from scipy.optimize import linprog
from numpy.polynomial.hermite import hermgauss
from balanced_method import (population_coefficients,batch_coefficients,finite_pool_coefficients,independent_label_law,
                             decision_pass,risk_acquisition_pass,root)
from v1_reference import matern32
from worlds import config


class ReferenceBudget:
    def __init__(self):
        rows=[rt.json.loads(s) for s in (rt.ROOT/'ledger.jsonl').read_text(encoding='utf-8').splitlines()]
        self.groups=[{'name':r['name'],'states':r['states']} for r in rows if r['event']=='REFERENCE']
        self.states=sum(r['states'] for r in self.groups)
        self.production_groups=[{'name':r['name'],'evaluations':r['evaluations']} for r in rows if r['event']=='PRODUCTION_NUMERICAL_CHECK']
        self.production_evaluations=sum(r['evaluations'] for r in self.production_groups)
    def charge(self,name,states):
        if any(g['name']==name for g in self.groups):raise RuntimeError(f'Already charged reference {name}; audit before retry')
        if len(self.groups)+1>30 or self.states+states>12000000:raise RuntimeError('Reference budget exhausted')
        rt.append({'event':'REFERENCE','name':name,'states':int(states)})
        self.groups.append({'name':name,'states':int(states)});self.states+=int(states)
    def production(self,name,evaluations):
        if any(g['name']==name for g in self.production_groups):raise RuntimeError(f'Already charged numerical check {name}')
        if self.production_evaluations+evaluations>10000000:raise RuntimeError('Production validation budget exhausted')
        rt.append({'event':'PRODUCTION_NUMERICAL_CHECK','name':name,'evaluations':int(evaluations)})
        self.production_groups.append({'name':name,'evaluations':int(evaluations)})
        self.production_evaluations+=int(evaluations)


def tensor(order,dim):
    n,w=hermgauss(order);n=n*np.sqrt(2);w=w/np.sqrt(np.pi)
    ids=np.array(list(itertools.product(range(order),repeat=dim)))
    return n[ids],np.prod(w[ids],axis=1)


def explicit_finite_loss(d,y):
    n1=int(sum(y));n0=len(y)-n1
    if min(n1,n0)==0:return .5
    return .5*(sum((1-d[i])*y[i] for i in range(len(y)))/n1+
               sum(d[i]*(1-y[i]) for i in range(len(y)))/n0)


def independent_batch_terms(h,tau,m=96):
    """Independent finite geometric-sum implementation, including p=0 or 1.

    No log-ratio code from production is used; the endpoint coefficients have
    finite limits. This avoids 0/0 at far tensor nodes with underflowed tails.
    """
    eta=ndtr(h/tau);negative=ndtr(-h/tau)
    p=eta.mean(1);q=negative.mean(1)
    gp=np.ones_like(p);gq=np.ones_like(q)
    for _ in range(m-1):
        gp=1+p*gp;gq=1+q*gq
    positive_factor=np.maximum(gq-p**(m-1),0.)
    negative_factor=np.maximum(gp-q**(m-1),0.)
    both=.5*(p*positive_factor+q*negative_factor)
    return eta*positive_factor[:,None],negative*negative_factor[:,None],eta,both


def iid_batch_enumeration(budget):
    m=4;v=np.array([.5,.5]);etas=np.array([[.2,.9],[.7,.3]]);posterior=np.array([.6,.4])
    budget.charge('IID_batch_exact_enumeration',4**m*4*2)
    actions=np.array(list(itertools.product((0,1),repeat=2)));loss=np.zeros(4)
    atoms=list(itertools.product((0,1),(0,1))) # (feature atom, label)
    for sequence in itertools.product(atoms,repeat=m):
        xx=np.array([a[0] for a in sequence]);yy=np.array([a[1] for a in sequence])
        probability=sum(mass*np.prod(v[xx]*np.where(yy,eta[xx],1-eta[xx])) for mass,eta in zip(posterior,etas))
        loss += probability*np.array([explicit_finite_loss(d[xx],yy) for d in actions])
    from scipy.special import ndtri
    A,B,_,_,both=batch_coefficients(ndtri(etas),1.,2,batch_size=m)
    a=posterior@A;b=posterior@B;empty=1-posterior@both
    formula=np.array([.5*empty+.5*v@(a*(1-d)+b*d) for d in actions])
    budget.charge('finite_batch_endpoint_arithmetic',3)
    extremes=np.array([[1000.,1000.],[-1000.,-1000.],[1000.,-1000.]])
    ea,eb,_,_,_=batch_coefficients(extremes,1.,2,batch_size=96)
    ra,rb,_,_=independent_batch_terms(extremes,1.,m=96)
    return {'batch_size':m,'actions':actions,'enumerated_losses':loss,'formula_losses':formula,
            'max_error':float(np.max(abs(loss-formula))),'chosen_action':a>=b,
            'zero_class_probability':float(empty),'bounded_coefficients':bool(max(A.max(),B.max())<=m+1e-12),
            'endpoint_finite':bool(np.isfinite([ea,eb,ra,rb]).all()),
            'endpoint_independent_max_error':float(max(np.max(abs(ea-ra)),np.max(abs(eb-rb))))}


def finite_reference(budget):
    budget.charge('fixed_pool_enumeration_and_paired_channel',64*64*5)
    p=np.array([.1,.65,.75,.85,.9,.95]);y,w=independent_label_law(p)
    actions=np.array(list(itertools.product((0,1),repeat=6)))
    losses=np.array([sum(ww*explicit_finite_loss(d,yy) for yy,ww in zip(y,w)) for d in actions])
    result=finite_pool_coefficients(y,w)
    err=abs(result['risk']-losses.min())
    paid={0:0,4:1};yp,wp=independent_label_law(p,paid);paidresult=finite_pool_coefficients(yp,wp)
    assert all(np.all(yp[:,i]==v) for i,v in paid.items())
    zero=finite_pool_coefficients(np.ones((1,6),int),np.ones(1))
    # Exact paired finite-pool lookahead, four-state auxiliary output D in {0,1}.
    # Its channel depends on the entire label state; it is a numerical fixture.
    pz=.2+.6*(y[:,1]==y[:,2]);j=3
    future=0.;coefffuture=0.;probcheck=0.
    for depth in (0,1):
        for label in (0,1):
            joint=w*np.where(depth,pz,1-pz)*(y[:,j]==label)
            mass=joint.sum()
            if mass==0:continue
            posterior=joint/mass
            lf=[sum(ww*explicit_finite_loss(d,yy) for yy,ww in zip(y,posterior)) for d in actions]
            future+=mass*min(lf);coefffuture+=mass*finite_pool_coefficients(y,posterior)['risk'];probcheck+=mass
    return {'risk_coefficient_vs_all_actions_error':float(err),'expected_BA_conditional_both':float(1-(result['risk']-.5*(1-result['p_both']))/result['p_both']),
            'p_both':result['p_both'],'decision':result['decision'],'paid_decision':paidresult['decision'],
            'paid_labels_fixed':True,'zero_class_risk':zero['risk'],'zero_class_p_both':zero['p_both'],
            'paired_utility_bruteforce':float(losses.min()-future),
            'paired_utility_coefficient':float(result['risk']-coefffuture),
            'paired_error':float(abs(future-coefffuture)),'outcome_mass':float(probcheck)}


def uncertain_prevalence_reference(budget):
    budget.charge('uncertain_prevalence_two_state_exact',2)
    eta=np.array([[.6,.001],[.001,.99]]);v=np.array([.05,.95]);w=np.array([.5,.5])
    pi=eta@v;A=w@(eta/pi[:,None]);B=w@((1-eta)/(1-pi[:,None]))
    exact=A>=B;plug=(w@eta)>=(w@pi)
    def loss(d):return float(.5*v@(A*(1-d)+B*d))
    covariance=np.sum(w[:,None]*(eta-w@eta)*(pi-w@pi)[:,None],axis=0)
    return {'eta_states':eta,'reference_weights':v,'state_weights':w,'pi_states':pi,
            'posterior_pi_mean':float(w@pi),'posterior_probabilities':w@eta,
            'exact_A':A,'exact_B':B,'exact_decision':exact,'mean_pi_decision':plug,
            'exact_risk':loss(exact),'mean_pi_risk':loss(plug),'plug_in_regret':loss(plug)-loss(exact),
            'probability_prevalence_covariance':covariance}


class GaussianFixture:
    def __init__(self):
        self.x_ref=np.array([[-.5],[.5]])
        self.weights=np.array([.65,.35]);self.c=SimpleNamespace(probit_scale=.6,response_noise_sd=.35)
        self.posts=[]
        for mean,scale,coupling in (([-.15,.3],1.,.75),([.2,-.1],.7,-.3)):
            H=np.array([[.25,.12],[.12,.3]])*scale
            F=np.array([[.3,.05],[.05,.28]])
            C=coupling*.15*np.eye(2)
            self.posts.append({'h_mean':np.asarray(mean),'h_cov':H,'f_mean':np.array([.1,-.05]),'f_cov':F,'f_h_cov':C})
    def component_posteriors(self,x):
        # Only the numerical fixture's reference points are requested here.
        if len(x)!=2:raise ValueError('Fixture has exactly two points')
        return self.posts


def quadrature_gaussian_fixture(model,order,zorder):
    """Independent tensor GH; explicit predictive mixture and branch normalization."""
    nodes,ww=tensor(order,2);zn,zw0=tensor(zorder,1);zn=zn[:,0]
    tau=model.c.probit_scale;K=len(model.weights);nr=2
    A=np.zeros(nr);B=A.copy();p=A.copy()
    for mass,post in zip(model.weights,model.posts):
        h=post['h_mean']+nodes@np.linalg.cholesky(post['h_cov']).T
        aa,bb,eta,_=independent_batch_terms(h,tau)
        A+=mass*(ww@aa);B+=mass*(ww@bb);p+=mass*(ww@eta)
    risk=float(.5*np.minimum(A,B).mean());scores=[]
    for j in (0,1):
        future=0.
        for origin in range(K):
            op=model.posts[origin];ov=op['f_cov'][j,j]+model.c.response_noise_sd**2
            for z,weight in zip(op['f_mean'][j]+np.sqrt(ov)*zn,model.weights[origin]*zw0):
                dens=[];branchA=[];branchB=[];branchP=[]
                for mass,post in zip(model.weights,model.posts):
                    variance=post['f_cov'][j,j]+model.c.response_noise_sd**2
                    # Independent block-normal conditioning construction.
                    cov=np.block([[post['h_cov'],post['f_h_cov'][j,:,None]],
                                  [post['f_h_cov'][j,None,:],np.array([[variance]])]])
                    mean=post['h_mean']+cov[:2,2]*(z-post['f_mean'][j])/variance
                    HC=cov[:2,:2]-cov[:2,2,None]@cov[2,None,:2]/variance
                    h=mean+nodes@np.linalg.cholesky(HC).T
                    a,b,eta,_=independent_batch_terms(h,tau)
                    qq=np.stack([ndtr(-h[:,j]/tau),eta[:,j]],axis=1)
                    branchA.append(np.einsum('s,sy,si->yi',ww,qq,a))
                    branchB.append(np.einsum('s,sy,si->yi',ww,qq,b));branchP.append(ww@qq)
                    dens.append(mass*np.exp(-.5*(z-post['f_mean'][j])**2/variance)/np.sqrt(2*np.pi*variance))
                postmass=np.asarray(dens)/sum(dens)
                ar=np.einsum('k,kyi->yi',postmass,branchA);br=np.einsum('k,kyi->yi',postmass,branchB)
                py=postmass@np.asarray(branchP)
                # Normalize each branch before computing its Bayes risk, then
                # weight by its predictive probability (unlike production code).
                future+=weight*sum(py[y]*.5*np.minimum(ar[y]/py[y],br[y]/py[y]).mean() for y in (0,1))
        scores.append(risk-future)
    return {'A':A,'B':B,'p':p,'risk':risk,'scores':np.array(scores)}


def gaussian_checks(budget):
    fixture=GaussianFixture();refs=[]
    for order,zorder in ((20,17),(40,33),(64,49)):
        rt.wait_slot();budget.charge(f'gaussian_tensor_{order}_{zorder}',2*order**2+8*zorder*order**2)
        refs.append(quadrature_gaussian_fixture(fixture,order,zorder))
    budget.production('gaussian_decision_QMC',4*2*2**14)
    q=decision_pass(fixture,fixture.x_ref,np.empty((0,1)),bits=14,seed=8201)
    budget.production('gaussian_acquisition_QMC',4*2*2*(2*33)*2**12)
    a=risk_acquisition_pass(fixture,[0,1],bits=12,order=33,seed=8202)
    truth=refs[-1];conv=float(np.max(abs(refs[-1]['scores']-refs[-2]['scores'])))
    return {'quadrature_levels':refs,'reference_score_convergence':conv,
            'qmc_decision_max_A_error':float(np.max(abs(q['a']-truth['A']))),
            'qmc_risk_error':abs(q['risk']-truth['risk']),'qmc_acquisition':a,
            'max_acquisition_error':float(np.max(abs(a['scores']-truth['scores']))),
            'reference_top':int(np.argmax(truth['scores'])),'qmc_top':int(np.argmax(a['scores'])),
            'posterior_scope':'exact Gaussian-mixture fixture, not exact fitted V2 posterior'}


def one_label_v2_reference(budget):
    X=np.array([[-.4,0,0,0],[.5,.2,0,0]]);c=config();y=np.array([1]);z=np.array([.1])
    fitted=rt.charged_fit('check_one_label_v2',X,X[:1],y,z,validation=True)
    K=matern32(X,X,c.f_amplitude,c.f_lengthscale)
    D=matern32(X,X,c.discrepancy_amplitude,c.discrepancy_lengthscale)
    D=D-D.mean(0)[None,:]-D.mean(1)[:,None]+D.mean()
    H=K+D+c.threshold_sd**2*np.ones((2,2));vz=K[0,0]+c.response_noise_sd**2
    levels=[]
    for order in (48,96,160):
        rt.wait_slot();budget.charge(f'nonGaussian_V2_one_label_{order}',3*order**2);nodes,ww=tensor(order,2)
        arrays=[];masses=[]
        for rho in (0.,.5,1.):
            mu=rho*K[:,0]*z[0]/vz;C=H-rho*rho*np.outer(K[:,0],K[:,0])/vz
            h=mu+nodes@np.linalg.cholesky(C+1e-12*np.eye(2)).T
            eta=ndtr(h/c.probit_scale);weights=ww*eta[:,0]
            aa,bb,eta,_=independent_batch_terms(h,c.probit_scale)
            pi=eta.mean(1)
            arrays.append((weights@aa,weights@bb,weights@eta,weights@pi))
            masses.append(weights.sum())
        mass=sum(masses);A=sum(a[0] for a in arrays)/mass;B=sum(a[1] for a in arrays)/mass
        levels.append({'A':A,'B':B,'p':sum(a[2] for a in arrays)/mass,
                       'pi':sum(a[3] for a in arrays)/mass,'weights':np.asarray(masses)/mass,
                       'risk':float(.5*np.minimum(A,B).mean())})
    # True paired acquisition after the old label: integrate both probit factors
    # against the Gaussian posterior conditioned ONLY on the old response. No EP
    # density enters this reference. Outer response proposal is before old Y;
    # its old-label likelihood is retained in every unnormalized branch moment.
    cf=K-np.outer(K[:,0],K[:,0])/vz;mf=K[:,0]*z[0]/vz
    future_var=cf[1,1]+c.response_noise_sd**2
    analytic_evidence=np.mean([ndtr((rho*K[0,0]*z[0]/vz)/np.sqrt(c.probit_scale**2+H[0,0]-rho*rho*K[0,0]**2/vz)) for rho in (0.,.5,1.)])
    acquisition_refs=[]
    for order,zorder in ((32,17),(64,33),(96,49)):
        rt.wait_slot()
        budget.charge(f'true_V2_paired_{order}_{zorder}',3*order**2*zorder)
        nodes,ww=tensor(order,2);zn,zw=tensor(zorder,1)
        future=0.
        for value,weight in zip(mf[1]+np.sqrt(future_var)*zn[:,0],zw):
            A=np.zeros((2,2));B=A.copy()
            for rho in (0.,.5,1.):
                mu=rho*K[:,0]*z[0]/vz
                C=H-rho*rho*np.outer(K[:,0],K[:,0])/vz
                cross=rho*cf[1]
                mu=mu+cross*(value-mf[1])/future_var
                C=C-np.outer(cross,cross)/future_var
                h=mu+nodes@np.linalg.cholesky(C+1e-12*np.eye(2)).T
                aa,bb,eta,_=independent_batch_terms(h,c.probit_scale)
                negative=ndtr(-h/c.probit_scale)
                old=eta[:,0]
                for future_y,lik in ((0,negative[:,1]),(1,eta[:,1])):
                    A[future_y]+=(ww*old*lik)@aa/3
                    B[future_y]+=(ww*old*lik)@bb/3
            future+=weight*.5*np.minimum(A,B).sum()/2/analytic_evidence
        acquisition_refs.append(float(levels[-1]['risk']-future))
    budget.production('nonGaussian_acquisition_QMC',4*1*3*(3*33)*2**12)
    approximate_acquisition=risk_acquisition_pass(fitted,[1],12,33,8212)
    budget.production('nonGaussian_decision_QMC',4*3*2**14)
    q=decision_pass(fitted,X,np.empty((0,4)),14,8211)
    p=fitted.predict_proba(X);truth=levels[-1]
    return {'reference_levels':levels,'reference_convergence_probability':float(np.max(abs(levels[-1]['p']-levels[-2]['p']))),
            'reference_convergence_risk':abs(levels[-1]['risk']-levels[-2]['risk']),
            'EP_probability_error':float(np.max(abs(p-truth['p']))),'EP_risk_error':abs(q['risk']-truth['risk']),
            'EP_coeff_A_error':float(np.max(abs(q['a']-truth['A']))),
            'EP_probabilities':p,'EP_decision':q['decision'],'exact_decision':truth['A']>=truth['B'],
            'exact_paired_acquisition_levels':acquisition_refs,
            'exact_paired_reference_convergence':abs(acquisition_refs[-1]-acquisition_refs[-2]),
            'EP_paired_acquisition':approximate_acquisition,
            'EP_paired_acquisition_error':abs(float(approximate_acquisition['scores'][0])-acquisition_refs[-1]),
            'note':'Non-Gaussian posterior reference; converged EP and QMC do not remove this approximation error. Only one unpaid candidate here; ranking reference is separately Gaussian.'}


def local_safeguard(budget):
    budget.charge('additional_idea_feature_cell_80_percent_recall',4)
    v=np.array([.8,.2]);eta=np.array([.98,.55]);pi=v@eta
    a=v*eta/pi;b=v*(1-eta)/(1-pi)
    coeff=.5*(b-a) # loss(d)=constant+coeff*d
    solution=linprog(coeff,A_ub=np.array([[0.,-1.]]),b_ub=np.array([-.8]),bounds=[(0,1),(0,1)],method='highs',options={'threads':1})
    if not solution.success:raise RuntimeError(solution.message)
    optimum=(eta>=pi).astype(float)
    def ba(d):return float(.5*(a@d+b@(1-d)))
    return {'target_weights':v,'true_probabilities_ORACLE_TOY':eta,'pi':float(pi),
            'BA_optimal_actions':optimum,'BA_optimal':ba(optimum),'mixed_cell_positive_recall':float(optimum[1]),
            'constrained_randomized_actions':solution.x,'BA_with_80_percent_cell_recall':ba(solution.x),
            'within_mixed_cell_irreducible_error':.45,
            'interpretation':'Known eta already discards the mixed cell under BA. Feature-cell recall can force retention at a BA cost, without identifying which individuals are positive. Hidden morphology is not observable from these toy channels.'}


def checks_leakage(budget):
    X=np.array([[-.8,0,0,0],[-.2,.2,0,0],[.3,0,.2,0],[.8,0,0,.2]])
    model=rt.charged_fit('check_leakage',X,X[[0,2]],[0,1],[-.3,np.nan],validation=True)
    budget.production('leakage_decision_QMC_pair',2*4*3*2**10)
    q1=decision_pass(model,X,np.empty((0,4)),10,8301)
    # No unpaid/test argument exists in either method API. Re-evaluation after
    # corrupting evaluator-only arrays must be byte-equivalent.
    hidden=np.array([1.,0.]);hidden[:]=np.nan
    q2=decision_pass(model,X,np.empty((0,4)),10,8301)
    budget.production('missing_depth_label_only_QMC',4*2*3*2**8)
    a=risk_acquisition_pass(model,[1,3],8,9,8302,response_availability=0.)
    return {'decision_corruption_max_change':float(np.max(abs(q1['a']-q2['a']))),
            'missing_response_retains_paid_label':model.diagnostics['n_paid']==2 and model.diagnostics['n_response']==1,
            'label_only_scores':a['scores'],'component_weights':model.weights,
            'note':'Interface test, not a proof of all downstream adapters.'}


def saved_section(name,fn,budget):
    path=rt.ROOT/'reference_sections'/f'{name}.json'
    fingerprint=rt.sha(rt.ROOT/'MANIFEST.json')
    if path.exists():
        saved=rt.load(path)
        if saved['manifest_sha256']!=fingerprint:raise RuntimeError('Reference cache manifest mismatch')
        if saved['status']!='ok':raise RuntimeError(f'Preserved failed reference {name}')
        return saved['result']
    rows=[rt.json.loads(s) for s in (rt.ROOT/'ledger.jsonl').read_text(encoding='utf-8').splitlines()]
    if any(r['event']=='REFERENCE_SECTION_START' and r['name']==name for r in rows):
        raise RuntimeError(f'Interrupted reference {name}; audit before any retry')
    rt.wait_slot();rt.append({'event':'REFERENCE_SECTION_START','name':name,'manifest_sha256':fingerprint})
    try:
        result=fn(budget)
        rt.save(path,{'status':'ok','manifest_sha256':fingerprint,'result':result})
        rt.append({'event':'REFERENCE_SECTION_END','name':name,'status':'ok'})
        print(f'Reference section {name}: saved',flush=True)
        return result
    except Exception as ex:
        rt.save(path,{'status':'failed','manifest_sha256':fingerprint,'error':repr(ex)})
        rt.append({'event':'REFERENCE_SECTION_END','name':name,'status':'failed','error':repr(ex)})
        raise


def run():
    rt.verify()
    if (rt.ROOT/'INDEPENDENT_CHECKS.json').exists():
        print('Existing checks retained; no reference rerun.');return
    rt.wait_slot();budget=ReferenceBudget()
    result={}
    sections=(('finite_pool',finite_reference),('iid_batch',iid_batch_enumeration),
              ('uncertain_prevalence',uncertain_prevalence_reference),('gaussian_acquisition',gaussian_checks),
              ('nonGaussian_inference',one_label_v2_reference),('additional_idea',local_safeguard),('leakage_missing',checks_leakage))
    try:
        for name,fn in sections:result[name]=saved_section(name,fn,budget)
    except Exception as ex:
        result.update(acceptance_pass=False,status='STOPPED_REFERENCE_EXCEPTION',error=repr(ex),
                      manifest_sha256=rt.sha(rt.ROOT/'MANIFEST.json'),
                      reference_groups=budget.groups,reference_states=budget.states,
                      production_validation_evaluations=budget.production_evaluations,accounting=rt.counts())
        rt.save(rt.ROOT/'INDEPENDENT_CHECKS.json',result)
        raise
    f=result['finite_pool'];g=result['gaussian_acquisition'];ng=result['nonGaussian_inference']
    checks={'finite_exact':f['risk_coefficient_vs_all_actions_error']<1e-12 and f['paired_error']<1e-12,
            'iid_batch_exact':result['iid_batch']['max_error']<1e-12 and result['iid_batch']['bounded_coefficients'],
            'tail_arithmetic':result['iid_batch']['endpoint_finite'] and result['iid_batch']['endpoint_independent_max_error']<1e-12,
            'zero_class':f['zero_class_risk']==.5 and f['zero_class_p_both']==0,
            'posterior_mean_not_exact':result['uncertain_prevalence']['plug_in_regret']>0,
            'quadrature_converged':g['reference_score_convergence']<.0005,
            'qmc_acquisition_accuracy':g['max_acquisition_error']<.002,
            'qmc_decision_accuracy':g['qmc_decision_max_A_error']<.002,
            'toy_ranking':g['reference_top']==g['qmc_top'],
            'nonGaussian_reference_converged':ng['reference_convergence_probability']<.003 and ng['reference_convergence_risk']<.003,
            'nonGaussian_paired_reference_converged':ng['exact_paired_reference_convergence']<.003,
            'leakage':result['leakage_missing']['decision_corruption_max_change']==0,
            'missing_response':result['leakage_missing']['missing_response_retains_paid_label']}
    result.update(checks=checks,acceptance_pass=all(checks.values()),reference_groups=budget.groups,
                  manifest_sha256=rt.sha(rt.ROOT/'MANIFEST.json'),
                  reference_states=budget.states,production_validation_groups=budget.production_groups,
                  production_validation_evaluations=budget.production_evaluations,accounting=rt.counts())
    rt.save(rt.ROOT/'INDEPENDENT_CHECKS.json',result)
    print(checks,flush=True)


if __name__=='__main__':run()
