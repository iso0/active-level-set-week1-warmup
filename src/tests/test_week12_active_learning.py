"""Information-barrier and paid-budget contracts for the development runner."""
import numpy as np
import pandas as pd

from src import week12_active_learning as al


def test_single_class_discovery_is_paid_and_never_fits_invalid_gp(tmp_path, monkeypatch):
    from src import week12_startup as startup
    from src.external_validation import runner
    n = 30
    x = np.column_stack([np.linspace(100,200,n), np.linspace(.2,1,n), np.repeat(.00005,n), np.arange(n)+300])
    data = pd.DataFrame(x, columns=al.FEATURES)
    data["has_keyhole"] = 1
    data.loc[18,"has_keyhole"] = 0
    data["sim_id"] = [f"id{i}" for i in range(n)]
    split = {"split_id":"fixture", "repeat":1, "fold":1,
             "train_indices":list(range(25)), "test_indices":list(range(25,30))}
    calls = []
    class FakeEvaluator:
        def fit_predict(self, x, revealed, labels, train, predict, run_id, budget):
            assert set(labels) == {0,1}
            assert len(revealed) == budget == len(labels)
            assert set(revealed) <= set(train)
            calls.append(budget)
            return np.repeat(.7,len(predict)), {"optimizer_converged": True,"fallback_status":"none"}, None
    monkeypatch.setattr(runner,"FrozenM3Evaluator",FakeEvaluator)
    monkeypatch.setattr(al,"load_new",lambda:data)
    monkeypatch.setattr(al,"original_order",lambda x,s:list(range(25)))
    monkeypatch.setattr(al,"q20_flags",lambda *args:np.array([True,False,False,False,False]))
    monkeypatch.setattr(al,"protocol_hash",lambda:"fixture")
    monkeypatch.setattr(al,"source_hashes",lambda:{})
    monkeypatch.setattr(al,"DEST",tmp_path)
    monkeypatch.setattr(startup,"startup_next",lambda rule,x,train,q,seen,order,sid:next(i for i in order if i not in q))
    monkeypatch.setattr(al,"select_refinement",lambda kind,x,train,q,seen,candidates,*args:(int(candidates[0]),"margin"))
    result=al.run_split(split,{"paid":{"startup":"maximin","minimum_start":16,"refinement":"margin"}},horizon=24)
    assert result["complete"]
    assert min(calls)==19
    import gzip,json
    p=json.loads(gzip.decompress((tmp_path/"checkpoints/fixture.json.gz").read_bytes()))
    path=pd.DataFrame(p["paths"])
    assert path.query_order.tolist()==list(range(1,25))
    assert path.loc[path.query_order<=19,"selection_mode"].str.startswith("paid_startup").all()
    predictions=pd.DataFrame(p["predictions"])
    assert predictions.loc[predictions.budget<=18,"predictor"].str.startswith("Beta").all()
    assert predictions.loc[predictions.budget>=19,"predictor"].eq("historical_M3").all()
    assert set(predictions.row_index)==set(split["test_indices"])


def test_margin_selector_uses_only_supplied_candidate_probabilities():
    x=np.array([[100,.2,.00004,300],[200,.5,.00005,350],[150,.4,.00005,340],[190,.7,.00005,320]],float)
    for hypothetical_unrevealed_labels in ([0,0],[1,1],[0,1]):
        # Hidden outcomes are deliberately not an input to the selector.
        chosen,mode=al.select_refinement("margin",x,[0,1,2,3],[0,1],[0,1],np.array([2,3]),np.array([.51,.8]),None,"test")
        assert chosen==2 and mode=="margin"
