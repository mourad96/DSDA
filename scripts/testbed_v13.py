"""Protocol v1.3 testbed (Task 1): 82 RR27 crashes, geometric junction flag.

Simulates true positions on the real OSM graph, the reports and their
degradations (S0, S1, S2), runs DSDA (Full DSDA at sigma = 150, 250, 350 m and
the ablation configurations at 150 m) and writes:
  results/ablation_v1_3.csv and .md      Task 1 ablation (all scenarios)
  results/_cache/testbed_v13.npz         per-record decisions for Tasks 2 and 3
  results/testbed_v13_manifest.json      hashes, seeds, anchors, QA

Usage: python scripts/testbed_v13.py [--replicates 1000]
"""

from __future__ import annotations

import argparse
import csv
import datetime as _dt
import json
import math
import random
import sys
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import numpy as np
import pandas as pd
from scipy.spatial import cKDTree
from shapely.geometry import Point

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "scripts"))

import osm_testbed as tb  # noqa: E402
from dsda import CrashEvent, DSDAEngine, DSDAParameters, Point2D  # noqa: E402

# ======================================================================
# PROTOCOL v1.3 (testbed/PROTOCOL_v1.3.md)
# ======================================================================
PROTOCOL_VERSION = "1.3"
BASE_SEED = 2026
REPLICATES = 1000
SIGMAS = (150.0, 250.0, 350.0)
JUNCTION_RADIUS_M = 30.0
PLANTED_N = 10
PLANTED_HALF_WIDTH_M = 25.0
PLANTED_TARGET_PK = 34.0
SCENARIOS: Dict[str, Dict[str, float]] = {
    "S0": dict(p_omit=0.00, p_sub=0.00, p_typo=0.00, p_pk_shift=0.00, p_pk_missing=0.00, p_gis_gap=0.00,
               p_j_omit=0.00, p_j_fp=0.00),
    "S1": dict(p_omit=0.15, p_sub=0.05, p_typo=0.25, p_pk_shift=0.05, p_pk_missing=0.05, p_gis_gap=0.10,
               p_j_omit=0.10, p_j_fp=0.05),
    "S2": dict(p_omit=0.30, p_sub=0.10, p_typo=0.50, p_pk_shift=0.10, p_pk_missing=0.10, p_gis_gap=0.20,
               p_j_omit=0.20, p_j_fp=0.10),
}
FULL = (0.500, 0.375, 0.125)
CONFIGS = [  # (name, weights, junction pass, fallback policy)
    ("Full DSDA, junction pass ON", FULL, True, "transfer"),
    ("Full DSDA, junction pass OFF", FULL, False, "transfer"),
    ("Toponymy only", (1.0, 0.0, 0.0), True, "transfer"),
    ("Without topology", (0.571, 0.429, 0.0), True, "transfer"),
    ("Without proximity", (0.8, 0.0, 0.2), True, "transfer"),
    ("Nominal LRS PK only", (0.0, 1.0, 0.0), True, "reject"),
]
BASELINES = ("Nominal PK post (no geocoding)", "Municipality centroid")
GATE = 0.85
# ======================================================================

DRAW_KEYS = ("p_omit", "p_sub", "p_typo", "p_pk_shift", "p_pk_missing", "p_j_omit", "p_j_fp")


def load_crashes(path: Path) -> pd.DataFrame:
    d = pd.read_csv(path)
    assert len(d) == 82 and d.pk.between(27, 42).all()
    return d


