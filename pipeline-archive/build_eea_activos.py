"""
build_eea_activos.py
====================
Activos e inversion por sector, EEA 2024 (ano fiscal 2023), empresas grandes F2, ponderado.

Del Balance General (archivo *_c02_1.csv, con dato1=2023 y dato2=2022):
  - Clave 42 = TOTAL ACTIVO (validado: cuadra con total pasivo+patrimonio, Clave 84).
  - Clave 28 = Propiedad, planta y equipo (PP&E bruto); Clave 29 = (-) Depreciacion acumulada.
    PP&E neto = Clave 28 - Clave 29.
  - INVERSION (proxy) = PP&E bruto 2023 - PP&E bruto 2022 (variacion del activo fijo bruto). Es
    un PROXY de la formacion bruta de capital: neto de retiros y afectado por revaluaciones, no
    es la inversion bruta exacta (esa requiere el capitulo de movimiento de activo fijo).

Solo F2 (las medianas/micro no tienen balance detallado). Ano de referencia 2023.

Out: datasets/eea_activos_sector.csv
"""
from __future__ import annotations
from pathlib import Path
import glob
import re
import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
RAW = ROOT / "raw" / "eea_inei"
MOD2SEC = {
    "Comercio": "Comercio", "Manufactura": "Manufactura", "Construc": "Construccion",
    "Transportes": "Transp./Comunic.", "Servicios Electricos": "Electr./Agua",
    "Hidrocarburos": "Mineria/Hidroc.", "Pesca": "Agro/Pesca", "Acuicult": "Agro/Pesca",
    "Hospedaje": "Aloj./Restaurantes", "Restaurantes": "Aloj./Restaurantes",
    "Agencia de Viajes": "Otros servicios", "Centros Educativos": "Otros servicios",
    "Universidades": "Otros servicios", "Servicios": "Otros servicios",
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


def wsum(d, cl, w, clave, col):
    return (pd.to_numeric(d.loc[cl == clave, col], errors='coerce') * w[cl == clave]).sum()


def main():
    m = pd.read_csv(RAW / "_eea_manifest.csv")
    f2 = m[(m.year == 2024) & m["module"].str.contains(" F2", na=False)]
    rows = []
    for _, r in f2.iterrows():
        sec = sec_of(r["module"])
        if sec is None:
            continue
        c02 = [x for x in glob.glob(f"raw/eea_inei/{r.csv_code}/**/*.csv", recursive=True) if re.search(r'_c02_1\.csv$', x)]
        if not c02:
            continue
        d = rd(c02[0])
        if 'clave' not in d.columns or 'dato2' not in d.columns:
            continue
        cl = pd.to_numeric(d['clave'], errors='coerce'); w = pd.to_numeric(d['factor_exp'], errors='coerce')
        if not (cl == 42).any():
            continue
        rows.append({"sector": sec,
                     "activo_total": wsum(d, cl, w, 42, 'dato1'),
                     "ppe_bruto": wsum(d, cl, w, 28, 'dato1'),
                     "deprec": wsum(d, cl, w, 29, 'dato1'),
                     "ppe_bruto_2022": wsum(d, cl, w, 28, 'dato2')})
    a = pd.DataFrame(rows).groupby("sector", as_index=False).sum()
    a["ppe_neto"] = a.ppe_bruto - a.deprec
    a["inversion"] = a.ppe_bruto - a.ppe_bruto_2022
    a["intensidad_capital"] = (100 * a.ppe_neto / a.activo_total).round(1)  # % activos en capital fijo
    a["tasa_inversion"] = (100 * a.inversion / a.ppe_bruto_2022).round(1)
    for c in ["activo_total", "ppe_neto", "ppe_bruto", "inversion"]:
        a[c + "_mmM"] = (a[c] / 1e9).round(1)
    a = a.sort_values("activo_total", ascending=False)
    a.to_csv(ROOT / "datasets" / "eea_activos_sector.csv", index=False, encoding="utf-8")
    print(a[["sector", "activo_total_mmM", "ppe_neto_mmM", "intensidad_capital", "inversion_mmM", "tasa_inversion"]].to_string(index=False))
    t = a[["activo_total", "ppe_neto", "inversion"]].sum() / 1e9
    print(f"\nTOTAL F2: activos S/{t.activo_total:,.0f} mil M, PP&E neto S/{t.ppe_neto:,.0f} mil M, "
          f"inversion(proxy) S/{t.inversion:,.0f} mil M")


if __name__ == "__main__":
    main()
