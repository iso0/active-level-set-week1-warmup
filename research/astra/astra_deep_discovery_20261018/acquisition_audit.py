"""Prospective small finite-mixture lookahead audit on six recorded paid prefixes."""
import os
for key in ('OMP_NUM_THREADS','OPENBLAS_NUM_THREADS','MKL_NUM_THREADS','NUMEXPR_NUM_THREADS'):
    os.environ[key]='1'
import gzip
import hashlib
import json
import math
import time
import uuid
from coordination import HERE,Slot,now
import ledger

with Slot() as slot:
    import numpy as np
    from scipy.integrate import quad
    from scipy.special import ndtr,logsumexp
    from model import MixtureGP
    from worlds import World
    from acquisition import sur_scores
    from threadpoolctl import threadpool_limits
    with threadpool_limits(1):
        audit_manifest=json.loads((HERE/'FROZEN_ACQUISITION_AUDIT.json').read_text())
        for name,h in audit_manifest['source_hashes'].items():
            if hashlib.sha256((HERE/name).read_bytes()).hexdigest()!=h:
                raise RuntimeError('frozen diagnostic changed '+name)
        mf=json.loads((HERE/'FROZEN_MANIFEST_V2.json').read_text())
        for name,h in mf['source_hashes'].items():
            if hashlib.sha256((HERE/name).read_bytes()).hexdigest()!=h:
                raise RuntimeError('frozen science changed '+name)
        destination=HERE/'results'/'ACTUAL_PREFIX_ACQUISITION_AUDIT.json'
        if destination.exists():raise SystemExit('Audit already recorded; no duplicate fits')
        audit_source_hash=hashlib.sha256(__import__('pathlib').Path(__file__).read_bytes()).hexdigest()
        progress_path=HERE/'runtime'/'ACQUISITION_AUDIT_PROGRESS.json'
        if progress_path.exists():
            progress=json.loads(progress_path.read_text())
            if progress.get('source_hash')!=audit_source_hash:raise RuntimeError('audit checkpoint source changed')
            states=progress['states']
        else:states=[]
        attempt=uuid.uuid4().hex
        for family in ('smooth','island_small_unseen','anisotropic'):
            k=mf['families'].index(family)
            wid=f'v2__TEST__r00__f{k:02d}__structure__boundary_regional'
            path=HERE/'results'/'TEST'/(wid+'.json.gz')
            with gzip.open(path,'rt',encoding='utf-8') as f:row=json.load(f)
            world=World(family,row['unit']['seed'],**mf['world_sizes'])
            for budget in (16,40):
                if any(s['unit']==wid and s['budget']==budget for s in states):continue
                slot.check();paid=row['paid_ids'][:budget];model=MixtureGP('structure',1)
                ledger.reserve('controlled',len(model.components),'ACQUISITION_AUDIT__'+wid,attempt)
                model.fit(world.x[paid],[list(world.pay(i).values) for i in paid],paid)
                full=model.snapshot(world.x,world.ref_x)
                event=next(e for e in row['events'] if e['paid_before']==budget)
                if full.digest()!=event['prequery_hash']:raise AssertionError('actual pre-query posterior hash differs')
                scores=sur_scores(full);unpaid=np.array([i for i in range(len(world.x)) if i not in paid])
                top=unpaid[np.lexsort((unpaid,-scores[unpaid]))[:5]].tolist()
                ids=top+[int(i) for i in unpaid if i not in top][:3]
                refs=world.ref_x[:32];small=model.snapshot(world.x[ids],refs)
                current=float(np.minimum(small.ref_probability,1-small.ref_probability).mean())
                approximate=sur_scores(small); exact=[];diagnostics=[]
                started=time.perf_counter()
                for cid in ids:
                    xx=world.x[cid:cid+1];cm=[];cv=[];rm=[];rv=[];cr=[]
                    for comp in model.components:
                        m,v=comp.project(xx,np.zeros(1,int));mr,vr=comp.project(refs,np.zeros(len(refs),int))
                        cm.append(m[0]);cv.append(1-float((v*v).sum())+comp.spec.noise_sd**2)
                        rm.append(mr);rv.append(1-(vr*vr).sum(0))
                        cr.append((comp.kernel(refs,np.zeros(len(refs),int),xx,np.zeros(1,int))-vr.T@v)[:,0])
                    cm,cv,rm,rv,cr=map(np.asarray,(cm,cv,rm,rv,cr))
                    logw=np.log(np.maximum(model.weights,1e-300))
                    def integrand(y):
                        logmass=logw-.5*((y-cm)**2/cv+np.log(2*np.pi*cv))
                        logdensity=logsumexp(logmass)
                        weights=np.exp(logmass-logdensity)
                        updated_m=rm+cr*((y-cm)/cv)[:,None]
                        updated_v=np.maximum(rv-cr**2/cv[:,None],1e-12)
                        prob=weights@ndtr(updated_m/np.sqrt(updated_v))
                        return float(np.exp(logdensity)*np.minimum(prob,1-prob).mean())
                    lo=float(np.min(cm-10*np.sqrt(cv)));hi=float(np.max(cm+10*np.sqrt(cv)))
                    points=sorted(set(cm.tolist()))
                    values=[]
                    for tol in (1e-7,1e-9):
                        result=quad(integrand,lo,hi,epsabs=tol,epsrel=tol,points=points,limit=400,full_output=1)
                        value,error,info=result[:3]
                        values.append({'eps':tol,'risk':float(value),'error':float(error),'evaluations':int(info['neval']),
                                       'message':result[3] if len(result)>3 else None})
                    gain=(current-values[-1]['risk'])*(1-small.availability_weights[0])
                    exact.append(gain)
                    diagnostics.append({'candidate_id':cid,'quadrature':values,
                        'tolerance_difference':abs(values[0]['risk']-values[1]['risk']),
                        'accepted_reference':bool(max(v['error'] for v in values)<=1e-6 and abs(values[0]['risk']-values[1]['risk'])<=1e-6 and gain>=-1e-6)})
                exact=np.asarray(exact)
                states.append({'unit':wid,'budget':budget,'prequery_hash_verified':True,'candidate_ids':ids,
                    'reference_points':32,'posterior_effective_components':float(1/np.sum(model.weights**2)),
                    'moment_scores':approximate.tolist(),'quadrature_scores':exact.tolist(),
                    'max_absolute_score_error':float(np.max(abs(exact-approximate))),
                    'moment_winner':ids[int(approximate.argmax())],'quadrature_winner':ids[int(exact.argmax())],
                    'reference_regret':float(exact.max()-exact[approximate.argmax()]),
                    'quadrature_winner_gap':float(np.diff(np.sort(exact))[-1]),
                    'wall_seconds':time.perf_counter()-started,'candidates':diagnostics})
                ledger.atomic_json(progress_path,{'utc':now().isoformat(),'states':states,'source_hash':audit_source_hash})
        with ledger.database() as c:
            reserved=[json.loads(r['payload']) for r in c.execute("SELECT payload FROM events WHERE kind='FIT_RESERVED' AND unit LIKE 'ACQUISITION_AUDIT__%'")]
        ledger.atomic_json(destination,{'utc':now().isoformat(),'states':states,'nominal_distinct_fits':6,
            'actual_reserved_fits':len(reserved),'actual_reserved_component_solves':sum(r['components'] for r in reserved),
            'all_references_accepted':all(c['accepted_reference'] for s in states for c in s['candidates']),
            'scope':'finite scalar mixture, screened candidates and 32 reference points; no method selection or physical-posterior exactness claim'})
        print('Recorded six actual-prefix acquisition diagnostics')
