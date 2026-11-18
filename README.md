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

## 2. Algorithm 1, step by step

1. **Sector reference** (used only when the PK marker is omitted or ambiguous):
   - $k_{\text{prev}}$ uninitialized or route change: $k_{\text{municipality}}$;
   - $\Delta t \leq 24$ h since the last accepted record on the route: $k_{\text{municipality}}$;
   - otherwise: $k_{\text{prev}}$ (last accepted record).
2. **Candidate generation**
   - **Primary LRS-anchored mode** (PK marker resolved on the route): the active anchor is the nominal PK post $k_{\text{PK}}$; candidates are all nodes within $R_{\max} = 500$ m of $k_{\text{PK}}$ (nodes of other routes included, their topology score is 0); base weights $(0.500, 0.375, 0.125)$. This mode is independent of record order.
   - **Fallback mode** (PK omitted, unknown, or shared by several chainages without a sector reference): no proximity anchor; candidates are the route nodes in the active sector; base weights $(0.875, 0.000, 0.125)$.
3. **Proximity decay** to $k_{\text{PK}}$ ($\sigma = 150$ m).
4. **Intersection pass**: if `intersection_descriptors` is set, $w_1 \leftarrow w_1 + w_3$ and $w_3 \leftarrow 0$.
5. **Acceptance gate**: the best candidate is accepted if $C_s \geq 0.85$; only accepted records update $k_{\text{prev}}$ (anchor independence). Rejected records go to manual review.

**Ground truth is never used at runtime.** `CrashEvent` has no ground-truth field and the engine does not read RTK-DGPS coordinates. Positional accuracy ($E_{\text{geo}}$, median, P90, P95, RMSE) is computed afterwards with `dsda.evaluation.compute_geocoding_accuracy`, for accepted records (conditional) and for all records using the top-ranked candidate (inclusive).

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
tests/
├── conftest.py            # Fixtures (Figure 3 example, synthetic corridor)
├── test_metrics.py        # Similarity functions and weights
├── test_anchor_rules.py   # LRS-anchored mode, sector rules, intersection pass, no runtime ground truth
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
    t_rep="Hydraulic bridge (PK 34)",
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

## 6. Tests

```bash
pytest -v
```
