"""Full-label ceiling on the frozen 100 outer folds: train on all 324 training
labels, evaluate on the 81 held-out (q20 / q30 / full81).  Many model classes,
with and without configuration metadata.  Development diagnostic only."""
import numpy as np, pandas as pd, time, sys, json
from core import *
from sklearn.preprocessing import StandardScaler
from sklearn.ensemble import RandomForestClassifier, GradientBoostingClassifier
from sklearn.neighbors import KNeighborsClassifier
from sklearn.svm import SVC
from sklearn.linear_model import LogisticRegression
from sklearn.gaussian_process import GaussianProcessClassifier
from sklearn.gaussian_process.kernels import ConstantKernel, Matern
from joblib import Parallel, delayed

d = Data(); pop = d.population; y = d.labels
meta = pd.read_csv('pop_meta.csv')
assert (meta.experiment_name.values == pop.experiment_name.values).all()
cfg = pd.get_dummies(meta.cfg).to_numpy(float)
TE = meta.TE.to_numpy(float)
U = np.c_[d.logh, np.log(pop.VX), np.log(pop.LS), pop.ST]
X4 = d.x4
D = pop.value__max_depth.to_numpy(float)


def models():
    return {
        "H_logistic_logh": lambda: LogisticRegression(C=1e6, max_iter=3000),
        "logistic_u4": lambda: LogisticRegression(C=1e6, max_iter=5000),
        "kNN5": lambda: KNeighborsClassifier(5),
        "kNN1": lambda: KNeighborsClassifier(1),
        "RF500": lambda: RandomForestClassifier(500, random_state=0, min_samples_leaf=1),
        "GBM": lambda: GradientBoostingClassifier(random_state=0),
        "SVC_rbf": lambda: SVC(C=10, gamma="scale"),
        "GPC_ARD_wide": lambda: GaussianProcessClassifier(ConstantKernel(1.0, (1e-2, 1e3)) * Matern(1.0, (1e-2, 1e3), nu=1.5), random_state=0),
    }


def run(spec):
    tr = np.asarray(spec.train_indices); te = np.asarray(spec.test_indices); fl = d.flags(spec); q = fl["B1_q20"]; q3 = fl["B1_q30"]
    rows = []
    def rec(name, pred):
        rows.append({"run_id": spec.run_id, "repeat": spec.repeat, "model": name,
                     "q20_acc": float((pred[q] == y[te][q]).mean()), "q30_acc": float((pred[q3] == y[te][q3]).mean()),
                     "full_acc": float((pred == y[te]).mean()),
                     "q20_kh_recall": float(((pred == 1) & (y[te] == 1))[q].sum() / max(1, (y[te][q] == 1).sum()))})
    # M3 exact
    m3 = M3(d, spec).fit(tr, 324); rec("M3", (m3.proba(te) >= .5).astype(int))
    for feats_name, F in (("u4", U), ("u4+cfg+TE", np.c_[U, cfg, TE])):
        sc = StandardScaler().fit(F[tr]); Z = sc.transform(F)
        for name, mk in models().items():
            if name == "H_logistic_logh":
                if feats_name != "u4": continue
                Zh = StandardScaler().fit(U[tr][:, :1]).transform(U[:, :1]); mdl = mk().fit(Zh[tr], y[tr]); rec(name, mdl.predict(Zh[te])); continue
            mdl = mk().fit(Z[tr], y[tr]); rec(f"{name}|{feats_name}", mdl.predict(Z[te]))
    return rows


if __name__ == "__main__":
    t0 = time.time()
    out = Parallel(n_jobs=2)(delayed(run)(s) for s in d.specs)
    df = pd.DataFrame([r for rows in out for r in rows]); df.to_csv("diag_ceiling_runs.csv", index=False)
    summ = df.groupby("model")[["q20_acc", "q30_acc", "full_acc", "q20_kh_recall"]].mean().sort_values("q20_acc", ascending=False)
    print(summ.round(4).to_string()); summ.to_csv("diag_ceiling_summary.csv"); print("elapsed", time.time() - t0)
