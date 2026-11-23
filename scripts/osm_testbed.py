"""Controlled geospatial testbed for DSDA on the real OpenStreetMap graph (RR27).

Protocol: testbed/PROTOCOL.md (version PROTOCOL_VERSION below). Every constant
in the PROTOCOL section of this file is fixed by that document; both were
committed before any real OpenStreetMap extract was loaded. Results must be
reported as they come out of this script, whatever they are.

What is real and what is simulated
  real       OpenStreetMap road graph, toponyms and structures (extract supplied
             by the user, its OSM timestamp is recorded in manifest.json);
             RR27 registry fields PK (integer) and selectin (intersection flag);
             the five PK calibration anchors supplied by the authors.
  simulated  the true crash positions (drawn inside the recorded PK interval),
             the landmarks a report would contain, and every degradation.
DSDA itself is run unchanged (dsda.engine, published weights, sigma, R_max and
gate). Ground truth is read only after all decisions are taken.

Inputs
  --osm       Overpass API JSON or OSM XML (query `out geom`), or .osm.pbf
              (needs the `osmium` package), covering the RR27 corridor.
  --registry  RR27 registry (Excel, sheet MC27, columns PK and selectin).

Outputs (--out DIR)
  manifest.json, qa_report.md
  table5_testbed.{csv,md}    corridor metrics by scenario (S0, S1, S2)
  tableC1_testbed.{csv,md}   error distribution, reference scenario S1
  tableC2_testbed.{csv,md}   records routed to manual review, S1 replicate 0
  tableD2_testbed.{csv,md}   component ablation, reference scenario S1
  replicates.csv             one row per scenario x replicate x configuration
  S1_r0/                     nodes.csv, pk_posts.csv, events.csv,
                             ground_truth.csv for scenario S1 replicate 0, plus
                             the output of scripts/run_ablation.py on them.

Usage
  python scripts/osm_testbed.py --osm export.json --registry rr27.xlsx --out testbed_out
"""

from __future__ import annotations

import argparse
import csv
import datetime as _dt
import hashlib
import json
import math
import platform
import random
import re
import statistics
import subprocess
import sys
import unicodedata
import xml.etree.ElementTree as ET
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, Iterable, List, Optional, Sequence, Tuple

import networkx as nx
import numpy as np
from pyproj import Transformer
from scipy.spatial import cKDTree
from shapely.geometry import LineString, MultiPoint, Point, Polygon
from shapely.ops import nearest_points

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "scripts"))

from dsda import (  # noqa: E402
    CrashEvent,
    DSDAEngine,
    DSDAParameters,
    GisDatabase,
    GisNode,
    PKPost,
    Point2D,
    compute_geocoding_accuracy,
    normalize_toponym,
)
from dsda.models import GeocodingStatus, WGS84Point  # noqa: E402
from run_ablation import CONFIGS  # noqa: E402
import run_ablation  # noqa: E402

# ======================================================================
# PROTOCOL (fixed by testbed/PROTOCOL.md; do not change after data loading)
# ======================================================================
PROTOCOL_VERSION = "1.1"
CRS = "EPSG:32632"                      # WGS 84 / UTM zone 32N
ROUTE = "RR27"
ROUTE_REF = r"^(RR|MC|C|RL|R)\s*-?\s*27$"  # OSM ref values identifying the route
ANCHORS: List[Tuple[float, str, Tuple[str, ...]]] = [
    (27.000, "place", ("beni khiar", "bni khiar", "beni khiyar")),
    (31.240, "place", ("maamoura",)),
    (33.080, "hydraulic", ()),
    (33.560, "hydraulic", ()),
    (36.300, "place", ("mazraa",)),
]
HYDRAULIC_SEARCH_M = 300.0     # max distance between predicted and OSM structure
ORIGIN_PK = 27.000             # v1.1: Beni Khiar, origin of the unit-scale calibration
UNIT_SCALE = 0.001             # v1.1: PK-km per metre of centerline
SCALE_FLAG = (0.80, 1.25)      # QA flag on PK km per OSM km between anchors
PK_HALF_WIDTH_KM = 0.5         # integer PK n -> true PK ~ U[n - 0.5, n + 0.5)
FEATURE_BUFFER_M = 700.0       # named features kept within this distance of RR27
ATTACH_MAX_M = 150.0           # feature indexed in the GIS if a road vertex is this close
LANDMARK_RADIUS_M = 300.0      # a report cites the nearest feature within this radius
SUBSTITUTE_RADIUS_M = 1500.0   # wrong landmark drawn among features within this radius
GROSS_ERROR_M = 150.0          # accepted record with E_geo above this = gross error
SCENARIOS: Dict[str, Dict[str, float]] = {
    "S0": dict(p_omit=0.00, p_sub=0.00, p_typo=0.00, p_pk_shift=0.00, p_pk_missing=0.00, p_flag=0.00, p_gis_gap=0.00),
    "S1": dict(p_omit=0.15, p_sub=0.05, p_typo=0.25, p_pk_shift=0.05, p_pk_missing=0.05, p_flag=0.05, p_gis_gap=0.10),
    "S2": dict(p_omit=0.30, p_sub=0.10, p_typo=0.50, p_pk_shift=0.10, p_pk_missing=0.10, p_flag=0.10, p_gis_gap=0.20),
}
REFERENCE_SCENARIO = "S1"
REPLICATES = 1000
BASE_SEED = 2026
DRIVABLE = {
    "motorway", "trunk", "primary", "secondary", "tertiary", "unclassified", "residential",
    "living_street", "service", "track", "road",
    "motorway_link", "trunk_link", "primary_link", "secondary_link", "tertiary_link",
}
FEATURE_KEYS = (
    "place", "amenity", "shop", "tourism", "leisure", "historic", "man_made", "office",
    "railway", "landuse", "natural", "waterway", "building", "craft", "industrial",
    "healthcare", "public_transport", "highway", "bridge", "sport", "power",
)
MUNICIPAL_PLACES = {"city", "town", "village"}
# ======================================================================

_TO_UTM = Transformer.from_crs("EPSG:4326", CRS, always_xy=True)
_TO_WGS = Transformer.from_crs(CRS, "EPSG:4326", always_xy=True)


def utm(lat: float, lon: float) -> Tuple[float, float]:
    x, y = _TO_UTM.transform(lon, lat)
    return float(x), float(y)


def wgs(x: float, y: float) -> Tuple[float, float]:
    lon, lat = _TO_WGS.transform(x, y)
    return float(lat), float(lon)


# ----------------------------------------------------------------------
# OSM loading (Overpass JSON, OSM XML with `out geom`, or PBF)
# ----------------------------------------------------------------------
@dataclass
class OsmData:
    nodes: Dict[int, Tuple[float, float, Dict[str, str]]]   # tagged nodes: id -> (lat, lon, tags)
    vertex: Dict[int, Tuple[float, float]]                  # every way vertex: id -> (lat, lon)
    ways: List[dict]                                        # {id, tags, nodes, coords}
    relations: List[dict]                                   # {id, tags, ways}
    timestamp: Optional[str] = None


