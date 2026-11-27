"""Export the 82 in-scope RR27 crashes (PK 27 to 42) without identifying fields.

Input: the institutional workbook (sheet MC27). Output: data/rr27_82_anonymized.csv
with columns id, year, pk, fatalities, injured, oss (OSS = 10 F + I), sorted by
year then PK; id is a new sequential number unrelated to the registry order.
Usage: python scripts/export_rr27_82.py BD_RR27F.xlsx
"""

import sys
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]


def main(path: str) -> None:
    d = pd.read_excel(path, sheet_name="MC27")
    d = d[(d["PK"] >= 27) & (d["PK"] <= 42)].copy()
    out = pd.DataFrame({
        "year": pd.to_datetime(d["Date_accid"]).dt.year.astype(int),
        "pk": d["PK"].astype(int),
        "fatalities": d["Morts"].astype(int),
        "injured": d["Blessés"].astype(int),
    })
    out["oss"] = 10 * out["fatalities"] + out["injured"]
    out = out.sort_values(["year", "pk", "fatalities", "injured"], kind="mergesort").reset_index(drop=True)
    out.insert(0, "id", range(1, len(out) + 1))
    assert len(out) == 82, len(out)
    dst = ROOT / "data" / "rr27_82_anonymized.csv"
    out.to_csv(dst, index=False, lineterminator="\n")
    print(f"{dst}: {len(out)} crashes, {int((out.fatalities > 0).sum())} fatal, OSS {int(out.oss.sum())}")


if __name__ == "__main__":
    main(sys.argv[1])
