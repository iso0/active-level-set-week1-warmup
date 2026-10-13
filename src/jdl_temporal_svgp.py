"""Temporal repair sub-study — converged separable SVGP (run with the torch venv).

Same model as Week 20 Track 2 (k = s^2 Matern32-ARD(z) x Matern32(s), constant mean, Gaussian noise, learned inducing
locations, float64, same data, initialisation and seeds); only the optimisation protocol changes:
  * natural-gradient descent on the variational distribution (NaturalVariationalDistribution + gpytorch.optim.NGD,
    lr 0.1) and Adam (lr 0.01) on hyperparameters and inducing locations, minibatch 1024; both learning rates are
    halved at iterations 5000 and 10000;
  * a stopping rule driven only by training evidence, evaluated every 250 iterations on a fixed probe subset of the
    training points (8192 points, fixed seed): stop when, for 3 consecutive checks, the relative change of the probe
    ELBO is <= 5e-4 AND the RMS change of the probe predictive mean is <= 5e-3 (log1p units); at least 1000 and at
    most 20000 iterations; a fit that reaches the cap is recorded as not converged;
  * identical protocol and caps for M = 400 and M = 800 (equal convergence effort).
Posterior summaries come from 2000 posterior latent trajectories as before.

Steps:  .venv/Scripts/python.exe -m src.jdl_temporal_svgp validate | fit M names...
"""
from __future__ import annotations

import json
import sys
import time
from pathlib import Path

import numpy as np
import torch
import gpytorch

from src.week20_track2_common import sample_summaries
import src.week20_track2_svgp as W20

ROOT = Path(__file__).resolve().parents[1]
CACHE = ROOT / "outputs" / "week20_active_temporal_development" / "_cache" / "track2"
CKPT, PRED = CACHE / "checkpoints", CACHE / "predictions"
TR = ROOT / "outputs" / "joint_depth_label_development" / "temporal_repair"
S_MAX = 0.9
PROTOCOL = {"ngd_lr": 0.1, "adam_lr": 0.01, "lr_halving_at": [5000, 10000], "minibatch": 1024, "check_every": 250, "probe_points": 8192,
            "elbo_rel_tol": 5e-4, "mean_rms_tol": 5e-3, "consecutive_checks": 3, "min_iterations": 1000, "max_iterations": 20000,
            "samples": 2000, "seed": 20261012, "threads": 3, "dtype": "float64", "init": W20.CONFIG["init"]}
torch.set_num_threads(PROTOCOL["threads"])
torch.set_default_dtype(torch.float64)


class NatSVGP(gpytorch.models.ApproximateGP):
    def __init__(self, Z, dz=4):
        vd = gpytorch.variational.NaturalVariationalDistribution(Z.size(0))
        vs = gpytorch.variational.VariationalStrategy(self, Z, vd, learn_inducing_locations=True)
        super().__init__(vs)
        self.mean_module = gpytorch.means.ConstantMean()
        self.covar_module, self.kz, self.ks = W20.kernel(dz)

    def forward(self, x):
        return gpytorch.distributions.MultivariateNormal(self.mean_module(x), self.covar_module(x))


def train(X, y, M, proto=PROTOCOL, fixed=None):
    gen = torch.Generator().manual_seed(proto["seed"])
    n = X.size(0)
    idx = torch.randperm(n, generator=gen)[:M]
    model = NatSVGP(X[idx].clone(), dz=X.size(1) - 1)
    lik = gpytorch.likelihoods.GaussianLikelihood(noise_constraint=gpytorch.constraints.GreaterThan(1e-6))
    W20.init_hypers(model, lik, {"init": proto["init"]})
    if fixed is not None:                                                     # validation: fixed hyperparameters and inducing inputs
        model.kz.lengthscale = fixed["lz"]; model.ks.lengthscale = fixed["ls"]; model.covar_module.outputscale = fixed["os"]
        lik.noise = fixed["noise"]; model.mean_module.constant.data.fill_(0.0)
        model.variational_strategy.inducing_points.requires_grad_(False)
        hyper = []
    else:
        hyper = [p for p in list(model.hyperparameters()) + list(lik.parameters()) if p.requires_grad]
    ngd = gpytorch.optim.NGD(model.variational_parameters(), num_data=n, lr=proto["ngd_lr"])
    adam = torch.optim.Adam(hyper, lr=proto["adam_lr"]) if hyper else None
    mll = gpytorch.mlls.VariationalELBO(lik, model, num_data=n)
    pgen = torch.Generator().manual_seed(proto["seed"] + 7)
    probe = torch.randperm(n, generator=pgen)[:min(proto["probe_points"], n)]
    bs = min(proto["minibatch"], n)
    trace, stable, prev_elbo, prev_mean, status, it = [], 0, None, None, "max_iterations", 0
    model.train(); lik.train()
    for it in range(1, proto["max_iterations"] + 1):
        if it in proto["lr_halving_at"]:
            for g in ngd.param_groups:
                g["lr"] *= 0.5
            if adam is not None:
                for g in adam.param_groups:
                    g["lr"] *= 0.5
        b = torch.randint(0, n, (bs,), generator=gen) if bs < n else torch.arange(n)
        ngd.zero_grad()
        if adam is not None:
            adam.zero_grad()
        loss = -mll(model(X[b]), y[b]); loss.backward()
        ngd.step()
        if adam is not None:
            adam.step()
        if it % proto["check_every"] == 0:
            model.eval(); lik.eval()
            with torch.no_grad():
                f = model(X[probe])
                elbo = float(gpytorch.mlls.VariationalELBO(lik, model, num_data=len(probe))(f, y[probe]))
                mean = f.mean.clone()
            model.train(); lik.train()
            rel = abs(elbo - prev_elbo) / max(1.0, abs(prev_elbo)) if prev_elbo is not None else np.inf
            rms = float(torch.sqrt(torch.mean((mean - prev_mean) ** 2))) if prev_mean is not None else np.inf
            trace.append({"iteration": it, "probe_elbo_per_point": elbo, "rel_change": rel, "probe_mean_rms_change": rms})
            ok = rel <= proto["elbo_rel_tol"] and rms <= proto["mean_rms_tol"]
            stable = stable + 1 if ok else 0
            prev_elbo, prev_mean = elbo, mean
            if it >= proto["min_iterations"] and stable >= proto["consecutive_checks"]:
                status = "converged"; break
    model.eval(); lik.eval()
    return model, lik, {"status": status, "iterations": it, "trace": trace}


