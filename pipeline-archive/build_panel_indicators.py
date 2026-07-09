"""
build_panel_indicators.py - Panel nacional de indicadores ENAHO 2004-2025
==========================================================================
Motor que recorre los modulos con TODOS los anios en disco (nucleo 01,02,03,04,05,
34,37,85) y calcula ~22 indicadores nacionales PONDERADOS por anio. Cada modulo se
lee una vez por anio (fallback pyreadstat para Stata v110, 2005-2009). Salida tidy:
  datasets/panel_indicators.csv   (year, indicator, value, grupo)
La consumen fig_series_modulos.py (series de tiempo) y fig_correlaciones.py.

Run: python build_panel_indicators.py
"""
from __future__ import annotations
from pathlib import Path
import numpy as np, pandas as pd
import enaho_codes as ec

ROOT = Path(__file__).resolve().parents[1]; RAW = ROOT / "raw"; DATA = ROOT / "datasets"


def L(folder, mod, year, cols=None):
    p = RAW / folder / f"enaho-{year}-{mod}.dta"
    if not p.exists():
        return None
    try:
        import pyreadstat
        df, _ = pyreadstat.read_dta(str(p), encoding="latin1", usecols=cols) if cols else \
            pyreadstat.read_dta(str(p), encoding="latin1")
    except Exception:
        try:
            df = pd.read_stata(p, convert_categoricals=False)
        except Exception:
            return None
    df.columns = [c.lower() for c in df.columns]
    return df


def num(s):
    return pd.to_numeric(s, errors="coerce")


def W(mask, w):
    mask = np.atleast_1d(np.asarray(mask, float)); w = np.atleast_1d(np.asarray(w, float))
    if mask.shape != w.shape:
        return np.nan
    ok = np.isfinite(mask) & np.isfinite(w)
    return 100 * np.average(mask[ok], weights=w[ok]) if ok.any() else np.nan


def Wm(x, w):
    x = np.asarray(x, float); w = np.asarray(w, float); ok = np.isfinite(x) & np.isfinite(w)
    return np.average(x[ok], weights=w[ok]) if ok.any() else np.nan


def wmedian(x, w):
    x = np.asarray(x, float); w = np.asarray(w, float); ok = np.isfinite(x) & np.isfinite(w)
    x, w = x[ok], w[ok]
    if not len(x):
        return np.nan
    o = np.argsort(x); cw = np.cumsum(w[o]) / w[o].sum()
    return x[o][np.searchsorted(cw, 0.5)]


