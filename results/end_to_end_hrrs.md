# End-to-end DSDA to HRRS (1000 replicates; mean [2.5th, 97.5th percentile])

Reference 1 (registry) and Reference 2 (simulated truth) coincide at kilometre level.

## S0, sigma = 150 m, Cs = 0.85

| Statistic | A accepted-only | B fail-safe hybrid | C ungated best-candidate |
|---|---|---|---|
| Records located (of 82) | 13.8 [9.0, 18.0] | 82.0 [82.0, 82.0] | 82.0 [82.0, 82.0] |
| Rank of HRRS-2 by rate | 3.95 [3.00, 4.00] | 1.00 [1.00, 1.00] | 1.00 [1.00, 1.00] |
| HRRS-2 macro Tier 1 (%) | 0.0 [0.0, 0.0] | 100.0 [100.0, 100.0] | 100.0 [100.0, 100.0] |
| HRRS-2 Tier 1 (%) | 0.0 [0.0, 0.0] | 100.0 [100.0, 100.0] | 100.0 [100.0, 100.0] |
| HRRS-1 Tier 1, false positive (%) | 6.4 [0.0, 100.0] | 0.0 [0.0, 0.0] | 0.0 [0.0, 0.0] |
| HRRS-3 Tier 1, false positive (%) | 77.1 [0.0, 100.0] | 0.0 [0.0, 0.0] | 0.5 [0.0, 0.0] |
| PK 41 first by OSS (%) | 45.8 [0.0, 100.0] | 100.0 [100.0, 100.0] | 100.0 [100.0, 100.0] |
| PK 41 permutation p < 0.05 (%) | 15.3 [0.0, 100.0] | 100.0 [100.0, 100.0] | 100.0 [100.0, 100.0] |
| Recall@3 | 0.22 [0.00, 0.33] | 1.00 [1.00, 1.00] | 1.00 [1.00, 1.00] |
| Recall@4 | 0.20 [0.00, 0.25] | 1.00 [1.00, 1.00] | 1.00 [1.00, 1.00] |
| Recall@5 | 0.18 [0.00, 0.20] | 1.00 [1.00, 1.00] | 0.99 [0.80, 1.00] |
| Jaccard, most likely cluster | 0.18 [0.00, 0.20] | 1.00 [1.00, 1.00] | 1.00 [1.00, 1.00] |
| OSS share in top 3 km (%) | 22.9 [11.1, 28.7] | 52.2 [52.2, 52.2] | 52.2 [52.2, 52.2] |
| OSS share in top 5 km (%) | 31.7 [13.8, 35.1] | 75.6 [75.6, 75.6] | 75.5 [72.0, 75.6] |
| Spearman, OSS profile | 0.20 [-0.04, 0.32] | 1.00 [1.00, 1.00] | 1.00 [0.95, 1.00] |
| Crashes in a wrong PK (%) | 0.0 [0.0, 0.0] | 0.0 [0.0, 0.0] | 1.3 [0.0, 3.7] |
| Crashes in a wrong segment (%) | 0.0 [0.0, 0.0] | 0.0 [0.0, 0.0] | 0.0 [0.0, 0.0] |
| Half-km accuracy, all 82 (%) | n/a | 52.7 [48.8, 56.7] | 56.9 [46.3, 67.1] |
| Half-km accuracy, accepted (%) | 66.1 [41.6, 90.9] | n/a | n/a |
| Accepted records in HRRS-2 (of 33) | 0.0 [0.0, 0.0] | n/a | n/a |

| Planted hotspot (10 crashes) | Planted accepted (%) | Recovered, policy B (%) | Recovered, policy C (%) | Recovered, nominal PK (%) |
|---|---|---|---|---|
| v1: unnamed junction, PK 34.26 | 0.0 [0.0, 0.0] | 0.0 [0.0, 0.0] | 100.0 [100.0, 100.0] | 40.7 [0.0, 100.0] |
| v2: named building, PK 34.94 | 0.0 [0.0, 0.0] | 0.0 [0.0, 0.0] | 100.0 [100.0, 100.0] | 46.8 [0.0, 100.0] |

