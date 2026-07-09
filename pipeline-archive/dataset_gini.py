"""
dataset_gini.py  -  Income inequality (Gini + p90/p10) from ENAHO, INEI method
=============================================================================
Reuses dataset_income.real_income(year) -> per-household real per-capita income
(ipcr_0, base-2025 Lima soles) with INEI person weights (factornd07), then
computes the WEIGHTED Gini coefficient and the p90/p10 ratio:
  * national, urban and rural, per year  -> gini_nacional_tiempo.csv
  * by department, per year               -> gini_departamento_tiempo.csv

Weighted Gini = 1 - 2*(area under the weighted Lorenz curve). Percentiles are
weighted. Negative incomes are clipped to 0 for the Lorenz curve.

Run:  python dataset_gini.py            # all available years
      python dataset_gini.py 2019 2024  # a subset (for testing)
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd

import dataset_income as di
import enaho_codes as ec  # noqa (dataset_income depends on it)

OUTDIR = Path(__file__).resolve().parents[1] / "datasets"
DEP_NAME = ec.DEPTO_NAMES if hasattr(ec, "DEPTO_NAMES") else {}


def wgini(x, w) -> float:
    x = np.asarray(x, float)
    w = np.asarray(w, float)
    m = np.isfinite(x) & np.isfinite(w) & (w > 0)
    x, w = np.clip(x[m], 0, None), w[m]
    if x.size < 2 or w.sum() <= 0:
        return np.nan
    o = np.argsort(x, kind="mergesort")
    x, w = x[o], w[o]
    xw = x * w
    if xw.sum() <= 0:
        return np.nan
    P = np.concatenate([[0], np.cumsum(w) / w.sum()])
    L = np.concatenate([[0], np.cumsum(xw) / xw.sum()])
    area = np.sum((P[1:] - P[:-1]) * (L[1:] + L[:-1]) / 2)
    return round(float(1 - 2 * area), 4)


def wpct(x, w, q) -> float:
    x = np.asarray(x, float)
    w = np.asarray(w, float)
    m = np.isfinite(x) & np.isfinite(w) & (w > 0)
    x, w = x[m], w[m]
    o = np.argsort(x, kind="mergesort")
    x, w = x[o], w[o]
    cw = np.cumsum(w) - 0.5 * w
    cw /= w.sum()
    return float(np.interp(q, cw, x))


def p90p10(x, w) -> float:
    p10 = wpct(x, w, 0.10)
    p90 = wpct(x, w, 0.90)
    return round(p90 / p10, 2) if p10 and p10 > 0 else np.nan


def main():
    args = [int(a) for a in sys.argv[1:] if a.isdigit()]
    years = args if args else list(range(2004, 2026))

    nat_rows, dep_rows = [], []
    for y in years:
        try:
            df = di.real_income(y)
        except Exception as e:  # noqa
            print(f"  [{y}] skipped: {e}")
            continue
        df = df[df["ipcr_0"].notna() & df["factornd07"].notna()]
        if df.empty:
            print(f"  [{y}] no data")
            continue
        x, w = df["ipcr_0"].values, df["factornd07"].values
        g = wgini(x, w)
        urb = df[df["area"] == 1]
        rur = df[df["area"] == 2]
        nat_rows.append({
            "anio": y, "gini": g,
            "gini_urbano": wgini(urb["ipcr_0"], urb["factornd07"]),
            "gini_rural": wgini(rur["ipcr_0"], rur["factornd07"]),
            "p90_p10": p90p10(x, w),
        })
        for dp, sub in df.groupby("dpto"):
            dep_rows.append({"anio": y, "dep": int(dp),
                             "gini": wgini(sub["ipcr_0"], sub["factornd07"])})
        print(f"  [{y}] Gini={g}  urb={nat_rows[-1]['gini_urbano']}  "
              f"rur={nat_rows[-1]['gini_rural']}  p90/p10={nat_rows[-1]['p90_p10']}")

    if not nat_rows:
        raise SystemExit("no years produced Gini")
    OUTDIR.mkdir(exist_ok=True)
    pd.DataFrame(nat_rows).to_csv(OUTDIR / "gini_nacional_tiempo.csv", index=False)
    pd.DataFrame(dep_rows).to_csv(OUTDIR / "gini_departamento_tiempo.csv", index=False)
    print(f"wrote gini_nacional_tiempo.csv ({len(nat_rows)} years) and "
          f"gini_departamento_tiempo.csv ({len(dep_rows)} rows)")


if __name__ == "__main__":
    main()
