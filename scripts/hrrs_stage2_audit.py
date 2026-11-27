"""Stage-2 HRRS audit of the 82 RR27 registry crashes (protocol v1.3, section 7).

Reads data/rr27_82_anonymized.csv and applies the frozen HRRS module
(dsda/hrrs.py): macro-scale critical rates with exact Poisson bounds, Poisson
frequency scan (82 crashes and 26 fatal crashes), OSS randomisation scan,
conditional OSS permutation scan, mutually exclusive classification, PK 41
severity vigilance, and the prospective holdout 2007-2011 against 2012-2015.

Usage: python scripts/hrrs_stage2_audit.py [--draws 10000] [--seed 2026]
Output: results/hrrs_stage2_audit.csv (long format) and .md
"""

from __future__ import annotations

import argparse
import csv
import sys
from pathlib import Path

import numpy as np
import pandas as pd
from scipy.stats import spearmanr

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from dsda import hrrs  # noqa: E402

PERIODS = {"2007-2011": (2007, 2011), "2012-2015": (2012, 2015)}


def rank_order(values: np.ndarray, counts: np.ndarray) -> np.ndarray:
    """Bin indices sorted by value, then count, then PK (all descending except PK)."""
    return np.lexsort((hrrs.PKS, -counts, -values))


def best_window(values: np.ndarray, length: int) -> tuple:
    sums = np.array([values[i:i + length].sum() for i in range(len(values) - length + 1)])
    i = int(np.argmax(sums))
    return f"PK {hrrs.PKS[i]}-{hrrs.PKS[i + length - 1]}", float(sums[i])


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--draws", type=int, default=10000)
    ap.add_argument("--seed", type=int, default=2026)
    ap.add_argument("--data", type=Path, default=ROOT / "data" / "rr27_82_anonymized.csv")
    ap.add_argument("--out", type=Path, default=ROOT / "results" / "hrrs_stage2_audit.csv")
    a = ap.parse_args()

    d = pd.read_csv(a.data)
    assert len(d) == 82 and d.pk.between(27, 42).all()
    bins = hrrs.bin_index(d.pk.values.astype(float))
    oss = d.oss.values.astype(float)
    rows = []

    def add(section, item, statistic, value, detail=""):
        if isinstance(value, (float, np.floating)):
            value = round(float(value), 4)
        rows.append({"section": section, "item": item, "statistic": statistic, "value": value, "detail": detail})

    E = hrrs.exposure()
    t_mean = len(d) / E.sum()
    add("corridor", "RR27 PK 27-42", "crashes", len(d))
    add("corridor", "RR27 PK 27-42", "fatal crashes", int((d.fatalities > 0).sum()))
    add("corridor", "RR27 PK 27-42", "OSS total", int(oss.sum()))
    add("corridor", "RR27 PK 27-42", "exposure (1e8 veh-km)", E.sum())
    add("corridor", "RR27 PK 27-42", "T_mean computed (crashes / 1e8 veh-km)", t_mean,
        f"fixed value used for T_c: {hrrs.T_MEAN_REGISTRY}")

    res = hrrs.classify(bins, oss, draws=a.draws, seed=a.seed)
    for seg, m in res["macro"].items():
        for k in ("n", "E", "T", "Tc", "LCB", "UCB"):
            add("macro", seg, k, m[k])
        add("macro", seg, "LCB_95 > T_c", bool(m["macro_tier1"]))
        add("macro", seg, "UCB_95 < T_c", bool(m["macro_clear"]))

    scans = dict(res["scans"])
    fatal = d.fatalities.values > 0
    scans["frequency_fatal"] = hrrs.frequency_scan(
        np.bincount(bins[fatal], minlength=len(hrrs.PKS)).astype(float), a.draws, a.seed + 10)
    for kind, sc in scans.items():
        for rank, w in enumerate(hrrs.clusters(sc), start=1):
            label = "most likely cluster" if rank == 1 else f"secondary cluster {rank - 1}"
            add(f"scan_{kind}", hrrs.window_label(w), "statistic", sc.stat[w], label)
            add(f"scan_{kind}", hrrs.window_label(w), "p_adj", sc.p_adj[w],
                ", ".join(hrrs.SEGMENTS_OF_WINDOW[w]))
    perm = scans["oss_permutation"]
    w41 = hrrs.PK41_WINDOW
    order = rank_order(res["oss_km"], res["counts"])
    add("vigilance_PK41", "PK 41", "OSS", res["oss_km"][41 - hrrs.PK_MIN])
    add("vigilance_PK41", "PK 41", "OSS rank", int(np.where(order == 41 - hrrs.PK_MIN)[0][0]) + 1)
    add("vigilance_PK41", "PK 41", "permutation p_raw", perm.p_raw[w41])
    add("vigilance_PK41", "PK 41", "permutation p_adj", perm.p_adj[w41])

    for seg, t in res["tiers"].items():
        flags = "; ".join(f"{k} {lab} (p_adj {p:.4f})" for k, lab, p in res["scan_flags"][seg])
        add("classification", seg, "tier", t, flags)

    # prospective holdout
    profiles = {}
    for name, (y0, y1) in PERIODS.items():
        sel = d.year.between(y0, y1).values
        years = y1 - y0 + 1
        Ep = hrrs.exposure(years)
        cnt = np.bincount(bins[sel], minlength=len(hrrs.PKS)).astype(float)
        okm = np.bincount(bins[sel], weights=oss[sel], minlength=len(hrrs.PKS))
        rate = cnt / Ep
        profiles[name] = (cnt, okm, rate)
        add(f"holdout_{name}", "corridor", "crashes", int(cnt.sum()))
        add(f"holdout_{name}", "corridor", "OSS", int(okm.sum()))
        for lab, vec in (("frequency", cnt), ("rate", rate), ("OSS", okm)):
            top = rank_order(vec, cnt)[:3]
            add(f"holdout_{name}", f"top 3 km by {lab}", "PKs",
                ", ".join(f"PK {hrrs.PKS[i]} ({vec[i]:.2f})" if lab == "rate" else f"PK {hrrs.PKS[i]} ({vec[i]:.0f})" for i in top))
        for lab, vec in (("frequency", cnt), ("OSS", okm)):
            win, val = best_window(vec, 3)
            add(f"holdout_{name}", f"best 3 km window by {lab}", "window", win, f"{val:.0f}")
        seg_rate = {s: m["T"] for s, m in hrrs.macro_table(cnt, E=Ep).items()}
        add(f"holdout_{name}", "segment ranking by rate", "order",
            " > ".join(f"{s} ({v:.2f})" for s, v in sorted(seg_rate.items(), key=lambda kv: -kv[1])))
    (c1, o1, r1), (c2, o2, r2) = profiles["2007-2011"], profiles["2012-2015"]
    for lab, v1, v2 in (("frequency", c1, c2), ("rate", r1, r2), ("OSS", o1, o2)):
        rho = spearmanr(v1, v2).correlation
        top1, top2 = set(rank_order(v1, c1)[:3]), set(rank_order(v2, c2)[:3])
        add("holdout_agreement", lab, "Spearman rho (16 km)", rho)
        add("holdout_agreement", lab, "top-3 km overlap (of 3)", len(top1 & top2))

    a.out.parent.mkdir(parents=True, exist_ok=True)
    with open(a.out, "w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=["section", "item", "statistic", "value", "detail"], lineterminator="\n")
        w.writeheader()
        w.writerows(rows)
    with open(a.out.with_suffix(".md"), "w", encoding="utf-8") as fh:
        fh.write(f"# Stage-2 HRRS audit (82 RR27 crashes, {a.draws} draws, seed {a.seed})\n\n")
        fh.write("| Section | Item | Statistic | Value | Detail |\n|---|---|---|---|---|\n")
        for r in rows:
            fh.write(f"| {r['section']} | {r['item']} | {r['statistic']} | {r['value']} | {r['detail']} |\n")
    print(f"{a.out}: {len(rows)} rows; tiers {res['tiers']}")


if __name__ == "__main__":
    main()
