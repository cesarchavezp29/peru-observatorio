"""
build_epen_dpto_indicadores2.py
===============================
Mas indicadores laborales por departamento (EPEN Dpto 2022-2025, microdatos, ponderado):
  - brecha_participacion = tasa de actividad hombre - mujer (exclusion femenina de la PEA)
  - tcompleto_bajo_min   = % de ocupados a tiempo completo (>=35h/sem) que ganan < salario
                           minimo ("trabajadores pobres a tiempo completo")
  - pct_agricola         = % de ocupados en agricultura (CIIU c309_cod 100-399)
RMV: 2022=1025, 2023=1025, 2024=1025, 2025=1130.
Out: datasets/epen_dpto_indicadores2_2022_2025.csv
"""
from __future__ import annotations
from pathlib import Path
import glob
import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
RAW = ROOT / "raw" / "epen_inei"
OUT = ROOT / "datasets" / "epen_dpto_indicadores2_2022_2025.csv"
CODES = {2022: 790, 2023: 874, 2024: 935, 2025: 1001}
RMV = {2022: 1025, 2023: 1025, 2024: 1025, 2025: 1130}
DPTO = {1: "Amazonas", 2: "Ancash", 3: "Apurimac", 4: "Arequipa", 5: "Ayacucho",
        6: "Cajamarca", 7: "Callao", 8: "Cusco", 9: "Huancavelica", 10: "Huanuco",
        11: "Ica", 12: "Junin", 13: "La Libertad", 14: "Lambayeque", 15: "Lima",
        16: "Loreto", 17: "Madre de Dios", 18: "Moquegua", 19: "Pasco", 20: "Piura",
        21: "Puno", 22: "San Martin", 23: "Tacna", 24: "Tumbes", 25: "Ucayali"}


def main():
    rows = []
    for y, code in CODES.items():
        fs = glob.glob(str(RAW / f"{code}_*/*.csv"))
        if not fs:
            continue
        df = pd.read_csv(fs[0], encoding="latin-1", low_memory=False)
        df.columns = [c.strip().strip('"').lower() for c in df.columns]
        for c in ["ocup300", "ccdd", "c207", "c208", "c309_cod", "whorat", "ingtotp", "fac300_anual"]:
            df[c] = pd.to_numeric(df[c], errors="coerce")
        w = "fac300_anual"; rmv = RMV[y]
        for dd, name in DPTO.items():
            g = df[(df["ccdd"] == dd) & (df["c208"] >= 14)]
            if len(g) < 50:
                continue
            def act(sub):
                return 100 * (sub[w] * sub["ocup300"].isin([1, 2])).sum() / sub[w].sum() if sub[w].sum() else np.nan
            ah, am = act(g[g["c207"] == 1]), act(g[g["c207"] == 2])
            oc = g[g["ocup300"] == 1]
            ft = oc[oc["whorat"] >= 35]
            tcbm = 100 * (ft[w] * ((ft["ingtotp"] > 0) & (ft["ingtotp"] < rmv))).sum() / ft[w].sum() if ft[w].sum() else np.nan
            agr = (oc["c309_cod"] >= 100) & (oc["c309_cod"] < 400)
            pag = 100 * (oc[w] * agr).sum() / oc[w].sum() if oc[w].sum() else np.nan
            rows.append({"anio": y, "ccdd": dd, "departamento": name,
                         "actividad_h": round(ah, 1), "actividad_m": round(am, 1),
                         "brecha_participacion": round(ah - am, 1),
                         "tcompleto_bajo_min": round(tcbm, 1), "pct_agricola": round(pag, 1)})
        print(f"  {y}: {len([r for r in rows if r['anio']==y])} deptos")
    d = pd.DataFrame(rows)
    d.to_csv(OUT, index=False, encoding="utf-8")
    print(f"\nWrote {OUT} ({len(d)} filas)")
    last = d[d["anio"] == 2025]
    print("\n2025 -- brecha de participacion de genero (top/bottom):")
    s = last.sort_values("brecha_participacion", ascending=False)
    print(s[["departamento", "actividad_h", "actividad_m", "brecha_participacion", "tcompleto_bajo_min", "pct_agricola"]].head(5).to_string(index=False))
    print("  ...")
    print(s[["departamento", "actividad_h", "actividad_m", "brecha_participacion", "tcompleto_bajo_min", "pct_agricola"]].tail(3).to_string(index=False))


if __name__ == "__main__":
    main()
