| Configuration | Weights (w1, w2, w3) | Automated throughput (of 83) | Conditional mean E_geo (m) | Inclusive mean E_geo (m) | Conditional P90 (m) |
|---|---|---|---|---|---|
| Municipality centroid (address-level baseline) | -- | -- | -- | 1680.3 [1644.6, 1713.6] | -- |
| Nominal LRS PK only (proximity baseline) | (0.000, 1.000, 0.000) | 45.0 [45.0, 45.0] | 244.4 [201.6, 288.2] | 268.6 [231.9, 308.2] | 442.2 [387.0, 485.4] |
| Toponymy only (no proximity, no topology) | (1.000, 0.000, 0.000) | 33.8 [29.0, 39.0] | 99.4 [71.6, 135.9] | 218.3 [181.8, 255.0] | 221.4 [158.8, 308.3] |
| Without topology (S_top + S_prox) | (0.571, 0.429, 0.000) | 14.2 [9.0, 19.0] | 139.7 [79.0, 207.5] | 256.0 [218.7, 293.9] | 305.2 [173.4, 432.4] |
| Without proximity (S_top + S_topo) | (0.800, 0.000, 0.200) | 20.8 [16.0, 25.0] | 103.9 [54.3, 163.2] | 219.4 [183.4, 256.2] | 267.9 [136.1, 410.9] |
| Full DSDA | (0.500, 0.375, 0.125) | 13.4 [9.0, 18.0] | 148.9 [83.8, 225.4] | 255.1 [218.0, 293.8] | 313.9 [183.5, 429.6] |

Scenario S0. Mean over 1000 replicates [2.5th, 97.5th percentile].
