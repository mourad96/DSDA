# DSDA: Deterministic Spatial Disambiguation Algorithm

A production-grade, reproducible Python implementation of the **Deterministic Spatial Disambiguation Algorithm (DSDA)** for resolving ambiguous linear-referencing crash narratives into georeferenced GIS locations along highway corridors.

---

## 1. Formal Mathematical Specification

The Contextual Compatibility Score ($C_s$) is a deterministic multi-criteria score defined as:

$$C_s(k) = w_1 \cdot S_{\text{toponym}}(m_k) + w_2 \cdot S_{\text{proximity}}(l_k) + w_3 \cdot S_{\text{topology}}(t_k) \quad \text{(A1)}$$

### Standard Multi-Criteria Weights
- $w_1 = 0.500$ (Toponymic similarity)
- $w_2 = 0.375$ (Spatial proximity)
- $w_3 = 0.125$ (Topological route match)

---

### Component Formulations

#### 1. Toponym Match ($S_{\text{toponym}}$) &mdash; Equation A2
Computes the maximum Jaro-Winkler string similarity ($d_{jw}$) between extracted narrative landmarks ($T_{\text{rep}}$) and GIS centerline node attributes ($T_{\text{gis}}(k)$):

$$S_{\text{toponym}}(m_k) = \max_{m \in T_{\text{rep}},\, g \in T_{\text{gis}}(k)} \left[ d_{jw}(m, g) \right] \quad \text{(A2)}$$

Includes Unicode normalization, accent stripping (e.g. *Béni Khiar* $\leftrightarrow$ *Beni Khiar*), and token cleaning.

#### 2. Proximity Match ($S_{\text{proximity}}$) &mdash; Equation A3
Localized Gaussian decay function penalizing spatial deviation $d(k, k_{\text{prev}})$ from the chronologically prior geocoded anchor ($k_{\text{prev}}$):

$$S_{\text{proximity}}(l_k) = \exp\left( -\frac{d(k, k_{\text{prev}})^2}{2 \sigma^2} \right) \quad \text{(A3)}$$

- Structural bandwidth $\sigma = 150.0\,\text{m}$ (approximates the median inter-landmark spacing along corridor segments).
- Sensitivity testing ($\sigma \in [100, 250]\,\text{m}$) demonstrates classification stability.

---

### The Three Anchor Initialization Rules

To prevent recursive error propagation and handle initial corridor states, the proximity function operates under three deterministic initialization rules:

1. **Rule 1: Cold Start**
   - For the chronologically first event in a dataset, or when switching to a different route identifier, $k_{\text{prev}}$ is uninitialized.
   - The $S_{\text{proximity}}$ component is neutralized, with $w_2$ variance absorbed by $w_1$:
     $$w_1 = 0.875, \quad w_2 = 0.000, \quad w_3 = 0.125$$
   - Geocoding is purely toponymic and topological.

2. **Rule 2: Simultaneous Events ($\Delta t \le 24\text{h}$)**
   - If multiple crash events occur within a tight temporal window ($\Delta t \le 24\,\text{h}$) on the same route, $k_{\text{prev}}$ defaults to the **established regional centroid of the primary municipality** rather than the immediately prior accident.
   - Explicitly prevents tight temporal clustering artifacts.

3. **Rule 3: Anchor Independence (Error Propagation Shield)**
   - To break recursive error chains, the algorithm strictly utilizes independent anchors.
   - If an event is flagged for manual review ($C_s < 0.85$) or exceeds the spatial error tolerance ($E_{\text{geo}} > 50\,\text{m}$), it is **rejected as an anchor**.
   - The system reverts to the last safely geocoded event for subsequent $k_{\text{prev}}$ evaluations.

#### 3. Topology Match ($S_{\text{topology}}$)
Binary infrastructure filter:
$$S_{\text{topology}}(t_k) = \begin{cases} 1.0 & \text{if candidate } k \text{ connects directly to the designated highway hierarchy} \\ 0.0 & \text{otherwise} \end{cases}$$
Corridors are modeled as bidirectional single-carriageways.

---

## 2. Package Architecture

```
dsda/
├── __init__.py           # Package exports
├── models.py             # Dataclasses (Point2D, GisNode, CrashEvent, Anchor, GeocodingResult)
├── text_utils.py         # Unicode accent normalization & string sanitization
├── metrics.py            # Equations A1, A2, A3, dynamic weight rebalancing
├── gis_store.py          # Spatial database indexed by PK marker
└── engine.py             # Core DSDAEngine & backward-compatible function
tests/
├── conftest.py           # Shared fixtures
├── test_metrics.py       # Math metric unit tests (Gaussian decay, Jaro-Winkler, weights)
├── test_anchor_rules.py  # Rule 1 (Cold start), Rule 2 (Simultaneous), Rule 3 (Anchor independence)
├── test_engine.py        # Database querying, summary formatting, sigma sensitivity
└── test_poc_parity.py    # Exact numerical parity against the prototype script
```

---

## 3. Installation

```bash
pip install .
```

For development and running tests:
```bash
pip install -e ".[dev]"
```

---

## 4. Quick Start

### A. Backward-Compatible POC Call
```python
from dsda import dsda_algorithm_with_logs

base_sig = [
    {
        "node_name": "Node P3 (Target)",
        "PK_marker": "PK34",
        "Gazetteer": "B. Khair",
        "Highway_Hierarchy": "RR27",
        "x": 500068.85,
        "y": 3700000,
        "WGS84_Coordinates": (33.881, 10.098),
    },
    {
        "node_name": "Node P1 (Bypass)",
        "PK_marker": "PK34",
        "Gazetteer": "B. K",
        "Highway_Hierarchy": "RR27",
        "x": 500126.69,
        "y": 3700000,
        "WGS84_Coordinates": (33.882, 10.099),
    },
]

# Standard Call with prior anchor
result = dsda_algorithm_with_logs(
    pk_marker="PK34",
    t_rep="B. Khiar",
    target_route="RR27",
    k_prev={"x": 500000, "y": 3700000},
    gis_database=base_sig,
)

print(result["Decision"])
# Output: AUTO-VALIDATED: Node P3 (Target) -> (33.881, 10.098)
```

### B. High-Level Engine & Corridor Sequence Processing
```python
from datetime import datetime
from dsda import DSDAEngine, GisDatabase, CrashEvent, Point2D

gis_db = GisDatabase.from_records(...)
engine = DSDAEngine()

events = [
    CrashEvent(
        event_id="CRASH_01",
        route="RR27",
        pk_marker="PK34",
        narrative_landmarks=["B. Khiar"],
        timestamp=datetime(2025, 1, 1, 9, 0),
        municipality_centroid=Point2D(500050.0, 3700020.0),
    ),
]

results = engine.process_corridor(events, gis_db)
for res in results:
    print(res.summary_table())
```

---

## 5. Running the Test Suite

Run all 32 unit and regression tests with `pytest`:

```bash
pytest -v
```
