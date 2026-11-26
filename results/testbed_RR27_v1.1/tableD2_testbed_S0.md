| Configuration | Weights (w1, w2, w3) | Automated throughput (of 83) | Conditional mean E_geo (m) | Inclusive mean E_geo (m) | Conditional P90 (m) |
|---|---|---|---|---|---|
| Municipality centroid (address-level baseline) | -- | -- | -- | 1682.8 [1647.6, 1717.4] | -- |
| Nominal LRS PK only (proximity baseline) | (0.000, 1.000, 0.000) | 45.0 [45.0, 45.0] | 235.9 [190.6, 277.3] | 265.6 [224.6, 304.9] | 449.5 [390.2, 492.5] |
| Toponymy only (no proximity, no topology) | (1.000, 0.000, 0.000) | 34.0 [29.0, 39.0] | 93.0 [65.6, 131.2] | 213.5 [171.3, 252.5] | 211.4 [152.0, 302.7] |
| Without topology (S_top + S_prox) | (0.571, 0.429, 0.000) | 13.4 [8.0, 18.0] | 139.0 [71.6, 217.3] | 252.6 [209.0, 291.0] | 330.0 [164.9, 487.2] |
| Without proximity (S_top + S_topo) | (0.800, 0.000, 0.200) | 24.7 [20.0, 29.0] | 95.5 [53.0, 149.1] | 214.4 [173.9, 253.1] | 248.0 [143.4, 392.4] |
| Full DSDA | (0.500, 0.375, 0.125) | 12.8 [8.0, 18.0] | 146.5 [72.5, 228.1] | 245.6 [201.6, 286.1] | 337.3 [173.3, 473.4] |

Scenario S0. Mean over 1000 replicates [2.5th, 97.5th percentile].
