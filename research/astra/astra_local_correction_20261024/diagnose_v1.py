"""Post-pilot cached geometry/weight diagnosis; no model fits or new selection."""
import argparse
import json
from control import ROOT,atomic,now,read
from resources import Slot

def main():
    with Slot():
        import numpy as np
        from research_v1.model import compact_distance
        rows=[]
        for path in sorted((ROOT/'results').glob('unit__dev_v1_*.json')):
            r=read(path)
            if 'records' not in r:continue
            with np.load(ROOT/'results/dev_v1'/r['id']/'world.npz') as z:w={k:z[k] for k in z.files}
            last=r['records'][-1];paid=np.array(last['paid_ids']);local=w['region'][256:]
            d=np.linalg.norm(w['x'][256:][local,None]-w['x'][paid][None,:],axis=2)
            dg=last['arms']['gated']['diagnostics'];weights=np.array(dg['weights'][1:])
            centers=np.random.default_rng(91612).choice(256,32,replace=False)
            gates=np.array([np.exp(-np.sum((w['x']-w['x'][j])**2,axis=1)/(2*(rad/2)**2)) for rad in (.45,.9) for j in centers])
            eigen_ranks=[]
            for ix,a in enumerate(gates):
                rad=(.45,.9)[ix//32];dist=np.linalg.norm(w['x'][paid,None]-w['x'][paid][None,:],axis=2)
                kk=.36*a[paid,None]*a[None,paid]*compact_distance(dist,rad)
                eigen_ranks.append(float(np.trace(kk)**2/max(np.sum(kk*kk),1e-30)))
            with np.load(ROOT/last['predictions_file']) as p:
                strong=p['strong_probability'][256:];gated=p['gated_probability'][256:]
                change=(strong>=.5)!=(gated>=.5)
                mean_delta=float(np.mean(np.abs(p['gated_mean'][256:]-p['strong_mean'][256:])))
            rows.append({'id':r['id'],'family':r['family'],'path':r['path'],'paid_region_hits':last['paid_region_hits'],
                'gate_weight':float(weights.sum()),'max_compact_corr_regional_mean_r045':float(compact_distance(d,.45).max(1).mean()),
                'max_compact_corr_regional_mean_r09':float(compact_distance(d,.9).max(1).mean()),
                'posterior_weighted_effective_rank':float(weights@eigen_ranks/max(weights.sum(),1e-30)),
                'mean_absolute_latent_mean_change':mean_delta,'classification_changed_fraction':float(change.mean()),
                'regional_classification_changed_fraction':float(change[local].mean()),
                'noise_sd':float(np.exp(dg['theta'][-1]))})
        summaries=[]
        for fam in dict.fromkeys(r['family'] for r in rows):
            rr=[r for r in rows if r['family']==fam]
            summaries.append({'family':fam,**{key:float(np.mean([r[key] for r in rr])) for key in rr[0] if key not in ('id','family','path')}})
        result={'utc':now().isoformat(),'scope':'POST-HOC EXPLORATORY cached geometry; no refit, new worlds or causal conclusion.',
                'per_path':rows,'families':summaries,'new_model_fits':0}
        atomic(ROOT/'results/analysis_dev_v1/GEOMETRY_DIAGNOSIS.json',result)
        print(json.dumps(summaries))

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--threads',type=int,choices=[1],required=True);p.parse_args();main()
