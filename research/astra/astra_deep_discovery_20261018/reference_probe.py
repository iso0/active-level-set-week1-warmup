"""Bounded diagnostic of the failed quadrature reference; no GP fits."""
import os
for k in ('OMP_NUM_THREADS','OPENBLAS_NUM_THREADS','MKL_NUM_THREADS','NUMEXPR_NUM_THREADS'):
    os.environ[k]='1'
from coordination import Slot,HERE,now
import ledger

with Slot() as slot:
    import numpy as np
    from scipy.integrate import quad
    from scipy.special import ndtr
    from scipy.stats import norm
    from threadpoolctl import threadpool_limits
    from acquisition import gaussian_error_reduction
    with threadpool_limits(1):
        rows=[]
        for a in (0.,.2,1.,3.,-1.):
            for rho in (.01,.2,.7,.99):
                fun=lambda z: norm.pdf(z)*ndtr(-abs(a+rho*z)/np.sqrt(1-rho*rho))
                cut=-a/rho
                old=quad(fun,-np.inf,cut,epsabs=2e-11)[0]+quad(fun,cut,np.inf,epsabs=2e-11)[0]
                points=sorted(set([-12.,0.,12.]+([cut] if -12<cut<12 else [])))
                stable=sum(quad(fun,l,h,epsabs=2e-12)[0] for l,h in zip(points[:-1],points[1:]))
                # A second independent representation integrates the derivative
                # of Bayes value over correlation, without calling Owen's T.
                integrand=lambda angle: np.exp(-a*a/(2*np.sin(angle)**2))/np.pi if angle else (1/np.pi if a==0 else 0.)
                value=quad(integrand,0,np.arcsin(rho),epsabs=2e-12)[0]
                approx=float(gaussian_error_reduction(a,rho*rho))
                rows.append({'a':a,'rho':rho,'old_future_risk':old,'bounded_future_risk':stable,
                             'bounded_gain':float(ndtr(-abs(a))-stable),'derivative_integral_gain':value,
                             'owen_gain':approx,'bounded_vs_derivative_error':abs(ndtr(-abs(a))-stable-value)})
        result={'utc':now().isoformat(),'rows':rows,'truncation_error_bound':float(2*ndtr(-12)),
                'GP_fits':0,'status':'diagnostic only','cases':len(rows)}
        ledger.atomic_json(HERE/'results'/'REFERENCE_FAILURE_DIAGNOSIS.json',result)
        ledger.event('REFERENCE_PROBE',None,'BOUNDED_QUADRATURE_DIAGNOSIS',{'cases':len(rows),'fits':0,'path':'results/REFERENCE_FAILURE_DIAGNOSIS.json'})
        print('max bounded/derivative error',max(r['bounded_vs_derivative_error'] for r in rows))
        print('max old/bounded risk error',max(abs(r['old_future_risk']-r['bounded_future_risk']) for r in rows))
