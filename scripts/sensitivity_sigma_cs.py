"""Post hoc sensitivity of DSDA to (sigma, Cs gate) (protocol v1.3, section 4; Task 2).

Reads results/_cache/testbed_v13.npz (scripts/testbed_v13.py) and writes
results/sensitivity_sigma_cs.csv and .md. The pre-specified configuration is
sigma = 150 m, Cs = 0.85. The sigma carried into Task 3 is chosen by the rule
declared in the protocol: minimum mean positional error of policy B (accepted
DSDA position, otherwise nominal post of the reported PK) on S1 at Cs = 0.85,
ties to the smaller sigma. It is a post hoc choice.
"""

from __future__ import annotations

import csv
import json
import math
import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
from testbed_v13 import record_metrics, summary  # noqa: E402

GATES_S1 = (0.70, 0.75, 0.80, 0.85, 0.90, 0.95)
PRE_SPECIFIED = (150.0, 0.85)
METRICS = ["accepted", "accepted_pct", "cond_mean", "cond_median", "cond_p90", "cond_p95", "cond_max",
           "accepted_egeo_gt_150", "incl_n", "incl_mean", "incl_max", "policyB_mean_error"]


def replicate_metrics(cs, egeo, post_egeo, gate):
    acc = np.nan_to_num(cs, nan=-1.0) >= gate
    m = record_metrics(acc, egeo)
    m["accepted_pct"] = 100.0 * m["accepted"] / len(cs)
    b = np.where(acc, egeo, post_egeo)
    b = b[np.isfinite(b)]
    m["policyB_mean_error"] = float(b.mean()) if len(b) else None
    return m


def main() -> None:
    z = np.load(ROOT / "results" / "_cache" / "testbed_v13.npz")
    scen = [str(s) for s in z["scenarios"]]
    sigmas = [float(s) for s in z["sigmas"]]
    cs, eg, peg = z["cs"][..., :82], z["egeo"][..., :82], z["post_egeo"][..., :82]
    R = cs.shape[2]
    grid = [("S1", s, g) for s in sigmas for g in GATES_S1] + \
           [(sc, s, 0.85) for sc in ("S0", "S2") for s in sigmas]
    rows = []
    cache = {}
    for sc, s, g in grid:
        si, gi = scen.index(sc), sigmas.index(s)
        reps = [replicate_metrics(cs[si, gi, r], eg[si, gi, r], peg[si, r], g) for r in range(R)]
        for mk in METRICS:
            mean, lo, hi, k = summary([m[mk] for m in reps])
            rows.append({"scenario": sc, "sigma_m": int(s), "gate": g,
                         "pre_specified": (s, g) == PRE_SPECIFIED, "metric": mk,
                         "mean": mean, "p2_5": lo, "p97_5": hi, "replicates_defined": k})
            cache[(sc, s, g, mk)] = mean
    cand = [(cache[("S1", s, 0.85, "policyB_mean_error")], s) for s in sigmas]
    best_sigma = min(cand)[1]
    out = ROOT / "results" / "sensitivity_sigma_cs.csv"
    with open(out, "w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=list(rows[0]), lineterminator="\n")
        w.writeheader()
        for r in rows:
            w.writerow({k: (f"{v:.4f}" if isinstance(v, float) and math.isfinite(v) else ("" if isinstance(v, float) else v))
                        for k, v in r.items()})
    (ROOT / "results" / "sensitivity_best_sigma.json").write_text(json.dumps({
        "rule": "minimum S1 mean positional error of policy B at Cs = 0.85, ties to the smaller sigma (post hoc)",
        "policyB_mean_error_by_sigma": {int(s): round(v, 2) for v, s in cand},
        "best_sigma_m": int(best_sigma)}, indent=2), encoding="utf-8")

    def cell(sc, s, g, mk, d=1):
        for r in rows:
            if (r["scenario"], r["sigma_m"], r["gate"], r["metric"]) == (sc, int(s), g, mk):
                if not math.isfinite(r["mean"]):
                    return "n/a"
                t = f"{r['mean']:.{d}f} [{r['p2_5']:.{d}f}, {r['p97_5']:.{d}f}]"
                return t + ("" if r["replicates_defined"] == R else f" ({r['replicates_defined']}/{R})")

    with open(out.with_suffix(".md"), "w", encoding="utf-8") as fh:
        fh.write(f"# Post hoc sensitivity to sigma and the Cs gate (Full DSDA, junction pass ON; {R} replicates)\n\n")
        fh.write("Pre-specified configuration: sigma = 150 m, Cs = 0.85. Values: mean [2.5th, 97.5th percentile].\n\n")
        fh.write("| Scenario | sigma (m) | Cs gate | Accepted (of 82) | Conditional median (m) | Conditional P90 (m) | "
                 "Accepted with E_geo > 150 m | Policy B mean error (m) |\n|---|---|---|---|---|---|---|---|\n")
        for sc, s, g in grid:
            fh.write(f"| {sc} | {int(s)} | {g:.2f} | {cell(sc, s, g, 'accepted')} | {cell(sc, s, g, 'cond_median')} | "
                     f"{cell(sc, s, g, 'cond_p90')} | {cell(sc, s, g, 'accepted_egeo_gt_150')} | "
                     f"{cell(sc, s, g, 'policyB_mean_error')} |\n")
        fh.write(f"\nSigma carried into Task 3 (post hoc rule): {int(best_sigma)} m "
                 f"(policy B mean error on S1 at Cs = 0.85: "
                 + ", ".join(f"{int(s)} m: {v:.1f}" for v, s in cand) + ")."
                 + (" It lies on the boundary of the grid, so the minimum may lie beyond it.\n"
                    if best_sigma == max(sigmas) else "\n"))
    print(out, "best sigma", best_sigma)


if __name__ == "__main__":
    main()
