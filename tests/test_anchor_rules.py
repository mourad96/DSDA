"""Algorithm 1 (stateless): LRS-anchored mode, municipal sector reference,
intersection pass, deterministic tie-breaking, and absence of ground truth
at runtime."""

import dataclasses
import random
from datetime import datetime

from dsda.engine import DSDAEngine
from dsda.gis_store import GisDatabase
from dsda.models import (
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

    def test_candidates_limited_to_r_max_all_routes(self, corridor_gis_db):
        res = DSDAEngine().resolve_event(
            _event("E1", "PK34", "Hydraulic bridge (PK 34)", None), corridor_gis_db
        )
        names = {c.node.node_name for c in res.candidate_evaluations}
        # PK33 and PK35 nodes are 1.5 km away: outside R_max = 500 m.
        # The RR43 node is kept (all routes queried) with S_topology = 0.
        assert names == {"RR27_PK34_Bridge", "RR27_PK34_Culvert", "RR43_PK34_Cross"}
        assert all(c.distance_m <= 500.0 for c in res.candidate_evaluations)


class TestStatelessness:
    def _events(self):
        return [
            _event("A", "PK33", "Maamoura Sud", datetime(2025, 1, 1, 8)),
            _event("B", "PK34", "Unknown Landmark XYZ QWERTY", datetime(2025, 1, 1, 9)),
            _event("C", None, "El Mazraa Nord", datetime(2025, 1, 1, 10), municipality_centroid=NABEUL_CENTROID),
            _event("D", "PK34", "Hydraulic bridge (PK 34)", datetime(2025, 1, 3, 8)),
            _event("E", None, "Hydraulic bridge", datetime(2025, 2, 1, 8), municipality_centroid=NABEUL_CENTROID),
        ]

    @staticmethod
    def _signature(r):
        return (r.event_id, r.status, r.selected_node.node_name if r.selected_node else None,
                round(r.best_score, 12), r.mode)

    def test_result_independent_of_order_and_of_other_records(self, corridor_gis_db):
        engine = DSDAEngine()
        events = self._events()
        alone = {e.event_id: self._signature(engine.resolve_event(e, corridor_gis_db)) for e in events}
        for seed in range(5):
            shuffled = events[:]
            random.Random(seed).shuffle(shuffled)
            for r in engine.process_corridor(shuffled, corridor_gis_db):
                assert self._signature(r) == alone[r.event_id]

    def test_sector_reference_is_always_the_municipality(self, corridor_gis_db):
        engine = DSDAEngine()
        for r in engine.process_corridor(self._events(), corridor_gis_db):
            if r.mode == ResolutionMode.SECTOR_FALLBACK:
                assert r.sector_reference.anchor_type == AnchorType.MUNICIPALITY_CENTROID
                assert r.sector_reference.coords == NABEUL_CENTROID

    def test_engine_has_no_state_variable(self):
        import dsda.engine as eng
        src = open(eng.__file__, encoding="utf-8").read()
        assert "k_prev" not in src and "PRIOR_EVENT" not in src


class TestFallbackMode:
    def test_omitted_pk_uses_fallback_weights(self, corridor_gis_db):
        ev = _event("E1", None, "Hydraulic bridge", datetime(2025, 1, 1, 10),
                    municipality_centroid=NABEUL_CENTROID)
        res = DSDAEngine().resolve_event(ev, corridor_gis_db)
        assert res.mode == ResolutionMode.SECTOR_FALLBACK
        assert res.anchor_used is None
        assert res.weights_used == {"w1": 0.875, "w2": 0.000, "w3": 0.125}
        assert all(c.s_proximity == 0.0 for c in res.candidate_evaluations)

    def test_ambiguous_pk_resolved_by_municipal_sector(self):
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


class TestDeterministicTieBreaking:
    """Highest Cs, then smallest distance d to the anchor, then Node_ID."""

    POST = Point2D(0.0, 0.0)

    def _db(self, nodes):
        return GisDatabase(nodes, pk_posts=[PKPost("RR27", "PK1", self.POST)])

    def test_equal_cs_smaller_distance_wins(self):
        # Same gazetteer and route, equidistant on each side would tie on Cs:
        # place them at 100 m and 100 m but on different axes -> same d; use
        # the toponymy-only configuration to create a Cs tie at different d.
        from dsda.models import DSDAParameters
        nodes = [
            GisNode("B_far", "PK1", ["Oued"], "RR27", Point2D(300.0, 0.0)),
            GisNode("A_near", "PK1", ["Oued"], "RR27", Point2D(120.0, 0.0)),
        ]
        engine = DSDAEngine(DSDAParameters(w1=1.0, w2=0.0, w3=0.0))
        res = engine.resolve_event(CrashEvent("E", "RR27", "PK1", ["Oued"]), self._db(nodes))
        assert res.candidate_evaluations[0].cs_score == res.candidate_evaluations[1].cs_score
        assert res.selected_node.node_name == "A_near"

    def test_equal_cs_and_distance_lexicographic_id(self):
        nodes = [
            GisNode("node_b", "PK1", ["Oued"], "RR27", Point2D(0.0, 100.0)),
            GisNode("node_a", "PK1", ["Oued"], "RR27", Point2D(100.0, 0.0)),
        ]
        for order in (nodes, nodes[::-1]):
            res = DSDAEngine().resolve_event(CrashEvent("E", "RR27", "PK1", ["Oued"]), self._db(order))
            assert res.candidate_evaluations[0].cs_score == res.candidate_evaluations[1].cs_score
            assert res.selected_node.node_name == "node_a"

    def test_fallback_tie_uses_node_id(self):
        nodes = [
            GisNode("node_z", "PK9", ["Oued"], "RR27", Point2D(10.0, 0.0)),
            GisNode("node_m", "PK9", ["Oued"], "RR27", Point2D(900.0, 0.0)),
        ]
        db = GisDatabase(nodes)
        res = DSDAEngine().resolve_event(CrashEvent("E", "RR27", None, ["Oued"]), db)
        assert res.mode == ResolutionMode.SECTOR_FALLBACK
        assert res.selected_node.node_name == "node_m"  # d = 0 for all: Node_ID decides


class TestNoGroundTruthAtRuntime:
    def test_event_has_no_ground_truth_field(self):
        fields = {f.name for f in dataclasses.fields(CrashEvent)}
        assert "ground_truth_coords" not in fields

    def test_engine_does_not_import_evaluation(self):
        import dsda.engine as eng
        src = open(eng.__file__, encoding="utf-8").read()
        assert "ground_truth" not in src.replace("Ground-truth coordinates are never used here", "")
        assert "dsda.evaluation" not in src.split('"""', 2)[2]
