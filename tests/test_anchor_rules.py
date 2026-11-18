"""Algorithm 1: LRS-anchored mode, sector reference rules, intersection pass,
anchor independence, and absence of ground truth at runtime."""

import dataclasses
from datetime import datetime

from dsda.engine import DSDAEngine
from dsda.gis_store import GisDatabase
from dsda.models import (
    Anchor,
    AnchorType,
    CrashEvent,
    GeocodingStatus,
    GisNode,
    PKPost,
    Point2D,
    ResolutionMode,
)

NABEUL_CENTROID = Point2D(500050.0, 3700020.0)


def _event(eid, pk, landmark, ts, **kw):
    return CrashEvent(event_id=eid, route=kw.pop("route", "RR27"), pk_marker=pk,
                      narrative_landmarks=[landmark], timestamp=ts, **kw)


class TestPrimaryLrsAnchoredMode:
    def test_anchor_is_nominal_pk_post(self, corridor_gis_db, pk34_post):
        res = DSDAEngine().resolve_event(
            _event("E1", "PK34", "Hydraulic bridge (PK 34)", datetime(2025, 1, 1, 10)), corridor_gis_db
        )
        assert res.mode == ResolutionMode.LRS_ANCHORED
        assert res.anchor_used.anchor_type == AnchorType.PK_POST
        assert res.anchor_used.coords == pk34_post
        assert res.weights_used == {"w1": 0.500, "w2": 0.375, "w3": 0.125}
        assert res.status == GeocodingStatus.AUTO_VALIDATED
        assert res.selected_node.node_name == "RR27_PK34_Bridge"

    def test_candidates_limited_to_r_max(self, corridor_gis_db):
        res = DSDAEngine().resolve_event(
            _event("E1", "PK34", "Hydraulic bridge (PK 34)", None), corridor_gis_db
        )
        names = {c.node.node_name for c in res.candidate_evaluations}
        # PK33 and PK35 nodes are 1.5 km away: outside R_max = 500 m
        assert names == {"RR27_PK34_Bridge", "RR27_PK34_Culvert", "RR43_PK34_Cross"}
        assert all(c.distance_m <= 500.0 for c in res.candidate_evaluations)

    def test_order_independence(self, corridor_gis_db):
        engine = DSDAEngine()
        target = _event("T", "PK34", "Hydraulic bridge (PK 34)", datetime(2025, 3, 1, 10))
        others = [
            _event("A", "PK33", "Maamoura Sud", datetime(2025, 1, 1, 8)),
            _event("B", "PK35", "El Mazraa Nord", datetime(2025, 2, 1, 8)),
        ]
        alone = engine.process_corridor([target], corridor_gis_db)[0]
        in_sequence = engine.process_corridor(others + [target], corridor_gis_db)[-1]
        assert alone.selected_node == in_sequence.selected_node
        assert alone.best_score == in_sequence.best_score
        assert alone.anchor_used.coords == in_sequence.anchor_used.coords