GRP = {}   # indicator -> grupo (modulo)
rows = []
for y in ec.years():
    rec = {}
    # --- M34 Sumaria (ancla: pobreza, tamano hogar, pesos) ---
    su = L("sumaria", "34", y)
    if su is not None:
        f = num(su.get("factor07")); mie = num(su.get("mieperho"))
        pw = f * mie
        pob = num(su.get("pobreza"))
        rec["pobreza"] = W(pob.isin([1, 2]), pw); GRP["pobreza"] = "34 Pobreza"
        rec["pobreza_extrema"] = W(pob == 1, pw); GRP["pobreza_extrema"] = "34 Pobreza"
        rec["tam_hogar"] = Wm(mie, f); GRP["tam_hogar"] = "34 Pobreza"
        su["hh"] = (su["conglome"].astype(str).str.zfill(6) + su["vivienda"].astype(str).str.zfill(3)
                    + su["hogar"].astype(str).str.zfill(2))
        wmap = su.set_index("hh")["factor07"]
    else:
        wmap = None
    # --- M01 Vivienda ---
    v = L("vivienda_hogar", "01", y)
    if v is not None:
        f = num(v.get("factor07"))
        rec["agua_red_dentro"] = W(num(v.get("p110")) == 1, f); GRP["agua_red_dentro"] = "01 Vivienda"
        rec["electricidad"] = W(num(v.get("p1121")) == 1, f); GRP["electricidad"] = "01 Vivienda"
        rec["cocina_gas"] = W((num(v.get("p1132")) == 1) | (num(v.get("p1133")) == 1), f); GRP["cocina_gas"] = "01 Vivienda"
        rec["celular"] = W(num(v.get("p1142")) == 1, f); GRP["celular"] = "01 Vivienda"
    # --- M02 Miembros (demografia, peso poblacional) ---
    m2 = L("miembros", "02", y)
    if m2 is not None:
        fp = num(m2.get("facpob07"));
        if fp.isna().all():
            fp = num(m2.get("factor07"))
        edad = num(m2.get("p208a"))
        rec["pct_60mas"] = W(edad >= 60, fp); GRP["pct_60mas"] = "02 Demografia"
        rec["pct_0a14"] = W(edad <= 14, fp); GRP["pct_0a14"] = "02 Demografia"
        rec["edad_mediana"] = wmedian(edad, fp); GRP["edad_mediana"] = "02 Demografia"
        jefa = (num(m2.get("p203")) == 1) & (num(m2.get("p207")) == 2)
        rec["pct_jefa_mujer"] = W(jefa.where(num(m2.get("p203")) == 1), fp); GRP["pct_jefa_mujer"] = "02 Demografia"
    # --- M03 Educacion ---
    e = L("educacion", "03", y)
    if e is not None:
        f = num(e.get("factor07")); edad = None
        EDU = {1: 0, 2: 0, 3: 3, 4: 6, 5: 9, 6: 11, 7: 13, 8: 14, 9: 14, 10: 17, 11: 19, 12: 6}
        anios = num(e.get("p301a")).map(EDU)
        # edad: M03 suele traer p208a propio; si no, traer de M02 por llave-persona
        if "p208a" in e.columns:
            edad = num(e["p208a"])
        elif m2 is not None:
            key = lambda d: (d["conglome"].astype(str).str.zfill(6) + d["vivienda"].astype(str).str.zfill(3)
                             + d["hogar"].astype(str).str.zfill(2) + num(d["codperso"]).fillna(0).astype(int).astype(str).str.zfill(2))
            e["pk"] = key(e); m2["pk"] = key(m2)
            e = e.merge(m2[["pk", "p208a"]], on="pk", how="left"); edad = num(e["p208a"])
        ad = (edad >= 25) if edad is not None else pd.Series(True, index=e.index)
        rec["educ_anios_25"] = Wm(anios.where(ad), f.where(ad)); GRP["educ_anios_25"] = "03 Educacion"
        rec["pct_superior_25"] = W((num(e.get("p301a")) >= 7).where(ad), f.where(ad)); GRP["pct_superior_25"] = "03 Educacion"
        anlf = (num(e.get("p302")) == 2)
        a15 = (edad >= 15) if edad is not None else pd.Series(True, index=e.index)
        rec["analfabetismo_15"] = W(anlf.where(a15), f.where(a15)); GRP["analfabetismo_15"] = "03 Educacion"
        rec["pct_lengua_indigena"] = W(num(e.get("p300a")).isin([1, 2, 3]).where(num(e.get("p300a")).isin([1, 2, 3, 4])), f)
        GRP["pct_lengua_indigena"] = "03 Educacion"
    # --- M04 Salud ---
    s4 = L("salud", "04", y)
    if s4 is not None:
        f = num(s4.get("factor07"))
        seg = pd.Series(False, index=s4.index)
        for k in range(1, 9):
            c = s4.get(f"p419{k}")
            if c is not None:
                seg = seg | (num(c) == 1)
        rec["pct_algun_seguro"] = W(seg, f); GRP["pct_algun_seguro"] = "04 Salud"
        rec["pct_sis"] = W(num(s4.get("p4195")) == 1, f); GRP["pct_sis"] = "04 Salud"
    # --- M05 Empleo ---
    m5 = L("empleo_ingreso", "05", y)
    if m5 is not None:
        fa = num(m5.get("fac500a"))
        if fa.isna().all():
            fa = num(m5.get("factor07"))
        occ = num(m5.get("ocu500")) == 1
        p507 = num(m5.get("p507")); br = num(m5.get("p506r4"))
        rec["pct_agricola"] = W(((br >= 111) & (br <= 322)).where(occ), fa.where(occ)); GRP["pct_agricola"] = "05 Empleo"
        rec["pct_independiente"] = W((p507 == 2).where(occ), fa.where(occ)); GRP["pct_independiente"] = "05 Empleo"
        rec["pct_asalariado"] = W(p507.isin([3, 4]).where(occ), fa.where(occ)); GRP["pct_asalariado"] = "05 Empleo"
        rec["pct_empleo_vulnerable"] = W(p507.isin([2, 5]).where(occ), fa.where(occ)); GRP["pct_empleo_vulnerable"] = "05 Empleo"
    # --- M37 Programas ---
    m37 = L("programas_sociales", "37", y)
    if m37 is not None and "p710_04" in m37.columns and "factor07" in m37.columns:
        f = num(m37["factor07"])
        rec["pct_juntos"] = W(num(m37["p710_04"]) == 1, f); GRP["pct_juntos"] = "37 Programas"
        rec["pct_pension65"] = W(num(m37["p710_05"]) == 1, f); GRP["pct_pension65"] = "37 Programas"
    # --- M85 Gobernabilidad (trust) ---
    g = L("gobernabilidad", "85", y)
    if g is not None and wmap is not None:
        TI = [f"p1_{i:02d}" for i in range(1, 22)]
        T = g[[c for c in TI if c in g.columns]].apply(num)
        ans = T.isin([1, 2, 3, 4, 5]); tru = T.isin([3, 4])
        g["ts"] = tru.sum(axis=1) / ans.sum(axis=1).replace(0, np.nan)
        g["hh"] = (g["conglome"].astype(str).str.zfill(6) + g["vivienda"].astype(str).str.zfill(3)
                   + g["hogar"].astype(str).str.zfill(2))
        g["fw"] = g["hh"].map(wmap)
        rec["confianza_inst"] = 100 * Wm(g["ts"], g["fw"]); GRP["confianza_inst"] = "85 Gobernabilidad"
    for k, val in rec.items():
        rows.append({"year": y, "indicator": k, "value": val, "grupo": GRP.get(k, "")})
    print(f"{y}: {len(rec)} indicadores")

out = pd.DataFrame(rows)
out.to_csv(DATA / "panel_indicators.csv", index=False)
print(f"\nOK -> datasets/panel_indicators.csv ({out['indicator'].nunique()} indicadores x {out['year'].nunique()} anios)")
