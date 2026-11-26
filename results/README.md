# Testbed outputs (RR27, controlled OpenStreetMap testbed)

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
