"""Produce la familia educacion (5 tablas) desde el modulo 03 crudo 2004-2025.

PORTADO SIN REFACTORIZAR de los cinco builders fig_* (la parte de datos, sin
figuras): analfabetismo 15+ por region natural (p302 con la regla del filtro
— a quien no se le pregunta se le asume alfabeto), anios de escolaridad por
cohorte quinquenal 25-69 (p301a->anios con el diccionario oficial), anios por
sexo 25+, y superior (p301a 7-11) por area (estrato 1-5 urbano / 6-8 rural)
y por sexo. Ponderado por factor07. Unica plomeria compartida: cada anio se
lee UNA vez con las columnas que las cinco tablas necesitan.

movilidad_educativa_tiempo (multi-modulo M02xM03) queda para su propio port.

Run:
  ENAHO_RAW=... python pipeline/build_educacion.py [--check-against data/datasets]
"""
from __future__ import annotations

import argparse
import os
import sys
import tempfile
from pathlib import Path

import numpy as np
import pandas as pd

DATASETS = Path(__file__).resolve().parent.parent / "data" / "datasets"
YEARS = list(range(2004, 2026))
EDU = {1: 0, 2: 0, 3: 3, 4: 6, 5: 9, 6: 11, 7: 13, 8: 14, 9: 14, 10: 17, 11: 19, 12: 6}
REGS = [("Costa", [1, 2, 3, 8]), ("Sierra", [4, 5, 6]), ("Selva", [7])]
COLS = ["p301a", "p302", "p207", "p208a", "dominio", "estrato", "factor07"]
TABLES = ["analfabetismo_region_tiempo_2004_2025.csv", "educacion_cohorte_2025.csv",
          "educacion_sexo_tiempo_2004_2025.csv",
          "educacion_superior_area_tiempo_2004_2025.csv",
          "educacion_superior_sexo_tiempo_2004_2025.csv"]


def rd(p, cols):
    if not p.exists():
        return None
    import pyreadstat
    have = pyreadstat.read_dta(str(p), metadataonly=True)[1].column_names
    cl = {c.lower(): c for c in have}
    use = [cl[c] for c in cols if c in cl]
    try:
        d, _ = pyreadstat.read_dta(str(p), encoding="latin1", usecols=use)
    except Exception:
        d = pd.read_stata(p, convert_categoricals=False, columns=use)
    d.columns = [c.lower() for c in d.columns]
    return d


def wshare(mask01, w):
    m = np.asarray(mask01, float)
    w = np.asarray(w, float)
    ok = np.isfinite(m) & np.isfinite(w)
    return 100 * np.average(m[ok], weights=w[ok]) if ok.any() else np.nan


def wmean(x, w):
    x = np.asarray(x, float)
    w = np.asarray(w, float)
    ok = np.isfinite(x) & np.isfinite(w)
    return np.average(x[ok], weights=w[ok]) if ok.any() else np.nan


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--check-against", default=None)
    a = ap.parse_args()
    raw = Path(os.environ.get("ENAHO_RAW", "peru_raw/enaho"))
    if not raw.exists():
        print(f"FAIL: ENAHO_RAW no existe: {raw}")
        sys.exit(1)
    outdir = Path(tempfile.mkdtemp()) if a.check_against else DATASETS

    ana_rows, sexo_rows, supa_rows, sups_rows = [], [], [], []
    coh_df = None
    for y in YEARS:
        df = rd(raw / "educacion" / f"enaho-{y}-03.dta", COLS)
        if df is None:
            continue
        n = lambda c: pd.to_numeric(df[c], errors="coerce") if c in df.columns \
            else pd.Series(np.nan, index=df.index)
        w = n("factor07")
        edad = n("p208a")
        # analfabetismo por region natural
        if "p302" in df.columns and "dominio" in df.columns:
            lee = n("p302")
            dom = n("dominio")
            a15 = (edad >= 15)
            ana = (lee == 2).where(a15, np.nan)
            rec = {"year": y}
            for lab, codes in REGS:
                m = a15 & dom.isin(codes)
                rec[lab] = wshare(ana[m], w[m])
            rec["Nacional"] = wshare(ana[a15], w[a15])
            ana_rows.append(rec)
        if "p301a" in df.columns:
            anios = n("p301a").map(EDU)
            sx = n("p207")
            ad = edad >= 25
            sexo_rows.append({"year": y,
                              "Hombres": wmean(anios[ad & (sx == 1)], w[ad & (sx == 1)]),
                              "Mujeres": wmean(anios[ad & (sx == 2)], w[ad & (sx == 2)])})
            edu = n("p301a")
            sup = edu.isin([7, 8, 9, 10, 11])
            if "estrato" in df.columns:
                est = n("estrato")
                urb = ad & est.between(1, 5)
                rur = ad & est.between(6, 8)
                supa_rows.append({"year": y, "Urbano": wshare(sup[urb], w[urb]),
                                  "Rural": wshare(sup[rur], w[rur])})
            sups_rows.append({"year": y,
                              "Hombres": wshare(sup[ad & (sx == 1)], w[ad & (sx == 1)]),
                              "Mujeres": wshare(sup[ad & (sx == 2)], w[ad & (sx == 2)])})
        # cohortes: solo el anio 2025
        if y == 2025 and "p301a" in df.columns:
            d2 = pd.DataFrame({"anios": n("p301a").map(EDU), "edad": edad,
                               "sexo": n("p207"), "w": w})
            d2["nac"] = 2025 - d2["edad"]
            d2 = d2[(d2.edad >= 25) & (d2.edad <= 69)].dropna(subset=["anios", "nac", "sexo", "w"]).copy()
            d2["coh"] = (d2["nac"] // 5) * 5
            rows = []
            for coh, g in d2.groupby("coh"):
                if coh < 1956:
                    continue
                rec = {"cohorte": int(coh)}
                for sxv, name in [(1, "Hombres"), (2, "Mujeres")]:
                    s = g[g.sexo == sxv]
                    rec[name] = np.average(s["anios"], weights=s["w"]) if len(s) else np.nan
                rec["n"] = len(g)
                rows.append(rec)
            coh_df = pd.DataFrame(rows).sort_values("cohorte")
        print(f"  {y} ok")

    pd.DataFrame(ana_rows).to_csv(outdir / TABLES[0], index=False)
    coh_df.to_csv(outdir / TABLES[1], index=False)
    pd.DataFrame(sexo_rows).sort_values("year").to_csv(outdir / TABLES[2], index=False)
    pd.DataFrame(supa_rows).to_csv(outdir / TABLES[3], index=False)
    pd.DataFrame(sups_rows).to_csv(outdir / TABLES[4], index=False)

    if a.check_against:
        refdir = Path(a.check_against)
        bad = 0
        for nme in TABLES:
            ref = pd.read_csv(refdir / nme)
            new = pd.read_csv(outdir / nme)
            if list(ref.columns) != list(new.columns) or len(ref) != len(new):
                print(f"  FAIL forma {nme}: ref {ref.shape} vs new {new.shape}")
                bad += 1
                continue
            ok = True
            for c in ref.columns:
                rv = pd.to_numeric(ref[c], errors="coerce")
                nv = pd.to_numeric(new[c], errors="coerce")
                if rv.notna().any():
                    d = (rv - nv).abs().max()
                    if pd.notna(d) and d > 1e-3:
                        print(f"  FAIL {nme} col {c}: max diff {d}")
                        ok = False
                        break
            bad += 0 if ok else 1
        print(f"comparadas {len(TABLES)} tablas, {bad} con diferencias")
        sys.exit(1 if bad else 0)


if __name__ == "__main__":
    main()
