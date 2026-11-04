"""Efficiency measuring (own code).

Efficiency (cost vs. benefit)
-----------------------------
The criteria are split into COST criteria (here: price) and BENEFIT criteria
(everything the money buys).  For each alternative two PROMETHEE scores are
computed from the unicriterion net flows phi_j:

    phi_benefit(a) = sum_{j in benefit} w_j phi_j(a) / sum_{j in benefit} w_j
    phi_cost(a)    = sum_{j in cost}    w_j phi_j(a) / sum_{j in cost}    w_j

(higher = better for both; for the price, higher phi = cheaper).
An alternative is EFFICIENT if no other alternative is at least as good on
both scores and strictly better on one (Pareto / non-dominated).  Moving along
the efficient frontier shows how much extra money buys how much extra benefit.

Best choice for a budget
------------------------
Reading the frontier for a budget B: among the printers with price <= B,
take the one with the highest benefit flow.  (This is NOT PROMETHEE V:
PROMETHEE V selects a portfolio, i.e. a combination of several alternatives;
here exactly one printer is bought.)
"""
from __future__ import annotations

from itertools import combinations

import numpy as np

from .core import normalise


def split_flows(phi_j: np.ndarray, w, cost_idx: list[int]):
    """Return (phi_benefit, phi_cost) for every alternative."""
    w = normalise(w)
    m = phi_j.shape[1]
    cost = np.zeros(m, bool)
    cost[list(cost_idx)] = True
    wb, wc = np.where(cost, 0, w), np.where(cost, w, 0)
    return phi_j @ (wb / wb.sum()), phi_j @ (wc / wc.sum())


def efficient_set(benefit: np.ndarray, cost_score: np.ndarray) -> np.ndarray:
    """Boolean mask of non-dominated alternatives (both scores: higher = better)."""
    n = len(benefit)
    eff = np.ones(n, bool)
    for a in range(n):
        for b in range(n):
            if b != a and benefit[b] >= benefit[a] and cost_score[b] >= cost_score[a] \
                    and (benefit[b] > benefit[a] or cost_score[b] > cost_score[a]):
                eff[a] = False
                break
    return eff


def best_within_budget(scores: np.ndarray, costs: np.ndarray, budget: float,
                       min_items: int = 1, max_items: int = 1):
    """Best affordable choice by enumeration. Returns (best subset tuple, total score)."""
    n = len(scores)
    best, best_val = (), -np.inf
    for k in range(min_items, max_items + 1):
        for sub in combinations(range(n), k):
            if costs[list(sub)].sum() <= budget + 1e-9:
                val = scores[list(sub)].sum()
                if val > best_val + 1e-12:
                    best, best_val = sub, val
    return best, best_val


def budget_sweep(scores: np.ndarray, costs: np.ndarray, budgets):
    """Best affordable printer for every budget; -1 = nothing affordable."""
    out = []
    for b in budgets:
        sub, _ = best_within_budget(scores, costs, b)
        out.append(sub[0] if sub else -1)
    return np.array(out)