def load_osm(path: Path) -> OsmData:
    suffix = "".join(path.suffixes).lower()
    if suffix.endswith(".pbf"):
        return _load_pbf(path)
    text = path.read_text(encoding="utf-8")
    if text.lstrip().startswith("{"):
        return _load_json(json.loads(text))
    return _load_xml(ET.fromstring(text))


def _load_json(doc: dict) -> OsmData:
    nodes, vertex, ways, rels = {}, {}, [], []
    for e in doc.get("elements", []):
        t = e.get("type")
        if t == "node":
            vertex[e["id"]] = (e["lat"], e["lon"])
            if e.get("tags"):
                nodes[e["id"]] = (e["lat"], e["lon"], e["tags"])
        elif t == "way":
            geom = e.get("geometry") or []
            ids = e.get("nodes") or []
            if not geom and ids and all(i in vertex for i in ids):
                geom = [{"lat": vertex[i][0], "lon": vertex[i][1]} for i in ids]
            coords = [(g["lat"], g["lon"]) for g in geom if g]
            if ids and len(ids) == len(geom):
                for i, g in zip(ids, geom):
                    if g:
                        vertex[i] = (g["lat"], g["lon"])
            ways.append({"id": e["id"], "tags": e.get("tags", {}), "nodes": ids, "coords": coords})
        elif t == "relation":
            rels.append({"id": e["id"], "tags": e.get("tags", {}),
                         "ways": [m["ref"] for m in e.get("members", []) if m.get("type") == "way"]})
    ts = (doc.get("osm3s") or {}).get("timestamp_osm_base")
    return OsmData(nodes, vertex, ways, rels, ts)


def _load_xml(root: ET.Element) -> OsmData:
    nodes, vertex, ways, rels = {}, {}, [], []
    ts = None
    meta = root.find("meta")
    if meta is not None:
        ts = meta.get("osm_base")
    for el in root:
        tags = {t.get("k"): t.get("v") for t in el.findall("tag")}
        if el.tag == "node":
            i, lat, lon = int(el.get("id")), float(el.get("lat")), float(el.get("lon"))
            vertex[i] = (lat, lon)
            if tags:
                nodes[i] = (lat, lon, tags)
        elif el.tag == "way":
            ids, coords = [], []
            for nd in el.findall("nd"):
                ref = int(nd.get("ref"))
                ids.append(ref)
                if nd.get("lat") is not None:
                    vertex[ref] = (float(nd.get("lat")), float(nd.get("lon")))
                if ref in vertex:
                    coords.append(vertex[ref])
            ways.append({"id": int(el.get("id")), "tags": tags, "nodes": ids, "coords": coords})
        elif el.tag == "relation":
            rels.append({"id": int(el.get("id")), "tags": tags,
                         "ways": [int(m.get("ref")) for m in el.findall("member") if m.get("type") == "way"]})
    return OsmData(nodes, vertex, ways, rels, ts)


def _load_pbf(path: Path) -> OsmData:  # pragma: no cover - optional dependency
    import osmium

    data = OsmData({}, {}, [], [], None)

    class H(osmium.SimpleHandler):
        def node(self, n):
            if len(n.tags):
                data.nodes[n.id] = (n.location.lat, n.location.lon, {t.k: t.v for t in n.tags})

        def way(self, w):
            ids, coords = [], []
            for nd in w.nodes:
                if nd.location.valid():
                    ids.append(nd.ref)
                    coords.append((nd.location.lat, nd.location.lon))
                    data.vertex[nd.ref] = coords[-1]
            data.ways.append({"id": w.id, "tags": {t.k: t.v for t in w.tags}, "nodes": ids, "coords": coords})

        def relation(self, r):
            data.relations.append({"id": r.id, "tags": {t.k: t.v for t in r.tags},
                                   "ways": [m.ref for m in r.members if m.type == "w"]})

    H().apply_file(str(path), locations=True)
    return data


def crop(data: OsmData, bbox: Tuple[float, float, float, float]) -> OsmData:
    s, w, n, e = bbox

    def inside(lat, lon):
        return s <= lat <= n and w <= lon <= e

    ways = [wy for wy in data.ways if any(inside(*c) for c in wy["coords"])]
    keep = {i for wy in ways for i in wy["nodes"]}
    nodes = {i: v for i, v in data.nodes.items() if inside(v[0], v[1])}
    vertex = {i: v for i, v in data.vertex.items() if i in keep or i in nodes}
    return OsmData(nodes, vertex, ways, data.relations, data.timestamp)


# ----------------------------------------------------------------------
# Names
# ----------------------------------------------------------------------
NAME_KEYS = ("name:fr", "name", "name:en", "alt_name", "bridge:name", "official_name")


def names_of(tags: Dict[str, str]) -> List[str]:
    out: List[str] = []
    for k in NAME_KEYS:
        v = (tags.get(k) or "").strip()
        for part in v.split(";"):
            part = part.strip()
            if part and part not in out:
                out.append(part)
    return out


def report_name(tags: Dict[str, str]) -> Optional[str]:
    """Name a French-language report would use: name:fr, else name."""
    for k in ("name:fr", "name", "alt_name", "bridge:name"):
        v = (tags.get(k) or "").split(";")[0].strip()
        if v:
            return v
    return None


def is_route_way(tags: Dict[str, str], route_re: re.Pattern) -> bool:
    if "highway" not in tags:
        return False
    return any(route_re.match(p.strip()) for p in (tags.get("ref") or "").split(";"))


# ----------------------------------------------------------------------
# Corridor model
# ----------------------------------------------------------------------
@dataclass
class Feature:
    fid: str
    name: str                 # name used by a report
    names: List[str]          # all names indexed in the GIS
    x: float
    y: float
    kind: str
    vertex: Optional[int] = None   # attached road vertex (None: not indexable)


@dataclass
class Corridor:
    line: LineString
    path: List[int]                     # OSM vertex ids along the centerline
    chain: np.ndarray                   # chainage of each path vertex (m)
    vxy: Dict[int, Tuple[float, float]]  # vertex id -> UTM
    way_of_vertex: Dict[int, List[int]]
    ways: Dict[int, dict]
    route_vertices: set
    anchors: List[dict] = field(default_factory=list)
    pk_s: Tuple[np.ndarray, np.ndarray] = None  # calibration (PK km, s m)
    slope: float = 0.0                          # PK km per metre (least squares)
    features: List[Feature] = field(default_factory=list)
    junctions: Dict[int, List[str]] = field(default_factory=dict)  # vertex -> crossing names
    places: List[Tuple[str, float, float]] = field(default_factory=list)  # municipal places
    posts: List[PKPost] = field(default_factory=list)
    on_path: set = field(default_factory=set)
    qa: List[str] = field(default_factory=list)

    # --- calibration ---------------------------------------------------
    def pk_of_s(self, s: float) -> float:
        pk, ss = self.pk_s
        if s < ss[0]:
            return float(pk[0] + self.slope * (s - ss[0]))
        if s > ss[-1]:
            return float(pk[-1] + self.slope * (s - ss[-1]))
        return float(np.interp(s, ss, pk))

    def s_of_pk(self, p: float) -> float:
        pk, ss = self.pk_s
        if p < pk[0]:
            return float(ss[0] + (p - pk[0]) / self.slope)
        if p > pk[-1]:
            return float(ss[-1] + (p - pk[-1]) / self.slope)
        return float(np.interp(p, pk, ss))

    def point_at(self, s: float) -> Tuple[float, float]:
        p = self.line.interpolate(min(max(s, 0.0), self.line.length))
        return p.x, p.y


