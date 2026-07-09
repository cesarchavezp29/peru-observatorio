"""
validate_official_income.py - convalidate real income & expenditure vs INEI
===========================================================================
Reproduces INEI's official 'Ingreso/Gasto real promedio per capita mensual a
precios de Lima' (ipcr_0 / gpgru0 from the INEI do-file) by year and by area
(urban/rural), so the income map's anchors can be checked against published
INEI figures.

Run: python validate_official_income.py
"""
from __future__ import annotations
import numpy as np, pandas as pd
import enaho_codes as ec
from dataset_income import real_income, wmean
from validate_gasto import gasto_real

# INEI published anchors (a precios de Lima, base 2025), national:
OFFICIAL_GASTO = {2024: 903.0, 2025: 920.0}     # poverty report 2025

YEARS = [2019, 2020, 2021, 2022, 2023, 2024, 2025]


def main():
    rows = []
    for y in YEARS:
        if y not in ec.YEAR_CODE:
            continue
        d = real_income(y)
        inc_nat = wmean(d)
        inc_u = wmean(d[d.area == 1]); inc_r = wmean(d[d.area == 2])
        gas_nat = gasto_real(y)
        rows.append({"year": y,
                     "income_nat": round(inc_nat, 1), "income_urb": round(inc_u, 1),
                     "income_rur": round(inc_r, 1),
                     "gasto_nat": round(gas_nat, 1),
                     "gasto_official": OFFICIAL_GASTO.get(y)})
    df = pd.DataFrame(rows)
    df["gasto_diff"] = (df["gasto_nat"] - df["gasto_official"]).round(1)
    df["income_yoy%"] = (100 * df["income_nat"].pct_change()).round(1)
    df.to_csv("../datasets/validation_income_gasto.csv", index=False)

    print(f"{'Year':<6}{'IncomeNat':>10}{'Urban':>8}{'Rural':>8}{'GastoNat':>10}"
          f"{'GastoOff':>10}{'diff':>7}{'IncYoY%':>9}")
    print("-" * 70)
    for _, r in df.iterrows():
        go = "" if pd.isna(r.gasto_official) else f"{r.gasto_official:10.1f}"
        gd = "" if pd.isna(r.gasto_diff) else f"{r.gasto_diff:+7.1f}"
        yo = "" if pd.isna(r["income_yoy%"]) else f"{r['income_yoy%']:+9.1f}"
        print(f"{int(r.year):<6}{r.income_nat:>10.1f}{r.income_urb:>8.1f}{r.income_rur:>8.1f}"
              f"{r.gasto_nat:>10.1f}{go}{gd}{yo}")
    print("-" * 70)
    print("Gasto vs INEI published: 2025 anchor S/920.0, 2024 S/903.0")
    print("Saved datasets/validation_income_gasto.csv")


if __name__ == "__main__":
    main()
