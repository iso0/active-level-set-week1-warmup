"""Week 20 Track 2 — separable input x time GP on log1p depth trajectories (sparse variational GP, GPyTorch).

Run with the project venv:  .venv/Scripts/python.exe -m src.week20_track2_svgp validate | fit [names...] | fidelity
Kernel k((z,s),(z',s')) = sigma^2 * Matern32_ARD(z,z') * Matern32(s,s'), constant mean, Gaussian noise.
Why not exact Kronecker: the training design is a staircase (each run covers s in [0, s_obs]), not a complete
z x s grid, so the Kronecker identities do not hold; `validate` shows they do hold on a complete grid.
numpy / torch / gpytorch only (this script runs in .venv; no pandas).
"""
from __future__ import annotations

import json
import os
import sys
import time
from pathlib import Path

import numpy as np
import torch
import gpytorch

from src.week20_track2_common import sample_summaries

ROOT = Path(__file__).resolve().parents[1]
CACHE = ROOT / "outputs" / "week20_active_temporal_development" / "_cache" / "track2"
CKPT, PRED = CACHE / "checkpoints", CACHE / "predictions"
T2 = ROOT / "outputs" / "week20_active_temporal_development" / "track2"
S_MAX = 0.9
CONFIG = {"inducing_points": 400, "iterations": 2000, "learning_rate": 0.01, "minibatch": 1024, "samples": 2000, "seed": 20261012,
          "init": {"lengthscale_z": 1.0, "lengthscale_s": 0.05, "outputscale": 1.0, "noise": 0.01},
          "inducing_init": "fixed-seed random subset of the training inputs; locations learned", "optimizer": "Adam on all hyperparameters, variational and inducing parameters",
          "threads": 4, "dtype": "float64"}
torch.set_num_threads(CONFIG["threads"])
torch.set_default_dtype(torch.float64)


def peak_memory_bytes():
    if os.name != "nt":
        import resource
        return int(resource.getrusage(resource.RUSAGE_SELF).ru_maxrss) * 1024
    import ctypes
    from ctypes import wintypes as w

    class PMC(ctypes.Structure):
        _fields_ = [("cb", w.DWORD), ("PageFaultCount", w.DWORD), ("PeakWorkingSetSize", ctypes.c_size_t), ("WorkingSetSize", ctypes.c_size_t),
                    ("QuotaPeakPagedPoolUsage", ctypes.c_size_t), ("QuotaPagedPoolUsage", ctypes.c_size_t), ("QuotaPeakNonPagedPoolUsage", ctypes.c_size_t),
                    ("QuotaNonPagedPoolUsage", ctypes.c_size_t), ("PagefileUsage", ctypes.c_size_t), ("PeakPagefileUsage", ctypes.c_size_t)]
    k32, ps = ctypes.WinDLL("kernel32"), ctypes.WinDLL("psapi")
    k32.GetCurrentProcess.restype = w.HANDLE
    ps.GetProcessMemoryInfo.argtypes = [w.HANDLE, ctypes.POINTER(PMC), w.DWORD]
    pmc = PMC(); pmc.cb = ctypes.sizeof(PMC)
    ps.GetProcessMemoryInfo(k32.GetCurrentProcess(), ctypes.byref(pmc), pmc.cb)
    return int(pmc.PeakWorkingSetSize)


def kernel(dz):
    kz = gpytorch.kernels.MaternKernel(nu=1.5, ard_num_dims=dz, active_dims=tuple(range(dz)))
    ks = gpytorch.kernels.MaternKernel(nu=1.5, active_dims=(dz,))
    return gpytorch.kernels.ScaleKernel(kz * ks), kz, ks


