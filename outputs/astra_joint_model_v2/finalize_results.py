"""Attach the separately frozen supplement and verify provenance; no fits."""
from pathlib import Path
import json,hashlib
import numpy as np
from run_controlled import ROOT,save

result=json.loads((ROOT/"CONTROLLED_RESULTS.json").read_text())
supp=json.loads((ROOT/"SUPPLEMENTAL_DIAGNOSTICS.json").read_text())
result["supplemental_diagnostics"]=supp
result["total_accounting"]={
    "controlled_model_requests":result["run_state"]["requests"]+supp["controlled_requests"],
    "component_solves_including_correctness_and_induced_fallback":
        result["run_state"]["component_solves"]+supp["component_solves"],
    "main_numerical_reference_groups":7,"supplemental_ESS_chains":4,
    "ceiling":600}
assert result["total_accounting"]["component_solves_including_correctness_and_induced_fallback"]<=600
assert not result["run_state"]["pending"]
for name,digest in result["run_state"]["source_sha256"].items():
    assert hashlib.sha256((ROOT/name).read_bytes()).hexdigest()==digest,name
provenance=json.loads((ROOT/"evidence/PROVENANCE.json").read_text())
old=ROOT.parent/"week20_method_development"
for name,digest in provenance["immutable_V1_sha256"].items():
    assert hashlib.sha256((old/name).read_bytes()).hexdigest()==digest,name
result["status"]="COMPLETE_WITH_REPORTED_LIMITATIONS"
result["V1_package_unchanged"]=True
save(ROOT/"CONTROLLED_RESULTS.json",result)
s=json.loads((ROOT/"RESULTS_SUMMARY.json").read_text())
seq=s["sequential"]
deltas=[r["paired_minus_margin_AULC"]["BA"] for r in seq]
brief={"accounting":result["total_accounting"],
       "sequential_BA_delta_mean":float(np.mean(deltas)),
       "sequential_BA_delta_range":[float(min(deltas)),float(max(deltas))],
       "sequential_positive_pairs":int(np.sum(np.array(deltas)>0)),
       "sequential_path_divergence":sum(r["first_divergence_budget"] is not None for r in seq),
       "main_failures":len(s["fit_failures"]),"main_fallbacks":len(s["fallbacks"]),
       "query_stops":len(s["query_stops"])}
save(ROOT/"DELIVERY_ACCOUNTING.json",brief)
print(json.dumps(brief,indent=2))
