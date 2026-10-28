"""Paid-ID ask/tell adapter. Caller owns resources and supplies actual observations."""
import hashlib
import json
import math
from pathlib import Path
import numpy as np
from .local_core import ModelFamily
from .coherent_core import rankone_bank

def source_hash():
    p=Path(__file__).parent;h=hashlib.sha256()
    for name in ('api.py','local_core.py','coherent_core.py'):h.update((p/name).read_bytes())
    return h.hexdigest()

class PaidLocalLearner:
    def __init__(self,candidates,reference,model='strong'):
        self.x=np.asarray(candidates,float);self.reference=np.asarray(reference,float)
        if self.x.ndim!=2 or self.x.shape[1]!=4 or self.reference.ndim!=2 or self.reference.shape[1]!=4:raise ValueError('Expected public four-dimensional normalized inputs')
        if not np.isfinite(self.x).all() or not np.isfinite(self.reference).all():raise ValueError('Nonfinite input')
        if np.min(self.x)<0 or np.max(self.x)>1 or np.min(self.reference)<0 or np.max(self.reference)>1:raise ValueError('Normalize from public inputs before construction')
        if model not in ('strong','compact','gated','trace_match','coherent','coherent_trace'):raise ValueError('Unknown model')
        self.model=model;self.core=ModelFamily(self.x,self.reference);self.paid=[];self.records=[];self.pending=None;self.cache=None

    def _posterior(self):
        if self.cache is not None:return self.cache
        ids=[r['paid_id'] for r in self.records if r['quality']=='valid' and r['monitor'] is not None]
        if len(ids)<8:return None
        values=[r['monitor'] for r in self.records if r['quality']=='valid' and r['monitor'] is not None]
        if self.model in ('coherent','coherent_trace'):
            self.core.fit(ids,values,all_models=False)
            p=rankone_bank(self.core.x,ids,values,self.core.theta,np.asarray(self.core.gates),np.asarray(self.core.matches))[0][self.model]
        else:p=self.core.fit(ids,values,all_models=self.model!='strong')[self.model]
        self.cache={k:p[k].tolist() for k in ('mean','variance','probability')}
        self.cache['noise_variance']=float(np.exp(2*self.core.theta[-1]))
        return self.cache

    def ask(self,selector='margin'):
        if self.pending is not None:return dict(self.pending)
        if len(self.paid)==len(self.x):raise StopIteration('Pool exhausted')
        p=self._posterior()
        if selector not in ('margin','maximin'):raise ValueError('Only tested cheap controls are available')
        if selector=='maximin' or p is None:
            score=-np.sum((self.x-.5)**2,axis=1) if not self.paid else np.sum((self.x[:,None]-self.x[np.array(self.paid)][None,:])**2,axis=2).min(1)
            mode='maximin_startup' if p is None else 'maximin'
        else:score=-np.abs(np.asarray(p['probability'][:len(self.x)])-.5);mode='margin'
        score[np.array(self.paid,dtype=int)]=-np.inf;j=int(np.argmax(score))
        before={'paid_id':j,'budget_before':len(self.paid),'selector':mode,'model':self.model,'source_hash':source_hash(),
                'mean_before':None if p is None else p['mean'][j],
                'latent_variance_before':None if p is None else p['variance'][j],
                'observation_variance_before':None if p is None else p['variance'][j]+p['noise_variance'],
                'variance_contract':'latent variance + independent homoskedastic noise exactly once; plug-in hyperparameters',
                'target':'latent continuous monitor >= 0; canonical recorded label is a distinct target'}
        payload={'records':self.records,'posterior':p,'before':before,'core_state':self.core.state()}
        before['posterior_hash']=hashlib.sha256(json.dumps(payload,sort_keys=True,allow_nan=False).encode()).hexdigest()
        self.pending=before;return dict(before)

    def tell(self,paid_id,monitor,quality='valid',cost=1.,canonical_label=None):
        if self.pending is None or paid_id!=self.pending['paid_id'] or paid_id in self.paid:raise ValueError('Observation must match the unique pending paid ID')
        if quality not in ('valid','missing','numerical_failure'):raise ValueError('Unknown quality')
        if not math.isfinite(cost) or cost<=0:raise ValueError('Positive finite paid cost required')
        if monitor is not None and not math.isfinite(float(monitor)):raise ValueError('Use None and missing quality for unavailable output')
        if quality=='valid' and monitor is None:raise ValueError('Valid output cannot be missing')
        row={'paid_id':int(paid_id),'monitor':None if monitor is None else float(monitor),'quality':quality,'cost':float(cost),
             'canonical_label':canonical_label,'canonical_label_used_by_model':False,'prequery':self.pending}
        self.paid.append(int(paid_id));self.records.append(row);self.pending=None;self.cache=None

    def snapshot(self):
        return {'schema':1,'source_hash':source_hash(),'candidates':self.x.tolist(),'reference':self.reference.tolist(),
                'model':self.model,'paid':self.paid,'records':self.records,'pending':self.pending,'cache':self.cache,'core_state':self.core.state()}

    @classmethod
    def restore(cls,state):
        if state['schema']!=1 or state['source_hash']!=source_hash():raise ValueError('Snapshot/source mismatch')
        obj=cls(state['candidates'],state['reference'],state['model']);obj.paid=list(state['paid']);obj.records=list(state['records'])
        obj.pending=state['pending'];obj.cache=state['cache'];obj.core.restore(state['core_state']);return obj
