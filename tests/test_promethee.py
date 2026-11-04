import numpy as np
import pytest

from promethee import Criterion, Problem, promethee, promethee_I, kendall_tau
from promethee.core import PREFERENCE_FUNCTIONS
from promethee.sensitivity import phi_with_weight, stability_intervals, monte_carlo
from promethee.group import group_flows


def test_preference_functions_shapes():
    d = np.array([-1.0, 0.0, 1.0, 2.0, 3.0, 5.0])
    assert PREFERENCE_FUNCTIONS["usual"](d).tolist() == [0, 0, 1, 1, 1, 1]
    assert PREFERENCE_FUNCTIONS["u-shape"](d, q=2).tolist() == [0, 0, 0, 0, 1, 1]
    assert PREFERENCE_FUNCTIONS["v-shape"](d, p=4).tolist() == [0, 0, .25, .5, .75, 1]
    assert PREFERENCE_FUNCTIONS["level"](d, q=1, p=3).tolist() == [0, 0, 0, .5, .5, 1]
    assert PREFERENCE_FUNCTIONS["linear"](d, q=1, p=3).tolist() == [0, 0, 0, .5, 1, 1]
    g = PREFERENCE_FUNCTIONS["gaussian"](d, s=1)
    assert g[0] == 0 and g[1] == 0 and g[2] == pytest.approx(1 - np.exp(-0.5))


def test_hand_computed_example():
    # 3 alternatives, 2 criteria (max, min), usual + v-shape(p=10)
    X = np.array([[10, 50], [8, 40], [6, 60]], dtype=float)
    crit = [Criterion("c1", "c1", "max", "usual"),
            Criterion("c2", "c2", "min", "v-shape", p=10)]
    r = promethee(X, crit, [0.5, 0.5])
    # pi(a1,a2)=.5*1 + .5*0 = .5 ; pi(a1,a3)=.5+.5*1=1 ; pi(a2,a1)=.5*1=.5
    # pi(a2,a3)=.5+.5=1 ; pi(a3,a1)=0 ; pi(a3,a2)=0
    expected_pi = np.array([[0, .5, 1], [.5, 0, 1], [0, 0, 0]])
    np.testing.assert_allclose(r.pi, expected_pi)
    np.testing.assert_allclose(r.phi_plus, [.75, .75, 0])
    np.testing.assert_allclose(r.phi_minus, [.25, .25, 1])
    np.testing.assert_allclose(r.phi, [.5, .5, -1])
    assert abs(r.phi.sum()) < 1e-12
    R = promethee_I(r)
    assert R[0, 1] == "I" and R[0, 2] == "P" and R[2, 0] == "-"


def test_net_flow_is_weighted_unicriterion_flows():
    p = Problem.from_json("data/problem.json")
    r = promethee(p.X, p.criteria, p.weights)
    np.testing.assert_allclose(r.phi, r.phi_j @ p.weights)
    assert abs(r.phi.sum()) < 1e-12


def test_stability_intervals_are_exact():
    p = Problem.from_json("data/problem.json")
    r = promethee(p.X, p.criteria, p.weights)
    base_order = np.argsort(-r.phi).tolist()
    for s in stability_intervals(r.phi_j, p.weights):
        j = s["j"]
        eps = 1e-6
        for t in (s["rank_lo"] + eps, s["rank_hi"] - eps):
            o = np.argsort(-phi_with_weight(r.phi_j, p.weights, j, t)).tolist()
            assert o == base_order
        for t, inside in ((s["rank_lo"] - eps, s["rank_lo"] > 0),
                          (s["rank_hi"] + eps, s["rank_hi"] < 1)):
            if inside:
                o = np.argsort(-phi_with_weight(r.phi_j, p.weights, j, t)).tolist()
                assert o != base_order


def test_monte_carlo_rows_sum_to_one():
    p = Problem.from_json("data/problem.json")
    r = promethee(p.X, p.criteria, p.weights)
    acc, mean_rank, _ = monte_carlo(r.phi_j, n_samples=500)
    np.testing.assert_allclose(acc.sum(axis=1), 1)
    np.testing.assert_allclose(acc.sum(axis=0), 1)


def test_group_equals_promethee_with_mixed_weights():
    p = Problem.from_json("data/problem.json")
    r = promethee(p.X, p.criteria, p.weights)
    dms = {k: np.array(v["weights"]) for k, v in p.group["decision_makers"].items()}
    imp = {k: v["importance"] for k, v in p.group["decision_makers"].items()}
    names, lam, indiv, group = group_flows(r.phi_j, dms, imp)
    w_mix = sum(l * dms[k] / dms[k].sum() for l, k in zip(lam, names))
    np.testing.assert_allclose(group, promethee(p.X, p.criteria, w_mix).phi)


def test_kendall_tau():
    assert kendall_tau([1, 2, 3], [1, 2, 3]) == 1
    assert kendall_tau([1, 2, 3], [3, 2, 1]) == -1
