"""GT systems (PROTOCOL_GT.md section 4; registered 9dcee41f before any result). Paid outcomes and public inputs only.

Every GP is C1's engine unchanged (src.ea_cand.gp_fit: GPMAP, Matern-3/2 ARD on the standardised log inputs, physics trend theta * z_h with
theta ~ N(0, 3^2) integrated, the weak MAP hyperprior, two starts, RC18 quality weights 1e4 for short records); only the target changes.
  GEO_A1 / GEO_A2  separate GPs on log d (= C1's depth GP) and log w (W_A / W_atA); m = m_d - m_w + log 2, v = v_d + v_w (independent
                   posteriors, stated assumption); P = Phi(m / sqrt(v_obs))
  GEO_B1/B2/B3     one GP on g1 / g2 / g3; P = Phi(m_g / sqrt(v_obs))
  CAL_B1           1-D Bayesian logistic (C1's classifier family, one feature) on s = m_g / sqrt(v_obs) of GEO_B1; training s honest K = 10 OOF
  C1_G             C1's classifier + m_g1 as a separately shrunk feature (src.ea_diag.lin_u); honest OOF training features
  C1_T             C1's classifier + predicted Tmax(0.75 ms) as a separately shrunk feature (lin_u); temperature GP = C1's engine; honest OOF
  ORACLE_T         as C1_T with the TRUE Tmax(0.75) where it exists (paid and test rows); evaluator-only diagnostic, never a method
  C1               recomputed exactly as src.ea_cand.predict(SYSTEMS["C1"]) (reuse check against the recorded predictions)
Out-of-fold rule = src.ea_diag2.cf_generic (fold of the j-th paid run = j mod 10; a fold without 3 good rows predicts the mean of the
fold's training values of the SAME target). Observation predictive variances (latent + noise) give the probabilities: the label belongs to
the observed run. One-class rule (label systems only) = C1's.
"""
from __future__ import annotations

import time
import warnings

import numpy as np
from scipy.special import ndtr

import src.ea_cand as CA
import src.ea_diag as DG
import src.gt_data as GD
import src.rc18_campaign as C18
import src.rc19b_keyhole as K
import src.rc20_attr as A
import src.rc22_common as C22
import src.rc24_pac as PC

LOG2 = float(np.log(2.0))
GEO = {"GEO_A1": ("A", "logW1"), "GEO_A2": ("A", "logW2"), "GEO_B1": ("B", "g1"), "GEO_B2": ("B", "g2"), "GEO_B3": ("B", "g3")}
LABEL_SYSTEMS = ("C1", "CAL_B1", "C1_G", "C1_T", "ORACLE_T")
ALL = tuple(GEO) + LABEL_SYSTEMS
TE_MS = 0.75


class Hidden:
    """Outcome table of one task (every row). Learners read it ONLY through paid(rev, key): NaN outside the paid rows."""

    def __init__(self, task, R=None, E=None):
        ids = [str(s) for s in task["ids"]]; R = (GD.runs() if R is None else R).reindex(ids)
        E = GD.early() if E is None else E; pos = {str(s): i for i, s in enumerate(E["ids"])}; k = int(np.flatnonzero(np.isclose(E["grid_ms"], TE_MS))[0])
        self.cols = {"logW1": np.log(R.W_A_um.to_numpy(float)), "logW2": np.log(R.W_atA_um.to_numpy(float)),
                     "g1": R.g1.to_numpy(float), "g2": R.g2.to_numpy(float), "g3": R.g3.to_numpy(float),
                     "Te": np.array([E["Tmax"][pos[s], k] if s in pos else np.nan for s in ids], float)}
        self.n = len(ids)

    def paid(self, rev, key):
        out = np.full(self.n, np.nan); L = rev.paid
        if len(L):
            out[L] = self.cols[key][L]
        return out

    def oracle(self, key):
        """Evaluator-only access (ORACLE_T and evaluation)."""
        return self.cols[key].copy()


