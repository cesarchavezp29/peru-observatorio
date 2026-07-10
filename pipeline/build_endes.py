"""Produce endes_indicadores.csv (TFR, maternidad adolescente, educacion,
desnutricion, anticoncepcion) 2004-2024.

PORTADO SIN REFACTORIZAR de build_endes_indicators.py, con la trampa de los
archivos ACUMULATIVOS 2004-2008 como codigo (endes_units verbatim inline):
2004-2007 salen del acumulado 194 y 2008 del 209, cada registro asignado a su
anio calendario verdadero via CMC.

INSUMOS DECLARADOS: los CSV limpios endes_mujeres/nacimientos_2004_2024
(construidos por clean_endes_women/nacimientos.py, publicados en
pipeline-archive — su porteo es W5c) + los recodes .sav crudos (ENDES_RAW,
layout <anio>_<codigo> del workspace o el equivalente de perudata.endes).

Run:
  ENDES_RAW=... ENDES_CLEAN=... python pipeline/build_endes.py [--check-against data/datasets/endes_indicadores.csv]
"""
from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

import numpy as np
import pandas as pd
import pyreadstat

DATASETS = Path(__file__).resolve().parent.parent / "data" / "datasets"
AGES = [15, 20, 25, 30, 35, 40, 45]

# --- endes_units verbatim (trampa acumulativa 2004-2008) -------------------
ENDES_CODE = {2004: 120, 2005: 150, 2006: 183, 2007: 194, 2008: 209, 2009: 238,
              2010: 260, 2011: 290, 2012: 323, 2013: 407, 2014: 441, 2015: 504,
              2016: 548, 2017: 605, 2018: 638, 2019: 691, 2020: 739, 2021: 760,
              2022: 786, 2023: 910, 2024: 968}
_SRC = {2004: "2007_194", 2005: "2007_194", 2006: "2007_194", 2007: "2007_194",
        2008: "2008_209"}
for _y in range(2009, 2025):
    _SRC[_y] = f"{_y}_{ENDES_CODE[_y]}"


def wmean(s, v, w):
    s = s.dropna(subset=[v, w])
    return np.average(s[v], weights=s[w]) if len(s) and s[w].sum() > 0 else np.nan


def wshare(mask, w):
    return 100 * w[mask].sum() / w.sum() if w.sum() > 0 else np.nan


