"""
dataset_epen_lima_ingresos_grupos.py
====================================
Ingreso laboral (ingprin) por NIVEL EDUCATIVO y por SEXO, Lima Metropolitana, trimestre
movil 2001-2022, desde clean/epen_lima_panel.parquet. Real (soles de 2001, IPC Lima INEI)
y brecha salarial de genero.

Universo de ingreso = ocupados remunerados (excl TFNR=5 y Otro=7), ingprin valido --
misma definicion validada vs INEI/BCRP PN38070GM (0.07%).

Niveles (p109a -> educ): prim (<=4), sec (5-6), sup_no_univ (7-8), sup_univ (9-10).
Out: datasets/epen_lima_ingresos_grupos_trim_2001_2022.csv
"""
from __future__ import annotations
from pathlib import Path
import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
PANEL = ROOT / "clean" / "epen_lima_panel.parquet"
IPC = ROOT / "datasets" / "_ipc_lima_linked.csv"
OUT = ROOT / "datasets" / "epen_lima_ingresos_grupos_trim_2001_2022.csv"


def cmonth_key(ts):
    y, m = ts // 100, ts % 100; cm = m + 1; cy = y
    if cm > 12: cm -= 12; cy += 1
    return cy * 100 + cm


def wmean(g, mask):
    gg = g[mask & g["ingprin"].notna()]
    return float((gg["w"] * gg["ingprin"]).sum() / gg["w"].sum()) if gg["w"].sum() else np.nan


def main():
    p = pd.read_parquet(PANEL, columns=["trim_start", "trim_label", "edad", "sexo",
                                        "ocu200", "categ_ocup", "educ", "ingprin", "w"])
    o = p[(p["edad"] >= 14) & (p["ocu200"] == 1) & (~p["categ_ocup"].isin([5, 7]))].copy()
    ipc = pd.read_csv(IPC).set_index("ym")["factor_to_2001soles"]
    EDU = {"prim": [1, 2, 3, 4], "sec": [5, 6], "sup_no_univ": [7, 8], "sup_univ": [9, 10]}
    rows = []
    for ts, g in o.groupby("trim_start"):
        fac = ipc.get(cmonth_key(int(ts)), np.nan)
        rec = {"trim_start": int(ts), "trim_label": g["trim_label"].iloc[0], "anio": int(ts) // 100}
        for nm, codes in EDU.items():
            val = wmean(g, g["educ"].isin(codes)) * fac
            rec[f"ing_real_{nm}"] = round(val) if val == val else np.nan
        h = wmean(g, g["sexo"] == 1); m = wmean(g, g["sexo"] == 2)
        rec["ing_h"] = round(h) if h == h else np.nan
        rec["ing_m"] = round(m) if m == m else np.nan
        rec["ratio_m_h"] = round(m / h, 4) if h else np.nan
        rec["brecha_pct"] = round(100 * (1 - m / h), 1) if h else np.nan
        rows.append(rec)
    d = pd.DataFrame(rows).sort_values("trim_start")
    d.to_csv(OUT, index=False, encoding="utf-8")
    print(f"Wrote {OUT} ({len(d)} trimestres)")
    print(d.groupby("anio")[["ing_real_prim", "ing_real_sup_univ", "ratio_m_h"]].mean().round(2).to_string())


if __name__ == "__main__":
    main()
