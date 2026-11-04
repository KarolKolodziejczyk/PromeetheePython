"""Sensitivity analysis for PROMETHEE II (own code).

Contents
--------
* ``stability_intervals`` – exact weight-stability intervals per criterion
  (for the complete ranking and for the first position).
* ``weight_sweep``        – one-at-a-time sweep of a weight from 0 to 1.
* ``threshold_sensitivity`` – scaling of the preference thresholds q, p, s and
  replacement of all preference functions by the "usual" criterion.

All weight analyses use the standard convention: when the weight of criterion
j becomes t, the remaining weights keep their mutual proportions and are
rescaled to sum to 1 - t.
"""
from __future__ import annotations

import copy

import numpy as np

from .core import (Criterion, kendall_tau, normalise, preference_matrices, promethee,
                   ranks_from_scores, unicriterion_flows)


def _phi_rest(phi_j: np.ndarray, w: np.ndarray, j: int) -> np.ndarray:
    """Net flow obtained from all criteria except j (weights renormalised)."""
    rest = np.delete(np.arange(len(w)), j)
    wr = w[rest]
    if wr.sum() == 0:
        return np.zeros(phi_j.shape[0])
    return phi_j[:, rest] @ (wr / wr.sum())


def phi_with_weight(phi_j: np.ndarray, w: np.ndarray, j: int, t: float) -> np.ndarray:
    return t * phi_j[:, j] + (1 - t) * _phi_rest(phi_j, w, j)


def stability_intervals(phi_j: np.ndarray, w, tol: float = 1e-12):
    """Exact stability intervals of each weight.

    phi_a(t) - phi_b(t) is linear in t, so each pair (a,b) swaps order at most
    once; the interval around the current weight is bounded by the closest
    swap points.

    Returns list of dicts with keys: criterion index, weight, ranking interval
    (lo, hi), top-1 interval (lo, hi).
    """
    w = normalise(w)
    n, m = phi_j.shape
    out = []
    for j in range(m):
        pj = phi_j[:, j]
        pr = _phi_rest(phi_j, w, j)
        base = phi_with_weight(phi_j, w, j, w[j])
        best = int(np.argmax(base))
        lo_all, hi_all, lo_top, hi_top = 0.0, 1.0, 0.0, 1.0
        for a in range(n):
            for b in range(a + 1, n):
                dr = pr[a] - pr[b]
                dj = pj[a] - pj[b]
                slope = dj - dr
                if abs(slope) < tol:
                    continue
                t = -dr / slope
                if not (0.0 < t < 1.0):
                    continue
                involves_best = best in (a, b)
                if t <= w[j] + tol:
                    lo_all = max(lo_all, t)
                    if involves_best:
                        lo_top = max(lo_top, t)
                if t >= w[j] - tol:
                    hi_all = min(hi_all, t)
                    if involves_best:
                        hi_top = min(hi_top, t)
        out.append({"j": j, "weight": w[j], "rank_lo": lo_all, "rank_hi": hi_all,
                    "top_lo": lo_top, "top_hi": hi_top, "best": best})
    return out


def weight_sweep(phi_j: np.ndarray, w, j: int, steps: int = 101):
    w = normalise(w)
    ts = np.linspace(0, 1, steps)
    flows = np.array([phi_with_weight(phi_j, w, j, t) for t in ts])
    return ts, flows


def threshold_sensitivity(X: np.ndarray, criteria: list[Criterion], w,
                          factors=(0.25, 0.5, 0.75, 1.0, 1.25, 1.5, 2.0)):
    """Scale all thresholds (q, p, s) by a factor and recompute the ranking.

    Also evaluates the variant where every criterion uses the 'usual'
    preference function (no thresholds at all).
    Returns list of (label, phi, ranks, kendall_tau_vs_base).
    """
    base = promethee(X, criteria, w)
    base_r = base.ranks()
    rows = []
    for f in factors:
        crit = copy.deepcopy(criteria)
        for c in crit:
            c.q, c.p, c.s = c.q * f, c.p * f, c.s * f
        res = promethee(X, crit, w)
        rows.append((f"thresholds x{f:g}", res.phi, res.ranks(),
                     kendall_tau(base_r, res.ranks())))
    crit = copy.deepcopy(criteria)
    for c in crit:
        c.function = "usual"
    res = promethee(X, crit, w)
    rows.append(("all 'usual' (type I)", res.phi, res.ranks(),
                 kendall_tau(base_r, res.ranks())))
    return rows


def single_threshold_sweep(X, criteria, w, j: int, param: str, values):
    """Vary a single threshold of criterion j; return net flows per value."""
    flows = []
    for v in values:
        crit = copy.deepcopy(criteria)
        setattr(crit[j], param, v)
        if crit[j].function in ("linear", "level") and crit[j].q > crit[j].p:
            crit[j].q = crit[j].p
        P = preference_matrices(X, crit)
        flows.append(unicriterion_flows(P) @ normalise(w))
    return np.array(flows)


__all__ = ["stability_intervals", "weight_sweep",
           "threshold_sensitivity", "single_threshold_sweep", "phi_with_weight",
           "ranks_from_scores"]
