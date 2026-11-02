"""Evaluator/oracle only; generated after freeze, never imported by model."""
import hashlib
import numpy as np
FAMILIES=('radial_shift','radial_island','rotated_ridge','compact_plateau','twin_islands','annular_shell',
          'smooth','rare_negative','heteroskedastic','heavy_tail','outliers','correlated_corruption')
LOCAL=FAMILIES[:6]
def world(seed,family,replicate):
    rng=np.random.default_rng(seed);x=rng.uniform(size=(1024,4))
    direction=rng.normal(size=4);direction/=np.linalg.norm(direction)
    h=(x-.5)@direction
    background=1.7*h+.16*np.sin(2*np.pi*x[:,1])+.12*np.cos(2*np.pi*x[:,3])+rng.uniform(-.18,.18)
    center=rng.uniform(.25,.75,size=4);rotation=np.linalg.qr(rng.normal(size=(4,4)))[0]
    scale=(.75,1.,1.25)[replicate%3];sign=1. if replicate%2==0 else -1.
    amplitude=rng.uniform(1.1,1.9)
    widths=scale*np.array([.18,.22,.30,.46]);v=(x-center)@rotation/widths
    radial=np.exp(-.5*np.sum(v*v,axis=1));shape=radial.copy()
    if family in ('radial_shift','correlated_corruption'):
        widths=scale*np.array([.20,.25,.48,.48]);v=(x-center)/widths;shape=np.exp(-.5*np.sum(v*v,axis=1))
    elif family=='rotated_ridge':
        widths=scale*np.array([.09,.22,.60,.65]);v=(x-center)@rotation/widths
        shape=np.exp(-.5*(v[:,0]**2+v[:,1]**2)-.15*(v[:,2]**4+v[:,3]**4))
    elif family=='compact_plateau':
        shape=np.exp(-.5*np.sum(np.abs(v)**6,axis=1))
    elif family=='twin_islands':
        widths=scale*np.array([.14,.18,.28,.40])
        c2=np.clip(center+.28*rotation[:,0],.15,.85)
        v1=(x-center)@rotation/widths;v2=(x-c2)@rotation/widths
        shape=np.maximum(np.exp(-.5*np.sum(v1*v1,axis=1)),.85*np.exp(-.5*np.sum(v2*v2,axis=1)))
    elif family=='annular_shell':
        radial_distance=np.sqrt(np.sum(v*v,axis=1))
        shape=np.exp(-.5*((radial_distance-1.1)/.25)**2)
    if family in ('radial_island','compact_plateau','twin_islands','annular_shell'):
        background=sign*(-.60+.24*h)
    elif family=='rare_negative':background+=.65
    f=background+(sign*amplitude*shape if family in LOCAL else 0.)
    sd=np.full(len(x),.06)
    if family=='heteroskedastic':sd+=.35*(x[:,0]>.65)
    noise=rng.normal(size=len(x))*sd
    if family=='heavy_tail':noise=rng.standard_t(2.5,size=len(x))*.12
    if family=='outliers':noise+=rng.normal(size=len(x))*1.4*(rng.uniform(size=len(x))<.08)
    corruption=sign*amplitude*shape if family=='correlated_corruption' else np.zeros(len(x))
    z=f+noise+corruption;region=shape>.35
    return {'x':x,'latent':f,'observed':z,'labels':f>=0,'region':region,'noise_sd':sd,
        'background':background,'shape':shape,'corruption':corruption,'center':center,'widths':widths,
        'rotation':rotation,'sign':np.array(sign),'amplitude':np.array(amplitude),
        'family':family,'seed':seed,'replicate':replicate,
        'world_hash':hashlib.sha256(x.tobytes()+f.tobytes()+z.tobytes()).hexdigest()}

def maximin(x,paid):
    if not paid:return int(np.argmin(np.sum((x-.5)**2,axis=1)))
    distance=np.sum((x[:,None]-x[np.asarray(paid)][None,:])**2,axis=2).min(1)
    distance[np.asarray(paid)]=-np.inf;return int(np.argmax(distance))

class PaidOracle:
    def __init__(self,w,paid=()):self._values=w['observed'][:256];self.paid=list(paid)
    def reveal(self,index):
        assert 0<=index<256 and index not in self.paid
        self.paid.append(int(index));return float(self._values[index])
