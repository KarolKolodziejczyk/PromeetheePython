"""Own-code PROMETHEE I/II with sensitivity analysis, F-PROMETHEE and efficiency extension."""
from .core import (Criterion, Problem, PrometheeResult, kendall_tau, normalise,
                   preference_matrices, promethee, promethee_I, ranks_from_scores,
                   spearman_rho, unicriterion_flows, weighted_sum,
                   normalised_matrix)

__all__ = ["Criterion", "Problem", "PrometheeResult", "kendall_tau", "normalise",
           "preference_matrices", "promethee", "promethee_I", "ranks_from_scores",
           "spearman_rho", "unicriterion_flows", "weighted_sum", "normalised_matrix"]
