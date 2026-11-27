# DSDA: Deterministic Spatial Disambiguation Algorithm

Reference Python implementation of the **Deterministic Spatial Disambiguation Algorithm (DSDA)** (Algorithm 1, Appendix A of the manuscript), which resolves linear-referencing crash descriptions (route, PK marker, landmarks) into georeferenced centerline nodes.

---

## 1. Formal specification

The Contextual Compatibility Score of a candidate node $k$ is

$$C_s(k) = w_1 \cdot S_{\text{toponym}}(m_k) + w_2 \cdot S_{\text{proximity}}(l_k) + w_3 \cdot S_{\text{topology}}(t_k) \quad \text{(A1)}$$

with standard weights $w_1 = 0.500$, $w_2 = 0.375$, $w_3 = 0.125$ and acceptance gate $C_s \geq 0.85$.

### Components

- **Toponym match (A2).** Maximum Jaro-Winkler similarity between the extracted landmarks $T_{\text{rep}}$ and the gazetteer attributes of node $k$, with accent stripping and token cleaning.
- **Proximity match (A3).** Gaussian decay to the nominal coordinate of the extracted kilometric post $k_{\text{PK}}$:
  $$S_{\text{proximity}}(l_k) = \exp\left(-\frac{d(k, k_{\text{PK}})^2}{2\sigma^2}\right), \quad \sigma = 150\ \text{m}.$$
- **Topology match.** 1.0 if node $k$ belongs to the designated route, else 0.0.

---

## 2. Algorithm 1, step by step (stateless)

1. **Sector reference**: `sector_ref <- k_municipality`. No state is carried from one record to the next, so every result is independent of processing order and of the other records.
2. **Candidate generation**
   - **Primary LRS-anchored mode** (PK marker resolved on the route; an ambiguous label is resolved with `sector_ref`): the active anchor is the nominal PK post $k_{\text{PK}}$; candidates are all nodes within $R_{\max} = 500$ m of $k_{\text{PK}}$ (nodes of other routes included, their topology score is 0); base weights $(0.500, 0.375, 0.125)$.
   - **Fallback mode** (PK omitted or unresolved): no proximity anchor; candidates are the route nodes in the municipal sector; $w_2$ is transferred to toponymy, giving $(0.875, 0.000, 0.125)$.
3. **Proximity decay** to $k_{\text{PK}}$ ($\sigma = 150$ m).
4. **Intersection pass**: if `intersection_descriptors` is set, $w_1 \leftarrow w_1 + w_3$ and $w_3 \leftarrow 0$.
5. **Deterministic selection and gate**: candidates are ranked by highest $C_s$, then smallest distance $d$ to $k_{\text{PK}}$ ($d = 0$ for all candidates in fallback mode), then lexicographic `Node_ID`; the first one is accepted if $C_s \geq 0.85$, otherwise the record goes to manual review.

**Ground truth is never used at runtime.** `CrashEvent` has no ground-truth field and the engine does not read reference coordinates. Positional accuracy ($E_{\text{geo}}$, median, P90, P95, RMSE) is computed afterwards with `dsda.evaluation.compute_geocoding_accuracy`, for accepted records (conditional) and for all records using the top-ranked candidate (inclusive).

---

## 3. Package architecture

```
dsda/
├── models.py       # Point2D, GisNode, PKPost, CrashEvent, Anchor, GeocodingResult, DSDAParameters
├── text_utils.py   # Accent normalization and string cleaning
├── metrics.py      # Equations A1 to A3, weight resolution (incl. intersection pass)
├── gis_store.py    # Centerline nodes, nominal PK posts, radius and sector queries
├── engine.py       # DSDAEngine (Algorithm 1) and single-event entry point
└── evaluation.py   # Post-hoc accuracy against ground truth (E_geo, P90, P95, RMSE)
scripts/
├── run_ablation.py          # Table D.2: component ablation (4 configurations + full model)
└── table_f3_poisson_snr.py  # Table F.3: scan-window SNR and 95% Poisson bands (seed 2026)
data/
├── rr27_table_f2.csv        # Per-PK counts of Table F.2 (30-crash subset)
└── example_synthetic/       # Synthetic files documenting the ablation input format
tests/
├── conftest.py            # Fixtures (Figure 3 example, synthetic corridor)
├── test_metrics.py        # Similarity functions and weights
├── test_anchor_rules.py   # LRS-anchored mode, statelessness, tie-breaking, intersection pass, no runtime ground truth
├── test_ablation_script.py # Ablation script on the synthetic example
├── test_engine.py         # GIS queries, summaries, sigma sensitivity
├── test_evaluation.py     # Post-hoc accuracy and percentiles
└── test_poc_parity.py     # Values of Figure 3 (panel c)
```

---

## 4. Installation

```bash
pip install .            # library
pip install -e ".[dev]"  # with pytest
```

---

## 5. Quick start

