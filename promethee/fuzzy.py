"""F-PROMETHEE: PROMETHEE II with triangular fuzzy numbers (own code).

Uncertain values of the decision matrix (and optionally the weights) are
triangular fuzzy numbers (TFN) (l, m, u): m = the value used in the crisp
analysis, l / u = the lowest / highest plausible value.

alpha-cuts
----------
For 0 <= alpha <= 1 a TFN becomes the interval [l + alpha (m - l), u - alpha (u - m)]:
alpha = 1 -> only m (the crisp problem), alpha = 0 -> the whole support [l, u].

Fuzzy net flow
--------------
For every alpha we want the smallest and the largest net flow phi(a) over ALL
decision matrices (and weight vectors) inside the alpha-cuts.  This is exact
and cheap because phi(a) is monotone:

* phi(a) grows when a's own values get better and when the other
  alternatives' values get worse (preference functions are non-decreasing);
* phi(a) = sum_j w_j phi_j(a) is linear in the weights.

So max phi(a): a at the good end of its intervals, all others at the bad end,
then the weights that favour a's best criteria (greedy linear programme).
min phi(a): the opposite.  The result {[min, max] for every alpha} is the
fuzzy net flow of a.

Guaranteed dominance
--------------------
min of phi(a) - phi(b) over everything plausible at level alpha.  a is put at
its bad end and b at its good end; every third alternative c is chosen
separately per criterion (the expression is separable) on a fine grid; then
the weights.  If the minimum is > 0, a beats b for every plausible matrix
and weight vector at that alpha.
"""
from __future__ import annotations

import numpy as np

from .core import Criterion, normalise, promethee


# ---------------------------------------------------------------- weights
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
    for j in np.argsort(-c if maximize else c, kind="stable"):
        add = min(hi[j] - lo[j], rest)
        w[j] += add
        rest -= add
        if rest <= 1e-15:
            break
    return float(w @ c)


# --------------------------------------------------------- fuzzy matrix
def fuzzy_matrix(X: np.ndarray, criteria: list[Criterion], alt_ids: list[str], spec: list[dict]):
    """Build TFN matrix (L, M, U) from the JSON spec; criteria not listed stay crisp."""
    X = np.asarray(X, float)
    L, M, U = X.copy(), X.copy(), X.copy()
    ids = [c.id for c in criteria]
    for s in spec:
        j = ids.index(s["criterion"])
        if "relative" in s:
            L[:, j], U[:, j] = X[:, j] * (1 - s["relative"]), X[:, j] * (1 + s["relative"])
        if "absolute" in s:
            L[:, j], U[:, j] = X[:, j] - s["absolute"], X[:, j] + s["absolute"]
        if "clip" in s:
            L[:, j], U[:, j] = np.clip(L[:, j], *s["clip"]), np.clip(U[:, j], *s["clip"])
        for alt, (lo, mid, hi) in s.get("override", {}).items():
            i = alt_ids.index(alt)
            L[i, j], M[i, j], U[i, j] = lo, mid, hi
    return L, M, U


def matrix_cut(L, M, U, alpha: float):
    return L + alpha * (M - L), U - alpha * (U - M)


def _end(lo, hi, crit: Criterion, good: bool):
    """Value at the good (or bad) end of an interval for this criterion."""
    if crit.direction == "max":
        return hi if good else lo
    return lo if good else hi


def _weight_cut(w, w_spread, alpha):
    return alpha_cut(*triangular_weights(w, w_spread), alpha)


# --------------------------------------------------------- fuzzy flows
def fuzzy_net_flows(L, M, U, criteria, w, w_spread: float, alphas):
    """(lo, hi) of the fuzzy net flow, shape (len(alphas), n) each."""
    n, m = L.shape
    lo = np.empty((len(alphas), n))
    hi = np.empty((len(alphas), n))
    for k, al in enumerate(alphas):
        clo, chi = matrix_cut(L, M, U, al)
        wl, wu = _weight_cut(w, w_spread, al)
        for a in range(n):
            for maximize, out in ((True, hi), (False, lo)):
                C = np.empty((n, m))
                for j, c in enumerate(criteria):
                    C[:, j] = _end(clo[:, j], chi[:, j], c, good=not maximize)
                    C[a, j] = _end(clo[a, j], chi[a, j], c, good=maximize)
                phi_j_a = promethee(C, criteria, w).phi_j[a]
                out[k, a] = extreme_linear(phi_j_a, wl, wu, maximize)
    return lo, hi


def guaranteed_margin(L, M, U, criteria, w, w_spread: float, alpha: float, a: int, b: int,
                      grid: int = 41) -> float:
    """min over all plausible matrices and weights (at alpha) of phi(a) - phi(b)."""
    n, m = L.shape
    clo, chi = matrix_cut(L, M, U, alpha)
    D = np.zeros(m)
    for j, c in enumerate(criteria):
        ga = _end(clo[a, j], chi[a, j], c, good=False)
        gb = _end(clo[b, j], chi[b, j], c, good=True)
        P = lambda x, y: float(c.preference(np.array([x - y]))[0])  # noqa: E731
        total = 2 * (P(ga, gb) - P(gb, ga))
        for k in range(n):
            if k in (a, b):
                continue
            g = np.linspace(clo[k, j], chi[k, j], grid)
            term = (c.preference(ga - g) - c.preference(g - ga)
                    - c.preference(gb - g) + c.preference(g - gb))
            total += term.min()
        D[j] = total / (n - 1)
    wl, wu = _weight_cut(w, w_spread, alpha)
    return extreme_linear(D, wl, wu, maximize=False)


def guaranteed_alpha(L, M, U, criteria, w, w_spread: float, a: int, steps: int = 101) -> float:
    """Smallest alpha from which a beats every other alternative for ALL plausible
    values and weights.  0 = guaranteed on the whole support, 1 = only crisp."""
    n = L.shape[0]
    alphas = np.linspace(0, 1, steps)
    margins = np.array([min(guaranteed_margin(L, M, U, criteria, w, w_spread, al, a, b)
                            for b in range(n) if b != a) for al in alphas])
    ok = margins > 0
    if ok[0]:
        return 0.0
    if not ok.any():
        return 1.0
    k = int(np.argmax(ok))
    m0, m1 = margins[k - 1], margins[k]
    return float(alphas[k - 1] + (alphas[k] - alphas[k - 1]) * (-m0) / (m1 - m0))


def defuzzify(lo: np.ndarray, hi: np.ndarray) -> np.ndarray:
    """Average of the alpha-cut midpoints (alphas equally spaced) -> crisp score."""
    return ((lo + hi) / 2).mean(axis=0)
