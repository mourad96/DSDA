"""Tests of the frozen HRRS module (dsda/hrrs.py, protocol v1.3, section 5)."""

from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pytest

pytest.importorskip("scipy")
pd = pytest.importorskip("pandas")

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from dsda import hrrs  # noqa: E402

DATA = ROOT / "data" / "rr27_82_anonymized.csv"


@pytest.fixture(scope="module")
def registry():
    d = pd.read_csv(DATA)
    return hrrs.bin_index(d.pk.values.astype(float)), d.oss.values.astype(float), d


def test_axis_and_windows():
    assert len(hrrs.PKS) == 16 and hrrs.AXIS == (26.5, 42.5)
    assert len(hrrs.WINDOWS) == 16 + 15 + 14 + 13 + 12 == 70
    assert list(hrrs.bin_index(np.array([26.5, 27.49, 42.49, 42.5, 26.49, np.nan]))) == [0, 0, 15, -1, -1, -1]


def test_registry_figures(registry):
    bins, oss, d = registry
    assert len(d) == 82 and int((d.fatalities > 0).sum()) == 26 and int(oss.sum()) == 550
    E = hrrs.exposure()
    assert 82 / E.sum() == pytest.approx(9.08, abs=0.01)


def test_macro_scale_reference(registry):
    bins, oss, _ = registry
    m = hrrs.macro_table(np.bincount(bins, minlength=16).astype(float))
    assert m["HRRS-2"]["n"] == 33
    assert m["HRRS-2"]["Tc"] == pytest.approx(13.23, abs=0.01)
    assert m["HRRS-2"]["LCB"] == pytest.approx(13.68, abs=0.01)
    assert m["HRRS-2"]["macro_tier1"] and m["HRRS-1"]["macro_clear"]
    res = hrrs.classify(bins, oss, draws=100, seed=1, with_scans=False)
    assert res["tiers"] == {"HRRS-1": 3, "HRRS-2": 1, "HRRS-3": 2, "HRRS-4": 2}
    assert res["oss_rank1_pk"] == 41 and res["oss_km"][41 - 27] == 107


def test_permutation_moments_exact():
    rng = np.random.default_rng(0)
    bins = rng.integers(0, 16, size=40)
    oss = rng.integers(1, 30, size=40).astype(float)
    sc = hrrs.oss_permutation_scan(bins, oss, draws=20000, seed=3)
    # z statistics of permuted sums have mean ~0 and variance ~1 for a window
    onehot = np.zeros((40, 16)); onehot[np.arange(40), bins] = 1
    member = onehot @ hrrs._WIN_MATRIX.T
    w = int(np.argmax(member.sum(axis=0) * (40 - member.sum(axis=0))))
    sims = np.array([rng.permutation(oss) @ member[:, w] for _ in range(20000)])
    n_w = member[:, w].sum()
    assert sims.mean() == pytest.approx(n_w * oss.mean(), rel=0.01)
    assert sims.var() == pytest.approx(n_w * (40 - n_w) / 39 * oss.var(), rel=0.05)
    assert np.all((sc.p_adj >= sc.p_raw - 1e-12))


def test_empty_and_constant_inputs():
    empty = hrrs.classify(np.array([], dtype=int), np.array([]), draws=50, seed=0)
    assert all(t != 1 for t in empty["tiers"].values()) and empty["oss_rank1_pk"] is None
    const = hrrs.oss_permutation_scan(np.array([1, 2, 3]), np.array([5.0, 5.0, 5.0]), 50, 0)
    assert np.all(const.p_adj == 1.0)


def test_clusters_do_not_overlap(registry):
    bins, oss, _ = registry
    sc = hrrs.frequency_scan(np.bincount(bins, minlength=16).astype(float), 2000, 2026)
    taken = np.zeros(16, dtype=bool)
    for w in hrrs.clusters(sc):
        i, L = hrrs.WINDOWS[w]
        assert not taken[i:i + L].any()
        taken[i:i + L] = True
    assert hrrs.window_label(sc.best) == "PK 33-37"


def test_half_kilometre_helpers():
    pytest.importorskip("pyproj")
    pytest.importorskip("shapely")
    sys.path.insert(0, str(ROOT / "scripts"))
    import end_to_end_hrrs as e2e
    pos = np.array([34.0, 34.264, 34.9, np.nan, 26.5])
    post = np.array([True, False, False, False, False])
    c = e2e.half_counts(pos, post)
    assert c[14] == 0.5 and c[15] == 1.5 and c[16] == 1.0 and c[0] == 1.0 and c.sum() == 4.0
    credit = e2e.half_credit(np.array([34.0, 34.0, 35.0, 34.3, np.nan]), np.array([True, True, True, False, False]),
                             np.array([33.7, 34.2, 34.2, 34.2, 34.2]))
    assert list(credit) == [0.5, 0.5, 0.0, 1.0, 0.0]
