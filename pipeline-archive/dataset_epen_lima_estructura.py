"""
dataset_epen_lima_estructura.py
===============================
Estructura del empleo (categoria ocupacional) de los ocupados de Lima Metropolitana,
trimestre movil 2001-2022, desde clean/epen_lima_panel.parquet. Ponderado, 14+.

categ_ocup (p206): 1 Empleador, 2 Independiente, 3 Empleado, 4 Obrero,
                   5 TFNR, 6 Trab. hogar, 7 Otro.
Asalariado = Empleado + Obrero. Autoempleo = Independiente + TFNR.

Out: datasets/epen_lima_estructura_trim_2001_2022.csv
"""
from __future__ import annotations
from pathlib import Path
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
PANEL = ROOT / "clean" / "epen_lima_panel.parquet"
OUT = ROOT / "datasets" / "epen_lima_estructura_trim_2001_2022.csv"


def main():
    p = pd.read_parquet(PANEL, columns=["trim_start", "trim_label", "edad", "ocu200", "categ_ocup", "w"])
    o = p[(p["edad"] >= 14) & (p["ocu200"] == 1)]
    rows = []
    for ts, g in o.groupby("trim_start"):
        tot = g["w"].sum()
        def sh(cats): return round(100 * g[g["categ_ocup"].isin(cats)]["w"].sum() / tot, 2)
        rows.append({"trim_start": int(ts), "trim_label": g["trim_label"].iloc[0], "anio": int(ts) // 100,
                     "asalariado": sh([3, 4]), "empleado": sh([3]), "obrero": sh([4]),
                     "independiente": sh([2]), "empleador": sh([1]),
                     "tfnr": sh([5]), "trab_hogar": sh([6])})
    d = pd.DataFrame(rows).sort_values("trim_start")
    d.to_csv(OUT, index=False, encoding="utf-8")
    print(f"Wrote {OUT} ({len(d)} trimestres)")


if __name__ == "__main__":
    main()
