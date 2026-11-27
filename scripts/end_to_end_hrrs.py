"""End-to-end DSDA to HRRS experiment (protocol v1.3, section 6; Task 3).

Feeds the DSDA decisions of scripts/testbed_v13.py (S0, S1, S2; sigma = 150 m
and the post hoc sigma of Task 2; Cs = 0.85) into the frozen HRRS module
(dsda/hrrs.py) under three policies for rejected records, and compares the
screening with Reference 1 (registry integer PKs) and Reference 2 (simulated
true continuous positions). Writes results/end_to_end_hrrs.csv and .md.
"""

from __future__ import annotations

import argparse
import csv
import json
import math
import sys
from pathlib import Path
from typing import Dict, List, Optional

import numpy as np
import pandas as pd
from scipy.stats import spearmanr

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "scripts"))
from dsda import hrrs  # noqa: E402
from testbed_v13 import summary  # noqa: E402

GATE = 0.85
KS = (3, 4, 5)
FREQ_DRAWS, OSS_DRAWS = 10000, 2000
BASE_SEED = 2026
POLICIES = ("A accepted-only", "B fail-safe hybrid", "C ungated best-candidate")
HALF_BINS = 32
SEG_OF_BIN = np.array([next(n for n, (a, b) in hrrs.SEGMENTS.items() if a <= pk <= b) for pk in hrrs.PKS])


def top_k(oss_km: np.ndarray, counts: np.ndarray, k: int) -> np.ndarray:
    return np.lexsort((hrrs.PKS, -counts, -oss_km))[:k]


def half_bin(pos: np.ndarray) -> np.ndarray:
    pos = np.asarray(pos, dtype=float)
    out = np.floor((pos - hrrs.AXIS[0]) / 0.5)
    out[~np.isfinite(pos) | (pos < hrrs.AXIS[0]) | (pos >= hrrs.AXIS[1])] = -1
    return out.astype(int)


def half_counts(pos: np.ndarray, at_post: np.ndarray) -> np.ndarray:
    """Crash counts in the 32 bins of 500 m. A record placed on an integer post
    (policy B, rejected) lies on the boundary between the two halves of its
    kilometre and counts 0.5 in each (uninformative within the kilometre)."""
    out = np.zeros(HALF_BINS)
    hb = half_bin(pos)
    ok = (hb >= 0) & ~at_post
    np.add.at(out, hb[ok], 1.0)
    kb = hrrs.bin_index(pos)
    okp = at_post & (kb >= 0)
    np.add.at(out, 2 * kb[okp], 0.5)
    np.add.at(out, 2 * kb[okp] + 1, 0.5)
    return out


def half_credit(pos: np.ndarray, at_post: np.ndarray, truth: np.ndarray) -> np.ndarray:
    """Per-record half-kilometre accuracy credit: 1 if the 500 m bin is right,
    0.5 for a post record in the right kilometre, 0 otherwise (or unplaced)."""
    hb, ht = half_bin(pos), half_bin(truth)
    credit = ((hb == ht) & (hb >= 0)).astype(float)
    kb, kt = hrrs.bin_index(pos), hrrs.bin_index(truth)
    credit[at_post] = 0.5 * ((kb[at_post] == kt[at_post]) & (kb[at_post] >= 0))
    return credit


def interval_of_window(w: int):
    i, L = hrrs.WINDOWS[w]
    return (hrrs.PKS[i] - 0.5, hrrs.PKS[i + L - 1] + 0.5)


def jaccard(a, b) -> float:
    inter = max(0.0, min(a[1], b[1]) - max(a[0], b[0]))
    union = (a[1] - a[0]) + (b[1] - b[0]) - inter
    return inter / union if union > 0 else math.nan


def reference(bins: np.ndarray, oss: np.ndarray, seed: int) -> dict:
    res = hrrs.classify(bins, oss, draws=FREQ_DRAWS, seed=seed, oss_draws=FREQ_DRAWS, freq_seed=BASE_SEED)
    res["mlc"] = interval_of_window(res["scans"]["frequency"].best)
    res["topk"] = {k: set(top_k(res["oss_km"], res["counts"], k)) for k in KS}
    return res


