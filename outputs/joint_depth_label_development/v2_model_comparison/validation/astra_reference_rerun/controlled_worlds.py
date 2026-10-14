"""Frozen synthetic generators. No selection of worlds by model performance."""
import numpy as np
from scipy.special import ndtr
from v1_reference import Config, matern32

WORLDS=("informative_depth","redundant_depth","local_contradiction","harmful_bridge",
        "uncertain_threshold","zero_paid_negatives","one_paid_negative",
        "two_paid_negatives","missing_response","model_generated")
ARMS=("V2_EP_mixture","V1_Laplace","Binary_V2_EP","Binary_V1_Laplace","rho1_EP")


def maximin(X,start=0):
    chosen=[int(start)%len(X)]
    d=np.sum((X-X[chosen[0]])**2,axis=1)
    d[chosen[0]]=-np.inf
    while len(chosen)<len(X):
        j=int(np.argmax(d));chosen.append(j)
        d=np.minimum(d,np.sum((X-X[j])**2,axis=1))
        d[chosen]=-np.inf
    return np.array(chosen)


def config(dim=4):
    ls=.5 if dim==1 else 1.5
    return Config(f_lengthscale=ls,discrepancy_lengthscale=ls)


def make_world(name,seed,pool_size=40,test_size=96):
    rng=np.random.default_rng(seed)
    X=rng.uniform(-1,1,(pool_size+test_size,4))
    pool=np.arange(pool_size);test=np.arange(pool_size,len(X))
    path=maximin(X[pool],seed%pool_size)
    f=.7*X[:,0]+.2*X[:,1]-.1*X[:,2]+.1*X[:,3]+.15
    h=f.copy();theta=0.;tau=.15
    if name=="redundant_depth":
        f=np.full(len(X),.15)
        h=.9*X[:,1]-.4*X[:,2]+.1*X[:,3]+.1
        tau=.20
    elif name=="local_contradiction":
        h=f-1.4*np.exp(-((X[:,0]-.45)**2+(X[:,1]-.2)**2)/.18)
    elif name=="harmful_bridge":
        h=-f
    elif name=="uncertain_threshold":
        theta=.25;h=f-theta
    elif name in ("zero_paid_negatives","one_paid_negative","two_paid_negatives"):
        f=.6+.1*X[:,0]
        h=.75-X[:,0]+.1*X[:,1]
        tau=.12
    elif name=="model_generated":
        c=config()
        k=matern32(X,X,c.f_amplitude,c.f_lengthscale)
        L=np.linalg.cholesky(k+1e-10*np.eye(len(X)))
        f=L@rng.normal(size=len(X))
        g=L@rng.normal(size=len(X))
        kd=matern32(X,X,c.discrepancy_amplitude,c.discrepancy_lengthscale)
        kd-=kd[:,pool].mean(1)[:,None]+kd[pool,:].mean(0)[None,:]-kd[np.ix_(pool,pool)].mean()
        eig,V=np.linalg.eigh((kd+kd.T)/2)
        delta=(V*np.sqrt(np.maximum(eig,0)))@rng.normal(size=len(X))
        theta=float(rng.normal(0,.35))
        h=.5*f+np.sqrt(.75)*g-theta+delta
    elif name not in ("informative_depth","missing_response"):
        raise ValueError(name)
    eta=ndtr(h/tau)
    y=(rng.uniform(size=len(X))<eta).astype(int)
    z=f+rng.normal(0,.03,len(X))
    note="Unconditioned generated outcomes"
    if name in ("zero_paid_negatives","one_paid_negative","two_paid_negatives"):
        number={"zero_paid_negatives":0,"one_paid_negative":1,"two_paid_negatives":2}[name]
        # Declared composition stress, not a population-representative sample.
        y[path[:16]]=1
        negative_ids=path[:8][np.argsort(X[path[:8],0])[-number:]] if number else []
        y[negative_ids]=0
        note=f"Paid prefixes conditioned by construction on {number} negatives; held-out outcomes unchanged"
    if name=="missing_response":
        z[np.arange(len(X))%3==0]=np.nan
    return {"name":name,"seed":seed,"X":X,"f":f,"eta":eta,"y":y,"z":z,
            "pool":pool,"test":test,"path":path,"theta":theta,"note":note}


def metrics(y,p,eta,interval):
    y=np.asarray(y);p=np.asarray(p)
    pred=p>=.5
    pos=y==1;neg=~pos
    sens=float(pred[pos].mean()) if pos.any() else None
    spec=float((~pred[neg]).mean()) if neg.any() else None
    pp=np.clip(p,1e-12,1-1e-12)
    return {"BA":(sens+spec)/2 if sens is not None and spec is not None else None,
            "specificity":spec,"sensitivity":sens,
            "Brier":float(np.mean((p-y)**2)),
            "log_loss":float(-np.mean(y*np.log(pp)+(1-y)*np.log1p(-pp))),
            "probability_MSE":float(np.mean((p-eta)**2)),
            "pi_90_coverage":float(np.mean((eta>=interval[0])&(eta<=interval[1]))),
            "pi_90_width":float(np.mean(interval[1]-interval[0])),
            "TP":int(np.sum(pred&pos)),"FN":int(np.sum(~pred&pos)),
            "TN":int(np.sum(~pred&neg)),"FP":int(np.sum(pred&neg)),
            "n_test_positive":int(pos.sum()),"n_test_negative":int(neg.sum())}
