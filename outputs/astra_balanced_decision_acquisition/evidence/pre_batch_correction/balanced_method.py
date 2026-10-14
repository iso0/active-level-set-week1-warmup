"""Posterior balanced-risk decisions and paired-output one-step risk reduction.

Imports the byte-identical V2 model. No outcome arrays or evaluator groups enter
selectors. mu is a fixed, feature-only reference distribution, not paid counts.
Population risk is an inductive proxy, not fixed-test-label expected BA.
"""
from functools import lru_cache
import itertools
import numpy as np
from scipy.special import ndtri, ndtr, log_ndtr, logsumexp
from scipy.stats import qmc
from joint_model_v2 import gh


@lru_cache(maxsize=32)
def normal_points(bits, dimension, seed):
    u = qmc.Sobol(dimension, scramble=True, seed=int(seed)).random_base2(bits)
    return ndtri(np.clip(u, np.finfo(float).eps, 1-np.finfo(float).eps))


def root(C):
    C = (np.asarray(C)+np.asarray(C).T)/2
    ev = np.linalg.eigvalsh(C)
    if ev.min() < -1e-7:
        raise FloatingPointError(f"Covariance not PSD: {ev.min()}")
    reg = max(1e-12, 1e-12-ev.min())
    return np.linalg.cholesky(C+reg*np.eye(len(C))), float(reg)


def population_coefficients(h, tau, nref, weights=None):
    """Per latent draw eta/pi and (1-eta)/(1-pi), including dependence.

    Last axis is inputs. First nref inputs define the fixed reference measure.
    Log tails keep the two class normalizations separate, even when ndtr rounds.
    """
    v = np.ones(nref)/nref if weights is None else np.asarray(weights, float)
    if np.any(v <= 0) or not np.isclose(v.sum(), 1):
        raise ValueError("Positive, normalized reference weights required")
    lp, ln = log_ndtr(h/tau), log_ndtr(-h/tau)
    lpi = logsumexp(lp[..., :nref]+np.log(v), axis=-1)
    lpn = logsumexp(ln[..., :nref]+np.log(v), axis=-1)
    a, b = np.exp(lp-lpi[..., None]), np.exp(ln-lpn[..., None])
    return a, b, np.exp(lpi), np.exp(lp)


def decision_pass(model, xref, xpredict, bits=10, seed=771, scrambles=4, weights=None):
    nr = len(xref)
    X = np.vstack([xref, xpredict])
    posts = model.component_posteriors(X)
    aa, bb, pp, prevs, regs = [], [], [], [], []
    for s in range(scrambles):
        A = np.zeros(len(X)); B = A.copy(); P = A.copy(); pi = 0.
        for k, (w, post) in enumerate(zip(model.weights, posts)):
            L, reg = root(post['h_cov']); regs.append(reg)
            z = normal_points(bits, len(X), seed+1009*s+37*k)
            h = post['h_mean']+z@L.T
            a, b, pr, p = population_coefficients(h, model.c.probit_scale, nr, weights)
            A += w*a.mean(0); B += w*b.mean(0); P += w*p.mean(0); pi += w*pr.mean()
        aa.append(A); bb.append(B); pp.append(P); prevs.append(pi)
    A, B = np.mean(aa, 0), np.mean(bb, 0)
    score = (A-B)/(A+B)
    ss = (np.asarray(aa)-bb)/(np.asarray(aa)+bb)
    return {'a': A, 'b': B, 'signed_margin': score, 'decision': score>=0,
            'p_qmc': np.mean(pp, 0), 'pi_mean': float(np.mean(prevs)),
            'risk': float(.5*np.mean(np.minimum(A[:nr], B[:nr]))) if weights is None
                    else float(.5*np.asarray(weights)@np.minimum(A[:nr], B[:nr])),
            'margin_2se': 2*np.std(ss, axis=0, ddof=1)/np.sqrt(scrambles),
            'pi_2se': float(2*np.std(prevs, ddof=1)/np.sqrt(scrambles)),
            'bits': bits, 'max_covariance_regularization': max(regs)}


def decisions(model, xref, xpredict, seed=771):
    previous = decision_pass(model, xref, xpredict, 10, seed)
    history = []
    for bits in (12, 14):
        current = decision_pass(model, xref, xpredict, bits, seed)
        dm = float(np.max(abs(current['signed_margin']-previous['signed_margin'])))
        dp = abs(current['pi_mean']-previous['pi_mean'])
        history.append({'bits': bits, 'max_margin_change': dm, 'pi_change': dp})
        if dm<=.015 and dp<=.003:
            current['numerically_accepted'] = True
            break
        previous = current
    else:
        current['numerically_accepted'] = False
    current['history'] = history
    current['ambiguous'] = abs(current['signed_margin']) <= np.maximum(current['margin_2se'], dm)
    return current


