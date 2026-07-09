"""
build_panel_departamento.py - Panel DEPARTAMENTO x ANIO de indicadores clave 2004-2025
=======================================================================================
Construye un panel (25 deptos x 22 anios) de indicadores robustos de modulos con cobertura
completa: pobreza e ingreso real (M34), educacion/analfabetismo/lengua indigena (M03),
adultos mayores (M02), aseguramiento SIS (M04). Sirve para correlaciones ENTRE deptos
(corte transversal) vs DENTRO de deptos en el tiempo (efecto fijo). Pesos correctos por
modulo: M34/M03/M04 = factor07, M02 = facpob07. ingreso real = ipcr_0 (deflactado base 2025).
Salida: datasets/panel_departamento_2004_2025.csv (long: year, dpto, indicator, value).
Run: python build_panel_departamento.py
"""
from __future__ import annotations
from pathlib import Path
import numpy as np, pandas as pd
import enaho_codes as ec
from dataset_income import real_income

ROOT = Path(__file__).resolve().parents[1]; RAW = ROOT / "raw"
OUT = ROOT / "datasets" / "panel_departamento_2004_2025.csv"
EDU = {1: 0, 2: 0, 3: 3, 4: 6, 5: 9, 6: 11, 7: 13, 8: 14, 9: 14, 10: 17, 11: 19, 12: 6}
FOLDER = {"34": "sumaria", "03": "educacion", "02": "miembros", "04": "salud"}


def L(mod, year, cols=None):
    p = RAW / FOLDER[mod] / f"enaho-{year}-{mod}.dta"
    if not p.exists():
        return None
    try:
        import pyreadstat
        df, _ = (pyreadstat.read_dta(str(p), encoding="latin1", usecols=cols) if cols
                 else pyreadstat.read_dta(str(p), encoding="latin1"))
    except Exception:
        df = pd.read_stata(p, convert_categoricals=False)
    df.columns = [c.lower() for c in df.columns]
    df["dpto"] = df["ubigeo"].astype(str).str.strip().str.zfill(6).str[:2]
    return df


def num(s):
    return pd.to_numeric(s, errors="coerce")


def wshare(g, mask, w):
    """% ponderado por dpto de una mascara booleana."""
    d = pd.DataFrame({"dpto": g, "m": np.asarray(mask, float), "w": np.asarray(w, float)})
    d = d.dropna(subset=["m", "w"])
    return d.groupby("dpto").apply(lambda x: 100 * np.average(x["m"], weights=x["w"])
                                   if x["w"].sum() > 0 else np.nan, include_groups=False)


def wmean(g, x, w):
    d = pd.DataFrame({"dpto": g, "x": np.asarray(x, float), "w": np.asarray(w, float)})
    d = d.dropna(subset=["x", "w"])
    return d.groupby("dpto").apply(lambda r: np.average(r["x"], weights=r["w"])
                                   if r["w"].sum() > 0 else np.nan, include_groups=False)


rows = []


def add(year, ser, name):
    for dpto, val in ser.items():
        if pd.notna(val):
            rows.append({"year": year, "dpto": dpto, "indicator": name, "value": float(val)})


for y in ec.years():
    su = L("34", y)
    if su is not None:
        f = num(su.get("factor07")); mie = num(su.get("mieperho")); pw = f * mie
        pob = num(su.get("pobreza"))
        add(y, wshare(su["dpto"], pob.isin([1, 2]), pw), "pobreza")
    # ingreso real pc (deflactado) por dpto
    try:
        ri = real_income(y)
        ri["dpto"] = ri["ubigeo"].astype(str).str.zfill(6).str[:2]
        add(y, wmean(ri["dpto"], ri["ipcr_0"], ri["factornd07"]), "ingreso_real_pc")
    except Exception as e:
        print(f"{y}: ingreso FAIL {repr(e)[:60]}")
    e = L("03", y)
    if e is not None:
        f = num(e.get("factor07")); edad = num(e.get("p208a"))
        if edad is None or edad.isna().all():
            edad = pd.Series(np.nan, index=e.index)
        anios = num(e.get("p301a")).map(EDU)
        ad = edad >= 25; a15 = edad >= 15
        add(y, wmean(e["dpto"], anios.where(ad), f.where(ad)), "educ_anios_25")
        anlf = (num(e.get("p301a")) == 1)
        add(y, wshare(e["dpto"], anlf.where(a15), f.where(a15)), "analfabetismo_15")
        leng = num(e.get("p300a"))
        add(y, wshare(e["dpto"], leng.isin([1, 2, 3]).where(leng.isin([1, 2, 3, 4])), f), "lengua_indigena")
    m2 = L("02", y)
    if m2 is not None:
        fp = num(m2.get("facpob07"))
        if fp is None or fp.isna().all():
            fp = num(m2.get("factor07"))
        edad = num(m2.get("p208a"))
        add(y, wshare(m2["dpto"], edad >= 60, fp), "pct_60mas")
    s4 = L("04", y)
    if s4 is not None:
        f = num(s4.get("factor07"))
        add(y, wshare(s4["dpto"], num(s4.get("p4195")) == 1, f), "pct_sis")
    print(f"{y}: ok ({sum(1 for r in rows if r['year']==y)} dpto-indicator)")

out = pd.DataFrame(rows)
out.to_csv(OUT, index=False)
print(f"\nOK -> {OUT.name}  ({len(out)} filas, {out.dpto.nunique()} deptos, "
      f"{out.indicator.nunique()} indicadores, {out.year.nunique()} anios)")
