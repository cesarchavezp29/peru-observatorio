"""
analysis_trust_election.py - institutional trust vs 2nd-round vote, by department
=================================================================================
Question: in departments where people trust institutions LESS, who won the
presidential runoff (segunda vuelta)?

Trust  : ENAHO Module 85 (Gobernabilidad), dept-level weighted % of institutions
         trusted. 2021 election <- ENAHO 2021 ; 2026 election <- ENAHO 2025.
Votes  : ONPE district-level 2nd-round results (resultadosegundavuelta.onpe.gob.pe),
         aggregated to department.
         2021 2V: Castillo (Peru Libre, left/outsider) vs Keiko (Fuerza Popular, right)
         2026 2V: Keiko (Fuerza Popular, right) vs Juntos por el Peru (left)

Outputs (datasets/ , figures/):
  trust_vote_dept_2021.csv, trust_vote_dept_2026.csv
  fig_trust_vote.png/pdf
"""
from __future__ import annotations
import re, unicodedata
from pathlib import Path
import numpy as np, pandas as pd
import matplotlib.pyplot as plt

ROOT = Path(__file__).resolve().parents[1]
RAW = ROOT / "raw"
DATA = ROOT / "datasets"; FIG=ROOT/"figures"/"_archivo"; FIG.mkdir(parents=True,exist_ok=True)
ONPE = Path("D:/Investigacion/LavaJato/data/raw/onpe/resultados")

DEPTS = {1:"AMAZONAS",2:"ANCASH",3:"APURIMAC",4:"AREQUIPA",5:"AYACUCHO",6:"CAJAMARCA",
         7:"CALLAO",8:"CUSCO",9:"HUANCAVELICA",10:"HUANUCO",11:"ICA",12:"JUNIN",
         13:"LA LIBERTAD",14:"LAMBAYEQUE",15:"LIMA",16:"LORETO",17:"MADRE DE DIOS",
         18:"MOQUEGUA",19:"PASCO",20:"PIURA",21:"PUNO",22:"SAN MARTIN",23:"TACNA",
         24:"TUMBES",25:"UCAYALI"}


def norm(s):
    s = unicodedata.normalize("NFKD", str(s)).encode("ascii", "ignore").decode().upper().strip()
    return re.sub(r"\s+", " ", s)

NAME2CODE = {norm(v): k for k, v in DEPTS.items()}
NAME2CODE["APURIMAC"] = 3; NAME2CODE["JUNIN"] = 12


# ---------- trust by department (ENAHO module 85) ----------
def trust_by_dept(enaho_year: int) -> pd.DataFrame:
    gov = pd.read_stata(RAW / "gobernabilidad" / f"enaho-{enaho_year}-85.dta",
                        convert_categoricals=False)
    gov.columns = [c.lower() for c in gov.columns]
    items = [c for c in gov.columns if re.fullmatch(r"p1_\d{2}", c)]
    T = gov[items].apply(pd.to_numeric, errors="coerce").where(lambda d: d.isin([1,2,3,4]))
    gov["trust_share"] = (T >= 3).where(T.notna()).mean(axis=1)
    gov["dpto"] = gov["ubigeo"].astype(str).str.zfill(6).str[:2].astype(int)
    # weight: factor07 from sumaria (module 85 has no own weight)
    from dataset_income import _canon_sumaria
    su = pd.read_stata(_canon_sumaria(enaho_year), convert_categoricals=False)
    su.columns = [c.lower() for c in su.columns]
    su["hhid"] = (su["conglome"].astype(str).str.zfill(6)+su["vivienda"].astype(str).str.zfill(3)
                  +su["hogar"].astype(str).str.zfill(2))
    gov["hhid"] = (gov["conglome"].astype(str).str.zfill(6)+gov["vivienda"].astype(str).str.zfill(3)
                   +gov["hogar"].astype(str).str.zfill(2))
    gov = gov.merge(su[["hhid","factor07"]], on="hhid", how="left").dropna(subset=["factor07","trust_share"])
    rows = []
    for d, g in gov.groupby("dpto"):
        rows.append({"dpto": d, "department": DEPTS.get(d, str(d)),
                     "trust_pct": 100*np.average(g["trust_share"], weights=g["factor07"]),
                     "n_resp": len(g)})
    return pd.DataFrame(rows)


# ---------- 2021 2nd round (long) ----------
def vote_2021() -> pd.DataFrame:
    df = pd.read_csv(ONPE / "2021_2v" / "votacion-distrito-resultados.csv")
    df["dcode"] = df["departamento"].map(lambda x: NAME2CODE.get(norm(x)))
    df = df.dropna(subset=["dcode"])
    df["cand"] = np.where(df["AGRUPACION"].str.contains("PERU LIBRE", case=False), "castillo",
                  np.where(df["AGRUPACION"].str.contains("FUERZA POPULAR", case=False), "keiko", None))
    df = df.dropna(subset=["cand"])
    piv = df.groupby(["dcode","cand"])["TOTAL_VOTOS"].sum().unstack("cand").fillna(0)
    piv["castillo_pct"] = 100*piv["castillo"]/(piv["castillo"]+piv["keiko"])
    piv["keiko_pct"] = 100 - piv["castillo_pct"]
    piv["winner"] = np.where(piv["castillo_pct"] > 50, "Castillo (izq/outsider)", "Keiko (der)")
    return piv.reset_index().rename(columns={"dcode":"dpto"})


