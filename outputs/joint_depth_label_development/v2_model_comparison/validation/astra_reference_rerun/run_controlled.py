"""Resumable frozen V2 correctness/static/sequential runner; no SPH access."""
import os
for name in ("OMP_NUM_THREADS","OPENBLAS_NUM_THREADS","MKL_NUM_THREADS","NUMEXPR_NUM_THREADS"):
    os.environ[name]="1"
from pathlib import Path
import argparse, hashlib, json, pickle, platform, time, traceback
import numpy as np
import scipy
from scipy.special import ndtr, ndtri
from v1_reference import JointDepthLabelGP
from joint_model_v2 import JointModelV2
from controlled_worlds import WORLDS,ARMS,config,make_world,metrics

ROOT=Path(__file__).resolve().parent
CODE=("joint_model_v2.py","v1_reference.py","controlled_worlds.py",
      "run_controlled.py","reference_checks.py","SELECTION_RECORD_V2.json")


def clean(obj):
    if isinstance(obj,np.ndarray):return clean(obj.tolist())
    if isinstance(obj,np.generic):return clean(obj.item())
    if isinstance(obj,float) and not np.isfinite(obj):return None
    if isinstance(obj,dict):return {str(k):clean(v) for k,v in obj.items()}
    if isinstance(obj,(list,tuple)):return [clean(v) for v in obj]
    return obj


def save(path,obj):
    temp=path.with_suffix(path.suffix+".tmp")
    temp.write_text(json.dumps(clean(obj),indent=2,allow_nan=False),encoding="utf-8")
    temp.replace(path)


class V1Adapter:
    def __init__(self,ref,binary):
        self.obj=JointDepthLabelGP(ref,config())
        self.binary=binary
    def fit(self,X,y,z):
        self.obj.fit(X,y,z,use_response=not self.binary)
        self.diagnostics=dict(self.obj.diagnostics,component_solves=1,rho_weights=[1.],
                              fallback=False)
        return self
    def predict_proba(self,X):return self.obj.predict_proba(X)
    def probability_interval(self,X):
        q=self.obj.posterior(X)
        m=q["h_mean"];s=np.sqrt(np.maximum(np.diag(q["h_cov"]),0))
        return ndtr(np.array([m+ndtri(.05)*s,m+ndtri(.95)*s])/self.obj.config.probit_scale)


