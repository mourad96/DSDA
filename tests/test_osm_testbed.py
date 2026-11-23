"""Tests of scripts/osm_testbed.py on an invented OSM fixture (no real data)."""

from __future__ import annotations

import random
import sys
from pathlib import Path

import pytest

pytest.importorskip("pyproj")
pytest.importorskip("shapely")
pytest.importorskip("scipy")
pytest.importorskip("openpyxl")

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
sys.path.insert(0, str(ROOT / "tests" / "fixtures"))

import osm_testbed as tb  # noqa: E402
import synthetic_osm  # noqa: E402


@pytest.fixture(scope="module")
def inputs(tmp_path_factory):
    d = tmp_path_factory.mktemp("osm")
    return synthetic_osm.build(d / "osm.json"), synthetic_osm.build_registry(d / "registry.xlsx")


@pytest.fixture(scope="module")
def corridor(inputs):
    osm, reg = inputs
    data = tb.load_osm(osm)
    c = tb.build_corridor(data)
    tb.calibrate(c, data)
    tb.build_gis(c, data)
    registry = tb.load_registry(reg)
    c.posts = tb.pk_posts(c, registry)
    return c, registry


def test_calibration_uses_all_five_anchors(corridor):
    c, _ = corridor
    assert [a["pk"] for a in c.anchors] == [27.0, 31.24, 33.08, 33.56, 36.3]
    pk, s = c.pk_s
    for p, x in zip(pk, s):
        assert c.pk_of_s(x) == pytest.approx(p)
        assert c.s_of_pk(p) == pytest.approx(x)


def test_true_positions_stay_in_recorded_pk_interval(corridor):
    c, registry = corridor
    recs = tb.simulate_truth(c, registry, random.Random(tb.BASE_SEED))
    for r in recs:
        assert r.pk_recorded - 0.5 - 1e-6 <= r.true_pk < r.pk_recorded + 0.5 + 1e-6
        if r.junction is not None:
            assert r.selectin == 1


def test_degradations_are_nested_across_scenarios(corridor):
    c, registry = corridor
    recs = tb.simulate_truth(c, registry, random.Random(5))
    draws = tb.draw_degradations(recs, random.Random(6))
    injected = {}
    for name, p in tb.SCENARIOS.items():
        _, causes = tb.make_events(c, recs, draws, p)
        injected[name] = [bool(set(x) - {"no landmark within 300 m (structural)"}) for x in causes]
    assert not any(injected["S0"])
    assert all(b for a, b in zip(injected["S1"], injected["S2"]) if a)
    assert sum(injected["S2"]) > sum(injected["S1"]) > 0


def test_spelling_variant_is_deterministic():
    assert tb.spelling_variant("El Maamoura", random.Random(3)) == tb.spelling_variant("El Maamoura", random.Random(3))


def test_full_pass_is_deterministic_and_reproduced_by_run_ablation(inputs, tmp_path):
    osm, reg = inputs
    m1 = tb.run(osm, reg, tmp_path / "a", replicates=3)
    tb.run(osm, reg, tmp_path / "b", replicates=3)
    assert (tmp_path / "a" / "replicates.csv").read_text() == (tmp_path / "b" / "replicates.csv").read_text()
    for name in ("table5_testbed", "tableC1_testbed", "tableC2_testbed", "tableD2_testbed"):
        assert (tmp_path / "a" / f"{name}.md").exists()
    qa = (tmp_path / "a" / "qa_report.md").read_text()
    assert "reproduces the in-process acceptance counts" in qa
    assert m1["protocol_version"] == tb.PROTOCOL_VERSION
    assert len(m1["anchors"]) == 5
