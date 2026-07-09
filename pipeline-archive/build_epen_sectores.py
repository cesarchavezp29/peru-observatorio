"""
build_epen_sectores.py
======================
Estructura sectorial del empleo (rama de actividad CIIU) desde los microdatos EPEN Dpto
(nacional, 790/874/935/1001 = 2022-2025), ponderado. Para cada sector: % de empleo,
% informal (informal_p), ingreso medio (ingtotp). Rangos CIIU validados vs INEI.

Out: datasets/epen_sectores_2022_2025.csv
"""
from __future__ import annotations
from pathlib import Path
import glob
import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
RAW = ROOT / "raw" / "epen_inei"
OUT = ROOT / "datasets" / "epen_sectores_2022_2025.csv"
CODES = {2022: 790, 2023: 874, 2024: 935, 2025: 1001}


def sector(code):
    if 100 <= code < 400: return "Agricultura/pesca"
    if 500 <= code < 1000: return "Mineria"
    if 1000 <= code < 3400: return "Manufactura"
    if 3500 <= code < 4100: return "Electricidad/agua"
    if 4100 <= code < 4400: return "Construccion"
    if 4500 <= code < 4800: return "Comercio"
    if 4900 <= code < 5400: return "Transporte/comunic."
    if 5500 <= code < 5700: return "Restaurantes/hoteles"
    if 8400 <= code < 8500: return "Adm. publica"
    if 8500 <= code < 8600: return "Educacion"
    if 8600 <= code < 8900: return "Salud"
    if 5700 <= code < 10000: return "Otros servicios"
    return None


def main():
    rows = []
    for y, code in CODES.items():
        fs = glob.glob(str(RAW / f"{code}_*/*.csv"))
        if not fs:
            continue
        df = pd.read_csv(fs[0], encoding="latin-1", low_memory=False)
        df.columns = [c.strip().strip('"').lower() for c in df.columns]
        for c in ["ocup300", "c208", "c309_cod", "informal_p", "ingtotp", "fac300_anual"]:
            df[c] = pd.to_numeric(df[c], errors="coerce")
        w = "fac300_anual"
        oc = df[(df["c208"] >= 14) & (df["ocup300"] == 1)].copy()
        oc["sec"] = oc["c309_cod"].apply(sector)
        oc = oc[oc["sec"].notna()]
        tot = oc[w].sum()
        for s, g in oc.groupby("sec"):
            perc = g[(g["ingtotp"] > 0) & g["ingtotp"].notna()]
            rows.append({
                "anio": y, "sector": s,
                "pct_empleo": round(100 * g[w].sum() / tot, 2),
                "pct_informal": round(100 * (g[w] * (g["informal_p"] == 1)).sum() / g[w].sum(), 1),
                "ing_medio": round((perc[w] * perc["ingtotp"]).sum() / perc[w].sum()) if perc[w].sum() else np.nan,
            })
        print(f"  {y}: {len([r for r in rows if r['anio']==y])} sectores")
    d = pd.DataFrame(rows)
    d.to_csv(OUT, index=False, encoding="utf-8")
    print(f"\nWrote {OUT} ({len(d)} filas)")
    print(d[d["anio"] == 2025].sort_values("pct_empleo", ascending=False).to_string(index=False))


if __name__ == "__main__":
    main()
