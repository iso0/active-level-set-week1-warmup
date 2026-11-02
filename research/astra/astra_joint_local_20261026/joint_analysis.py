"""Frozen metric replay/paired analysis, loaded only by a claimed worker."""
import csv,json
from collections import defaultdict
import numpy as np
from control import ROOT,read,atomic,sha,now
ARMS=('strong','fixed_local','strong_extra','fixed_extra','joint','joint_trace')
LOCAL=('local_shift','small_island','rotated_local')
METRICS=('ba','positive_recall','negative_recall','regional_error','error','brier','log_loss','rmse','outside_error')

def independent_metrics(prob,mean,w):
    truth=w['latent'][256:]>=0;prediction=prob>=.5;r=w['region'][256:].astype(bool)
    tp=int(np.count_nonzero(prediction&truth));tn=int(np.count_nonzero((~prediction)&(~truth)))
    pos=int(truth.sum());neg=len(truth)-pos;cp=np.clip(prob,1e-12,1-1e-12)
    sensitivity=tp/pos if pos else None;specificity=tn/neg if neg else None
    return {'ba':(sensitivity+specificity)/2 if pos and neg else None,
      'positive_recall':sensitivity,'negative_recall':specificity,
      'regional_error':float(np.count_nonzero(prediction[r]!=truth[r])/r.sum()) if r.any() else None,
      'outside_error':float(np.count_nonzero(prediction[~r]!=truth[~r])/(~r).sum()) if (~r).any() else None,
      'error':float(np.count_nonzero(prediction!=truth)/len(truth)),
      'brier':float(np.dot(prob-truth,prob-truth)/len(truth)),
      'log_loss':float(-sum(np.log(cp[truth]))/len(truth)-sum(np.log(1-cp[~truth]))/len(truth)),
      'rmse':float(np.linalg.norm(mean-w['latent'][256:])/np.sqrt(len(truth)))}

def write_csv(path,rows):
    if not rows:return
    keys=list(dict.fromkeys(k for r in rows for k in r))
    with path.open('w',newline='',encoding='utf8') as h:
        w=csv.DictWriter(h,keys);w.writeheader();w.writerows(rows)

