"""
dataset_distribucion.py  -  distribution of REAL per-capita income over time
============================================================================
Two datasets built on the INEI-official ipcr_0 (real monthly per-capita income,
constant base-2025 soles at Lima prices, spatial ld + temporal i00 deflators),
reusing real_income() from dataset_income.py, person-weighted (factor07 x
mieperho) throughout.

Outputs (datasets/):
  income_percentiles_tiempo.csv   p10/p25/p50/p75/p90 + mean per year 2004-2025
  gic_periodos.csv                growth incidence curve: annualized real growth
                                  by percentile (5..95), for 2004-2025 and the
                                  three sub-periods 2004-2013 / 2013-2019 /
                                  2019-2025

VALIDATION: the weighted national mean per year is printed and, for any year
already present in income_real_national.csv, compared against it (must match to
0.1). That file was itself validated against INEI's published real income.

Run:  python dataset_distribucion.py
"""
from __future__ import annotations

import numpy as np
import pandas as pd

from dataset_income import OUTDIR, real_income, wmean

YEARS = list(range(2004, 2026))
PCTS = list(range(5, 100, 5))
WINDOWS = [(2004, 2025), (2004, 2013), (2013, 2019), (2019, 2025)]


def wquantile(values: np.ndarray, weights: np.ndarray, qs: list[float]) -> np.ndarray:
    """Weighted quantiles (type-4 style: cumulative weight interpolation)."""
    order = np.argsort(values)
    v, w = values[order], weights[order]
    cw = np.cumsum(w) - 0.5 * w
    cw /= np.sum(w)
    return np.interp(np.asarray(qs) / 100.0, cw, v)


def main() -> None:
    per_year: dict[int, pd.DataFrame] = {}
    pct_rows = []
    for y in YEARS:
        d = real_income(y)[["ipcr_0", "persons", "area"]]
        per_year[y] = d
        v = d["ipcr_0"].to_numpy(float)
        w = d["persons"].to_numpy(float)
        qs = wquantile(v, w, [10, 25, 50, 75, 90])
        mean = float(np.average(v, weights=w))
        pct_rows.append({"year": y, "p10": round(qs[0], 1), "p25": round(qs[1], 1),
                         "mediana": round(qs[2], 1), "p75": round(qs[3], 1),
                         "p90": round(qs[4], 1), "promedio": round(mean, 1),
                         "ratio_p90_p10": round(qs[4] / qs[0], 2)})
        print(f"  {y}: mediana S/{qs[2]:,.0f}  p10 S/{qs[0]:,.0f}  "
              f"p90 S/{qs[4]:,.0f}  promedio S/{mean:,.0f}")

    pct = pd.DataFrame(pct_rows)
    pct.to_csv(OUTDIR / "income_percentiles_tiempo.csv", index=False)
    print(f"wrote {OUTDIR / 'income_percentiles_tiempo.csv'}")

    # validation against the already-validated national means
    ref_path = OUTDIR / "income_real_national.csv"
    if ref_path.exists():
        ref = pd.read_csv(ref_path)
        chk = pct.merge(ref[["year", "real_pc_income_national"]], on="year")
        chk["diff"] = (chk["promedio"] - chk["real_pc_income_national"]).abs()
        bad = chk[chk["diff"] > 0.1]
        if len(bad):
            raise SystemExit(f"VALIDATION FAIL vs income_real_national:\n{bad}")
        print(f"validated: mean matches income_real_national in "
              f"{len(chk)}/{len(chk)} overlapping years (<=0.1)")

    # growth incidence curves
    gic_rows = []
    for pctl in PCTS:
        row = {"percentil": pctl}
        for y0, y1 in WINDOWS:
            q0 = wquantile(per_year[y0]["ipcr_0"].to_numpy(float),
                           per_year[y0]["persons"].to_numpy(float), [pctl])[0]
            q1 = wquantile(per_year[y1]["ipcr_0"].to_numpy(float),
                           per_year[y1]["persons"].to_numpy(float), [pctl])[0]
            g = 100 * ((q1 / q0) ** (1 / (y1 - y0)) - 1)
            row[f"crec_{y0}_{y1}"] = round(g, 2)
        gic_rows.append(row)
    gic = pd.DataFrame(gic_rows)
    gic.to_csv(OUTDIR / "gic_periodos.csv", index=False)
    print(f"wrote {OUTDIR / 'gic_periodos.csv'}")
    print(gic.to_string(index=False))


if __name__ == "__main__":
    main()
