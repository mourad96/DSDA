"""Table D.2: component ablation of the DSDA score on a corridor (e.g. RR27, N = 83).

All configurations share R_max = 500 m, sigma = 150 m and the gate Cs >= 0.85.
Only the base weights (w1, w2, w3) change. Fallback records (PK omitted or
unresolved) follow Algorithm 1: w2 = 0 and its weight is transferred to
toponymy (w1 <- w1 + w2), except in the PK-only baseline, which has nothing to
fall back on: those records are counted as not accepted and are excluded from
the inclusive mean (the inclusive n is reported). The intersection pass applies
in every configuration (w1 <- w1 + w3, w3 <- 0). Ties are broken by Cs, then
distance to k_PK, then Node_ID. Ground truth is read only after all decisions
are taken (dsda.evaluation).

Input files (UTF-8 CSV, projected coordinates in metres, e.g. UTM 32N):
  nodes.csv         node_id, route, pk_marker, gazetteer, x, y[, lat, lon]
                    (gazetteer: several names separated by '|')
  pk_posts.csv      route, pk_marker, x, y[, sector]
  events.csv        event_id, route, pk_marker, landmarks, intersection[, muni_x, muni_y]
                    (pk_marker empty if omitted; landmarks separated by '|';
                     intersection 0/1; columns = MLLM output, not the registry)
  ground_truth.csv  event_id, x, y        (reference positions, used post hoc only)

Usage:
  python scripts/run_ablation.py --data DIR [--out DIR]
Outputs: table_d2.csv, table_d2.md and decisions_<config>.csv (one row per record).
"""

from __future__ import annotations

import argparse
import csv
import sys
from pathlib import Path
from typing import Dict, List, Optional, Tuple

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))  # run without installing

from dsda import (  # noqa: E402
    CrashEvent,
    DSDAEngine,
    DSDAParameters,
    GisDatabase,
    PKPost,
    Point2D,
    compute_geocoding_accuracy,
)

CONFIGS: List[Tuple[str, Tuple[float, float, float]]] = [
    ("Nominal LRS PK only (proximity baseline)", (0.000, 1.000, 0.000)),
    ("Toponymy only (no proximity, no topology)", (1.000, 0.000, 0.000)),
    ("Without topology (S_top + S_prox)", (0.571, 0.429, 0.000)),
    ("Without proximity (S_top + S_topo)", (0.800, 0.000, 0.200)),
    ("Full DSDA", (0.500, 0.375, 0.125)),
]


def _read(path: Path) -> List[Dict[str, str]]:
    with open(path, newline="", encoding="utf-8-sig") as fh:
        return [{k.strip(): (v or "").strip() for k, v in row.items()} for row in csv.DictReader(fh)]


def _split(value: str) -> List[str]:
    return [v.strip() for v in value.split("|") if v.strip()]


def load(data_dir: Path):
    node_records = []
    for r in _read(data_dir / "nodes.csv"):
        rec = {
            "node_name": r["node_id"],
            "PK_marker": r.get("pk_marker", ""),
            "Gazetteer": _split(r.get("gazetteer", "")),
            "Highway_Hierarchy": r["route"],
            "x": float(r["x"]),
            "y": float(r["y"]),
        }
        if r.get("lat") and r.get("lon"):
            rec["WGS84_Coordinates"] = (float(r["lat"]), float(r["lon"]))
        node_records.append(rec)
    posts = [
        PKPost(r["route"], r["pk_marker"], Point2D(float(r["x"]), float(r["y"])), r.get("sector") or None)
        for r in _read(data_dir / "pk_posts.csv")
    ]
    events = []
    for r in _read(data_dir / "events.csv"):
        muni: Optional[Point2D] = None
        if r.get("muni_x") and r.get("muni_y"):
            muni = Point2D(float(r["muni_x"]), float(r["muni_y"]))
        events.append(
            CrashEvent(
                event_id=r["event_id"],
                route=r["route"],
                pk_marker=r.get("pk_marker") or None,
                narrative_landmarks=_split(r.get("landmarks", "")),
                municipality_centroid=muni,
                intersection_descriptors=r.get("intersection", "0") in {"1", "true", "True", "TRUE"},
            )
        )
    truth = {r["event_id"]: Point2D(float(r["x"]), float(r["y"])) for r in _read(data_dir / "ground_truth.csv")}
    return GisDatabase.from_records(node_records, pk_posts=posts), events, truth


def run(data_dir: Path, out_dir: Path) -> List[Dict[str, str]]:
    db, events, truth = load(data_dir)
    missing = [e.event_id for e in events if e.event_id not in truth]
    if missing:
        raise SystemExit(f"Ground truth missing for {len(missing)} records: {missing[:10]}")
    out_dir.mkdir(parents=True, exist_ok=True)
    n = len(events)
    rows = []
    for name, (w1, w2, w3) in CONFIGS:
        policy = "reject" if (w1 == 0.0 and w3 == 0.0) else "transfer"
        engine = DSDAEngine(DSDAParameters(w1=w1, w2=w2, w3=w3, fallback_policy=policy))
        results = engine.process_corridor(events, db)
        rep = compute_geocoding_accuracy(results, truth)  # post hoc only
        slug = name.split(" (")[0].lower().replace(" ", "_")
        with open(out_dir / f"decisions_{slug}.csv", "w", newline="", encoding="utf-8") as fh:
            wr = csv.writer(fh)
            wr.writerow(["event_id", "mode", "status", "selected_node", "cs", "e_geo_m"])
            for r in results:
                e = r.selected_node.coords.distance_to(truth[r.event_id]) if r.selected_node else ""
                wr.writerow([r.event_id, r.mode.value, r.status.value,
                             r.selected_node.node_name if r.selected_node else "",
                             f"{r.best_score:.4f}", f"{e:.2f}" if e != "" else ""])
        c, i = rep.conditional, rep.inclusive
        rows.append({
            "Configuration": name,
            "Weights (w1, w2, w3)": f"({w1:.3f}, {w2:.3f}, {w3:.3f})",
            "Automated throughput": f"{rep.n_accepted}/{n} ({100 * rep.n_accepted / n:.1f}%)",
            "Conditional mean E_geo (m)": f"{c.mean:.1f}" if c.n else "n/a",
            "Inclusive mean E_geo (m)": f"{i.mean:.1f}" if i.n else "n/a",
            "Conditional P90 (m)": f"{c.p90:.1f}" if c.n else "n/a",
            "Inclusive n": str(i.n),
            "Conditional P95 (m)": f"{c.p95:.1f}" if c.n else "n/a",
            "Inclusive RMSE (m)": f"{i.rmse:.1f}" if i.n else "n/a",
        })
    with open(out_dir / "table_d2.csv", "w", newline="", encoding="utf-8") as fh:
        wr = csv.DictWriter(fh, fieldnames=list(rows[0]))
        wr.writeheader()
        wr.writerows(rows)
    with open(out_dir / "table_d2.md", "w", encoding="utf-8") as fh:
        fh.write("| " + " | ".join(rows[0]) + " |\n|" + "---|" * len(rows[0]) + "\n")
        for r in rows:
            fh.write("| " + " | ".join(r.values()) + " |\n")
    return rows


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--data", type=Path, required=True)
    ap.add_argument("--out", type=Path, default=Path("ablation_out"))
    args = ap.parse_args()
    for r in run(args.data, args.out):
        print(r)


if __name__ == "__main__":
    main()
