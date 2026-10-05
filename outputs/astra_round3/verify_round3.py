"""Read-only Week 16 audit and independent finite-law checks. Writes only beside this script."""
from pathlib import Path
from fractions import Fraction as F
import json, hashlib, itertools
import numpy as np
import pandas as pd
from scipy.special import ndtr, logit
from scipy.integrate import quad

OUT=Path(__file__).resolve().parent
REPO=Path(r'C:\Users\ozgur\Documents\thesis')
ROOT=REPO/'outputs/week16_theory_meets_data'
results={}
s=pd.read_csv(ROOT/'headroom/states.csv')
d=pd.read_csv(ROOT/'headroom/decoy_sd.csv')
v=pd.read_csv(ROOT/'validation/peer_validation.csv')
a=pd.read_csv(ROOT/'laplace_audit/synthetic_paths.csv')
phys=s[s.family.isin(['dev','curvedMono','rough']) & ~s.saturated_ref]
results['states']={'all':len(s),'physics_nonsaturated':len(phys),'median_ratio':float(phys.r_model_ref.median()),'saturated':s.loc[s.saturated_ref,['cell','budget']].to_dict('records')}
rows=[]
for family,g in s.groupby('family'):
    H=g['H|Vref|Vt_ham_ref']; A=g['A|Vref|Vt_ham_ref']
    rows.append({'family':family,'states':len(g),'median_r_model':g.r_model_ref.median(),'sumA_over_sumH':A.sum()/H.sum(),'mean_A_errors400':400*A.mean(),'mean_H_errors400':400*H.mean(),'median_rank':g['rho|Vref|Vt_ham_ref'].median()})
pd.DataFrame(rows).to_csv(OUT/'independent_week16_summary.csv',index=False)
results['families']=rows
results['validation']={'states':len(v),'median_candidate_martingale_gap':v.martingale_gap_median.median(),'max_state_median_martingale_gap':v.martingale_gap_median.max(),'max_candidate_martingale_gap':v.martingale_gap_max.max(),'states_negative_majority':int((v.vsur_negative_share>.5).sum()),'median_rank_peer_vsur':v.spearman_peer_vsur.median()}
merged=d.merge(s[['cell','rep','budget','margin_p']],on=['cell','rep','budget'],validate='one_to_one')
tau=np.sqrt(8/np.pi)
def selfvalue(row):
    sd=row.s_margin
    mu=logit(np.clip(row.margin_p,1e-14,1-1e-14))*np.sqrt(1+np.pi*sd*sd/8)
    z0=-mu/sd
    def fn(z):
        return (2*ndtr((mu+sd*z)/tau)-1)*np.exp(-z*z/2)/np.sqrt(2*np.pi)
    c=quad(fn,z0,np.inf,epsabs=1e-10)[0]-quad(fn,-np.inf,z0,epsabs=1e-10)[0]
    m=2*ndtr(mu/sd)-1
    return max(0,(abs(c)-abs(m))/2)
merged['self_value']=merged.apply(selfvalue,axis=1)
merged['decoy']=merged.r_model_ref<.5
dec=merged.groupby(['family','decoy'])[['s_margin','rho_self_margin','self_value']].median().reset_index()
dec.to_csv(OUT/'independent_decoy_selfvalues.csv',index=False)
results['decoy_selfvalue']=dec.to_dict('records')
bad=a[a.base_fail_frac>0]
results['laplace']={'failed_paths':len(bad),'failed_cells':sorted(bad.cell.unique()),'other_base_failures':int((a.loc[~a.index.isin(bad.index),'base_fail_frac']>0).sum()),'corrected_means':bad.groupby('cell')[['margin_nsd_aulc_old','margin_nsd_aulc_fixed']].mean().to_dict('index'),'max_other_trace_difference':a.loc[~a.index.isin(bad.index),'max_abs_nsd_change'].max()}

# Every integer 2x2 law up to denominator 12, including degenerate observations.
count=0
for den in range(1,13):
    for x in range(den+1):
      for y in range(den-x+1):
       for z in range(den-x-y+1):
        w=den-x-y-z
        p=list(map(lambda n:F(n,den),[x,y,z,w])) # ++,+-,-+,--
        m=p[0]+p[1]-p[2]-p[3]; c=p[0]-p[1]-p[2]+p[3]
        direct=min(p[0],p[2])+min(p[1],p[3])
        assert direct==(1-max(abs(m),abs(c)))/2
        count+=1
results['binary_identity_exact_laws']=count

# Exact coherent counterexamples for Week15 plug-in edge and ratio risk.
worlds=[(0,0),(0,1),(1,0),(1,1)]
def risk(p,dice=False):
    q=[sum(pi*t[i] for pi,t in zip(p,worlds)) for i in [0,1]]
    pred=int((q[0]>F(1,2)) != (q[1]>F(1,2)))
    pc=p[1]+p[2]
    err=1-pc if pred else pc
    return err/(pc+pred) if dice else err
