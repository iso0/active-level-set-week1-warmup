"""The single coherent-gate continuation. Imports only inside an allocated worker."""
import json
import time
import numpy as np
import psutil
from scipy.linalg import cho_factor,cho_solve,solve_triangular
from scipy.special import logsumexp,ndtr
from control import ROOT,atomic,now,read,sha
from research_v1.model import matern,combine
from research_v1.worker import Meter,metrics,save_npz

ARMS=('strong','gated','coherent','coherent_trace')

def rankone_bank(x,paid,y,theta,gates,matches,meter=None):
    """Exact Woodbury update for each component, conditional on theta."""
    paid=np.asarray(paid,int);y=np.asarray(y,float);d=x.shape[1]
    if meter:meter('model_requests',2);meter('component_solves',1+2*len(gates))
    amp2,noise2=np.exp(2*np.asarray(theta)[d:]);ell=np.exp(theta[:d])
    cross=amp2*matern(x[paid],x,ell);c=cross[:,paid]+(noise2+1e-10)*np.eye(len(paid))
    fac=cho_factor(c,lower=True,check_finite=False);alpha=cho_solve(fac,y,check_finite=False)
    v=solve_triangular(fac[0],cross,lower=True,check_finite=False)
    mu0=cross.T@alpha;var0=np.maximum(amp2-np.sum(v*v,axis=0),1e-12)
    ld0=float(2*np.log(np.diag(fac[0])).sum());quad0=float(y@alpha)
    loge0=-.5*(ld0+quad0+len(paid)*np.log(2*np.pi))
    base={'mean':mu0,'variance':var0,'log_evidence':loge0,'logdet':ld0,'quadratic':quad0}
    count=len(gates);a=np.vstack([gates,np.sqrt(matches)[:,None]*np.ones((count,len(x)))])
    ap=a[:,paid];ci_a=cho_solve(fac,ap.T,check_finite=False)
    q=np.sum(ap*ci_a.T,axis=1);b=ap@alpha;vbeta=1/(1/.36+q)
    residual=a-(cross.T@ci_a).T
    means=mu0+residual*(vbeta*b)[:,None];variances=var0+residual**2*vbeta[:,None]
    logdet=ld0+np.log1p(.36*q);quad=quad0-vbeta*b*b
    all_cs=[{'mean':means[j],'variance':variances[j],
             'log_evidence':float(-.5*(logdet[j]+quad[j]+len(paid)*np.log(2*np.pi))),
             'logdet':float(logdet[j]),'quadratic':float(quad[j])} for j in range(2*count)]
    out={}
    for name,offset in [('coherent',0),('coherent_trace',count)]:
        cs=[base,*all_cs[offset:offset+count]];prior=np.r_[.5,np.full(count,.5/count)];p=combine(cs,prior)
        p['diagnostics']={'null_weight':float(p['weights'][0]),'effective_components':float(1/np.sum(p['weights']**2)),
                         'component_log_evidence':[float(z['log_evidence']) for z in cs],
                         'component_logdet':[z['logdet'] for z in cs],'component_quadratic':[z['quadratic'] for z in cs],
                         'weights':p['weights'].tolist(),'theta':list(theta),'gate_reference_trace':list(matches),
                         'beta_posterior_mean':(vbeta*b)[offset:offset+count].tolist(),
                         'beta_posterior_variance':vbeta[offset:offset+count].tolist()}
        out[name]=p
    return out,{'dense_factorizations':1,'rankone_updates':2*count,'base_log_evidence':loge0}

