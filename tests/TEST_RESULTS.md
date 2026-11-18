# DSDA test report

Regenerated with `pytest -v` after aligning the code with Algorithm 1 (manuscript v2.5).

- Python 3.13.18
- Result: **44 passed in 0.05s**

## What the suite checks

| Area | File | Checks |
|---|---|---|
| Equations A1 to A3 | `test_metrics.py` | Jaro-Winkler toponym score, Gaussian proximity ($\sigma$ = 150 m), topology, weight sets (standard, fallback, intersection pass), parameter validation ($R_{\max}$, gate) |
| Algorithm 1 | `test_anchor_rules.py` | Anchor = nominal PK post $k_{\text{PK}}$; candidates within $R_{\max}$ = 500 m; order independence; fallback weights (0.875, 0, 0.125); sector reference rules ($k_{\text{municipality}}$ if $k_{\text{prev}}$ missing, route change or $\Delta t \leq 24$ h, else $k_{\text{prev}}$); ambiguous PK labels; intersection pass; only accepted records update $k_{\text{prev}}$; no ground truth in `CrashEvent` or in the engine |
| Engine and GIS store | `test_engine.py` | PK normalization, PK post resolution, radius queries, summaries, stability for $\sigma \in [100, 250]$ m |
| Post-hoc accuracy | `test_evaluation.py` | Linear-interpolated percentiles (P90, P95), conditional vs inclusive populations, decisions unchanged by ground truth |
| Figure 3 | `test_poc_parity.py` | Panel (c) values: P3 0.945 / 0.900 / 1.0 / **0.935** (accepted), P1 0.804 (< 0.85, manual review), P2 0.458, P4 0.369 |

## Figure 3 reproduction (`python example_usage.py`)

| Node | Route | d (m) | $S_{\text{toponym}}$ | $S_{\text{proximity}}$ | $S_{\text{topology}}$ | $C_s$ |
|---|---|---|---|---|---|---|
| P3 (bridge) | RR27 | 68.85 | 0.945 | 0.900 | 1.0 | **0.935** |
| P1 (culvert) | RR27 | 126.69 | 0.834 | 0.700 | 1.0 | 0.804 |
| P2 | RR43 | 151.61 | 0.467 | 0.600 | 0.0 | 0.458 |
| P4 | MC28 | 232.76 | 0.513 | 0.300 | 0.0 | 0.369 |

$T_{\text{rep}}$ = "Hydraulic bridge (PK 34)", anchor = PK 34 post. The gazetteer strings are a toy example; the values are what the code computes, they are not tuned to a target.

## Scope

These tests verify the implementation of Algorithm 1 on synthetic data. They do not reproduce the corridor results of the manuscript (RR27, RN15), which require the real gazetteer, the PK post layer and the RTK-DGPS ground truth.

## Detailed results

