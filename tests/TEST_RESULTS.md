# DSDA Test Execution & Validation Report

This report documents the verification, benchmark performance, and test execution of the **Deterministic Spatial Disambiguation Algorithm (DSDA)**, conforming to Appendix A.1 of the formal mathematical specification.

---

## 1. Summary of Test Runs & Execution Times

| Test Scenario | Condition / Rule | Anchor ($k_{\text{prev}}$) | Weights $(w_1, w_2, w_3)$ | Selected Candidate | Score ($C_s$) | Decision | Execution Time |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| **Test 1** | Standard Corridor Case | Active Anchor (`x=500000, y=3700000`) | `{w1: 0.5, w2: 0.375, w3: 0.125}` | **Node P3 (Target)** | **0.950** | **AUTO-VALIDATED** | **~0.055 ms** (55 µs) |
| **Test 2** | Cold Start | `k_prev = None` (Route start) | `{w1: 0.875, w2: 0.0, w3: 0.125}` | **Node P3 (Target)** | **0.978** | **AUTO-VALIDATED** | **~0.044 ms** (44 µs) |
| **Test 3** | Simultaneous Events ($\le 24\text{h}$) | Regional Municipality Centroid | `{w1: 0.5, w2: 0.375, w3: 0.125}` | **Node P3 (Target)** | **0.981** | **AUTO-VALIDATED** | **~0.035 ms** (35 µs) |
| **Test 4** | Ambiguous Narrative ($C_s < 0.85$) | Active Anchor (`Node P3`) | `{w1: 0.5, w2: 0.375, w3: 0.125}` | Node P3 (Target) | 0.697 | **MANUAL REVIEW** | **~0.048 ms** (48 µs) |
| **Corridor** | Full 4-Event Corridor Sequence | Dynamic (Rules 1, 2, 3) | Adaptive | Pipeline Sequence | Multi-score | Full Corridor Run | **~0.153 ms** (153 µs) |

> **Throughput**: Single-event disambiguation throughput is **~18,000 to 28,000 events/second** per CPU core.

---

## 2. Detailed Test Outputs with Execution Time

```text
==================== TEST 1 : CAS STANDARD (AVEC ANCRE) ====================
Poids appliqués : {'w1': 0.5, 'w2': 0.375, 'w3': 0.125}
Temps d'exécution : 0.055 ms (54.9 microsecondes)
--- DÉTAIL DE L'ÉVALUATION DES CANDIDATS ---
Candidat : Node P3 (Target)
  - Distance calculée : 68.85m
  - Sous-scores : Toponymie=0.975 | Proximité=0.9 | Topologie=1.0 (RR27)
  - Score final (Cs)  : 0.95

Candidat : Node P1 (Bypass)
  - Distance calculée : 126.69m
  - Sous-scores : Toponymie=0.9 | Proximité=0.7 | Topologie=1.0 (RR27)
  - Score final (Cs)  : 0.838

Candidat : Node P2 (Parallel)
  - Distance calculée : 151.61m
  - Sous-scores : Toponymie=0.595 | Proximité=0.6 | Topologie=0.0 (RR43)
  - Score final (Cs)  : 0.523

Candidat : Node P4 (Local)
  - Distance calculée : 232.76m
  - Sous-scores : Toponymie=0.492 | Proximité=0.3 | Topologie=0.0 (MC28)
  - Score final (Cs)  : 0.359

--- DÉCISION FINALE DU SYSTÈME DSDA ---
AUTO-VALIDATED: Node P3 (Target) -> (33.881, 10.098)
```

