"""Resumable NGD-SVGP training with atomic model/optimizer/RNG checkpoints - for FUTURE temporal jobs only.

It is not used by, and not retrofitted into, the temporal-repair fits that were running when it was written
(src/jdl_temporal_svgp.py stays byte-identical).  `train_resumable` executes the loop of the frozen
`src.jdl_temporal_svgp.train` operation by operation (same model, generators, optimizers, learning-rate schedule and
stopping rule) and additionally writes a checkpoint every `every` iterations containing:
    model, likelihood, NGD and Adam state_dicts; the minibatch generator state; the probe indices; the stopping-rule
    state (trace, consecutive-stable counter, previous probe ELBO and probe mean); the last completed iteration;
    SHA-256 fingerprints of the training data and of the protocol.
A checkpoint is written to <path>.tmp, flushed and fsynced, then moved over <path> with os.replace (atomic on one
volume); a JSON sidecar stores the file's SHA-256, which `load` verifies before anything is restored.  A checkpoint
whose data or protocol fingerprint differs from the current call is refused.

Validation (`python -m src.jdl_svgp_resumable validate`, torch venv, one thread): on a small synthetic data set
(a) train_resumable without checkpoints is bitwise identical to the frozen train(); (b) a run stopped right after an
intermediate checkpoint and resumed in fresh objects ends bitwise identical to the uninterrupted run (parameters,
trace, predictions); (c) a corrupted checkpoint is refused; (d) an interrupted write (stale .tmp) leaves the previous
checkpoint valid.

v2 (2026-10-14, after queue task T11): the first validation (CHECKPOINT_MECHANISM_VALIDATION.json, kept) failed both
bitwise checks.  gpytorch's NaturalVariationalDistribution draws its initial natural-parameter noise
(torch.randn_like, sd 1e-3) from the unseeded global torch RNG at the first forward pass, and the harness seeded that
RNG only once, so the compared runs started from different initialisations.  v2 seeds the global RNG before every
fresh run, and checkpoints/restores the global RNG state together with the minibatch generator.  It writes
CHECKPOINT_MECHANISM_VALIDATION_v2.json; checks and tolerances (bitwise equality) are unchanged.
"""
from __future__ import annotations

import hashlib
import io
import json
import os
import sys
import time
from pathlib import Path

import numpy as np
import torch
import gpytorch

import src.jdl_temporal_svgp as F            # frozen module (read only); importing it sets 3 torch threads and float64

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "outputs" / "joint_depth_label_development" / "temporal_repair" / "checkpoint_mechanism"
GLOBAL_SEED = 0                                                      # v2 validation: global torch seed before each fresh run


def _fingerprint(X, y, proto):
    h = hashlib.sha256()
    h.update(X.detach().cpu().numpy().tobytes()); h.update(y.detach().cpu().numpy().tobytes())
    data = h.hexdigest()
    prot = hashlib.sha256(json.dumps({k: v for k, v in proto.items() if k != "threads"}, sort_keys=True, default=str).encode()).hexdigest()
    return data, prot


def save_checkpoint(path, payload):
    path = Path(path); path.parent.mkdir(parents=True, exist_ok=True)
    buf = io.BytesIO(); torch.save(payload, buf); blob = buf.getvalue()
    tmp = path.with_suffix(path.suffix + ".tmp")
    with open(tmp, "wb") as fh:
        fh.write(blob); fh.flush(); os.fsync(fh.fileno())
    os.replace(tmp, path)
    side = path.with_suffix(path.suffix + ".json")
    stmp = side.with_suffix(".json.tmp")
    with open(stmp, "w", encoding="utf-8") as fh:
        json.dump({"sha256": hashlib.sha256(blob).hexdigest(), "iteration": payload["iteration"], "data_fp": payload["data_fp"], "protocol_fp": payload["protocol_fp"]}, fh)
        fh.flush(); os.fsync(fh.fileno())
    os.replace(stmp, side)


def load_checkpoint(path, data_fp, protocol_fp):
    path = Path(path); side = path.with_suffix(path.suffix + ".json")
    if not path.exists() or not side.exists():
        return None
    meta = json.loads(side.read_text(encoding="utf-8"))
    blob = path.read_bytes()
    if hashlib.sha256(blob).hexdigest() != meta["sha256"]:
        raise RuntimeError("checkpoint file does not match its recorded SHA-256; refusing to resume")
    payload = torch.load(io.BytesIO(blob), weights_only=False)
    if payload["data_fp"] != data_fp or payload["protocol_fp"] != protocol_fp:
        raise RuntimeError("checkpoint belongs to different data or protocol; refusing to resume")
    return payload


