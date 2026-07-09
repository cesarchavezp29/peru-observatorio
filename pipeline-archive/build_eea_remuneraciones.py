"""
build_eea_remuneraciones.py
===========================
Remuneraciones (gastos de personal) y participacion del trabajo en el Valor Agregado, por
sector, EEA 2024 (ano fiscal 2023), empresas grandes F2, ponderado.

A nivel de empresa (IRUC), del Capitulo 09 "Gastos de Personal" (archivo *_c09_1.csv):
  - Clave 01, dato1 = TOTAL gastos de personal = compensacion laboral (remuneraciones + cargas
    sociales + beneficios). Es el numerador de la participacion del trabajo.
  - Clave 02, dato1 = Remuneraciones puras (sueldos, salarios, comisiones, gratificaciones...).
Se cruza con VALOR AGREGADO = Clave 88 del Estado de Produccion (*_c03_1.csv).

participacion del trabajo = compensacion (Clave 01) / VA. Solo F2 (donde existe el VA).

Out: datasets/eea_remuneraciones_sector.csv
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


def wsum(d, clave, col='dato1'):
    cl = pd.to_numeric(d['clave'], errors='coerce')
    v = pd.to_numeric(d.loc[cl == clave, col], errors='coerce')
    w = pd.to_numeric(d.loc[cl == clave, 'factor_exp'], errors='coerce')
    return (v * w).sum()


def main():
    m = pd.read_csv(RAW / "_eea_manifest.csv")
    f2 = m[(m.year == 2024) & m["module"].str.contains(" F2", na=False)]
    rows = []
    for _, r in f2.iterrows():
        sec = sec_of(r["module"])
        if sec is None:
            continue
        files = glob.glob(f"raw/eea_inei/{r.csv_code}/**/*.csv", recursive=True)
        c09 = [x for x in files if re.search(r'_c09_1\.csv$', x)]
        c03 = [x for x in files if re.search(r'_c03_1\.csv$', x)]
        if not c09 or not c03:
            continue
        d9 = rd(c09[0]); d3 = rd(c03[0])
        if 'clave' not in d9.columns or 'clave' not in d3.columns:
            continue
        rows.append({"sector": sec,
                     "compensacion": wsum(d9, 1), "remuneraciones": wsum(d9, 2),
                     "valor_agregado": wsum(d3, 88)})
    out = (pd.DataFrame(rows).groupby("sector", as_index=False)
           .agg(compensacion=("compensacion", "sum"), remuneraciones=("remuneraciones", "sum"),
                valor_agregado=("valor_agregado", "sum")))
    out["part_trabajo"] = (100 * out.compensacion / out.valor_agregado).round(1)
    for c in ["compensacion", "remuneraciones", "valor_agregado"]:
        out[c + "_mmM"] = (out[c] / 1e9).round(1)
    out = out.sort_values("part_trabajo", ascending=False)
    out.to_csv(ROOT / "datasets" / "eea_remuneraciones_sector.csv", index=False, encoding="utf-8")
    print(out[["sector", "compensacion_mmM", "remuneraciones_mmM", "valor_agregado_mmM", "part_trabajo"]].to_string(index=False))
    t = out[["compensacion", "valor_agregado"]].sum()
    print(f"\nTOTAL F2: compensacion S/{t.compensacion/1e9:,.0f} mil M, VA S/{t.valor_agregado/1e9:,.0f} mil M")
    print(f"Participacion del trabajo en el VA (agregada) = {100*t.compensacion/t.valor_agregado:.1f}%")


if __name__ == "__main__":
    main()
