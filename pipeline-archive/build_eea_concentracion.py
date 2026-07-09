"""
build_eea_concentracion.py
==========================
Concentracion de mercado segun la EEA 2024 (ano fiscal 2023), por macro-sector y por industria
CIIU rev.4 a 4 digitos. Mercado = ventas (VENTAS2023 del archivo c00 de cada modulo, F2+M),
ponderado por factor de expansion.

Medidas:
  - CR4 / CR8 = participacion de las 4 / 8 mayores empresas en las ventas del mercado. Las
    grandes (F2) son censo (peso ~1, verificado), asi que sus ventas son exactas; el total del
    mercado es la suma ponderada (incluye las medianas muestreadas).
  - HHI = suma de cuadrados de participaciones x 10000 (>2500 = altamente concentrado, DOJ).

Los macro-sectores NO son mercados (Comercio = miles de mercados), por eso la concentracion real
se ve a nivel de industria CIIU 4 digitos. Solo se reportan industrias con >=6 empresas y ventas
>= S/2 mil M (mercados relevantes y con muestra suficiente).

Out: datasets/eea_concentracion_sector.csv, datasets/eea_concentracion_industria.csv
"""
from __future__ import annotations
from pathlib import Path
import glob
import re
import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
RAW = ROOT / "raw" / "eea_inei"

CIIU4 = {  # nombres CIIU rev.4 de las industrias que aparecen concentradas
    "1103": "Cerveza y bebidas malteadas", "1920": "Refinacion de petroleo",
    "2431": "Fundicion de hierro y acero", "2410": "Siderurgia (hierro y acero)",
    "1104": "Bebidas no alcoholicas y aguas", "5223": "Servicios para transporte aereo",
    "6120": "Telecomunicaciones moviles", "1050": "Productos lacteos",
    "6110": "Telecomunicaciones fijas", "9200": "Juegos de azar y apuestas",
    "4711": "Supermercados / minorista no espec.", "6190": "Otras telecomunicaciones",
    "1702": "Papel y carton ondulado", "0910": "Apoyo a extraccion de petroleo/gas",
    "0163": "Actividades poscosecha", "2432": "Fundicion de metales no ferrosos",
    "2420": "Metales preciosos y no ferrosos", "1040": "Aceites y grasas",
    "1709": "Otros articulos de papel", "5110": "Transporte aereo de pasajeros",
    "2029": "Otros productos quimicos", "0620": "Extraccion de gas natural",
}


def macro4(d2):
    if 1 <= d2 <= 3: return "Agro/Pesca"
    if 5 <= d2 <= 9: return "Mineria/Hidroc."
    if 10 <= d2 <= 33: return "Manufactura"
    if 35 <= d2 <= 39: return "Electr./Agua"
    if 41 <= d2 <= 43: return "Construccion"
    if 45 <= d2 <= 47: return "Comercio"
    if d2 in (55, 56): return "Aloj./Restaurantes"
    if d2 in (49, 50, 51, 52, 53, 58, 59, 60, 61, 62, 63): return "Transp./Comunic."
    if 64 <= d2 <= 99: return "Otros servicios"


def load():
    m = pd.read_csv(RAW / "_eea_manifest.csv")
    mods = m[(m.year == 2024) & ~m["module"].str.contains("TIC|Segur", case=False, na=False)]
    rows = []
    for _, r in mods.iterrows():
        for f in glob.glob(f"raw/eea_inei/{r.csv_code}/**/*_c00*.csv", recursive=True):
            sep = ';' if ';' in open(f, encoding='latin-1').readline() else ','
            d = pd.read_csv(f, encoding="latin-1", sep=sep, low_memory=False)
            d.columns = [c.strip().strip('"').lower() for c in d.columns]
            vcol = 'ventas2023' if 'ventas2023' in d.columns else ('ventas2022' if 'ventas2022' in d.columns else None)
            if not vcol or 'ciiu' not in d:
                continue
            rows.append(pd.DataFrame({
                'ciiu': d['ciiu'].astype(str).str.replace(r'\.0$', '', regex=True).str.zfill(4),
                'v': pd.to_numeric(d[vcol], errors='coerce'), 'w': pd.to_numeric(d['factor_exp'], errors='coerce')}))
    a = pd.concat(rows).dropna(subset=['v', 'w'])
    a = a[a.v > 0]
    a['sec'] = pd.to_numeric(a.ciiu.str[:2], errors='coerce').apply(macro4)
    return a


def conc(g):
    tot = (g.w * g.v).sum(); sv = g.sort_values('v', ascending=False)['v']
    return pd.Series({"n": len(g), "ventas_mmM": round(tot / 1e9, 1),
                      "cr4": round(100 * sv.head(4).sum() / tot, 1),
                      "cr8": round(100 * sv.head(8).sum() / tot, 1),
                      "hhi": round((g.w * (g.v / tot) ** 2).sum() * 10000)})


def main():
    a = load()
    bs = a.groupby('sec').apply(conc, include_groups=False).reset_index().sort_values('cr4', ascending=False)
    bs.to_csv(ROOT / "datasets" / "eea_concentracion_sector.csv", index=False, encoding="utf-8")
    bi = a.groupby('ciiu').apply(conc, include_groups=False).reset_index()
    bi = bi[(bi.n >= 6) & (bi.ventas_mmM >= 2)].copy()
    bi['industria'] = bi.ciiu.map(lambda c: CIIU4.get(c, f"CIIU {c}"))
    bi['sec'] = pd.to_numeric(bi.ciiu.str[:2], errors='coerce').apply(macro4)
    bi = bi.sort_values('cr4', ascending=False)
    bi.to_csv(ROOT / "datasets" / "eea_concentracion_industria.csv", index=False, encoding="utf-8")
    print("== Por macro-sector =="); print(bs[["sec", "n", "cr4", "cr8", "hhi"]].to_string(index=False))
    print("\n== Top 16 industrias mas concentradas ==")
    print(bi.head(16)[["industria", "n", "ventas_mmM", "cr4", "hhi"]].to_string(index=False))


if __name__ == "__main__":
    main()