def tfr_year(mu: pd.DataFrame, na: pd.DataFrame) -> float:
    b = na.copy()
    b["ma"] = pd.to_numeric(b.get("madre_edad_al_nacer"), errors="coerce")
    if "cmc_entrevista" in b and "cmc_nac" in b:
        b["mago"] = pd.to_numeric(b["cmc_entrevista"], errors="coerce") - pd.to_numeric(b["cmc_nac"], errors="coerce")
    else:
        return np.nan
    b = b[(b["mago"] >= 0) & (b["mago"] < 36) & b["ma"].between(15, 49.999)]
    b["grp"] = (b["ma"] // 5 * 5).astype(int)
    num = b.groupby("grp").apply(lambda s: s["wt"].sum())
    m = mu.dropna(subset=["edad", "wt"]).copy()
    exp = {a: 0.0 for a in AGES}
    for t in (0.5, 1.5, 2.5):
        age_then = m["edad"] - t
        grp = (age_then // 5 * 5)
        for a in AGES:
            exp[a] += m.loc[grp == a, "wt"].sum()
    tfr = 0.0
    for a in AGES:
        births_a = float(num.get(a, 0.0))
        if exp[a] > 0:
            tfr += births_a / exp[a]
    return 5 * tfr


def _read_recode(d: Path, need_cols, want) -> pd.DataFrame | None:
    for p in sorted(d.rglob("*.sav")):
        _, m = pyreadstat.read_sav(str(p), metadataonly=True)
        cl = {c.lower(): c for c in m.column_names}
        if all(c in cl for c in need_cols):
            src = [cl[c] for c in (["caseid"] + list(want.values())) if c in cl]
            df, _ = pyreadstat.read_sav(str(p), usecols=src)
            df.columns = [c.lower() for c in df.columns]
            return df.rename(columns={v: k for k, v in want.items() if v in df.columns})
    return None


def stunting_year(d: Path, vwt: pd.DataFrame) -> float:
    df = _read_recode(d, ["hw70"], {"haz": "hw70"})
    if df is None:
        return np.nan
    df["caseid"] = df["caseid"].astype(str).str.strip()
    df = df.merge(vwt, on="caseid", how="inner")
    haz = pd.to_numeric(df["haz"], errors="coerce")
    df = df[haz < 9990]
    w = df["wt"].fillna(0).values
    return wshare((pd.to_numeric(df["haz"], errors="coerce") < -200).values, w)


def contra_year(d: Path, vwt: pd.DataFrame) -> float:
    df = _read_recode(d, ["v313", "v005"], {"meth": "v313", "wt_raw": "v005"})
    if df is None:
        return np.nan
    df["caseid"] = df["caseid"].astype(str).str.strip()
    df = df.merge(vwt[["caseid"]], on="caseid", how="inner")
    df["wt"] = pd.to_numeric(df["wt_raw"], errors="coerce") / 1e6
    w = df["wt"].fillna(0).values
    return wshare((pd.to_numeric(df["meth"], errors="coerce") == 3).values, w)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--check-against", default=None)
    a = ap.parse_args()
    raw = Path(os.environ.get("ENDES_RAW", "peru_raw/endes"))
    clean = Path(os.environ.get("ENDES_CLEAN", str(DATASETS)))
    mu = pd.read_csv(clean / "endes_mujeres_2004_2024.csv")
    na = pd.read_csv(clean / "endes_nacimientos_2004_2024.csv")
    rows = []
    for y in sorted(mu["anio"].unique()):
        w = mu[mu.anio == y].copy()
        wv = w["wt"].fillna(0).values
        adol = w[w["edad"].between(15, 19)]
        adol_m = ((pd.to_numeric(adol["hijos_nacidos"], errors="coerce") > 0) |
                  (pd.to_numeric(adol.get("embarazada"), errors="coerce") == 1)).values
        d = raw / _SRC[int(y)]
        vwt = w[["caseid", "wt"]].assign(caseid=lambda x: x.caseid.astype(str).str.strip())
        rows.append({
            "anio": y,
            "tfr": tfr_year(w, na[na.anio_encuesta == y]),
            "adol_madre": wshare(adol_m, adol["wt"].fillna(0).values),
            "educ_anios": wmean(w[w.edad.between(15, 49)], "educ_anios", "wt"),
            "superior_pct": wshare((pd.to_numeric(w["educ_nivel"], errors="coerce") == 3).values, wv),
            "edad_1er_hijo": wmean(w, "edad_primer_hijo", "wt"),
            "desnutricion": stunting_year(d, vwt),
            "anticon_mod": contra_year(d, vwt),
        })
        print(f"  {y}: TFR={rows[-1]['tfr']:.2f} desnut={rows[-1]['desnutricion']:.1f}%")
    out = pd.DataFrame(rows)
    if a.check_against:
        ref = pd.read_csv(a.check_against)
        if list(ref.columns) != list(out.columns) or len(ref) != len(out):
            print(f"FAIL forma: ref {ref.shape} vs new {out.shape}")
            sys.exit(1)
        bad = []
        for c in ref.columns:
            d = (pd.to_numeric(ref[c], errors="coerce")
                 - pd.to_numeric(out[c].reset_index(drop=True), errors="coerce")).abs().max()
            if pd.notna(d) and d > 1e-3:
                bad.append((c, float(d)))
        if bad:
            print(f"FAIL: difiere del committeado: {bad}")
            sys.exit(1)
        print(f"CHECK OK: {len(ref)} filas x {len(ref.columns)} columnas coinciden")
        return
    out.to_csv(DATASETS / "endes_indicadores.csv", index=False)
    print(f"wrote endes_indicadores.csv ({len(out)} anios)")


if __name__ == "__main__":
    main()