def references(u,q,slot):
    q.reserve(u['id'],'reference_solves',100,2000)
    from scipy.stats import multivariate_normal
    rng=np.random.default_rng(716291);errors=[]
    for n in (3,8,16):
        x=rng.uniform(size=(40,4));paid=np.arange(n);y=rng.normal(size=n)
        theta=np.log([.2,.4,.8,1.2,.7,.15]);a=np.exp(-np.sum((x-.45)**2,axis=1)/.15)
        m=float(np.mean(a[n:]**2));out,_=rankone_bank(x,paid,y,theta,np.array([a]),np.array([m]))
        k=.49*matern(x,x,np.exp(theta[:4]));basec=k[:n,:n]+(.15**2+1e-10)*np.eye(n)
        base_mu=k[:,paid]@np.linalg.solve(basec,y);base_var=np.diag(k)-np.sum(k[:,paid]*np.linalg.solve(basec,k[paid]).T,axis=1)
        log0=multivariate_normal.logpdf(y,cov=basec)
        for name,basis in [('coherent',a),('coherent_trace',np.full(len(x),np.sqrt(m)))]:
            kk=k+.36*np.outer(basis,basis);c=kk[:n,:n]+(.15**2+1e-10)*np.eye(n)
            mu=kk[:,paid]@np.linalg.solve(c,y);var=np.diag(kk)-np.sum(kk[:,paid]*np.linalg.solve(c,kk[paid]).T,axis=1)
            log1=multivariate_normal.logpdf(y,cov=c);ww=np.exp(np.array([log0,log1])-logsumexp([log0,log1]))
            prob=ww[0]*ndtr(base_mu/np.sqrt(np.maximum(base_var,1e-12)))+ww[1]*ndtr(mu/np.sqrt(np.maximum(var,1e-12)))
            expected_mean=ww[0]*base_mu+ww[1]*mu
            expected_var=ww[0]*(base_var+base_mu**2)+ww[1]*(var+mu**2)-expected_mean**2
            error=max(float(np.max(abs(out[name]['mean']-expected_mean))),float(np.max(abs(out[name]['variance']-expected_var))),
                      float(np.max(abs(out[name]['probability']-prob))),abs(out[name]['diagnostics']['component_log_evidence'][1]-log1))
            assert error<1e-8;errors.append({'n':n,'model':name,'maximum_error':error})
    result={'status':'PASS','utc':now().isoformat(),'dense_references':errors,'reference_solves_reserved':100,
            'scope':'Woodbury, determinant lemma, exact finite-mixture moments conditional on fixed theta; not scientific performance.'}
    atomic(ROOT/'evidence/MODEL_NUMERICAL_CHECKS_V2.json',result);return result

def run_unit(u,q,slot):
    if u.get('kind')=='reference':return references(u,q,slot)
    parent_path=ROOT/'results'/('unit__'+u['parent_id']+'.json');assert sha(parent_path)==u['parent_sha256']
    parent=read(parent_path);source=ROOT/'results/dev_v1'/u['parent_id']
    with np.load(source/'world.npz') as saved:w={k:saved[k] for k in saved.files}
    x=w['x'];centers=np.random.default_rng(91612).choice(256,32,replace=False)
    gates=np.array([np.exp(-np.sum((x-x[j])**2,axis=1)/(2*(rad/2)**2)) for rad in (.45,.9) for j in centers])
    matches=np.mean(gates[:,256:]**2,axis=1)
    directory=ROOT/'results/dev_v2'/u['id'];directory.mkdir(parents=True,exist_ok=True)
    previous=q.checkpoint(u['id']);records=previous.get('records',[]);completed={r['budget'] for r in records}
    meter=Meter(q,u['id']);cpu=time.process_time();wall=time.perf_counter();previous_cpu=previous.get('cpu_seconds',0);previous_wall=previous.get('wall_seconds',0)
    for original in parent['records']:
        b=original['budget']
        if b in completed:continue
        slot.check();theta=np.array(original['arms']['strong']['diagnostics']['theta'])
        paid=parent['paid'][:b];observations=parent['observations'][:b]
        out,counts=rankone_bank(x,paid,observations,theta,gates,matches,meter)
        arrays={};row={'budget':b,'paid_ids':paid,'paid_region_hits':original['paid_region_hits'],'arms':{},'actual_operations':counts}
        assert sha(ROOT/original['predictions_file'])==original['predictions_sha256']
        with np.load(ROOT/original['predictions_file']) as old:
            for arm in ('strong','gated'):
                for field in ('mean','variance','probability'):arrays[arm+'_'+field]=old[arm+'_'+field]
                row['arms'][arm]=original['arms'][arm]
        for arm,p in out.items():
            for field in ('mean','variance','probability','within','between'):arrays[arm+'_'+field]=p[field]
            row['arms'][arm]={'metrics':metrics(p['probability'][256:],p['mean'][256:],w),'diagnostics':p['diagnostics']}
        path=directory/f'B{b:02d}.npz';save_npz(path,**arrays)
        row.update(predictions_file=str(path.relative_to(ROOT)),predictions_sha256=sha(path),parent_predictions_sha256=original['predictions_sha256'])
        records.append(row);state={'records':records,'cpu_seconds':previous_cpu+time.process_time()-cpu,
             'wall_seconds':previous_wall+time.perf_counter()-wall,'peak_rss_bytes':psutil.Process().memory_info().rss,
             'used_counts':{k:previous.get('used_counts',{}).get(k,0)+v for k,v in meter.used.items()}}
        q.checkpoint(u['id'],state)
    state=q.checkpoint(u['id'])
    return {'status':'COMPLETE','utc':now().isoformat(),'id':u['id'],'family':parent['family'],'seed':parent['seed'],'path':parent['path'],
            'parent_id':u['parent_id'],'parent_sha256':u['parent_sha256'],'paid':parent['paid'],'new_queries':0,'new_background_optimizations':0,**state}
