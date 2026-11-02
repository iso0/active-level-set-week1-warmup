"""Registered final numerical replay plus standalone-contract check, no optimization."""
import json
import numpy as np
from scipy.special import ndtr
from control import ROOT,atomic,now,read,sha

def run_unit(u,q,slot):
    q.reserve(u['id'],'reference_solves',768,2000)
    rows=[];search=[];max_error=0.;near_ties=0
    for parent,h in read(ROOT/'FROZEN_DEV_V2.json')['parents'].items():
        p=ROOT/'results'/('unit__'+parent+'.json');assert sha(p)==h;r=read(p)
        with np.load(ROOT/'results/dev_v1'/parent/'world.npz') as w:
            x=w['x'][:256].copy();paid=np.array(r['paid']);region=w['region'];labels=w['labels'];observed=w['observed']
            footprint=[i+1 for i,j in enumerate(paid) if region[j]]
            latent_positive=[i+1 for i,j in enumerate(paid) if region[j] and labels[j]]
            recorded_positive=[i+1 for i,j in enumerate(paid) if region[j] and observed[j]>=0]
            search.append({'parent':parent,'family':r['family'],'seed':r['seed'],'path':r['path'],
                'first_footprint_hit':footprint[0] if footprint else None,
                'first_latent_positive_in_footprint':latent_positive[0] if latent_positive else None,
                'first_observed_positive_in_footprint':recorded_positive[0] if recorded_positive else None,
                'footprint_hits':len(footprint),'latent_positive_footprint_hits':len(latent_positive),
                'observed_positive_footprint_hits':len(recorded_positive)})
        for query in r['queries']:
            if query['budget_before']%2==0:continue
            slot.check();b=query['budget_before'];paid=np.array(r['paid'][:b]);y=np.array(r['observations'][:b]);theta=np.array(query['theta_before'])
            amp2,noise2=np.exp(2*theta[4:]);ell=np.exp(theta[:4])
            distance=np.sqrt(3*np.sum(((x[paid,None]-x[None,:])/ell)**2,axis=2));ks=amp2*(1+distance)*np.exp(-distance)
            c=ks[:,paid]+(noise2+1e-10)*np.eye(b)
            mean=ks.T@np.linalg.solve(c,y);var=np.maximum(amp2-np.sum(ks*np.linalg.solve(c,ks),axis=0),1e-12)
            j=query['query_id'];error=max(abs(mean[j]-query['mean_before']),abs(var[j]-query['latent_variance_before']),abs(noise2-query['noise_variance_before']))
            assert error<1e-8;max_error=max(max_error,float(error));gap=None;literal_match=None
            if r['path']=='strong_margin':
                score=-np.abs(ndtr(mean/np.sqrt(var))-.5);score[paid]=-np.inf
                gap=float(np.max(score)-score[j]);assert gap<1e-8
                literal_match=int(np.argmax(score))==j
                if not literal_match:near_ties+=1
            rows.append({'parent':parent,'budget':b,'maximum_moment_error':float(error),'margin_gap':gap,'literal_argmax_match':literal_match})
    assert len(rows)==512
    # Portable ask/tell replay with fixed theta: no empirical-Bayes optimization.
    from handoff.api import PaidLocalLearner
    rng=np.random.default_rng(716292);candidates=rng.uniform(size=(40,4));reference=rng.uniform(size=(70,4))
    learner=PaidLocalLearner(candidates,reference,model='coherent')
    for i in range(8):
        query=learner.ask();assert query==learner.ask()
        learner.tell(query['paid_id'],float(candidates[query['paid_id'],0]-.5),canonical_label=bool(i%2))
    learner.core.theta=np.log([.3,.5,.7,.9,.8,.1]);learner.core.theta_budget=8
    query=learner.ask();saved=json.loads(json.dumps(learner.snapshot()));restored=PaidLocalLearner.restore(saved)
    assert restored.ask()==query
    assert query['observation_variance_before']>=query['latent_variance_before']>0
    restored.tell(query['paid_id'],None,quality='missing',cost=1.)
    assert len(restored.paid)==9 and sum(r['cost'] for r in restored.records)==9
    rejected=False
    try:restored.tell(query['paid_id'],0.)
    except ValueError:rejected=True
    assert rejected and all(not r['canonical_label_used_by_model'] for r in restored.records)
    result={'status':'PASS','utc':now().isoformat(),'odd_budget_replays':len(rows),'maximum_moment_error':max_error,
            'margin_argmax_roundoff_near_ties':near_ties,'replays':rows,'search_diagnostics':search,'standalone_ask_tell_pass':True,
            'standalone_resume_pending_query_identical':True,'missing_channel_charged':True,'duplicate_id_rejected':True,
            'canonical_label_explicitly_unused':True,'new_parameter_optimizations':0,'reference_solves_reserved':768,
            'scope':'Independent dense numerical references and interface tests; no new scientific worlds or acquisition paths.'}
    atomic(ROOT/'evidence/FINAL_NUMERICAL_AND_HANDOFF_CHECKS.json',result);return result
