"""Synthetic OSM extract and registry for testing scripts/osm_testbed.py.

INVENTED geometry and names (placed inland, around 37.0 N 8.1 E): this is a
software test fixture, not a representation of the RR27 corridor. Only the
three anchor place names are borrowed so that the calibration code path runs.
"""

from __future__ import annotations

import json
import math
import random
from pathlib import Path

LAT0, LON0 = 37.0, 8.0
M_PER_DEG_LAT = 111_000.0
M_PER_DEG_LON = 111_000.0 * math.cos(math.radians(LAT0))


def ll(x_m: float, y_m: float):
    return LAT0 + y_m / M_PER_DEG_LAT, LON0 + x_m / M_PER_DEG_LON


def build(path: Path) -> Path:
    rng = random.Random(7)
    elements, nid = [], [1000]

    def node(x, y, tags=None, keep=False):
        nid[0] += 1
        lat, lon = ll(x, y)
        el = {"type": "node", "id": nid[0], "lat": lat, "lon": lon}
        if tags:
            el["tags"] = tags
        if tags or keep:
            elements.append(el)
        return nid[0], lat, lon

    def way(wid, pts, tags):
        ids, geom = [], []
        for p in pts:
            ids.append(p[0])
            geom.append({"lat": p[1], "lon": p[2]})
        elements.append({"type": "way", "id": wid, "nodes": ids, "geometry": geom, "tags": tags})

    # main road: 22 km, gentle curve, vertex every 100 m
    main = []
    for k in range(221):
        x = k * 100.0
        main.append(node(x, 150.0 * math.sin(x / 3000.0)))
    way(1, main[:120], {"highway": "secondary", "ref": "C27"})
    way(2, main[119:], {"highway": "secondary", "ref": "C27", "bridge": "no"})
    # crossing roads every 800 m, some named, sharing the main-road vertex
    wid = 100
    for j, k in enumerate(range(5, 221, 8)):
        base = main[k]
        x0 = k * 100.0
        y0 = 150.0 * math.sin(x0 / 3000.0)
        pts = [base] + [node(x0 + 5.0 * i, y0 + 100.0 * i) for i in range(1, 8)]
        tags = {"highway": "tertiary" if j % 3 == 0 else "residential"}
        if j % 2 == 0:
            tags["name"] = f"Rue Test {j:02d}"
        wid += 1
        way(wid, pts, tags)
    # parallel road 350 m north, 5 to 15 km
    par = [node(x, 350.0 + 150.0 * math.sin(x / 3000.0)) for x in range(5000, 15001, 100)]
    way(50, par, {"highway": "unclassified", "ref": "P1"})
    # anchors: places (offset from the road), two waterways crossing the road
    node(2000.0, 250.0, {"place": "town", "name": "Beni Khiar"})
    node(6240.0, -300.0, {"place": "village", "name": "El Maamoura"})
    node(11300.0, 200.0, {"place": "village", "name": "El Mazraa"})
    node(18500.0, 400.0, {"place": "town", "name": "Bourg Test"})
    for w, xc, nm in ((60, 8080.0, "Oued Alpha"), (61, 8560.0, None)):
        pts = [node(xc + 20.0 * i, 200.0 * i) for i in range(-4, 5)]
        tags = {"waterway": "stream"}
        if nm:
            tags["name"] = nm
        way(w, pts, tags)
    # named point features within 600 m of the road
    kinds = ["amenity=school", "amenity=cafe", "amenity=fuel", "shop=bakery", "amenity=mosque", "tourism=hotel"]
    words = ["Alpha", "Bravo", "Charlie", "Delta", "Echo", "Foxtrot", "Golf", "Hotel", "India", "Juliett",
             "Kilo", "Lima", "Mike", "November", "Oscar", "Papa", "Quebec", "Romeo", "Sierra", "Tango"]
    for k in range(60):
        x = rng.uniform(500.0, 21500.0)
        y = 150.0 * math.sin(x / 3000.0) + rng.uniform(-600.0, 600.0)
        key, val = rng.choice(kinds).split("=")
        node(x, y, {key: val, "name": f"{val.capitalize()} {rng.choice(words)} {k:02d}"})
    doc = {"version": 0.6, "osm3s": {"timestamp_osm_base": "2000-01-01T00:00:00Z (synthetic fixture)"},
           "elements": elements}
    path.write_text(json.dumps(doc), encoding="utf-8")
    return path


def build_registry(path: Path) -> Path:
    import pandas as pd

    pks = [27, 27, 31, 32, 33, 33, 34, 34, 35, 35, 36, 36, 37, 37, 38, 39, 40, 41, 42, 43]
    sel = [1, 0, 0, 1, 0, 1, 0, 1, 1, 0, 0, 1, 0, 1, 0, 0, 1, 0, 1, 0]
    with pd.ExcelWriter(path) as xw:
        pd.DataFrame({"PK": pks, "selectin": sel}).to_excel(xw, sheet_name="MC27", index=False)
    return path
