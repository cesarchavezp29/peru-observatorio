"""
build_eea_ventas_va.py
======================
Ventas y Valor Agregado por sector, EEA 2024 (ano fiscal 2023), microdatos ponderados.

- VENTAS: VENTAS2023 del archivo c00 de cada modulo sectorial (frame de ventas declaradas).
- VALOR AGREGADO y PRODUCCION: del Estado de Produccion (archivo *_c03_1.csv), donde INEI ya
  computa, una fila por empresa: Clave 38 = PRODUCCION TOTAL (VBP), Clave 88 = VALOR AGREGADO
  (= 38 - consumo intermedio). Verificado contra el Diccionario_Variables_s04_fF2_EEA2024.pdf.

ALCANCE: el VA solo existe para empresas GRANDES (formato F2, que llenan la cuenta de
produccion detallada); las medianas (M) y micro (N) no la tienen. Por eso ventas y VA se
reportan para el universo F2, comparable entre si. Ano de referencia: 2023.

CAVEAT (ver README_EEA_METODOLOGIA.md): el formulario de CONSTRUCCION no trae VENTAS2023, solo
VENTAS2022 -> las ventas de construccion son de 2022 (un ano antes que su VA 2023). Sin solucion
(no existe la columna 2023); impacto menor (construccion ~7% del total).

Out: datasets/eea_ventas_va_sector.csv  (sector, ventas, produccion, valor_agregado, n_emp)
"""
from __future__ import annotations
from pathlib import Path
import glob
import re
import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
RAW = ROOT / "raw" / "eea_inei"

# modulo (nombre EEA) -> macro-sector
MOD2SEC = {
    "Comercio": "Comercio", "Manufactura": "Manufactura", "Construc": "Construccion",
    "Transportes": "Transp./Comunic.", "Servicios Electricos": "Electr./Agua",
    "Hidrocarburos": "Mineria/Hidroc.", "Pesca": "Agro/Pesca", "Acuicult": "Agro/Pesca",
    "Hospedaje": "Aloj./Restaurantes", "Restaurantes": "Aloj./Restaurantes",
    "Agencia de Viajes": "Otros servicios", "Centros Educativos": "Otros servicios",
    "Universidades": "Otros servicios", "Servicios": "Otros servicios",
}


def sec_of(modname):
    for k, v in MOD2SEC.items():
        if k.lower() in modname.lower():
            return v
    return None


def read(f):
    sep = ';' if ';' in open(f, encoding='latin-1').readline() else ','
    d = pd.read_csv(f, encoding="latin-1", sep=sep, low_memory=False)
    d.columns = [c.strip().strip('"').lower() for c in d.columns]
    return d


def main():
    m = pd.read_csv(RAW / "_eea_manifest.csv")
    f2 = m[(m.year == 2024) & m["module"].str.contains(" F2", na=False)]
    rows = []
    for _, r in f2.iterrows():
        sec = sec_of(r["module"])
        if sec is None:
            continue
        files = glob.glob(f"raw/eea_inei/{r.csv_code}/**/*.csv", recursive=True)
        # ventas: c00
        c00 = [x for x in files if re.search(r'_c00_', x)]
        ventas = 0.0
        if c00:
            d = read(c00[0])
            vcol = 'ventas2023' if 'ventas2023' in d.columns else ('ventas2022' if 'ventas2022' in d.columns else None)
            if vcol:
                v = pd.to_numeric(d[vcol], errors='coerce'); w = pd.to_numeric(d['factor_exp'], errors='coerce')
                ventas = (v * w).sum()
        # VA y produccion: estado de produccion c03_1
        c03 = [x for x in files if re.search(r'_c03_1\.csv$', x)]
        va = prod = 0.0; nemp = 0
        if c03 and 'clave' in read(c03[0]).columns:
            d = read(c03[0]); cl = pd.to_numeric(d['clave'], errors='coerce'); w = pd.to_numeric(d['factor_exp'], errors='coerce')
            va = (pd.to_numeric(d.loc[cl == 88, 'dato1'], errors='coerce') * w[cl == 88]).sum()
            prod = (pd.to_numeric(d.loc[cl == 38, 'dato1'], errors='coerce') * w[cl == 38]).sum()
            nemp = int((cl == 88).sum())
        rows.append({"sector": sec, "ventas": ventas, "produccion": prod, "valor_agregado": va, "n_emp": nemp})
    out = (pd.DataFrame(rows).groupby("sector", as_index=False)
           .agg(ventas=("ventas", "sum"), produccion=("produccion", "sum"),
                valor_agregado=("valor_agregado", "sum"), n_emp=("n_emp", "sum"))
           .sort_values("valor_agregado", ascending=False))
    for c in ["ventas", "produccion", "valor_agregado"]:
        out[c + "_mmM"] = (out[c] / 1e9).round(1)
    out.to_csv(ROOT / "datasets" / "eea_ventas_va_sector.csv", index=False, encoding="utf-8")
    print(out[["sector", "n_emp", "ventas_mmM", "produccion_mmM", "valor_agregado_mmM"]].to_string(index=False))
    tot = out[["ventas", "produccion", "valor_agregado"]].sum() / 1e9
    print(f"\nTOTAL F2 (S/ mil millones): ventas {tot.ventas:,.0f}  produccion {tot.produccion:,.0f}  VA {tot.valor_agregado:,.0f}")
    print(f"VA/Produccion = {100*tot.valor_agregado/tot.produccion:.0f}%  |  VA total = S/ {tot.valor_agregado/1000:.2f} billones")


if __name__ == "__main__":
    main()
