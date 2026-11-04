"""Core PROMETHEE I / II implementation (own code, numpy only).

Notation
--------
* ``X``      – performance matrix, shape (n_alternatives, n_criteria)
* ``w``      – criteria weights (normalised to sum 1)
* ``P_j(a,b)`` – unicriterion preference degree of ``a`` over ``b`` on criterion j
* ``pi(a,b) = sum_j w_j P_j(a,b)`` – aggregated preference index
* ``phi+ (a) = 1/(n-1) sum_b pi(a,b)`` – positive (leaving) flow
* ``phi- (a) = 1/(n-1) sum_b pi(b,a)`` – negative (entering) flow
* ``phi  (a) = phi+(a) - phi-(a)``     – net flow (PROMETHEE II)

Because ``phi(a) = sum_j w_j phi_j(a)`` (``phi_j`` = unicriterion net flow), the
net flow is *linear in the weights*; the sensitivity module exploits this.
"""
from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path

import numpy as np

# ---------------------------------------------------------------------------
# Preference functions (Brans & Vincke, 6 generalised criteria)
# d = difference g(a) - g(b) already oriented so that "positive = better"
# ---------------------------------------------------------------------------


def _usual(d, q=0.0, p=0.0, s=0.0):
    return (d > 0).astype(float)


def _u_shape(d, q=0.0, p=0.0, s=0.0):
    return (d > q).astype(float)


def _v_shape(d, q=0.0, p=1.0, s=0.0):
    return np.clip(d / p, 0.0, 1.0) * (d > 0)


def _level(d, q=0.0, p=1.0, s=0.0):
    return np.where(d > p, 1.0, np.where(d > q, 0.5, 0.0))


def _linear(d, q=0.0, p=1.0, s=0.0):
    span = p - q if p > q else 1.0          # p == q degenerates to U-shape
    return np.where(d > p, 1.0, np.where(d > q, (d - q) / span, 0.0))


def _gaussian(d, q=0.0, p=0.0, s=1.0):
    return np.where(d > 0, 1.0 - np.exp(-(d**2) / (2 * s**2)), 0.0)


PREFERENCE_FUNCTIONS = {
    "usual": _usual,        # type I
    "u-shape": _u_shape,    # type II   (q)
    "v-shape": _v_shape,    # type III  (p)
    "level": _level,        # type IV   (q, p)
    "linear": _linear,      # type V    (q, p)  "V-shape with indifference"
    "gaussian": _gaussian,  # type VI   (s)
}


@dataclass
class Criterion:
    id: str
    name: str
    direction: str = "max"          # "max" or "min"
    function: str = "usual"
    q: float = 0.0
    p: float = 0.0
    s: float = 0.0

    def preference(self, d: np.ndarray) -> np.ndarray:
        if self.direction == "min":
            d = -d
        fn = PREFERENCE_FUNCTIONS[self.function]
        return fn(d, q=self.q, p=self.p, s=self.s)


@dataclass
class Problem:
    title: str
    alt_ids: list[str]
    alt_names: list[str]
    criteria: list[Criterion]
    X: np.ndarray
    weights: np.ndarray
    weight_scenarios: dict[str, np.ndarray] = field(default_factory=dict)
    group: dict = field(default_factory=dict)

    @property
    def labels(self) -> list[str]:
        return [f"{i} {n}" for i, n in zip(self.alt_ids, self.alt_names)]

    @classmethod
    def from_json(cls, path: str | Path) -> "Problem":
        cfg = json.loads(Path(path).read_text(encoding="utf-8"))
        alt_ids = list(cfg["alternatives"].keys())
        crit = [Criterion(**{k: v for k, v in c.items()}) for c in cfg["criteria"]]
        X = np.array([cfg["performance"][a] for a in alt_ids], dtype=float)
        scen = {k: normalise(v) for k, v in cfg.get("weight_scenarios", {}).items()}
        return cls(
            title=cfg.get("title", "MCDM problem"),
            alt_ids=alt_ids,
            alt_names=[cfg["alternatives"][a] for a in alt_ids],
            criteria=crit,
            X=X,
            weights=normalise(cfg["weights"]),
            weight_scenarios=scen,
            group=cfg.get("group", {}),
        )


def normalise(w) -> np.ndarray:
    w = np.asarray(w, dtype=float)
    if np.any(w < 0) or w.sum() <= 0:
        raise ValueError("weights must be non-negative and not all zero")
    return w / w.sum()


# ---------------------------------------------------------------------------
# PROMETHEE computations
# ---------------------------------------------------------------------------