```text
==================== TEST 2 : COLD START (k_prev = None) ====================
Poids appliqués : {'w1': 0.875, 'w2': 0.0, 'w3': 0.125}
Temps d'exécution : 0.044 ms (44.4 microsecondes)
--- DÉTAIL DE L'ÉVALUATION DES CANDIDATS ---
Candidat : Node P3 (Target)
  - Distance calculée : 0.0m
  - Sous-scores : Toponymie=0.975 | Proximité=0.0 | Topologie=1.0 (RR27)
  - Score final (Cs)  : 0.978

Candidat : Node P1 (Bypass)
  - Distance calculée : 0.0m
  - Sous-scores : Toponymie=0.9 | Proximité=0.0 | Topologie=1.0 (RR27)
  - Score final (Cs)  : 0.912

Candidat : Node P2 (Parallel)
  - Distance calculée : 0.0m
  - Sous-scores : Toponymie=0.595 | Proximité=0.0 | Topologie=0.0 (RR43)
  - Score final (Cs)  : 0.521

Candidat : Node P4 (Local)
  - Distance calculée : 0.0m
  - Sous-scores : Toponymie=0.492 | Proximité=0.0 | Topologie=0.0 (MC28)
  - Score final (Cs)  : 0.431

--- DÉCISION FINALE DU SYSTÈME DSDA ---
AUTO-VALIDATED: Node P3 (Target) -> (33.881, 10.098)
```

```text
==================== TEST 3 : SIMULTANEOUS EVENTS (<= 24h) ====================
Poids appliqués : {'w1': 0.5, 'w2': 0.375, 'w3': 0.125}
Ancre utilisée  : MUNICIPALITY_CENTROID (x=500050.0, y=3700020.0)
Temps d'exécution : 0.035 ms (34.5 microsecondes)
--- DÉTAIL DE L'ÉVALUATION DES CANDIDATS ---
Candidat : Node P3 (Target)
  - Distance calculée : 27.48m
  - Sous-scores : Toponymie=0.975 | Proximité=0.983 | Topologie=1.0 (RR27)
  - Score final (Cs)  : 0.981

Candidat : Node P1 (Bypass)
  - Distance calculée : 79.26m
  - Sous-scores : Toponymie=0.900 | Proximité=0.870 | Topologie=1.0 (RR27)
  - Score final (Cs)  : 0.901

Candidat : Node P2 (Parallel)
  - Distance calculée : 103.56m
  - Sous-scores : Toponymie=0.595 | Proximité=0.788 | Topologie=0.0 (RR43)
  - Score final (Cs)  : 0.593

Candidat : Node P4 (Local)
  - Distance calculée : 183.85m
  - Sous-scores : Toponymie=0.492 | Proximité=0.472 | Topologie=0.0 (MC28)
  - Score final (Cs)  : 0.423

--- DÉCISION FINALE DU SYSTÈME DSDA ---
AUTO-VALIDATED: Node P3 (Target) -> (33.881, 10.098)
```

```text
==================== TEST 4 : ANCHOR INDEPENDENCE (Cs < 0.85 REJECTION) ====================
Poids appliqués : {'w1': 0.5, 'w2': 0.375, 'w3': 0.125}
Ancre utilisée  : PRIOR_EVENT (Node P3)
Temps d'exécution : 0.048 ms (47.8 microsecondes)
--- DÉTAIL DE L'ÉVALUATION DES CANDIDATS ---
Candidat : Node P3 (Target)
  - Distance calculée : 0.00m
  - Sous-scores : Toponymie=0.395 | Proximité=1.000 | Topologie=1.0 (RR27)
  - Score final (Cs)  : 0.697

Candidat : Node P2 (Parallel)
  - Distance calculée : 82.76m
  - Sous-scores : Toponymie=0.520 | Proximité=0.859 | Topologie=0.0 (RR43)
  - Score final (Cs)  : 0.582

Candidat : Node P1 (Bypass)
  - Distance calculée : 57.84m
  - Sous-scores : Toponymie=0.000 | Proximité=0.928 | Topologie=1.0 (RR27)
  - Score final (Cs)  : 0.473

Candidat : Node P4 (Local)
  - Distance calculée : 163.91m
  - Sous-scores : Toponymie=0.421 | Proximité=0.550 | Topologie=0.0 (MC28)
  - Score final (Cs)  : 0.417

--- DÉCISION FINALE DU SYSTÈME DSDA ---
REJECTED: Manual Review Required (Max score 0.697 < 0.85)
-> Statut d'ancre : REJETÉE (Le système conserve l'ancre sûre précédente)
```

---

## 3. Automated Pytest Test Suite Results & Durations

Total test suite duration: **0.05 seconds** for 32 tests.

