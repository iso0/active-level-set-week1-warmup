"""Predeclared slice figures and real-path replay; diagnostic fits are charged."""
import os
for k in ('OMP_NUM_THREADS','OPENBLAS_NUM_THREADS','MKL_NUM_THREADS','NUMEXPR_NUM_THREADS'):
    os.environ[k]='1'
import argparse
import gzip
import hashlib
import json
from pathlib import Path
import sys
from coordination import HERE,Slot,now
import ledger


def main(phase,prefix,source_dir,manifest_name,action):
    manifest=json.loads((HERE/manifest_name).read_text())
    source=Path(source_dir).resolve()
    for name in ('model.py','policy.py','acquisition.py','worlds.py'):
        if hashlib.sha256((source/name).read_bytes()).hexdigest()!=manifest['source_hashes'][name]:
            raise RuntimeError('historical scientific source mismatch '+name)
    sys.path.insert(0,str(source))
    with Slot() as slot:
        import numpy as np
        from model import MixtureGP
        from policy import Policy
        from worlds import World
        from threadpoolctl import threadpool_limits
        with threadpool_limits(1):
            dst=HERE/'results'/'analysis'/f'{prefix}{phase}'
            dst.mkdir(parents=True,exist_ok=True)
            rows=[]
            for file in sorted((HERE/'results'/phase).glob(prefix+'*r00*.json.gz')):
                with gzip.open(file,'rt',encoding='utf-8') as f:rows.append(json.load(f))
            index={(r['unit']['family'],r['unit']['model'],r['unit']['selector']):r for r in rows}
            def fit(world,ids,kind,tag):
                slot.check()
                model=MixtureGP(kind,world.channels)
                ledger.reserve('controlled',len(model.components),tag,'diagnostic_reconstruction')
                model.fit(world.x[ids],[list(world.pay(i).values) for i in ids],ids)
                return model
            if action=='replay':
                checks=[]
                for family in ('smooth','island_small_unseen','heavy_tail'):
                    replay_arms=[('mixture','regional'),('mixture','sur_global')]
                    if prefix=='v2__':
                        replay_arms += [('structure','boundary_regional'),('structure','sur_global')]
                    for kind,selector in replay_arms:
                        row=index[(family,kind,selector)];s=row['unit']
                        world=World(family,s['seed'],**manifest['world_sizes'])
                        paid=list(world.startup)
                        pol=Policy(world.x,paid,selector,s.get('policy_seed',s['seed']+171))
                        for step in range(8):
                            model=fit(world,paid,kind,'REPLAY__'+s['id'])
                            p=model.snapshot(world.x,world.ref_x)
                            ch=pol.ask(p);old=row['events'][step]
                            if ch['paid_id']!=old['paid_id'] or ch['prequery_hash']!=old['prequery_hash']:
                                raise AssertionError('exact historical replay differs '+s['id']+' step '+str(step))
                            ob=world.pay(ch['paid_id']);pol.tell(ob);paid.append(ob.paid_id)
                        checks.append({'id':s['id'],'adaptive_queries_replayed':8,'exact_ID_and_full_posterior_hash':True})
                ledger.atomic_json(dst/'PATH_REPLAY.json',{'utc':now().isoformat(),'checks':checks,'status':'PASS',
                    'fits':len(checks)*8,'scope':'first registered realizations, not selected for performance'})
                print('Real path replay PASS:',len(checks),'trajectories')
                return
            import matplotlib
            matplotlib.use('Agg')
            import matplotlib.pyplot as plt
            from matplotlib.lines import Line2D
            arms=[('simple','random'),('simple','regional'),('mixture','sur_global'),('mixture','regional')]
            if prefix=='v2__':
                arms=[('simple','random'),('simple','boundary_regional'),('structure','sur_global'),('structure','boundary_regional')]
            budget_list=[b for b in (16,40,64) if b<=manifest[phase.lower()]['budget']]
            grid=np.linspace(0,1,64);gx,gy=np.meshgrid(grid,grid)
            all_paths=[]
            for family in manifest['families']:
                row=index[(family,'mixture','regional')];s=row['unit']
                world=World(family,s['seed'],**manifest['world_sizes'])
                nuisance=world.center.copy() if family.startswith('island_') else np.full(4,.5)
                xx=np.tile(nuisance,(gx.size,1));xx[:,0]=gx.ravel();xx[:,1]=gy.ravel()
                truth=world._truth(xx)[0].reshape(gx.shape)
                fig,axes=plt.subplots(len(arms),len(budget_list),figsize=(4.1*len(budget_list),12),squeeze=False)
                for a,(kind,selector) in enumerate(arms):
                    r=index[(family,kind,selector)]
                    for c,b in enumerate(budget_list):
                        paid=r['paid_ids'][:b];model=fit(world,paid,kind,'SLICE__'+r['unit']['id'])
                        _,_,prob=model.predict(xx);prob=prob.reshape(gx.shape)
                        ax=axes[a,c];im=ax.pcolormesh(gx,gy,prob,cmap='RdBu_r',vmin=0,vmax=1,shading='auto')
                        if truth.min()<0<truth.max():ax.contour(gx,gy,truth,levels=[0],colors='black',linewidths=1.5)
                        if prob.min()<.5<prob.max():ax.contour(gx,gy,prob,levels=[.5],colors='#f1ce40',linewidths=1.5)
                        ax.scatter(world.x[paid,0],world.x[paid,1],s=12,facecolors='none',edgecolors='white',linewidths=.7)
                        ax.set_title(kind+'/'+selector+'; B'+str(b),fontsize=9)
                        ax.set_xlabel('x0');ax.set_ylabel('x1');ax.set_aspect('equal')
                fig.suptitle(f'{phase} {family}, first registered realization\nSlice nuisance coordinates fixed; white paid points are projections from 4D',fontsize=11)
                fig.legend(handles=[Line2D([0],[0],color='black',label='True f=0'),Line2D([0],[0],color='#c4a000',label='Estimated p=.5')],loc='lower center',ncol=2)
                fig.tight_layout(rect=(0,.035,1,.95))
                file=dst/('slice_'+family+'.png');fig.savefig(file,dpi=140);plt.close(fig)
                all_paths.append(str(file.relative_to(HERE)))
            ledger.atomic_json(dst/'SLICE_MANIFEST.json',{'utc':now().isoformat(),'figures':all_paths,
                'source_manifest':manifest_name,'note':'Slices illustrate; aggregate 4D evaluator determines claims.'})
            print('Slice figures:',len(all_paths))


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--phase',choices=['DEV','TEST'],required=True)
    p.add_argument('--prefix',required=True);p.add_argument('--source-dir',required=True)
    p.add_argument('--manifest',required=True);p.add_argument('--action',choices=['slices','replay'],required=True)
    p.add_argument('--threads',choices=[1],type=int,required=True)
    a=p.parse_args();main(a.phase,a.prefix,a.source_dir,a.manifest,a.action)
