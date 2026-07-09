"""
dataset_trust.py - trust in institutions + per-capita income (Module 85 x Sumaria)
==================================================================================
ENAHO Module 85 (Gobernabilidad) asks one selected adult per household:
"Actualmente, tiene Ud. confianza en [institucion]?"  on a 1-4 scale
  1 = Nada, 2 = Poco, 3 = Suficiente, 4 = Bastante   (5 = No sabe -> missing)
for ~21 institutions (p1_01 .. p1_21).

We build a per-respondent trust index and merge each respondent's household REAL
per-capita income (ipcr_0, from dataset_income) by household id. The merge is 1:1
on (conglome,vivienda,hogar) - one governance respondent per household - so NO
observation is dropped (the module-merge pitfall). Income is household-level and
broadcast to its respondent.

Outputs (datasets/):
  trust_income_<year>.csv        per respondent: income_pc, trust_share, trust_mean, weight
  trust_by_institution_<year>.csv national % trusting each institution (weighted)

Run: python dataset_trust.py            # default 2025
     python dataset_trust.py 2024
"""
from __future__ import annotations
import sys
from pathlib import Path
import numpy as np
import pandas as pd
import enaho_codes as ec
from dataset_income import real_income

ROOT = Path(__file__).resolve().parents[1]
RAW = ROOT / "raw"
OUTDIR = ROOT / "datasets"

INSTITUTIONS = {
    "p1_01": "Jurado Nacional de Elecciones", "p1_02": "ONPE", "p1_03": "RENIEC",
    "p1_04": "Municipalidad provincial", "p1_05": "Municipalidad distrital",
    "p1_06": "Policia Nacional", "p1_07": "Fuerzas Armadas", "p1_08": "Gobierno regional",
    "p1_09": "Poder Judicial", "p1_10": "Ministerio de Educacion",
    "p1_11": "Defensoria del Pueblo", "p1_12": "Congreso", "p1_13": "Partidos politicos",
    "p1_14": "Prensa escrita", "p1_15": "Radio/Television", "p1_16": "Iglesia catolica",
    "p1_17": "Procuraduria anticorrupcion", "p1_18": "Ministerio Publico/Fiscalia",
    "p1_19": "Contraloria", "p1_20": "SUNAT", "p1_21": "Comision anticorrupcion",
}


def _hhid(df):
    c = df["conglome"].astype(str).str.zfill(6)
    v = df["vivienda"].astype(str).str.zfill(3)
    h = df["hogar"].astype(str).str.zfill(2)
    return c + v + h


def main():
    year = int(sys.argv[1]) if len(sys.argv) > 1 else 2025
    OUTDIR.mkdir(exist_ok=True)

    gov = pd.read_stata(RAW / "gobernabilidad" / f"enaho-{year}-85.dta", convert_categoricals=False)
    gov.columns = [c.lower() for c in gov.columns]
    items = [c for c in INSTITUTIONS if c in gov.columns]
    print(f"{year}: module 85 respondents = {len(gov):,}; trust items = {len(items)}")

    # recode: 5 (no sabe) -> NaN; scale 1..4
    T = gov[items].apply(pd.to_numeric, errors="coerce")
    T = T.where(T.isin([1, 2, 3, 4]))
    trusts = (T >= 3)                                  # Suficiente/Bastante = trusts
    gov["trust_share"] = trusts.where(T.notna()).mean(axis=1)   # share of institutions trusted
    gov["trust_mean"] = T.mean(axis=1)                          # mean 1-4 score
    gov["hhid"] = _hhid(gov)

    # household income (per capita, real) from Sumaria
    inc = real_income(year)[["conglome", "vivienda", "hogar", "ipcr_0", "factor07",
                             "mieperho", "ubigeo"]].copy()
    inc["hhid"] = _hhid(inc)

    # 1:1 merge - audit N
    m = gov[["hhid", "trust_share", "trust_mean"]].merge(
        inc[["hhid", "ipcr_0", "factor07", "ubigeo"]], on="hhid", how="left")
    matched = m["ipcr_0"].notna().sum()
    print(f"  merge audit: {len(gov):,} respondents -> {matched:,} matched to income "
          f"({100*matched/len(gov):.1f}%), {len(gov)-matched} unmatched")
    m = m.rename(columns={"ipcr_0": "income_pc"}).dropna(subset=["income_pc", "trust_share"])
    m.to_csv(OUTDIR / f"trust_income_{year}.csv", index=False)

    # per-institution national % trusting (weighted by factor07)
    gov2 = gov.merge(inc[["hhid", "factor07"]], on="hhid", how="left").dropna(subset=["factor07"])
    rows = []
    for it in items:
        v = pd.to_numeric(gov2[it], errors="coerce")
        v = v.where(v.isin([1, 2, 3, 4]))
        ok = v.notna()
        share = np.average((v[ok] >= 3), weights=gov2.loc[ok, "factor07"])
        rows.append({"item": it, "institution": INSTITUTIONS[it],
                     "pct_trust": round(100 * share, 1), "n": int(ok.sum())})
    inst = pd.DataFrame(rows).sort_values("pct_trust", ascending=False)
    inst.to_csv(OUTDIR / f"trust_by_institution_{year}.csv", index=False)

    # national weighted trust
    nat = np.average(m["trust_share"], weights=m["factor07"])
    print(f"  national mean trust_share (weighted): {100*nat:.1f}% of institutions trusted")
    print(f"\n  Most trusted:  " + ", ".join(f"{r.institution} {r.pct_trust}%"
          for _, r in inst.head(3).iterrows()))
    print(f"  Least trusted: " + ", ".join(f"{r.institution} {r.pct_trust}%"
          for _, r in inst.tail(3).iterrows()))
    print(f"\n  Wrote trust_income_{year}.csv ({len(m):,} rows), trust_by_institution_{year}.csv")


if __name__ == "__main__":
    main()