class Setup:
    """Corridor, GIS layer and fixed geometry (identical in every replicate)."""

    def __init__(self, osm_path: Path, crashes: pd.DataFrame):
        self.osm_path = osm_path
        self.data = tb.load_osm(osm_path)
        c = tb.build_corridor(self.data)
        tb.calibrate(c, self.data)
        tb.build_gis(c, self.data)
        registry = [(f"RR27-{i:03d}", int(pk), 0) for i, pk in zip(crashes.id, crashes.pk)]
        c.posts = tb.pk_posts(c, registry)
        self.c = c
        self.nodes = tb.base_nodes(c)
        self.post_xy = {p.pk_marker: (p.coords.x, p.coords.y) for p in c.posts}
        self.node_pk = {n["node_id"]: c.pk_of_s(c.line.project(Point(n["x"], n["y"]))) for n in self.nodes}
        self.node_xy = {n["node_id"]: (n["x"], n["y"]) for n in self.nodes}
        self.jv = list(c.junctions)
        self.jtree = cKDTree(np.array([c.vxy[v] for v in self.jv]))
        self.feats = c.features
        self.ftree = cKDTree(np.array([(f.x, f.y) for f in self.feats]))
        self.places = c.places
        path_index = {v: k for k, v in enumerate(c.path)}
        jpk = {v: c.pk_of_s(float(c.chain[path_index[v]])) for v in self.jv}
        # planted anchors (protocol v1.3, section 6b)
        vj = min(self.jv, key=lambda v: abs(jpk[v] - PLANTED_TARGET_PK))
        self.plant_primary = {"kind": "junction", "osm": f"node/{vj}", "s": float(c.chain[path_index[vj]]),
                              "pk": jpk[vj], "names": c.junctions[vj], "name": None}
        best = None
        for f in self.feats:
            if f.vertex is None:
                continue
            s = c.line.project(Point(f.x, f.y))
            pk = c.pk_of_s(s)
            if best is None or abs(pk - PLANTED_TARGET_PK) < abs(best[1] - PLANTED_TARGET_PK):
                best = (s, pk, f)
        self.plant_secondary = {"kind": "named feature", "osm": best[2].fid, "s": best[0], "pk": best[1],
                                "name": best[2].name, "offset_m": c.line.distance(Point(best[2].x, best[2].y))}

    def point(self, pk: float) -> Tuple[float, float]:
        return self.c.point_at(self.c.s_of_pk(pk))

    def junction_true(self, xy) -> Tuple[bool, Optional[int]]:
        d, k = self.jtree.query(xy)
        return (d <= JUNCTION_RADIUS_M), (self.jv[k] if d <= JUNCTION_RADIUS_M else None)

    def witness(self, xy, junction: Optional[int]) -> Optional[str]:
        if junction is not None and self.c.junctions[junction]:
            return self.c.junctions[junction][0]
        d, k = self.ftree.query(xy)
        return self.feats[k].name if d <= tb.LANDMARK_RADIUS_M else None

    def muni(self, xy):
        return min(self.places, key=lambda p: math.dist((p[1], p[2]), xy))


def simulate_replicate(st: Setup, crashes: pd.DataFrame, r: int):
    """True positions, witnesses and draws for the 82 crashes and the 20 planted ones."""
    rng_t = random.Random(BASE_SEED + r)
    recs = []
    for pk in crashes.pk:
        tpk = pk - 0.5 + rng_t.random()
        xy = st.point(tpk)
        jt, jv = st.junction_true(xy)
        recs.append({"pk": int(pk), "true_pk": tpk, "xy": xy, "jt": jt, "witness": st.witness(xy, jv),
                     "muni": st.muni(xy), "planted": 0})
    rng_p = random.Random(BASE_SEED + 3_000_000 + r)
    for variant, anchor in ((1, st.plant_primary), (2, st.plant_secondary)):
        for _ in range(PLANTED_N):
            s = anchor["s"] + (2 * rng_p.random() - 1) * PLANTED_HALF_WIDTH_M
            tpk = st.c.pk_of_s(s)
            xy = st.c.point_at(s)
            jt, jv = st.junction_true(xy)
            wit = anchor["name"] if anchor["name"] else st.witness(xy, jv)
            recs.append({"pk": int(math.floor(tpk + 0.5)), "true_pk": tpk, "xy": xy, "jt": jt, "witness": wit,
                         "muni": st.muni(xy), "planted": variant})
    rng_d = random.Random(BASE_SEED + 1_000_000 + r)
    draws = []
    for _ in recs:
        u = {k: rng_d.random() for k in DRAW_KEYS}
        draws.append((u, rng_d.random(), 1 if rng_d.random() < 0.5 else -1, rng_d.randrange(2 ** 31)))
    gap = tb.gis_gap_draws(st.c, random.Random(BASE_SEED + 2_000_000 + r))
    return recs, draws, gap


