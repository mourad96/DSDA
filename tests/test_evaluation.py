"""Post-hoc accuracy: ground truth is used only after the engine has decided."""

import math

from dsda.engine import DSDAEngine
from dsda.evaluation import compute_geocoding_accuracy, percentile_linear
from dsda.models import CrashEvent, GeocodingStatus, Point2D


def test_percentile_linear_matches_numpy_definition():
    xs = [10.0, 20.0, 30.0, 40.0]
    assert percentile_linear(xs, 50) == 25.0
    assert math.isclose(percentile_linear(xs, 90), 37.0)
    assert math.isclose(percentile_linear(xs, 95), 38.5)


def test_conditional_and_inclusive_populations(corridor_gis_db):
    engine = DSDAEngine()
    events = [
        CrashEvent("OK", "RR27", "PK34", ["Hydraulic bridge (PK 34)"]),
        CrashEvent("LOW", "RR27", "PK34", ["Unknown Landmark XYZ QWERTY"]),
    ]
    results = [engine.resolve_event(e, corridor_gis_db) for e in events]
    statuses = [r.status for r in results]
    assert statuses == [GeocodingStatus.AUTO_VALIDATED, GeocodingStatus.MANUAL_REVIEW_REQUIRED]

    gt = {"OK": Point2D(500068.85 + 30.0, 3700000.0), "LOW": Point2D(500068.85 + 120.0, 3700000.0)}
    rep = compute_geocoding_accuracy(results, gt)
    assert rep.n_records == 2 and rep.n_accepted == 1
    assert rep.conditional.n == 1 and math.isclose(rep.conditional.mean, 30.0)
    assert rep.inclusive.n == 2

    # Decisions are unchanged by the evaluation (no feedback into the engine)
    assert [r.status for r in results] == statuses


def test_ground_truth_does_not_change_decisions(corridor_gis_db):
    """A far-away ground truth must not reject an accepted record (old E_geo gate removed)."""
    engine = DSDAEngine()
    res = engine.resolve_event(CrashEvent("E", "RR27", "PK34", ["Hydraulic bridge (PK 34)"]), corridor_gis_db)
    assert res.status == GeocodingStatus.AUTO_VALIDATED
    rep = compute_geocoding_accuracy([res], {"E": Point2D(500068.85 + 120.0, 3700000.0)})
    assert rep.conditional.mean > 50.0
    assert res.status == GeocodingStatus.AUTO_VALIDATED
