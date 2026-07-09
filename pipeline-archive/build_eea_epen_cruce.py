"""
build_eea_epen_cruce.py
=======================
Cruce empresa <-> trabajador por sector, 2023. Compara el salario medio mensual desde los dos
lados de la misma economia:
  - EEA (lado EMPRESA): remuneraciones (Cap.09 Clave 02) / personal ocupado (Cap.10 Clave 08) / 12,
    empresas GRANDES formales (F2). Por modulo sectorial -> macro-sector.
  - EPEN (lado TRABAJADOR): ingreso laboral mensual medio (ingtotp) de los ocupados 14+, TODOS
    los trabajadores (formales e informales, grandes y pequenos, asalariados e independientes).
    EPEN Dpto nacional 2023 (code 874), rama CIIU (c309_cod) -> mismo macro-sector.

El cociente EEA/EPEN = premio de la gran empresa formal sobre el trabajador promedio del sector.
Mismo macro-sector (division CIIU 2 digitos) en ambos lados. Ano de referencia 2023.

Out: datasets/eea_epen_cruce_sector.csv
"""
from __future__ import annotations
from pathlib import Path
import glob
import re
import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
RAW = ROOT / "raw"


def macro(d2):
    if 1 <= d2 <= 3: return "Agro/Pesca"
    if 5 <= d2 <= 9: return "Mineria/Hidroc."
    if 10 <= d2 <= 33: return "Manufactura"
    if 35 <= d2 <= 39: return "Electr./Agua"
    if 41 <= d2 <= 43: return "Construccion"
    if 45 <= d2 <= 47: return "Comercio"
    if d2 in (55, 56): return "Aloj./Restaurantes"
    if d2 in (49, 50, 51, 52, 53, 58, 59, 60, 61, 62, 63): return "Transp./Comunic."
    if 64 <= d2 <= 99: return "Otros servicios"


MOD2SEC = {
    "Comercio": "Comercio", "Manufactura": "Manufactura", "Construc": "Construccion",
    "Transportes": "Transp./Comunic.", "Servicios Electricos": "Electr./Agua",
    "Pesca": "Agro/Pesca", "Acuicult": "Agro/Pesca", "Hospedaje": "Aloj./Restaurantes",
    "Restaurantes": "Aloj./Restaurantes", "Agencia de Viajes": "Otros servicios",
    "Centros Educativos": "Otros servicios", "Universidades": "Otros servicios",
    "Servicios": "Otros servicios",
}


def sec_of(n):
    for k, v in MOD2SEC.items():
        if k.lower() in n.lower():
            return v


def rd(f):
    sep = ';' if ';' in open(f, encoding='latin-1').readline() else ','
    d = pd.read_csv(f, encoding="latin-1", sep=sep, low_memory=False)
    d.columns = [c.strip().strip('"').lower() for c in d.columns]
    return d.rename(columns={d.columns[0]: 'iruc'})


def eea_side():
    m = pd.read_csv(RAW / "eea_inei" / "_eea_manifest.csv")
    f2 = m[(m.year == 2024) & m["module"].str.contains(" F2", na=False)]
    rows = []
    for _, r in f2.iterrows():
        sec = sec_of(r["module"])
        if sec is None:
            continue
        files = glob.glob(f"raw/eea_inei/{r.csv_code}/**/*.csv", recursive=True)
        c09 = [x for x in files if re.search(r'_c09_1\.csv$', x)]
        c10 = [x for x in files if re.search(r'_c10_1\.csv$', x)]
        if not c09 or not c10:
            continue
        d9 = rd(c09[0]); d10 = rd(c10[0])
        if 'clave' not in d9.columns or 'clave' not in d10.columns:
            continue
        cl9 = pd.to_numeric(d9['clave'], errors='coerce'); w9 = pd.to_numeric(d9['factor_exp'], errors='coerce')
        remun = (pd.to_numeric(d9.loc[cl9 == 2, 'dato1'], errors='coerce') * w9[cl9 == 2]).sum()
        cl10 = pd.to_numeric(d10['clave'], errors='coerce'); w10 = pd.to_numeric(d10['factor_exp'], errors='coerce')
        trab = (pd.to_numeric(d10.loc[cl10 == 8, 'dato1'], errors='coerce') * w10[cl10 == 8]).sum()
        rows.append({"sector": sec, "remun": remun, "trab": trab})
    a = pd.DataFrame(rows).groupby("sector", as_index=False).sum()
    a["eea_mensual"] = (a.remun / a.trab / 12).round(0)
    return a[["sector", "eea_mensual"]]


def epen_side():
    f = glob.glob(str(RAW / "epen_inei" / "874_*/*.csv"))[0]
    d = pd.read_csv(f, encoding="latin-1", low_memory=False)
    d.columns = [c.strip().strip('"').lower() for c in d.columns]
    for c in ["ocup300", "c208", "c309_cod", "informal_p", "ingtotp", "fac300_anual"]:
        d[c] = pd.to_numeric(d[c], errors="coerce")
    oc = d[(d.c208 >= 14) & (d.ocup300 == 1)].copy()
    oc["d2"] = oc.c309_cod.dropna().astype(int).astype(str).str.zfill(4).str[:2].astype(int).reindex(oc.index)
    oc["sector"] = oc["d2"].apply(lambda x: macro(x) if pd.notna(x) else None)
    oc = oc[oc.sector.notna()]
    w = "fac300_anual"
    rows = []
    for s, g in oc.groupby("sector"):
        perc = g[(g.ingtotp > 0) & g.ingtotp.notna()]
        rows.append({"sector": s,
                     "epen_mensual": round((perc[w] * perc.ingtotp).sum() / perc[w].sum()) if perc[w].sum() else np.nan,
                     "epen_informal": round(100 * (g[w] * (g.informal_p == 1)).sum() / g[w].sum(), 0),
                     "epen_ocupados": round(g[w].sum())})
    return pd.DataFrame(rows)


def main():
    a = eea_side().merge(epen_side(), on="sector", how="inner")
    a["premio"] = (a.eea_mensual / a.epen_mensual).round(2)
    a = a.sort_values("premio", ascending=False)
    a.to_csv(ROOT / "datasets" / "eea_epen_cruce_sector.csv", index=False, encoding="utf-8")
    print(a[["sector", "eea_mensual", "epen_mensual", "premio", "epen_informal", "epen_ocupados"]].to_string(index=False))


if __name__ == "__main__":
    main()
