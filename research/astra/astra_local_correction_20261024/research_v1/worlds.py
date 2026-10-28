"""Evaluator/oracle only. Parameters and future outputs never enter model inputs."""
import hashlib
import numpy as np

FAMILIES=('smooth','local_shift','small_island','rotated_local','rare_negative','heteroskedastic','outliers','correlated_corruption')

def world(seed,family):
    rng=np.random.default_rng(seed);x=rng.uniform(size=(1024,4))
    direction=rng.normal(size=4);direction/=np.linalg.norm(direction)
    h=(x-.5)@direction
    background=1.7*h+.16*np.sin(2*np.pi*x[:,1])+.12*np.cos(2*np.pi*x[:,3])
    center=rng.uniform(.25,.75,size=4);delta=x-center
    widths=np.array([.20,.25,.48,.48]);rotation=np.eye(4)
    if family=='rotated_local':rotation=np.linalg.qr(rng.normal(size=(4,4)))[0];widths=np.array([.12,.32,.50,.50])
    if family=='small_island':widths=np.array([.18,.22,.30,.46])
    distance2=np.sum((delta@rotation/widths)**2,axis=1);bump=np.exp(-.5*distance2)
    local=family in ('local_shift','small_island','rotated_local')
    if family=='small_island':background=-.60+.24*h
    elif family=='rare_negative':background+=.65
    else:background+=rng.uniform(-.18,.18)
    f=background+(1.6*bump if local else 0.)
    sd=np.full(len(x),.06)
    if family=='heteroskedastic':sd+=.35*(x[:,0]>.65)
    noise=rng.normal(size=len(x))*sd
    if family=='outliers':noise+=rng.normal(size=len(x))*1.4*(rng.uniform(size=len(x))<.08)
    corruption=1.6*bump if family=='correlated_corruption' else 0.
    z=f+noise+corruption
    region=bump>.35
    return {'x':x,'latent':f,'observed':z,'labels':f>=0,'region':region,'noise_sd':sd,
            'family':family,'seed':seed,'center':center,'widths':widths,'rotation':rotation,
            'world_hash':hashlib.sha256(x.tobytes()+f.tobytes()+z.tobytes()).hexdigest()}

def maximin(x,paid):
    if not paid:return int(np.argmin(np.sum((x-.5)**2,axis=1)))
    d=np.sum((x[:,None]-x[np.asarray(paid)][None,:])**2,axis=2).min(1)
    d[np.asarray(paid)]=-np.inf
    return int(np.argmax(d))

class PaidOracle:
    def __init__(self,world,paid=()):self._world=world;self.paid=list(paid)
    def reveal(self,index):
        assert 0<=index<256 and index not in self.paid
        self.paid.append(int(index));return float(self._world['observed'][index])