def fit_y(task, rev, Z, Y, rows=None):
    """C1's depth_fit_cand with the target Y (paid rows only): CA.gp_fit('phys', prior, STARTS), RC18 quality weights. None if < 3 good."""
    L = rev.paid if rows is None else np.asarray(rows, int); W = np.where(rev.paid_short(), C18.W_SHORT, 1.0)
    Lu = L[np.isfinite(Y[L])]
    if (W[Lu] <= 100).sum() < 3:
        return None
    H = A.hcol(task)[:, None]
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        g = CA.gp_fit(Z[Lu], Y[Lu], H[Lu], W[Lu], "phys", True, CA.STARTS)
    return {"g": g, "H": H, "rows": Lu}


def pred(fit, Z, idx):
    """Latent mean, latent variance, observation variance at idx."""
    return fit["g"].predict(Z[idx], Hs=fit["H"][idx])


def cf(rev, Z, rows, Y, fitter, predictor, Kf=A.KF):
    """src.ea_diag2.cf_generic with the fold fallback taken from the same target Y; also returns the full fit."""
    paid = rev.paid; fold, k = K.folds(len(paid), Kf); F = np.full(len(paid), np.nan)
    for j in range(k):
        tr = paid[fold != j]; f = fitter(tr)
        if f is None:
            v = Y[tr]; v = v[np.isfinite(v)]; F[fold == j] = float(np.mean(v)) if len(v) else 0.0
        else:
            F[fold == j] = predictor(f, paid[fold == j])
    full = fitter(paid); E = predictor(full, rows) if full is not None else np.full(len(rows), np.nanmean(Y[paid]) if np.isfinite(Y[paid]).any() else 0.0)
    return F, E, full


def geo_from_fits(fd, fw, kind, Z, rows):
    """(P, m, v_lat, v_obs) for one GEO system from its fits; None if a fit is missing."""
    if kind == "A":
        if fd is None or fw is None:
            return None
        md, ld, od = pred(fd, Z, rows); mw, lw, ow = pred(fw, Z, rows); m = md - mw + LOG2; vl = ld + lw; vo = od + ow
    else:
        if fw is None:
            return None
        m, vl, vo = pred(fw, Z, rows)
    return ndtr(m / np.sqrt(vo)), m, vl, vo


def one_class(rev):
    y_p = rev.paid_y(); A_p = rev.paid_A(); L = rev.paid; usable = np.isfinite(A_p[L])
    return len(set(y_p[L][usable].tolist())) < 2


