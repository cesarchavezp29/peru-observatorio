"""Produce transferencias_cobertura_2013_2025.csv (Juntos y Pension 65).

PORTADO SIN REFACTORIZAR de fig_transferencias_cobertura_tiempo.py: la trampa
p710 como codigo — el formato del modulo 37 cambia (ANCHO con dummies p710_NN
en 2013-2020 y 2025, LARGO con p712 en 2021-2024) y el codigo de Juntos corre
de 03 a 04 en 2014 (Wawa Wasi se partio y desplazo la lista).

Crudos: ENAHO_RAW (programas_sociales/enaho-YYYY-37.dta + sumaria).

Run:
  ENAHO_RAW=... python pipeline/build_transferencias.py
  ENAHO_RAW=... python pipeline/build_transferencias.py --check-against data/datasets/transferencias_cobertura_2013_2025.csv
"""
from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

import numpy as np
import pandas as pd

OUT = Path(__file__).resolve().parent.parent / "data" / "datasets" / "transferencias_cobertura_2013_2025.csv"
KEY = ["conglome", "vivienda", "hogar"]
YEARS = list(range(2013, 2026))
JUNTOS = {y: (3 if y == 2013 else 4) for y in YEARS}
PENSION65 = {y: 5 for y in YEARS}


def rd(p, cols=None):
    if not p.exists():
        return None
    try:
        import pyreadstat
        d, _ = pyreadstat.read_dta(str(p), encoding="latin1", usecols=cols) if cols else \
            pyreadstat.read_dta(str(p), encoding="latin1")
    except Exception:
        d = pd.read_stata(p, convert_categoricals=False)
        if cols:
            d = d[[c for c in d.columns if c.lower() in [x.lower() for x in cols]]]
    d.columns = [c.lower() for c in d.columns]
    return d


def hhid(d):
    return (pd.to_numeric(d["conglome"], errors="coerce").astype("Int64").astype(str).str.zfill(6)
            + pd.to_numeric(d["vivienda"], errors="coerce").astype("Int64").astype(str).str.zfill(3)
            + pd.to_numeric(d["hogar"], errors="coerce").astype("Int64").astype(str).str.zfill(2))


def wshare(mask01, w):
    m = np.asarray(mask01, float)
    w = np.asarray(w, float)
    ok = np.isfinite(m) & np.isfinite(w)
    return 100 * np.average(m[ok], weights=w[ok]) if ok.any() else np.nan


def build(raw: Path) -> pd.DataFrame:
    rows = []
    for y in YEARS:
        m = rd(raw / "programas_sociales" / f"enaho-{y}-37.dta")
        su = rd(raw / "sumaria" / f"enaho-{y}-34.dta", cols=KEY + ["factor07"])
        if m is None or su is None:
            print(f"{y}: falta archivo")
            continue
        m["hhid"] = hhid(m)
        su["hhid"] = hhid(su)
        su = su.drop_duplicates("hhid")
        jcol = f"p710_{JUNTOS[y]:02d}"
        pcol = f"p710_{PENSION65[y]:02d}"
        if jcol in m.columns:
            fmt = "ancho"
            flags = m[["hhid"]].copy()
            flags["juntos"] = (pd.to_numeric(m[jcol], errors="coerce") == 1).astype(float)
            flags["pension65"] = (pd.to_numeric(m[pcol], errors="coerce") == 1).astype(float)
            flags = flags.groupby("hhid", as_index=False).max()
        else:
            fmt = "largo"
            p712 = pd.to_numeric(m["p712"], errors="coerce")
            tmp = pd.DataFrame({"hhid": m["hhid"],
                                "juntos": (p712 == JUNTOS[y]).astype(float),
                                "pension65": (p712 == PENSION65[y]).astype(float)})
            flags = tmp.groupby("hhid", as_index=False).max()
        d = su.merge(flags, on="hhid", how="left")
        d["juntos"] = d["juntos"].fillna(0.0)
        d["pension65"] = d["pension65"].fillna(0.0)
        w = pd.to_numeric(d["factor07"], errors="coerce")
        rec = {"year": y, "fmt": fmt, "n_hh": len(d),
               "Juntos": wshare(d["juntos"], w), "Pension 65": wshare(d["pension65"], w)}
        rows.append(rec)
        print(f"{y} [{fmt:5s}] Juntos {rec['Juntos']:5.2f}%  Pension 65 {rec['Pension 65']:5.2f}%")
    return pd.DataFrame(rows).sort_values("year")


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
        if list(ref.columns) != list(df.columns) or len(ref) != len(df):
            print(f"FAIL forma: ref {ref.shape} {list(ref.columns)} vs new {df.shape} {list(df.columns)}")
            sys.exit(1)
        bad = []
        for c in ref.columns:
            rv = pd.to_numeric(ref[c], errors="coerce")
            nv = pd.to_numeric(df[c].reset_index(drop=True), errors="coerce")
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
