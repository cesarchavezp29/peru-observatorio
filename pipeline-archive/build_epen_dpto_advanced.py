"""
build_epen_dpto_advanced.py
===========================
Indicadores laborales AVANZADOS por departamento desde los microdatos EPEN "BD Publicacion
Dpto" (790=2022, 874=2023, 935=2024, 1001=2025). Ponderado (fac300_anual), 14+.

Indicadores:
  - indice_kaitz   = RMV / salario MEDIANO (ocupados remunerados). Cuan vinculante es el
                     minimo: ~1 = el minimo iguala al mediano (muy vinculante).
  - pct_bajo_rmv   = % de asalariados (cat 3) que ganan menos del salario minimo.
  - p90_p10        = razon del percentil 90 al 10 del ingreso (desigualdad salarial).
  - gini_ingreso   = Gini del ingreso laboral.
  - brecha_genero  = ingreso mediano mujer / hombre.
  - desempleo_joven= tasa de desempleo 14-24.
  - ratio_empleo   = ocupados / poblacion 14+.

RMV (Remuneracion Minima Vital): 2022=1025, 2023=1025, 2024=1025, 2025=1130.
Out: datasets/epen_dpto_advanced_2022_2025.csv
"""
from __future__ import annotations
from pathlib import Path
import glob
import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
RAW = ROOT / "raw" / "epen_inei"
OUT = ROOT / "datasets" / "epen_dpto_advanced_2022_2025.csv"
CODES = {2022: 790, 2023: 874, 2024: 935, 2025: 1001}
RMV = {2022: 1025, 2023: 1025, 2024: 1025, 2025: 1130}
DPTO = {1: "Amazonas", 2: "Ancash", 3: "Apurimac", 4: "Arequipa", 5: "Ayacucho",
        6: "Cajamarca", 7: "Callao", 8: "Cusco", 9: "Huancavelica", 10: "Huanuco",
        11: "Ica", 12: "Junin", 13: "La Libertad", 14: "Lambayeque", 15: "Lima",
        16: "Loreto", 17: "Madre de Dios", 18: "Moquegua", 19: "Pasco", 20: "Piura",
        21: "Puno", 22: "San Martin", 23: "Tacna", 24: "Tumbes", 25: "Ucayali"}


def wq(v, w, q):
    """Weighted quantile(s)."""
    m = np.isfinite(v) & np.isfinite(w) & (w > 0)
    v, w = v[m], w[m]
    if len(v) == 0:
        return np.nan if np.isscalar(q) else [np.nan] * len(q)
    o = np.argsort(v); v, w = v[o], w[o]
    cw = np.cumsum(w) - 0.5 * w
    cw /= w.sum()
    return np.interp(q, cw, v)


def wgini(v, w):
    m = np.isfinite(v) & np.isfinite(w) & (w > 0) & (v >= 0)
    v, w = v[m], w[m]
    if len(v) < 2:
        return np.nan
    o = np.argsort(v); v, w = v[o], w[o]
    cw = np.cumsum(w); cv = np.cumsum(v * w)
    cv /= cv[-1]; cw /= cw[-1]
    return 1 - np.sum((cw[1:] - cw[:-1]) * (cv[1:] + cv[:-1]))


def main():
    rows = []
    for y, code in CODES.items():
        fs = glob.glob(str(RAW / f"{code}_*/*.csv"))
        if not fs:
            continue
        df = pd.read_csv(fs[0], encoding="latin-1", low_memory=False)
        df.columns = [c.strip().strip('"').lower() for c in df.columns]
        for c in ["ocup300", "ccdd", "c207", "c208", "c310", "ingtotp", "fac300_anual"]:
            df[c] = pd.to_numeric(df[c], errors="coerce")
        w = "fac300_anual"; rmv = RMV[y]
        for dd, name in DPTO.items():
            g = df[(df["ccdd"] == dd) & (df["c208"] >= 14)]
            if len(g) < 50:
                continue
            # income earners: ocupados remunerados, excluir SOLO los NO remunerados del
            # diccionario c310: 4 (ayudante negocio familiar/TFNR) y 8 (practicante sin
            # remuneracion). El 7 (aprendiz/practicante REMUNERADO) SI se incluye. ingtotp>0.
            perc = g[(g["ocup300"] == 1) & (~g["c310"].isin([4, 8])) & (g["ingtotp"] > 0) & g["ingtotp"].notna()]
            iv, iw = perc["ingtotp"].values, perc[w].values
            med = wq(iv, iw, 0.5)
            p10, p90 = wq(iv, iw, [0.10, 0.90])
            asal = g[(g["ocup300"] == 1) & (g["c310"] == 3) & (g["ingtotp"] > 0) & g["ingtotp"].notna()]
            pct_bajo = 100 * (asal[w] * (asal["ingtotp"] < rmv)).sum() / asal[w].sum() if asal[w].sum() else np.nan
            medh = wq(perc[perc["c207"] == 1]["ingtotp"].values, perc[perc["c207"] == 1][w].values, 0.5)
            medm = wq(perc[perc["c207"] == 2]["ingtotp"].values, perc[perc["c207"] == 2][w].values, 0.5)
            yng = g[(g["c208"] >= 14) & (g["c208"] <= 24)]
            pea_y = (yng[w] * yng["ocup300"].isin([1, 2])).sum()
            des_y = 100 * (yng[w] * (yng["ocup300"] == 2)).sum() / pea_y if pea_y else np.nan
            rows.append({
                "anio": y, "ccdd": dd, "departamento": name, "rmv": rmv,
                "salario_mediano": round(med), "indice_kaitz": round(rmv / med, 3) if med else np.nan,
                "pct_bajo_rmv": round(pct_bajo, 1),
                "p90_p10": round(p90 / p10, 2) if p10 else np.nan,
                "gini_ingreso": round(wgini(iv, iw), 3),
                "brecha_genero": round(medm / medh, 3) if medh else np.nan,
                "desempleo_joven": round(des_y, 2),
            })
        print(f"  {y}: {len([r for r in rows if r['anio']==y])} deptos")
    d = pd.DataFrame(rows)
    d.to_csv(OUT, index=False, encoding="utf-8")
    print(f"\nWrote {OUT} ({len(d)} filas)")
    last = d[d["anio"] == 2025].sort_values("indice_kaitz", ascending=False)
    print("\n2025 -- indice de Kaitz (RMV/mediano), top/bottom:")
    print(last[["departamento", "salario_mediano", "indice_kaitz", "pct_bajo_rmv", "p90_p10", "gini_ingreso"]].head(6).to_string(index=False))
    print("  ...")
    print(last[["departamento", "salario_mediano", "indice_kaitz", "pct_bajo_rmv", "p90_p10", "gini_ingreso"]].tail(4).to_string(index=False))


if __name__ == "__main__":
    main()