def fit_checkpoint(name, M):
    tag = f"svgp_ngd_M{M}"
    d = dict(np.load(CKPT / f"{name}.npz", allow_pickle=False))
    K = int(d["K"]); centers = d["centers"]; width = S_MAX / K
    X = torch.tensor(np.c_[d["pts_z"], d["pts_s"]]); y0 = d["pts_y"]; ym, ys = float(y0.mean()), float(y0.std())
    y = torch.tensor((y0 - ym) / ys)
    t0 = time.time()
    model, lik, info = train(X, y, M)
    t_fit = time.time() - t0
    rng = torch.Generator().manual_seed(PROTOCOL["seed"] + 1)
    n_test = len(d["test_ids"]); mean = np.zeros((n_test, K)); var = np.zeros((n_test, K))
    summ = {k: [] for k in ("max_planned", "max_observed", "argmax_s_observed", "exceed_s_observed")}
    with torch.no_grad(), gpytorch.settings.fast_pred_var(False), gpytorch.settings.cholesky_jitter(1e-8):
        for i in range(n_test):
            Xs = torch.tensor(np.c_[np.repeat(d["z_test"][i:i + 1], K, 0), centers])
            f = model(Xs)
            mean[i] = f.mean.numpy() * ys + ym; var[i] = np.maximum(f.variance.numpy(), 0.0) * ys ** 2
            plan = d["te_plan"][i]; obs = np.isfinite(d["te_obs"][i]); use = plan | obs
            fu = model(Xs[torch.tensor(use)])
            L = torch.linalg.cholesky(fu.covariance_matrix + 1e-8 * torch.eye(int(use.sum())))
            smp = (fu.mean[None, :] + torch.randn((PROTOCOL["samples"], int(use.sum())), generator=rng) @ L.T).numpy() * ys + ym
            full = np.full((PROTOCOL["samples"], K), -np.inf); full[:, use] = smp
            for k, v in sample_summaries(full, plan, obs, centers, width).items():
                summ[k].append(v)
    noise = float(lik.noise.detach()) * ys ** 2
    PRED.mkdir(parents=True, exist_ok=True)
    np.savez_compressed(PRED / f"{tag}_{name}.npz", test_ids=d["test_ids"], mean=mean, var_latent=var, var_noise=np.full(mean.shape, noise),
                        supported=np.ones(K, bool), **{k: np.array(v) for k, v in summ.items()})
    row = {"checkpoint": name, "tag": tag, "inducing_points": M, "n_points": int(X.size(0)), "status": info["status"], "iterations": info["iterations"],
           "fit_seconds": t_fit, "total_seconds": time.time() - t0, "final_probe_elbo_per_point": info["trace"][-1]["probe_elbo_per_point"] if info["trace"] else None,
           "trace": info["trace"], "peak_memory_bytes": W20.peak_memory_bytes(), **W20.hypers(model, lik)}
    TR.mkdir(parents=True, exist_ok=True)
    with open(TR / "svgp_ngd_fits.jsonl", "a") as fh:
        fh.write(json.dumps(row) + "\n")
    print(json.dumps({k: row[k] for k in ("checkpoint", "tag", "status", "iterations", "fit_seconds", "final_probe_elbo_per_point", "lengthscale_s", "noise")}), flush=True)
    return row