def _candidate_table(posts, mixture, j, tau, noise, bits, order, seed, observe_depth):
    """Unnormalized future-label coefficient table, no fantasy GP refits.

    Each component has its own Gaussian-conditioned Sobol particles. This avoids
    response-likelihood importance collapse. ESS includes future-label weights.
    """
    nr = len(posts[0]['h_mean']); K = len(mixture); M = 2**bits
    mf = np.array([p['f_mean'][j] for p in posts])
    vz = np.array([max(p['f_cov'][j,j],0)+noise**2 for p in posts])
    if observe_depth:
        nodes, ww = gh(order)
        z = (mf[:,None]+np.sqrt(vz[:,None])*nodes).ravel()
        zw = (mixture[:,None]*ww).ravel()
        logw = np.log(mixture)[:,None]-.5*(np.log(2*np.pi*vz)[:,None]+(z-mf[:,None])**2/vz[:,None])
        wk = np.exp(logw-logsumexp(logw, axis=0))
    else:
        z, zw = np.array([0.]), np.array([1.]); wk = mixture[:,None]
    nz = len(z)
    A = np.zeros((nz,2,nr)); B = A.copy()
    mass = np.zeros((nz,2)); squares = mass.copy(); maxreg=0.
    for k,p in enumerate(posts):
        C = p['h_cov'].copy(); mu = np.broadcast_to(p['h_mean'], (nz,nr)).copy()
        if observe_depth:
            cross = p['f_h_cov'][j]
            C -= np.outer(cross,cross)/vz[k]
            mu += (z-mf[k])[:,None]*cross[None,:]/vz[k]
        L, reg = root(C); maxreg=max(maxreg,reg)
        eps = normal_points(bits,nr,seed+37*k)@L.T
        # Chunk future depths; common normals across depths/candidates reduce noise.
        for lo in range(0,nz,12):
            hi=min(nz,lo+12)
            h = mu[lo:hi,None,:]+eps[None,:,:]
            a,b,_,eta = population_coefficients(h,tau,nr)
            q = eta[:,:,j]
            for y,prob in ((0,1-q),(1,q)):
                weight=wk[k,lo:hi]
                A[lo:hi,y] += weight[:,None]*np.mean(a*prob[:,:,None],axis=1)
                B[lo:hi,y] += weight[:,None]*np.mean(b*prob[:,:,None],axis=1)
                mass[lo:hi,y] += weight*prob.mean(1)
                squares[lo:hi,y] += weight**2*np.mean(prob**2,axis=1)/M
    basea = np.einsum('z,zyi->i',zw,A)
    baseb = np.einsum('z,zyi->i',zw,B)
    base = .5*np.minimum(basea,baseb).mean()
    after = .5*np.einsum('z,zyi->',zw,np.minimum(A,B))/nr
    ess=np.divide(mass**2,squares,out=np.zeros_like(mass),where=squares>0)
    low_mass=float(np.sum(zw[:,None]*mass*(ess<32)))
    return {'score':float(base-after),'base_risk':float(base),'after_risk':float(after),
            'a':basea,'b':baseb,'ess_min':float(ess.min()),
            'low_ess_outcome_mass':low_mass,'max_covariance_regularization':maxreg,
            'normalization_error':float(abs(zw@mass.sum(1)-1))}


def risk_acquisition_pass(model, candidate_ids, bits, order, seed=1171, response_availability=1.):
    posts=model.component_posteriors(model.x_ref)
    candidates=np.asarray(candidate_ids,int)
    score=np.zeros((4,len(candidates))); bases=score.copy(); low=score.copy(); norm=score.copy(); ess=score.copy()
    for s in range(4):
        for jj,j in enumerate(candidates):
            pieces=[]
            if response_availability>0:
                pieces.append((response_availability,_candidate_table(posts,model.weights,j,model.c.probit_scale,
                    model.c.response_noise_sd,bits,order,seed+1009*s,True)))
            if response_availability<1:
                pieces.append((1-response_availability,_candidate_table(posts,model.weights,j,model.c.probit_scale,
                    model.c.response_noise_sd,bits,order,seed+1009*s,False)))
            score[s,jj]=sum(w*q['score'] for w,q in pieces)
            bases[s,jj]=sum(w*q['base_risk'] for w,q in pieces)
            low[s,jj]=sum(w*q['low_ess_outcome_mass'] for w,q in pieces)
            norm[s,jj]=max(q['normalization_error'] for _,q in pieces)
            ess[s,jj]=min(q['ess_min'] for _,q in pieces)
    return {'scores':score.mean(0),'score_2se':2*score.std(0,ddof=1)/2,
            'replicate_scores':score,'base_risks':bases.mean(0),'ess_min':float(ess.min()),
            'low_ess_outcome_mass':float(low.max()),'normalization_error':float(norm.max()),
            'bits':bits,'gh_order':order}


