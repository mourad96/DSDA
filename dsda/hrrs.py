"""Frozen HRRS screening module for the RR27 corridor (protocol v1.3, section 5).

Corridor: PK 27 to 42, one PK post = 1.0 km, continuous axis [26.5, 42.5) km
(16 one-kilometre bins centred on the integer PKs). Monitoring horizon Y = 9
years (2007 to 2015).

Macro scale: per-segment crash rate T_s (crashes per 1e8 veh-km), critical rate
T_c,s = T_mean + 1.645 sqrt(T_mean / E_s) + 1 / (2 E_s) anchored at the
registry corridor mean (T_mean = 9.08), exact 95 % Poisson bounds.

Micro scale: one-dimensional scans over every contiguous window of 1 to 5 bins
(70 windows), with Monte Carlo multiplicity adjustment (maximum statistic):
  * Poisson frequency scan (Kulldorff log-likelihood ratio, expected counts
    proportional to exposure E_k);
  * OSS randomisation scan: crash positions redrawn proportionally to E_k, each
    crash keeping its OSS_i = 10 F_i + I_i;
  * conditional permutation scan: positions fixed, the OSS_i permuted.
The two OSS scans use the standardised window excess z_W = (O_W - m_W) / s_W,
with the exact null mean and variance of each window, and the maximum of z_W
over the 70 windows.

Clusters are reported as in SaTScan: the most likely cluster, then secondary
clusters in decreasing order of the statistic that do not overlap a cluster
already reported. A cluster is attributed to the segment(s) holding at least
half of its length.

Classification (mutually exclusive): Tier 1 if LCB_95 > T_c,s or if a cluster
with adjusted p < 0.05 (frequency scan or either OSS scan) is attributed to the
segment; Tier 3 if UCB_95 < T_c,s and no such cluster; Tier 2 otherwise. PK 41 severity vigilance: PK 41 ranked first by
OSS and/or raw conditional-permutation p < 0.05 for its one-kilometre window.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, List, Optional, Sequence, Tuple

import numpy as np
from scipy.stats import chi2

PK_MIN, PK_MAX = 27, 42
PKS = np.arange(PK_MIN, PK_MAX + 1)                    # 16 bins
AXIS = (PK_MIN - 0.5, PK_MAX + 0.5)                    # [26.5, 42.5)
YEARS = 9
AADT = {pk: (18375 if pk <= 31 else 16849 if pk <= 36 else 16451) for pk in PKS}
SEGMENTS: Dict[str, Tuple[int, int]] = {               # inclusive PK ranges
    "HRRS-1": (27, 32), "HRRS-2": (33, 35), "HRRS-3": (36, 40), "HRRS-4": (41, 42),
}
T_MEAN_REGISTRY = 9.08                                 # crashes / 1e8 veh-km (82 crashes)
MAX_WINDOW = 5
ALPHA = 0.05
Z_CRIT = 1.645


def exposure(years: float = YEARS) -> np.ndarray:
    """E_k in 1e8 veh-km for each one-kilometre bin."""
    return np.array([AADT[pk] * 365.0 * years / 1e8 for pk in PKS])


def windows(n_bins: int = len(PKS), max_len: int = MAX_WINDOW) -> List[Tuple[int, int]]:
    """Contiguous windows as (start index, length)."""
    return [(i, L) for L in range(1, max_len + 1) for i in range(n_bins - L + 1)]


WINDOWS = windows()
_WIN_MATRIX = np.zeros((len(WINDOWS), len(PKS)))
for _w, (_i, _L) in enumerate(WINDOWS):
    _WIN_MATRIX[_w, _i:_i + _L] = 1.0


def window_label(w: int) -> str:
    i, L = WINDOWS[w]
    return f"PK {PKS[i]}" if L == 1 else f"PK {PKS[i]}-{PKS[i + L - 1]}"


def bin_index(pk_position: np.ndarray) -> np.ndarray:
    """Bin of a continuous position (km); -1 outside [26.5, 42.5)."""
    pos = np.asarray(pk_position, dtype=float)
    idx = np.floor(pos - AXIS[0]).astype(int)
    idx[(pos < AXIS[0]) | (pos >= AXIS[1]) | ~np.isfinite(pos)] = -1
    return idx


# ----------------------------------------------------------------------
# Macro scale
# ----------------------------------------------------------------------
def poisson_bounds(n: int, alpha: float = ALPHA) -> Tuple[float, float]:
    lo = chi2.ppf(alpha / 2, 2 * n) / 2 if n > 0 else 0.0
    hi = chi2.ppf(1 - alpha / 2, 2 * n + 2) / 2
    return float(lo), float(hi)


def macro_table(counts: np.ndarray, t_mean: float = T_MEAN_REGISTRY, E: Optional[np.ndarray] = None) -> Dict[str, dict]:
    E = exposure() if E is None else E
    out = {}
    for name, (a, b) in SEGMENTS.items():
        sl = slice(a - PK_MIN, b - PK_MIN + 1)
        n, Es = int(counts[sl].sum()), float(E[sl].sum())
        lo, hi = poisson_bounds(n)
        tc = t_mean + Z_CRIT * np.sqrt(t_mean / Es) + 1.0 / (2.0 * Es)
        out[name] = {"n": n, "E": Es, "T": n / Es, "Tc": tc, "LCB": lo / Es, "UCB": hi / Es,
                     "macro_tier1": lo / Es > tc, "macro_clear": hi / Es < tc}
    return out


# ----------------------------------------------------------------------
# Scans
# ----------------------------------------------------------------------
def _llr(n_w: np.ndarray, mu_w: np.ndarray, N: float) -> np.ndarray:
    n_w = np.asarray(n_w, dtype=float)
    out = np.zeros(np.broadcast(n_w, mu_w).shape)
    hi = (n_w > mu_w) & (n_w > 0)
    nn, mm = np.broadcast_to(n_w, out.shape)[hi], np.broadcast_to(mu_w, out.shape)[hi]
    rest = N - nn
    with np.errstate(divide="ignore", invalid="ignore"):
        term2 = np.where(rest > 0, rest * np.log(rest / (N - mm)), 0.0)
    out[hi] = nn * np.log(nn / mm) + term2
    return out


_NULL_CACHE: Dict[Tuple[int, int, int], np.ndarray] = {}


def frequency_null_max(N: int, draws: int, seed: int, E: Optional[np.ndarray] = None) -> np.ndarray:
    """Null distribution of the maximum LLR for N crashes (multinomial on E_k)."""
    key = (N, draws, seed)
    if key not in _NULL_CACHE:
        E = exposure() if E is None else E
        p = E / E.sum()
        rng = np.random.default_rng(seed)
        counts = rng.multinomial(N, p, size=draws)                  # draws x 16
        n_w = counts @ _WIN_MATRIX.T                                 # draws x 70
        mu_w = N * (_WIN_MATRIX @ p)
        _NULL_CACHE[key] = _llr(n_w, mu_w[None, :], N).max(axis=1)
    return _NULL_CACHE[key]


@dataclass
class ScanResult:
    stat: np.ndarray          # per-window statistic (LLR or z)
    p_adj: np.ndarray         # per-window adjusted p (maximum statistic)
    p_raw: Optional[np.ndarray] = None

    @property
    def best(self) -> int:
        return int(np.argmax(self.stat))


def frequency_scan(counts: np.ndarray, draws: int, seed: int) -> ScanResult:
    N = int(counts.sum())
    E = exposure()
    if N == 0:
        return ScanResult(np.zeros(len(WINDOWS)), np.ones(len(WINDOWS)))
    mu_w = N * (_WIN_MATRIX @ (E / E.sum()))
    stat = _llr(_WIN_MATRIX @ counts, mu_w, N)
    null = np.sort(frequency_null_max(N, draws, seed))
    ge = len(null) - np.searchsorted(null, stat - 1e-12, side="left")
    p_adj = (1 + ge) / (1 + len(null))
    p_adj[stat <= 0] = 1.0
    return ScanResult(stat, p_adj)


def _z(obs_w: np.ndarray, mean_w: np.ndarray, sd_w: np.ndarray) -> np.ndarray:
    with np.errstate(divide="ignore", invalid="ignore"):
        z = np.where(sd_w > 0, (obs_w - mean_w) / sd_w, 0.0)
    return z


def oss_randomisation_scan(bins: np.ndarray, oss: np.ndarray, draws: int, seed: int) -> ScanResult:
    """Positions redrawn proportionally to E_k; each crash keeps its OSS."""
    bins, oss = np.asarray(bins), np.asarray(oss, dtype=float)
    keep = bins >= 0
    bins, oss = bins[keep], oss[keep]
    if len(oss) == 0 or oss.sum() == 0:
        return ScanResult(np.zeros(len(WINDOWS)), np.ones(len(WINDOWS)))
    E = exposure()
    p_w = _WIN_MATRIX @ (E / E.sum())
    mean_w = p_w * oss.sum()
    sd_w = np.sqrt(p_w * (1 - p_w) * (oss ** 2).sum())
    obs = _WIN_MATRIX @ np.bincount(bins, weights=oss, minlength=len(PKS))
    stat = _z(obs, mean_w, sd_w)
    rng = np.random.default_rng(seed)
    pos = rng.choice(len(PKS), size=(draws, len(oss)), p=E / E.sum())
    sums = np.zeros((draws, len(PKS)))
    np.add.at(sums, (np.repeat(np.arange(draws), len(oss)), pos.ravel()), np.tile(oss, draws))
    null = np.sort(_z(sums @ _WIN_MATRIX.T, mean_w, sd_w).max(axis=1))
    ge = len(null) - np.searchsorted(null, stat - 1e-12, side="left")
    return ScanResult(stat, (1 + ge) / (1 + draws))


def oss_permutation_scan(bins: np.ndarray, oss: np.ndarray, draws: int, seed: int) -> ScanResult:
    """Positions fixed; OSS values permuted among crashes (conditional test)."""
    bins, oss = np.asarray(bins), np.asarray(oss, dtype=float)
    keep = bins >= 0
    bins, oss = bins[keep], oss[keep]
    N = len(oss)
    if N < 2 or np.all(oss == oss[0]):
        return ScanResult(np.zeros(len(WINDOWS)), np.ones(len(WINDOWS)), np.ones(len(WINDOWS)))
    onehot = np.zeros((N, len(PKS)))
    onehot[np.arange(N), bins] = 1.0
    member = onehot @ _WIN_MATRIX.T                                  # N x 70 (0/1)
    n_w = member.sum(axis=0)
    mu, var = oss.mean(), oss.var()                                  # population variance
    mean_w = n_w * mu
    sd_w = np.sqrt(np.where(N > 1, n_w * (N - n_w) / (N - 1) * var, 0.0))
    obs = oss @ member
    stat = _z(obs, mean_w, sd_w)
    rng = np.random.default_rng(seed)
    perm = rng.permuted(np.tile(oss, (draws, 1)), axis=1)            # draws x N
    sims = perm @ member                                             # draws x 70
    null = np.sort(_z(sims, mean_w[None, :], sd_w[None, :]).max(axis=1))
    ge = len(null) - np.searchsorted(null, stat - 1e-12, side="left")
    p_adj = (1 + ge) / (1 + draws)
    p_raw = (1 + (sims >= obs[None, :] - 1e-9).sum(axis=0)) / (1 + draws)
    p_adj[n_w == 0] = 1.0
    p_raw[n_w == 0] = 1.0
    return ScanResult(stat, p_adj, p_raw)


# ----------------------------------------------------------------------
# Classification
# ----------------------------------------------------------------------
def _segments_of_window(w: int) -> List[str]:
    """Segment(s) holding at least half of the window length."""
    i, L = WINDOWS[w]
    cover: Dict[str, int] = {}
    for k in range(i, i + L):
        pk = PKS[k]
        for name, (a, b) in SEGMENTS.items():
            if a <= pk <= b:
                cover[name] = cover.get(name, 0) + 1
    return [name for name, c in cover.items() if 2 * c >= L]


SEGMENTS_OF_WINDOW = [_segments_of_window(w) for w in range(len(WINDOWS))]


def clusters(sc: ScanResult) -> List[int]:
    """Most likely cluster, then non-overlapping secondary clusters (SaTScan rule)."""
    taken = np.zeros(len(PKS), dtype=bool)
    out = []
    for w in np.argsort(-sc.stat, kind="stable"):
        if sc.stat[w] <= 0:
            break
        i, L = WINDOWS[w]
        if taken[i:i + L].any():
            continue
        out.append(int(w))
        taken[i:i + L] = True
    return out
PK41_WINDOW = WINDOWS.index((41 - PK_MIN, 1))


def classify(bins: np.ndarray, oss: np.ndarray, draws: int, seed: int,
             t_mean: float = T_MEAN_REGISTRY, with_scans: bool = True) -> dict:
    """Full HRRS screening of one set of crash positions (bins) with their OSS."""
    bins, oss = np.asarray(bins), np.asarray(oss, dtype=float)
    keep = bins >= 0
    counts = np.bincount(bins[keep], minlength=len(PKS)).astype(float)
    oss_km = np.bincount(bins[keep], weights=oss[keep], minlength=len(PKS))
    macro = macro_table(counts, t_mean)
    res = {"counts": counts, "oss_km": oss_km, "macro": macro, "n": int(keep.sum())}
    flagged = {name: [] for name in SEGMENTS}
    if with_scans:
        scans = {
            "frequency": frequency_scan(counts, draws, seed),
            "oss_randomisation": oss_randomisation_scan(bins, oss, draws, seed + 1),
            "oss_permutation": oss_permutation_scan(bins, oss, draws, seed + 2),
        }
        for kind, sc in scans.items():
            for w in clusters(sc):
                if sc.p_adj[w] < ALPHA:
                    for seg in SEGMENTS_OF_WINDOW[w]:
                        flagged[seg].append((kind, window_label(w), float(sc.p_adj[w])))
        res["scans"] = scans
    tiers = {}
    for name, m in macro.items():
        if m["macro_tier1"] or flagged[name]:
            tiers[name] = 1
        elif m["macro_clear"]:
            tiers[name] = 3
        else:
            tiers[name] = 2
    res["tiers"] = tiers
    res["scan_flags"] = flagged
    order = np.lexsort((PKS, -counts, -oss_km))                    # OSS, then count, then PK
    res["oss_rank1_pk"] = int(PKS[order[0]]) if keep.any() else None
    if with_scans:
        res["pk41_perm_p_raw"] = float(res["scans"]["oss_permutation"].p_raw[PK41_WINDOW])
    return res