def validate():
    """Controlled example (same as the Week 20 check): with fixed hyperparameters and inducing inputs equal to all
    training inputs, the NGD-trained SVGP must reproduce the exact GP posterior."""
    g = np.random.default_rng(0)
    nz, ns = 15, 25
    Zr = g.standard_normal((nz, 4)); S = np.linspace(0, 0.9, ns)
    X = np.c_[np.repeat(Zr, ns, 0), np.tile(S, nz)]
    keep = g.uniform(size=len(X)) < 1.0
    lz, ls_, os_, noise = 1.3, 0.2, 0.8, 0.02
    Kx = W20.kernel(4)[0]
    Kx.base_kernel.kernels[0].lengthscale = torch.full((1, 4), lz); Kx.base_kernel.kernels[1].lengthscale = torch.tensor([[ls_]]); Kx.outputscale = torch.tensor(os_)
    Xt = torch.tensor(X)
    with torch.no_grad():
        Kfull = Kx(Xt).to_dense().numpy()
    f = np.linalg.cholesky(Kfull + 1e-10 * np.eye(len(X))) @ g.standard_normal(len(X))
    yv = f + np.sqrt(noise) * g.standard_normal(len(X))
    Xtr, ytr = X[keep][::3], yv[keep][::3]                                   # 125 training points
    Ktr = Kfull[np.ix_(keep, keep)][::3, ::3]
    with torch.no_grad():
        Kte = Kx(torch.tensor(X[:40]), torch.tensor(Xtr)).to_dense().numpy(); Kee = Kx(torch.tensor(X[:40])).to_dense().numpy()
    A = np.linalg.solve(Ktr + noise * np.eye(len(Xtr)), Kte.T).T
    m_ex, v_ex = A @ ytr, np.diag(Kee - A @ Kte.T)
    proto = {**PROTOCOL, "minibatch": len(Xtr), "max_iterations": 3000, "min_iterations": 1000, "ngd_lr": 1.0, "lr_halving_at": []}
    fixed = {"lz": torch.full((1, 4), lz), "ls": torch.tensor([[ls_]]), "os": torch.tensor(os_), "noise": torch.tensor(noise)}
    model, lik, info = train(torch.tensor(Xtr), torch.tensor(ytr), len(Xtr), proto, fixed)   # exercises the stopping rule (minibatch = all points)
    # exactness: inducing inputs = the training inputs, fixed hyperparameters, full-batch NGD at lr 1
    model2 = NatSVGP(torch.tensor(Xtr), dz=4)
    model2.kz.lengthscale = fixed["lz"]; model2.ks.lengthscale = fixed["ls"]; model2.covar_module.outputscale = fixed["os"]; model2.mean_module.constant.data.fill_(0.0)
    model2.variational_strategy.inducing_points.requires_grad_(False)
    lik2 = gpytorch.likelihoods.GaussianLikelihood(); lik2.noise = fixed["noise"]
    ngd = gpytorch.optim.NGD(model2.variational_parameters(), num_data=len(Xtr), lr=1.0)
    mll = gpytorch.mlls.VariationalELBO(lik2, model2, num_data=len(Xtr))
    model2.train(); lik2.train()
    for _ in range(20):                                                       # with a Gaussian likelihood, one full-batch NGD step at lr 1 is exact
        ngd.zero_grad(); (-mll(model2(torch.tensor(Xtr)), torch.tensor(ytr))).backward(); ngd.step()
    model2.eval(); lik2.eval()
    with torch.no_grad():
        f2 = model2(torch.tensor(X[:40]))
        m2, v2 = f2.mean.numpy(), f2.variance.numpy()
    res = {"exact_vs_ngd_svgp_M_eq_N": {"max_abs_mean_diff": float(np.max(np.abs(m2 - m_ex))), "max_abs_var_diff": float(np.max(np.abs(v2 - v_ex))),
                                        "passed": bool(np.max(np.abs(m2 - m_ex)) < 1e-4 and np.max(np.abs(v2 - v_ex)) < 1e-4)},
           "stopping_rule_on_controlled_example": {"status": info["status"], "iterations": info["iterations"]}}
    TR.mkdir(parents=True, exist_ok=True)
    (TR / "svgp_ngd_validation.json").write_text(json.dumps(res, indent=1), encoding="utf-8")
    print(json.dumps(res, indent=1))
    return res


if __name__ == "__main__":
    step = sys.argv[1] if len(sys.argv) > 1 else "validate"
    if step == "validate":
        validate()
    elif step == "fit":
        M = int(sys.argv[2]); names = sys.argv[3:]
        done = set()
        f = TR / "svgp_ngd_fits.jsonl"
        if f.exists():
            done = {(json.loads(l)["checkpoint"], json.loads(l)["inducing_points"]) for l in f.read_text().splitlines() if l.strip()}
        for nm in names:
            if (nm, M) not in done:
                fit_checkpoint(nm, M)
