| Configuration | Weights (w1, w2, w3) | Automated throughput | Conditional mean E_geo (m) | Inclusive mean E_geo (m) | Conditional P90 (m) | Inclusive n | Conditional P95 (m) | Inclusive RMSE (m) |
|---|---|---|---|---|---|---|---|---|
| Nominal LRS PK only (proximity baseline) | (0.000, 1.000, 0.000) | 44/83 (53.0%) | 284.5 | 274.2 | 501.7 | 77 | 534.4 | 361.3 |
| Toponymy only (no proximity, no topology) | (1.000, 0.000, 0.000) | 26/83 (31.3%) | 96.2 | 488.6 | 180.6 | 83 | 305.5 | 1242.9 |
| Without topology (S_top + S_prox) | (0.571, 0.429, 0.000) | 14/83 (16.9%) | 99.7 | 506.9 | 297.4 | 83 | 393.6 | 1245.2 |
| Without proximity (S_top + S_topo) | (0.800, 0.000, 0.200) | 21/83 (25.3%) | 104.3 | 490.3 | 271.8 | 83 | 345.8 | 1242.6 |
| Full DSDA | (0.500, 0.375, 0.125) | 14/83 (16.9%) | 99.7 | 503.2 | 297.4 | 83 | 393.6 | 1246.6 |
