"""Tests for DSDAEngine core execution and GIS database operations."""

import pytest
from dsda.engine import DSDAEngine
from dsda.gis_store import GisDatabase
from dsda.models import (
    Anchor,
    AnchorType,
    CrashEvent,
    DSDAParameters,
    GeocodingStatus,
    GisNode,
    Point2D,
)


class TestGisDatabase:
    """Tests for spatial repository indexing and lookups."""

    def test_pk_normalization_lookup(self, poc_gis_database):
        # Should match despite whitespace or casing
        nodes_std = poc_gis_database.query_by_pk("PK34")
        nodes_spaced = poc_gis_database.query_by_pk(" pk 34 ")
        assert len(nodes_std) == 4
        assert len(nodes_spaced) == 4

    def test_nearest_node_lookup(self, poc_gis_database):
        target_point = Point2D(500070.0, 3700000.0)
        nearest = poc_gis_database.find_nearest_node(target_point, route="RR27")
        assert nearest is not None
        assert nearest.node_name == "Node P3 (Target)"

    def test_from_records_and_len(self, poc_base_sig_dicts):
        db = GisDatabase.from_records(poc_base_sig_dicts)
        assert len(db) == 4
        all_nodes = list(db)
        assert len(all_nodes) == 4


class TestEngineEvaluation:
    """Tests for DSDAEngine single event evaluation and reporting."""

    def test_no_candidates_returns_rejected_status(self):
        engine = DSDAEngine()
        event = CrashEvent(
            event_id="E_NONE",
            route="RR27",
            pk_marker="PK999",
            narrative_landmarks=["Nonexistent"],
        )
        result = engine.evaluate_event(event=event, anchor=None, candidates=[])
        assert result.status == GeocodingStatus.NO_CANDIDATES
        assert result.selected_node is None
        assert result.best_score == 0.0
        assert "No candidates found" in result.decision_message

    def test_summary_table_formatting(self, poc_gis_database):
        engine = DSDAEngine()
        event = CrashEvent(
            event_id="E_TABLE",
            route="RR27",
            pk_marker="PK34",
            narrative_landmarks=["B. Khiar"],
        )
        candidates = poc_gis_database.query_by_pk("PK34")
        result = engine.evaluate_event(event=event, anchor=None, candidates=candidates)
        table = result.summary_table()
        assert "E_TABLE" in table
        assert "Node P3 (Target)" in table
        assert "AUTO-VALIDATED" in table

    def test_sigma_sensitivity_stability(self, poc_gis_database):
        """Verify paper finding: sensitivity testing sigma in [100, 250]m confirms classification stability."""
        anchor = Anchor(coords=Point2D(500000.0, 3700000.0), anchor_type=AnchorType.PRIOR_EVENT)
        candidates = poc_gis_database.query_by_pk("PK34")
        event = CrashEvent(
            event_id="E_SENSITIVITY",
            route="RR27",
            pk_marker="PK34",
            narrative_landmarks=["B. Khiar"],
        )

        for sigma in [100.0, 150.0, 200.0, 250.0]:
            engine = DSDAEngine(DSDAParameters(sigma=sigma))
            result = engine.evaluate_event(event, anchor, candidates)
            assert result.status == GeocodingStatus.AUTO_VALIDATED
            assert result.selected_node.node_name == "Node P3 (Target)"
            assert result.best_score >= 0.85
