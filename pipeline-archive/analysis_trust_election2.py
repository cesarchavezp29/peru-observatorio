"""
analysis_trust_election2.py - refined: POLITICAL trust + income control
=======================================================================
Department-level OLS of 2nd-round vote share on:
  - trust in POLITICAL institutions (Congreso, partidos, Poder Judicial, gob. regional)
  - real per-capita income (control)

Models (per election):
  M1: vote ~ political_trust
  M2: vote ~ income
  M3: vote ~ political_trust + income   (does trust survive the income control?)

2021 election <- ENAHO 2021 ; 2026 election <- ENAHO 2025.
Robust (HC1) standard errors; standardized betas for comparability.
"""
from __future__ import annotations
import re
from pathlib import Path
import numpy as np, pandas as pd
import statsmodels.api as sm

from analysis_trust_election import DEPTS, vote_2021, vote_2026
from dataset_income import _canon_sumaria, real_income

ROOT = Path(__file__).resolve().parents[1]
RAW = ROOT / "raw"; DATA = ROOT / "datasets"

# political / representative institutions in module 85
POLITICAL = {"p1_08": "Gob. regional", "p1_09": "Poder Judicial",
             "p1_12": "Congreso", "p1_13": "Partidos politicos"}


def dept_trust_income(enaho_year: int) -> pd.DataFrame:
    # --- trust (module 85) ---
    gov = pd.read_stata(RAW / "gobernabilidad" / f"enaho-{enaho_year}-85.dta",
                        convert_categoricals=False)
    gov.columns = [c.lower() for c in gov.columns]
    pol = [c for c in POLITICAL if c in gov.columns]
    allp = [c for c in gov.columns if re.fullmatch(r"p1_\d{2}", c)]
    P = gov[pol].apply(pd.to_numeric, errors="coerce").where(lambda d: d.isin([1, 2, 3, 4]))
    A = gov[allp].apply(pd.to_numeric, errors="coerce").where(lambda d: d.isin([1, 2, 3, 4]))
    gov = gov.assign(
        trust_pol=(P >= 3).where(P.notna()).mean(axis=1),
        trust_all=(A >= 3).where(A.notna()).mean(axis=1),
        hhid=(gov["conglome"].astype(str).str.zfill(6) + gov["vivienda"].astype(str).str.zfill(3)
              + gov["hogar"].astype(str).str.zfill(2)))
    # --- income (sumaria, real pc) + weight ---
    inc = real_income(enaho_year)
    inc["hhid"] = (inc["conglome"].astype(str).str.zfill(6) + inc["vivienda"].astype(str).str.zfill(3)
                   + inc["hogar"].astype(str).str.zfill(2))
    g = gov.merge(inc[["hhid", "ipcr_0", "factor07", "mieperho"]], on="hhid", how="left")
    g["dpto"] = g["ubigeo"].astype(str).str.zfill(6).str[:2].astype(int)
    g["pw"] = g["factor07"] * g["mieperho"]
    rows = []
    for d, x in g.groupby("dpto"):
        m = x.dropna(subset=["factor07"])
        def wm(col):
            mm = m[col].notna()
            return np.average(m.loc[mm, col], weights=m.loc[mm, "factor07"])
        rows.append({"dpto": d, "department": DEPTS.get(d, str(d)),
                     "trust_pol": 100 * wm("trust_pol"), "trust_all": 100 * wm("trust_all"),
                     "income_pc": np.average(m.dropna(subset=["ipcr_0"])["ipcr_0"],
                                             weights=m.dropna(subset=["ipcr_0"])["pw"])})
    return pd.DataFrame(rows)


def z(s):
    return (s - s.mean()) / s.std(ddof=0)


def ols(df, yname, xnames):
    X = sm.add_constant(df[xnames]); y = df[yname]
    r = sm.OLS(y, X).fit(cov_type="HC1")
    zb = {}
    for x in xnames:
        zb[x] = sm.OLS(z(y), sm.add_constant(df[xnames].apply(z))).fit().params[x]
    return r, zb


def report(name, df, yname, ylabel):
    print("\n" + "=" * 74)
    print(f"{name}: {ylabel} (% by department, n={len(df)})")
    print("=" * 74)
    for tag, xs in [("M1 trust_pol", ["trust_pol"]),
                    ("M2 income", ["income_pc"]),
                    ("M3 trust_pol + income", ["trust_pol", "income_pc"])]:
        r, zb = ols(df, yname, xs)
        bits = []
        for x in xs:
            bits.append(f"{x}: b={r.params[x]:+.3f} (p={r.pvalues[x]:.3f}, beta*={zb[x]:+.2f})")
        print(f"  {tag:<26} R2={r.rsquared:.2f} | " + " ; ".join(bits))


def main():
    out = {}
    for el, eny, vfun, yname, ylab in [
        ("2021", 2021, vote_2021, "castillo_pct", "Castillo (izq) vote"),
        ("2026", 2025, vote_2026, "keiko_pct", "Keiko (der) vote")]:
        d = dept_trust_income(eny).merge(vfun(), on="dpto")
        d.to_csv(DATA / f"trust_income_vote_dept_{el}.csv", index=False)
        report(f"{el} 2V", d, yname, ylab)
        out[el] = d
    print("\nSaved datasets/trust_income_vote_dept_2021.csv, _2026.csv")


if __name__ == "__main__":
    main()