class SepSVGP(gpytorch.models.ApproximateGP):
    def __init__(self, Z, dz=4):
        vd = gpytorch.variational.CholeskyVariationalDistribution(Z.size(0))
        vs = gpytorch.variational.VariationalStrategy(self, Z, vd, learn_inducing_locations=True)
        super().__init__(vs)
        self.mean_module = gpytorch.means.ConstantMean()
        self.covar_module, self.kz, self.ks = kernel(dz)

    def forward(self, x):
        return gpytorch.distributions.MultivariateNormal(self.mean_module(x), self.covar_module(x))


def init_hypers(model, lik, cfg=CONFIG):
    model.kz.lengthscale = torch.full_like(model.kz.lengthscale, cfg["init"]["lengthscale_z"])
    model.ks.lengthscale = torch.full_like(model.ks.lengthscale, cfg["init"]["lengthscale_s"])
    model.covar_module.outputscale = torch.tensor(cfg["init"]["outputscale"])
    lik.noise = torch.tensor(cfg["init"]["noise"])


def train(X, y, cfg=CONFIG, M=None, fixed_hypers=None, iters=None):
    gen = torch.Generator().manual_seed(cfg["seed"])
    M = M or cfg["inducing_points"]
    idx = torch.randperm(X.size(0), generator=gen)[:M]
    model = SepSVGP(X[idx].clone(), dz=X.size(1) - 1)
    lik = gpytorch.likelihoods.GaussianLikelihood(noise_constraint=gpytorch.constraints.GreaterThan(1e-6))
    init_hypers(model, lik, cfg)
    params = list(model.parameters()) + list(lik.parameters())
    if fixed_hypers is not None:                                       # validation: hyperparameters fixed, variational part only
        model.kz.lengthscale = fixed_hypers["lz"]; model.ks.lengthscale = fixed_hypers["ls"]
        model.covar_module.outputscale = fixed_hypers["os"]; lik.noise = fixed_hypers["noise"]; model.mean_module.constant.data.fill_(0.0)
        params = list(model.variational_strategy._variational_distribution.parameters())
        if fixed_hypers.get("fix_inducing", False):
            model.variational_strategy.inducing_points.requires_grad_(False)
        else:
            params.append(model.variational_strategy.inducing_points)
    opt = torch.optim.Adam(params, lr=cfg["learning_rate"])
    mll = gpytorch.mlls.VariationalELBO(lik, model, num_data=X.size(0))
    model.train(); lik.train()
    trace = []; n = X.size(0); bs = min(cfg["minibatch"], n); run = 0.0
    for it in range(iters or cfg["iterations"]):
        b = torch.randint(0, n, (bs,), generator=gen) if bs < n else torch.arange(n)
        opt.zero_grad(); loss = -mll(model(X[b]), y[b]); loss.backward(); opt.step()
        run += float(loss)
        if (it + 1) % 50 == 0:
            trace.append(run / 50); run = 0.0
    model.eval(); lik.eval()
    with torch.no_grad():
        elbo = 0.0
        for s in range(0, n, 4096):
            sl = slice(s, s + 4096)
            elbo += float(mll(model(X[sl]), y[sl])) * (min(s + 4096, n) - s)
        elbo /= n
    return model, lik, {"elbo_per_point": elbo, "trace": trace}


def hypers(model, lik):
    return {"lengthscale_z": model.kz.lengthscale.detach().numpy().ravel().tolist(), "lengthscale_s": float(model.ks.lengthscale.detach()),
            "outputscale": float(model.covar_module.outputscale.detach()), "noise": float(lik.noise.detach()), "mean": float(model.mean_module.constant.detach())}