def build_corridor(data: OsmData, route_regex: str = ROUTE_REF) -> Corridor:
    route_re = re.compile(route_regex, re.I)
    ways = {w["id"]: w for w in data.ways}
    vxy = {i: utm(*ll) for i, ll in data.vertex.items()}
    route_ways = {w["id"] for w in data.ways if is_route_way(w["tags"], route_re)}
    for r in data.relations:
        if r["tags"].get("route") == "road" and route_re.match((r["tags"].get("ref") or "").strip()):
            route_ways |= {i for i in r["ways"] if i in ways and "highway" in ways[i]["tags"]}
    if not route_ways:
        raise SystemExit(f"No OSM way matches {route_regex}: the route cannot be identified (protocol section 2).")

    g = nx.Graph()
    way_of_vertex: Dict[int, List[int]] = {}
    for w in data.ways:
        hw = w["tags"].get("highway")
        if hw not in DRIVABLE:
            continue
        is_route = w["id"] in route_ways
        ids = [i for i in w["nodes"] if i in vxy]
        for i in ids:
            way_of_vertex.setdefault(i, []).append(w["id"])
        for a, b in zip(ids, ids[1:]):
            d = math.dist(vxy[a], vxy[b])
            wgt = d * (1.0 if is_route else 10.0)
            if g.has_edge(a, b) and g[a][b]["weight"] <= wgt:
                continue
            g.add_edge(a, b, weight=wgt, length=d)
    route_vertices = {i for wid in route_ways for i in ways[wid]["nodes"] if i in vxy}
    rv = sorted(route_vertices)
    pts = np.array([vxy[i] for i in rv])
    hull = MultiPoint([tuple(p) for p in pts]).convex_hull
    cand = [i for i in rv if Point(vxy[i]).distance(hull.exterior if isinstance(hull, Polygon) else hull) < 1.0]
    cp = np.array([vxy[i] for i in cand])
    dmat = np.sqrt(((cp[:, None, :] - cp[None, :, :]) ** 2).sum(-1))
    a, b = np.unravel_index(np.argmax(dmat), dmat.shape)
    try:
        path = nx.shortest_path(g, cand[a], cand[b], weight="weight")
    except nx.NetworkXNoPath:
        raise SystemExit("The route endpoints are not connected in the extracted road graph.")
    coords = [vxy[i] for i in path]
    chain = np.concatenate([[0.0], np.cumsum([math.dist(p, q) for p, q in zip(coords, coords[1:])])])
    on_route = sum(1 for u, v in zip(path, path[1:]) if u in route_vertices and v in route_vertices)
    c = Corridor(LineString(coords), path, chain, vxy, way_of_vertex, ways, route_vertices)
    c.qa.append(f"Route ways matched ({route_regex}): {len(route_ways)}; centerline length "
                f"{c.line.length / 1000:.2f} km; share of centerline edges on tagged route ways: "
                f"{on_route / max(1, len(path) - 1):.1%}.")
    return c


def _norm_place(tags: Dict[str, str]) -> List[str]:
    return [normalize_toponym(n) for n in names_of(tags)]


def calibrate(c: Corridor, data: OsmData) -> None:
    """Piecewise-linear PK calibration on the authors' anchors (protocol section 3)."""
    found = []
    for pk, kind, keys in ANCHORS:
        if kind != "place":
            continue
        best = None
        for i, (lat, lon, tags) in data.nodes.items():
            if "place" not in tags:
                continue
            if not any(k in n for n in _norm_place(tags) for k in keys):
                continue
            x, y = utm(lat, lon)
            d = c.line.distance(Point(x, y))
            if best is None or d < best[0]:
                best = (d, i, report_name(tags), x, y)
        if best is None:
            c.qa.append(f"Check anchor PK {pk:.3f} ({keys[0]}): no OSM place of that name.")
            continue
        s = c.line.project(Point(best[3], best[4]))
        found.append({"pk": pk, "kind": "place", "osm": f"node/{best[1]}", "name": best[2],
                      "offset_m": round(best[0], 1), "s": s})
    if len(found) < 2:
        raise SystemExit("Fewer than two place anchors found: chainage orientation impossible.")
    found.sort(key=lambda a: a["pk"])
    if found[-1]["s"] < found[0]["s"]:   # orient chainage along increasing PK
        coords = list(c.line.coords)[::-1]
        c.path = c.path[::-1]
        c.line = LineString(coords)
        c.chain = np.concatenate([[0.0], np.cumsum([math.dist(p, q) for p, q in zip(coords, coords[1:])])])
        for a in found:
            a["s"] = c.line.length - a["s"]

    # hydraulic structures: bridges on the centerline and waterway crossings
    struct = []
    on_path = set(c.path)
    for w in c.ways.values():
        t = w["tags"]
        if "highway" in t and t.get("bridge", "no") != "no" and any(i in on_path for i in w["nodes"]):
            xs = [c.vxy[i] for i in w["nodes"] if i in on_path]
            if xs:
                mid = np.mean(xs, axis=0)
                struct.append((c.line.project(Point(*mid)), f"way/{w['id']} (bridge)", report_name(t)))
        if "waterway" in t and len(w["coords"]) >= 2:
            ln = LineString([utm(*ll) for ll in w["coords"]])
            inter = ln.intersection(c.line)
            pts = [inter] if inter.geom_type == "Point" else list(getattr(inter, "geoms", []))
            for p in pts:
                if p.geom_type == "Point":
                    struct.append((c.line.project(p), f"way/{w['id']} (waterway {t.get('waterway')})", report_name(t)))
    struct.sort()
    merged = []
    for s, ref, nm in struct:
        if merged and s - merged[-1][0] < 30.0:
            continue
        merged.append((s, ref, nm))
    # Protocol v1.1 (amendment of 23 November 2026, before any DSDA run): the
    # authors' anchors could not all be located on OSM (see PROTOCOL.md, section 0).
    # Calibration = origin anchor + unit scale (1 PK-km = 1 km along the RR27
    # centerline); the other anchors are reported as checks only.
    origin = next((a for a in found if a["pk"] == ORIGIN_PK), None)
    if origin is None:
        raise SystemExit(f"Origin anchor PK {ORIGIN_PK:.3f} not found on OSM: protocol v1.1 stops here.")
    c.pk_s = (np.array([origin["pk"]]), np.array([origin["s"]]))
    c.slope = UNIT_SCALE
    origin["role"] = "origin"
    c.anchors = [origin]
    for a in found:
        if a is origin:
            continue
        implied = c.pk_of_s(a["s"])
        a["role"] = "check"
        a["implied_pk"] = implied
        ratio = (a["pk"] - ORIGIN_PK) / ((a["s"] - origin["s"]) / 1000.0) if a["s"] != origin["s"] else float("inf")
        flag = "" if SCALE_FLAG[0] <= ratio <= SCALE_FLAG[1] else "  << outside QA range"
        c.qa.append(f"Check anchor PK {a['pk']:.3f} ({a['name']}, {a['offset_m']:.0f} m from RR27): "
                    f"unit-scale PK at its projection {implied:.3f} (difference {implied - a['pk']:+.3f} km); "
                    f"ratio to origin {ratio:.3f} PK-km per OSM-km{flag}.")
        c.anchors.append(a)
    used = set()
    for pk, kind, _ in ANCHORS:
        if kind != "hydraulic":
            continue
        pred = c.s_of_pk(pk)
        options = sorted((abs(sv - pred), sv, ref, nm) for sv, ref, nm in merged if ref not in used)
        if not options:
            c.qa.append(f"Check anchor PK {pk:.3f} (hydraulic structure): no OSM structure on the centerline.")
            continue
        dist, sv, ref, nm = options[0]
        within = dist <= HYDRAULIC_SEARCH_M
        if within:
            used.add(ref)
        c.qa.append(f"Check anchor PK {pk:.3f} (hydraulic structure): nearest OSM structure {ref} at unit-scale PK "
                    f"{c.pk_of_s(sv):.3f} ({dist:.0f} m{'' if within else ', beyond the 300 m tolerance'}).")
        c.anchors.append({"pk": pk, "kind": "hydraulic", "osm": ref, "name": nm, "offset_m": round(dist, 1),
                          "s": sv, "role": "check" if within else "check (not matched)",
                          "implied_pk": c.pk_of_s(sv)})
    c.qa.append(f"Calibration (protocol v1.1): PK = {ORIGIN_PK:.3f} + (s - {origin['s']:.1f} m) / 1000.")


