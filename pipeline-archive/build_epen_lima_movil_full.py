"""
build_epen_lima_movil_full.py
=============================
Serie Lima Metropolitana TRIMESTRE MOVIL CONTINUA 2001-2026, TODO microdatos INEI:
 - EPE legacy 2001-2022 (datasets/epen_lima_empleo_trim_2001_2022.csv)
 - EPEN moderno movil 2022-2026 (datasets/epen_lima_movil_modern_2022_2026.csv, region==1)
Misma frecuencia (trimestre movil) en toda la serie; el EPEN moderno reproduce BCRP a 0.00pp.
Clave = ym (mes final del trimestre movil).

Out: datasets/epen_lima_movil_2001_2026.csv
"""
from __future__ import annotations
from pathlib import Path
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
LEG = ROOT / "datasets" / "epen_lima_empleo_trim_2001_2022.csv"
MOD = ROOT / "datasets" / "epen_lima_movil_modern_2022_2026.csv"
OUT = ROOT / "datasets" / "epen_lima_movil_2001_2026.csv"
COLS = ["tasa_desempleo", "tasa_desempleo_h", "tasa_desempleo_m", "tasa_desempleo_joven",
        "tasa_desempleo_adulto", "tasa_desempleo_mayor", "tasa_actividad",
        "tasa_actividad_h", "tasa_actividad_m"]


def endkey(ts):
    y, m = ts // 100, ts % 100; em = m + 2; ey = y
    if em > 12: em -= 12; ey += 1
    return ey * 100 + em


def main():
    leg = pd.read_csv(LEG)
    leg["ym"] = leg["trim_start"].apply(endkey)
    leg = leg[["ym"] + COLS + ["ing_lab_prom"]].rename(columns={"ing_lab_prom": "ing_nominal"})
    leg["fuente"] = "EPE legacy"
    mod = pd.read_csv(MOD)
    mod = mod[["ym"] + COLS + ["ing_nominal"]]
    mod["fuente"] = "EPEN moderno"
    mod = mod[mod["ym"] > leg["ym"].max()]              # solo lo posterior al legacy
    d = pd.concat([leg, mod]).drop_duplicates("ym").sort_values("ym")
    d.to_csv(OUT, index=False, encoding="utf-8")
    print(f"Wrote {OUT} | {len(d)} trimestres moviles | {int(d.ym.min())}-{int(d.ym.max())}")
    print(f"  legacy: {(d.fuente=='EPE legacy').sum()}  moderno: {(d.fuente=='EPEN moderno').sum()}")


if __name__ == "__main__":
    main()