def make_events(st: Setup, recs, draws, p) -> Tuple[List[CrashEvent], List[Optional[int]]]:
    events, reported = [], []
    for i, (rec, (u, sub_pick, sign, tseed)) in enumerate(zip(recs, draws)):
        lm = rec["witness"]
        if lm is not None and u["p_omit"] < p["p_omit"]:
            lm = None
        if lm is not None and u["p_sub"] < p["p_sub"]:
            idx = st.ftree.query_ball_point(rec["xy"], tb.SUBSTITUTE_RADIUS_M)
            pool = sorted({st.feats[k].name for k in idx
                           if tb.normalize_toponym(st.feats[k].name) != tb.normalize_toponym(lm)})
            if pool:
                lm = pool[int(sub_pick * len(pool)) % len(pool)]
        if lm is not None and u["p_typo"] < p["p_typo"]:
            lm = tb.spelling_variant(lm, random.Random(tseed))
        if u["p_pk_missing"] < p["p_pk_missing"]:
            pk = None
        elif u["p_pk_shift"] < p["p_pk_shift"]:
            pk = rec["pk"] + sign
        else:
            pk = rec["pk"]
        flag = (rec["jt"] and u["p_j_omit"] >= p["p_j_omit"]) or ((not rec["jt"]) and u["p_j_fp"] < p["p_j_fp"])
        events.append(CrashEvent(event_id=f"E{i:03d}", route=tb.ROUTE, pk_marker=None if pk is None else f"PK{pk}",
                                 narrative_landmarks=[lm] if lm else [],
                                 municipality_centroid=Point2D(rec["muni"][1], rec["muni"][2]),
                                 intersection_descriptors=bool(flag)))
        reported.append(pk)
    return events, reported


def summary(values) -> Tuple[float, float, float, int]:
    xs = np.array([v for v in values if v is not None and np.isfinite(v)], dtype=float)
    if len(xs) == 0:
        return (math.nan, math.nan, math.nan, 0)
    return (float(xs.mean()), float(np.percentile(xs, 2.5)), float(np.percentile(xs, 97.5)), len(xs))


def error_stats(errors: List[float]) -> Dict[str, Optional[float]]:
    if not errors:
        return {k: None for k in ("mean", "median", "p90", "p95", "rmse", "max")}
    e = np.array(errors)
    return {"mean": e.mean(), "median": np.percentile(e, 50), "p90": np.percentile(e, 90),
            "p95": np.percentile(e, 95), "rmse": math.sqrt((e ** 2).mean()), "max": e.max()}


def record_metrics(accepted: np.ndarray, egeo: np.ndarray, gated: bool = True) -> Dict[str, Optional[float]]:
    """Per-replicate metrics over the 82 crashes."""
    m: Dict[str, Optional[float]] = {}
    located = np.isfinite(egeo)
    if gated:
        acc = accepted & located
        m["accepted"] = float(acc.sum())
        cs = error_stats(list(egeo[acc]))
        for k, v in cs.items():
            m[f"cond_{k}"] = v
        m["accepted_egeo_gt_150"] = float((egeo[acc] > tb.GROSS_ERROR_M).sum())
    inc = error_stats(list(egeo[located]))
    m["incl_n"] = float(located.sum())
    for k, v in inc.items():
        m[f"incl_{k}"] = v
    return m


