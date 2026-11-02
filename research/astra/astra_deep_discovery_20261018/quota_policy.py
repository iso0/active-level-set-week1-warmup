"""Prospectively registered equal-local-share controls; only paid own observations."""
import numpy as np
from policy import Policy as BasePolicy
from acquisition import sur_scores


class QuotaPolicy(BasePolicy):
    def __init__(self,features,startup,mode,seed):
        if mode not in ('quota_surprise','quota_no_surprise'):
            raise ValueError('unregistered quota control')
        self.control_arm=mode
        self.default_anchor=int(startup[-1])
        super().__init__(features,startup,'boundary_regional',seed)

    def ask(self,p):
        if self.step%2==0:
            return super().ask(p)
        if self.pending is not None or p.paid_count!=len(self.paid):
            raise RuntimeError('pending query or stale posterior')
        if self.episode and self.step-self.episode['born']>=12:
            self.episode=None
        ids=np.array([i for i in range(len(self.x)) if i not in self.paid],int)
        if not len(ids):
            raise StopIteration
        episode=self.episode if self.control_arm=='quota_surprise' else None
        anchor=episode['anchor'] if episode else self.default_anchor
        distance=np.linalg.norm(self.x[ids]-self.x[anchor],axis=1)
        local=ids[np.lexsort((ids,distance))[:12]]
        scores=sur_scores(p)
        i=int(local[np.argmax(scores[local])])
        ordered=np.sort(scores[ids]);top=float(ordered[-1])
        gap=float(ordered[-1]-ordered[-2]) if len(ordered)>1 else None
        choice={'paid_id':i,'reason':'local_quota_surprise' if episode else 'local_quota_default',
            'prequery_hash':p.digest(),'model_hash':p.model_hash,'paid_before':len(self.paid),
            'mean':p.mean[i].tolist(),'latent_cov':p.latent_cov[i].tolist(),
            'noise_cov':p.noise_cov[i].tolist(),'variance_kind':'latent plus separate observation noise',
            'model_weights':p.weights.tolist(),'best_score':top,'top_two_gap':gap,
            'primary_probability_before':float(p.probability[i]),
            'near_tie':gap is not None and gap<=max(1e-10,1e-3*abs(top)),
            'local_anchor':int(anchor),'local_candidate_count':len(local),
            'local_radius_actual':float(np.linalg.norm(self.x[local]-self.x[anchor],axis=1).max())}
        self.pending=(choice,p)
        return choice

    def tell(self,observation):
        event=super().tell(observation)
        if not event['reason'].startswith('local') and observation.values[0] is not None and observation.quality[0]:
            self.default_anchor=observation.paid_id
        if self.control_arm=='quota_no_surprise':
            event['counterfactual_boundary_trigger']=event['triggered']
            event['triggered']=False
            self.episode=None
        return event
