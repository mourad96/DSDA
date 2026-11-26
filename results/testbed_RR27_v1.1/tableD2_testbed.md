| Configuration | Weights (w1, w2, w3) | Automated throughput (of 83) | Conditional mean E_geo (m) | Inclusive mean E_geo (m) | Conditional P90 (m) |
|---|---|---|---|---|---|
| Municipality centroid (address-level baseline) | -- | -- | -- | 1682.8 [1647.6, 1717.4] | -- |
| Nominal LRS PK only (proximity baseline) | (0.000, 1.000, 0.000) | 42.6 [39.0, 46.0] | 269.4 [206.4, 342.2] | 300.8 [248.0, 361.6] | 480.3 [407.4, 576.6] |
| Toponymy only (no proximity, no topology) | (1.000, 0.000, 0.000) | 23.9 [16.0, 31.0] | 114.7 [60.1, 212.4] | 437.3 [262.6, 654.3] | 253.8 [146.6, 572.3] |
| Without topology (S_top + S_prox) | (0.571, 0.429, 0.000) | 9.7 [5.0, 15.0] | 157.5 [50.6, 374.3] | 459.1 [288.3, 683.8] | 344.2 [105.9, 749.1] |
| Without proximity (S_top + S_topo) | (0.800, 0.000, 0.200) | 17.8 [11.0, 24.0] | 120.3 [49.1, 251.8] | 436.8 [261.9, 657.5] | 290.1 [114.4, 590.5] |
| Full DSDA | (0.500, 0.375, 0.125) | 9.3 [4.0, 14.0] | 163.9 [51.0, 366.7] | 456.0 [282.9, 680.3] | 352.8 [111.4, 781.6] |

Scenario S1. Mean over 1000 replicates [2.5th, 97.5th percentile].
