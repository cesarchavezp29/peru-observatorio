"""Produce informalidad_reconstruida.csv desde el modulo 05 crudo (2004-2025).

PORTADO SIN REFACTORIZAR de ENAHO_ANALYSIS/scripts/build_informalidad.py: la
regla operativa INEI (OIT 17 CIET) validada contra ocupinf (concordancia
94-97.5%), con sus trampas documentadas como codigo — el cambio de codigos de
p511a en 2012, el renombre p510a->p510a1, y el gate de insumos que marca
2004-2006 como NO construible en vez de reportar un valor enganoso.

Las demas tablas de la familia empleo (brechas salariales, PEA, NEET,
subempleo, estructura) siguen en pipeline-archive/ hasta su porteo (W3b).

Crudos: ENAHO_RAW (layout peru_raw/enaho de perudata: empleo_ingreso/enaho-YYYY-05.dta).

Run:
  ENAHO_RAW=... python pipeline/build_empleo.py
  ENAHO_RAW=... python pipeline/build_empleo.py --check-against data/datasets/informalidad_reconstruida.csv
"""
from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

import numpy as np
import pandas as pd

YEARS = list(range(2004, 2026))
OUT = Path(__file__).resolve().parent.parent / "data" / "datasets" / "informalidad_reconstruida.csv"


def L(raw: Path, year: int):
    p = raw / "empleo_ingreso" / f"enaho-{year}-05.dta"
    if not p.exists():
        return None
    try:
        import pyreadstat
        df, _ = pyreadstat.read_dta(str(p), encoding="latin1")
    except Exception:
        df = pd.read_stata(p, convert_categoricals=False)
    df.columns = [c.lower() for c in df.columns]
    return df


def num(d, c):
    if c not in d.columns:
        return pd.Series(np.nan, index=d.index)
    return pd.to_numeric(d[c], errors="coerce")


def reconstruct(df, year):
    cat = num(df, "p507").values
    formal_contract = [1, 2] if year <= 2011 else [1, 2, 6]
    cf = num(df, "p511a").isin(formal_contract).values
    if "p510a1" in df.columns:
        sector_formal = num(df, "p510a1").isin([1, 2]).values
    else:
        sector_formal = (num(df, "p510a") == 1).values
    informal = np.zeros(len(df), bool)
    informal[np.isin(cat, [5, 7])] = True
    dep = np.isin(cat, [3, 4, 6])
    informal[dep] = ~cf[dep]
    emp = np.isin(cat, [1, 2])
    informal[emp] = ~sector_formal[emp]
    return informal


def build(raw: Path) -> pd.DataFrame:
    rows = []
    for y in YEARS:
        df = L(raw, y)
        if df is None:
            continue
        oc = (num(df, "ocu500") == 1).values
        w = num(df, "fac500a")
        if w.isna().all():
            w = num(df, "factor07")
        ww = w.fillna(0).values
        cat = num(df, "p507")
        emp_m = oc & cat.isin([1, 2]).values
        dep_m = oc & cat.isin([3, 4, 6]).values
        reg_var = "p510a1" if "p510a1" in df.columns else "p510a"
        cov_reg = 1 - (num(df, reg_var)[emp_m].isna().mean() if emp_m.any() else 1)
        cov_con = 1 - (num(df, "p511a")[dep_m].isna().mean() if dep_m.any() else 1)
        construible = (cov_reg >= 0.8) and (cov_con >= 0.8)
        rec = reconstruct(df, y)
        has_off = "ocupinf" in df.columns
        off = (num(df, "ocupinf") == 1).values if has_off else None
        m = oc & np.isfinite(ww)
        rate_rec = 100 * np.average(rec[m], weights=ww[m])
        if has_off:
            moff = m & num(df, "ocupinf").notna().values
            conc = 100 * np.mean(rec[moff] == off[moff])
            rate_off = 100 * np.average(off[moff], weights=ww[moff])
        else:
            conc = np.nan
            rate_off = np.nan
        if has_off:
            fuente = "ocupinf oficial"
        elif construible:
            fuente = "reconstruido confiable (insumos OK)"
        else:
            fuente = "NO construible (faltan insumos)"
            rate_rec = np.nan
        rows.append({"year": y, "informal_reconstruido": rate_rec,
                     "informal_oficial": rate_off, "concordancia_%": conc,
                     "cobertura_registro": round(cov_reg, 2),
                     "cobertura_contrato": round(cov_con, 2), "fuente": fuente})
        print(f"{y}: reconstruido {rate_rec if np.isfinite(rate_rec) else float('nan'):5.1f}"
              f"  [{fuente}]")
    return pd.DataFrame(rows)


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--check-against", default=None)
    a = ap.parse_args()
    raw = Path(os.environ.get("ENAHO_RAW", "peru_raw/enaho"))
    if not raw.exists():
        print(f"FAIL: ENAHO_RAW no existe: {raw}")
        sys.exit(1)
    df = build(raw)
    if df.empty:
        print("FAIL: sin datos")
        sys.exit(1)

    if a.check_against:
        ref = pd.read_csv(a.check_against)
        # el duckdb del app recorta columnas (TRANSFORMS) pero el CSV committeado
        # es la salida completa del builder: comparar columna a columna
        if list(ref.columns) != list(df.columns) or len(ref) != len(df):
            print(f"FAIL forma: ref {ref.shape} {list(ref.columns)} vs new {df.shape}")
            sys.exit(1)
        bad = []
        for c in ref.columns:
            rv = pd.to_numeric(ref[c], errors="coerce")
            nv = pd.to_numeric(df[c], errors="coerce")
            if rv.notna().any():
                d = (rv - nv).abs().max()
                if pd.notna(d) and d > 1e-3:
                    bad.append((c, float(d)))
            elif not ref[c].astype(str).equals(df[c].reset_index(drop=True).astype(str)):
                bad.append((c, "texto"))
        if bad:
            print(f"FAIL: difiere del committeado: {bad}")
            sys.exit(1)
        print(f"CHECK OK: {len(ref)} filas x {len(ref.columns)} columnas coinciden")
        return

    df.to_csv(OUT, index=False)
    print(f"wrote {OUT}")


if __name__ == "__main__":
    main()
