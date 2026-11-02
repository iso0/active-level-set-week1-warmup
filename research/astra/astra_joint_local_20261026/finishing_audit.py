"""Post-TEST validation only. No new method choice or scientific fitting.

One toy fit checks the portable interface. Dense references use saved parameters.
Loaded by run_queue after resources.Slot, never as an unallocated script.
"""
import json,hashlib,time,csv
from collections import defaultdict
import numpy as np
from scipy.special import ndtr
from control import ROOT,read,sha,atomic,now
from joint_model import predict,make_gates
from joint_references import dense
from handoff_api import JointLocalLearner,digest

def kernel(a,b,theta):
    r=np.sqrt(3*np.sum(((a[:,None]-b[None])/np.exp(theta[:4]))**2,axis=2))
    return np.exp(2*theta[4])*(1+r)*np.exp(-r)

def direct_null(x,paid,y,theta):
    c=kernel(x[paid],x[paid],theta)+(np.exp(2*theta[-1])+1e-10)*np.eye(len(paid))
    cross=kernel(x,x[paid],theta)
    mean=cross@np.linalg.solve(c,y)
    variance=np.maximum(np.exp(2*theta[4])-np.sum(cross*np.linalg.solve(c,cross.T).T,axis=1),1e-12)
    return mean,variance,ndtr(mean/np.sqrt(variance))

def feature_choice(x,paid):
    if not paid:return int(np.argmin(np.sum((x-.5)**2,axis=1)))
    d=np.sum((x[:,None]-x[np.array(paid)][None])**2,axis=2).min(1)
    d[paid]=-np.inf;return int(np.argmax(d))

def csvout(path,rows):
    with path.open('w',newline='',encoding='utf8') as h:
        writer=csv.DictWriter(h,list(rows[0]));writer.writeheader();writer.writerows(rows)