def run(args) -> None:
    crashes = load_crashes(args.data)
    st = Setup(args.osm, crashes)
    tb.CachedGis._cache = {}
    R, NREC = args.replicates, 82 + 2 * PLANTED_N
    scen_names = list(SCENARIOS)
    shape = (len(scen_names), len(SIGMAS), R, NREC)
    cs_arr = np.full(shape, np.nan)
    pk_arr = np.full(shape, np.nan)
    eg_arr = np.full(shape, np.nan)
    rep_pk = np.full((len(scen_names), R, NREC), np.nan)
    post_eg = np.full((len(scen_names), R, NREC), np.nan)
    true_pk = np.full((R, NREC), np.nan)
    jt_arr = np.zeros((R, NREC), dtype=bool)
    per_rep: Dict[Tuple[str, str], List[dict]] = {}
    engines = {(cfg[0], s): DSDAEngine(DSDAParameters(w1=cfg[1][0], w2=cfg[1][1], w3=cfg[1][2], sigma=s,
                                                       fallback_policy=cfg[3]))
               for cfg in CONFIGS for s in SIGMAS}
    main = slice(0, 82)
    no_landmark = 0
    for r in range(R):
        recs, draws, gap = simulate_replicate(st, crashes, r)
        no_landmark += sum(x["witness"] is None for x in recs[:82])
        true_pk[r] = [x["true_pk"] for x in recs]
        jt_arr[r] = [x["jt"] for x in recs]
        truth = np.array([x["xy"] for x in recs])
        for si, scen in enumerate(scen_names):
            p = SCENARIOS[scen]
            events, reported = make_events(st, recs, draws, p)
            rep_pk[si, r] = [np.nan if v is None else v for v in reported]
            gis, _ = tb.make_gis(st.c, st.nodes, gap, p["p_gis_gap"])
            for k, v in enumerate(reported):
                if v is not None and f"PK{v}" in st.post_xy:
                    post_eg[si, r, k] = math.dist(st.post_xy[f"PK{v}"], truth[k])
            for gi, sig in enumerate(SIGMAS):
                res = engines[(CONFIGS[0][0], sig)].process_corridor(events, gis)
                for k, x in enumerate(res):
                    if x.selected_node is not None:
                        nid = x.selected_node.node_name
                        cs_arr[si, gi, r, k] = x.best_score
                        pk_arr[si, gi, r, k] = st.node_pk[nid]
                        eg_arr[si, gi, r, k] = math.dist(st.node_xy[nid], truth[k])
            # ablation at sigma = 150 m on the 82 crashes
            acc0 = cs_arr[si, 0, r, main] >= GATE
            per_rep.setdefault((scen, CONFIGS[0][0]), []).append(record_metrics(acc0, eg_arr[si, 0, r, main]))
            for name, w, jpass, pol in CONFIGS[1:]:
                ev = events[:82] if jpass else [CrashEvent(e.event_id, e.route, e.pk_marker, e.narrative_landmarks,
                                                           municipality_centroid=e.municipality_centroid,
                                                           intersection_descriptors=False) for e in events[:82]]
                res = engines[(name, 150.0)].process_corridor(ev, gis)
                acc = np.array([x.best_score >= GATE and x.selected_node is not None for x in res])
                eg = np.array([math.dist(st.node_xy[x.selected_node.node_name], truth[k]) if x.selected_node else np.nan
                               for k, x in enumerate(res)])
                per_rep.setdefault((scen, name), []).append(record_metrics(acc, eg))
            per_rep.setdefault((scen, BASELINES[0]), []).append(
                record_metrics(None, post_eg[si, r, main], gated=False))
            muni_eg = np.array([math.dist((x["muni"][1], x["muni"][2]), x["xy"]) for x in recs[:82]])
            per_rep.setdefault((scen, BASELINES[1]), []).append(record_metrics(None, muni_eg, gated=False))
        if (r + 1) % 100 == 0:
            print(f"replicate {r + 1}/{R}", flush=True)

    # ---------------- outputs ----------------
    out = args.out
    (out / "_cache").mkdir(parents=True, exist_ok=True)
    np.savez_compressed(out / "_cache" / "testbed_v13.npz", cs=cs_arr, sel_pk=pk_arr, egeo=eg_arr,
                        reported_pk=rep_pk, post_egeo=post_eg, true_pk=true_pk, junction_true=jt_arr,
                        oss=np.concatenate([crashes.oss.values.astype(float), np.full(2 * PLANTED_N, np.nan)]),
                        registry_pk=np.concatenate([crashes.pk.values.astype(float),
                                                    np.full(2 * PLANTED_N, np.nan)]),
                        planted=np.array([0] * 82 + [1] * PLANTED_N + [2] * PLANTED_N),
                        scenarios=np.array(scen_names), sigmas=np.array(SIGMAS))
    metrics = ["accepted", "cond_mean", "cond_median", "cond_p90", "cond_p95", "accepted_egeo_gt_150",
               "incl_n", "incl_mean", "incl_p90", "incl_p95", "incl_rmse", "incl_max"]
    rows = []
    names = [c[0] for c in CONFIGS] + list(BASELINES)
    weights = {c[0]: c[1] for c in CONFIGS}
    for scen in scen_names:
        for name in names:
            reps = per_rep[(scen, name)]
            for mkey in metrics:
                if mkey not in reps[0]:
                    continue
                mean, lo, hi, k = summary([m[mkey] for m in reps])
                rows.append({"scenario": scen, "configuration": name,
                             "weights": "" if name not in weights else "({:.3f}, {:.3f}, {:.3f})".format(*weights[name]),
                             "sigma_m": 150 if name in weights else "", "gate": GATE if name in weights else "",
                             "metric": mkey, "mean": mean, "p2_5": lo, "p97_5": hi, "replicates_defined": k})
    with open(out / "ablation_v1_3.csv", "w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=list(rows[0]), lineterminator="\n")
        w.writeheader()
        for row in rows:
            w.writerow({k: (f"{v:.4f}" if isinstance(v, float) and np.isfinite(v) else ("" if isinstance(v, float) else v))
                        for k, v in row.items()})
    _ablation_md(out, rows, R)
    manifest = {
        "protocol_version": PROTOCOL_VERSION, "run_utc": _dt.datetime.now(_dt.timezone.utc).isoformat(timespec="seconds"),
        "code_commit": tb.git_commit(), "script_sha256": tb.sha256(Path(__file__)),
        "osm_file": str(args.osm.relative_to(ROOT)) if args.osm.is_relative_to(ROOT) else args.osm.name,
        "osm_sha256": tb.sha256(args.osm), "osm_timestamp": st.data.timestamp,
        "data_sha256": tb.sha256(args.data), "replicates": R, "base_seed": BASE_SEED, "scenarios": SCENARIOS,
        "sigmas": SIGMAS, "gate": GATE, "junction_radius_m": JUNCTION_RADIUS_M,
        "plant_primary": {k: v for k, v in st.plant_primary.items()},
        "plant_secondary": {k: (round(v, 3) if isinstance(v, float) else v) for k, v in st.plant_secondary.items()},
        "qa": st.c.qa,
        "junction_true_share_82": float(jt_arr[:, :82].mean()),
        "no_landmark_share_82": no_landmark / (82 * R),
    }
    (out / "testbed_v13_manifest.json").write_text(json.dumps(manifest, indent=2, ensure_ascii=False, default=str),
                                                   encoding="utf-8")
    print("done", manifest["code_commit"])


def _ablation_md(out: Path, rows: List[dict], R: int) -> None:
    def cell(scen, name, metric, d=1):
        for row in rows:
            if row["scenario"] == scen and row["configuration"] == name and row["metric"] == metric:
                if not np.isfinite(row["mean"]):
                    return "n/a"
                txt = f"{row['mean']:.{d}f} [{row['p2_5']:.{d}f}, {row['p97_5']:.{d}f}]"
                return txt + ("" if row["replicates_defined"] == R else f" ({row['replicates_defined']}/{R})")
        return "n/a"

    names = [c[0] for c in CONFIGS] + list(BASELINES)
    with open(out / "ablation_v1_3.md", "w", encoding="utf-8") as fh:
        for scen in SCENARIOS:
            fh.write(f"\n## Scenario {scen} (mean over {R} replicates [2.5th, 97.5th percentile])\n\n")
            fh.write("| Configuration | Accepted (of 82) | Conditional mean (m) | Conditional median (m) | "
                     "Conditional P90 (m) | Accepted with E_geo > 150 m | Inclusive mean (m) | Inclusive P90 (m) |\n")
            fh.write("|---|---|---|---|---|---|---|---|\n")
            for name in names:
                fh.write(f"| {name} | {cell(scen, name, 'accepted')} | {cell(scen, name, 'cond_mean')} | "
                         f"{cell(scen, name, 'cond_median')} | {cell(scen, name, 'cond_p90')} | "
                         f"{cell(scen, name, 'accepted_egeo_gt_150')} | {cell(scen, name, 'incl_mean')} | "
                         f"{cell(scen, name, 'incl_p90')} |\n")


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--osm", type=Path, default=ROOT / "data" / "osm" / "rr27_corridor_2026-11-23.json.gz")
    ap.add_argument("--data", type=Path, default=ROOT / "data" / "rr27_82_anonymized.csv")
    ap.add_argument("--out", type=Path, default=ROOT / "results")
    ap.add_argument("--replicates", type=int, default=REPLICATES)
    run(ap.parse_args())


if __name__ == "__main__":
    main()
