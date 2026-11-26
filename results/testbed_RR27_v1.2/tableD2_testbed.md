| Configuration | Weights (w1, w2, w3) | Automated throughput (of 83) | Conditional mean E_geo (m) | Inclusive mean E_geo (m) | Conditional P90 (m) |
|---|---|---|---|---|---|
| Municipality centroid (address-level baseline) | -- | -- | -- | 1680.3 [1644.6, 1713.6] | -- |
| Nominal LRS PK only (proximity baseline) | (0.000, 1.000, 0.000) | 42.6 [39.0, 46.0] | 277.3 [218.4, 350.2] | 303.9 [251.3, 363.6] | 473.8 [400.9, 633.2] |
| Toponymy only (no proximity, no topology) | (1.000, 0.000, 0.000) | 23.8 [17.0, 31.0] | 120.2 [66.4, 214.3] | 438.9 [267.1, 654.0] | 257.3 [146.2, 510.5] |
| Without topology (S_top + S_prox) | (0.571, 0.429, 0.000) | 10.3 [5.0, 16.0] | 156.4 [61.0, 337.4] | 460.0 [292.1, 676.8] | 323.7 [129.0, 698.7] |
| Without proximity (S_top + S_topo) | (0.800, 0.000, 0.200) | 15.6 [10.0, 21.0] | 128.8 [49.8, 260.9] | 438.3 [267.9, 655.9] | 304.4 [112.9, 619.7] |
| Full DSDA | (0.500, 0.375, 0.125) | 9.7 [5.0, 15.0] | 165.1 [65.6, 346.0] | 459.8 [292.8, 677.3] | 334.5 [132.7, 738.0] |

Scenario S1. Mean over 1000 replicates [2.5th, 97.5th percentile].