def build_gis(c: Corridor, data: OsmData) -> None:
    """Junctions, named features and municipal places (protocol section 4)."""
    route_re = re.compile(ROUTE_REF, re.I)
    c.on_path = set(c.path)
    path_edges = {frozenset(e) for e in zip(c.path, c.path[1:])}

    def centerline_way(w: dict) -> bool:
        ids = w["nodes"]
        return is_route_way(w["tags"], route_re) or any(frozenset(e) in path_edges for e in zip(ids, ids[1:]))

    # junctions: centerline vertices shared with another drivable way
    for i in c.path:
        crossing = [wid for wid in c.way_of_vertex.get(i, []) if not centerline_way(c.ways[wid])]
        if crossing:
            nm: List[str] = []
            for wid in crossing:
                t = c.ways[wid]["tags"]
                for n in names_of(t) + [r.strip() for r in (t.get("ref") or "").split(";") if r.strip()]:
                    if n not in nm:
                        nm.append(n)
            c.junctions[i] = nm

    # named features within FEATURE_BUFFER_M of the centerline
    feats: List[Feature] = []
    for i, (lat, lon, t) in data.nodes.items():
        nm = report_name(t)
        if not nm or not any(k in t for k in FEATURE_KEYS):
            continue
        x, y = utm(lat, lon)
        if c.line.distance(Point(x, y)) <= FEATURE_BUFFER_M:
            kind = next(k for k in FEATURE_KEYS if k in t)
            feats.append(Feature(f"node/{i}", nm, names_of(t), x, y, f"{kind}={t[kind]}"))
    for w in c.ways.values():
        t = w["tags"]
        nm = report_name(t)
        if not nm or "highway" in t or len(w["coords"]) < 2:
            continue
        xy = [utm(*ll) for ll in w["coords"]]
        closed = xy[0] == xy[-1] and len(xy) >= 4 and "waterway" not in t
        if closed:
            p = Polygon(xy).representative_point()
        else:   # linear feature: its point nearest to the corridor
            p = nearest_points(LineString(xy), c.line)[0]
        if c.line.distance(p) <= FEATURE_BUFFER_M:
            kind = next((k for k in FEATURE_KEYS if k in t), "named way")
            feats.append(Feature(f"way/{w['id']}", nm, names_of(t), p.x, p.y,
                                 f"{kind}={t.get(kind, '')}".rstrip("=")))
    # attach each feature to the nearest drivable vertex within ATTACH_MAX_M
    vids = [i for i in c.way_of_vertex if i in c.vxy]
    tree = cKDTree(np.array([c.vxy[i] for i in vids]))
    for f in feats:
        d, k = tree.query((f.x, f.y))
        if d <= ATTACH_MAX_M:
            f.vertex = vids[k]
    c.features = feats
    for i, (lat, lon, t) in data.nodes.items():
        if t.get("place") in MUNICIPAL_PLACES and report_name(t):
            x, y = utm(lat, lon)
            c.places.append((report_name(t), x, y))
    c.qa.append(f"Junctions on the centerline: {len(c.junctions)} "
                f"({sum(1 for v in c.junctions.values() if v)} with a named or numbered crossing road).")
    c.qa.append(f"Named features within {FEATURE_BUFFER_M:.0f} m: {len(feats)}; indexable "
                f"(road vertex within {ATTACH_MAX_M:.0f} m): {sum(1 for f in feats if f.vertex is not None)}.")
    c.qa.append(f"Municipal places (city/town/village): {len(c.places)}.")


def hierarchy_of(c: Corridor, vertex: int) -> str:
    if vertex in c.on_path:
        return ROUTE
    for wid in c.way_of_vertex.get(vertex, []):
        t = c.ways[wid]["tags"]
        ref = (t.get("ref") or "").split(";")[0].strip()
        return ref or f"local:{t.get('highway', '')}"
    return "local"


def base_nodes(c: Corridor) -> List[dict]:
    """GIS layer: one node per indexed vertex (junction or feature attachment)."""
    gaz: Dict[int, List[Tuple[str, Optional[str]]]] = {}
    for v, names in c.junctions.items():
        gaz.setdefault(v, [])
        gaz[v] += [(n, None) for n in names]
    for f in c.features:
        if f.vertex is not None:
            gaz.setdefault(f.vertex, [])
            gaz[f.vertex] += [(n, f.fid) for n in f.names]
    path_index = {v: k for k, v in enumerate(c.path)}
    out = []
    for v in sorted(gaz):
        x, y = c.vxy[v]
        lat, lon = wgs(x, y)
        h = hierarchy_of(c, v)
        pk = c.pk_of_s(float(c.chain[path_index[v]])) if v in path_index else None
        out.append({"node_id": f"N{v}", "vertex": v, "route": h,
                    "pk_marker": f"PK{int(math.floor(pk + 0.5))}" if pk is not None else "",
                    "gazetteer": gaz[v], "x": x, "y": y, "lat": lat, "lon": lon})
    return out


# ----------------------------------------------------------------------
# Registry and simulation
# ----------------------------------------------------------------------
INTERSECTION_CAUSE = "non respect priorite feux stop"   # right-of-way, signal or stop violation


