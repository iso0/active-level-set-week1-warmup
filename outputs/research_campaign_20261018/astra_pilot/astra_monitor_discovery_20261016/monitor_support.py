"""No data access and no fitting. Physical-time integration and a fixed time basis.

Helpers require paid traces or evaluator-owned traces. No extrapolation, gap
bridging, absent-phase imputation, or replacement of canonical labels is allowed.
"""
from __future__ import annotations
import math


def time_summary(times_s, values, *, planned_end_s, observed_end_s,
                 threshold=None, max_gap_s, valid=None):
    """Piecewise-linear integration; invalid endpoints remove the whole interval.

    Return valid duration and missing duration EXPLICITLY. This is a numerical
    convention, not evidence that unobserved excursions between samples are absent.
    No row-count averaging: unequal solver time steps receive unequal weight.
    """
    t, q = list(times_s), list(values)
    if len(t) != len(q) or len(t) < 2:
        raise ValueError("aligned time/value arrays of length >=2 required")
    if any(not math.isfinite(v) for v in t) or any(b <= a for a, b in zip(t, t[1:])):
        raise ValueError("time must be finite and strictly increasing")
    if not (planned_end_s > 0 and 0 < observed_end_s <= planned_end_s and max_gap_s > 0):
        raise ValueError("invalid physical support")
    mask = [math.isfinite(v) for v in q]
    if valid is not None:
        if len(valid) != len(q):
            raise ValueError("valid mask not aligned")
        mask = [a and bool(b) for a, b in zip(mask, valid)]
    duration = integral = squared = above = 0.0
    used_peaks = []
    for j in range(len(t)-1):
        left, right = max(0., t[j]), min(observed_end_s, t[j+1])
        if right <= left or t[j+1]-t[j] > max_gap_s or not (mask[j] and mask[j+1]):
            continue
        a = q[j]+(q[j+1]-q[j])*(left-t[j])/(t[j+1]-t[j])
        b = q[j]+(q[j+1]-q[j])*(right-t[j])/(t[j+1]-t[j])
        dt = right-left
        duration += dt
        integral += dt*(a+b)/2
        squared += dt*(a*a+a*b+b*b)/3
        used_peaks.extend(((a, left), (b, right)))
        if threshold is not None:
            if a > threshold and b > threshold:
                above += dt
            elif a <= threshold and b <= threshold:
                pass
            else:
                frac = (threshold-a)/(b-a)
                above += dt*((1-frac) if b > a else frac)
    # A native isolated finite sample is recorded separately from interval-supported peaks.
    native = [(v, s) for s, v, ok in zip(t, q, mask) if ok and 0 <= s <= observed_end_s]
    peak = max(native, key=lambda a: a[0]) if native else (None, None)
    supported_peak = max(used_peaks, key=lambda a: a[0]) if used_peaks else (None, None)
    return {"valid_duration_s": duration, "observed_end_s": observed_end_s,
            "planned_end_s": planned_end_s, "missing_planned_duration_s": max(0., planned_end_s-duration),
            "support_fraction": duration/planned_end_s, "integral": integral if duration else None,
            "time_mean": integral/duration if duration else None,
            "time_rms": math.sqrt(max(0., squared/duration)) if duration else None,
            "native_peak": peak[0], "native_peak_time_s": peak[1],
            "interval_supported_peak": supported_peak[0],
            "duration_above_s": above if threshold is not None and duration else None,
            "nonfinite_rows": sum(not math.isfinite(v) for v in q),
            "invalid_rows": sum(not v for v in mask),
            "truncated": observed_end_s < planned_end_s}


def time_basis(tau, knots=(0., .18, .36, .54, .72, .9)):
    """Six piecewise-linear hat functions of tau=t/derived_exit, not record end."""
    if not math.isfinite(tau) or tau < knots[0] or tau > knots[-1]:
        raise ValueError("no basis extrapolation beyond declared time domain")
    b = [0.]*len(knots)
    if tau == knots[-1]:
        b[-1] = 1.
        return b
    for j in range(len(knots)-1):
        if knots[j] <= tau < knots[j+1]:
            w = (tau-knots[j])/(knots[j+1]-knots[j])
            b[j], b[j+1] = 1-w, w
            return b
    raise ValueError("bad knots")


def input_time_kernel(x, tau, z, sigma, *, length=.3, amplitude=1.):
    """PSD k_x(x,z) b(tau)^T b(sigma), rank six in time, four inputs + time."""
    if len(x) != 4 or len(z) != 4 or length <= 0 or amplitude <= 0:
        raise ValueError("four features and positive kernel parameters required")
    r = math.sqrt(sum((a-b)**2 for a, b in zip(x, z))) / length
    v = math.sqrt(3)*r
    return amplitude**2*(1+v)*math.exp(-v)*sum(a*b for a, b in zip(time_basis(tau), time_basis(sigma)))
