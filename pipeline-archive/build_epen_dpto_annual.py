"""
build_epen_dpto_annual.py
=========================
Indicadores de empleo por DEPARTAMENTO (25 + Callao) desde los microdatos del EPEN moderno
"BD Publicacion Dpto" (nacional), anual 2022-2025. Solo EPEN moderno (la EPE legacy era
Lima-only). Variables: ocup300, ccdd (departamento), c207 sexo, c208 edad, informal_p
(informalidad OFICIAL), ingtotp ingreso, fac300_anual peso.

Codes nacionales Dpto: 790=2022, 874=2023, 935=2024, 1001=2025.
Out: datasets/epen_dpto_annual_2022_2025.csv (una fila por departamento x ano)
"""
from __future__ import annotations
from pathlib import Path
import glob
import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
RAW = ROOT / "raw" / "epen_inei"
OUT = ROOT / "datasets" / "epen_dpto_annual_2022_2025.csv"
CODES = {2022: 790, 2023: 874, 2024: 935, 2025: 1001}
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
            print(f"  {y} (code {code}): NO FILE"); continue
        df = pd.read_csv(fs[0], encoding="latin-1", low_memory=False)
        df.columns = [c.strip().strip('"').lower() for c in df.columns]
        for c in ["ocup300", "ccdd", "c207", "c208", "informal_p", "ingtotp", "fac300_anual"]:
            df[c] = pd.to_numeric(df[c], errors="coerce")
        w = "fac300_anual"
        for dd, name in DPTO.items():
            g = df[(df["ccdd"] == dd) & (df["c208"] >= 14)]
            if not len(g):
                continue
            pea = (g[w] * g["ocup300"].isin([1, 2])).sum()
            des = 100 * (g[w] * (g["ocup300"] == 2)).sum() / pea if pea else np.nan
            act = 100 * pea / g[w].sum() if g[w].sum() else np.nan
            oc = g[g["ocup300"] == 1]
            inf = 100 * (oc[w] * (oc["informal_p"] == 1)).sum() / oc[w].sum() if oc[w].sum() else np.nan
            perc = oc[(oc["ingtotp"] > 0) & oc["ingtotp"].notna()]
            ing = (perc[w] * perc["ingtotp"]).sum() / perc[w].sum() if perc[w].sum() else np.nan
            rows.append({"anio": y, "ccdd": dd, "departamento": name, "n": len(g),
                         "tasa_desempleo": round(des, 2), "tasa_actividad": round(act, 2),
                         "tasa_informalidad": round(inf, 1), "ing_nominal": round(ing)})
        print(f"  {y}: {len([r for r in rows if r['anio']==y])} departamentos")
    d = pd.DataFrame(rows)
    d.to_csv(OUT, index=False, encoding="utf-8")
    print(f"\nWrote {OUT} ({len(d)} filas)")
    # 2025 ranking by informality
    last = d[d["anio"] == 2025].sort_values("tasa_informalidad", ascending=False)
    print("\n2025 -- informalidad (top/bottom 5):")
    print(last[["departamento", "tasa_informalidad", "tasa_desempleo", "ing_nominal"]].head().to_string(index=False))
    print("  ...")
    print(last[["departamento", "tasa_informalidad", "tasa_desempleo", "ing_nominal"]].tail().to_string(index=False))


if __name__ == "__main__":
    main()
