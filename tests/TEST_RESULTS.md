# DSDA test report

Regenerated with `pytest -v` after making the engine stateless (Algorithm 1, Appendix A.2, manuscript of 19 November 2026).

- Python 3.13.18
- Result: **55 passed** (50 DSDA tests plus 5 testbed tests)

## What the suite checks

| Area | File | Checks |
|---|---|---|
| Equations A1 to A3 | `test_metrics.py` | Jaro-Winkler toponym score, Gaussian proximity ($\sigma$ = 150 m), topology, weights (standard, fallback, intersection pass, ablation configurations), parameter validation |
| Algorithm 1 | `test_anchor_rules.py` | Anchor = nominal PK post $k_{PK}$; candidates of all routes within $R_{max}$ = 500 m; sector reference = $k_{municipality}$; identical results whatever the order and the other records; no `k_prev`; fallback weights (0.875, 0, 0.125); intersection pass; tie-breaking (highest $C_s$, then smallest $d$, then Node_ID); no ground truth in `CrashEvent` or in the engine |
| Engine and GIS store | `test_engine.py` | PK normalization, PK post resolution, radius queries, summaries, stability for $\sigma \in [100, 250]$ m |
| Post-hoc accuracy | `test_evaluation.py` | Linear-interpolated percentiles (P90, P95), conditional vs inclusive populations, decisions unchanged by ground truth |
| Ablation script | `test_ablation_script.py` | Five rows produced; full-model row identical to a direct run; PK-only baseline rejects records without PK (synthetic data) |
| OSM testbed | `test_osm_testbed.py` | On an invented OSM fixture: five anchors found and inverted exactly; true positions inside the recorded PK interval; scenarios nested (S0 none, S1 within S2); deterministic full pass; `run_ablation.py` reproduces the in-process counts |
| Figure 3 | `test_poc_parity.py` | Panel (c) values for $T_{rep}$ = "Hydraulic bridge (Maamoura)" |

## Figure 3 reproduction (`python example_usage.py`)

| Node | Route | k.Gazetteer | d (m) | $S_{toponym}$ | $S_{proximity}$ | $S_{topology}$ | $C_s$ |
|---|---|---|---|---|---|---|---|
| P3 | RR27 | Hydraulic bridge | 68.85 | 0.928 | 0.900 | 1.0 | **0.927** |
| P1 | RR27 | Hydraulic culvert | 126.69 | 0.842 | 0.700 | 1.0 | 0.808 |
| P2 | RR43 | RR43 junction | 151.61 | 0.511 | 0.600 | 0.0 | 0.480 |
| P4 | MC28 | Farm track | 232.76 | 0.447 | 0.300 | 0.0 | 0.336 |

Anchor = PK 34 post. Synthetic, illustrative test case: the gazetteer strings and coordinates are not RR27 data. $C_s$ is computed from unrounded components.

## Scope

These tests verify the implementation on synthetic data. They do not reproduce the corridor results of the manuscript (RR27, RN15), which would require surveyed crash positions; no such survey exists. The OSM testbed (`testbed/PROTOCOL.md`) evaluates DSDA on simulated positions instead.

## Detailed results

| File | Test | Status |
|---|---|---|
| `test_ablation_script.py` | `test_ablation_rows_and_full_model_consistency` | PASSED |
| `test_ablation_script.py` | `test_pk_only_baseline_rejects_records_without_pk` | PASSED |
| `test_anchor_rules.py` | `TestPrimaryLrsAnchoredMode::test_anchor_is_nominal_pk_post` | PASSED |
| `test_anchor_rules.py` | `TestPrimaryLrsAnchoredMode::test_candidates_limited_to_r_max_all_routes` | PASSED |
| `test_anchor_rules.py` | `TestStatelessness::test_result_independent_of_order_and_of_other_records` | PASSED |
| `test_anchor_rules.py` | `TestStatelessness::test_sector_reference_is_always_the_municipality` | PASSED |
| `test_anchor_rules.py` | `TestStatelessness::test_engine_has_no_state_variable` | PASSED |
| `test_anchor_rules.py` | `TestFallbackMode::test_omitted_pk_uses_fallback_weights` | PASSED |
| `test_anchor_rules.py` | `TestFallbackMode::test_ambiguous_pk_resolved_by_municipal_sector` | PASSED |
| `test_anchor_rules.py` | `TestIntersectionPass::test_weights_anchored` | PASSED |
| `test_anchor_rules.py` | `TestIntersectionPass::test_weights_fallback` | PASSED |
| `test_anchor_rules.py` | `TestDeterministicTieBreaking::test_equal_cs_smaller_distance_wins` | PASSED |
| `test_anchor_rules.py` | `TestDeterministicTieBreaking::test_equal_cs_and_distance_lexicographic_id` | PASSED |
| `test_anchor_rules.py` | `TestDeterministicTieBreaking::test_fallback_tie_uses_node_id` | PASSED |
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
| `test_metrics.py` | `TestProximitySimilarity::test_no_anchor_returns_zero` | PASSED |
| `test_metrics.py` | `TestProximitySimilarity::test_exact_coincidence_distance_zero` | PASSED |
| `test_metrics.py` | `TestProximitySimilarity::test_gaussian_decay_at_one_sigma` | PASSED |
| `test_metrics.py` | `TestProximitySimilarity::test_gaussian_decay_at_two_sigma` | PASSED |
| `test_metrics.py` | `TestProximitySimilarity::test_invalid_sigma_raises_value_error` | PASSED |
| `test_metrics.py` | `TestTopologySimilarity::test_matching_route_returns_one` | PASSED |
| `test_metrics.py` | `TestTopologySimilarity::test_case_and_whitespace_insensitivity` | PASSED |
| `test_metrics.py` | `TestTopologySimilarity::test_mismatched_route_returns_zero` | PASSED |
| `test_metrics.py` | `TestTopologySimilarity::test_empty_route_returns_zero` | PASSED |
| `test_metrics.py` | `TestWeightsAndCompositeScore::test_fallback_weights` | PASSED |
| `test_metrics.py` | `TestWeightsAndCompositeScore::test_standard_weights` | PASSED |
| `test_metrics.py` | `TestWeightsAndCompositeScore::test_intersection_pass_weights` | PASSED |
| `test_metrics.py` | `TestWeightsAndCompositeScore::test_fallback_weights_for_ablation_configs` | PASSED |
| `test_metrics.py` | `TestWeightsAndCompositeScore::test_composite_score_calculation` | PASSED |
| `test_metrics.py` | `TestWeightsAndCompositeScore::test_invalid_parameters_raise_error` | PASSED |
| `test_poc_parity.py` | `TestFigure3Example::test_lrs_anchored_mode` | PASSED |
| `test_poc_parity.py` | `TestFigure3Example::test_fallback_without_pk_post` | PASSED |
| `test_poc_parity.py` | `TestFigure3Example::test_unrelated_landmark_is_rejected` | PASSED |
