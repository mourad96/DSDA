# Testbed outputs (RR27, controlled OpenStreetMap testbed)

## Protocol v1.3 (82 crashes, DSDA to HRRS; `testbed/PROTOCOL_v1.3.md`)

- `ablation_v1_3.csv` / `.md` (Task 1): DSDA configurations and baselines, S0/S1/S2,
  1,000 replicates; `testbed_v13_manifest.json` holds hashes, seeds, code commit and the
  planted-hotspot anchors.
- `sensitivity_sigma_cs.csv` / `.md` (Task 2): post hoc grid sigma x Cs gate;
  `sensitivity_best_sigma.json` records the sigma chosen by the declared rule.
- `end_to_end_hrrs.csv` / `.md` (Task 3): HRRS screening of DSDA outputs under
  policies A, B and C against the registry, sub-kilometre tests.
- `hrrs_stage2_audit.csv` / `.md` (Task 4): stage-2 audit of the 82 registry crashes.

All CSV files are in long format with the mean, the 2.5th and 97.5th percentiles over
replicates and the number of replicates where the statistic is defined.

## Protocols v1.1 and v1.2 (earlier testbed tables)

Outputs of `scripts/osm_testbed.py` on the OSM extract of 2026-11-23T20:02:34Z
(see `manifest.json` in each folder for file hashes, seeds and code commit).

- `testbed_RR27_v1.2/`: reference results (protocol v1.2; 9 intersection crashes
  read from the detailed cause field).
- `testbed_RR27_v1.1/`: sensitivity analysis (protocol v1.1; the 31 records of the
  coded category "Non respect priorite, feux, stop" treated as intersection crashes).

Each folder holds `table5_testbed`, `tableC1_testbed`, `tableC2_testbed`,
`tableD2_testbed` (CSV and Markdown, S0 and S2 companions for D.2),
`qa_report.md`, `manifest.json`, `replicates.csv.gz` (one row per scenario,
replicate and configuration) and `S1_r0/` (input files of scenario S1,
replicate 0, with the output of `scripts/run_ablation.py` on them).
Positions are simulated on the real road graph: these are not field measurements.
The institutional registry itself is not distributed; `S1_r0/events.csv` carries
only the integer PK and the intersection flag of each record.