def train_resumable(X, y, M, proto=F.PROTOCOL, fixed=None, ckpt_path=None, every=None, stop_after=None):
    """Frozen F.train loop + atomic checkpoints.  `stop_after` (validation only) returns right after that iteration's
    checkpoint, as if the process had been killed there."""
    data_fp, prot_fp = _fingerprint(X, y, proto)
    gen = torch.Generator().manual_seed(proto["seed"])
    n = X.size(0)
    idx = torch.randperm(n, generator=gen)[:M]
    model = F.NatSVGP(X[idx].clone(), dz=X.size(1) - 1)
    lik = gpytorch.likelihoods.GaussianLikelihood(noise_constraint=gpytorch.constraints.GreaterThan(1e-6))
    F.W20.init_hypers(model, lik, {"init": proto["init"]})
    if fixed is not None:
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
    trace, stable, prev_elbo, prev_mean, status, start = [], 0, None, None, "max_iterations", 1
    resumed_from = None
    if ckpt_path is not None:
        ck = load_checkpoint(ckpt_path, data_fp, prot_fp)
        if ck is not None:
            model.load_state_dict(ck["model"]); lik.load_state_dict(ck["likelihood"]); ngd.load_state_dict(ck["ngd"])
            if adam is not None:
                adam.load_state_dict(ck["adam"])
            gen.set_state(ck["gen_state"])
            if ck.get("torch_rng_state") is not None:                # v2: the global stream (gpytorch draws its init noise there)
                torch.set_rng_state(ck["torch_rng_state"])
            if not torch.equal(probe, ck["probe"]):
                raise RuntimeError("probe indices differ from the checkpoint")
            trace, stable, prev_elbo, prev_mean = ck["trace"], ck["stable"], ck["prev_elbo"], ck["prev_mean"]
            start, resumed_from = ck["iteration"] + 1, ck["iteration"]
            if ck.get("finished"):
                model.eval(); lik.eval()
                return model, lik, {"status": ck["status"], "iterations": ck["iteration"], "trace": trace, "resumed_from": resumed_from}
    model.train(); lik.train()
    it = start - 1
    for it in range(start, proto["max_iterations"] + 1):
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
        done = False
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
                status = "converged"; done = True
        if ckpt_path is not None and every and (it % every == 0 or done or it == proto["max_iterations"]):
            save_checkpoint(ckpt_path, {"model": model.state_dict(), "likelihood": lik.state_dict(), "ngd": ngd.state_dict(),
                                        "adam": adam.state_dict() if adam is not None else None, "gen_state": gen.get_state(),
                                        "torch_rng_state": torch.get_rng_state(), "probe": probe,
                                        "trace": trace, "stable": stable, "prev_elbo": prev_elbo, "prev_mean": prev_mean, "iteration": it,
                                        "finished": done or it == proto["max_iterations"], "status": status, "data_fp": data_fp, "protocol_fp": prot_fp})
        if done:
            break
        if stop_after is not None and it == stop_after:
            return None, None, {"status": "interrupted_for_validation", "iterations": it}
    model.eval(); lik.eval()
    return model, lik, {"status": status, "iterations": it, "trace": trace, "resumed_from": resumed_from}


def _params(model, lik):
    return {k: v.detach().clone() for k, v in list(model.state_dict().items()) + [("lik." + k, v) for k, v in lik.state_dict().items()]}


