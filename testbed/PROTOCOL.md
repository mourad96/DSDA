# DSDA controlled geospatial testbed on the OpenStreetMap graph (RR27)

The study restricted to the 82 RR27 crashes, with the frozen HRRS screening, follows
`testbed/PROTOCOL_v1.3.md`; this document covers versions 1.0 to 1.2.

Protocol version 1.2. Version 1.0 was frozen on 23 November 2026, before any
real OpenStreetMap extract was loaded; version 1.1 (section 0) amends only the
PK calibration, on the same day, after inspection of the extract and before any
DSDA run on it; version 1.2 (section 0b) amends only the intersection
indicator, on 26 November 2026, after a factual error was found in the
registry reading. Results of version 1.1 are kept as a sensitivity analysis. Implementation: `scripts/osm_testbed.py` (constants in its
PROTOCOL block mirror this document). Any later change requires a new version
number, and the change and its reason are reported with the results.

## 0. Amendment 1.1 (PK calibration)

Quality checks on the extract (OSM base timestamp 2026-11-23T20:02:34Z) showed
that the anchors of section 3 cannot all be located on OSM:

- Maamoura PK 31+240: the village place node lies 1.47 km from the RR27
  centerline; its projection falls 1.6 km from Beni Khiar, which would imply
  2.66 PK-km per km of road (QA range 0.80 to 1.25).
- El Mazraa PK 36+300: no OSM element of that name exists.
- Hydraulic structures PK 33+080 and 33+560: a single structure (stream bridge)
  lies on the centerline in that sector.

Applying section 3 unchanged would compress each PK kilometre into about 376 m
of road, placing simulated crashes artificially close to their posts and
inflating acceptance. Version 1.1 therefore replaces items 3 and 4 of section 3:
PK = 27.000 + (s - s_BK) / 1000, where s_BK is the projection of the Beni Khiar
place node (7 m from the centerline), i.e. one PK kilometre per kilometre of
road, which is the definition of a kilometric point. The other four anchors are
kept as checks: their unit-scale PK and discrepancy are reported in
`qa_report.md`. Beyond this calibration rule nothing else changes. The choice
was made by the authors without any DSDA output on the extract.

## 0b. Amendment 1.2 (intersection indicator)

Version 1.1 treated every record of the coded cause category "Non respect
priorite, feux, stop" (selectin = 1, 31 of 83 records) as an intersection
crash. The detailed cause field of the registry shows that this category
groups four manoeuvres: failure to keep right (16 records), illegal overtaking
(6), improper change of direction (5) and right-of-way violation (4). Failure
to keep right and overtaking crashes are not junction crashes. Version 1.2
therefore reads the intersection indicator from the detailed cause: a record is
an intersection crash when its detailed cause is "Non respect priorite" or
"Changement de direction" (9 of 83 records). This changes only which records
are placed at junctions and carry the intersection flag; every other rule,
parameter, seed and scenario is unchanged. The amendment follows from the
registry content, not from the v1.1 results; both result sets are reported.

## 1. Purpose and status

The testbed measures how DSDA, as published (Algorithm 1, weights 0.500 /
0.375 / 0.125, sigma = 150 m, R_max = 500 m, gate Cs >= 0.85), behaves on the
real RR27 road graph when crash positions are known by construction. It is a
simulation study. It is not a field validation: no crash position in it was
measured. Results are reported as produced, for every scenario, whatever they
are; no parameter of this protocol or of DSDA is adjusted after the results are
seen.

| Element | Real | Simulated |
|---|---|---|
| Road graph, toponyms, bridges, waterways | OpenStreetMap extract (timestamp recorded) | |
| PK and intersection indicator of the 83 RR27 records | Registry (PK integer, coded cause) | |
| PK calibration anchors | Supplied by the authors | |
| True crash position | | Drawn inside the recorded PK interval |
| Landmarks cited by the report, and their errors | | Drawn from OSM features and scenario rates |

## 2. Data

- OpenStreetMap: query `testbed/overpass_query.overpassql` (bounding box
  36.42 N to 36.63 N, 10.74 E to 10.92 E; drivable highways, waterways, named
  elements, places, road route relations; `out geom`). A Geofabrik Tunisia
  `.osm.pbf` cropped to the same box is accepted. The file SHA-256 and the OSM
  base timestamp are written to `manifest.json`.
- Registry: sheet MC27 of the RR27 workbook. Fields used: `PK` (integer km)
  and the detailed cause. Version 1.2: a record is an intersection crash when
  its detailed cause is "Non respect priorite" or "Changement de direction"
  (9 of 83; section 0b). Version 1.1 used the coded category "Non respect
  priorite, feux, stop" (selectin = 1, 31 of 83). No other registry field
  enters the testbed.
- Projection: WGS 84 / UTM zone 32N (EPSG:32632).

## 3. Route and PK calibration

1. RR27 ways: OSM highways whose `ref` matches `^(RR|MC|C|RL|R)\s*-?\s*27$`,
   plus members of road route relations with that ref. If none matches, the run
   stops (a manual list of way identifiers would be a protocol change).
2. Centerline: shortest path on the drivable graph between the two most distant
   RR27 vertices, with non-RR27 edges weighted x10 (gaps in the tagging are
   bridged by the shortest connection). Chainage s in metres along it.