def fit_checkpoint(name, M=None, tag="svgp"):
    d = dict(np.load(CKPT / f"{name}.npz", allow_pickle=False))
    K = int(d["K"]); centers = d["centers"]; width = S_MAX / K
    X = torch.tensor(np.c_[d["pts_z"], d["pts_s"]]); y0 = d["pts_y"]; ym, ys = float(y0.mean()), float(y0.std())
    y = torch.tensor((y0 - ym) / ys)
    t0 = time.time()
    model, lik, info = train(X, y, M=M)
    t_fit = time.time() - t0
    rng = torch.Generator().manual_seed(CONFIG["seed"] + 1)
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
            smp = (fu.mean[None, :] + torch.randn((CONFIG["samples"], int(use.sum())), generator=rng) @ L.T).numpy() * ys + ym
            full = np.full((CONFIG["samples"], K), -np.inf); full[:, use] = smp
            for k, v in sample_summaries(full, plan, obs, centers, width).items():
                summ[k].append(v)
    noise = float(lik.noise.detach()) * ys ** 2
    PRED.mkdir(parents=True, exist_ok=True)
    np.savez_compressed(PRED / f"{tag}_{name}.npz", test_ids=d["test_ids"], mean=mean, var_latent=var, var_noise=np.full(mean.shape, noise),
                        supported=np.ones(K, bool), **{k: np.array(v) for k, v in summ.items()})
    row = {"checkpoint": name, "tag": tag, "n_points": int(X.size(0)), "inducing_points": int(M or CONFIG["inducing_points"]), "fit_seconds": t_fit,
           "total_seconds": time.time() - t0, "elbo_per_point": info["elbo_per_point"], "trace_first": info["trace"][0], "trace_last": info["trace"][-1],
           "trace_last10pct_change": float(np.mean(info["trace"][-4:]) - np.mean(info["trace"][-8:-4])), "peak_memory_bytes": peak_memory_bytes(), **hypers(model, lik)}
    with open(T2 / "svgp_fits.jsonl", "a") as fh:
        fh.write(json.dumps(row) + "\n")
    print(json.dumps({k: row[k] for k in ("checkpoint", "tag", "n_points", "fit_seconds", "elbo_per_point", "lengthscale_s", "noise")}), flush=True)
    return row


