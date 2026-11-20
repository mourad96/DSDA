"""Single-event example of Figure 3 (PK 34 on RR27, anchor = nominal PK post)."""

import math
from dsda.engine import dsda_algorithm_with_logs

K_PK = {"x": 500000, "y": 3700000}
T_REP = "Hydraulic bridge (Maamoura)"


def _log(res, name):
    return next(log for log in res["Logs"] if log["Node"] == name)


class TestFigure3Example:
    """Values printed in Figure 3, panel (c)."""

    def test_lrs_anchored_mode(self, poc_base_sig_dicts):
        res = dsda_algorithm_with_logs(
            pk_marker="PK34",
            t_rep=T_REP,
            target_route="RR27",
            k_pk=K_PK,
            gis_database=poc_base_sig_dicts,
        )
        assert res["Mode"] == "LRS_ANCHORED"
        assert res["Weights_Used"] == {"w1": 0.500, "w2": 0.375, "w3": 0.125}
        assert "AUTO-VALIDATED: Node P3 (Bridge)" in res["Decision"]
        assert [log["Node"] for log in res["Logs"]] == [
            "Node P3 (Bridge)", "Node P1 (Culvert)", "Node P2 (RR43)", "Node P4 (MC28)"
        ]

        p3 = _log(res, "Node P3 (Bridge)")
        assert math.isclose(p3["Distance_m"], 68.85, abs_tol=0.01)
        assert math.isclose(p3["S_Toponym"], 0.928, abs_tol=0.001)
        assert math.isclose(p3["S_Proximity"], 0.900, abs_tol=0.001)
        assert p3["S_Topology"] == 1.0
        assert math.isclose(p3["Cs_Score"], 0.927, abs_tol=0.001)

        p1 = _log(res, "Node P1 (Culvert)")
        assert math.isclose(p1["S_Toponym"], 0.842, abs_tol=0.001)
        assert math.isclose(p1["S_Proximity"], 0.700, abs_tol=0.001)
        assert p1["S_Topology"] == 1.0
        assert math.isclose(p1["Cs_Score"], 0.808, abs_tol=0.001)
        assert p1["Cs_Score"] < 0.85  # near miss, would go to manual review

        p2 = _log(res, "Node P2 (RR43)")
        assert math.isclose(p2["S_Toponym"], 0.511, abs_tol=0.001)
        assert math.isclose(p2["S_Proximity"], 0.600, abs_tol=0.001)
        assert p2["S_Topology"] == 0.0
        assert math.isclose(p2["Cs_Score"], 0.480, abs_tol=0.001)

        p4 = _log(res, "Node P4 (MC28)")
        assert math.isclose(p4["S_Toponym"], 0.447, abs_tol=0.001)
        assert math.isclose(p4["S_Proximity"], 0.300, abs_tol=0.001)
        assert p4["S_Topology"] == 0.0
        assert math.isclose(p4["Cs_Score"], 0.336, abs_tol=0.001)

    def test_fallback_without_pk_post(self, poc_base_sig_dicts):
        res = dsda_algorithm_with_logs(
            pk_marker="PK34",
            t_rep=T_REP,
            target_route="RR27",
            k_pk=None,
            gis_database=poc_base_sig_dicts,
        )
        assert res["Mode"] == "SECTOR_FALLBACK"
        assert res["Weights_Used"] == {"w1": 0.875, "w2": 0.000, "w3": 0.125}
        top = res["Logs"][0]
        assert top["Node"] == "Node P3 (Bridge)"
        assert top["S_Proximity"] == 0.0
        # 0.875 * 0.928 + 0.125 * 1.0
        assert math.isclose(top["Cs_Score"], 0.937, abs_tol=0.001)

    def test_unrelated_landmark_is_rejected(self, poc_base_sig_dicts):
        res = dsda_algorithm_with_logs(
            pk_marker="PK34",
            t_rep="Completely Unrelated Landmark",
            target_route="A1_AUTOROUTE",
            k_pk=None,
            gis_database=poc_base_sig_dicts,
        )
        assert "REJECTED: Manual Review Required" in res["Decision"]
        assert all(log["Cs_Score"] < 0.85 for log in res["Logs"])
