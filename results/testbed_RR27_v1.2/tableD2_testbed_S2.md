| Configuration | Weights (w1, w2, w3) | Automated throughput (of 83) | Conditional mean E_geo (m) | Inclusive mean E_geo (m) | Conditional P90 (m) |
|---|---|---|---|---|---|
| Municipality centroid (address-level baseline) | -- | -- | -- | 1680.3 [1644.6, 1713.6] | -- |
| Nominal LRS PK only (proximity baseline) | (0.000, 1.000, 0.000) | 40.2 [34.0, 45.0] | 311.0 [233.7, 394.1] | 338.5 [276.2, 409.7] | 561.1 [420.5, 1004.5] |
| Toponymy only (no proximity, no topology) | (1.000, 0.000, 0.000) | 16.0 [9.0, 23.0] | 148.4 [61.8, 312.1] | 656.8 [412.8, 934.3] | 319.4 [127.2, 817.7] |
| Without topology (S_top + S_prox) | (0.571, 0.429, 0.000) | 7.1 [3.0, 12.0] | 187.1 [38.6, 546.6] (defined in 998/1000) | 667.3 [421.7, 943.6] | 393.4 [72.5, 1309.8] (defined in 998/1000) |
| Without proximity (S_top + S_topo) | (0.800, 0.000, 0.200) | 11.1 [6.0, 17.0] | 167.4 [44.2, 438.3] | 655.3 [411.7, 932.6] | 379.3 [93.3, 1087.2] |
| Full DSDA | (0.500, 0.375, 0.125) | 6.7 [3.0, 12.0] | 198.1 [36.6, 605.2] (defined in 998/1000) | 667.6 [422.9, 943.8] | 408.7 [65.3, 1413.9] (defined in 998/1000) |

Scenario S2. Mean over 1000 replicates [2.5th, 97.5th percentile].
