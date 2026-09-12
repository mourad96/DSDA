"""Unit tests for the three anchor initialization and propagation rules (Appendix A.1)."""

from datetime import datetime, timedelta
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


class TestRule1ColdStart:
    """Rule 1: Cold Start initialization on dataset start or route transition."""

    def test_first_event_in_dataset_is_cold_start(self, corridor_gis_db):
        engine = DSDAEngine()
        event = CrashEvent(
            event_id="E01",
            route="RR27",
            pk_marker="PK34",
            narrative_landmarks=["B. Khiar"],
            timestamp=datetime(2025, 1, 1, 10, 0),
        )
        results = engine.process_corridor([event], corridor_gis_db)
        assert len(results) == 1
        res = results[0]

        # Weights must be cold start
        assert res.weights_used["w1"] == 0.875
        assert res.weights_used["w2"] == 0.000
        assert res.weights_used["w3"] == 0.125
        assert res.anchor_used is None
        # Candidate evaluations must have 0.0 proximity
        for c in res.candidate_evaluations:
            assert c.s_proximity == 0.0
            assert c.distance_m == 0.0

    def test_switching_route_triggers_cold_start(self, corridor_gis_db):
        engine = DSDAEngine()
        event_rr27 = CrashEvent(
            event_id="E01_RR27",
            route="RR27",
            pk_marker="PK34",
            narrative_landmarks=["B. Khiar"],
            timestamp=datetime(2025, 1, 1, 10, 0),
        )
        # Event on MC28 5 days later
        event_mc28 = CrashEvent(
            event_id="E02_MC28",
            route="MC28",
            pk_marker="PK10",
            narrative_landmarks=["Grombalia Centre"],
            timestamp=datetime(2025, 1, 6, 10, 0),
        )

        results = engine.process_corridor([event_rr27, event_mc28], corridor_gis_db)
        assert len(results) == 2

        # First event is cold start
        assert results[0].anchor_used is None
        assert results[0].weights_used["w1"] == 0.875

        # Second event switched route -> MUST trigger Rule 1 Cold Start!
        assert results[1].anchor_used is None
        assert results[1].weights_used["w1"] == 0.875
        assert results[1].weights_used["w2"] == 0.000


class TestRule2SimultaneousEvents:
    """Rule 2: Events within tight temporal window (<=24h) default to regional centroid."""

    def test_event_within_24h_uses_municipality_centroid(self, corridor_gis_db):
        engine = DSDAEngine()
        # Regional centroid of municipality within corridor vicinity (~30m from PK34)
        nabeul_centroid = Point2D(500050.0, 3700020.0)

        # Event 1 at T=0
        event1 = CrashEvent(
            event_id="E01",
            route="RR27",
            pk_marker="PK33",
            narrative_landmarks=["Station Nabeul"],
            timestamp=datetime(2025, 1, 1, 8, 0),
        )

        # Event 2 at T=3h (<= 24h) on same route
        event2 = CrashEvent(
            event_id="E02",
            route="RR27",
            pk_marker="PK34",
            narrative_landmarks=["B. Khiar"],
            timestamp=datetime(2025, 1, 1, 11, 0),
            municipality_centroid=nabeul_centroid,
        )

        # Event 3 at T=40h (> 24h after Event 2)
        event3 = CrashEvent(
            event_id="E03",
            route="RR27",
            pk_marker="PK35",
            narrative_landmarks=["Korba Sud"],
            timestamp=datetime(2025, 1, 3, 3, 0),
            municipality_centroid=nabeul_centroid,
        )

        results = engine.process_corridor([event1, event2, event3], corridor_gis_db)

        # Event 1: Cold start
        assert results[0].anchor_used is None

        # Event 2: Within 3h of Event 1 -> Uses Municipality Centroid anchor!
        assert results[1].anchor_used is not None
        assert results[1].anchor_used.anchor_type == AnchorType.MUNICIPALITY_CENTROID
        assert results[1].anchor_used.coords == nabeul_centroid

        # Event 3: > 24h after Event 2 -> Reverts to PRIOR_EVENT anchor (Event 2's location)
        assert results[2].anchor_used is not None
        assert results[2].anchor_used.anchor_type == AnchorType.PRIOR_EVENT
        assert results[2].anchor_used.source_id == "E02"
        assert results[2].anchor_used.coords == results[1].selected_node.coords