3. Anchors: Beni Khiar PK 27+000, Maamoura PK 31+240, El Mazraa PK 36+300 (OSM
   `place` nodes whose normalised name contains the key; the one nearest to the
   centerline; projected on it); hydraulic structures PK 33+080 and PK 33+560
   (RR27 bridges and waterway crossings of the centerline; for each, the
   structure nearest to the chainage predicted from the three places, within
   300 m, each structure used once). An anchor that cannot be found is dropped
   and reported.
4. PK(s): piecewise-linear interpolation between anchors; outside them, linear
   extrapolation with the least-squares slope over all anchors (the registry
   reaches PK 43, so PK 36+300 to 44 is extrapolated). Ratios outside
   0.80 to 1.25 PK-km per OSM-km are flagged. A non-monotone calibration stops
   the run.
5. Nominal posts k_PK: integer PKs 26 to 44 placed at s(PK).

Items 3 and 4 above are the version 1.0 rule, replaced by section 0 in version 1.1.

## 4. GIS layer seen by DSDA

- Junction nodes: centerline vertices shared with another drivable way;
  gazetteer = names and refs of the crossing ways.
- Feature nodes: named OSM elements (points; area representative points;
  for linear features, the point nearest to RR27) within 700 m of the
  centerline, attached to the nearest drivable vertex if it lies within 150 m
  (otherwise the feature exists on the ground but is not indexed).
- Each node carries its route: RR27 if on the centerline, otherwise the way ref
  or highway class (topology score 0).
- Municipality reference: nearest OSM `place` = city, town or village.

## 5. Simulated records

For each of the 83 registry records, in each replicate:

- True position: PK uniform in [n - 0.5, n + 0.5) (integer PK read as the
  nearest kilometre), mapped to the centerline. Intersection crashes are placed
  at a junction drawn uniformly among those in that interval (if none, uniform
  position).
- Landmark cited by the report: for an intersection crash, the crossing road
  name; otherwise the nearest named feature within 300 m of the true position
  (French name if present). None if there is no such feature.
- Degradations, independent per record, with uniforms shared across scenarios
  so that scenarios are nested:

| Rate | S0 (ideal) | S1 (reference) | S2 (degraded) |
|---|---|---|---|
| Landmark omitted | 0 | 0.15 | 0.30 |
| Wrong landmark (other feature within 1.5 km) | 0 | 0.05 | 0.10 |
| Spelling variant (article or accent dropped, one letter deleted or transposed) | 0 | 0.25 | 0.50 |
| PK recorded one km off | 0 | 0.05 | 0.10 |
| PK missing (fallback mode) | 0 | 0.05 | 0.10 |
| Intersection indicator flipped | 0 | 0.05 | 0.10 |
| OSM feature missing from the GIS gazetteer | 0 | 0.10 | 0.20 |

No empirical error rates exist for these reports: the rates are assumptions
that bracket plausible conditions, declared before any run. S1 is the reference
scenario for Tables C.1, C.2 and D.2; Table 5 reports all three.

## 6. DSDA runs and evaluation

- Engine: `dsda.engine` unchanged (stateless, tie-breaking Cs, then distance d
  to k_PK, then Node_ID; d = 0 for every candidate in fallback mode).
- Configurations: Full DSDA and the four ablations of `scripts/run_ablation.py`
  (PK-only uses the reject policy for records without a resolvable PK).
  Baseline: municipality centroid (address-level geocoding).
- Replicates: 1,000 per scenario; seeds 2026 + r (positions),
  2026 + 1,000,000 + r (degradations), 2026 + 2,000,000 + r (gazetteer gaps).
- Metrics (post hoc only): throughput; conditional mean, median, P90, P95 of
  E_geo on accepted records; accepted records with E_geo > 150 m; inclusive
  mean, P90, P95, RMSE and maximum over best candidates. Each reported as the
  mean over replicates with the 2.5th and 97.5th percentiles across replicates.
- Table C.2: records not accepted in S1, replicate 0, with the degradations and
  structural causes known by construction.
- The files of S1 replicate 0 are exported and `scripts/run_ablation.py` is run
  on them; the QA report states whether it reproduces the in-process counts.

## 7. Property of the algorithm stated before any run

In LRS-anchored mode with S_top = S_topo = 1, Cs = 0.5 + 0.375 S_prox + 0.125
reaches 0.85 only if S_prox >= 0.6, that is d <= 150 x sqrt(2 ln(1/0.6)) =
151.6 m from k_PK (the intersection pass gives the same bound). With integer
PKs, a true position is uniform over +/- 500 m around its post, so about 30%
of records lie within that radius. Acceptance in LRS mode is therefore expected
to stay well below the 76/83 previously reported, independently of the
landmark quality. In fallback mode (w2 = 0) a perfect toponym match gives
Cs = 1 at any distance.

## 8. Limitations

Simulated positions and reports; OSM completeness and naming as of the
extraction date; PK calibration on a single origin with unit scale (v1.1); municipality approximated
by the nearest place; uniform position within the PK interval; degradation
rates assumed. The testbed says nothing about real positional accuracy on
RR27 or RN15.