class Experiment:
    def __init__(self):
        self.hashes={n:hashlib.sha256((ROOT/n).read_bytes()).hexdigest() for n in CODE}
        self.fingerprint=hashlib.sha256(json.dumps(self.hashes,sort_keys=True).encode()).hexdigest()
        self.records=ROOT/"records";self.records.mkdir(exist_ok=True)
        self.checkpoints=ROOT/"checkpoints";self.checkpoints.mkdir(exist_ok=True)
        self.state_path=ROOT/"RUN_STATE.json"
        if self.state_path.exists():
            self.state=json.loads(self.state_path.read_text())
            if self.state["fingerprint"]!=self.fingerprint:
                raise RuntimeError("Source/manifest changed; preserve records and record a prospective amendment")
        else:
            correctness=json.loads((ROOT/"NUMERICAL_REFERENCES.json").read_text())
            self.state={"fingerprint":self.fingerprint,"source_sha256":self.hashes,
                        "requests":12,"component_solves":correctness["correctness_component_solves"],
                        "correctness_requests":12,
                        "correctness_component_solves":correctness["correctness_component_solves"],
                        "failures":0,"reference_checks":correctness["separately_counted_reference_evaluations"],
                        "environment":{"python":platform.python_version(),"numpy":np.__version__,
                                       "scipy":scipy.__version__},
                        "pending":[]}
            save(self.state_path,self.state)
        self.worlds={}

    def world(self,name,seed,pool_size=40):
        key=f"{name}_{seed}_{pool_size}"
        if key not in self.worlds:
            self.worlds[key]=make_world(name,seed,pool_size)
        return self.worlds[key]

    def fit(self,key,arm,w,paid):
        rp=self.records/(key+".json");cp=self.checkpoints/(key+".pkl")
        if rp.exists():
            rec=json.loads(rp.read_text())
            return (pickle.loads(cp.read_bytes()) if rec["status"]=="ok" else None),rec
        if key in self.state["pending"]:
            raise RuntimeError(f"Unfinished request {key}; explicit recovery amendment required")
        worst=6 if arm=="V2_EP_mixture" else 2 if arm in ("rho1_EP","Binary_V2_EP") else 1
        if self.state["component_solves"]+worst>600 or self.state["requests"]>=600:
            raise RuntimeError("Frozen computation ceiling reached")
        self.state["requests"]+=1;self.state["pending"].append(key)
        save(self.state_path,self.state)
        paid=np.array(paid,dtype=int)
        # Only these paid arrays cross the model boundary.
        Xp=w["X"][paid].copy();yp=w["y"][paid].copy();zp=w["z"][paid].copy()
        xr=w["X"][w["pool"]].copy()
        model=None;start=time.perf_counter()
        rec={"key":key,"arm":arm,"world":w["name"],"seed":w["seed"],
             "budget":len(paid),"paid_ids":paid,"y_paid":yp,"z_paid":zp}
        try:
            if arm=="V2_EP_mixture":
                model=JointModelV2(xr,config()).fit(Xp,yp,zp)
            elif arm=="rho1_EP":
                model=JointModelV2(xr,config(),rhos=(1.,)).fit(Xp,yp,zp)
            elif arm=="Binary_V2_EP":
                model=JointModelV2(xr,config()).fit(Xp,yp,zp,use_response=False)
            else:
                model=V1Adapter(xr,arm=="Binary_V1_Laplace").fit(Xp,yp,zp)
            Xtest=w["X"][w["test"]]
            p=model.predict_proba(Xtest)
            ci=model.probability_interval(Xtest)
            if not np.isfinite(p).all() or not np.isfinite(ci).all():
                raise FloatingPointError("Nonfinite prediction")
            rec.update(status="ok",diagnostics=model.diagnostics,
                       predictions=p,intervals=ci,
                       paid_probabilities=model.predict_proba(Xp),
                       metrics=metrics(w["y"][w["test"]],p,w["eta"][w["test"]],ci))
            cp.write_bytes(pickle.dumps(model))
            count=model.diagnostics["component_solves"]
        except Exception as ex:
            count=getattr(model,"solve_count",worst)
            rec.update(status="failed",error=str(ex),traceback=traceback.format_exc())
            self.state["failures"]+=1
        rec["seconds"]=time.perf_counter()-start
        rec["component_solves_charged"]=count
        save(rp,rec)
        self.state["component_solves"]+=count
        self.state["pending"].remove(key)
        save(self.state_path,self.state)
        return model if rec["status"]=="ok" else None,clean(rec)

    def static(self):
        for name in WORLDS:
            for seed in (1301,1302):
                w=self.world(name,seed)
                for budget in (8,16):
                    paid=w["path"][:budget]
                    for arm in ARMS:
                        self.fit(f"static_{name}_{seed}_B{budget}_{arm}",arm,w,paid)
            print(f"static complete: {name}; components={self.state['component_solves']}",flush=True)
            self.collect()

    def sequential(self):
        for name in ("informative_depth","local_contradiction","harmful_bridge"):
            for seed in (2301,2302,2303):
                w=self.world(name,seed,24)
                for rule in ("paired","margin"):
                    paid=w["path"][:6].tolist()
                    for budget in range(6,11):
                        key=f"seq_{name}_{seed}_{rule}_B{budget}"
                        model,rec=self.fit(key,"V2_EP_mixture",w,paid)
                        if model is None:break
                        if budget==10:continue
                        qp=self.records/(key+"_query.json")
                        if qp.exists():
                            query=json.loads(qp.read_text())
                            if query["status"]!="ok":break
                            paid.append(query["selected"]);continue
                        candidates=np.array([i for i in w["pool"] if i not in paid])
                        Xc=w["X"][candidates]
                        t=time.perf_counter()
                        try:
                            if rule=="margin":
                                values=-abs(model.predict_proba(Xc)-.5)
                                chosen=int(np.argmax(values))
                                details={"score":values}
                            else:
                                low=model.acquisition(Xc,gh_order=15,cdf_order=48)
                                high=model.acquisition(Xc,gh_order=31,cdf_order=64)
                                error=float(np.max(abs(high["score"]-low["score"])))
                                values=high["score"]
                                ix=np.argsort(-values,kind="stable")
                                gap=float(values[ix[0]]-values[ix[1]])
                                tail=float(high["omitted_tail_bound"].max())
                                stable=gap>2*error+tail or (gap<=1e-8 and error<=1e-8)
                                if not stable:
                                    low=high
                                    high=model.acquisition(Xc,gh_order=63,cdf_order=96)
                                    error=float(np.max(abs(high["score"]-low["score"])))
                                    values=high["score"];ix=np.argsort(-values,kind="stable")
                                    gap=float(values[ix[0]]-values[ix[1]])
                                    stable=gap>2*error+float(high["omitted_tail_bound"].max()) or (gap<=1e-8 and error<=1e-8)
                                if not stable:
                                    raise RuntimeError(f"Unresolved acquisition ranking: gap={gap}, estimate={error}")
                                best=values.max()
                                chosen=int(np.flatnonzero(values>=best-1e-8)[0]) if gap<=1e-8 else int(np.argmax(values))
                                details=dict(high,quadrature_difference=error,top_gap=gap)
                            query={"status":"ok","selected":int(candidates[chosen]),
                                   "candidate_ids":candidates,"details":details,
                                   "seconds":time.perf_counter()-t}
                        except Exception as ex:
                            query={"status":"numerical_stop","error":str(ex),"seconds":time.perf_counter()-t}
                        save(qp,query)
                        if query["status"]!="ok":break
                        paid.append(query["selected"])
                print(f"sequential complete: {name}/{seed}; components={self.state['component_solves']}",flush=True)
                self.collect()

    def collect(self):
        # Regenerate worlds from frozen generator even in a resumed process.
        for name in WORLDS:
            for seed in (1301,1302):self.world(name,seed)
        for name in ("informative_depth","local_contradiction","harmful_bridge"):
            for seed in (2301,2302,2303):self.world(name,seed,24)
        results=[json.loads(p.read_text()) for p in sorted(self.records.glob("*.json"))]
        refs=json.loads((ROOT/"NUMERICAL_REFERENCES.json").read_text()) if (ROOT/"NUMERICAL_REFERENCES.json").exists() else None
        save(ROOT/"CONTROLLED_RESULTS.json",{"status":"COLLECTED","scope":"Synthetic mechanism evidence only",
             "run_state":self.state,"selection":json.loads((ROOT/"SELECTION_RECORD_V2.json").read_text()),
             "worlds":self.worlds,"records":results,"numerical_references":refs})


if __name__=="__main__":
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument("mode",choices=["static","sequential","collect","all"])
    args=ap.parse_args()
    experiment=Experiment()
    if args.mode in ("static","all"):experiment.static()
    if args.mode in ("sequential","all"):experiment.sequential()
    experiment.collect()
