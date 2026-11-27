# RR27 study protocol, version 1.3 (DSDA testbed and frozen HRRS screening)

Frozen on 27 November 2026, before any simulation under this version was run.
Version 1.3 implements the specification of 27 November 2026 (L. Touiti):
the study is restricted to the 82 injury crashes of RR27 and traces how the
uncertainty of integer PKs propagates from DSDA to HRRS screening. It is labelled
1.3 because versions 1.0 to 1.2 of the testbed protocol already exist
(`testbed/PROTOCOL.md`); their results remain archived in `results/`.
Any later change requires a new version number and is reported with the results.

## 1. Data

- Crashes: `data/rr27_82_anonymized.csv` (id, year, pk, fatalities, injured,
  oss), the 82 injury crashes of the RR27 registry with PK 27 to 42, years 2007 to
  2015 (Y = 9). The single record at PK 43 is excluded. OSS_i = 10 F_i + I_i.
  26 crashes are fatal. No other registry field is used.
- Road network: OpenStreetMap extract of 2026-11-23T20:02:34Z
  (`data/osm/rr27_corridor_2026-11-23.json.gz`, ODbL), RR27 centerline and
  calibration as in version 1.1: PK = 27.000 + (s - s_BK) / 1000.
- Corridor axis: one PK post = 1.0 km; the 16 one-kilometre bins
  [n - 0.5, n + 0.5) for n = 27 to 42 form the continuous axis [26.5, 42.5).
- Traffic: AADT 18,375 veh/day (PK 27 to 31), 16,849 (PK 32 to 36), 16,451
  (PK 37 to 42); exposure E_k = AADT x 365 x 9 x 1 km, in 1e8 veh-km.

## 2. Simulated positions and reports (DSDA testbed)

- True position of crash i with registry PK n: PK uniform on [n - 0.5, n + 0.5),
  mapped to the centerline. Seeds: 2026 + r (positions), 2026 + 1,000,000 + r
  (report degradations), 2026 + 2,000,000 + r (gazetteer gaps), 2026 + 3,000,000 + r
  (planted hotspot), r = 0 to 999.
- Junction indicator (replaces the cause-based proxy of versions 1.1 and 1.2):
  is_junction_true = 1 when the true position lies within 30 m of a junction
  node (centerline vertex shared with another drivable OSM way).
- Reported junction flag: S0 exact; S1 omission rate 0.10 (true junction
  reported as non-junction) and false-positive rate 0.05; S2 0.20 and 0.10.
- Landmark cited by the report: for a junction crash whose nearest junction
  (within 30 m) has a named or numbered crossing road, that name; otherwise the
  nearest named OSM feature within 300 m of the true position; otherwise none.
- Other degradations, unchanged from version 1.1 (S0 / S1 / S2): landmark
  omitted 0 / 0.15 / 0.30; wrong landmark 0 / 0.05 / 0.10; spelling variant
  0 / 0.25 / 0.50; PK recorded one km off 0 / 0.05 / 0.10; PK missing
  0 / 0.05 / 0.10; feature missing from the gazetteer 0 / 0.10 / 0.20. Uniform
  draws are shared across scenarios, so that S0, S1 and S2 are nested.
- No empirical error rates exist for these reports: all rates are assumptions.

## 3. DSDA configurations (Task 1)

Initial parameters, frozen: w = (0.500, 0.375, 0.125), sigma = 150 m,
R_max = 500 m, gate Cs >= 0.85.

| Configuration | Definition |
|---|---|
| Full DSDA, junction pass ON (reference) | reported junction flag used (w1 <- w1 + w3, w3 <- 0) |
| Full DSDA, junction pass OFF | reported flag ignored |
| Toponymy only | w = (1, 0, 0) |
| Without topology | w = (0.571, 0.429, 0) |
| Without proximity | w = (0.8, 0, 0.2) |
| Nominal LRS PK only (principal baseline) | w = (0, 1, 0), records without a PK rejected |
| Nominal PK post (no geocoding) | position = k_PK of the reported PK |
| Municipality centroid (secondary baseline) | position = nearest OSM city, town or village |

Output `results/ablation_v1_3.csv`: for each scenario and configuration,
throughput (n/82), conditional mean, median, P90, P95 of E_geo, accepted records
with E_geo > 150 m, inclusive mean, P90, P95, RMSE, maximum; mean over 1,000
replicates with the 2.5th and 97.5th percentiles and the number of replicates in
which each statistic is defined.

## 4. Post hoc sensitivity on (sigma, Cs) (Task 2)

(sigma = 150 m, Cs = 0.85) stays the pre-specified configuration. Post hoc grid:
sigma in {150, 250, 350} m crossed with Cs in {0.70, 0.75, 0.80, 0.85, 0.90,
0.95} on S1, and sigma in {150, 250, 350} m at Cs = 0.85 on S0 and S2 (Full DSDA,
junction pass ON). Output `results/sensitivity_sigma_cs.csv`, same statistics as
section 3. The sigma carried into Task 3, declared before the grid is run, is
the one that minimises, on S1 at Cs = 0.85, the mean positional error of
policy B (section 6); ties go to the smaller sigma. It is a post hoc choice on the
same simulated data and is reported as such.

## 5. Frozen HRRS screening (`dsda/hrrs.py`)