def load_registry(path: Path, qa: Optional[List[str]] = None) -> List[Tuple[str, int, int]]:
    """Registry fields used: PK (integer) and the intersection indicator.

    A record is an intersection crash when its coded cause is a right-of-way,
    signal or stop violation ("Non respect priorite, feux, stop"); in the RR27
    registry this is exactly the set flagged selectin = 1. Without a cause
    column, selectin is used.
    """
    import pandas as pd

    df = pd.read_excel(path, sheet_name="MC27")
    cause_col = "Causes codifi\u00e9es"
    out = []
    agree = 0
    for k, (_, rec) in enumerate(df.iterrows(), start=1):
        sel = int(rec["selectin"]) if "selectin" in df.columns else None
        if cause_col in df.columns:
            flag = int(normalize_toponym(str(rec[cause_col])) == INTERSECTION_CAUSE)
            agree += int(sel is not None and sel == flag)
        else:
            flag = int(sel)
        out.append((f"RR27-{k:03d}", int(rec["PK"]), flag))
    if qa is not None:
        n_int = sum(f for _, _, f in out)
        msg = f"Registry: {len(out)} records, {n_int} intersection crashes"
        if cause_col in df.columns and "selectin" in df.columns:
            msg += f" (cause-based flag agrees with selectin on {agree}/{len(out)} records)"
        qa.append(msg + ".")
    return out


_ARTICLE = re.compile(r"^(el|al|ech|er|es|et|ed|ez|en|le|la|les)[\s\-']+", re.I)


def spelling_variant(name: str, rng: random.Random) -> str:
    """One deterministic transcription variant (protocol section 5)."""
    op = rng.randrange(3)
    u = rng.random()
    base = "".join(ch for ch in unicodedata.normalize("NFKD", name) if not unicodedata.combining(ch))
    if op == 0:
        v = _ARTICLE.sub("", base)
        return v if v != base else base.replace("ou", "u").replace("ch", "sh")
    letters = [i for i, ch in enumerate(base) if ch.isalpha()][1:]
    if len(letters) < 2:
        return base
    i = letters[int(u * len(letters)) % len(letters)]
    if op == 1:
        return base[:i] + base[i + 1:]
    j = i + 1 if i + 1 < len(base) else i - 1
    s = list(base)
    s[i], s[j] = s[j], s[i]
    return "".join(s)


@dataclass
class SimRecord:
    event_id: str
    pk_recorded: int
    selectin: int
    true_s: float
    true_pk: float
    truth: Tuple[float, float]
    junction: Optional[int]
    witness: Optional[str]
    witness_fid: Optional[str]
    muni: Tuple[str, float, float]


def simulate_truth(c: Corridor, registry, rng: random.Random) -> List[SimRecord]:
    path_index = {v: k for k, v in enumerate(c.path)}
    feats = [f for f in c.features]
    ftree = cKDTree(np.array([(f.x, f.y) for f in feats])) if feats else None
    junction_pk = {v: c.pk_of_s(float(c.chain[path_index[v]])) for v in c.junctions}
    out = []
    for eid, pk, sel in registry:
        lo, hi = pk - PK_HALF_WIDTH_KM, pk + PK_HALF_WIDTH_KM
        u = rng.random()
        junction = None
        if sel == 1:
            js = sorted(v for v, p in junction_pk.items() if lo <= p < hi)
            if js:
                junction = js[int(u * len(js)) % len(js)]
        if junction is not None:
            s = float(c.chain[path_index[junction]])
            x, y = c.vxy[junction]
        else:
            s = c.s_of_pk(lo + u * (hi - lo))
            x, y = c.point_at(s)
        witness, wfid = None, None
        if junction is not None and c.junctions[junction]:
            witness = c.junctions[junction][0]
        elif ftree is not None:
            d, k = ftree.query((x, y))
            if d <= LANDMARK_RADIUS_M:
                witness, wfid = feats[k].name, feats[k].fid
        muni = min(c.places, key=lambda p: math.dist((p[1], p[2]), (x, y))) if c.places else ("", x, y)
        out.append(SimRecord(eid, pk, sel, s, c.pk_of_s(s), (x, y), junction, witness, wfid, muni))
    return out


@dataclass
class Draw:
    """Uniform draws per record, shared by all scenarios (coupled degradations)."""
    u: Dict[str, float]
    sub_pick: float
    shift_sign: int
    typo_seed: int


def draw_degradations(records: Sequence[SimRecord], rng: random.Random) -> List[Draw]:
    out = []
    for _ in records:
        u = {k: rng.random() for k in ("p_omit", "p_sub", "p_typo", "p_pk_shift", "p_pk_missing", "p_flag")}
        out.append(Draw(u, rng.random(), 1 if rng.random() < 0.5 else -1, rng.randrange(2**31)))
    return out


def gis_gap_draws(c: Corridor, rng: random.Random) -> Dict[str, float]:
    return {f.fid: rng.random() for f in sorted(c.features, key=lambda f: f.fid)}


def make_events(c: Corridor, recs: Sequence[SimRecord], draws: Sequence[Draw], p: Dict[str, float]):
    feats = c.features
    ftree = cKDTree(np.array([(f.x, f.y) for f in feats])) if feats else None
    events, causes = [], []
    for r, d in zip(recs, draws):
        cause = []
        if r.witness is None:
            cause.append("no landmark within 300 m (structural)")
        landmark = r.witness
        if landmark is not None and d.u["p_omit"] < p["p_omit"]:
            landmark = None
            cause.append("landmark omitted")
        if landmark is not None and d.u["p_sub"] < p["p_sub"] and ftree is not None:
            idx = ftree.query_ball_point(r.truth, SUBSTITUTE_RADIUS_M)
            pool = sorted({feats[k].name for k in idx
                           if normalize_toponym(feats[k].name) != normalize_toponym(landmark)})
            if pool:
                landmark = pool[int(d.sub_pick * len(pool)) % len(pool)]
                cause.append("wrong landmark")
        if landmark is not None and d.u["p_typo"] < p["p_typo"]:
            landmark = spelling_variant(landmark, random.Random(d.typo_seed))
            cause.append("spelling variant")
        pk = r.pk_recorded
        pk_marker: Optional[str] = f"PK{pk}"
        if d.u["p_pk_missing"] < p["p_pk_missing"]:
            pk_marker = None
            cause.append("PK missing (fallback)")
        elif d.u["p_pk_shift"] < p["p_pk_shift"]:
            pk_marker = f"PK{pk + d.shift_sign}"
            cause.append(f"PK recorded {d.shift_sign:+d} km")
        flag = bool(r.selectin)
        if d.u["p_flag"] < p["p_flag"]:
            flag = not flag
            cause.append("intersection flag flipped")
        events.append(CrashEvent(
            event_id=r.event_id, route=ROUTE, pk_marker=pk_marker,
            narrative_landmarks=[landmark] if landmark else [],
            municipality_centroid=Point2D(r.muni[1], r.muni[2]),
            intersection_descriptors=flag,
        ))
        causes.append(cause)
    return events, causes