| File | Test | Status |
|---|---|---|
| `test_anchor_rules.py` | `TestPrimaryLrsAnchoredMode::test_anchor_is_nominal_pk_post` | PASSED |
| `test_anchor_rules.py` | `TestPrimaryLrsAnchoredMode::test_candidates_limited_to_r_max` | PASSED |
| `test_anchor_rules.py` | `TestPrimaryLrsAnchoredMode::test_order_independence` | PASSED |
| `test_anchor_rules.py` | `TestFallbackAndSectorReference::test_omitted_pk_uses_fallback_weights` | PASSED |
| `test_anchor_rules.py` | `TestFallbackAndSectorReference::test_sector_reference_rules` | PASSED |
| `test_anchor_rules.py` | `TestFallbackAndSectorReference::test_ambiguous_pk_resolved_by_sector` | PASSED |
| `test_anchor_rules.py` | `TestIntersectionPass::test_weights_anchored` | PASSED |
| `test_anchor_rules.py` | `TestIntersectionPass::test_weights_fallback` | PASSED |
| `test_anchor_rules.py` | `TestAnchorIndependence::test_rejected_event_does_not_update_k_prev` | PASSED |
| `test_anchor_rules.py` | `TestNoGroundTruthAtRuntime::test_event_has_no_ground_truth_field` | PASSED |
| `test_anchor_rules.py` | `TestNoGroundTruthAtRuntime::test_engine_does_not_import_evaluation` | PASSED |
| `test_engine.py` | `TestGisDatabase::test_pk_normalization_lookup` | PASSED |
| `test_engine.py` | `TestGisDatabase::test_pk_post_resolution` | PASSED |
| `test_engine.py` | `TestGisDatabase::test_query_within_radius` | PASSED |
| `test_engine.py` | `TestGisDatabase::test_nearest_node_lookup` | PASSED |
| `test_engine.py` | `TestGisDatabase::test_from_records_and_len` | PASSED |
| `test_engine.py` | `TestEngineEvaluation::test_no_candidates_returns_rejected_status` | PASSED |
| `test_engine.py` | `TestEngineEvaluation::test_summary_table_formatting` | PASSED |
| `test_engine.py` | `TestEngineEvaluation::test_sigma_sensitivity_stability` | PASSED |
| `test_evaluation.py` | `test_percentile_linear_matches_numpy_definition` | PASSED |
| `test_evaluation.py` | `test_conditional_and_inclusive_populations` | PASSED |
| `test_evaluation.py` | `test_ground_truth_does_not_change_decisions` | PASSED |
| `test_metrics.py` | `TestToponymSimilarity::test_exact_match` | PASSED |
| `test_metrics.py` | `TestToponymSimilarity::test_transposition_variation` | PASSED |
| `test_metrics.py` | `TestToponymSimilarity::test_accent_and_diacritic_invariance` | PASSED |
| `test_metrics.py` | `TestToponymSimilarity::test_multiple_aliases_selects_maximum` | PASSED |
| `test_metrics.py` | `TestToponymSimilarity::test_empty_inputs_return_zero` | PASSED |
| `test_metrics.py` | `TestProximitySimilarity::test_cold_start_none_anchor_returns_zero` | PASSED |
| `test_metrics.py` | `TestProximitySimilarity::test_exact_coincidence_distance_zero` | PASSED |
| `test_metrics.py` | `TestProximitySimilarity::test_gaussian_decay_at_one_sigma` | PASSED |
| `test_metrics.py` | `TestProximitySimilarity::test_gaussian_decay_at_two_sigma` | PASSED |
| `test_metrics.py` | `TestProximitySimilarity::test_invalid_sigma_raises_value_error` | PASSED |
| `test_metrics.py` | `TestTopologySimilarity::test_matching_route_returns_one` | PASSED |
| `test_metrics.py` | `TestTopologySimilarity::test_case_and_whitespace_insensitivity` | PASSED |
| `test_metrics.py` | `TestTopologySimilarity::test_mismatched_route_returns_zero` | PASSED |
| `test_metrics.py` | `TestTopologySimilarity::test_empty_route_returns_zero` | PASSED |
| `test_metrics.py` | `TestWeightsAndCompositeScore::test_cold_start_weights` | PASSED |
| `test_metrics.py` | `TestWeightsAndCompositeScore::test_standard_weights` | PASSED |
| `test_metrics.py` | `TestWeightsAndCompositeScore::test_intersection_pass_weights` | PASSED |
| `test_metrics.py` | `TestWeightsAndCompositeScore::test_composite_score_calculation` | PASSED |
| `test_metrics.py` | `TestWeightsAndCompositeScore::test_invalid_parameters_raise_error` | PASSED |
| `test_poc_parity.py` | `TestFigure3Example::test_lrs_anchored_mode` | PASSED |
| `test_poc_parity.py` | `TestFigure3Example::test_fallback_without_pk_post` | PASSED |
| `test_poc_parity.py` | `TestFigure3Example::test_unrelated_landmark_is_rejected` | PASSED |