def validate(threads=1):
    torch.set_num_threads(threads)
    torch.manual_seed(0)
    g = np.random.default_rng(1)
    nz, ns = 120, 30
    Z = g.standard_normal((nz, 4)); S = np.linspace(0, 0.9, ns)
    X = np.c_[np.repeat(Z, ns, 0), np.tile(S, nz)]
    yv = np.sin(X[:, 0]) + 0.5 * np.cos(3 * X[:, 4]) + 0.05 * g.standard_normal(len(X))
    Xt, yt = torch.tensor(X), torch.tensor((yv - yv.mean()) / yv.std())
    proto = {**F.PROTOCOL, "max_iterations": 600, "check_every": 100, "min_iterations": 200, "lr_halving_at": [200, 400], "minibatch": 256,
             "probe_points": 1024, "seed": 777, "threads": threads}
    OUT.mkdir(parents=True, exist_ok=True)
    t0 = time.time()
    # v2: every fresh run starts from the same global torch RNG state, as a fresh process would (gpytorch draws the
    # initial natural-parameter noise from the global stream); the resumed run starts from a deliberately different
    # global state, so its continuation relies on the checkpointed state alone
    torch.manual_seed(GLOBAL_SEED)
    mF, lF, iF = F.train(Xt, yt, 40, proto)
    torch.manual_seed(GLOBAL_SEED)
    mA, lA, iA = train_resumable(Xt, yt, 40, proto)
    pF, pA = _params(mF, lF), _params(mA, lA)
    same_as_frozen = all(torch.equal(pF[k], pA[k]) for k in pF) and iF["trace"] == iA["trace"]
    ck = OUT / "validation_ckpt.pt"
    for p in (ck, ck.with_suffix(".pt.json")):
        if p.exists():
            p.unlink()
    torch.manual_seed(GLOBAL_SEED)
    train_resumable(Xt, yt, 40, proto, ckpt_path=ck, every=150, stop_after=300)           # "killed" right after iteration 300
    torch.manual_seed(GLOBAL_SEED + 12345)
    mB, lB, iB = train_resumable(Xt, yt, 40, proto, ckpt_path=ck, every=150)                # fresh objects, resume at 301
    pB = _params(mB, lB)
    with torch.no_grad():
        xq = Xt[:50]
        pred_same = bool(torch.equal(mA(xq).mean, mB(xq).mean) and torch.equal(mA(xq).variance, mB(xq).variance))
    resume_identical = all(torch.equal(pA[k], pB[k]) for k in pA) and iA["trace"] == iB["trace"] and pred_same
    # corrupted checkpoint must be refused
    blob = bytearray(ck.read_bytes()); blob[len(blob) // 2] ^= 0xFF
    bad = OUT / "validation_ckpt_corrupt.pt"; bad.write_bytes(bytes(blob)); (bad.with_suffix(".pt.json")).write_text(ck.with_suffix(".pt.json").read_text())
    data_fp, prot_fp = _fingerprint(Xt, yt, proto)
    try:
        load_checkpoint(bad, data_fp, prot_fp); refused = False
    except RuntimeError:
        refused = True
    # an interrupted write leaves a stale .tmp; the previous checkpoint stays valid
    (ck.with_suffix(".pt.tmp")).write_bytes(b"partial write")
    still_valid = load_checkpoint(ck, data_fp, prot_fp) is not None
    # a checkpoint for other data is refused
    try:
        load_checkpoint(ck, hashlib.sha256(b"other").hexdigest(), prot_fp); wrong_data_refused = False
    except RuntimeError:
        wrong_data_refused = True
    res = {"status": "PASS" if (same_as_frozen and resume_identical and refused and still_valid and wrong_data_refused) else "FAIL",
           "torch_threads": torch.get_num_threads(), "torch": torch.__version__, "gpytorch": gpytorch.__version__,
           "uninterrupted_resumable_equals_frozen_train_bitwise": same_as_frozen, "resumed_at_iteration": iB.get("resumed_from"),
           "interrupted_and_resumed_equals_uninterrupted_bitwise": resume_identical, "corrupted_checkpoint_refused": refused,
           "stale_tmp_leaves_checkpoint_valid": still_valid, "other_data_refused": wrong_data_refused, "status_frozen_run": iF["status"],
           "iterations": iA["iterations"], "seconds": time.time() - t0, "note": "validation of the mechanism only; not used by any running or completed study fit",
           "version": "v2", "module_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
           "global_rng_control": f"torch.manual_seed({GLOBAL_SEED}) before every fresh run; the resumed run starts from seed {GLOBAL_SEED + 12345} and must rely on the checkpointed generator and global RNG states",
           "previous_attempt": "CHECKPOINT_MECHANISM_VALIDATION.json (queue T11, 2026-10-14 22:25 UTC): FAIL on both bitwise checks because the harness seeded the global RNG once, so the compared runs started from different gpytorch initialisations; kept unchanged"}
    for p in (bad, bad.with_suffix(".pt.json"), ck.with_suffix(".pt.tmp")):
        if p.exists():
            p.unlink()
    (OUT / "CHECKPOINT_MECHANISM_VALIDATION_v2.json").write_text(json.dumps(res, indent=1), encoding="utf-8")
    print(json.dumps(res, indent=1))
    return res


if __name__ == "__main__":
    if (sys.argv[1] if len(sys.argv) > 1 else "validate") == "validate":
        validate()