class CachedGis(GisDatabase):
    """GisDatabase with memoised spatial queries (same answers, faster).

    The node list is rebuilt for every replicate (gazetteer gaps differ), but the
    geometry does not change, so candidate index lists are shared.
    """

    _cache: Dict[tuple, List[int]] = {}

    def __init__(self, nodes: List[GisNode], posts: List[PKPost]):
        super().__init__(nodes=nodes, pk_posts=posts)
        self._order = {n.node_name: k for k, n in enumerate(self._all_nodes)}

    def query_within_radius(self, center, radius):
        key = ("r", round(center.x, 3), round(center.y, 3), radius)
        if key not in CachedGis._cache:
            CachedGis._cache[key] = [self._order[n.node_name] for n in super().query_within_radius(center, radius)]
        return [self._all_nodes[k] for k in CachedGis._cache[key]]

    def query_in_sector(self, route, sector_ref, radius):
        key = ("s", route, None if sector_ref is None else (round(sector_ref.x, 3), round(sector_ref.y, 3)), radius)
        if key not in CachedGis._cache:
            CachedGis._cache[key] = [self._order[n.node_name] for n in super().query_in_sector(route, sector_ref, radius)]
        return [self._all_nodes[k] for k in CachedGis._cache[key]]


def make_gis(c: Corridor, nodes: List[dict], gap: Dict[str, float], p_gap: float) -> Tuple[CachedGis, List[PKPost]]:
    gis_nodes = []
    for n in nodes:
        names = []
        for nm, fid in n["gazetteer"]:
            if fid is not None and gap.get(fid, 1.0) < p_gap:
                continue
            if nm not in names:
                names.append(nm)
        gis_nodes.append(GisNode(node_name=n["node_id"], pk_marker=n["pk_marker"], gazetteer=names,
                                 highway_hierarchy=n["route"], coords=Point2D(n["x"], n["y"]),
                                 wgs84=WGS84Point(n["lat"], n["lon"])))
    return CachedGis(gis_nodes, c.posts), c.posts


def pk_posts(c: Corridor, registry) -> List[PKPost]:
    lo = min(pk for _, pk, _ in registry) - 1
    hi = max(pk for _, pk, _ in registry) + 1
    posts = []
    for n in range(lo, hi + 1):
        s = c.s_of_pk(float(n))
        if not 0.0 <= s <= c.line.length:
            c.qa.append(f"PK {n}: outside the extracted centerline, post not created.")
            continue
        x, y = c.point_at(s)
        sector = min(c.places, key=lambda p: math.dist((p[1], p[2]), (x, y)))[0] if c.places else None
        posts.append(PKPost(ROUTE, f"PK{n}", Point2D(x, y), sector))
    return posts


# ----------------------------------------------------------------------
# Metrics
# ----------------------------------------------------------------------
def run_config(events, gis, truth, weights) -> Tuple[dict, list]:
    w1, w2, w3 = weights
    policy = "reject" if (w1 == 0.0 and w3 == 0.0) else "transfer"
    engine = DSDAEngine(DSDAParameters(w1=w1, w2=w2, w3=w3, fallback_policy=policy))
    results = engine.process_corridor(events, gis)
    rep = compute_geocoding_accuracy(results, truth)   # post hoc only
    cond = [r["e_geo"] for r in rep.per_record if r["e_geo"] is not None and r["status"] == GeocodingStatus.AUTO_VALIDATED.value]
    m = {"n": rep.n_records, "accepted": rep.n_accepted,
         "gross": sum(1 for e in cond if e > GROSS_ERROR_M)}
    for pop, s in (("cond", rep.conditional), ("incl", rep.inclusive)):
        for k in ("n", "mean", "median", "p90", "p95", "rmse", "max"):
            m[f"{pop}_{k}"] = getattr(s, k) if s is not None else None
    return m, results


def summarise(values: Sequence[Optional[float]]) -> Optional[Tuple[float, float, float, int]]:
    xs = [v for v in values if v is not None]
    if not xs:
        return None
    a = np.array(xs, dtype=float)
    return float(a.mean()), float(np.percentile(a, 2.5)), float(np.percentile(a, 97.5)), len(xs)


def fmt(s, digits=1, total=None) -> str:
    if s is None:
        return "n/a"
    mean, lo, hi, k = s
    txt = f"{mean:.{digits}f} [{lo:.{digits}f}, {hi:.{digits}f}]"
    if total is not None and k < total:
        txt += f" (defined in {k}/{total})"
    return txt


def write_table(path: Path, header: List[str], rows: List[List[str]], note: str = "") -> None:
    with open(path.with_suffix(".csv"), "w", newline="", encoding="utf-8") as fh:
        w = csv.writer(fh)
        w.writerow(header)
        w.writerows(rows)
    with open(path.with_suffix(".md"), "w", encoding="utf-8") as fh:
        fh.write("| " + " | ".join(header) + " |\n|" + "---|" * len(header) + "\n")
        for r in rows:
            fh.write("| " + " | ".join(r) + " |\n")
        if note:
            fh.write("\n" + note + "\n")


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def git_commit() -> str:
    try:
        return subprocess.check_output(["git", "-C", str(ROOT), "rev-parse", "HEAD"], text=True).strip()
    except Exception:  # pragma: no cover
        return "unknown"


