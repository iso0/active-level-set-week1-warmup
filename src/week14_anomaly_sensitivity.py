"""POST-HOC NEW mechanism check (not a method choice, no relabelling): is the closure harm on NEW-only
caused by the single order-violating non-Keyhole case (P 423 W, VX 0.332 m/s)?  The case is removed from
TRAINING folds only in this sensitivity run; it stays in every test fold and in all primary analyses."""
import json
from pathlib import Path
import numpy as np, pandas as pd
from joblib import Parallel, delayed
from src.week14_real_checks import F, W12, load_old_new, score_models, to_log
from src.week14_order import SIGNS_O3
OUT = Path(__file__).resolve().parents[1] / "outputs/week14_research_program/real_data"


def main():
    _, new = load_old_new()
    X, y, s = to_log(new[F].to_numpy()), new.has_keyhole.to_numpy(), new.log_h.to_numpy()
    anom = int(np.nonzero((y == 0) & (new.VX.to_numpy() < .5))[0][0])
    sp = json.loads((W12 / "audit/original_splits.json").read_text())
    def one(sd):
        tr = np.setdiff1d(np.asarray(sd["train_indices"]), [anom]); te = np.asarray(sd["test_indices"])
        return score_models(X[tr], y[tr], s[tr], X[te], y[te], s[te], SIGNS_O3, "POSTHOC_NEW_only_anomaly_removed_from_training",
                            {"split": sd["split_id"], "repeat": sd["repeat"], "anomaly_in_original_training": bool(anom in sd["train_indices"])})
    res = Parallel(n_jobs=7)(delayed(one)(sd) for sd in sp)
    df = pd.DataFrame([x for r in res for x in r])
    df.to_csv(OUT / "anomaly_sensitivity.csv", index=False)
    print("anomaly row", anom, new.loc[anom, ["P", "VX", "LS", "ST"]].to_dict())
    print(df[df.ok].groupby("model")[["BA", "minority_recall", "majority_recall", "AUC", "closure_errors", "closure_implied"]].mean().round(3).to_string())


if __name__ == "__main__":
    main()
