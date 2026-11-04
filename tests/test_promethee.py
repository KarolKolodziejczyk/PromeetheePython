import numpy as np
import pytest

from promethee import Criterion, Problem, promethee, promethee_I, kendall_tau
from promethee.core import PREFERENCE_FUNCTIONS
from promethee.sensitivity import phi_with_weight, stability_intervals, monte_carlo
from promethee.core import weighted_sum
from promethee.sort import flowsort


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


def test_wsm_reproduces_task1_spreadsheet():
    # Task 1 (KK_MCDM_1.xlsx): U1 0.850, H2D 0.673, K2 0.662, Prusa 0.588 (method 1)
    p = Problem.from_json("data/problem.json")
    s = weighted_sum(p.X, p.criteria, p.weights, "ratio")
    np.testing.assert_allclose(s, [0.66171, 0.85000, 0.67316, 0.58844], atol=1e-4)


def test_flowsort_extremes():
    p = Problem.from_json("data/problem.json")
    R = np.array(list(p.config["sort"]["profiles"].values()), float)
    # an alternative equal to the ideal profile -> best class,
    # one far worse than the limits -> below the lowest class
    X = np.vstack([R[0], R[-1] * np.array([2, 1.5, 0.5, 0.5, 0.5, 0.5])])
    o = flowsort(X, p.criteria, p.weights, R)
    assert o["net"][0] == 0
    assert o["net"][1] == len(R) - 1


def test_kendall_tau():
    assert kendall_tau([1, 2, 3], [1, 2, 3]) == 1
    assert kendall_tau([1, 2, 3], [3, 2, 1]) == -1
