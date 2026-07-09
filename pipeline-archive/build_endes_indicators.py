"""
build_endes_indicators.py
=========================
National per-year ENDES indicators across modules -> datasets/endes_indicadores.csv.
Each indicator is weighted (v005/1e6) and validated in ballpark vs INEI/DHS reports.

From the cleaned files (datasets/endes_mujeres / _nacimientos):
  * tfr            Total Fertility Rate, ASFR over the 36 months before interview
                   (age-at-birth numerator, reconstructed 3-woman-year exposure denom).
  * adol_madre     % women 15-19 already mother or pregnant (CEB>0 or embarazada).
  * educ_anios     mean years of education, women 15-49.
  * superior_pct   % women 15-49 with higher education (educ_nivel==3).
  * edad_1er_hijo  mean age at first birth (v212), women who are mothers.

Read directly from recodes (content-detected, weighted by mother v005):
  * desnutricion   % children <5 with chronic malnutrition / stunting (hw70 < -200,
                   valid hw70 < 9990). REC44/anthropometry recode.
  * anticon_mod    % women 15-49 using a modern contraceptive method (v313==3). REC42.

Run: py -3.14 build_endes_indicators.py
"""
from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd
import pyreadstat

import endes_codes as ec
import endes_units as eu

ROOT = Path(__file__).resolve().parents[1]
RAW = ROOT / "raw" / "endes"
DATA = ROOT / "datasets"
AGES = [15, 20, 25, 30, 35, 40, 45]   # 5-yr group lower bounds, 15-49


def wmean(s, v, w):
    s = s.dropna(subset=[v, w])
    return np.average(s[v], weights=s[w]) if len(s) and s[w].sum() > 0 else np.nan


def wshare(mask, w):
    return 100 * w[mask].sum() / w.sum() if w.sum() > 0 else np.nan


def tfr_year(mu: pd.DataFrame, na: pd.DataFrame) -> float:
    """TFR from ASFR over 36 months pre-interview. mu=women (this yr), na=births (this yr)."""
    b = na.copy()
    b["ma"] = pd.to_numeric(b.get("madre_edad_al_nacer"), errors="coerce")
    if "cmc_entrevista" in b and "cmc_nac" in b:
        b["mago"] = pd.to_numeric(b["cmc_entrevista"], errors="coerce") - pd.to_numeric(b["cmc_nac"], errors="coerce")
    else:
        return np.nan
    b = b[(b["mago"] >= 0) & (b["mago"] < 36) & b["ma"].between(15, 49.999)]
    b["grp"] = (b["ma"] // 5 * 5).astype(int)
    num = b.groupby("grp").apply(lambda s: s["wt"].sum())          # weighted births last 3yr
    # exposure: each woman contributes 3 woman-years at ages (cur-0.5, -1.5, -2.5)
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
            tfr += births_a / exp[a]      # annual ASFR (num=3yr births, exp=3 woman-yrs)
    return 5 * tfr


def _read_recode(d: Path, need_cols: list[str], want: dict) -> pd.DataFrame | None:
    """Find a .sav containing all need_cols; read want vars + caseid + v005."""
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
    df = df.merge(vwt, on="caseid", how="inner")   # inner = true-year caseids only
    haz = pd.to_numeric(df["haz"], errors="coerce")
    df = df[haz < 9990]                       # drop flagged 9996-9998
    w = df["wt"].fillna(0).values
    return wshare((pd.to_numeric(df["haz"], errors="coerce") < -200).values, w)


def contra_year(d: Path, vwt: pd.DataFrame) -> float:
    df = _read_recode(d, ["v313", "v005"], {"meth": "v313", "wt_raw": "v005"})
    if df is None:
        return np.nan
    df["caseid"] = df["caseid"].astype(str).str.strip()
    df = df.merge(vwt[["caseid"]], on="caseid", how="inner")   # true-year caseids only
    df["wt"] = pd.to_numeric(df["wt_raw"], errors="coerce") / 1e6
    w = df["wt"].fillna(0).values
    return wshare((pd.to_numeric(df["meth"], errors="coerce") == 3).values, w)


def main():
    mu = pd.read_csv(DATA / "endes_mujeres_2004_2024.csv")
    na = pd.read_csv(DATA / "endes_nacimientos_2004_2024.csv")
    rows = []
    for y in sorted(mu["anio"].unique()):
        w = mu[mu.anio == y].copy()
        wv = w["wt"].fillna(0).values
        ceb = pd.to_numeric(w["hijos_nacidos"], errors="coerce")
        emb = pd.to_numeric(w.get("embarazada"), errors="coerce")
        adol = w[w["edad"].between(15, 19)]
        adol_m = ((pd.to_numeric(adol["hijos_nacidos"], errors="coerce") > 0) |
                  (pd.to_numeric(adol.get("embarazada"), errors="coerce") == 1)).values
        d = eu.dir_for(y)        # true-year source folder
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
        print(f"  {y}: TFR={rows[-1]['tfr']:.2f} adol={rows[-1]['adol_madre']:.1f}% "
              f"educ={rows[-1]['educ_anios']:.1f} sup={rows[-1]['superior_pct']:.1f}% "
              f"desnut={rows[-1]['desnutricion']:.1f}% anticon={rows[-1]['anticon_mod']:.1f}%")
    out = pd.DataFrame(rows)
    out.to_csv(DATA / "endes_indicadores.csv", index=False)
    print(f"\nOK -> datasets/endes_indicadores.csv ({len(out)} anios)")


if __name__ == "__main__":
    main()