def evaluate(pos: np.ndarray, oss: np.ndarray, reg_bins: np.ndarray, ref: dict, seed: int) -> Dict[str, Optional[float]]:
    bins = hrrs.bin_index(pos)
    located = bins >= 0
    m: Dict[str, Optional[float]] = {"located": float(located.sum())}
    res = hrrs.classify(bins, oss, draws=FREQ_DRAWS, seed=seed, oss_draws=OSS_DRAWS, freq_seed=BASE_SEED)
    T = {s: v["T"] for s, v in res["macro"].items()}
    if located.sum() == 0 or len(set(T.values())) == 1:
        m["hrrs2_rank"] = None
    else:
        m["hrrs2_rank"] = 1.0 + sum(1 for s, v in T.items() if v > T["HRRS-2"])
    m["hrrs2_macro_tier1_pct"] = 100.0 * bool(res["macro"]["HRRS-2"]["macro_tier1"])
    m["hrrs2_tier1_pct"] = 100.0 * (res["tiers"]["HRRS-2"] == 1)
    m["fp_tier1_hrrs1_pct"] = 100.0 * (res["tiers"]["HRRS-1"] == 1)
    m["fp_tier1_hrrs3_pct"] = 100.0 * (res["tiers"]["HRRS-3"] == 1)
    has = res["oss_km"].sum() > 0
    m["pk41_oss_rank1_pct"] = 100.0 * (has and res["oss_rank1_pk"] == 41)
    m["pk41_perm_p_lt_0.05_pct"] = 100.0 * (has and res["pk41_perm_p_raw"] < 0.05)
    m["pk41_vigilance_both_pct"] = 100.0 * (has and res["oss_rank1_pk"] == 41 and res["pk41_perm_p_raw"] < 0.05)
    for k in KS:
        tk = set(top_k(res["oss_km"], res["counts"], k)) if has else set()
        m[f"recall_at_{k}"] = len(tk & ref["topk"][k]) / k if has else 0.0
        m[f"oss_share_top_{k}_pct"] = 100.0 * oss[np.isin(reg_bins, list(tk))].sum() / oss.sum() if has else 0.0
    fs = res["scans"]["frequency"]
    m["jaccard_mlc"] = jaccard(interval_of_window(fs.best), ref["mlc"]) if fs.stat.max() > 0 else None
    rho = spearmanr(res["oss_km"], ref["oss_km"]).correlation if located.sum() > 0 else math.nan
    m["spearman_oss_profile"] = None if not np.isfinite(rho) else float(rho)
    if located.sum() > 0:
        m["wrong_pk_pct"] = 100.0 * (bins[located] != reg_bins[located]).mean()
        m["wrong_segment_pct"] = 100.0 * (SEG_OF_BIN[bins[located]] != SEG_OF_BIN[reg_bins[located]]).mean()
    else:
        m["wrong_pk_pct"] = m["wrong_segment_pct"] = None
    return m


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--replicates", type=int, default=None, help="first N replicates only (smoke test)")
    ap.add_argument("--out", type=Path, default=ROOT / "results" / "end_to_end_hrrs.csv")
    a = ap.parse_args()
    z = np.load(ROOT / "results" / "_cache" / "testbed_v13.npz")
    best = json.loads((ROOT / "results" / "sensitivity_best_sigma.json").read_text())["best_sigma_m"]
    scen = [str(s) for s in z["scenarios"]]
    sigmas = [float(s) for s in z["sigmas"]]
    use_sigmas = sorted({150.0, float(best)})
    oss = z["oss"][:82]
    reg_bins = hrrs.bin_index(z["registry_pk"][:82])
    R = z["cs"].shape[2] if a.replicates is None else min(a.replicates, z["cs"].shape[2])
    ref1 = reference(reg_bins, oss, BASE_SEED)
    rows: List[dict] = []
    acc_metrics: Dict[tuple, List[dict]] = {}
    planted = z["planted"]
    for si, sc in enumerate(scen):
        for s in use_sigmas:
            gi = sigmas.index(s)
            for r in range(R):
                cs = np.nan_to_num(z["cs"][si, gi, r], nan=-1.0)
                sel, rep, tpk = z["sel_pk"][si, gi, r], z["reported_pk"][si, r], z["true_pk"][r]
                acc = cs >= GATE
                pos = {"A accepted-only": np.where(acc, sel, np.nan),
                       "B fail-safe hybrid": np.where(acc, sel, rep),
                       "C ungated best-candidate": sel.copy()}
                true_bins = hrrs.bin_index(tpk[:82])
                assert np.array_equal(true_bins, reg_bins), "Reference 2 bins must equal Reference 1 bins"
                at_post = {"A accepted-only": np.zeros_like(acc), "B fail-safe hybrid": ~acc & np.isfinite(rep),
                           "C ungated best-candidate": np.zeros_like(acc)}
                in_hrrs2 = SEG_OF_BIN[np.clip(reg_bins, 0, None)] == "HRRS-2"
                for pol, p in pos.items():
                    seed = BASE_SEED + 4_000_000 + r
                    m = evaluate(p[:82], oss, reg_bins, ref1, seed)
                    # half-kilometre accuracy (Reference 2 only); all 82 crashes for B and C
                    # (unplaced = 0), accepted records only for A
                    credit = half_credit(p[:82], at_post[pol][:82], tpk[:82])
                    if pol.startswith("A"):
                        m["half_km_accuracy_pct"] = None
                        m["half_km_accuracy_accepted_pct"] = 100.0 * credit[acc[:82]].mean() if acc[:82].any() else None
                        m["accepted_in_hrrs2"] = float((acc[:82] & in_hrrs2).sum())
                    else:
                        m["half_km_accuracy_pct"] = 100.0 * credit.mean()
                    acc_metrics.setdefault((sc, s, pol), []).append(m)
                # planted hotspot recovery: policies B, C and nominal PK
                rng = np.random.default_rng(BASE_SEED + 6_000_000 + 10 * r + si)
                nominal = rep + rng.uniform(-0.5, 0.5, size=rep.shape)
                no_post = np.zeros_like(acc)
                for variant in (1, 2):
                    idx = np.r_[0:82, np.flatnonzero(planted == variant)]
                    anchor = np.median(tpk[planted == variant])
                    target = int(half_bin(np.array([anchor]))[0])
                    for lab, p, ap in (("B fail-safe hybrid", pos["B fail-safe hybrid"], at_post["B fail-safe hybrid"]),
                                       ("C ungated best-candidate", pos["C ungated best-candidate"], no_post),
                                       ("Nominal PK (uniform within km)", nominal, no_post)):
                        cnt = half_counts(p[idx], ap[idx])
                        rec = 100.0 * (cnt[target] > np.delete(cnt, target).max())
                        mm = {"recovered_pct": rec}
                        if lab.startswith("B"):
                            mm["planted_accepted_pct"] = 100.0 * acc[planted == variant].mean()
                        acc_metrics.setdefault((sc, s, f"planted v{variant} | {lab}"), []).append(mm)
                if r % 200 == 0:
                    print(sc, s, r, flush=True)
    for (sc, s, pol), reps in acc_metrics.items():
        keys = list(reps[0])
        for k in keys:
            mean, lo, hi, kk = summary([m.get(k) for m in reps])
            ref_label = ("Ref 2 (simulated truth)" if k.startswith("half_km") or pol.startswith("planted")
                         else "Ref 1 (registry) = Ref 2 at km level" if k in (
                             "recall_at_3", "recall_at_4", "recall_at_5", "jaccard_mlc", "spearman_oss_profile",
                             "wrong_pk_pct", "wrong_segment_pct") else "")
            rows.append({"scenario": sc, "sigma_m": int(s), "gate": GATE, "policy": pol, "reference": ref_label,
                         "metric": k, "mean": mean, "p2_5": lo, "p97_5": hi, "replicates_defined": kk})
    # reference rows
    for k in KS:
        rows.append({"scenario": "registry", "sigma_m": "", "gate": "", "policy": "Reference 1 (registry)",
                     "reference": "", "metric": f"oss_share_top_{k}_pct",
                     "mean": 100.0 * oss[np.isin(reg_bins, list(ref1["topk"][k]))].sum() / oss.sum(),
                     "p2_5": "", "p97_5": "", "replicates_defined": ""})
        rows.append({"scenario": "registry", "sigma_m": "", "gate": "", "policy": "Reference 1 (registry)",
                     "reference": "", "metric": f"top_{k}_km",
                     "mean": " ".join(f"PK{hrrs.PKS[i]}" for i in sorted(ref1["topk"][k])),
                     "p2_5": "", "p97_5": "", "replicates_defined": ""})
    rows.append({"scenario": "registry", "sigma_m": "", "gate": "", "policy": "Reference 1 (registry)", "reference": "",
                 "metric": "frequency_mlc", "mean": f"[{ref1['mlc'][0]}, {ref1['mlc'][1]})", "p2_5": "", "p97_5": "",
                 "replicates_defined": ""})
    out = a.out
    with open(out, "w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=list(rows[0]), lineterminator="\n")
        w.writeheader()
        for row in rows:
            w.writerow({k: (f"{v:.4f}" if isinstance(v, float) and math.isfinite(v) else ("" if isinstance(v, float) else v))
                        for k, v in row.items()})
    _markdown(out, rows, R, use_sigmas)
    print(out)


def _markdown(out: Path, rows: List[dict], R: int, use_sigmas) -> None:
    def get(sc, s, pol, k, d=1):
        for row in rows:
            if (row["scenario"], row["sigma_m"], row["policy"], row["metric"]) == (sc, int(s), pol, k):
                v = row["mean"]
                if not (isinstance(v, float) and math.isfinite(v)):
                    return "n/a"
                t = f"{v:.{d}f} [{row['p2_5']:.{d}f}, {row['p97_5']:.{d}f}]"
                return t + ("" if row["replicates_defined"] == R else f" ({row['replicates_defined']}/{R})")
        return "n/a"

    metrics = [("located", "Records located (of 82)", 1), ("hrrs2_rank", "Rank of HRRS-2 by rate", 2),
               ("hrrs2_macro_tier1_pct", "HRRS-2 macro Tier 1 (%)", 1), ("hrrs2_tier1_pct", "HRRS-2 Tier 1 (%)", 1),
               ("fp_tier1_hrrs1_pct", "HRRS-1 Tier 1, false positive (%)", 1),
               ("fp_tier1_hrrs3_pct", "HRRS-3 Tier 1, false positive (%)", 1),
               ("pk41_oss_rank1_pct", "PK 41 first by OSS (%)", 1), ("pk41_perm_p_lt_0.05_pct", "PK 41 permutation p < 0.05 (%)", 1),
               ("recall_at_3", "Recall@3", 2), ("recall_at_4", "Recall@4", 2), ("recall_at_5", "Recall@5", 2),
               ("jaccard_mlc", "Jaccard, most likely cluster", 2), ("oss_share_top_3_pct", "OSS share in top 3 km (%)", 1),
               ("oss_share_top_5_pct", "OSS share in top 5 km (%)", 1), ("spearman_oss_profile", "Spearman, OSS profile", 2),
               ("wrong_pk_pct", "Crashes in a wrong PK (%)", 1), ("wrong_segment_pct", "Crashes in a wrong segment (%)", 1),
               ("half_km_accuracy_pct", "Half-km accuracy, all 82 (%)", 1),
               ("half_km_accuracy_accepted_pct", "Half-km accuracy, accepted (%)", 1),
               ("accepted_in_hrrs2", "Accepted records in HRRS-2 (of 33)", 1)]
    with open(out.with_suffix(".md"), "w", encoding="utf-8") as fh:
        fh.write(f"# End-to-end DSDA to HRRS ({R} replicates; mean [2.5th, 97.5th percentile])\n\n"
                 "Reference 1 (registry) and Reference 2 (simulated truth) coincide at kilometre level.\n")
        for s in use_sigmas:
            for sc in ("S0", "S1", "S2"):
                fh.write(f"\n## {sc}, sigma = {int(s)} m, Cs = {GATE}\n\n| Statistic | " + " | ".join(POLICIES) + " |\n|---|---|---|---|\n")
                for k, lab, d in metrics:
                    fh.write(f"| {lab} | " + " | ".join(get(sc, s, pol, k, d) for pol in POLICIES) + " |\n")
                fh.write("\n| Planted hotspot (10 crashes) | Planted accepted (%) | Recovered, policy B (%) | "
                         "Recovered, policy C (%) | Recovered, nominal PK (%) |\n|---|---|---|---|---|\n")
                for v, lab in ((1, "v1: unnamed junction, PK 34.26"), (2, "v2: named building, PK 34.94")):
                    fh.write(f"| {lab} | {get(sc, s, f'planted v{v} | B fail-safe hybrid', 'planted_accepted_pct')} | "
                             + " | ".join(get(sc, s, f"planted v{v} | {p}", "recovered_pct") for p in
                                          ("B fail-safe hybrid", "C ungated best-candidate", "Nominal PK (uniform within km)")) + " |\n")


if __name__ == "__main__":
    main()