## S1, sigma = 150 m, Cs = 0.85

| Statistic | A accepted-only | B fail-safe hybrid | C ungated best-candidate |
|---|---|---|---|
| Records located (of 82) | 10.0 [5.0, 15.0] | 78.5 [75.0, 82.0] | 81.7 [80.0, 82.0] |
| Rank of HRRS-2 by rate | 3.85 [3.00, 4.00] | 1.00 [1.00, 1.00] | 1.00 [1.00, 1.00] |
| HRRS-2 macro Tier 1 (%) | 0.0 [0.0, 0.0] | 18.1 [0.0, 100.0] | 18.1 [0.0, 100.0] |
| HRRS-2 Tier 1 (%) | 0.0 [0.0, 0.0] | 100.0 [100.0, 100.0] | 97.3 [0.0, 100.0] |
| HRRS-1 Tier 1, false positive (%) | 6.7 [0.0, 100.0] | 0.1 [0.0, 0.0] | 0.1 [0.0, 0.0] |
| HRRS-3 Tier 1, false positive (%) | 52.1 [0.0, 100.0] | 3.4 [0.0, 100.0] | 6.9 [0.0, 100.0] |
| PK 41 first by OSS (%) | 40.0 [0.0, 100.0] | 63.1 [0.0, 100.0] | 64.8 [0.0, 100.0] |
| PK 41 permutation p < 0.05 (%) | 6.1 [0.0, 100.0] | 83.0 [0.0, 100.0] | 83.0 [0.0, 100.0] |
| Recall@3 | 0.21 [0.00, 0.33] | 0.86 [0.67, 1.00] | 0.85 [0.67, 1.00] |
| Recall@4 | 0.19 [0.00, 0.25] | 0.94 [0.75, 1.00] | 0.93 [0.75, 1.00] |
| Recall@5 | 0.16 [0.00, 0.20] | 0.96 [0.80, 1.00] | 0.92 [0.60, 1.00] |
| Jaccard, most likely cluster | 0.14 [0.00, 0.25] | 0.99 [0.80, 1.00] | 0.98 [0.67, 1.00] |
| OSS share in top 3 km (%) | 22.2 [10.0, 28.7] | 50.8 [43.8, 52.2] | 50.4 [37.5, 52.2] |
| OSS share in top 5 km (%) | 29.6 [11.8, 35.1] | 74.2 [63.6, 75.6] | 72.3 [60.9, 75.6] |
| Spearman, OSS profile | 0.19 [-0.07, 0.33] | 0.97 [0.87, 1.00] | 0.95 [0.84, 1.00] |
| Crashes in a wrong PK (%) | 1.6 [0.0, 14.3] | 4.9 [1.2, 10.0] | 9.6 [3.7, 16.0] |
| Crashes in a wrong segment (%) | 0.1 [0.0, 0.0] | 1.2 [0.0, 3.9] | 3.7 [0.0, 8.5] |
| Half-km accuracy, all 82 (%) | n/a | 47.4 [42.7, 51.8] | 49.9 [39.0, 61.0] |
| Half-km accuracy, accepted (%) | 64.4 [33.3, 93.9] | n/a | n/a |
| Accepted records in HRRS-2 (of 33) | 0.0 [0.0, 0.0] | n/a | n/a |

| Planted hotspot (10 crashes) | Planted accepted (%) | Recovered, policy B (%) | Recovered, policy C (%) | Recovered, nominal PK (%) |
|---|---|---|---|---|
| v1: unnamed junction, PK 34.26 | 0.0 [0.0, 0.0] | 0.0 [0.0, 0.0] | 100.0 [100.0, 100.0] | 45.9 [0.0, 100.0] |
| v2: named building, PK 34.94 | 0.1 [0.0, 0.0] | 0.0 [0.0, 0.0] | 99.1 [100.0, 100.0] | 41.2 [0.0, 100.0] |

