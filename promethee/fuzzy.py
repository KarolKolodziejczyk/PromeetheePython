"""Fuzzy-set stability analysis of PROMETHEE II (own code).

Idea
----
The decision maker cannot state weights exactly, only "about 0.30".  Each
weight becomes a triangular fuzzy number (l, m, u):

    m = the crisp weight,  l = m (1 - spread),  u = m (1 + spread).

An alpha-cut (0 <= alpha <= 1) of a triangular number is the interval

    [l + alpha (m - l),  u - alpha (u - m)]

alpha = 1 -> only the crisp weight ("fully plausible"),
alpha = 0 -> the whole support [l, u] ("barely plausible").

For every alpha we look at *all* weight vectors that lie inside the alpha-cuts
of every criterion and sum to 1.  Because the net flow is linear in the
weights (phi = sum_j w_j phi_j), the smallest and largest net flow over that
set is a small linear programme with an exact greedy solution: start every
weight at its lower bound, then give the remaining weight to the criteria with
the best (or worst) coefficient first.  This gives

* fuzzy net flows  phi~(a)   – an interval of phi(a) for every alpha;
* guaranteed dominance       – min over the set of phi(a) - phi(b);
  if it is > 0, a beats b for *every* plausible weight vector at that alpha.
"""
from __future__ import annotations

import numpy as np

from .core import normalise


def triangular_weights(w, spread: float):
    m = normalise(w)
    return m * (1 - spread), m, m * (1 + spread)


def alpha_cut(l, m, u, alpha: float):
    return l + alpha * (m - l), u - alpha * (u - m)


def extreme_linear(c: np.ndarray, lo: np.ndarray, hi: np.ndarray, maximize: bool) -> float:
    """max (or min) of sum_j w_j c_j  s.t.  lo <= w <= hi,  sum w = 1 (exact greedy)."""
    lo, hi = np.asarray(lo, float), np.asarray(hi, float)
    if lo.sum() > 1 + 1e-12 or hi.sum() < 1 - 1e-12:
        raise ValueError("alpha-cut box does not intersect the weight simplex")
    w = lo.copy()
    rest = 1.0 - lo.sum()
    order = np.argsort(-c if maximize else c, kind="stable")
    for j in order:
        add = min(hi[j] - lo[j], rest)
        w[j] += add
        rest -= add
        if rest <= 1e-15:
            break
    return float(w @ c)


def fuzzy_flows(phi_j: np.ndarray, w, spread: float, alphas):
    """Lower / upper net flow of every alternative for every alpha-cut.

    Returns (lo, hi), each of shape (len(alphas), n_alternatives).
    """
    l, m, u = triangular_weights(w, spread)
    n = phi_j.shape[0]
    lo = np.empty((len(alphas), n))
    hi = np.empty((len(alphas), n))
    for k, a in enumerate(alphas):
        wl, wu = alpha_cut(l, m, u, a)
        for i in range(n):
            lo[k, i] = extreme_linear(phi_j[i], wl, wu, maximize=False)
            hi[k, i] = extreme_linear(phi_j[i], wl, wu, maximize=True)
    return lo, hi


def guaranteed_margin(phi_j: np.ndarray, w, spread: float, alphas, a: int):
    """min over plausible weights of phi(a) - phi(b), for every alpha and b.

    Shape (len(alphas), n). Column a is meaningless (0).
    """
    l, m, u = triangular_weights(w, spread)
    n = phi_j.shape[0]
    out = np.zeros((len(alphas), n))
    for k, al in enumerate(alphas):
        wl, wu = alpha_cut(l, m, u, al)
        for b in range(n):
            if b != a:
                out[k, b] = extreme_linear(phi_j[a] - phi_j[b], wl, wu, maximize=False)
    return out


def defuzzify(lo: np.ndarray, hi: np.ndarray) -> np.ndarray:
    """Average of alpha-cut midpoints (alphas equally spaced) – a crisp score."""
    return ((lo + hi) / 2).mean(axis=0)


def robust_spread(phi_j: np.ndarray, w, a: int, tol: float = 1e-4) -> float:
    """Largest spread s (<= 1) such that a is best for EVERY weight vector in
    the whole support (alpha = 0) of the triangular fuzzy weights."""
    def ok(s):
        margins = np.delete(guaranteed_margin(phi_j, w, s, [0.0], a)[0], a)
        return margins.min() > 0
    if not ok(0.0):
        return 0.0
    if ok(1.0):
        return 1.0
    lo, hi = 0.0, 1.0
    while hi - lo > tol:
        mid = (lo + hi) / 2
        lo, hi = (mid, hi) if ok(mid) else (lo, mid)
    return lo


def guaranteed_alpha(phi_j: np.ndarray, w, spread: float, a: int, steps: int = 1001) -> float:
    """Smallest alpha from which a is best for EVERY weight vector in the alpha-cut.

    0 -> guaranteed even on the whole support; 1 -> only at the crisp weights.
    """
    alphas = np.linspace(0, 1, steps)
    margins = np.delete(guaranteed_margin(phi_j, w, spread, alphas, a), a, axis=1).min(axis=1)
    ok = margins > 0
    if ok[0]:
        return 0.0
    if not ok.any():
        return 1.0
    k = int(np.argmax(ok))
    m0, m1 = margins[k - 1], margins[k]          # linear interpolation of the crossing
    return float(alphas[k - 1] + (alphas[k] - alphas[k - 1]) * (-m0) / (m1 - m0))