# ======================================================================================== validation on a controlled example
def validate():
    """(1) Kronecker identity on a complete grid vs dense GP; (2) SVGP vs exact GP with fixed hyperparameters."""
    g = np.random.default_rng(0)
    nz, ns, dz = 15, 25, 4
    Zs = g.normal(size=(nz, dz)); S = np.linspace(0, S_MAX, ns)
    lz, lsv, os_, noise = np.array([0.8, 1.2, 1.5, 2.0]), 0.15, 1.0, 0.05 ** 2
    def m32(r):
        return (1 + np.sqrt(3) * r) * np.exp(-np.sqrt(3) * r)
    Kz = m32(np.sqrt((((Zs[:, None, :] - Zs[None, :, :]) / lz) ** 2).sum(-1))); Ks = m32(np.abs(S[:, None] - S[None, :]) / lsv)
    Kfull = os_ * np.kron(Kz, Ks)
    f = np.linalg.cholesky(Kfull + 1e-10 * np.eye(nz * ns)) @ g.normal(size=nz * ns)
    yv = f + np.sqrt(noise) * g.normal(size=nz * ns)
    # (1) Kronecker: (Kz (x) Ks + noise I)^-1 y via eigendecompositions vs dense solve, and the log marginal likelihood
    ez, Qz = np.linalg.eigh(os_ * Kz); es, Qs = np.linalg.eigh(Ks)
    lam = np.kron(ez, es) + noise
    Yg = yv.reshape(nz, ns); a_k = (Qz @ ((Qz.T @ Yg @ Qs) / lam.reshape(nz, ns)) @ Qs.T).ravel()
    a_d = np.linalg.solve(Kfull + noise * np.eye(nz * ns), yv)
    lml_k = -0.5 * yv @ a_k - 0.5 * np.log(lam).sum() - 0.5 * len(yv) * np.log(2 * np.pi)
    sign, ld = np.linalg.slogdet(Kfull + noise * np.eye(nz * ns)); lml_d = -0.5 * yv @ a_d - 0.5 * ld - 0.5 * len(yv) * np.log(2 * np.pi)
    mean_k, mean_d = Kfull @ a_k, Kfull @ a_d
    res_k = np.linalg.norm((Kfull + noise * np.eye(nz * ns)) @ a_k - yv) / np.linalg.norm(yv)
    out = {"kronecker_vs_dense": {"max_abs_posterior_mean_diff": float(np.abs(mean_k - mean_d).max()), "lml_diff": float(lml_k - lml_d), "relative_residual": float(res_k),
                                  "pass_1e-8": bool(np.abs(mean_k - mean_d).max() < 1e-8 and abs(lml_k - lml_d) < 1e-8 and res_k < 1e-6), "covariance_order": "kron(Kz, Ks): z outer, s inner (row-major Y[z, s])"}}
    # (2) SVGP (gpytorch) vs exact posterior, hyperparameters fixed at the generating values
    X = torch.tensor(np.c_[np.repeat(Zs, ns, 0), np.tile(S, nz)]); y = torch.tensor(yv)
    Xt = torch.tensor(np.c_[np.repeat(g.normal(size=(5, dz)), ns, 0), np.tile(S, 5)])
    Kxt = os_ * m32(np.sqrt((((Xt.numpy()[:, None, :4] - X.numpy()[None, :, :4]) / lz) ** 2).sum(-1))) * m32(np.abs(Xt.numpy()[:, None, 4] - X.numpy()[None, :, 4]) / lsv)
    Ktt = os_ * m32(np.sqrt((((Xt.numpy()[:, None, :4] - Xt.numpy()[None, :, :4]) / lz) ** 2).sum(-1))) * m32(np.abs(Xt.numpy()[:, None, 4] - Xt.numpy()[None, :, 4]) / lsv)
    A = Kfull + noise * np.eye(len(yv)); ex_mean = Kxt @ np.linalg.solve(A, yv); ex_var = np.diag(Ktt - Kxt @ np.linalg.solve(A, Kxt.T))
    fh = {"lz": torch.tensor(lz)[None, :], "ls": torch.tensor([[lsv]]), "os": torch.tensor(os_), "noise": torch.tensor(noise)}
    for M, fix in ((len(yv), True), (60, False)):
        cfg = dict(CONFIG); cfg["minibatch"] = len(yv)
        model, lik, info = train(X, y, cfg=cfg, M=M, fixed_hypers={**fh, "fix_inducing": fix}, iters=6000)
        with torch.no_grad():
            p = model(Xt); m_s, v_s = p.mean.numpy(), p.variance.numpy()
        out[f"svgp_M{M}"] = {"max_abs_mean_diff": float(np.abs(m_s - ex_mean).max()), "max_abs_var_diff": float(np.abs(v_s - ex_var).max()),
                              "elbo_total": info["elbo_per_point"] * len(yv), "exact_lml": float(lml_d), "elbo_minus_lml": info["elbo_per_point"] * len(yv) - float(lml_d),
                              "inducing": "all training inputs, fixed" if fix else "60 learned"}
    T2.mkdir(parents=True, exist_ok=True)
    (T2 / "svgp_validation.json").write_text(json.dumps(out, indent=1))
    print(json.dumps(out, indent=1))
    return out


if __name__ == "__main__":
    step = sys.argv[1] if len(sys.argv) > 1 else "fit"
    if step == "validate":
        validate()
    elif step == "fit":
        names = sys.argv[2:] or sorted(p.stem for p in CKPT.glob("ckpt_*.npz"))
        done = {json.loads(l)["checkpoint"] for l in (T2 / "svgp_fits.jsonl").read_text().splitlines() if l.strip() and json.loads(l)["tag"] == "svgp"} if (T2 / "svgp_fits.jsonl").exists() else set()
        for n in names:
            if n in done and (PRED / f"svgp_{n}.npz").exists():
                continue
            fit_checkpoint(n)
    elif step == "fidelity":
        fit_checkpoint(sys.argv[2] if len(sys.argv) > 2 else "ckpt_r1_f1_B40", M=2 * CONFIG["inducing_points"], tag="svgp_M800")