## S2, sigma = 150 m, Cs = 0.85

| Statistic | A accepted-only | B fail-safe hybrid | C ungated best-candidate |
|---|---|---|---|
| Records located (of 82) | 7.0 [3.0, 12.0] | 74.6 [69.0, 79.0] | 81.5 [80.0, 82.0] |
| Rank of HRRS-2 by rate | 3.67 [2.00, 4.00] | 1.00 [1.00, 1.00] | 1.00 [1.00, 1.00] |
| HRRS-2 macro Tier 1 (%) | 0.0 [0.0, 0.0] | 4.6 [0.0, 100.0] | 4.6 [0.0, 100.0] |
| HRRS-2 Tier 1 (%) | 0.0 [0.0, 0.0] | 99.4 [100.0, 100.0] | 96.7 [0.0, 100.0] |
| HRRS-1 Tier 1, false positive (%) | 4.3 [0.0, 100.0] | 0.3 [0.0, 0.0] | 1.4 [0.0, 0.0] |
| HRRS-3 Tier 1, false positive (%) | 34.0 [0.0, 100.0] | 10.6 [0.0, 100.0] | 13.4 [0.0, 100.0] |
| PK 41 first by OSS (%) | 33.8 [0.0, 100.0] | 45.9 [0.0, 100.0] | 47.6 [0.0, 100.0] |
| PK 41 permutation p < 0.05 (%) | 2.7 [0.0, 100.0] | 67.0 [0.0, 100.0] | 68.0 [0.0, 100.0] |
| Recall@3 | 0.19 [0.00, 0.33] | 0.79 [0.33, 1.00] | 0.77 [0.33, 1.00] |
| Recall@4 | 0.16 [0.00, 0.25] | 0.88 [0.50, 1.00] | 0.85 [0.50, 1.00] |
| Recall@5 | 0.14 [0.00, 0.20] | 0.91 [0.60, 1.00] | 0.83 [0.60, 1.00] |
| Jaccard, most likely cluster | 0.12 [0.00, 0.25] | 0.98 [0.80, 1.00] | 0.96 [0.67, 1.00] |
| OSS share in top 3 km (%) | 20.4 [8.4, 28.7] | 49.5 [34.4, 52.2] | 47.6 [31.3, 52.2] |
| OSS share in top 5 km (%) | 25.8 [8.5, 35.1] | 71.9 [57.3, 75.6] | 68.3 [51.5, 75.6] |
| Spearman, OSS profile | 0.17 [-0.09, 0.33] | 0.94 [0.80, 0.99] | 0.89 [0.70, 0.99] |
| Crashes in a wrong PK (%) | 3.7 [0.0, 25.0] | 9.6 [2.9, 16.5] | 17.5 [9.8, 25.9] |
| Crashes in a wrong segment (%) | 0.4 [0.0, 10.0] | 2.5 [0.0, 6.7] | 7.4 [2.4, 13.4] |
| Half-km accuracy, all 82 (%) | n/a | 42.4 [37.2, 47.6] | 43.9 [32.9, 54.9] |
| Half-km accuracy, accepted (%) | 62.7 [20.0, 100.0] | n/a | n/a |
| Accepted records in HRRS-2 (of 33) | 0.0 [0.0, 0.0] | n/a | n/a |

| Planted hotspot (10 crashes) | Planted accepted (%) | Recovered, policy B (%) | Recovered, policy C (%) | Recovered, nominal PK (%) |
|---|---|---|---|---|
| v1: unnamed junction, PK 34.26 | 0.0 [0.0, 0.0] | 0.0 [0.0, 0.0] | 99.7 [100.0, 100.0] | 45.2 [0.0, 100.0] |
| v2: named building, PK 34.94 | 0.4 [0.0, 10.0] | 0.0 [0.0, 0.0] | 92.4 [0.0, 100.0] | 38.5 [0.0, 100.0] |

