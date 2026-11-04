import numpy as np
import pytest

from promethee import Criterion, Problem, promethee, promethee_I, kendall_tau, preference_matrices
from promethee.core import PREFERENCE_FUNCTIONS
from promethee.sensitivity import phi_with_weight, stability_intervals
from promethee.core import weighted_sum
from promethee.efficiency import best_within_budget, efficient_set, split_flows
from promethee.fuzzy import fuzzy_matrix, fuzzy_promethee


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


def test_wsm_reproduces_task1_spreadsheet():
    # Task 1 (KK_MCDM_1.xlsx): U1 0.850, H2D 0.673, K2 0.662, Prusa 0.588 (method 1)
    p = Problem.from_json("data/problem.json")
    s = weighted_sum(p.X, p.criteria, p.weights, "ratio")
    np.testing.assert_allclose(s, [0.66171, 0.85000, 0.67316, 0.58844], atol=1e-4)


def test_efficiency_and_best_within_budget():
    p = Problem.from_json("data/problem.json")
    r = promethee(p.X, p.criteria, p.weights)
    ben, cost = split_flows(r.phi_j, p.weights, [0])
    # benefit + cost flows recombine into the full net flow
    w = p.weights
    np.testing.assert_allclose(w[0] * cost + (1 - w[0]) * ben, r.phi)
    eff = efficient_set(ben, cost)
    assert eff[int(np.argmin(p.X[:, 0]))]          # the cheapest is always efficient
    assert eff[int(np.argmax(ben))]                # the best-benefit one too
    # PROMETHEE V with a budget below every price selects nothing
    assert best_within_budget(ben, p.X[:, 0], 100)[0] == ()
    # with an unlimited budget it selects the highest benefit flow
    assert best_within_budget(ben, p.X[:, 0], 1e9)[0] == (int(np.argmax(ben)),)


def test_kendall_tau():
    assert kendall_tau([1, 2, 3], [1, 2, 3]) == 1
    assert kendall_tau([1, 2, 3], [3, 2, 1]) == -1


def _fuzzy_problem():
    p = Problem.from_json("data/problem.json")
    L, M, U = fuzzy_matrix(p.X, p.criteria, p.alt_ids, p.config["fuzzy"]["values"])
    return p, L, M, U


def test_f_promethee_middle_is_crisp_and_triangles_are_ordered():
    p, L, M, U = _fuzzy_problem()
    fr = fuzzy_promethee(L, M, U, p.criteria, p.weights, 0.1)
    crisp = promethee(p.X, p.criteria, p.weights)
    np.testing.assert_allclose(fr["phi"][:, 1], crisp.phi, atol=1e-12)
    np.testing.assert_allclose(fr["phi_plus"][:, 1], crisp.phi_plus, atol=1e-12)
    assert np.all(fr["phi"][:, 0] <= fr["phi"][:, 1] + 1e-12)
    assert np.all(fr["phi"][:, 1] <= fr["phi"][:, 2] + 1e-12)
    np.testing.assert_allclose(fr["centroid"], fr["phi"].mean(axis=1))


def test_f_promethee_crisp_input_gives_crisp_output():
    p = Problem.from_json("data/problem.json")
    fr = fuzzy_promethee(p.X, p.X, p.X, p.criteria, p.weights)
    crisp = promethee(p.X, p.criteria, p.weights).phi
    for k in range(3):
        np.testing.assert_allclose(fr["phi"][:, k], crisp, atol=1e-12)


def test_f_promethee_contains_random_scenarios():
    """Any matrix and weights inside the TFN supports give phi within [l, u]."""
    p, L, M, U = _fuzzy_problem()
    fr = fuzzy_promethee(L, M, U, p.criteria, p.weights, 0.1)
    rng = np.random.default_rng(5)
    for _ in range(2000):
        w = p.weights * rng.uniform(0.9, 1.1, size=len(p.weights))
        # un-normalised weights inside the fuzzy supports, as in the TFN product
        X = rng.uniform(L, U)
        P = preference_matrices(X, p.criteria)
        pi = np.tensordot(w, P, axes=1)
        n = len(X)
        phi = (pi.sum(axis=1) - pi.sum(axis=0)) / (n - 1)
        assert np.all(phi >= fr["phi"][:, 0] - 1e-9) and np.all(phi <= fr["phi"][:, 2] + 1e-9)