# ---------- 2026 2nd round (wide, has UBIGEO) ----------
def vote_2026() -> pd.DataFrame:
    df = pd.read_csv(ONPE / "2026_2v" / "presidencial_2v_distrito.csv")
    df.columns = [c.strip() for c in df.columns]
    juntos = [c for c in df.columns if "JUNTOS" in norm(c)][0]
    df["dpto"] = df["UBIGEO"].astype(str).str.zfill(6).str[:2].astype(int)
    g = df.groupby("dpto").agg(keiko=("fuerza_popular","sum"), juntos=(juntos,"sum")).reset_index()
    g["keiko_pct"] = 100*g["keiko"]/(g["keiko"]+g["juntos"])
    g["juntos_pct"] = 100 - g["keiko_pct"]
    g["winner"] = np.where(g["keiko_pct"] > 50, "Keiko (der)", "Juntos x Peru (izq)")
    return g


def regress(x, y):
    b1, b0 = np.polyfit(x, y, 1)
    r = np.corrcoef(x, y)[0,1]
    return b0, b1, r


def main():
    DATA.mkdir(exist_ok=True); FIG.mkdir(exist_ok=True)

    # ---- 2021 ----
    t21 = trust_by_dept(2021)
    v21 = vote_2021()
    m21 = t21.merge(v21, on="dpto").dropna(subset=["trust_pct","castillo_pct"])
    m21.to_csv(DATA / "trust_vote_dept_2021.csv", index=False)
    b0,b1,r21 = regress(m21["trust_pct"], m21["castillo_pct"])

    # ---- 2026 ----
    t25 = trust_by_dept(2025)
    v26 = vote_2026()
    m26 = t25.merge(v26, on="dpto").dropna(subset=["trust_pct","keiko_pct"])
    m26.to_csv(DATA / "trust_vote_dept_2026.csv", index=False)
    c0,c1,r26 = regress(m26["trust_pct"], m26["keiko_pct"])

    print("="*70)
    print("2021 2V: Castillo (izq/outsider) share vs dept institutional trust")
    print(f"  slope = {b1:+.2f} pp Castillo per +1pp trust  | r = {r21:+.2f}")
    lo = m21.nsmallest(5,"trust_pct"); hi = m21.nlargest(5,"trust_pct")
    print(f"  5 LOWEST-trust depts: " + ", ".join(f"{r.department}({r.trust_pct:.0f}%->Cast {r.castillo_pct:.0f}%)" for _,r in lo.iterrows()))
    print(f"  5 HIGHEST-trust depts:" + ", ".join(f"{r.department}({r.trust_pct:.0f}%->Cast {r.castillo_pct:.0f}%)" for _,r in hi.iterrows()))
    print(f"  -> low-trust winner: {lo['winner'].mode().iat[0]} | high-trust winner: {hi['winner'].mode().iat[0]}")
    print()
    print("2026 2V: Keiko (der) share vs dept institutional trust")
    print(f"  slope = {c1:+.2f} pp Keiko per +1pp trust  | r = {r26:+.2f}")
    lo2 = m26.nsmallest(5,"trust_pct"); hi2 = m26.nlargest(5,"trust_pct")
    print(f"  5 LOWEST-trust depts: " + ", ".join(f"{r.department}({r.trust_pct:.0f}%->Keiko {r.keiko_pct:.0f}%)" for _,r in lo2.iterrows()))
    print(f"  5 HIGHEST-trust depts:" + ", ".join(f"{r.department}({r.trust_pct:.0f}%->Keiko {r.keiko_pct:.0f}%)" for _,r in hi2.iterrows()))
    print(f"  -> low-trust winner: {lo2['winner'].mode().iat[0]} | high-trust winner: {hi2['winner'].mode().iat[0]}")
    print("="*70)

    # ---- figure ----
    fig, (a1, a2) = plt.subplots(1, 2, figsize=(13.5, 6))
    for ax, m, yc, lab, b, s, r, opp in [
        (a1, m21, "castillo_pct", "Castillo (Perú Libre, izq/outsider) — 2V 2021", b0, b1, r21, "Keiko"),
        (a2, m26, "keiko_pct",    "Keiko (Fuerza Popular, der) — 2V 2026", c0, c1, r26, "Juntos")]:
        ax.scatter(m["trust_pct"], m[yc], s=28, color="#1f4e79", zorder=3)
        for _, row in m.iterrows():
            ax.annotate(row["department"][:4], (row["trust_pct"], row[yc]), fontsize=6.5,
                        xytext=(2,2), textcoords="offset points", color="0.3")
        xs = np.linspace(m["trust_pct"].min(), m["trust_pct"].max(), 40)
        ax.plot(xs, b + s*xs, color="#c0392b", lw=2)
        ax.axhline(50, color="0.6", ls="--", lw=1)
        ax.set_xlabel("Confianza en instituciones (%), ENAHO depto")
        ax.set_ylabel(f"% voto {lab.split('(')[0].strip()}")
        ax.set_title(f"{lab}\nslope={s:+.2f}  r={r:+.2f}", fontsize=10)
        ax.grid(alpha=0.25)
    fig.suptitle("Confianza institucional vs voto en 2da vuelta, por departamento", fontsize=13, y=1.0)
    fig.tight_layout()
    for ext in ("pdf","png"):
        fig.savefig(FIG / f"fig_trust_vote.{ext}", dpi=160, bbox_inches="tight")
    print(f"Saved figures/fig_trust_vote.png + datasets/trust_vote_dept_{{2021,2026}}.csv")


if __name__ == "__main__":
    main()