## S0, sigma = 350 m, Cs = 0.85

| Statistic | A accepted-only | B fail-safe hybrid | C ungated best-candidate |
|---|---|---|---|
| Records located (of 82) | 25.2 [20.0, 30.0] | 82.0 [82.0, 82.0] | 82.0 [82.0, 82.0] |
| Rank of HRRS-2 by rate | 4.00 [4.00, 4.00] | 1.00 [1.00, 1.00] | 1.00 [1.00, 1.00] |
| HRRS-2 macro Tier 1 (%) | 0.0 [0.0, 0.0] | 100.0 [100.0, 100.0] | 100.0 [100.0, 100.0] |
| HRRS-2 Tier 1 (%) | 0.0 [0.0, 0.0] | 100.0 [100.0, 100.0] | 100.0 [100.0, 100.0] |
| HRRS-1 Tier 1, false positive (%) | 1.2 [0.0, 0.0] | 0.0 [0.0, 0.0] | 0.0 [0.0, 0.0] |
| HRRS-3 Tier 1, false positive (%) | 37.2 [0.0, 100.0] | 0.0 [0.0, 0.0] | 0.5 [0.0, 0.0] |
| PK 41 first by OSS (%) | 99.2 [100.0, 100.0] | 100.0 [100.0, 100.0] | 100.0 [100.0, 100.0] |
| PK 41 permutation p < 0.05 (%) | 75.9 [0.0, 100.0] | 100.0 [100.0, 100.0] | 100.0 [100.0, 100.0] |
| Recall@3 | 0.33 [0.33, 0.33] | 1.00 [1.00, 1.00] | 1.00 [1.00, 1.00] |
| Recall@4 | 0.25 [0.25, 0.25] | 1.00 [1.00, 1.00] | 1.00 [1.00, 1.00] |
| Recall@5 | 0.31 [0.20, 0.40] | 1.00 [1.00, 1.00] | 0.99 [0.80, 1.00] |
| Jaccard, most likely cluster | 0.06 [0.00, 0.40] | 1.00 [1.00, 1.00] | 1.00 [1.00, 1.00] |
| OSS share in top 3 km (%) | 29.1 [25.8, 34.4] | 52.2 [52.2, 52.2] | 52.2 [52.2, 52.2] |
| OSS share in top 5 km (%) | 38.6 [33.2, 42.7] | 75.6 [75.6, 75.6] | 75.5 [72.0, 75.6] |
| Spearman, OSS profile | 0.29 [0.20, 0.35] | 1.00 [1.00, 1.00] | 1.00 [0.95, 1.00] |
| Crashes in a wrong PK (%) | 0.0 [0.0, 0.0] | 0.0 [0.0, 0.0] | 1.3 [0.0, 3.7] |
| Crashes in a wrong segment (%) | 0.0 [0.0, 0.0] | 0.0 [0.0, 0.0] | 0.0 [0.0, 0.0] |
| Half-km accuracy, all 82 (%) | n/a | 59.0 [54.3, 64.0] | 58.6 [48.8, 68.3] |
| Half-km accuracy, accepted (%) | 79.3 [63.0, 94.7] | n/a | n/a |
| Accepted records in HRRS-2 (of 33) | 0.0 [0.0, 0.0] | n/a | n/a |

| Planted hotspot (10 crashes) | Planted accepted (%) | Recovered, policy B (%) | Recovered, policy C (%) | Recovered, nominal PK (%) |
|---|---|---|---|---|
| v1: unnamed junction, PK 34.26 | 0.0 [0.0, 0.0] | 0.0 [0.0, 0.0] | 100.0 [100.0, 100.0] | 40.7 [0.0, 100.0] |
| v2: named building, PK 34.94 | 0.0 [0.0, 0.0] | 0.0 [0.0, 0.0] | 100.0 [100.0, 100.0] | 46.8 [0.0, 100.0] |

