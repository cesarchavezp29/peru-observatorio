"""
build_eea_demografia.py
=======================
Composicion sectorial de las empresas de la EEA por ano (Capitulo 01 "para todos los
sectores", una fila por establecimiento). Macro-sector via CIIU; la EEA usa CIIU rev.3 hasta
2007 y rev.4 desde 2008 (se detecta por ano: comercio en div. 50-52 = rev3, en 45-47 = rev4),
con mapeos distintos -- aplicar uno solo cruza Comercio rev3 con Transportes rev4.

PONDERACION: el factor de expansion solo existe (y no nulo) desde 2012, salvo 2021 (columna
vacia en el Cap.01). Por eso la serie COMPARABLE/ponderada es 2012-2024 sin 2021. El pre-2012 y
2021 quedan como composicion MUESTRAL (pond=False) -- NO comparable con la ponderada (sesgo de
muestreo estratificado), se guarda solo para transparencia, no para la figura.

Se reporta COMPOSICION (participacion %), no niveles: el universo y la expansion de la EEA
cambian por ano (p.ej. 2024 sumo el estrato microempresa), asi que los conteos absolutos NO son
comparables en el tiempo; las participaciones dentro de cada ano si lo son.

Out: datasets/eea_demografia_sector.csv  (year, rev, pond, sector, n, peso, share)
"""
from __future__ import annotations
from pathlib import Path
import glob
import re
import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
RAW = ROOT / "raw" / "eea_inei"


def macro3(d2):  # CIIU rev.3
    if d2 in (1, 2, 5): return "Agro/Pesca"
    if 10 <= d2 <= 14: return "Mineria"
    if 15 <= d2 <= 37: return "Manufactura"
    if d2 in (40, 41): return "Electricidad/Agua"
    if d2 == 45: return "Construccion"
    if d2 in (50, 51, 52): return "Comercio"
    if d2 == 55: return "Aloj./Restaurantes"
    if 60 <= d2 <= 64: return "Transp./Comunic."
    if 65 <= d2 <= 99: return "Otros servicios"


def macro4(d2):  # CIIU rev.4
    if 1 <= d2 <= 3: return "Agro/Pesca"
    if 5 <= d2 <= 9: return "Mineria"
    if 10 <= d2 <= 33: return "Manufactura"
    if 35 <= d2 <= 39: return "Electricidad/Agua"
    if 41 <= d2 <= 43: return "Construccion"
    if 45 <= d2 <= 47: return "Comercio"
    if d2 in (55, 56): return "Aloj./Restaurantes"
    if d2 in (49, 50, 51, 52, 53, 58, 59, 60, 61, 62, 63): return "Transp./Comunic."
    if 64 <= d2 <= 99: return "Otros servicios"


def read_cap(code):
    fs = glob.glob(str(RAW / code / "**" / "*.csv"), recursive=True)
    f = ([x for x in fs if re.search(r'(cap|_c?01|CAP_01)', x, re.I)] or fs)[0]
    sep = ';' if ';' in open(f, encoding='latin-1').readline() else ','
    d = pd.read_csv(f, encoding="latin-1", sep=sep, low_memory=False)
    d.columns = [c.strip().strip('"').lower() for c in d.columns]
    return d


def main():
    m = pd.read_csv(RAW / "_eea_manifest.csv")
    cap = (m[m["module"].str.contains("todos los sectores", case=False, na=False)
             & ~m["module"].str.contains("TIC|Segur", case=False, na=False)]
           .sort_values("year").drop_duplicates("year"))
    rows = []
    for _, r in cap.iterrows():
        d = read_cap(r.csv_code); yr = int(r.year)
        d2 = pd.to_numeric(d['ciiu'].astype(str).str.replace(r'\.0$', '', regex=True).str[:2], errors='coerce')
        rev3 = d2.isin([50, 51, 52]).sum() > d2.isin([46, 47]).sum()
        d['sector'] = d2.apply(macro3 if rev3 else macro4)
        wcol = next((c for c in d.columns if c.startswith('fac') or 'factor' in c), None)
        w = pd.to_numeric(d[wcol], errors='coerce') if wcol else None
        pond = w is not None and w.sum() > 0
        d['w'] = w if pond else 1.0
        g = d.dropna(subset=['sector']).groupby('sector').agg(n=('w', 'size'), peso=('w', 'sum'))
        tot = g['peso'].sum()
        for sec, x in g.iterrows():
            rows.append({"year": yr, "rev": 3 if rev3 else 4, "pond": pond, "sector": sec,
                         "n": int(x['n']), "peso": round(x['peso']), "share": round(100 * x['peso'] / tot, 2)})
    out = pd.DataFrame(rows)
    out.to_csv(ROOT / "datasets" / "eea_demografia_sector.csv", index=False, encoding="utf-8")
    piv = out[out.pond].pivot(index="year", columns="sector", values="share").round(1)
    print("== Composicion PONDERADA (comparable, 2012-2024 sin 2021) ==")
    print(piv.to_string())
    print(f"\nWrote datasets/eea_demografia_sector.csv | {out.year.nunique()} anios "
          f"({out[out.pond].year.nunique()} ponderados)")


if __name__ == "__main__":
    main()
