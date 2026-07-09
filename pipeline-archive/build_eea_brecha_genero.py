"""
build_eea_brecha_genero.py
==========================
Brecha salarial de genero por sector, EEA 2024 (ano fiscal 2023), empresas grandes F2, ponderado.

A nivel de empresa (IRUC):
  - REMUNERACIONES por sexo: Capitulo 09 (*_c09_1.csv), Clave 02 (Remuneraciones = sueldos,
    salarios, comisiones, gratificaciones, vacaciones). dato3=Permanente Hombre, dato4=Permanente
    Mujer, dato6=Eventual Hombre, dato7=Eventual Mujer -> comp_H=dato3+dato6, comp_M=dato4+dato7.
  - PERSONAL por sexo: Capitulo 10 (*_c10_1.csv), Clave 08 (Total personal ocupado),
    dato2=promedio Hombre, dato3=promedio Mujer.
Salario medio anual por sexo = comp_sexo / personas_sexo. Brecha = (H - M)/H.

Es una brecha BRUTA (sin ajustar por ocupacion, horas ni educacion). Solo F2. Ano ref 2023.

Out: datasets/eea_brecha_genero_sector.csv
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


def num(s):
    return pd.to_numeric(s, errors='coerce')


def main():
    m = pd.read_csv(RAW / "_eea_manifest.csv")
    f2 = m[(m.year == 2024) & m["module"].str.contains(" F2", na=False)]
    rows = []
    for _, r in f2.iterrows():
        sec = sec_of(r["module"])
        if sec is None:
            continue
        fs_ = glob.glob(f"raw/eea_inei/{r.csv_code}/**/*.csv", recursive=True)
        c09 = [x for x in fs_ if re.search(r'_c09_1\.csv$', x)]
        c10 = [x for x in fs_ if re.search(r'_c10_1\.csv$', x)]
        if not c09 or not c10:
            continue
        d9 = rd(c09[0]); d10 = rd(c10[0])
        if 'clave' not in d9.columns or 'clave' not in d10.columns:
            continue
        s9 = d9[num(d9['clave']) == 2]; w9 = num(s9['factor_exp'])
        compH = (w9 * (num(s9['dato3']) + num(s9['dato6']))).sum()
        compM = (w9 * (num(s9['dato4']) + num(s9['dato7']))).sum()
        s10 = d10[num(d10['clave']) == 8]; w10 = num(s10['factor_exp'])
        persH = (w10 * num(s10['dato2'])).sum()
        persM = (w10 * num(s10['dato3'])).sum()
        rows.append({"sector": sec, "compH": compH, "compM": compM, "persH": persH, "persM": persM})
    a = pd.DataFrame(rows).groupby("sector", as_index=False).sum()
    a["wH"] = a.compH / a.persH
    a["wM"] = a.compM / a.persM
    a["brecha"] = (100 * (a.wH - a.wM) / a.wH).round(1)
    a["ratioMH"] = (a.wM / a.wH).round(3)
    a["pct_mujer"] = (100 * a.persM / (a.persH + a.persM)).round(1)
    a["wH_miles"] = (a.wH / 1000).round(1)
    a["wM_miles"] = (a.wM / 1000).round(1)
    a = a.sort_values("brecha", ascending=False)
    a.to_csv(ROOT / "datasets" / "eea_brecha_genero_sector.csv", index=False, encoding="utf-8")
    print(a[["sector", "pct_mujer", "wH_miles", "wM_miles", "brecha", "ratioMH"]].to_string(index=False))
    tH = a.compH.sum() / a.persH.sum(); tM = a.compM.sum() / a.persM.sum()
    print(f"\nAGREGADO F2: salario H=S/{tH:,.0f}  M=S/{tM:,.0f}  brecha={100*(tH-tM)/tH:.1f}%  "
          f"%mujeres={100*a.persM.sum()/(a.persH.sum()+a.persM.sum()):.0f}%")


if __name__ == "__main__":
    main()