def state(task, rev, Z, rows, hid, which=ALL, want_m=("GEO_A1", "GEO_B1")):
    """Probabilities at rows for the requested systems; m (latent mean of g) for want_m; fit success flags; CPU per group."""
    out, aux, cpu, info = {}, {}, {}, {"gp_fail": 0, "gp_fits": 0, "fallback": []}
    L = rev.paid; y = rev.paid_y()[L]; h = A.hcol(task); Yd = rev.paid_Y()[:, PC.DEPTH_COL]
    depth_fitter = lambda r: CA.depth_fit_cand(task, rev, Z, "phys", r, True, CA.STARTS)  # noqa: E731
    mean_pred = lambda f, idx: pred(f, Z, idx)[0]  # noqa: E731

    def note(f):
        info["gp_fits"] += 1
        if f is not None and not f["g"].opt.get("success", True):
            info["gp_fail"] += 1
        return f
    need_d = any(GEO.get(s, ("",))[0] == "A" for s in which) or any(s in LABEL_SYSTEMS for s in which)
    t0 = time.process_time()
    fd = Fd = Ed = None
    if any(s in LABEL_SYSTEMS for s in which):
        Fd, Ed, fd = cf(rev, Z, rows, Yd, depth_fitter, lambda f, idx: PC.depth_predict(f, Z, idx)[0]); note(fd)
    elif need_d:
        fd = note(depth_fitter(None))
    cpu["depth"] = time.process_time() - t0
    fits = {}
    for s in [s for s in which if s in GEO]:
        t1 = time.process_time(); kind, key = GEO[s]
        if key not in fits:
            fits[key] = note(fit_y(task, rev, Z, hid.paid(rev, key)))
        r = geo_from_fits(fd, fits[key], kind, Z, rows)
        if r is None:
            out[s] = np.full(len(rows), 0.5); info["fallback"].append(s); aux[s] = None
        else:
            out[s] = r[0]; aux[s] = r[1:]
        single_depth = not any(x in LABEL_SYSTEMS for x in which)       # with label systems the depth time includes the 10 OOF folds
        cpu[s] = time.process_time() - t1 + (cpu["depth"] if kind == "A" and single_depth else 0.0)
    oc = one_class(rev); info["one_class"] = bool(oc)
    lab = [s for s in which if s in LABEL_SYSTEMS]
    if lab:
        if oc:
            for s in lab:
                out[s] = np.full(len(rows), float(np.mean(y)))
        else:
            hL, hR = h[L], h[rows]
            with warnings.catch_warnings():
                warnings.simplefilter("ignore")
                if "C1" in lab:
                    t1 = time.process_time(); out["C1"] = DG.lin(Fd, hL, y, Ed, hR); cpu["C1"] = time.process_time() - t1 + cpu["depth"]
                if {"CAL_B1", "C1_G"} & set(lab):
                    t1 = time.process_time(); Yg = hid.paid(rev, "g1")
                    fitter = lambda r: fit_y(task, rev, Z, Yg, r)  # noqa: E731

                    def s_pred(f, idx):
                        m, _, vo = pred(f, Z, idx); return m / np.sqrt(vo)
                    tg = time.process_time() - t1
                    if "CAL_B1" in lab:
                        t2 = time.process_time(); Fs, Es, _ = cf(rev, Z, rows, Yg, fitter, s_pred)
                        out["CAL_B1"] = C22.phr_family(np.zeros((len(L), 1)), Fs, y, np.zeros((len(rows), 1)), Es, feats=())[0]
                        cpu["CAL_B1"] = time.process_time() - t2 + tg
                    if "C1_G" in lab:
                        t2 = time.process_time(); Fg, Eg, _ = cf(rev, Z, rows, Yg, fitter, mean_pred)
                        out["C1_G"] = DG.lin_u(hL, Fd, Fg, y, hR, Ed, Eg); cpu["C1_G"] = time.process_time() - t2 + tg + cpu["depth"]
                if {"C1_T", "ORACLE_T"} & set(lab):
                    t1 = time.process_time(); Yt = hid.paid(rev, "Te")
                    Ft, Et, _ = cf(rev, Z, rows, Yt, lambda r: fit_y(task, rev, Z, Yt, r), mean_pred); tt = time.process_time() - t1
                    if "C1_T" in lab:
                        t2 = time.process_time(); out["C1_T"] = DG.lin_u(hL, Fd, Ft, y, hR, Ed, Et); cpu["C1_T"] = time.process_time() - t2 + tt + cpu["depth"]
                    if "ORACLE_T" in lab:
                        t2 = time.process_time(); tru = hid.oracle("Te")
                        Ftr = np.where(np.isfinite(tru[L]), tru[L], Ft); Etr = np.where(np.isfinite(tru[rows]), tru[rows], Et)
                        out["ORACLE_T"] = DG.lin_u(hL, Fd, Ftr, y, hR, Ed, Etr); cpu["ORACLE_T"] = time.process_time() - t2 + tt + cpu["depth"]
    for s in want_m:
        if s in aux and aux[s] is not None:
            info[f"m_{s}"] = aux[s][0]
    info["aux"] = aux
    return {s: out[s] for s in which}, cpu, info