## S1, sigma = 350 m, Cs = 0.85

| Statistic | A accepted-only | B fail-safe hybrid | C ungated best-candidate |
|---|---|---|---|
| Records located (of 82) | 17.7 [12.0, 24.0] | 78.5 [75.0, 82.0] | 81.7 [80.0, 82.0] |
| Rank of HRRS-2 by rate | 3.99 [4.00, 4.00] | 1.00 [1.00, 1.00] | 1.00 [1.00, 1.00] |
| HRRS-2 macro Tier 1 (%) | 0.0 [0.0, 0.0] | 18.1 [0.0, 100.0] | 18.1 [0.0, 100.0] |
| HRRS-2 Tier 1 (%) | 0.0 [0.0, 0.0] | 100.0 [100.0, 100.0] | 96.6 [0.0, 100.0] |
| HRRS-1 Tier 1, false positive (%) | 6.4 [0.0, 100.0] | 0.1 [0.0, 0.0] | 0.1 [0.0, 0.0] |
| HRRS-3 Tier 1, false positive (%) | 37.0 [0.0, 100.0] | 3.4 [0.0, 100.0] | 7.9 [0.0, 100.0] |
| PK 41 first by OSS (%) | 89.9 [0.0, 100.0] | 63.1 [0.0, 100.0] | 64.8 [0.0, 100.0] |
| PK 41 permutation p < 0.05 (%) | 35.8 [0.0, 100.0] | 83.0 [0.0, 100.0] | 83.0 [0.0, 100.0] |
| Recall@3 | 0.32 [0.00, 0.33] | 0.86 [0.67, 1.00] | 0.85 [0.67, 1.00] |
| Recall@4 | 0.24 [0.25, 0.25] | 0.94 [0.75, 1.00] | 0.93 [0.75, 1.00] |
| Recall@5 | 0.30 [0.20, 0.40] | 0.96 [0.80, 1.00] | 0.91 [0.60, 1.00] |
| Jaccard, most likely cluster | 0.08 [0.00, 0.40] | 0.99 [0.80, 1.00] | 0.98 [0.67, 1.00] |
| OSS share in top 3 km (%) | 28.2 [18.5, 34.4] | 50.8 [43.8, 52.2] | 50.4 [37.5, 52.2] |
| OSS share in top 5 km (%) | 37.4 [30.5, 42.7] | 74.2 [63.6, 75.6] | 72.2 [60.9, 75.6] |
| Spearman, OSS profile | 0.27 [0.13, 0.38] | 0.97 [0.87, 1.00] | 0.94 [0.84, 1.00] |
| Crashes in a wrong PK (%) | 1.2 [0.0, 8.3] | 4.9 [1.2, 10.0] | 9.7 [3.7, 17.1] |
| Crashes in a wrong segment (%) | 0.2 [0.0, 4.6] | 1.2 [0.0, 3.9] | 3.7 [0.0, 8.5] |
| Half-km accuracy, all 82 (%) | n/a | 51.4 [45.7, 56.7] | 51.1 [40.2, 62.2] |
| Half-km accuracy, accepted (%) | 76.7 [53.8, 94.5] | n/a | n/a |
| Accepted records in HRRS-2 (of 33) | 0.0 [0.0, 0.0] | n/a | n/a |

| Planted hotspot (10 crashes) | Planted accepted (%) | Recovered, policy B (%) | Recovered, policy C (%) | Recovered, nominal PK (%) |
|---|---|---|---|---|
| v1: unnamed junction, PK 34.26 | 0.0 [0.0, 0.0] | 0.0 [0.0, 0.0] | 100.0 [100.0, 100.0] | 45.9 [0.0, 100.0] |
| v2: named building, PK 34.94 | 3.5 [0.0, 20.0] | 28.3 [0.0, 100.0] | 99.1 [100.0, 100.0] | 41.2 [0.0, 100.0] |