class TestRule3AnchorIndependence:
    """Rule 3: Rejection of low-confidence or high E_geo events as anchors."""

    def test_low_score_event_rejected_as_anchor_and_reverts(self, corridor_gis_db):
        engine = DSDAEngine()

        # Event 1: Valid event, gets auto-validated
        event1 = CrashEvent(
            event_id="E01_VALID",
            route="RR27",
            pk_marker="PK33",
            narrative_landmarks=["Station Nabeul"],
            timestamp=datetime(2025, 1, 1, 8, 0),
        )

        # Event 2: Ambiguous / completely unrecognized landmark -> will have low Cs (< 0.85)
        event2 = CrashEvent(
            event_id="E02_AMBIGUOUS",
            route="RR27",
            pk_marker="PK34",
            narrative_landmarks=["Unknown Landmark XYZ QWERTY"],
            timestamp=datetime(2025, 1, 3, 8, 0),  # >24h
        )

        # Event 3: Valid event 48h later
        event3 = CrashEvent(
            event_id="E03_VALID",
            route="RR27",
            pk_marker="PK35",
            narrative_landmarks=["Korba Sud"],
            timestamp=datetime(2025, 1, 5, 8, 0),  # >24h
        )

        results = engine.process_corridor([event1, event2, event3], corridor_gis_db)

        # Event 1 is auto-validated
        assert results[0].status == GeocodingStatus.AUTO_VALIDATED
        assert results[0].is_safe_anchor is True
        e1_coords = results[0].selected_node.coords

        # Event 2 is rejected for manual review (Cs < 0.85)
        assert results[1].status == GeocodingStatus.MANUAL_REVIEW_REQUIRED
        assert results[1].best_score < 0.85
        assert results[1].is_safe_anchor is False

        # Event 3 MUST NOT use Event 2 as an anchor!
        # It MUST revert to the last safely geocoded event (Event 1)
        assert results[2].anchor_used is not None
        assert results[2].anchor_used.source_id == "E01_VALID"
        assert results[2].anchor_used.coords == e1_coords

    def test_e_geo_tolerance_exceeded_rejects_as_anchor(self, corridor_gis_db):
        engine = DSDAEngine(DSDAParameters(e_geo_tolerance=50.0))

        # Event 1: High score, but ground truth is 120m away (E_geo > 50m)
        false_ground_truth = Point2D(500000.0 + 120.0, 3698500.0)
        event1 = CrashEvent(
            event_id="E01_ERRONEOUS",
            route="RR27",
            pk_marker="PK33",
            narrative_landmarks=["Station Nabeul"],
            timestamp=datetime(2025, 1, 1, 8, 0),
            ground_truth_coords=false_ground_truth,
        )

        # Event 2: Valid event 30 hours later
        event2 = CrashEvent(
            event_id="E02_NEXT",
            route="RR27",
            pk_marker="PK34",
            narrative_landmarks=["B. Khiar"],
            timestamp=datetime(2025, 1, 2, 14, 0),
        )

        results = engine.process_corridor([event1, event2], corridor_gis_db)

        # Event 1 failed E_geo tolerance check
        assert results[0].status == GeocodingStatus.MANUAL_REVIEW_REQUIRED
        assert results[0].e_geo > 50.0
        assert results[0].is_safe_anchor is False

        # Event 2 cannot use Event 1, so it remains in Cold Start!
        assert results[1].anchor_used is None
        assert results[1].weights_used["w1"] == 0.875
