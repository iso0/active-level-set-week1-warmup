"""Prospective QMC accuracy choice on an analytical fixture, not scientific scores."""
import os
for k in ('OMP_NUM_THREADS','OPENBLAS_NUM_THREADS','MKL_NUM_THREADS','NUMEXPR_NUM_THREADS'):
    os.environ[k]='1'
from coordination import HERE,Slot,now
import ledger

with Slot() as slot:
    import numpy as np
    from scipy.stats import qmc
    from model import MixtureGP
    from acquisition import sur_scores
    from threadpoolctl import threadpool_limits
    with threadpool_limits(1):
        rng=np.random.default_rng(17731)
        x=rng.uniform(size=(7,4));q=rng.uniform(size=(9,4))
        y=[[float(v)] for v in np.sin(4*x[:,0])-.4]
        model=MixtureGP('mixture',1)
        ledger.reserve('reference',len(model.components),'QMC_REFINEMENT','prospective_reference')
        model.fit(x,y,list(range(7)))
        rows=[]
        sizes=(128,256,512,1024,2048)
        for seed in range(251018,251022):
            cloud=qmc.Sobol(4,scramble=True,seed=seed).random_base2(13)
            reference=sur_scores(model.snapshot(q,cloud))
            for n in sizes:
                score=sur_scores(model.snapshot(q,cloud[:n]))
                err=float(np.max(abs(score-reference)))
                regret=float(reference.max()-reference[score.argmax()])
                rows.append({'scramble':seed,'n':n,'scores':score.tolist(),
                    'reference_scores':reference.tolist(),'maximum_score_error':err,
                    'selected':int(score.argmax()),'reference_selected':int(reference.argmax()),
                    'reference_regret':regret,'accept':bool(err<=5e-4 and regret<=5e-4)})
        selected=next((n for n in sizes if all(r['accept'] for r in rows if r['n']==n)),None)
        result={'utc':now().isoformat(),'selected_reference_size':selected,'rows':rows,
            'criterion':'all four scrambles: maximum score error and reference regret <=5e-4',
            'scope':'analytical fixture only; no scientific DEV/TEST outcomes used',
            'fits':1,'component_solves':4,'cloud_evaluations':24}
        ledger.atomic_json(HERE/'results'/'QMC_REFINEMENT.json',result)
        ledger.event('QMC_REFINEMENT',None,'REFERENCE_RESULT',{'selected_n':selected,'path':'results/QMC_REFINEMENT.json'})
        print('Selected N:',selected)
        for n in sizes:
            rr=[r for r in rows if r['n']==n]
            print(n,'max error',max(r['maximum_score_error'] for r in rr),'max regret',max(r['reference_regret'] for r in rr))