def select_risk(model,candidate_ids,seed=1171,response_availability=1.,decision_risk=None):
    previous=risk_acquisition_pass(model,candidate_ids,8,9,seed,response_availability)
    history=[]
    for bits,order in ((10,17),(12,33)):
        current=risk_acquisition_pass(model,candidate_ids,bits,order,seed,response_availability)
        delta=np.abs(current['scores']-previous['scores'])
        error=np.maximum(delta,current['score_2se'])
        history.append({'bits':bits,'gh_order':order,'max_order_difference':float(delta.max()),
                        'max_2se':float(current['score_2se'].max()),'low_ess_mass':current['low_ess_outcome_mass']})
        accepted=bool(error.max()<=.002 and current['low_ess_outcome_mass']<=.002)
        if accepted: break
        previous=current
    if not accepted:
        return {**current,'status':'NUMERICAL_STOP','history':history,'selected':None}
    top=int(np.argmax(current['scores']))
    tie=np.flatnonzero(current['scores'][top]-current['scores']<=.002+error[top]+error)
    chosen=int(min(np.asarray(candidate_ids)[tie]))
    current.update(status='accepted',selected=chosen,history=history,errors=error,
                   near_tie_ids=np.asarray(candidate_ids)[tie],estimated_argmax=int(np.asarray(candidate_ids)[top]),
                   ranking_resolved=bool(len(tie)==1),candidate_ids=np.asarray(candidate_ids),
                   max_tower_risk_difference=None if decision_risk is None else float(np.max(abs(current['base_risks']-decision_risk))))
    return current


def select_variance(model,candidate_ids,response_availability=1.):
    X=model.x_ref[np.asarray(candidate_ids)]
    def calc(g,c):
        paired=model.acquisition(X,gh_order=g,cdf_order=c)['score']
        if response_availability==1:return paired
        label=model.acquisition(X,gh_order=g,cdf_order=c,observe_response=False)['score']
        return response_availability*paired+(1-response_availability)*label
    prev=calc(15,48);hist=[]
    for g,c in ((31,64),(63,96)):
        score=calc(g,c);err=np.abs(score-prev)
        hist.append({'gh_order':g,'cdf_order':c,'max_order_difference':float(err.max())})
        if err.max()<=.0002:break
        prev=score
    else:return {'status':'NUMERICAL_STOP','selected':None,'history':hist}
    top=int(np.argmax(score));tie=np.flatnonzero(score[top]-score<=.0002+err[top]+err)
    return {'status':'accepted','selected':int(min(np.asarray(candidate_ids)[tie])),
            'scores':score,'candidate_ids':candidate_ids,'near_tie_ids':np.asarray(candidate_ids)[tie],
            'ranking_resolved':len(tie)==1,'history':hist}


def select_margin(decision,candidate_ids):
    ids=np.asarray(candidate_ids);s=np.abs(decision['signed_margin'][ids]);top=int(np.argmin(s))
    err=decision['margin_2se'][ids]
    tie=np.flatnonzero(s-s[top]<=1e-8+err+err[top])
    return {'status':'accepted','selected':int(min(ids[tie])),'scores':-s,'candidate_ids':ids,
            'near_tie_ids':ids[tie],'ranking_resolved':len(tie)==1}


def finite_pool_coefficients(label_states,probabilities):
    """Exact fixed recorded-pool coefficients from a normalized joint label law.

    Known paid labels must already be fixed in every state. Loss on all-one or
    all-zero events is the action-independent constant 1/2; zero denominators
    contribute zero coefficients. Conditional BA requires division by p_both.
    """
    y=np.asarray(label_states,int);w=np.asarray(probabilities,float);n=y.shape[1]
    if not np.isin(y,[0,1]).all() or np.any(w<0) or not np.isclose(w.sum(),1):raise ValueError('Invalid label law')
    N=y.sum(1);both=(N>0)&(N<n)
    a=np.sum(w[both,None]*y[both]/N[both,None],axis=0)
    b=np.sum(w[both,None]*(1-y[both])/(n-N[both,None]),axis=0)
    return {'a':a,'b':b,'decision':a>=b,'p_both':float(w[both].sum()),
            'risk':float(.5*w[~both].sum()+.5*np.minimum(a,b).sum())}


def independent_label_law(eta,paid=None):
    """Small-pool independent-Bernoulli reference law; paid outcomes fixed."""
    p=np.asarray(eta,float).copy();paid={} if paid is None else paid
    y=np.array(list(itertools.product((0,1),repeat=len(p))),int)
    w=np.prod(np.where(y,p,1-p),axis=1)
    # Conditioning on already observed labels; no simulated replacement labels.
    for i,value in paid.items():w[y[:,int(i)]!=value]=0
    if w.sum()==0:raise ValueError('Impossible paid labels under specified law')
    w/=w.sum();return y[w>0],w[w>0]
