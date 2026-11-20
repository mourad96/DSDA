"""Table F.3: scan-window SNR across radii with 95% Poisson bands.

Statistic (Eq. 8), for a radius r:
    window length l = 2r (km); a window [p, p + l] contains the integer
    kilometric posts it covers (closed interval);
    SNR_r = max over windows of (sum OSS in window / l) / (sum OSS corridor / L_net),
    with L_net = 15.0 km and OSS = 10 F + I.

Poisson band (parametric bootstrap of the whole statistic):
    for each draw, F*_i ~ Poisson(F_i) and I*_i ~ Poisson(I_i) independently at
    each post (observed counts of Table F.2), OSS*_i = 10 F*_i + I*_i; the
    window is re-optimized (maximum) and the corridor baseline recomputed for
    each draw; bounds = empirical 2.5% and 97.5% percentiles (numpy, linear
    interpolation).

Usage:
    python scripts/table_f3_poisson_snr.py [--draws 10000] [--seed 2026]
"""

from __future__ import annotations

import argparse
import csv
from pathlib import Path

import numpy as np

RADII_M = [300, 500, 700, 850, 1000, 1200, 1500]
L_NET_KM = 15.0
DATA = Path(__file__).resolve().parents[1] / "data" / "rr27_table_f2.csv"


def load_counts(path: Path):
    pk, f, i = [], [], []
    with open(path, newline="", encoding="utf-8") as fh:
        for row in csv.DictReader(fh):
            pk.append(int(row["PK"]))
            f.append(int(row["F"]))
            i.append(int(row["I"]))
    return np.array(pk), np.array(f), np.array(i)


def max_window_density(pk: np.ndarray, oss: np.ndarray, length_km: float) -> float:
    """Highest OSS density over windows [p, p + length] anchored at each post."""
    best = 0.0
    for p in pk:
        inside = (pk >= p) & (pk <= p + length_km + 1e-9)
        best = max(best, float(oss[inside].sum()))
    return best / length_km


def snr(pk: np.ndarray, oss: np.ndarray, radius_m: float) -> float:
    baseline = oss.sum() / L_NET_KM
    if baseline == 0:
        return float("nan")
    return max_window_density(pk, oss, 2.0 * radius_m / 1000.0) / baseline


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--draws", type=int, default=10_000)
    ap.add_argument("--seed", type=int, default=2026)
    ap.add_argument("--data", type=Path, default=DATA)
    args = ap.parse_args()

    pk, f, i = load_counts(args.data)
    oss_obs = 10 * f + i
    rng = np.random.default_rng(args.seed)
    draws = [(10 * rng.poisson(f) + rng.poisson(i)) for _ in range(args.draws)]

    print(f"Table F.3 | draws = {args.draws}, seed = {args.seed}, numpy {np.__version__}")
    print(f"Corridor OSS = {oss_obs.sum()}, baseline = {oss_obs.sum() / L_NET_KM:.2f} OSS/km")
    print("r (m) | 2r (km) | SNR_obs | 95% band")
    for r in RADII_M:
        sims = np.array([snr(pk, o, r) for o in draws])
        lo, hi = np.percentile(sims[~np.isnan(sims)], [2.5, 97.5])
        print(f"{r:5d} | {2 * r / 1000:7.2f} | {snr(pk, oss_obs, r):7.2f} | [{lo:.2f}, {hi:.2f}]")


if __name__ == "__main__":
    main()
