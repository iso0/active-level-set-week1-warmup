"""Future outputs enter only after ask; evaluator generator kept outside learner."""
import hashlib,json,time
import numpy as np
from control import ROOT,read,atomic,sha,now
from test_worlds import world,maximin,PaidOracle
from legacy_model import learn_theta
from joint_model import predict

def build(u,q,slot,Meter,metrics,save_npz):
    directory=ROOT/'data/test_v1'/u['id'];directory.mkdir(parents=True,exist_ok=True)
    parent_path=directory/'parent.json';world_path=directory/'world.npz'
    if parent_path.exists():
        parent=read(parent_path);assert parent['status']=='COMPLETE'
        assert sha(world_path)==parent['world_sha256']
        return parent_path,world_path
    w=world(u['seed'],u['family'],u['replicate'])
    if not world_path.exists():save_npz(world_path,**{k:v for k,v in w.items() if isinstance(v,np.ndarray)})
    else:
        with np.load(world_path) as h:
            assert np.array_equal(h['observed'],w['observed']) and np.array_equal(h['x'],w['x'])
    state=q.checkpoint(u['id']+'__path');paid=state.get('paid',[]);obs=state.get('observations',[])
    records=state.get('records',[]);queries=state.get('queries',[]);meter=Meter(q,u['id'])
    theta=np.array(state['theta']) if state.get('theta') is not None else None;theta_budget=state.get('theta_budget')
    oracle=PaidOracle(w,paid);x=w['x'];t0=time.process_time();wall=time.perf_counter()
    while len(paid)<8:
        j=maximin(x[:256],paid);obs.append(oracle.reveal(j));paid.append(j)
    for b in range(len(paid),25):
        slot.check();dd=np.asarray(paid);y=np.asarray(obs)
        fitlog=None
        if theta is None or b-theta_budget>=4:
            theta,fitlog=learn_theta(x[dd],y,theta,meter);theta_budget=b
        p=predict(theta,x,dd,y,None,meter=meter)
        if b%2==0:
            assert not any(r['budget']==b for r in records)
            records.append({'budget':b,'paid_ids':paid.copy(),'arms':{'strong':{'metrics':metrics(p['probability'][256:],p['mean'][256:],w),'diagnostics':p['diagnostics']}},'fit':fitlog})
        if b<24:
            if u['path']=='maximin':j=maximin(x[:256],paid)
            else:
                score=-abs(p['probability'][:256]-.5);score[dd]=-np.inf;j=int(np.argmax(score))
            before={'campaign_id':ROOT.name,'unit_id':u['id'],'budget_before':b,'paid_ids_before':paid.copy(),
                    'observations_before':obs.copy(),'query_id':j,'selector':u['path'],'theta_before':theta.tolist(),
                    'mean_before':float(p['mean'][j]),'latent_variance_before':float(p['variance'][j]),
                    'noise_variance_before':p['noise_variance'],'variance_contract':'latent_plus_observation_noise_once'}
            before['posterior_hash']=hashlib.sha256(json.dumps(before,sort_keys=True).encode()).hexdigest()
            atomic(directory/f'prequery_B{b:02d}.json',before)
            z=oracle.reveal(j);paid.append(j);obs.append(z)
            queries.append({**before,'observed':z})
        snap={'paid':paid,'observations':obs,'records':records,'queries':queries,'theta':theta.tolist(),'theta_budget':theta_budget,
              'cpu_seconds':state.get('cpu_seconds',0)+time.process_time()-t0,
              'wall_seconds':state.get('wall_seconds',0)+time.perf_counter()-wall,
              'used_counts':{k:state.get('used_counts',{}).get(k,0)+v for k,v in meter.used.items()}}
        q.checkpoint(u['id']+'__path',snap)
    parent={'id':u['id'],'status':'COMPLETE','utc':now().isoformat(),'family':u['family'],'seed':u['seed'],'path':u['path'],
            'world_sha256':sha(world_path),'world_hash':w['world_hash'],**snap}
    atomic(parent_path,parent);return parent_path,world_path
