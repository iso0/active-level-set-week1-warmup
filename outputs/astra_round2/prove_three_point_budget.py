"""Exact rational certificate audit for the three-point, two-query ratio."""
import itertools
import json
from fractions import Fraction as F
from pathlib import Path
import numpy as np
from scipy.optimize import linprog
worlds=list(itertools.product((0,1),repeat=3))
x=np.array(worlds)
def rows(j):
    groups=[[i for i in range(8) if worlds[i][j]==s] for s in (0,1)]
    result=[]
    for l in itertools.combinations(groups[0],2):
        for r in itertools.combinations(groups[1],2):
            result.append([int(i in l+r) for i in range(8)])
    return result
la,lb=rows(2),rows(1)
A=[[-v for v in row]+[1] for row in la]
A += [list(x[:,j])+[0] for j in range(3)]
A += [list(x[:,j]-x[:,2])+[0] for j in (0,1)]
rhs=[F(0)]*36+[F(1,2)]*3+[F(0)]*2
eq=[1]*8+[0]
certs=[]
for k,row in enumerate(lb):
    c=[4*row[i]+sum(worlds[i]) for i in range(8)]+[-5]
    sol=linprog(c,A_ub=np.array(A),b_ub=np.array(rhs,dtype=float),
                A_eq=[eq],b_eq=[1],bounds=(0,None),method="highs")
    assert sol.success
    y=[F(float(v)).limit_denominator(10000) for v in sol.ineqlin.marginals]
    lam=F(float(sol.eqlin.marginals[0])).limit_denominator(10000)
    assert all(v<=0 for v in y)
    assert all(sum(F(A[i][j])*y[i] for i in range(len(A)))+lam*eq[j]<=c[j]
               for j in range(9))
    bound=sum(v*w for v,w in zip(rhs,y))+lam
    assert bound>=0
    support={str(i+1):str(-v) for i,v in enumerate(y) if v}
    certs.append({"k":k+1,"lambda":str(lam),"minus_y":support,"bound":str(bound)})
dest=Path(__file__).with_name("three_point_budget_certificates.json")
dest.write_text(json.dumps({"world_order":worlds,"certificates":certs},indent=2))
for v in certs:
    terms=", ".join(key+":"+value for key,value in v["minus_y"].items())
    print(str(v["k"])+" & $"+v["lambda"]+"$ & $"+terms+"$ & $"+v["bound"]+r"$ \\")
print("All 36 dual certificates verified with exact rational arithmetic.")
