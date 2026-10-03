"""Independent structural checks for the completed Week 12 evidence package."""
from __future__ import annotations
import json
import numpy as np
import pandas as pd
from src.week12_development_common import (OUT, ROOT, FEATURES, load_new, load_splits,
    original_order, q20_flags, require, sha, verify_protected, write_json)


def validate():
    protected=verify_protected()
    require(protected["status"]=="PASS","Frozen evidence drift")
    new=load_new();x=new[FEATURES].to_numpy();y=new.has_keyhole.to_numpy();ids=new.sim_id.to_numpy()
    splits=load_splits()
    bothfull=sum(len(set(y[s["test_indices"]]))==2 for s in splits)
    bothq=sum(len(set(y[np.array(s["test_indices"])[q20_flags(x,y,ids,s["test_indices"])]]))==2 for s in splits)
    require(bothfull==91 and bothq==87,"Test-class composition drift")
    for stage in ["startup/diagnosis/QC.json","startup/benchmark/QC.json","models/transfer/qc.json","models/new_only/qc.json","active_learning/QC.json"]:
        q=json.loads((OUT/stage).read_text());require(q["status"]=="PASS",f"Failed QC {stage}")
        require(all(q.get("checks",{}).values()),f"Failed boolean check {stage}")
    transfer=pd.read_csv(OUT/"models/transfer/predictions.csv.gz")
    cv=pd.read_csv(OUT/"models/new_only/predictions.csv.gz")
    require(len(transfer)==680 and len(cv)==13600,"Model prediction completeness")
    require(not transfer.duplicated(["model","row_index"]).any(),"Duplicate transfer rows")
    for model,g in transfer.groupby("model"):
        g=g.sort_values("row_index")
        require(g.row_index.tolist()==list(range(136)),"Transfer IDs missing")
        require(np.array_equal(g.truth,y),"Transfer truth mismatch")
        require(np.array_equal(g.is_q20,q20_flags(x,y,ids,np.arange(136))),"Transfer q20 mismatch")
    for (sid,model),g in cv.groupby(["split_id","model"]):
        s=next(s for s in splits if s["split_id"]==sid)
        g=g.set_index("row_index").loc[s["test_indices"]]
        require(np.array_equal(g.truth,y[s["test_indices"]]),"CV truth mismatch")
        require(np.array_equal(g.is_q20,q20_flags(x,y,ids,s["test_indices"])),"CV q20 mismatch")
    from src.week12_startup import startup_next
    config=json.loads((OUT/"active_learning/config.json").read_text())
    paths=pd.read_csv(OUT/"active_learning/query_paths.csv.gz")
    startup_checked=0
    for s in splits:
        order=original_order(x,s)
        for arm,spec in config["arms"].items():
            g=paths[(paths.split_id==s["split_id"]) & (paths.arm==arm)].sort_values("query_order")
            queried=[];observed=[]
            require(len(g)==80,"Path lacks80 paid queries")
            for r in g.itertuples():
                if r.selection_mode.startswith("paid_startup"):
                    expected=startup_next(spec["startup"],x,s["train_indices"],queried,observed,order,s["split_id"])
                    require(expected==r.row_index,"Startup replay mismatch")
                    startup_checked+=1
                else:
                    require(len(set(observed))==2 and len(queried)>=spec["minimum_start"],"Premature refinement")
                queried.append(r.row_index);observed.append(r.revealed_label)
            require(np.array_equal(y[queried],observed),"Query-label ledger mismatch")
    predictions=pd.read_csv(OUT/"active_learning/predictions.csv.gz")
    require(len(predictions)==20*136*8*73,"AL prediction count mismatch")
    for s in splits:
        mask=q20_flags(x,y,ids,s["test_indices"])
        flagmap=dict(zip(s["test_indices"],mask))
        g=predictions[predictions.split_id==s["split_id"]]
        require(np.array_equal(g.q20,g.row_index.map(flagmap)),"AL q20 drift")
    summary=json.loads((OUT/"active_learning/summary.json").read_text())
    require(summary["complete"] and summary["path_count"]==800,"Incomplete AL summary")
    q={"status":"PASS","protected_evidence":protected,"withheld_outcomes_used":False,
       "frozen_external_status":"INCOMPLETE_FROZEN_STOP_UNCHANGED","old_new_training_mixed":False,
       "model_prediction_counts":{"transfer":680,"new_only":13600},
       "active_learning":{"paths":800,"predictions":len(predictions),"paid_queries":len(paths),
                           "startup_queries_independently_replayed":startup_checked,"q20_flags_verified":True},
       "single_class_test_folds":100-bothfull,"single_class_q20_folds":100-bothq,
       "tests":{"week12_passed":15,"historical_implementation_passed":16,
                "preexisting_archive_checks_failed":4,"details":"audit/historical_test_limitations.json"},
       "superseded_defect_retained":True,"scientific_categories":["HISTORICAL CONFIRMATORY / FROZEN","FROZEN EXTERNAL ATTEMPT","POST-HOC DEVELOPMENT","EXPLORATORY"]}
    write_json(OUT/"FINAL_QC.json",q)
    files={str(p.relative_to(OUT)).replace("\\","/"):{"sha256":sha(p),"bytes":p.stat().st_size}
           for p in sorted(OUT.rglob("*")) if p.is_file() and p.name!="ARTIFACT_MANIFEST.json"}
    write_json(OUT/"ARTIFACT_MANIFEST.json",{"files":files,"count":len(files),"scope":"All Week12 outputs except this manifest"})
    print(json.dumps(q,indent=2))


if __name__=="__main__":validate()
