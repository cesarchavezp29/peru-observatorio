"""
dataset_epen_lima_informalidad.py
=================================
Empleo en el SECTOR INFORMAL, Lima Metropolitana, trimestre movil 2001-2022, desde
clean/epen_lima_panel.parquet. Ponderado, ocupados 14+.

DEFINICION (sector informal, basada en unidad productiva -- NO usa seguro de salud, por
lo que NO esta contaminada por la expansion del SIS):
  informal = independiente (2) OR TFNR (5) OR trab. del hogar (6)
             OR  (empleador/empleado/obrero {1,3,4} en empresa de <=5 trabajadores)
  (tam_empresa_n = p207b, numero de personas en el centro de trabajo)

NB: EPE Lima NO tiene afiliacion a pensiones, por lo que NO puede construir el "empleo
informal" OFICIAL de INEI (definicion ILO basada en proteccion social, calculada con
ENAHO). Esta es una aproximacion por SECTOR; coincide con el empleo informal de Lima
de INEI (ENAHO, ~52-58% anual) dentro de ~1-3 pp -- QA en docs, no se cita en la figura.

Out: datasets/epen_lima_informalidad_trim_2001_2022.csv
"""
from __future__ import annotations
from pathlib import Path
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
PANEL = ROOT / "clean" / "epen_lima_panel.parquet"
OUT = ROOT / "datasets" / "epen_lima_informalidad_trim_2001_2022.csv"


def main():
    p = pd.read_parquet(PANEL, columns=["trim_start", "trim_label", "edad", "sexo",
                                        "ocu200", "categ_ocup", "tam_empresa_n", "tam_empresa_brk", "w"])
    o = p[(p["edad"] >= 14) & (p["ocu200"] == 1)].copy()
    # small firm (<=5): exact headcount p207b/p207bb when present, else the 8-bracket
    # p207aa (1-4 = 1..4 personas) for the few late-2006 files that only carry the bracket.
    small = (o["tam_empresa_n"] <= 5)
    small = small.where(o["tam_empresa_n"].notna(), o["tam_empresa_brk"].isin([1, 2, 3, 4]))
    o["informal"] = (o["categ_ocup"].isin([2, 5, 6])
                     | (o["categ_ocup"].isin([1, 3, 4]) & small)).astype(float)
    rows = []
    for ts, g in o.groupby("trim_start"):
        tot = g["w"].sum()
        rec = {"trim_start": int(ts), "trim_label": g["trim_label"].iloc[0], "anio": int(ts) // 100,
               "tasa_informalidad": round(100 * (g["w"] * g["informal"]).sum() / tot, 2)}
        for code, suf in [(1, "_h"), (2, "_m")]:
            gs = g[g["sexo"] == code]
            rec[f"tasa_informalidad{suf}"] = round(100 * (gs["w"] * gs["informal"]).sum() / gs["w"].sum(), 2) if gs["w"].sum() else None
        rows.append(rec)
    d = pd.DataFrame(rows).sort_values("trim_start")
    d.to_csv(OUT, index=False, encoding="utf-8")
    print(f"Wrote {OUT} ({len(d)} trimestres)")
    print(d.groupby("anio")["tasa_informalidad"].mean().round(1).to_string())


if __name__ == "__main__":
    main()
