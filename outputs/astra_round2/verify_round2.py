"""Scratch-only independent formula checks; never imports the thesis repository."""
from fractions import Fraction as F
from itertools import product
from itertools import combinations
from pathlib import Path
import json
import math
import re
import numpy as np

def phi(x):
    k = x.numerator // x.denominator
    return 2*k*x-k*(k+1)

def rare_value(n, p):
    best = (F(1), 0, F(0), F(0))
    for k in range(1, n):
        def raw(t):
            u = (k+t)/2
            v = p*(k-t)/(2*(1-p))
            return 2*p*phi(u)+2*(1-p)*phi(v)-p*k*(k-1)
        breaks = {F(0), F(k)}
        for z in range(k+1):
            for t in (F(2*z-k), F(k)-2*(1-p)*z/p):
                if 0 <= t <= k:
                    breaks.add(t)
        base = sorted(breaks)
        for left, right in zip(base, base[1:]):
            a, b = raw(left), raw(right)
            for x, y in ((a,b), (a-p*(k-1)*left,b-p*(k-1)*right)):
                if x != y:
                    t = left-x*(right-left)/(y-x)
                    if left <= t <= right:
                        breaks.add(t)
        for t in breaks:
            ell = max(F(0), raw(t))
            if ell <= p*(k-1)*t:
                value = (n*p+2*p*t+ell)/(n*p*(1+t))
                if value < best[0]:
                    best = (value,k,t,ell)
    return best

def branch_risk(spins, law, j, prediction):
    return sum(law[a] * np.mean(prediction[:, int(spins[a,j] == 1)]
                                != spins[a]) for a in range(len(law)))

rng = np.random.default_rng(20261004)
max_identity_error = 0.
max_regret_violation = 0.
max_bsc_violation = 0.
for n in range(2,7):
    x = np.array(list(product((-1.,1.), repeat=n)))
    for trial in range(300):
        p = rng.dirichlet(np.ones(len(x))*.4)
        q = rng.dirichlet(np.ones(len(x))*.4)
        mp,mq = p@x,q@x
        cp,cq = (x.T*p)@x,(x.T*q)@x
        fp = (1-np.maximum(abs(mp[:,None]),abs(cp))).mean(axis=0)/2
        fq = (1-np.maximum(abs(mq[:,None]),abs(cq))).mean(axis=0)/2
        actual = []
        for j in range(n):
            g = np.where(mq[:,None] + cq[:,j,None]*np.array([-1,1]) >= 0,1,-1)
            alpha = g.mean(axis=1)
            beta = (g[:,1]-g[:,0])/2
            formula = np.mean(1-alpha*mp-beta*cp[:,j])/2
            direct = branch_risk(x,p,j,g)
            max_identity_error = max(max_identity_error,abs(formula-direct))
            actual.append(direct)
        jq,jp = int(np.argmin(fq)),int(np.argmin(fp))
        d = np.maximum(abs(mp-mq)[:,None],abs(cp-cq)).mean(axis=0)
        violation = actual[jq]-fp[jp]-(d[jq]+d[jp])/2
        max_regret_violation=max(max_regret_violation,violation)
        eta=rng.random()
        gains=np.maximum(eta*abs(cp)-abs(mp[:,None]),0).mean(axis=0)/2
        margin=np.argmin(abs(mp))
        max_bsc_violation=max(max_bsc_violation,gains.max()/(n-1)-gains[margin])
assert max_identity_error < 1e-12
assert max_regret_violation < 1e-12
assert max_bsc_violation < 1e-12

rv=rare_value(136,F(3,34))
assert rv[0]==F(2798,86615)
k,t=rv[1],rv[2]
mu1=(k+t)/2
mu0=F(3,34)*(k-t)/(2*(1-F(3,34)))
leaf_pair=(F(3,34)*phi(mu1)+(1-F(3,34))*phi(mu0))/(k*(k-1))
assert leaf_pair==F(3,68)

balanced={}
for n in range(4,11):
    m=n-1
    a=max(z for z in range(math.isqrt(m)+1) if z%2==m%2)
    b=a+2
    prob=F(m-a*a,b*b-a*a)
    tau=(1-prob)*a+prob*b
    assert (1-prob)*a*a+prob*b*b==m
    value=F(n+2*tau,n*(1+tau))
    balanced[str(n)]=str(value)

def survival(k):
    return F(math.comb(124,k),math.comb(136,k)) if k<=124 else F(0)
quantiles={str(alpha):next(k for k in range(137) if survival(k)<=1-alpha)
           for alpha in (F(95,100),F(99,100))}
tex=Path(__file__).with_name("marginal_information_rounds_1_2.tex").read_text()
begins=re.findall(r"\\begin\{([^}]+)\}",tex)
ends=re.findall(r"\\end\{([^}]+)\}",tex)
assert sorted(begins)==sorted(ends), "Unbalanced environments"
labels=set(re.findall(r"\\label\{([^}]+)\}",tex))
refs=set(re.findall(r"\\(?:eqref|ref)\{([^}]+)\}",tex))
assert refs<=labels, refs-labels
assert tex.count(r"\[")==tex.count(r"\]")
worlds=np.array(list(product((0.,1.),repeat=3)))
constraints=np.vstack([np.ones(8),worlds.T])
rhs=np.array([1.,.1,.1,.25])
vertices=[]
for count in range(1,5):
    for ids in combinations(range(8),count):
        weights=np.linalg.lstsq(constraints[:,ids],rhs,rcond=None)[0]
        if min(weights)>-1e-10 and max(abs(constraints[:,ids]@weights-rhs))<1e-10:
            law=np.zeros(8)
            law[list(ids)]=np.maximum(weights,0)
            vertices.append(law)
vertices=np.unique(np.round(vertices,12),axis=0)
mix_rng=np.random.default_rng(151515)
mixtures=np.vstack([vertices,mix_rng.dirichlet(np.ones(len(vertices))*.05,
                                             size=50000)@vertices])
marginals=mixtures@worlds
joints=np.einsum('wi,wj,aw->aij',worlds,worlds,mixtures)
gain=np.maximum(2*joints-marginals[:,None,:],0).sum(axis=1)
twolevel_ratios=(gain@np.array([5/46,5/46,18/23]))/gain.max(axis=1)
assert twolevel_ratios.min()>=20/23-1e-10
result={
 "seed":20261004,"random_laws_checked":1500,
 "max_binary_identity_error":max_identity_error,
 "max_terminal_regret_violation":max_regret_violation,
 "max_common_BSC_bound_violation":max_bsc_violation,
 "rare_exact_value":str(rv[0]),"rare_value_float":float(rv[0]),
 "rare_K":k,"rare_t":str(t),"rare_L":str(rv[3]),
 "rare_mu1":str(mu1),"rare_mu0":str(mu0),"rare_leaf_pair":str(leaf_pair),
 "balanced_extremal_values":balanced,
 "rare_discovery_survival_9":float(survival(9)),
 "rare_discovery_survival_16":float(survival(16)),
 "discovery_quantiles":quantiles,
 "twolevel_vertices":len(vertices),"twolevel_laws_checked":len(mixtures),
 "twolevel_min_tested_ratio":float(twolevel_ratios.min()),
 "tex_static_checks":"PASS; not a compilation or visual-layout check"}
Path(__file__).with_name("verification_results.json").write_text(json.dumps(result,indent=2))
print(json.dumps(result,indent=2))
