"""Regression parity tests against the original DSDA proof-of-concept scenarios."""

import math
import pytest
from dsda.engine import dsda_algorithm_with_logs


class TestPocParity:
    """Exact numerical verification against user's prototype script."""

    def test_scenario_1_with_active_anchor(self, poc_base_sig_dicts):
        pk_extrait = "PK34"
        t_rep_extrait = "B. Khiar"
        route_extraite = "RR27"
        ancre_precedente = {"x": 500000, "y": 3700000}

        res = dsda_algorithm_with_logs(
            pk_marker=pk_extrait,
            t_rep=t_rep_extrait,
            target_route=route_extraite,
            k_prev=ancre_precedente,
            gis_database=poc_base_sig_dicts,
        )

        assert "AUTO-VALIDATED: Node P3 (Target)" in res["Decision"]
        assert res["Weights_Used"] == {"w1": 0.500, "w2": 0.375, "w3": 0.125}

        # Check logs ranking and top candidate values
        assert len(res["Logs"]) == 4
        top_log = res["Logs"][0]
        assert top_log["Node"] == "Node P3 (Target)"
        assert math.isclose(top_log["Distance_m"], 68.85, abs_tol=0.01)
        assert math.isclose(top_log["S_Toponym"], 0.975, abs_tol=0.001)
        assert math.isclose(top_log["S_Proximity"], 0.900, abs_tol=0.001)
        assert top_log["S_Topology"] == 1.0
        assert math.isclose(top_log["Cs_Score"], 0.950, abs_tol=0.001)

        # Check alternative candidates are properly ranked lower
        # Candidate P1 (Bypass): S_Toponym is lower ("B. K" vs "B. Khiar")
        p1_log = next(log for log in res["Logs"] if log["Node"] == "Node P1 (Bypass)")
        assert p1_log["Cs_Score"] < top_log["Cs_Score"]

        # Candidate P2 (Parallel): Route is RR43 != RR27 -> S_Topology = 0
        p2_log = next(log for log in res["Logs"] if log["Node"] == "Node P2 (Parallel)")
        assert p2_log["S_Topology"] == 0.0

    def test_scenario_2_cold_start(self, poc_base_sig_dicts):
        pk_extrait = "PK34"
        t_rep_extrait = "B. Khiar"
        route_extraite = "RR27"

        res = dsda_algorithm_with_logs(
            pk_marker=pk_extrait,
            t_rep=t_rep_extrait,
            target_route=route_extraite,
            k_prev=None,
            gis_database=poc_base_sig_dicts,
        )

        assert "AUTO-VALIDATED: Node P3 (Target)" in res["Decision"]
        assert res["Weights_Used"] == {"w1": 0.875, "w2": 0.000, "w3": 0.125}

        top_log = res["Logs"][0]
        assert top_log["Node"] == "Node P3 (Target)"
        assert top_log["Distance_m"] == 0.0
        assert top_log["S_Proximity"] == 0.0
        assert math.isclose(top_log["S_Toponym"], 0.975, abs_tol=0.001)
        # Cold start Cs = 0.875 * 0.975 + 0.125 * 1.0 = 0.978
        assert math.isclose(top_log["Cs_Score"], 0.978, abs_tol=0.001)

    def test_scenario_rejected_manual_review(self, poc_base_sig_dicts):
        # Query with unrecognized toponym and mismatched route
        res = dsda_algorithm_with_logs(
            pk_marker="PK34",
            t_rep="Completely Unrelated Landmark",
            target_route="A1_AUTOROUTE",
            k_prev=None,
            gis_database=poc_base_sig_dicts,
        )
        assert "REJECTED: Manual Review Required" in res["Decision"]
        for log in res["Logs"]:
            assert log["Cs_Score"] < 0.85
