"""Frozen analytic worlds; evaluator-only hidden outcomes and difficult groups."""
import numpy as np
from scipy.special import ndtr
from v1_reference import Config

WORLDS=('informative','redundant','harmful','rare_negatives','locally_mixed','selected_fraction','missing_depth')
SEEDS=(5101,5102,5103,5104)
ARMS=('balanced_risk','probability_variance','balanced_margin')


def config():
    return Config(f_lengthscale=1.5,discrepancy_lengthscale=1.5)


def maximin(x,start):
    selected=[int(start)%len(x)];dist=np.sum((x-x[selected[0]])**2,axis=1)
    while len(selected)<len(x):
        dist[selected]=-np.inf;j=int(np.argmax(dist));selected.append(j)
        dist=np.minimum(dist,np.sum((x-x[j])**2,axis=1))
    return np.asarray(selected)


def make_world(name,seed):
    rng=np.random.default_rng(seed);nq,nt=24,96
    X=rng.uniform(-1,1,(nq+nt,4))
    # Unequal feature density. Space filling is not sampling from this density.
    if name=='selected_fraction':
        rare=rng.random(len(X))<.20
        X[:,0]=np.where(rare,rng.uniform(.35,1,len(X)),rng.uniform(-1,.1,len(X)))
    f=.7*X[:,0]+.2*X[:,1]-.1*X[:,2]+.1*X[:,3]+.25
    h=f.copy();tau=.25
    region=X[:,0]>.5
    eta=None
    if name=='redundant':
        f=np.full(len(X),.2);h=.8*X[:,1]-.2*X[:,2]+.2
    elif name=='harmful':h=-f
    elif name=='rare_negatives':
        region=(X[:,0]>.45)&(X[:,1]>-.1)
        f=np.where(region,.1,.6)+.05*X[:,2]
        h=np.where(region,-.15+.2*X[:,2],.55+.12*X[:,0]);tau=.18
    elif name=='locally_mixed':
        region=X[:,0]>.5
        f=np.where(region,.04,.6)+.02*X[:,2]
        eta=np.where(region,.55,.98)
    elif name not in ('informative','missing_depth','selected_fraction'):raise ValueError(name)
    if eta is None:eta=ndtr(h/tau)
    y=(rng.random(len(X))<eta).astype(int)
    z=f+rng.normal(0,.03,len(X))
    availability=.75 if name=='missing_depth' else 1.
    if availability<1:z[rng.random(len(X))>availability]=np.nan
    path=maximin(X[:nq],seed%nq)
    if name=='selected_fraction':
        # Deterministic covariate-only selection deliberately favors high x0.
        first=np.argsort(-X[:nq,0],kind='stable')[:6]
        path=np.r_[first,[j for j in path if j not in first]]
    return {'name':name,'seed':seed,'X_pool':X[:nq],'X_test':X[nq:],
            'eta_pool':eta[:nq],'eta_test':eta[nq:],'y_pool':y[:nq],'y_test':y[nq:],
            'z_pool':z[:nq],'z_test':z[nq:],'f_pool':f[:nq],'f_test':f[nq:],
            'region_pool':region[:nq],'region_test':region[nq:],'startup':path[:6],
            'response_availability':availability,'target':'uniform fixed feature-only candidate pool; held-out inputs independently generated'}


class PaidOracle:
    def __init__(self,y,z):self._y=np.asarray(y);self._z=np.asarray(z);self.revealed=[]
    def reveal(self,j):
        j=int(j)
        if j in self.revealed:raise ValueError('Duplicate charged query')
        self.revealed.append(j);return int(self._y[j]),float(self._z[j])


def evaluate(y,p,d,eta,interval,region):
    y=np.asarray(y);d=np.asarray(d,bool);pos=y==1;neg=~pos
    def mean(a,mask):return float(np.mean(a[mask])) if np.any(mask) else None
    sens=mean(d,pos);spec=mean(~d,neg)
    pc=np.clip(p,1e-12,1-1e-12)
    return {'BA':None if sens is None or spec is None else (sens+spec)/2,
            'declared_batch_loss':.5 if sens is None or spec is None else 1-(sens+spec)/2,
            'sensitivity':sens,'specificity':spec,'brier':float(np.mean((p-y)**2)),
            'log_loss':float(-np.mean(y*np.log(pc)+(1-y)*np.log1p(-pc))),
            'probability_MSE':float(np.mean((p-eta)**2)),
            'pi_90_coverage':float(np.mean((eta>=interval[0])&(eta<=interval[1]))),
            'pi_90_width':float(np.mean(interval[1]-interval[0])),
            'region_error':mean(d!=y,region),'region_positive_recall':mean(d,region&pos),
            'region_negative_recall':mean(~d,region&neg),'region_n':int(region.sum()),
            'region_positive_n':int((region&pos).sum()),'region_negative_n':int((region&neg).sum()),
            'n_positive':int(pos.sum()),'n_negative':int(neg.sum()),
            'TP':int((d&pos).sum()),'TN':int((~d&neg).sum()),'FP':int((d&neg).sum()),'FN':int((~d&pos).sum())}