### A. Single event (Figure 3 example)
```python
from dsda import dsda_algorithm_with_logs

nodes = [
    {"node_name": "Node P3 (Bridge)",  "PK_marker": "PK34", "Gazetteer": "Hydraulic bridge",
     "Highway_Hierarchy": "RR27", "x": 500068.85, "y": 3700000},
    {"node_name": "Node P1 (Culvert)", "PK_marker": "PK34", "Gazetteer": "Hydraulic culvert",
     "Highway_Hierarchy": "RR27", "x": 500126.69, "y": 3700000},
]

result = dsda_algorithm_with_logs(
    pk_marker="PK34",
    t_rep="Hydraulic bridge (Maamoura)",
    target_route="RR27",
    k_pk={"x": 500000, "y": 3700000},   # nominal coordinate of the PK 34 post
    gis_database=nodes,
)
print(result["Decision"])   # AUTO-VALIDATED: Node P3 (Bridge) -> (500068.85, 3700000.0)
```

### B. Corridor processing and post-hoc evaluation
```python
from datetime import datetime
from dsda import (CrashEvent, DSDAEngine, GisDatabase, PKPost, Point2D,
                  compute_geocoding_accuracy)

gis_db = GisDatabase.from_records(node_records, pk_posts=[
    PKPost(route="RR27", pk_marker="PK34", coords=Point2D(500000.0, 3700000.0)),
])
events = [
    CrashEvent(event_id="CRASH_01", route="RR27", pk_marker="PK34",
               narrative_landmarks=["Hydraulic bridge"],
               timestamp=datetime(2025, 1, 1, 9, 0)),
]
results = DSDAEngine().process_corridor(events, gis_db)

# Ground truth only now, after all decisions are taken
report = compute_geocoding_accuracy(results, ground_truth={"CRASH_01": Point2D(500070.0, 3700001.0)})
print(report.acceptance_rate, report.conditional, report.inclusive)
```

---

## 6. Reproducing Tables D.2 and F.3

```bash
# Table D.2 (needs the corridor files described in the script header)
python scripts/run_ablation.py --data path/to/rr27 --out ablation_out

# Table F.3 (10,000 draws, seed 2026)
python scripts/table_f3_poisson_snr.py
```

`data/example_synthetic/` documents the format of the ablation input files (GIS nodes with gazetteer names, nominal PK posts, report fields, ground truth).

### Controlled testbed on the OpenStreetMap graph (Tables 5, C.1, C.2, D.2)

No surveyed crash positions exist for RR27. DSDA is therefore evaluated on a
simulation testbed built on the real OpenStreetMap road graph of RR27, with true positions
drawn inside each record's recorded PK interval. The protocol (`testbed/PROTOCOL.md`, v1.0)
was frozen before any real extract was loaded; results are reported whatever they are.

```bash
pip install pyproj shapely scipy openpyxl pandas networkx   # plus osmium for a .pbf
# OSM extract: run testbed/overpass_query.overpassql in overpass-turbo.eu, export raw OSM data (JSON)
python scripts/osm_testbed.py --osm export.json --registry BD_RR27F.xlsx --out testbed_out
```

Outputs: `table5_testbed`, `tableC1_testbed`, `tableC2_testbed`, `tableD2_testbed` (CSV and
Markdown), `manifest.json` (OSM timestamp, file hashes, seeds, anchors), `qa_report.md`, and the
input files of scenario S1 replicate 0 with the output of `scripts/run_ablation.py` on them.
The registry itself is not distributed; only its PK and coded-cause fields are read.

### Protocol v1.3: 82 RR27 crashes, from DSDA to the HRRS screening

`testbed/PROTOCOL_v1.3.md` (written and committed before any simulation) covers the 82
injury crashes of RR27 PK 27-42 (2007-2015), the frozen HRRS module `dsda/hrrs.py`
(segments HRRS-1 to HRRS-4, critical rates with exact Poisson bounds, multiplicity-adjusted
Poisson and severity scans) and four tasks, seed 2026, 1,000 replicates:

```bash
python scripts/export_rr27_82.py BD_RR27F.xlsx   # data/rr27_82_anonymized.csv (once)
python scripts/testbed_v13.py           # Task 1: results/ablation_v1_3.csv (+ simulation cache)
python scripts/sensitivity_sigma_cs.py  # Task 2: results/sensitivity_sigma_cs.csv, post hoc sigma
python scripts/end_to_end_hrrs.py       # Task 3: results/end_to_end_hrrs.csv
python scripts/hrrs_stage2_audit.py     # Task 4: results/hrrs_stage2_audit.csv (registry only)
```

Task 4 needs only `data/rr27_82_anonymized.csv`; Tasks 2 and 3 read the cache written by
Task 1 (`results/_cache/`, not versioned). Crash positions inside each kilometre are
simulated: Tasks 1 to 3 measure how DSDA behaves on the real OSM graph, not field accuracy.

---

## 7. Tests

```bash
pytest -v
```