- Segments: HRRS-1 PK 27 to 32 (6 km), HRRS-2 PK 33 to 35 (3 km), HRRS-3 PK 36
  to 40 (5 km), HRRS-4 PK 41 to 42 (2 km).
- Macro scale: T_s = n_s / E_s; T_c,s = T_mean + 1.645 sqrt(T_mean / E_s)
  + 1 / (2 E_s) with T_mean = 9.08 (registry corridor mean, kept fixed);
  exact 95 % Poisson bounds [LCB_95, UCB_95].
- Micro scale, every contiguous window of 1 to 5 bins (70 windows), adjusted p
  from the Monte Carlo distribution of the maximum statistic:
  Poisson frequency scan (Kulldorff log-likelihood ratio, expected counts
  proportional to E_k; also run on the 26 fatal crashes); OSS randomisation scan
  (positions redrawn proportionally to E_k, OSS_i kept); conditional permutation
  scan (positions fixed, OSS_i permuted). Both OSS scans use the standardised
  window excess with its exact null mean and variance.
- Clusters as in SaTScan: most likely cluster, then non-overlapping secondary
  clusters; a cluster is attributed to the segment(s) holding at least half of
  its length.
- Tier 1: LCB_95 > T_c,s, or a cluster with adjusted p < 0.05 (frequency or an
  OSS scan) attributed to the segment. Tier 3: UCB_95 < T_c,s and no such
  cluster. Tier 2: otherwise.
- PK 41 severity vigilance: PK 41 ranked first by OSS (ties: count, then PK),
  raw conditional-permutation p of its one-kilometre window.
- Monte Carlo draws: 10,000 (seed 2026) for the stage-2 audit (Task 4); in each
  replicate of Task 3, 10,000 for the frequency scan (null cached by number of
  crashes) and 2,000 for the two OSS scans.

## 6. End-to-end DSDA to HRRS (Task 3)

DSDA outputs (S0, S1, S2; sigma = 150 m and the sigma of section 4; Cs = 0.85)
are fed to the frozen HRRS module. A DSDA position is the chainage of the
selected node projected on the RR27 centerline; positions outside [26.5, 42.5)
are out of the corridor (excluded, counted).

- Policy A (accepted only): accepted records only. Empty or constant inputs give
  Tier 1 detection 0 and undefined correlations, which are counted.
- Policy B (fail-safe hybrid): accepted DSDA position, otherwise the nominal
  post of the reported PK; rejected records without a reported PK are excluded
  (counted).
- Policy C (ungated): best candidate for every record with a candidate.
- Reference 1: registry integer PKs. Reference 2: simulated true continuous
  positions. Because each PK interval is exactly one bin, the two references
  coincide for every kilometre-level statistic; they differ for half-kilometre
  statistics.

Statistics per replicate (mean and [2.5 %, 97.5 %] over 1,000 replicates, with
the number of replicates where defined), in `results/end_to_end_hrrs.csv`:
(a) rank of HRRS-2 by T_s among the four segments and share of replicates where
HRRS-2 is macro Tier 1 (LCB_95 > T_c,s) and Tier 1 overall; (b) share of
replicates where PK 41 ranks first by OSS, where its raw permutation p < 0.05,
and where HRRS-1 or HRRS-3 is classified Tier 1 (false positives against the
reference classification); (c) Recall@k, k = 3, 4, 5: overlap of the policy's top
k kilometres by OSS with the reference top k; (d) Jaccard index between the most
likely frequency cluster of the policy and of the reference, as intervals of the
continuous axis; (e) share of total OSS whose true position lies in the policy's
top k kilometres; (f) share of located crashes placed in a wrong integer PK and
in a wrong HRRS segment; Spearman correlation of the OSS-per-kilometre profiles.

Sub-kilometre resolution: (a) half_km_accuracy, the share of crashes placed in
the correct 500 m bin (32 bins), for policies B and C and for accepted records,
against the 50 % of an uninformative position within the correct kilometre;
(b) planted_hotspot_test: 10 crashes added within +/- 25 m (along the
centerline) of the named, indexable OSM feature whose projection is nearest to
PK 34.0 within [33.5, 34.5); recorded PK = nearest integer; same report model
and degradations. Recovery: the 500 m bin containing the feature ranks strictly
first by crash count among the 32 bins (82 + 10 crashes). Compared for policies
B and C and for the nominal PK (position uniform within the reported kilometre).

## 7. Stage-2 audit on the registry (Task 4)

`scripts/hrrs_stage2_audit.py`: section 5 applied to the 82 registry crashes
(10,000 draws, seed 2026), the fatal-crash scan, and the prospective holdout
2007 to 2011 against 2012 to 2015 (raw frequency, rate, best 3 km sliding window,
OSS by kilometre). Output `results/hrrs_stage2_audit.csv`.

## 8. Limitations stated in advance

Positions and reports are simulated. Landmarks, junctions and the GIS gazetteer
come from the same OSM source, which favours DSDA (same-source circularity).
The OSM extract dates from 2026, the crashes from 2007 to 2015; part of RR27 is
now a dual carriageway, and the PK calibration rests on a single origin. If
the HRRS segments were delineated after inspection of the registry, their
macro-scale test is descriptive and the confirmatory evidence is the
multiplicity-adjusted scan.