def run_unit(u,q,slot):
    started=time.process_time();out=ROOT/'results/finishing';out.mkdir(exist_ok=True)
    q.reserve(u['id'],'TEST_V1__reference_solves',1200,2000)
    limits={'model_requests':64,'optimizer_evaluations':100000,'rankone_updates':2000000}
    for k,v in limits.items():q.reserve(u['id'],'FINISHING__'+k,v,v)
    used={k:0 for k in limits}
    def meter(k,n=1):
        used[k]+=n
        if used[k]>limits[k]:raise RuntimeError('Finishing contract budget exceeded: '+k)
    units=[read(p) for p in sorted((ROOT/'results').glob('unit__test_v1_*')) if not p.name.endswith('cached_analysis.json')]
    assert len(units)==288
    integrity=[];moments=[];references=[];diagnostics=[];hits=[];query_plot=[]
    for unit in units:
        slot.check();base=ROOT/unit['parent_path'];parent=read(base)
        assert sha(base)==unit['parent_sha256'] and sha(ROOT/unit['world_path'])==unit['world_sha256']
        with np.load(ROOT/unit['world_path']) as z:w={k:z[k] for k in z.files}
        paid=unit['paid'];obs=unit['observations'];assert paid==parent['paid'] and obs==parent['observations']
        assert len(set(paid))==24 and all(0<=i<256 for i in paid)
        assert np.array_equal(w['observed'][paid],obs)
        start=[]
        for j in paid[:8]:assert j==feature_choice(w['x'][:256],start);start.append(j)
        selected=int(str(unit['seed'])[-3:])==0 and unit['path']=='strong_margin'
        for b in range(8,24):
            pre=read(base.parent/f'prequery_B{b:02d}.json');unhashed={k:v for k,v in pre.items() if k!='posterior_hash'}
            assert pre['posterior_hash']==digest(unhashed)
            assert pre['paid_ids_before']==paid[:b] and pre['observations_before']==obs[:b] and pre['query_id']==paid[b]
            assert {k:v for k,v in parent['queries'][b-8].items() if k!='observed'}==pre
            assert parent['queries'][b-8]['observed']==obs[b]
            if unit['path']=='maximin':assert pre['query_id']==feature_choice(w['x'][:256],paid[:b])
            if selected:
                mean,var,prob=direct_null(w['x'][:256],paid[:b],np.array(obs[:b]),np.array(pre['theta_before']))
                j=pre['query_id'];err=max(abs(mean[j]-pre['mean_before']),abs(var[j]-pre['latent_variance_before']))
                assert err<1e-8
                score=-abs(prob-.5);score[paid[:b]]=-np.inf;ranked=np.argsort(-score,kind='stable')
                gap=float(score[ranked[0]]-score[ranked[1]]);regret=float(score[ranked[0]]-score[j])
                assert regret<1e-8
                moments.append({'unit':unit['id'],'budget':b,'moment_max_error':float(err),'exact_argmax':bool(j==ranked[0]),
                                'score_regret':regret,'top_gap':gap,'near_tie_1e8':gap<1e-8})
                query_plot.append({'family':unit['family'],'budget':b,'recorded':pre['mean_before'],'dense':float(mean[j]),
                                   'latent_sd':float(np.sqrt(var[j])),'observed':obs[b]})
        for rec in unit['records']:
            assert sha(ROOT/rec['predictions_file'])==rec['predictions_sha256']
            assert rec['paid_ids']==paid[:rec['budget']] and rec['observations']==obs[:rec['budget']]
            d=rec['arms'];fixed=d['fixed_extra']['diagnostics'];joint=d['joint']['diagnostics'];t0=np.array(fixed['theta']);t1=np.array(joint['theta'])
            lw=np.array(joint['weights'][1:]);lw/=lw.sum()
            diagnostics.append({'family':unit['family'],'seed':unit['seed'],'path':unit['path'],'budget':rec['budget'],
                'joint_minus_fixed_ba':d['joint']['metrics']['ba']-d['fixed_extra']['metrics']['ba'],
                'joint_minus_fixed_region_error':d['joint']['metrics']['regional_error']-d['fixed_extra']['metrics']['regional_error'],
                'log_noise_change':float(t1[-1]-t0[-1]),'log_amplitude_change':float(t1[-2]-t0[-2]),
                'log_length_rms_change':float(np.sqrt(np.mean((t1[:4]-t0[:4])**2))),
                'null_weight_fixed':fixed['null_weight'],'null_weight_joint':joint['null_weight'],
                'location_entropy':joint['location_entropy'],
                'weighted_lambda':float(lw@joint['lambda_information']),
                'weighted_beta_variance':float(lw@joint['beta_variance']),
                'geometric_count':int(w['region'][paid[:rec['budget']]].sum())})
        if selected:
            rec=next(r for r in unit['records'] if r['budget']==16)
            ix=np.r_[paid[:16],np.arange(256,264)];x=w['x'][ix];g=make_gates(w['x'][:256],w['x'][256:])[0][:,ix]
            th=np.array(rec['arms']['joint']['diagnostics']['theta'])
            p=predict(th,x,np.arange(16),np.array(obs[:16]),g,full_cov=True,meter=meter)
            ref=dense(th,x,np.arange(16),np.array(obs[:16]),g)
            err=max(float(np.max(abs(p[k]-ref[k]))) for k in ('mean','covariance','probability','weights','log_evidence'))
            with np.load(ROOT/rec['predictions_file']) as z:
                saved=max(float(np.max(abs(p[k]-z['joint_'+k][ix]))) for k in ('mean','variance','probability'))
            assert max(err,saved)<1e-8
            references.append({'family':unit['family'],'seed':unit['seed'],'budget':16,'dense_error':err,'saved_error':saved,'components':65})
        def first(mask):
            found=np.flatnonzero(mask[paid]);return int(found[0]+1) if len(found) else None
        sign=float(w['sign']);geom=w['region'].astype(bool)
        hit={'family':unit['family'],'seed':unit['seed'],'path':unit['path'],'sign':sign,
             'first_geometric':first(geom),'first_geometric_latent_positive':first(geom&(w['latent']>=0)),
             'first_geometric_observed_positive':first(geom&(w['observed']>=0)),
             'first_geometric_signed_target':first(geom&(sign*w['latent']>=0)),
             'first_geometric_observed_signed_target':first(geom&(sign*w['observed']>=0)),
             'count_geometric':int(geom[paid].sum()),'count_signed_target':int((geom&(sign*w['latent']>=0))[paid].sum())}
        for arm in ('strong_extra','fixed_extra','joint'):
            after=[r for r in unit['records'] if hit['first_geometric'] is not None and r['budget']>=hit['first_geometric']]
            hit[arm+'_posthit_region_error_mean']=float(np.mean([r['arms'][arm]['metrics']['regional_error'] for r in after])) if after else None
        hits.append(hit);integrity.append({'unit':unit['id'],'path':True,'prequery_hashes':16,'prediction_hashes':9})
    assert len(references)==12 and len(moments)==192
    # Interface fixture: one toy paid-only fit; no scientific performance score.
    rng=np.random.default_rng(726299);xc=rng.uniform(size=(40,4));xr=rng.uniform(size=(20,4))
    a=JointLocalLearner(xc,xr,meter=meter)
    for i in range(8):
        ask=a.ask();assert a.ask()==ask
        a.tell(ask['id'],float(xc[ask['index'],0]-.5),canonical_label=(i%2))
    snap=a.snapshot();b=JointLocalLearner.restore(snap,meter=meter)
    before_counts=used.copy();pa=a._posterior();pb=b._posterior()
    assert np.array_equal(pa['probability'],pb['probability']) and a.ask()==b.ask()
    # Canonical label is logged but not a model target; changing it cannot affect posterior.
    alt=json.loads(json.dumps(snap))
    for row in alt['records']:row['canonical_label']=1-row['canonical_label']
    c=JointLocalLearner.restore(alt,meter=meter);assert np.array_equal(c._posterior()['probability'],pa['probability'])
    ask=a.ask();old_valid=len(a._valid());a.tell(ask['id'],None,quality='missing',cost=2)
    assert len(a.records)==9 and len(a._valid())==old_valid and sum(r['cost'] for r in a.records)==10
    rejected=False
    try:a.tell(ask['id'],1.)
    except ValueError:rejected=True
    assert rejected and len(a.records)==9
    assert used['optimizer_evaluations']==before_counts['optimizer_evaluations']
    atomic(out/'ASK_TELL_FIXTURE.json',{'status':'PASS','deterministic_restore':True,'pending_idempotent':True,
        'missing_charged':True,'duplicate_rejected':True,'canonical_not_used':True,'snapshot':snap,
        'scope':'Software/numerical contract fixture, not acquisition performance or real-data validation'})
    csvout(out/'MODEL_DIAGNOSTICS.csv',diagnostics);csvout(out/'HIT_DIAGNOSTICS.csv',hits)
    csvout(out/'PREQUERY_REPLAY.csv',moments);csvout(out/'DENSE_MIXTURE_REPLAY.csv',references)
    # Deterministic illustrations: first replicate per family, not best examples.
    import matplotlib;matplotlib.use('Agg');import matplotlib.pyplot as plt
    fig,axes=plt.subplots(3,4,figsize=(15,9),sharex=True)
    for ax,family in zip(axes.flat,sorted({r['family'] for r in query_plot})):
        rr=[r for r in query_plot if r['family']==family];bud=[r['budget'] for r in rr]
        ax.errorbar(bud,[r['recorded'] for r in rr],yerr=[2*r['latent_sd'] for r in rr],fmt='o',ms=3,label='prequery mean +/- 2 latent SD')
        ax.plot(bud,[r['dense'] for r in rr],'x',label='independent dense');ax.scatter(bud,[r['observed'] for r in rr],s=12,color='black',label='subsequent noisy observation')
        ax.axhline(0,color='gray',lw=.7);ax.set_title(family.replace('_',' '),fontsize=10);ax.set_xlabel('paid budget before next query')
    handles,labels=axes.flat[0].get_legend_handles_labels();fig.legend(handles,labels,loc='upper center',ncol=3,fontsize=9)
    fig.suptitle('Saved strong-margin paths: numerical replay, first replicate in every family',y=1.0)
    fig.tight_layout(rect=[0,0,1,.94]);fig.savefig(out/'PREQUERY_REPLAY.png',dpi=150);fig.savefig(out/'PREQUERY_REPLAY.pdf');plt.close(fig)
    report={'status':'PASS','utc':now().isoformat(),'all_path_checks':len(integrity),'prequery_hashes':len(integrity)*16,
        'saved_prediction_hashes':len(integrity)*9,'dense_mixture_prefixes':references,
        'independent_null_prequery_count':len(moments),'max_prequery_moment_error':max(r['moment_max_error'] for r in moments),
        'nonidentical_argmax':sum(not r['exact_argmax'] for r in moments),'near_ties':sum(r['near_tie_1e8'] for r in moments),
        'max_score_regret':max(r['score_regret'] for r in moments),'reference_factorizations':12*65+192,
        'used_contract_counts':used,'cpu_seconds':time.process_time()-started,
        'scope':'Cached-parameter references and one toy interface fit; no scientific refits, method changes or new acquisition experiment'}
    atomic(out/'AUDIT.json',report);return report
