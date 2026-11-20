"""scripts/run_ablation.py on the synthetic example (format and consistency only)."""

import importlib.util
from pathlib import Path

from dsda import DSDAEngine, compute_geocoding_accuracy

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data" / "example_synthetic"


def _module():
    spec = importlib.util.spec_from_file_location("run_ablation", ROOT / "scripts" / "run_ablation.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def test_ablation_rows_and_full_model_consistency(tmp_path):
    mod = _module()
    rows = mod.run(DATA, tmp_path)
    assert [r["Configuration"] for r in rows] == [name for name, _ in mod.CONFIGS]
    assert (tmp_path / "table_d2.csv").exists() and (tmp_path / "table_d2.md").exists()

    # The "Full DSDA" row must equal a direct run of the default engine
    db, events, truth = mod.load(DATA)
    rep = compute_geocoding_accuracy(DSDAEngine().process_corridor(events, db), truth)
    full = rows[-1]
    assert full["Automated throughput"].startswith(f"{rep.n_accepted}/{len(events)}")
    assert full["Conditional mean E_geo (m)"] == f"{rep.conditional.mean:.1f}"
    assert full["Inclusive mean E_geo (m)"] == f"{rep.inclusive.mean:.1f}"


def test_pk_only_baseline_rejects_records_without_pk(tmp_path):
    mod = _module()
    mod.run(DATA, tmp_path)
    lines = (tmp_path / "decisions_nominal_lrs_pk_only.csv").read_text(encoding="utf-8").splitlines()
    s05 = next(line for line in lines if line.startswith("S05,"))
    assert "SECTOR_FALLBACK,MANUAL_REVIEW_REQUIRED,," in s05
