"""Tests for DSDAEngine core execution and GIS database operations."""

from dsda.engine import DSDAEngine
from dsda.gis_store import GisDatabase
from dsda.models import (
    Anchor,
    AnchorType,
    CrashEvent,
    DSDAParameters,
    GeocodingStatus,
    Point2D,
)


class TestGisDatabase:
    def test_pk_normalization_lookup(self, poc_gis_database):
        assert len(poc_gis_database.query_by_pk("PK34")) == 4
        assert len(poc_gis_database.query_by_pk(" pk 34 ")) == 4

    def test_pk_post_resolution(self, poc_gis_database, pk34_post):
        post = poc_gis_database.resolve_pk_post("rr27", "pk 34")
        assert post is not None and post.coords == pk34_post
        assert poc_gis_database.resolve_pk_post("RR27", None) is None
        assert poc_gis_database.resolve_pk_post("RR27", "PK99") is None

    def test_query_within_radius(self, poc_gis_database, pk34_post):
        assert len(poc_gis_database.query_within_radius(pk34_post, 500.0)) == 4
        assert len(poc_gis_database.query_within_radius(pk34_post, 140.0)) == 2

    def test_nearest_node_lookup(self, poc_gis_database):
        nearest = poc_gis_database.find_nearest_node(Point2D(500070.0, 3700000.0), route="RR27")
        assert nearest is not None and nearest.node_name == "Node P3 (Bridge)"

    def test_from_records_and_len(self, poc_base_sig_dicts):
        db = GisDatabase.from_records(poc_base_sig_dicts)
        assert len(db) == 4 and len(list(db)) == 4


class TestEngineEvaluation:
    def test_no_candidates_returns_rejected_status(self):
        event = CrashEvent(event_id="E_NONE", route="RR27", pk_marker="PK999", narrative_landmarks=["Nonexistent"])
        result = DSDAEngine().evaluate_event(event, candidates=[])
        assert result.status == GeocodingStatus.NO_CANDIDATES
        assert result.selected_node is None
        assert result.best_score == 0.0
        assert "No candidates found" in result.decision_message

    def test_summary_table_formatting(self, poc_gis_database):
        event = CrashEvent(event_id="E_TABLE", route="RR27", pk_marker="PK34",
                           narrative_landmarks=["Hydraulic bridge (PK 34)"])
        result = DSDAEngine().resolve_event(event, poc_gis_database)
        table = result.summary_table()
        assert "E_TABLE" in table and "Node P3 (Bridge)" in table
        assert "AUTO-VALIDATED" in table and "LRS_ANCHORED" in table

    def test_sigma_sensitivity_stability(self, poc_gis_database, pk34_post):
        """Classification stable for sigma in [100, 250] m (Appendix A.1)."""
        anchor = Anchor(coords=pk34_post, anchor_type=AnchorType.PK_POST, route="RR27")
        candidates = poc_gis_database.query_within_radius(pk34_post, 500.0)
        event = CrashEvent(event_id="E_SIGMA", route="RR27", pk_marker="PK34",
                           narrative_landmarks=["Hydraulic bridge (PK 34)"])
        for sigma in [100.0, 150.0, 200.0, 250.0]:
            result = DSDAEngine(DSDAParameters(sigma=sigma)).evaluate_event(event, candidates, pk_anchor=anchor)
            assert result.status == GeocodingStatus.AUTO_VALIDATED
            assert result.selected_node.node_name == "Node P3 (Bridge)"