## S2, sigma = 350 m, Cs = 0.85

| Statistic | A accepted-only | B fail-safe hybrid | C ungated best-candidate |
|---|---|---|---|
| Records located (of 82) | 12.0 [6.0, 19.0] | 74.6 [69.0, 79.0] | 81.5 [80.0, 82.0] |
| Rank of HRRS-2 by rate | 3.94 [3.00, 4.00] | 1.00 [1.00, 1.00] | 1.00 [1.00, 1.00] |
| HRRS-2 macro Tier 1 (%) | 0.0 [0.0, 0.0] | 4.6 [0.0, 100.0] | 4.6 [0.0, 100.0] |
| HRRS-2 Tier 1 (%) | 0.0 [0.0, 0.0] | 99.4 [100.0, 100.0] | 95.2 [0.0, 100.0] |
| HRRS-1 Tier 1, false positive (%) | 5.5 [0.0, 100.0] | 0.3 [0.0, 0.0] | 1.4 [0.0, 0.0] |
| HRRS-3 Tier 1, false positive (%) | 24.7 [0.0, 100.0] | 10.6 [0.0, 100.0] | 14.4 [0.0, 100.0] |
| PK 41 first by OSS (%) | 74.1 [0.0, 100.0] | 45.9 [0.0, 100.0] | 47.6 [0.0, 100.0] |
| PK 41 permutation p < 0.05 (%) | 16.9 [0.0, 100.0] | 67.0 [0.0, 100.0] | 68.0 [0.0, 100.0] |
| Recall@3 | 0.30 [0.00, 0.33] | 0.79 [0.33, 1.00] | 0.77 [0.33, 1.00] |
| Recall@4 | 0.23 [0.00, 0.25] | 0.88 [0.50, 1.00] | 0.85 [0.50, 1.00] |
| Recall@5 | 0.28 [0.20, 0.40] | 0.91 [0.60, 1.00] | 0.82 [0.60, 1.00] |
| Jaccard, most likely cluster | 0.08 [0.00, 0.40] | 0.98 [0.80, 1.00] | 0.96 [0.67, 1.00] |
| OSS share in top 3 km (%) | 26.7 [11.1, 34.4] | 49.5 [34.4, 52.2] | 47.6 [31.3, 52.2] |
| OSS share in top 5 km (%) | 35.1 [21.3, 42.7] | 71.9 [57.3, 75.6] | 68.2 [51.5, 75.6] |
| Spearman, OSS profile | 0.25 [0.04, 0.40] | 0.94 [0.80, 0.99] | 0.89 [0.70, 0.99] |
| Crashes in a wrong PK (%) | 2.7 [0.0, 15.4] | 9.6 [2.9, 16.5] | 17.7 [9.8, 26.8] |
| Crashes in a wrong segment (%) | 0.4 [0.0, 7.7] | 2.5 [0.0, 6.7] | 7.4 [2.4, 13.4] |
| Half-km accuracy, all 82 (%) | n/a | 44.9 [39.0, 50.6] | 44.8 [34.1, 56.1] |
| Half-km accuracy, accepted (%) | 74.2 [46.7, 100.0] | n/a | n/a |
| Accepted records in HRRS-2 (of 33) | 0.0 [0.0, 0.0] | n/a | n/a |

| Planted hotspot (10 crashes) | Planted accepted (%) | Recovered, policy B (%) | Recovered, policy C (%) | Recovered, nominal PK (%) |
|---|---|---|---|---|
| v1: unnamed junction, PK 34.26 | 0.0 [0.0, 0.0] | 0.0 [0.0, 0.0] | 99.7 [100.0, 100.0] | 45.2 [0.0, 100.0] |
| v2: named building, PK 34.94 | 4.8 [0.0, 20.0] | 33.5 [0.0, 100.0] | 92.4 [0.0, 100.0] | 38.5 [0.0, 100.0] |