```text
============================= test session starts =============================
platform win32 -- Python 3.11.6, pytest-9.1.1, pluggy-1.6.0 -- Python311\python.exe
cachedir: .pytest_cache
rootdir: C:\Users\User\Documents\dev\dsda
configfile: pyproject.toml
testpaths: tests
plugins: anyio-4.13.0, hydra-core-1.3.2, langsmith-0.7.25
collected 32 items

tests/test_anchor_rules.py::TestRule1ColdStart::test_first_event_in_dataset_is_cold_start PASSED  [  3%]
tests/test_anchor_rules.py::TestRule1ColdStart::test_switching_route_triggers_cold_start PASSED   [  6%]
tests/test_anchor_rules.py::TestRule2SimultaneousEvents::test_event_within_24h_uses_municipality_centroid PASSED [  9%]
tests/test_anchor_rules.py::TestRule3AnchorIndependence::test_low_score_event_rejected_as_anchor_and_reverts PASSED [ 12%]
tests/test_anchor_rules.py::TestRule3AnchorIndependence::test_e_geo_tolerance_exceeded_rejects_as_anchor PASSED [ 15%]
tests/test_engine.py::TestGisDatabase::test_pk_normalization_lookup PASSED                       [ 18%]
tests/test_engine.py::TestGisDatabase::test_nearest_node_lookup PASSED                           [ 21%]
tests/test_engine.py::TestGisDatabase::test_from_records_and_len PASSED                          [ 25%]
tests/test_engine.py::TestEngineEvaluation::test_no_candidates_returns_rejected_status PASSED    [ 28%]
tests/test_engine.py::TestEngineEvaluation::test_summary_table_formatting PASSED                 [ 31%]
tests/test_engine.py::TestEngineEvaluation::test_sigma_sensitivity_stability PASSED             [ 34%]
tests/test_metrics.py::TestToponymSimilarity::test_exact_match PASSED                            [ 37%]
tests/test_metrics.py::TestToponymSimilarity::test_transposition_variation PASSED                [ 40%]
tests/test_metrics.py::TestToponymSimilarity::test_accent_and_diacritic_invariance PASSED       [ 43%]
tests/test_metrics.py::TestToponymSimilarity::test_multiple_aliases_selects_maximum PASSED      [ 46%]
tests/test_metrics.py::TestToponymSimilarity::test_empty_inputs_return_zero PASSED              [ 50%]
tests/test_metrics.py::TestProximitySimilarity::test_cold_start_none_anchor_returns_zero PASSED  [ 53%]
tests/test_metrics.py::TestProximitySimilarity::test_exact_coincidence_distance_zero PASSED     [ 56%]
tests/test_metrics.py::TestProximitySimilarity::test_gaussian_decay_at_one_sigma PASSED         [ 59%]
tests/test_metrics.py::TestProximitySimilarity::test_gaussian_decay_at_two_sigma PASSED         [ 62%]
tests/test_metrics.py::TestProximitySimilarity::test_invalid_sigma_raises_value_error PASSED    [ 65%]
tests/test_metrics.py::TestTopologySimilarity::test_matching_route_returns_one PASSED            [ 68%]
tests/test_metrics.py::TestTopologySimilarity::test_case_and_whitespace_insensitivity PASSED   [ 71%]
tests/test_metrics.py::TestTopologySimilarity::test_mismatched_route_returns_zero PASSED        [ 75%]
tests/test_metrics.py::TestTopologySimilarity::test_empty_route_returns_zero PASSED             [ 78%]
tests/test_metrics.py::TestWeightsAndCompositeScore::test_cold_start_weights PASSED              [ 81%]
tests/test_metrics.py::TestWeightsAndCompositeScore::test_standard_weights PASSED                [ 84%]
tests/test_metrics.py::TestWeightsAndCompositeScore::test_composite_score_calculation PASSED     [ 87%]
tests/test_metrics.py::TestWeightsAndCompositeScore::test_invalid_parameters_raise_error PASSED  [ 90%]
tests/test_poc_parity.py::TestPocParity::test_scenario_1_with_active_anchor PASSED              [ 93%]
tests/test_poc_parity.py::TestPocParity::test_scenario_2_cold_start PASSED                      [ 96%]
tests/test_poc_parity.py::TestPocParity::test_scenario_rejected_manual_review PASSED            [100%]

============================= 32 passed in 0.05s ==============================
```
