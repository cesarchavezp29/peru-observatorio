"""
build_epen_dpto_theil_urbano.py
===============================
Desigualdad de Theil (descomponible) y brechas URBANO-RURAL por departamento, desde los
microdatos EPEN Dpto (790/874/935/1001 = 2022-2025), ponderado. Ingreso = ingtotp de
ocupados remunerados (excl no-remunerados c310 {4,8}, ingtotp>0).

Theil T = sum_i w_i (x_i/mu) ln(x_i/mu) / sum_i w_i.
Descomposicion: T = ENTRE grupos (sum_g s_g ln(mu_g/mu)) + DENTRO (sum_g s_g T_g),
  s_g = participacion del grupo en el ingreso total. Grupos = departamento y educacion.
Urbano-rural: informalidad e ingreso por area (1=urbano, 2=rural).

Out: datasets/epen_dpto_theil_urbano_2022_2025.csv  + imprime la descomposicion nacional 2025.
"""
from __future__ import annotations
from pathlib import Path
import glob
import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
RAW = ROOT / "raw" / "epen_inei"
OUT = ROOT / "datasets" / "epen_dpto_theil_urbano_2022_2025.csv"
CODES = {2022: 790, 2023: 874, 2024: 935, 2025: 1001}
DPTO = {1: "Amazonas", 2: "Ancash", 3: "Apurimac", 4: "Arequipa", 5: "Ayacucho",
        6: "Cajamarca", 7: "Callao", 8: "Cusco", 9: "Huancavelica", 10: "Huanuco",
        11: "Ica", 12: "Junin", 13: "La Libertad", 14: "Lambayeque", 15: "Lima",
        16: "Loreto", 17: "Madre de Dios", 18: "Moquegua", 19: "Pasco", 20: "Piura",
        21: "Puno", 22: "San Martin", 23: "Tacna", 24: "Tumbes", 25: "Ucayali"}
EDUYR = {1: 0, 2: 0, 3: 3, 4: 6, 5: 9, 6: 11, 7: 6, 8: 13, 9: 14, 10: 15, 11: 17, 12: 19}


def theil(x, w):
    m = np.isfinite(x) & np.isfinite(w) & (w > 0) & (x > 0)
    x, w = x[m], w[m]
    if len(x) < 2:
        return np.nan
    mu = np.average(x, weights=w)
    return np.average((x / mu) * np.log(x / mu), weights=w)


def decompose(df, gcol, w="fac300_anual", x="ingtotp"):
    """T total, entre-grupos, dentro-grupos para la variable de agrupacion gcol."""
    d = df[np.isfinite(df[x]) & (df[x] > 0) & np.isfinite(df[gcol])]
    Ttot = theil(d[x].values, d[w].values)
    tot_inc = (d[w] * d[x]).sum()
    within = 0.0
    for _, g in d.groupby(gcol):
        if len(g) < 2:
            continue
        s_g = (g[w] * g[x]).sum() / tot_inc                 # participacion en ingreso
        within += s_g * theil(g[x].values, g[w].values)
    between = Ttot - within                                 # identidad exacta de Theil T
    return Ttot, between, within


def main():
    rows = []
    nat = {}
    for y, code in CODES.items():
        fs = glob.glob(str(RAW / f"{code}_*/*.csv"))
        if not fs:
            continue
        df = pd.read_csv(fs[0], encoding="latin-1", low_memory=False)
        df.columns = [c.strip().strip('"').lower() for c in df.columns]
        for c in ["ocup300", "ccdd", "c208", "c310", "c366", "ingtotp", "area", "informal_p", "fac300_anual"]:
            df[c] = pd.to_numeric(df[c], errors="coerce")
        w = "fac300_anual"
        rem = df[(df["c208"] >= 14) & (df["ocup300"] == 1) & (~df["c310"].isin([4, 8])) & (df["ingtotp"] > 0)].copy()
        rem["edgrp"] = rem["c366"].map(EDUYR)
        for dd, name in DPTO.items():
            g = rem[rem["ccdd"] == dd]
            if len(g) < 100:
                continue
            T = theil(g["ingtotp"].values, g[w].values)
            occ = df[(df["ccdd"] == dd) & (df["c208"] >= 14) & (df["ocup300"] == 1)]
            def inf_area(a):
                s = occ[occ["area"] == a]
                return 100 * (s[w] * (s["informal_p"] == 1)).sum() / s[w].sum() if s[w].sum() else np.nan
            def ing_area(a):
                s = g[g["area"] == a]
                return (s[w] * s["ingtotp"]).sum() / s[w].sum() if s[w].sum() else np.nan
            rows.append({"anio": y, "ccdd": dd, "departamento": name, "theil": round(T, 3),
                         "informal_urb": round(inf_area(1), 1), "informal_rur": round(inf_area(2), 1),
                         "ing_urb": round(ing_area(1)) if ing_area(1) == ing_area(1) else np.nan,
                         "ing_rur": round(ing_area(2)) if ing_area(2) == ing_area(2) else np.nan})
        if y == 2025:
            nat["dept"] = decompose(rem, "ccdd")
            nat["educ"] = decompose(rem, "edgrp")
            nat["area"] = decompose(rem, "area")
    d = pd.DataFrame(rows)
    d.to_csv(OUT, index=False, encoding="utf-8")
    print(f"Wrote {OUT} ({len(d)} filas)")
    print("\n=== DESCOMPOSICION DE THEIL (nacional 2025) ===")
    dec = []
    GN = {"dept": "Departamento", "educ": "Educacion", "area": "Urbano/rural"}
    for k, (T, b, wi) in nat.items():
        print(f"  por {k:5s}: T={T:.3f}  entre={b:.3f} ({100*b/T:.0f}%)  dentro={wi:.3f} ({100*wi/T:.0f}%)")
        dec.append({"grupo": GN[k], "theil_total": round(T, 4), "entre": round(b, 4), "dentro": round(wi, 4), "pct_entre": round(100 * b / T, 1)})
    pd.DataFrame(dec).to_csv(ROOT / "datasets" / "epen_theil_decomp_2025.csv", index=False, encoding="utf-8")
    print("\n2025 -- Theil por depto (top/bottom) + brecha urbano-rural informalidad:")
    last = d[d["anio"] == 2025].sort_values("theil", ascending=False)
    last["gap_inf_ur"] = (last["informal_rur"] - last["informal_urb"]).round(1)
    print(last[["departamento", "theil", "informal_urb", "informal_rur", "gap_inf_ur"]].head(5).to_string(index=False))


if __name__ == "__main__":
    main()