# ----------------------------------------------------------------------
# Main pass
# ----------------------------------------------------------------------
def run(osm_path: Path, registry_path: Path, out: Path, replicates: int = REPLICATES,
        bbox: Optional[Tuple[float, float, float, float]] = None, route_regex: str = ROUTE_REF) -> dict:
    out.mkdir(parents=True, exist_ok=True)
    data = load_osm(osm_path)
    if bbox:
        data = crop(data, bbox)
    c = build_corridor(data, route_regex)
    calibrate(c, data)
    build_gis(c, data)
    registry = load_registry(registry_path, c.qa)
    need = (min(pk for _, pk, _ in registry) - PK_HALF_WIDTH_KM, max(pk for _, pk, _ in registry) + PK_HALF_WIDTH_KM)
    s_need = (c.s_of_pk(need[0]), c.s_of_pk(need[1]))
    c.qa.append(f"Registry PK range {need[0]:.1f} to {need[1]:.1f} maps to chainage {s_need[0]:.0f} to "
                f"{s_need[1]:.0f} m on a {c.line.length:.0f} m centerline.")
    if s_need[0] < 0.0 or s_need[1] > c.line.length:
        raise SystemExit("The extracted centerline does not cover the registry PK range: enlarge the OSM extract.")
    c.posts = pk_posts(c, registry)
    nodes = base_nodes(c)
    c.qa.append(f"GIS layer: {len(nodes)} candidate nodes "
                f"({sum(1 for n in nodes if n['route'] == ROUTE)} on {ROUTE}).")
    CachedGis._cache = {}
    names = [n for n, _ in CONFIGS]
    rows = []           # replicates.csv
    agg: Dict[Tuple[str, str], List[dict]] = {}
    muni_base: Dict[str, List[float]] = {s: [] for s in SCENARIOS}
    pooled_cond: List[float] = []
    pooled_incl: List[float] = []
    c2_rows: List[List[str]] = []
    structural = {"no_landmark": [], "beyond_gate_radius": []}
    for r in range(replicates):
        rng_truth = random.Random(BASE_SEED + r)
        recs = simulate_truth(c, registry, rng_truth)
        rng_deg = random.Random(BASE_SEED + 1_000_000 + r)
        draws = draw_degradations(recs, rng_deg)
        gap = gis_gap_draws(c, random.Random(BASE_SEED + 2_000_000 + r))
        truth = {x.event_id: Point2D(*x.truth) for x in recs}
        post_xy = {p.pk_marker: p.coords for p in c.posts}
        structural["no_landmark"].append(sum(1 for x in recs if x.witness is None))
        structural["beyond_gate_radius"].append(sum(
            1 for x in recs if f"PK{x.pk_recorded}" in post_xy
            and Point2D(*x.truth).distance_to(post_xy[f"PK{x.pk_recorded}"]) > 151.6))
        for scen, p in SCENARIOS.items():
            events, causes = make_events(c, recs, draws, p)
            gis, _ = make_gis(c, nodes, gap, p["p_gis_gap"])
            muni_base[scen].append(statistics.fmean(
                math.dist(x.truth, (x.muni[1], x.muni[2])) for x in recs))
            for name, wts in CONFIGS:
                m, results = run_config(events, gis, truth, wts)
                agg.setdefault((scen, name), []).append(m)
                rows.append({"scenario": scen, "replicate": r, "configuration": name, **m})
                if scen == REFERENCE_SCENARIO and name == "Full DSDA":
                    for res in results:
                        if res.status == GeocodingStatus.AUTO_VALIDATED:
                            pooled_cond.append(res.selected_node.coords.distance_to(truth[res.event_id]))
                        if res.selected_node is not None:
                            pooled_incl.append(res.selected_node.coords.distance_to(truth[res.event_id]))
                    if r == 0:
                        c2_rows = _table_c2(c, recs, events, causes, results, truth, post_xy)
                        _write_replicate(out / f"{scen}_r0", c, nodes, gap, p, events, recs)
    # ---------------- outputs ----------------
    with open(out / "replicates.csv", "w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=list(rows[0]))
        w.writeheader()
        w.writerows(rows)
    n = len(registry)
    _table5(out, agg, n, replicates)
    _table_c1(out, agg, pooled_cond, pooled_incl, n, replicates)
    write_table(out / "tableC2_testbed",
                ["Record", "PK in simulated report", "Simulated true PK", "Mode", "Cs (best)", "Best-candidate E_geo (m)",
                 "Distance truth to registry PK post (m)", "Injected degradations / structural causes"], c2_rows,
                f"Scenario {REFERENCE_SCENARIO}, replicate 0 (seed {BASE_SEED}); Full DSDA; records not "
                f"accepted by the gate Cs >= 0.85. Causes are known by construction.")
    _table_d2(out, agg, muni_base, n, replicates)
    # run_ablation.py on the replicate-0 files (one pass, same engine)
    rep0 = out / f"{REFERENCE_SCENARIO}_r0"
    abl = run_ablation.run(rep0, rep0 / "ablation_out")
    inproc = {row["configuration"]: row["accepted"] for row in rows
              if row["scenario"] == REFERENCE_SCENARIO and row["replicate"] == 0}
    files = {row["Configuration"]: int(row["Automated throughput"].split("/")[0]) for row in abl}
    same = all(files[k] == inproc[k] for k in inproc)
    c.qa.append("scripts/run_ablation.py on the exported replicate-0 files "
                + ("reproduces" if same else "DOES NOT reproduce")
                + f" the in-process acceptance counts of scenario {REFERENCE_SCENARIO} "
                + "(" + ", ".join(f"{k.split(' (')[0]}: {files[k]}" for k in files) + ").")
    manifest = {
        "protocol_version": PROTOCOL_VERSION,
        "run_utc": _dt.datetime.now(_dt.timezone.utc).isoformat(timespec="seconds"),
        "code_commit": git_commit(),
        "script_sha256": sha256(Path(__file__)),
        "protocol_sha256": sha256(ROOT / "testbed" / "PROTOCOL.md") if (ROOT / "testbed" / "PROTOCOL.md").exists() else None,
        "osm_file": osm_path.name, "osm_sha256": sha256(osm_path), "osm_timestamp": data.timestamp,
        "registry_sha256": sha256(registry_path), "records": n,
        "crs": CRS, "route_regex": route_regex, "bbox": bbox,
        "anchors": [{k: (round(v, 2) if isinstance(v, float) else v) for k, v in a.items()} for a in c.anchors],
        "replicates": replicates, "base_seed": BASE_SEED, "scenarios": SCENARIOS,
        "reference_scenario": REFERENCE_SCENARIO,
        "structural": {k: summarise(v) for k, v in structural.items()},
        "python": platform.python_version(),
    }
    (out / "manifest.json").write_text(json.dumps(manifest, indent=2, ensure_ascii=False), encoding="utf-8")
    (out / "qa_report.md").write_text(
        "# Testbed QA report\n\n"
        + "\n".join(f"- {q}" for q in c.qa)
        + "\n\n## Calibration anchors (protocol v1.1)\n\n| PK | Kind | Role | OSM element | Name | Offset (m) | Chainage (m) | Unit-scale PK |\n|---|---|---|---|---|---|---|---|\n"
        + "\n".join(f"| {a['pk']:.3f} | {a['kind']} | {a.get('role', '')} | {a['osm']} | {a['name'] or ''} | {a['offset_m']} "
                    f"| {a['s']:.1f} | {a.get('implied_pk', a['pk']):.3f} |" for a in c.anchors)
        + f"\n\n## Structural properties of the simulated corpus (mean [2.5, 97.5] over {replicates} replicates)\n\n"
        + f"- Records without any named feature within {LANDMARK_RADIUS_M:.0f} m of the true position: "
        + fmt(manifest["structural"]["no_landmark"]) + f" of {n}\n"
        + "- Records whose true position lies more than 151.6 m from their recorded PK post "
        + "(beyond the radius where Cs >= 0.85 is reachable in LRS-anchored mode): "
        + fmt(manifest["structural"]["beyond_gate_radius"]) + f" of {n}\n",
        encoding="utf-8")
    return manifest


def _write_replicate(d: Path, c: Corridor, nodes, gap, p, events, recs) -> None:
    d.mkdir(parents=True, exist_ok=True)
    with open(d / "nodes.csv", "w", newline="", encoding="utf-8") as fh:
        w = csv.writer(fh)
        w.writerow(["node_id", "route", "pk_marker", "gazetteer", "x", "y", "lat", "lon"])
        for n in nodes:
            names = []
            for nm, fid in n["gazetteer"]:
                if (fid is None or gap.get(fid, 1.0) >= p["p_gis_gap"]) and nm not in names:
                    names.append(nm.replace("|", "/"))
            w.writerow([n["node_id"], n["route"], n["pk_marker"], "|".join(names),
                        f"{n['x']:.3f}", f"{n['y']:.3f}", f"{n['lat']:.7f}", f"{n['lon']:.7f}"])
    with open(d / "pk_posts.csv", "w", newline="", encoding="utf-8") as fh:
        w = csv.writer(fh)
        w.writerow(["route", "pk_marker", "x", "y", "sector"])
        for pp in c.posts:
            w.writerow([pp.route, pp.pk_marker, f"{pp.coords.x:.3f}", f"{pp.coords.y:.3f}", pp.sector or ""])
    with open(d / "events.csv", "w", newline="", encoding="utf-8") as fh:
        w = csv.writer(fh)
        w.writerow(["event_id", "route", "pk_marker", "landmarks", "intersection", "muni_x", "muni_y"])
        for e in events:
            w.writerow([e.event_id, e.route, e.pk_marker or "", "|".join(e.narrative_landmarks),
                        int(e.intersection_descriptors), f"{e.municipality_centroid.x:.3f}",
                        f"{e.municipality_centroid.y:.3f}"])
    with open(d / "ground_truth.csv", "w", newline="", encoding="utf-8") as fh:
        w = csv.writer(fh)
        w.writerow(["event_id", "x", "y"])
        for x in recs:
            w.writerow([x.event_id, f"{x.truth[0]:.3f}", f"{x.truth[1]:.3f}"])


def _table_c2(c, recs, events, causes, results, truth, post_xy) -> List[List[str]]:
    out = []
    for x, e, cause, res in zip(recs, events, causes, results):
        if res.status == GeocodingStatus.AUTO_VALIDATED:
            continue
        cause = list(cause)
        post = post_xy.get(f"PK{x.pk_recorded}")
        dpost = Point2D(*x.truth).distance_to(post) if post is not None else float("nan")
        if e.pk_marker is not None and dpost > 151.6:
            cause.append("true position > 151.6 m from PK post")
        if x.witness_fid and not any(f.fid == x.witness_fid and f.vertex is not None for f in c.features):
            cause.append("landmark not indexable (> 150 m from a road)")
        egeo = res.selected_node.coords.distance_to(truth[x.event_id]) if res.selected_node else None
        out.append([x.event_id, e.pk_marker or "(missing)", f"{x.true_pk:.3f}", res.mode.value,
                    f"{res.best_score:.3f}", f"{egeo:.1f}" if egeo is not None else "no candidate",
                    f"{dpost:.0f}", "; ".join(cause) or "none injected"])
    return out


def _metric_rows(agg, key, n, R, scen_list):
    def col(scen, metric, digits=1):
        return fmt(summarise([m[metric] for m in agg[(scen, key)]]), digits, R)

    rows = [
        ["Panel A: accepted records (Cs >= 0.85)"] + [""] * len(scen_list),
        ["Automated throughput (records, of %d)" % n] + [col(s, "accepted") for s in scen_list],
        ["Conditional mean E_geo (m)"] + [col(s, "cond_mean") for s in scen_list],
        ["Conditional median E_geo (m)"] + [col(s, "cond_median") for s in scen_list],
        ["Conditional P90 (m)"] + [col(s, "cond_p90") for s in scen_list],
        ["Conditional P95 (m)"] + [col(s, "cond_p95") for s in scen_list],
        ["Accepted with E_geo > %.0f m (records)" % GROSS_ERROR_M] + [col(s, "gross") for s in scen_list],
        ["Panel B: all records with a best candidate"] + [""] * len(scen_list),
        ["Records with a best candidate"] + [col(s, "incl_n") for s in scen_list],
        ["Inclusive mean E_geo (m)"] + [col(s, "incl_mean") for s in scen_list],
        ["Inclusive P90 (m)"] + [col(s, "incl_p90") for s in scen_list],
        ["Inclusive P95 (m)"] + [col(s, "incl_p95") for s in scen_list],
        ["Inclusive RMSE (m)"] + [col(s, "incl_rmse") for s in scen_list],
        ["Maximum E_geo (m)"] + [col(s, "incl_max") for s in scen_list],
    ]
    return rows


def _table5(out, agg, n, R):
    scen = list(SCENARIOS)
    write_table(out / "table5_testbed", ["Metric"] + [f"{s}{' (reference)' if s == REFERENCE_SCENARIO else ''}" for s in scen],
                _metric_rows(agg, "Full DSDA", n, R, scen),
                f"Full DSDA, published parameters. Values: mean over {R} replicates "
                f"[2.5th, 97.5th percentile across replicates]. Simulated positions on the real OSM graph; "
                f"not a field validation.")


def _table_c1(out, agg, pooled_cond, pooled_incl, n, R):
    bins = [0, 25, 50, 100, 150, 300, float("inf")]
    labels = ["0-25 m", "25-50 m", "50-100 m", "100-150 m", "150-300 m", "> 300 m"]
    rows = _metric_rows(agg, "Full DSDA", n, R, [REFERENCE_SCENARIO])
    rows.append(["Pooled distribution over all replicates", ""])
    for lo, hi, lab in zip(bins, bins[1:], labels):
        sc = sum(1 for e in pooled_cond if lo <= e < hi) / max(1, len(pooled_cond))
        si = sum(1 for e in pooled_incl if lo <= e < hi) / max(1, len(pooled_incl))
        rows.append([f"Share of E_geo in {lab} (accepted / inclusive)", f"{sc:.1%} / {si:.1%}"])
    write_table(out / "tableC1_testbed", ["Metric", REFERENCE_SCENARIO], rows,
                f"Reference scenario {REFERENCE_SCENARIO}, Full DSDA. Pooled shares over "
                f"{len(pooled_cond)} accepted and {len(pooled_incl)} best-candidate decisions.")


def _table_d2(out, agg, muni_base, n, R):
    for scen in SCENARIOS:
        rows = [["Municipality centroid (address-level baseline)", "--", "--", "--",
                 fmt(summarise(muni_base[scen]), 1, R), "--"]]
        for name, (w1, w2, w3) in CONFIGS:
            ms = agg[(scen, name)]
            rows.append([name, f"({w1:.3f}, {w2:.3f}, {w3:.3f})",
                         fmt(summarise([m["accepted"] for m in ms]), 1, R),
                         fmt(summarise([m["cond_mean"] for m in ms]), 1, R),
                         fmt(summarise([m["incl_mean"] for m in ms]), 1, R),
                         fmt(summarise([m["cond_p90"] for m in ms]), 1, R)])
        stem = "tableD2_testbed" if scen == REFERENCE_SCENARIO else f"tableD2_testbed_{scen}"
        write_table(out / stem, ["Configuration", "Weights (w1, w2, w3)", f"Automated throughput (of {n})",
                                 "Conditional mean E_geo (m)", "Inclusive mean E_geo (m)", "Conditional P90 (m)"],
                    rows, f"Scenario {scen}. Mean over {R} replicates [2.5th, 97.5th percentile].")


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--osm", type=Path, required=True)
    ap.add_argument("--registry", type=Path, required=True)
    ap.add_argument("--out", type=Path, default=Path("testbed_out"))
    ap.add_argument("--replicates", type=int, default=REPLICATES)
    ap.add_argument("--bbox", type=float, nargs=4, metavar=("S", "W", "N", "E"))
    ap.add_argument("--route-regex", default=ROUTE_REF)
    a = ap.parse_args()
    m = run(a.osm, a.registry, a.out, a.replicates, tuple(a.bbox) if a.bbox else None, a.route_regex)
    print(json.dumps({k: m[k] for k in ("osm_timestamp", "anchors", "structural")}, indent=1, ensure_ascii=False))


if __name__ == "__main__":
    main()
