"""Group decision-making extension (PROMETHEE GDSS-style aggregation).

Each decision maker (DM) k has own criteria weights w^k (the performance
table and preference functions are shared).  Individual net flows phi^k are
computed with PROMETHEE II and aggregated with DM importance weights

    phi_group(a) = sum_k  lambda_k * phi^k(a)

which is equivalent to running PROMETHEE II with the "group" weights
w_group = sum_k lambda_k w^k (flows are linear in the weights).
"""
from __future__ import annotations

import numpy as np

from .core import kendall_tau, normalise, ranks_from_scores


def group_flows(phi_j: np.ndarray, dm_weights: dict[str, np.ndarray],
                importance: dict[str, float]):
    names = list(dm_weights)
    lam = normalise([importance[k] for k in names])
    indiv = np.array([phi_j @ normalise(dm_weights[k]) for k in names])  # (K, n)
    group = lam @ indiv
    return names, lam, indiv, group


def consensus(indiv: np.ndarray, group: np.ndarray):
    """Kendall tau of every DM ranking vs the group ranking and pairwise."""
    K = indiv.shape[0]
    ranks = [ranks_from_scores(f) for f in indiv]
    g = ranks_from_scores(group)
    vs_group = np.array([kendall_tau(r, g) for r in ranks])
    pair = np.ones((K, K))
    for a in range(K):
        for b in range(K):
            pair[a, b] = kendall_tau(ranks[a], ranks[b])
    return vs_group, pair


def importance_simplex_winners(indiv: np.ndarray, resolution: int = 100):
    """For 3 DMs: winner for every importance vector on a triangular grid.

    Returns arrays (l1, l2, l3, winner_index).
    """
    if indiv.shape[0] != 3:
        raise ValueError("simplex map is implemented for exactly 3 DMs")
    pts = []
    for i in range(resolution + 1):
        for j in range(resolution + 1 - i):
            k = resolution - i - j
            lam = np.array([i, j, k]) / resolution
            pts.append((*lam, int(np.argmax(lam @ indiv))))
    return np.array(pts)


def importance_monte_carlo(indiv: np.ndarray, n_samples: int = 20000, seed: int = 7):
    """Share of random DM importance vectors for which each alternative wins."""
    rng = np.random.default_rng(seed)
    L = rng.dirichlet(np.ones(indiv.shape[0]), size=n_samples)
    winners = np.argmax(L @ indiv, axis=1)
    return np.bincount(winners, minlength=indiv.shape[1]) / n_samples