class TestFallbackAndSectorReference:
    def test_omitted_pk_uses_fallback_weights(self, corridor_gis_db):
        ev = _event("E1", None, "Hydraulic bridge", datetime(2025, 1, 1, 10),
                    municipality_centroid=NABEUL_CENTROID)
        res = DSDAEngine().resolve_event(ev, corridor_gis_db)
        assert res.mode == ResolutionMode.SECTOR_FALLBACK
        assert res.anchor_used is None
        assert res.weights_used == {"w1": 0.875, "w2": 0.000, "w3": 0.125}
        assert all(c.s_proximity == 0.0 for c in res.candidate_evaluations)
        assert res.sector_reference.anchor_type == AnchorType.MUNICIPALITY_CENTROID

    def test_sector_reference_rules(self, corridor_gis_db):
        engine = DSDAEngine()
        prev = Anchor(coords=Point2D(500200.0, 3701500.0), anchor_type=AnchorType.PRIOR_EVENT,
                      source_id="P", timestamp=datetime(2025, 1, 1, 8), route="RR27")
        within_24h = _event("E", None, "x", datetime(2025, 1, 1, 20), municipality_centroid=NABEUL_CENTROID)
        after_24h = _event("E", None, "x", datetime(2025, 1, 3, 8), municipality_centroid=NABEUL_CENTROID)
        other_route = _event("E", None, "x", datetime(2025, 1, 3, 8), route="MC28",
                             municipality_centroid=NABEUL_CENTROID)

        assert engine.sector_reference(within_24h, None).anchor_type == AnchorType.MUNICIPALITY_CENTROID
        assert engine.sector_reference(within_24h, prev).anchor_type == AnchorType.MUNICIPALITY_CENTROID
        assert engine.sector_reference(after_24h, prev) is prev
        assert engine.sector_reference(other_route, prev).anchor_type == AnchorType.MUNICIPALITY_CENTROID

    def test_ambiguous_pk_resolved_by_sector(self):
        # Same label "PK10" on two chainages of the same route (local vs national)
        posts = [
            PKPost(route="RN15", pk_marker="PK10", coords=Point2D(0.0, 0.0), sector="national"),
            PKPost(route="RN15", pk_marker="PK10", coords=Point2D(50000.0, 0.0), sector="local"),
        ]
        nodes = [
            GisNode("near_national", "PK10", ["Oued"], "RN15", Point2D(40.0, 0.0)),
            GisNode("near_local", "PK10", ["Oued"], "RN15", Point2D(50040.0, 0.0)),
        ]
        db = GisDatabase(nodes, pk_posts=posts)
        engine = DSDAEngine()

        no_sector = engine.resolve_event(CrashEvent("E", "RN15", "PK10", ["Oued"]), db)
        assert no_sector.mode == ResolutionMode.SECTOR_FALLBACK  # ambiguous label

        with_sector = engine.resolve_event(
            CrashEvent("E", "RN15", "PK10", ["Oued"], municipality_centroid=Point2D(49000.0, 0.0)), db
        )
        assert with_sector.mode == ResolutionMode.LRS_ANCHORED
        assert with_sector.anchor_used.coords == Point2D(50000.0, 0.0)
        assert with_sector.selected_node.node_name == "near_local"


class TestIntersectionPass:
    def test_weights_anchored(self, corridor_gis_db):
        ev = _event("E1", "PK34", "RR43 junction", None, intersection_descriptors=True)
        res = DSDAEngine().resolve_event(ev, corridor_gis_db)
        assert res.weights_used == {"w1": 0.625, "w2": 0.375, "w3": 0.0}
        assert res.selected_node.node_name == "RR43_PK34_Cross"  # junction no longer pruned

    def test_weights_fallback(self, corridor_gis_db):
        ev = _event("E1", None, "Hydraulic bridge", None, intersection_descriptors=True)
        res = DSDAEngine().resolve_event(ev, corridor_gis_db)
        assert res.weights_used == {"w1": 1.0, "w2": 0.0, "w3": 0.0}


class TestAnchorIndependence:
    def test_rejected_event_does_not_update_k_prev(self, corridor_gis_db):
        events = [
            _event("E1", "PK33", "Maamoura Sud", datetime(2025, 1, 1, 8)),
            _event("E2", "PK34", "Unknown Landmark XYZ QWERTY", datetime(2025, 1, 3, 8)),
            _event("E3", None, "El Mazraa Nord", datetime(2025, 1, 5, 8)),
        ]
        res = DSDAEngine().process_corridor(events, corridor_gis_db)
        assert res[0].status == GeocodingStatus.AUTO_VALIDATED
        assert res[1].status == GeocodingStatus.MANUAL_REVIEW_REQUIRED
        assert res[1].is_safe_anchor is False
        # E3 (> 24 h, PK omitted): sector reference is the last ACCEPTED event, E1
        assert res[2].sector_reference.anchor_type == AnchorType.PRIOR_EVENT
        assert res[2].sector_reference.source_id == "E1"


class TestNoGroundTruthAtRuntime:
    def test_event_has_no_ground_truth_field(self):
        fields = {f.name for f in dataclasses.fields(CrashEvent)}
        assert "ground_truth_coords" not in fields

    def test_engine_does_not_import_evaluation(self):
        import dsda.engine as eng
        src = open(eng.__file__, encoding="utf-8").read()
        assert "ground_truth" not in src.replace("Ground-truth coordinates are never used here", "")
        assert "dsda.evaluation" not in src.split('"""', 2)[2]
