"""
build_eea_productividad.py
==========================
Productividad laboral = Valor Agregado por trabajador, EEA 2024 (ano fiscal 2023), empresas
grandes (formato F2), ponderado. Por sector y por clase de tamano (personal ocupado).

A nivel de empresa se cruza, por IRUC:
  - VALOR AGREGADO: Clave 88 del Estado de Produccion (archivo *_c03_1.csv).
  - PERSONAL OCUPADO: Clave 08 (Total personal ocupado) del archivo *_c10_1.csv.
VA/trabajador del sector = sum(w*VA) / sum(w*trabajadores) (ratio de totales ponderados).

ALCANCE: solo F2 (grandes); las medianas (M) y micro (N) no tienen Estado de Produccion, asi
que no hay VA ni, por tanto, productividad-VA para ellas. La dimension "tamano" es por numero
de trabajadores dentro de las grandes.

Out: datasets/eea_productividad_sector.csv, datasets/eea_productividad_tamano.csv
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
BINS = [0, 50, 200, 500, np.inf]
BINLAB = ["1-50", "51-200", "201-500", "500+"]


def sec_of(n):
    for k, v in MOD2SEC.items():
        if k.lower() in n.lower():
            return v


def rd(f):
    sep = ';' if ';' in open(f, encoding='latin-1').readline() else ','
    d = pd.read_csv(f, encoding="latin-1", sep=sep, low_memory=False)
    d.columns = [c.strip().strip('"').lower() for c in d.columns]
    return d.rename(columns={d.columns[0]: 'iruc'})


def main():
    m = pd.read_csv(RAW / "_eea_manifest.csv")
    f2 = m[(m.year == 2024) & m["module"].str.contains(" F2", na=False)]
    firms = []
    for _, r in f2.iterrows():
        sec = sec_of(r["module"])
        if sec is None:
            continue
        files = glob.glob(f"raw/eea_inei/{r.csv_code}/**/*.csv", recursive=True)
        c03 = [x for x in files if re.search(r'_c03_1\.csv$', x)]
        c10 = [x for x in files if re.search(r'_c10_1\.csv$', x)]
        if not c03 or not c10:
            continue
        va = rd(c03[0])
        if 'clave' not in va.columns:
            continue
        cl = pd.to_numeric(va['clave'], errors='coerce')
        va = va[cl == 88][['iruc', 'dato1', 'factor_exp']].rename(columns={'dato1': 'va'})
        va['va'] = pd.to_numeric(va['va'], errors='coerce')
        em = rd(c10[0]); ce = pd.to_numeric(em['clave'], errors='coerce')
        em = em[ce == 8][['iruc', 'dato1']].rename(columns={'dato1': 'trab'})
        em['trab'] = pd.to_numeric(em['trab'], errors='coerce')
        g = va.merge(em, on='iruc', how='inner')
        g['w'] = pd.to_numeric(g['factor_exp'], errors='coerce'); g['sector'] = sec
        firms.append(g[['sector', 'va', 'trab', 'w']])
    f = pd.concat(firms).dropna(subset=['va', 'trab', 'w'])
    f = f[f.trab > 0]
    # por sector
    bs = f.groupby('sector').apply(lambda x: pd.Series({
        "trab": (x.w * x.trab).sum(), "va": (x.w * x.va).sum(),
        "va_x_trab": (x.w * x.va).sum() / (x.w * x.trab).sum()}), include_groups=False).reset_index()
    bs = bs.sort_values("va_x_trab", ascending=False)
    bs.to_csv(ROOT / "datasets" / "eea_productividad_sector.csv", index=False, encoding="utf-8")
    # por tamano (clase de personal ocupado)
    f['tam'] = pd.cut(f.trab, bins=BINS, labels=BINLAB)
    bt = f.groupby('tam', observed=True).apply(lambda x: pd.Series({
        "n": len(x), "trab": (x.w * x.trab).sum(), "va": (x.w * x.va).sum(),
        "va_x_trab": (x.w * x.va).sum() / (x.w * x.trab).sum()}), include_groups=False).reset_index()
    bt.to_csv(ROOT / "datasets" / "eea_productividad_tamano.csv", index=False, encoding="utf-8")
    # pivote sector x tamano
    piv = (f.groupby(['sector', 'tam'], observed=True)
           .apply(lambda x: (x.w * x.va).sum() / (x.w * x.trab).sum(), include_groups=False)
           .unstack() / 1000).round(1)
    piv.to_csv(ROOT / "datasets" / "eea_productividad_sector_tamano.csv", encoding="utf-8")
    print("== VA/trabajador por SECTOR (S/ miles/ano) ==")
    print(bs.assign(va_x_trab=(bs.va_x_trab / 1000).round(1))[["sector", "va_x_trab"]].to_string(index=False))
    print("\n== VA/trabajador por TAMANO (S/ miles/ano) ==")
    print(bt.assign(va_x_trab=(bt.va_x_trab / 1000).round(1))[["tam", "n", "va_x_trab"]].to_string(index=False))
    print("\n== sector x tamano (S/ miles/ano) ==")
    print(piv.to_string())


if __name__ == "__main__":
    main()
