"""FlowSort – PROMETHEE-based sorting (Nemery & Lamboray, 2008).

K ordered classes C_1 (best) ... C_K (worst) are delimited by K+1 limiting
profiles r_1 (upper bound of C_1) ... r_{K+1} (lower bound of C_K).

Each alternative a is evaluated *alone* against the profiles: PROMETHEE flows
are computed on the set R ∪ {a}, so the class of a does not depend on which
other printers are being compared (unlike a ranking).

Assignment rules
* net flow : a -> C_k  if  phi(r_k) >= phi(a) > phi(r_{k+1})
* phi+     : a -> C_k  if  phi+(r_k) >= phi+(a) > phi+(r_{k+1})
* phi-     : a -> C_k  if  phi-(r_k) <  phi-(a) <= phi-(r_{k+1})
If a is better than r_1 it goes to C_1; if it is worse than r_{K+1} it is
"below" the lowest class (index K, i.e. outside the accepted classes).
When the phi+ and phi- assignments differ, the alternative lies in the
interval of classes between them (imprecise assignment).
"""
from __future__ import annotations

import numpy as np

from .core import Criterion, normalise, promethee


def check_profiles(R: np.ndarray, criteria: list[Criterion]) -> None:
    """Profiles must dominate each other: r_k at least as good as r_{k+1}."""
    for k in range(len(R) - 1):
        for j, c in enumerate(criteria):
            better = R[k, j] <= R[k + 1, j] if c.direction == "min" else R[k, j] >= R[k + 1, j]
            if not better:
                raise ValueError(f"profile {k + 1} does not dominate profile {k + 2} "
                                 f"on criterion {c.id}")


def _class_index(val, prof, higher_is_better=True, tol=1e-12):
    """C_k if val is strictly better than the lower bound r_{k+1} of C_k.

    Exactly meeting the lowest profile still counts as the lowest class.
    """
    K = len(prof) - 1
    sign = 1.0 if higher_is_better else -1.0
    for k in range(K):
        margin = sign * (val - prof[k + 1])
        if margin > tol or (k == K - 1 and margin >= -tol):
            return k
    return K  # below the lowest profile


def flowsort(X: np.ndarray, criteria: list[Criterion], w, R: np.ndarray):
    """Return dict with per-alternative class indices and the flows used.

    Class index k = 0 .. K-1 for C_1..C_K, K = "below the lowest profile".
    """
    w = normalise(w)
    R = np.asarray(R, float)
    check_profiles(R, criteria)
    out = {"net": [], "plus": [], "minus": [], "phi": [], "profile_phi": []}
    for a in range(X.shape[0]):
        S = np.vstack([R, X[a]])
        res = promethee(S, criteria, w)
        phi_r, phi_a = res.phi[:-1], res.phi[-1]
        out["net"].append(_class_index(phi_a, phi_r, True))
        out["plus"].append(_class_index(res.phi_plus[-1], res.phi_plus[:-1], True))
        out["minus"].append(_class_index(res.phi_minus[-1], res.phi_minus[:-1], False))
        out["phi"].append(phi_a)
        out["profile_phi"].append(phi_r)
    for k in ("net", "plus", "minus"):
        out[k] = np.array(out[k])
    out["phi"] = np.array(out["phi"])
    out["profile_phi"] = np.array(out["profile_phi"])
    return out


def class_acceptability(X, criteria, w, R, n_samples: int = 5000, spread: float = 0.2,
                        mode: str = "local", seed: int = 3):
    """Share of random weight vectors assigning each alternative to each class.

    Returns array (n_alternatives, K+1); last column = below lowest profile.
    """
    rng = np.random.default_rng(seed)
    m = len(criteria)
    K = len(R) - 1
    if mode == "local":
        W = normalise(w) * rng.uniform(1 - spread, 1 + spread, size=(n_samples, m))
    else:
        W = rng.dirichlet(np.ones(m), size=n_samples)
    W /= W.sum(axis=1, keepdims=True)
    counts = np.zeros((X.shape[0], K + 1))
    for wk in W:
        cls = flowsort(X, criteria, wk, R)["net"]
        counts[np.arange(X.shape[0]), cls] += 1
    return counts / n_samples