def after(p,dice=False):
    q=p[1]
    p0=[x/(1-q) if i!=1 else F(0) for i,x in enumerate(p)]
    return q*risk([F(0),F(1),F(0),F(0)],dice)+(1-q)*risk(p0,dice)
edge=[F(x,9) for x in [2,2,2,3]]
dice=[F(x,5) for x in [1,1,2,1]]
assert risk(edge)==F(4,9) and after(edge)==F(5,9)
assert risk(dice,True)==F(1,4) and after(dice,True)==F(4,15)
results['coherent_negative_scores']={'plugin_edge':str(risk(edge)-after(edge)),'plugin_dice':str(risk(dice,True)-after(dice,True)),'optimized_ratio_two_nonempty_edges':str(F(1,15)-F(1,14))}

# Random-moment perturbation theorem checked against exact binary decision enumeration.
rng=np.random.default_rng(20261005)
max_bound_ratio=0
for _ in range(2000):
    labels=np.array(list(itertools.product([-1,1],repeat=4))) # two targets, two observations
    P=rng.dirichlet(np.ones(16)); Q=rng.dirichlet(np.ones(16))
    mP=P@labels[:,:2]; mQ=Q@labels[:,:2]
    cP=np.einsum('s,si,sj->ij',P,labels[:,:2],labels[:,2:]); cQ=np.einsum('s,si,sj->ij',Q,labels[:,:2],labels[:,2:])
    DeltaQ=np.maximum(np.abs(cQ)-np.abs(mQ[:,None]),0).mean(axis=0)/2
    jQ=int(np.argmax(DeltaQ))
    terminalP=(1-np.maximum(np.abs(mP[:,None]),np.abs(cP))).mean(axis=0)/2
    jP=int(np.argmin(terminalP))
    decisions=np.where(mQ[:,None]+cQ[:,jQ,None]*np.array([1,-1])[None,:]>=0,1,-1)
    alpha=decisions.mean(axis=1); beta=(decisions[:,0]-decisions[:,1])/2
    terminalPQ=(1-alpha*mP-beta*cP[:,jQ]).mean()/2
    D=np.maximum(np.abs(mP[:,None]-mQ[:,None]),np.abs(cP-cQ)).mean(axis=0)
    bound=(D[jQ]+D[jP])/2
    regret=terminalPQ-terminalP[jP]
    assert regret>=-1e-12 and regret<=bound+1e-12
    max_bound_ratio=max(max_bound_ratio,regret/bound)
results['moment_bound']={'random_laws':2000,'max_regret_over_bound':max_bound_ratio}

# Sequential parity: all first/second joint moments agree but two observations identify target only in P.
eps=F(1,10)
def parity_law(independent):
    law={}
    for aa,bb,tt,ee in itertools.product([-1,1],repeat=4):
        if not independent and tt!=aa*bb: continue
        prob=(F(1,8) if independent else F(1,4))*(F(1,2)+eps if ee==1 else F(1,2)-eps)
        key=(tt,aa,bb,tt*ee)
        law[key]=law.get(key,F(0))+prob
    return law
P=parity_law(False); Q=parity_law(True)
for subset in itertools.chain(itertools.combinations(range(4),1),itertools.combinations(range(4),2)):
    for signs in itertools.product([-1,1],repeat=len(subset)):
        pp=sum(pr for x,pr in P.items() if tuple(x[i] for i in subset)==signs)
        qq=sum(pr for x,pr in Q.items() if tuple(x[i] for i in subset)==signs)
        assert pp==qq
results['parity']={'pairwise_laws_identical':True,'Q_greedy_gain':str(eps),'P_opt_gain':'1/2','ratio':str(2*eps)}

# Ranking inversion bound, exhaustive binary sequences through length 10.
nseq=0
for n in range(1,11):
    for y in itertools.product([0,1],repeat=n):
        r=sum(y)
        if not r: continue
        D=y.index(1)+1
        V=sum(1 for i in range(n) for j in range(i+1,n) if y[i]==0 and y[j]==1)
        assert D<=1+V//r
        nseq+=1
results['ranking_exact_sequences']=nseq

source_paths=[REPO/'src'/x for x in ['week16_peer.py','week16_headroom.py','week16_cells.py','week16_validate.py','week16_calibration.py','week16_real.py','week15_ebr.py']]+[ROOT/x for x in ['WEEK16_REPORT.md','THEORY_WEEK16.md','ERRATUM_LAPLACE.md','headroom/states.csv','headroom/decoy_sd.csv','validation/peer_validation.csv','laplace_audit/synthetic_paths.csv']]
results['source_sha256']={str(p):hashlib.sha256(p.read_bytes()).hexdigest() for p in source_paths}
(OUT/'verification_results.json').write_text(json.dumps(results,indent=2,allow_nan=False),encoding='utf-8')
print(json.dumps({k:val for k,val in results.items() if k not in ['source_sha256','decoy_selfvalue']},indent=2))
print(dec.to_string(index=False))