def preference_matrices(X: np.ndarray, criteria: list[Criterion]) -> np.ndarray:
    """Unicriterion preference degrees, shape (m, n, n): P[j, a, b]."""
    n, m = X.shape
    P = np.empty((m, n, n))
    for j, c in enumerate(criteria):
        d = X[:, j][:, None] - X[:, j][None, :]
        P[j] = c.preference(d)
        np.fill_diagonal(P[j], 0.0)
    return P


def unicriterion_flows(P: np.ndarray) -> np.ndarray:
    """phi_j(a), shape (n, m)."""
    m, n, _ = P.shape
    return ((P.sum(axis=2) - P.sum(axis=1)) / (n - 1)).T


@dataclass
class PrometheeResult:
    pi: np.ndarray
    phi_plus: np.ndarray
    phi_minus: np.ndarray
    phi: np.ndarray
    phi_j: np.ndarray

    def ranking(self) -> np.ndarray:
        """Indices of alternatives from best to worst (PROMETHEE II)."""
        return np.argsort(-self.phi, kind="stable")

    def ranks(self) -> np.ndarray:
        """Rank position (1 = best) of each alternative."""
        return ranks_from_scores(self.phi)


def ranks_from_scores(scores: np.ndarray) -> np.ndarray:
    order = np.argsort(-np.asarray(scores), kind="stable")
    r = np.empty(len(order), dtype=int)
    r[order] = np.arange(1, len(order) + 1)
    return r


def promethee(X: np.ndarray, criteria: list[Criterion], w, P: np.ndarray | None = None
              ) -> PrometheeResult:
    w = normalise(w)
    if P is None:
        P = preference_matrices(X, criteria)
    n = X.shape[0]
    pi = np.tensordot(w, P, axes=1)
    phi_plus = pi.sum(axis=1) / (n - 1)
    phi_minus = pi.sum(axis=0) / (n - 1)
    return PrometheeResult(pi, phi_plus, phi_minus, phi_plus - phi_minus,
                           unicriterion_flows(P))


def promethee_I(res: PrometheeResult, tol: float = 1e-9) -> np.ndarray:
    """PROMETHEE I partial preorder.

    Returns matrix R with R[a,b] in {'P', 'I', 'R', '-'}:
    'P' a outranks b, 'I' indifferent, 'R' incomparable, '-' b outranks a.
    """
    n = len(res.phi)
    R = np.full((n, n), "", dtype=object)
    fp, fm = res.phi_plus, res.phi_minus
    for a in range(n):
        for b in range(n):
            if a == b:
                R[a, b] = "="
                continue
            plus_ge, plus_gt = fp[a] >= fp[b] - tol, fp[a] > fp[b] + tol
            min_le, min_lt = fm[a] <= fm[b] + tol, fm[a] < fm[b] - tol
            plus_eq = abs(fp[a] - fp[b]) <= tol
            min_eq = abs(fm[a] - fm[b]) <= tol
            if plus_eq and min_eq:
                R[a, b] = "I"
            elif plus_ge and min_le and (plus_gt or min_lt):
                R[a, b] = "P"
            elif (fp[b] >= fp[a] - tol) and (fm[b] <= fm[a] + tol):
                R[a, b] = "-"
            else:
                R[a, b] = "R"
    return R


# ---------------------------------------------------------------------------
# Reference method for comparison: weighted sum  S = N x W  ("P x W")
# ---------------------------------------------------------------------------


def weighted_sum(X: np.ndarray, criteria: list[Criterion], w) -> np.ndarray:
    """Simple additive weighting on min-max normalised performances."""
    w = normalise(w)
    lo, hi = X.min(axis=0), X.max(axis=0)
    span = np.where(hi > lo, hi - lo, 1.0)
    N = (X - lo) / span
    for j, c in enumerate(criteria):
        if c.direction == "min":
            N[:, j] = 1.0 - N[:, j]
    return N @ w


# ---------------------------------------------------------------------------
# Rank correlation helpers
# ---------------------------------------------------------------------------


def kendall_tau(r1, r2) -> float:
    r1, r2 = np.asarray(r1), np.asarray(r2)
    n = len(r1)
    s = 0
    for i in range(n):
        for j in range(i + 1, n):
            s += np.sign(r1[i] - r1[j]) * np.sign(r2[i] - r2[j])
    return 2 * s / (n * (n - 1))


def spearman_rho(r1, r2) -> float:
    r1, r2 = np.asarray(r1, float), np.asarray(r2, float)
    n = len(r1)
    return 1 - 6 * np.sum((r1 - r2) ** 2) / (n * (n**2 - 1))
