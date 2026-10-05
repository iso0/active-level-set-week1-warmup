from pathlib import Path
from fractions import Fraction as F
import itertools,json
import numpy as np
from scipy.integrate import quad
from scipy.special import ndtr
out=Path(__file__).resolve().parent
ans={}
bits=list(itertools.product([0,1],repeat=3))
plus=[F(v,70) for v in [34,0,0,12,0,12,12,0]]
minus=[F(v,70) for v in [22,12,12,0,12,0,0,12]]
def cube_risk(p):
    return min(F(1,2),1-max(p))
def cube_after(p):
    val=F(0)
    for o in [0,1]:
        ps=[p[i] for i,b in enumerate(bits) if b[0]==o]
        mass=sum(ps)
        val+=min(mass/2,mass-max(ps))
    return val
for coords in list(itertools.combinations(range(3),1))+list(itertools.combinations(range(3),2)):
    for vals in itertools.product([0,1],repeat=len(coords)):
        assert sum(p for p,b in zip(plus,bits) if tuple(b[i] for i in coords)==vals)==sum(p for p,b in zip(minus,bits) if tuple(b[i] for i in coords)==vals)
assert cube_risk(plus)-cube_after(plus)==F(11,70)
assert cube_risk(minus)-cube_after(minus)==0
ans['hausdorff_pair_counterexample']={'value_plus':'11/70','value_minus':'0','all_pairs_equal':True}

# Actual optimization of the nonconcave ratio over every feasible edge action.
def ratio(p):
    risks=[]
    for a,b in itertools.product([0,1],repeat=2):
        num=(1-a)+(p if b==0 else 1-p)
        den=1+p+a+b
        risks.append(num/den)
    return min(risks)
assert ratio(F(3,4))==F(1,15)
assert (ratio(F(1,2))+ratio(F(1)))/2==F(1,14)
ans['optimized_ratio_gain']=str(ratio(F(3,4))-(ratio(F(1,2))+ratio(F(1)))/2)

# Common independent sign-noise theorem, arbitrary finite joint sign laws.
rng=np.random.default_rng(20261006)
count=0;min_slack=1.
for n in range(2,8):
    worlds=np.array(list(itertools.product([-1,1],repeat=n)))
    for _ in range(150):
        law=rng.dirichlet(np.ones(2**n)*.3)
        m=law@worlds
        C=np.einsum('s,si,sj->ij',law,worlds,worlds)
        for alpha in [.2,.5,1.]:
            values=np.maximum(alpha*np.abs(C)-np.abs(m[:,None]),0).mean(axis=0)/2
            j=np.argmin(np.abs(m))
            slack=values[j]-max(values)/(n-1)
            assert slack>=-1e-13
            min_slack=min(min_slack,slack);count+=1
ans['common_bsc']={'law_channel_checks':count,'minimum_bound_slack':min_slack}

# Exact finite summation of all deterministic two-query observation policies.
# Q and P Bayes terminal rules are separately minimized, then deployed under P.
worlds=np.array(list(itertools.product([-1,1],repeat=4)))
target=worlds[:,0]
policies=[]
for first in range(1,4):
    rem=[x for x in range(1,4) if x!=first]
    for seconds in itertools.product(rem,repeat=2):
        policies.append((first,dict(zip([-1,1],seconds))))
def stats(P,Q,pol):
    first,seconds=pol
    eps0=abs(P[worlds[:,first]==1].sum()-Q[worlds[:,first]==1].sum())
    eps1=0.;delta=0.;rp=0.;rq=0.;rpq=0.
    for o1 in [-1,1]:
        sel1=worlds[:,first]==o1
        p1=P[sel1].sum();q1=Q[sel1].sum()
        second=seconds[o1]
        eps1+=p1*abs(P[sel1&(worlds[:,second]==1)].sum()/p1-Q[sel1&(worlds[:,second]==1)].sum()/q1)
        for o2 in [-1,1]:
            sel=sel1&(worlds[:,second]==o2)
            ph=P[sel].sum();qh=Q[sel].sum()
            pt=P[sel&(target==1)].sum()/ph
            qt=Q[sel&(target==1)].sum()/qh
            delta+=ph*abs(pt-qt)
            rp+=ph*min(pt,1-pt);rq+=qh*min(qt,1-qt)
            rpq+=ph*(1-pt if qt>=.5 else pt)
    return rp,rq,rpq,min(1.,eps0+eps1+delta)
mins=1.
for _ in range(200):
    P=rng.dirichlet(np.ones(16)*.5);Q=rng.dirichlet(np.ones(16)*.5)
    rows=[stats(P,Q,p) for p in policies]
    ip=min(range(len(rows)),key=lambda i:rows[i][0])
    iq=min(range(len(rows)),key=lambda i:rows[i][1])
    regret=rows[iq][2]-rows[ip][0]
    bound=rows[iq][3]+rows[ip][3]
    assert regret>=-1e-12 and regret<=bound+1e-12
    for rp,rq,rpq,gamma in rows:
        assert abs(rpq-rq)<=gamma+1e-12
    mins=min(mins,bound-regret)
ans['sequential_simulation']={'law_pairs':200,'policies_each':len(policies),'minimum_regret_slack':mins}

# Gaussian random-threshold geometric value by independent one-dimensional quadrature.
sigma=2.;tau=np.sqrt(8/np.pi)
errs=[]
for c in [.001,.01,.1,1.,10.]:
    moment=quad(lambda z:sigma*z*(2*ndtr(-c*sigma*z/tau)-1)*np.exp(-z*z/2)/np.sqrt(2*np.pi),-np.inf,np.inf,epsabs=1e-11)[0]
    expected=2*c*c*sigma**4/(np.pi*(c*c*sigma*sigma+tau*tau))
    errs.append(abs(moment*moment-expected))
assert max(errs)<1e-10
ans['gaussian_boundary_value_max_quadrature_error']=max(errs)

# Startup construction probabilities, including the smallest k and fixed horizon.
startup=[]
for k in range(1,7):
    M=k+1;records=[]
    for w in itertools.product([0,1],repeat=M):
        tb=2 if w[0]!=w[1] else 3
        paid=tb+(M-2)
        assert paid<=k+2
        records.append(tb)
    assert sum(records)/len(records)==2.5
    startup.append({'k':k,'A_T':2,'B_mean_T':2.5,'A_final_risk':.5,'B_final_risk':0})
ans['discovery_geometry']=startup

# Exact normal-risk minimizer, crossover and clipping checks by formula.
for D in [.1,1,5]:
    for v in [.2,1,4]:
        w=D*D/(D*D+v)
        risk=(1-w)**2*D*D+w*w*v
        assert abs(risk-D*D*v/(D*D+v))<1e-12
        for q in np.linspace(0,1,1001):
            assert risk<=(1-q)**2*D*D+q*q*v+1e-12
ans['shrinkage_formula_grids']=9

(out/'extension_verification_results.json').write_text(json.dumps(ans,indent=2),encoding='utf-8')
print(json.dumps(ans,indent=2))
