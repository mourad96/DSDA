# Testbed QA report

- Route ways matched (^(RR|MC|C|RL|R)\s*-?\s*27$): 93; centerline length 26.68 km; share of centerline edges on tagged route ways: 93.8%.
- Check anchor PK 36.300 (mazraa): no OSM place of that name.
- Check anchor PK 31.240 (Maâmoura, 1470 m from RR27): unit-scale PK at its projection 28.592 (difference -2.648 km); ratio to origin 2.664 PK-km per OSM-km  << outside QA range.
- Check anchor PK 33.080 (hydraulic structure): nearest OSM structure way/208559838 (waterway stream) at unit-scale PK 33.841 (761 m, beyond the 300 m tolerance).
- Check anchor PK 33.560 (hydraulic structure): nearest OSM structure way/208559838 (waterway stream) at unit-scale PK 33.841 (281 m).
- Calibration (protocol v1.1): PK = 27.000 + (s - 4463.0 m) / 1000.
- Junctions on the centerline: 191 (19 with a named or numbered crossing road).
- Named features within 700 m: 508; indexable (road vertex within 150 m): 505.
- Municipal places (city/town/village): 10.
- Registry: 83 records, 31 intersection crashes (cause-based flag agrees with selectin on 83/83 records).
- Registry PK range 26.5 to 43.5 maps to chainage 3963 to 20963 m on a 26677 m centerline.
- GIS layer: 539 candidate nodes (250 on RR27).
- scripts/run_ablation.py on the exported replicate-0 files reproduces the in-process acceptance counts of scenario S1 (Nominal LRS PK only: 44, Toponymy only: 26, Without topology: 14, Without proximity: 21, Full DSDA: 14).

## Calibration anchors (protocol v1.1)

| PK | Kind | Role | OSM element | Name | Offset (m) | Chainage (m) | Unit-scale PK |
|---|---|---|---|---|---|---|---|
| 27.000 | place | origin | node/1128018620 | Béni Khiar | 6.8 | 4463.0 | 27.000 |
| 31.240 | place | check | node/1865629269 | Maâmoura | 1470.2 | 6054.9 | 28.592 |
| 33.080 | hydraulic | check (not matched) | way/208559838 (waterway stream) |  | 761.0 | 11304.1 | 33.841 |
| 33.560 | hydraulic | check | way/208559838 (waterway stream) |  | 281.0 | 11304.1 | 33.841 |

## Structural properties of the simulated corpus (mean [2.5, 97.5] over 1000 replicates)

- Records without any named feature within 300 m of the true position: 48.5 [44.0, 53.0] of 83
- Records whose true position lies more than 151.6 m from their recorded PK post (beyond the radius where Cs >= 0.85 is reachable in LRS-anchored mode): 59.4 [52.0, 67.0] of 83
