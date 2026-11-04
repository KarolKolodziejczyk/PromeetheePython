"""F-PROMETHEE with triangular fuzzy numbers (own code).

Every uncertain value is a triangular fuzzy number (TFN) (l, m, u):
m = the value used in the crisp analysis, l / u = lowest / highest plausible.
Crisp values are TFNs with l = m = u.

All PROMETHEE steps are done on the three numbers (l, m, u) with standard
TFN arithmetic (cf. Goumas & Lygerou, 2000):

1. fuzzy difference      d~ = a~ - b~ = (a_l - b_u,  a_m - b_m,  a_u - b_l)
2. fuzzy preference      P~ = (P(d_l), P(d_m), P(d_u))   (sorted, so l <= m <= u)
3. fuzzy index           pi~(a,b) = sum_j w_j P~_j(a,b)          (crisp weights)
4. fuzzy flows           phi+~ = mean_b pi~(a,b),   phi-~ = mean_b pi~(b,a)
5. fuzzy net flow        phi~ = phi+~ - phi-~ = (phi+_l - phi-_u, phi+_m - phi-_m, phi+_u - phi-_l)
6. ranking               centroid (l + m + u) / 3

The middle value m is exactly the crisp PROMETHEE II net flow.
"""
from __future__ import annotations

import numpy as np

from .core import Criterion, normalise


def fuzzy_matrix(X: np.ndarray, criteria: list[Criterion], alt_ids: list[str], spec: list[dict]):
    """Build the TFN matrix (L, M, U) from the JSON spec; unlisted criteria stay crisp."""
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


def fuzzy_promethee(L, M, U, criteria: list[Criterion], w):
    """F-PROMETHEE II. Returns dict with TFN arrays of shape (n, 3) = (l, m, u):
    'pi' (n, n, 3), 'phi_plus', 'phi_minus', 'phi', and 'centroid' (n,)."""
    w = normalise(w)
    n, m = L.shape
    pi = np.zeros((n, n, 3))
    for j, c in enumerate(criteria):
        for a in range(n):
            for b in range(n):
                if a == b:
                    continue
                d = np.array([L[a, j] - U[b, j], M[a, j] - M[b, j], U[a, j] - L[b, j]])
                pi[a, b] += w[j] * np.sort(c.preference(d))
    phi_plus = pi.sum(axis=1) / (n - 1)
    phi_minus = pi.sum(axis=0) / (n - 1)
    phi = np.stack([phi_plus[:, 0] - phi_minus[:, 2],
                    phi_plus[:, 1] - phi_minus[:, 1],
                    phi_plus[:, 2] - phi_minus[:, 0]], axis=1)
    return {"pi": pi, "phi_plus": phi_plus, "phi_minus": phi_minus, "phi": phi,
            "centroid": phi.mean(axis=1)}
