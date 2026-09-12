"""Unit tests for DSDA mathematical similarity metrics and weighting."""

import math
import pytest
from dsda.metrics import (
    compute_composite_score,
    compute_proximity_similarity,
    compute_topology_similarity,
    compute_toponym_similarity,
    resolve_weights,
)
from dsda.models import DSDAParameters, Point2D


class TestToponymSimilarity:
    """Tests for ToponymMatch S_toponym (Equation A2)."""

    def test_exact_match(self):
        sim = compute_toponym_similarity(["Beni Khiar"], ["Beni Khiar"])
        assert math.isclose(sim, 1.0, rel_tol=1e-5)

    def test_transposition_variation(self):
        # Transposition B. Khiar vs B. Khair
        sim = compute_toponym_similarity(["B. Khiar"], ["B. Khair"])
        assert sim > 0.90

    def test_accent_and_diacritic_invariance(self):
        sim = compute_toponym_similarity(["Béni Khiar"], ["Beni Khiar"])
        assert sim > 0.95

    def test_multiple_aliases_selects_maximum(self):
        extracted = ["B. Khiar", "Station"]
        candidate_aliases = ["Village", "Bir", "B. Khair"]
        # Should pick max similarity (between B. Khiar and B. Khair)
        sim = compute_toponym_similarity(extracted, candidate_aliases)
        assert sim > 0.90

    def test_empty_inputs_return_zero(self):
        assert compute_toponym_similarity([], ["Beni Khiar"]) == 0.0
        assert compute_toponym_similarity(["Beni Khiar"], []) == 0.0
        assert compute_toponym_similarity(["   "], [""]) == 0.0


class TestProximitySimilarity:
    """Tests for ProximityMatch S_proximity (Equation A3)."""

    def test_cold_start_none_anchor_returns_zero(self):
        cand = Point2D(500000.0, 3700000.0)
        s_prox, dist = compute_proximity_similarity(cand, None, sigma=150.0)
        assert s_prox == 0.0
        assert dist == 0.0

    def test_exact_coincidence_distance_zero(self):
        p1 = Point2D(500000.0, 3700000.0)
        p2 = Point2D(500000.0, 3700000.0)
        s_prox, dist = compute_proximity_similarity(p1, p2, sigma=150.0)
        assert math.isclose(dist, 0.0, abs_tol=1e-6)
        assert math.isclose(s_prox, 1.0, abs_tol=1e-6)

    def test_gaussian_decay_at_one_sigma(self):
        # At d = sigma = 150m, S_proximity = exp(-0.5) ≈ 0.60653
        p1 = Point2D(500000.0, 3700000.0)
        p2 = Point2D(500150.0, 3700000.0)
        s_prox, dist = compute_proximity_similarity(p1, p2, sigma=150.0)
        assert math.isclose(dist, 150.0, abs_tol=1e-3)
        expected = math.exp(-0.5)
        assert math.isclose(s_prox, expected, rel_tol=1e-4)

    def test_gaussian_decay_at_two_sigma(self):
        # At d = 2*sigma = 300m, S_proximity = exp(-2.0) ≈ 0.13533
        p1 = Point2D(500000.0, 3700000.0)
        p2 = Point2D(500300.0, 3700000.0)
        s_prox, dist = compute_proximity_similarity(p1, p2, sigma=150.0)
        assert math.isclose(dist, 300.0, abs_tol=1e-3)
        expected = math.exp(-2.0)
        assert math.isclose(s_prox, expected, rel_tol=1e-4)

    def test_invalid_sigma_raises_value_error(self):
        p = Point2D(0.0, 0.0)
        with pytest.raises(ValueError, match="Bandwidth sigma must be > 0"):
            compute_proximity_similarity(p, p, sigma=0.0)
        with pytest.raises(ValueError, match="Bandwidth sigma must be > 0"):
            compute_proximity_similarity(p, p, sigma=-10.0)


class TestTopologySimilarity:
    """Tests for TopologyMatch S_topology (Binary infrastructure filter)."""

    def test_matching_route_returns_one(self):
        assert compute_topology_similarity("RR27", "RR27") == 1.0

    def test_case_and_whitespace_insensitivity(self):
        assert compute_topology_similarity(" rr27 ", "RR27") == 1.0

    def test_mismatched_route_returns_zero(self):
        assert compute_topology_similarity("RR43", "RR27") == 0.0
        assert compute_topology_similarity("MC28", "RR27") == 0.0

    def test_empty_route_returns_zero(self):
        assert compute_topology_similarity("", "RR27") == 0.0
        assert compute_topology_similarity("RR27", "") == 0.0


class TestWeightsAndCompositeScore:
    """Tests for weight resolution and Equation A1 composite score."""

    def test_cold_start_weights(self):
        params = DSDAParameters()
        w = resolve_weights(is_cold_start=True, params=params)
        assert w["w1"] == 0.875
        assert w["w2"] == 0.000
        assert w["w3"] == 0.125
        assert math.isclose(sum(w.values()), 1.0)

    def test_standard_weights(self):
        params = DSDAParameters()
        w = resolve_weights(is_cold_start=False, params=params)
        assert w["w1"] == 0.500
        assert w["w2"] == 0.375
        assert w["w3"] == 0.125
        assert math.isclose(sum(w.values()), 1.0)

    def test_composite_score_calculation(self):
        weights = {"w1": 0.5, "w2": 0.375, "w3": 0.125}
        cs = compute_composite_score(s_toponym=1.0, s_proximity=0.8, s_topology=1.0, weights=weights)
        expected = 0.5 * 1.0 + 0.375 * 0.8 + 0.125 * 1.0  # 0.5 + 0.3 + 0.125 = 0.925
        assert math.isclose(cs, expected, rel_tol=1e-5)

    def test_invalid_parameters_raise_error(self):
        with pytest.raises(ValueError, match="Standard weights must sum to 1.0"):
            DSDAParameters(w1=0.6, w2=0.6, w3=0.1)

        with pytest.raises(ValueError, match="Cold start weights must sum to 1.0"):
            DSDAParameters(cold_start_w1=0.5, cold_start_w2=0.0, cold_start_w3=0.1)

        with pytest.raises(ValueError, match="Validation threshold must be in"):
            DSDAParameters(validation_threshold=1.5)
