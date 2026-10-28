"""Portable research interface; caller allocates a numerical resource first.

The model is frozen joint empirical Bayes. Margin is an unbenchmarked interface
baseline, not a promoted acquisition result. No oracle/evaluator is imported.
"""
import hashlib
import json
import numpy as np
from joint_model import make_gates, fit_theta, predict
from legacy_model import learn_theta

def digest(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, allow_nan=False).encode()).hexdigest()

class JointLocalLearner:
    def __init__(self, candidates, reference, candidate_ids=None, meter=None):
        self.candidates=np.asarray(candidates,float); self.reference=np.asarray(reference,float)
        if self.candidates.ndim!=2 or self.candidates.shape[1]!=4 or self.reference.shape[1]!=4:
            raise ValueError('Frozen model requires four scaled features')
        if not np.isfinite(self.candidates).all() or not np.isfinite(self.reference).all():
            raise ValueError('Finite features required')
        self.ids=list(range(len(self.candidates))) if candidate_ids is None else list(candidate_ids)
        if len(self.ids)!=len(self.candidates) or len(set(self.ids))!=len(self.ids):raise ValueError('Unique IDs required')
        self.x=np.vstack([self.candidates,self.reference]);self.gates=make_gates(self.candidates,self.reference)[0]
        self.meter=meter;self.records=[];self.theta=None;self.base=None;self.fit_n=0;self.pending=None;self.fit_logs=[]

    def _valid(self):
        return [r for r in self.records if r['quality']=='valid' and r['monitor'] is not None]

    def _posterior(self):
        valid=self._valid()
        if self.theta is None:return None
        return predict(np.array(self.theta),self.x,[r['index'] for r in valid],
                       [r['monitor'] for r in valid],self.gates,meter=self.meter)

    def ask(self):
        if self.pending is not None:return json.loads(json.dumps(self.pending))
        paid=[r['index'] for r in self.records];available=[i for i in range(len(self.ids)) if i not in paid]
        if not available:raise StopIteration('Finite pool exhausted')
        p=self._posterior()
        if p is None:
            if not paid:scores=-np.linalg.norm(self.candidates-.5,axis=1)
            else:scores=np.sqrt(((self.candidates[:,None]-self.candidates[paid][None])**2).sum(2)).min(1)
            scores[paid]=-np.inf;j=int(np.argmax(scores));selector='feature_maximin_until_8_valid'
        else:
            scores=-abs(p['probability'][:len(self.ids)]-.5);scores[paid]=-np.inf;j=int(np.argmax(scores));selector='joint_probability_margin'
        before={'paid_ids':[r['id'] for r in self.records],'paid_observations':self.records,
                'theta':self.theta,'features_sha256':digest([self.candidates.tolist(),self.reference.tolist()]),
                'variance_kind':'latent_total_within_plus_between; observation=noise_added_once'}
        self.pending={'id':self.ids[j],'index':j,'selector':selector,'posterior_hash':digest(before),
                      'budget_before':len(self.records),'valid_before':len(self._valid()),
                      'mean':None if p is None else float(p['mean'][j]),
                      'latent_variance':None if p is None else float(p['variance'][j]),
                      'noise_variance':None if p is None else p['noise_variance'],
                      'within':None if p is None else float(p['within'][j]),
                      'between':None if p is None else float(p['between'][j]),
                      'variance_kind':before['variance_kind']}
        return json.loads(json.dumps(self.pending))

    def tell(self, candidate_id, monitor, *, quality='valid', cost=1.0, canonical_label=None):
        if self.pending is None or candidate_id!=self.pending['id']:raise ValueError('Only outstanding paid ID can be told')
        if quality not in ('valid','missing','invalid'):raise ValueError('Unknown quality')
        if not np.isfinite(cost) or cost<0:raise ValueError('Nonnegative finite cost required')
        if monitor is not None and not np.isfinite(monitor):raise ValueError('Use missing/invalid, not NaN')
        if quality=='valid' and monitor is None:raise ValueError('Valid requires monitor')
        record={'id':candidate_id,'index':self.pending['index'],'monitor':None if monitor is None else float(monitor),
                'quality':quality,'cost':float(cost),'canonical_label':canonical_label,'prequery':self.pending}
        self.records.append(record);self.pending=None
        valid=self._valid();n=len(valid)
        if n>=8 and (self.theta is None or n-self.fit_n>=4):
            xx=self.x[[r['index'] for r in valid]];y=np.array([r['monitor'] for r in valid])
            base,blog=learn_theta(xx,y,None if self.base is None else np.array(self.base),self.meter)
            theta,jlog=fit_theta(xx,y,self.gates[:,[r['index'] for r in valid]],base,
                                None if self.theta is None else np.array(self.theta),self.meter)
            self.base=base.tolist();self.theta=theta.tolist();self.fit_n=n
            self.fit_logs.append({'valid_n':n,'base':blog,'joint':jlog})
        return {'paid':len(self.records),'valid':n,'total_cost':sum(r['cost'] for r in self.records)}

    def snapshot(self):
        value={'version':1,'candidates':self.candidates.tolist(),'reference':self.reference.tolist(),'ids':self.ids,
               'records':self.records,'theta':self.theta,'base':self.base,'fit_n':self.fit_n,
               'pending':self.pending,'fit_logs':self.fit_logs}
        # Deep copy: snapshots cannot be mutated by later tell calls.
        return json.loads(json.dumps(value,allow_nan=False))

    @classmethod
    def restore(cls, state, meter=None):
        if state['version']!=1:raise ValueError('Unknown snapshot version')
        obj=cls(state['candidates'],state['reference'],state['ids'],meter)
        for key in ('records','theta','base','fit_n','pending','fit_logs'):
            setattr(obj,key,json.loads(json.dumps(state[key])))
        if len({r['id'] for r in obj.records})!=len(obj.records):raise ValueError('Duplicate paid record')
        return obj