def run_unit(u,q,slot):
    freeze=read(ROOT/'FROZEN_DEV_V1.json');summary=q.summary();output=ROOT/'results/analysis_dev_v1';output.mkdir(parents=True,exist_ok=True)
    units=[];failed=[]
    with q.connect() as db:
        for r in db.execute("SELECT id,status,error FROM units WHERE phase='DEV_V1'"):
            if r['status']=='COMPLETE':units.append(read(ROOT/'results'/('unit__'+r['id']+'.json')))
            else:failed.append(dict(r))
    rows=[];curves=[];fitrows=[];max_metric_error=0.;pathchecks=[]
    for unit in units:
        slot.check();world_path=ROOT/unit['world_path'];assert sha(world_path)==unit['world_sha256']
        parent=read(ROOT/unit['parent_path']);assert sha(ROOT/unit['parent_path'])==unit['parent_sha256']
        assert unit['paid']==parent['paid'] and unit['observations']==parent['observations']
        with np.load(world_path) as z:w={k:z[k] for k in z.files}
        assert np.array_equal(w['latent']>=0,w['labels'])
        for rec in unit['records']:
            assert rec['paid_ids']==parent['paid'][:rec['budget']]
            p=ROOT/rec['predictions_file'];assert sha(p)==rec['predictions_sha256']
            with np.load(p) as arr:
                for arm in ARMS:
                    m=independent_metrics(arr[arm+'_probability'][256:],arr[arm+'_mean'][256:],w)
                    for key,value in m.items():
                        original=rec['arms'][arm]['metrics'][key]
                        assert (value is None)==(original is None)
                        if value is not None:
                            err=abs(value-original);max_metric_error=max(max_metric_error,err);assert err<1e-8
                    curves.append({'family':unit['family'],'seed':unit['seed'],'path':unit['path'],'arm':arm,'budget':rec['budget'],**m})
            for arm,fit in rec['fits'].items():
                fitrows.append({'family':unit['family'],'seed':unit['seed'],'path':unit['path'],'budget':rec['budget'],
                    'fit':arm,'starts':fit['starts'],'selected_success':fit['chosen_success'],
                    'failed_starts':sum(not v['success'] for v in fit.get('all_starts',[])) if 'all_starts' in fit else fit['starts']-fit['successes'],
                    'cpu_seconds':fit['cpu_seconds'],'cpu_target_covered':fit.get('cpu_target_covered'),
                    'cap_reached':fit.get('cap_reached',False),'objective':fit['nll']})
        budgets=np.array([r['budget'] for r in unit['records']]);assert np.array_equal(budgets,np.arange(8,25,2))
        for arm in ARMS:
            sr={'family':unit['family'],'seed':unit['seed'],'path':unit['path'],'arm':arm}
            for key in METRICS:
                vals=[r['arms'][arm]['metrics'][key] for r in unit['records']]
                sr[key+'_aulc']=float(np.trapezoid(vals,x=budgets)/16) if all(v is not None for v in vals) else None
            for target in (.90,.93,.95):
                ba=[r['arms'][arm]['metrics']['ba'] for r in unit['records']]
                confirmed=[int(budgets[j]) for j in range(1,len(budgets)) if ba[j] is not None and ba[j-1] is not None and ba[j]>=target and ba[j-1]>=target]
                sr[f'attained_{target:.2f}']=bool(confirmed);sr[f'confirmed_budget_{target:.2f}']=min(confirmed) if confirmed else None
                sr[f'burden_{target:.2f}']=min(confirmed) if confirmed else 25
                sr[f'kept_at24_{target:.2f}']=bool(confirmed and ba[-1]>=target)
            sr['fit_cpu_seconds']=sum(r['fit_cpu_seconds'][arm] for r in unit['records'])
            sr['prediction_cpu_seconds']=sum(r['prediction_cpu_seconds'][arm] for r in unit['records'])
            sr['cpu_seconds']=sr['fit_cpu_seconds']+sr['prediction_cpu_seconds']
            last=unit['records'][-1]['arms'][arm]['diagnostics'];theta=np.array(last['theta'])
            sr.update(null_weight_b24=last['null_weight'],noise_sd_b24=float(np.exp(theta[-1])),amplitude_b24=float(np.exp(theta[-2])),
                      min_length_b24=float(np.exp(theta[:4]).min()),max_length_b24=float(np.exp(theta[:4]).max()),
                      geometric_hits_b24=unit['records'][-1]['hits']['geometric'],
                      latent_positive_hits_b24=unit['records'][-1]['hits']['geometric_latent_positive'])
            rows.append(sr)
        pathchecks.append({'id':unit['id'],'paid_path_exact':True,'world_sha256':unit['world_sha256'],'parent_sha256':unit['parent_sha256']})
    lookup={(r['family'],r['seed'],r['path'],r['arm']):r for r in rows}
    families=sorted({r['family'] for r in rows});allworlds=sorted({(r['family'],r['seed']) for r in rows})
    def contrast(arm,control,key,which=None):
        which=set(families if which is None else which);groups=defaultdict(list);worlds=[]
        for fam,seed in allworlds:
            if fam not in which:continue
            vals=[]
            for panel in ('maximin','strong_margin'):
                a=lookup.get((fam,seed,panel,arm));b=lookup.get((fam,seed,panel,control))
                if a is not None and b is not None and a.get(key) is not None and b.get(key) is not None:vals.append(float(a[key])-float(b[key]))
            if len(vals)==2:
                delta=float(np.mean(vals));groups[fam].append(delta);worlds.append({'family':fam,'seed':seed,'delta':delta})
        if not groups:return {'mean':None,'worlds':0,'pointwise95':None}
        rng=np.random.default_rng(726261)
        boot=np.mean([np.mean(rng.choice(v,(2000,len(v)),replace=True),axis=1) for _,v in sorted(groups.items())],axis=0)
        return {'mean':float(np.mean([np.mean(v) for v in groups.values()])),
                'pointwise95':np.quantile(boot,[.025,.975]).tolist(),'worlds':len(worlds),'per_world':worlds}
    ctrls=[f for f in families if f not in LOCAL]
    screen={'local_ba_vs_strong_extra':contrast('joint','strong_extra','ba_aulc',LOCAL),
            'local_ba_vs_fixed_extra':contrast('joint','fixed_extra','ba_aulc',LOCAL),
            'local_ba_vs_joint_trace':contrast('joint','joint_trace','ba_aulc',LOCAL),
            'local_regional_error_vs_strong_extra':contrast('joint','strong_extra','regional_error_aulc',LOCAL),
            'control_ba_vs_strong_extra':contrast('joint','strong_extra','ba_aulc',ctrls)}
    for family in ('smooth','outliers','correlated_corruption'):
        screen[family+'_ba_vs_strong_extra']=contrast('joint','strong_extra','ba_aulc',[family])
    complete=len(units)==64 and not failed
    gate=complete and all(screen[k]['mean'] is not None and screen[k]['mean']>=.005 for k in ('local_ba_vs_strong_extra','local_ba_vs_fixed_extra','local_ba_vs_joint_trace'))
    gate=gate and screen['local_regional_error_vs_strong_extra']['mean']<0
    gate=gate and all(screen[k]['mean']>-.01 for k in ('control_ba_vs_strong_extra','smooth_ba_vs_strong_extra','outliers_ba_vs_strong_extra','correlated_corruption_ba_vs_strong_extra'))
    comparisons={}
    for arm,control in [('joint','strong'),('joint','fixed_local'),('joint','strong_extra'),('joint','fixed_extra'),('joint','joint_trace'),('strong_extra','strong'),('fixed_extra','fixed_local')]:
        comparisons[arm+'__minus__'+control]={group:{key:contrast(arm,control,key,fs) for key in [m+'_aulc' for m in METRICS]+['burden_0.90','burden_0.93','burden_0.95','cpu_seconds']} for group,fs in [('all',families),('local',LOCAL),('controls',ctrls)]}
    famrows=[];overall=[]
    for family in [*families,'ALL']:
        for arm in ARMS:
            rr=[r for r in rows if r['arm']==arm and (family=='ALL' or r['family']==family)];out={'family':family,'arm':arm,'paths':len(rr)}
            for key in [m+'_aulc' for m in METRICS]+['cpu_seconds','fit_cpu_seconds','prediction_cpu_seconds','null_weight_b24','noise_sd_b24','amplitude_b24','min_length_b24','max_length_b24','latent_positive_hits_b24']:
                vals=[r[key] for r in rr if r[key] is not None];out[key]=float(np.mean(vals)) if vals else None
            for t in (.90,.93,.95):
                out[f'attained_{t:.2f}']=sum(r[f'attained_{t:.2f}'] for r in rr)
                out[f'burden_{t:.2f}']=float(np.mean([r[f'burden_{t:.2f}'] for r in rr])) if rr else None
            famrows.append(out)
            if family=='ALL':overall.append(out)
    write_csv(output/'PER_WORLD_PATH_MODEL.csv',rows);write_csv(output/'PER_BUDGET_METRICS.csv',curves)
    write_csv(output/'OPTIMIZATION.csv',fitrows);write_csv(output/'ALL_FAMILIES.csv',famrows)
    result={'status':'COMPLETE' if complete else 'INCOMPLETE','utc':now().isoformat(),'screen_pass':bool(gate),'screen':screen,
      'comparisons':comparisons,'all_families':famrows,'overall':overall,'complete_paths':len(units),'failed':failed,
      'worlds':len(allworlds),'metric_replay_max_error':max_metric_error,'path_integrity':pathchecks,
      'optimizer_selected_failures':sum(not r['selected_success'] for r in fitrows),
      'optimizer_start_failures':sum(r['failed_starts'] for r in fitrows),
      'extra_cpu_target_not_covered':sum(r['cpu_target_covered'] is False for r in fitrows),
      'total_execution_cpu_seconds':sum(r['cpu_seconds'] for r in units),
      'total_execution_wall_seconds':sum(r['wall_seconds'] for r in units),
      'peak_rss_bytes':max((r['peak_rss_bytes'] for r in units),default=0),'queue':summary,
      'inference':'Pointwise family-stratified whole-world bootstrap, four worlds per family; paths averaged inside world. Inspected DEV, no confirmation, no multiple-test guarantee.',
      'cost_note':'Strong_extra/fixed_extra get joint theta as assistance; displayed CPU excludes that borrowed optimization, add joint optimizer cost for standalone deployment. These are deliberately strong diagnostic controls.'}
    # Produce descriptive scientific figures; not a mechanism-selection input.
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    fig,axs=plt.subplots(2,2,figsize=(14,9),layout='constrained')
    for ax,key,title in zip(axs.flat,['ba_aulc','regional_error_aulc','log_loss_aulc','noise_sd_b24'],['Early balanced accuracy','Regional sign error','Log loss','Fitted noise SD at B24']):
        for arm in ARMS:
            yy=[next((r[key] for r in famrows if r['family']==f and r['arm']==arm),np.nan) for f in families]
            ax.plot(range(len(families)),yy,marker='o',label=arm,linewidth=1)
        ax.set_xticks(range(len(families)),families,rotation=35,ha='right');ax.set_title(title);ax.grid(alpha=.2)
    axs[0,0].legend(fontsize=8,ncol=2);fig.suptitle('Joint-local DEV — same64 paths /32 worlds; descriptive family means')
    fig.savefig(output/'ALL_FAMILIES.png',dpi=150);fig.savefig(output/'ALL_FAMILIES.pdf');plt.close(fig)
    lines=['# All families — frozen DEV v1','', '|Family|Model|BA-AULC|Positive recall|Negative recall|Regional error|Log loss|CPU/path s|','|---|---|---:|---:|---:|---:|---:|---:|']
    for r in famrows:
        vals=[r[k] for k in ['ba_aulc','positive_recall_aulc','negative_recall_aulc','regional_error_aulc','log_loss_aulc','cpu_seconds']]
        lines.append('|'+r['family']+'|'+r['arm']+'|'+'|'.join('undefined' if v is None else f'{v:.6f}' for v in vals)+'|')
    (output/'ALL_FAMILIES.md').write_text('\n'.join(lines)+'\n',encoding='utf8')
    atomic(output/'ANALYSIS.json',result);atomic(ROOT/'runtime/ANALYSIS_STATUS.json',{'status':'COMPLETE','utc':now().isoformat(),'result':'results/analysis_dev_v1/ANALYSIS.json','screen_pass':bool(gate)})
    return {'status':'COMPLETE','analysis_path':'results/analysis_dev_v1/ANALYSIS.json','sha256':sha(output/'ANALYSIS.json'),'screen_pass':bool(gate)}
