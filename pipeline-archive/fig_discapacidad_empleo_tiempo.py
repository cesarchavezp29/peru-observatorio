"""
fig_discapacidad_empleo_tiempo.py - La exclusion laboral de la discapacidad (M04 x M05 x M34)
================================================================================================
MULTI-MODULO (M04 salud/discapacidad x M05 empleo x M34 pobreza): tasa de ocupacion de personas
en edad de trabajar (25-59) con y sin discapacidad, 2016-2025, con el dato de pobreza en el
recuadro.

Pregunta: que tan grande es la brecha de empleo entre personas con y sin discapacidad, y se
cierra o se ensancha?

CONSTRUCCION (anclado en M05, persona 25-59):
  - M04 (Salud): DISCAPACIDAD = cualquiera de p401h1..p401h6 == 1 (limitacion permanente para
    moverse, ver, hablar, oir, entender, relacionarse - set corto tipo Washington Group).
    Disponible 2016-2025. Merge por llave-persona (conglome+vivienda+hogar+codperso).
  - M05 (Empleo): ocu500 OCUPADO=1, p208a edad, fac500a peso.
  - M34 (Sumaria): pobreza in {1,2} (para el dato del recuadro). Merge por llave-hogar.
CODIGOS VERIFICADOS estables 2016-2025 (verify_codes.py): p401h1-6 (1=si/2=no), ocu500
(1=ocupado), pobreza. Universo 25-59 (aisla edad de trabajar; la prevalencia sube fuerte con la
edad -> la de toda la poblacion es mayor por los adultos mayores). Ponderado por fac500a.
Un plot. Run: python fig_discapacidad_empleo_tiempo.py [--rebuild]
"""
from __future__ import annotations
from pathlib import Path
import sys
import numpy as np, pandas as pd
import figstyle as fs

ROOT = Path(__file__).resolve().parents[1]; RAW = ROOT / "raw"
FIG = ROOT / "figures" / "05_demografia_salud_educacion"; FIG.mkdir(parents=True, exist_ok=True)
CSV = ROOT / "datasets" / "discapacidad_empleo_tiempo.csv"
PK = ["conglome", "vivienda", "hogar", "codperso"]; HK = ["conglome", "vivienda", "hogar"]
YEARS = list(range(2016, 2026))
H = [f"p401h{i}" for i in range(1, 7)]


def num(s):
    return pd.to_numeric(s, errors="coerce")


def rd(folder, mod, year, cols):
    import pyreadstat
    fp = RAW / folder / f"enaho-{year}-{mod}.dta"
    if not fp.exists():
        return None
    have = pyreadstat.read_dta(str(fp), metadataonly=True)[1].column_names
    cl = {c.lower(): c for c in have}
    d, _ = pyreadstat.read_dta(str(fp), encoding="latin1", usecols=[cl[c] for c in cols if c in cl])
    d.columns = [c.lower() for c in d.columns]
    return d


def key(d, keys):
    return d[keys].apply(lambda col: num(col).astype("Int64").astype(str)).agg("-".join, axis=1)


def wr(mask, base, w):
    b = base
    return 100 * w[mask & b].sum() / w[b].sum() if w[b].sum() > 0 else np.nan


if CSV.exists() and "--rebuild" not in sys.argv:
    p = pd.read_csv(CSV)
else:
    rows = []
    for y in YEARS:
        m4 = rd("salud", "04", y, PK + H)
        m5 = rd("empleo_ingreso", "05", y, PK + ["ocu500", "fac500a", "p208a"])
        su = rd("sumaria", "34", y, HK + ["pobreza"])
        if m4 is None or m5 is None or su is None:
            continue
        dis = pd.Series(False, index=m4.index)
        for c in H:
            if c in m4.columns:
                dis = dis | (num(m4[c]) == 1)
        m4["dis"] = dis; m4["pk"] = key(m4, PK)
        m5["pk"] = key(m5, PK); m5["hk"] = key(m5, HK); su["hk"] = key(su, HK)
        d = (m5.merge(m4.drop_duplicates("pk")[["pk", "dis"]], on="pk", how="left")
               .merge(su.drop_duplicates("hk")[["hk", "pobreza"]], on="hk", how="left"))
        a = num(d["p208a"]); w = num(d["fac500a"]).fillna(0); emp = (num(d["ocu500"]) == 1)
        D = d["dis"].fillna(False).astype(bool); wa = a.between(25, 59)
        poor = num(d["pobreza"]).isin([1, 2])
        rec = {"year": y, "prev": wr(D, wa, w),
               "emp_dis": wr(emp, wa & D, w), "emp_nodis": wr(emp, wa & ~D, w),
               "poor_dis": wr(poor, wa & D, w), "poor_nodis": wr(poor, wa & ~D, w)}
        rows.append(rec)
        print(f"{y}: prev {rec['prev']:4.1f} | emp DIS {rec['emp_dis']:4.1f} noDIS {rec['emp_nodis']:4.1f} "
              f"(gap {rec['emp_nodis']-rec['emp_dis']:4.1f}) | poor DIS {rec['poor_dis']:4.1f} noDIS {rec['poor_nodis']:4.1f}")
    p = pd.DataFrame(rows).sort_values("year")
    p.to_csv(CSV, index=False)

fs.use()
fig, ax = fs.fig_ax()
lines = [("Sin discapacidad", "emp_nodis", fs.NAVY), ("Con discapacidad", "emp_dis", fs.CRANBERRY)]
labels = []
for name, col, c in lines:
    s = p.dropna(subset=[col])
    ax.plot(s.year, s[col], "-o", color=c, lw=2.4, ms=4.2, mfc="white", mec=c, mew=1.2, zorder=5)
    labels.append((f"{name}  {s[col].iloc[-1]:.0f}%", s[col].iloc[-1], c))
fs.end_labels(ax, labels, x_end=p.year.max(), gap=4, fs=8.6)
ax.axvspan(2019.6, 2020.4, color=fs.GREY, alpha=0.10, zorder=0)
last = p.dropna(subset=["emp_dis"]).iloc[-1]
ax.set_xlim(2015.6, 2028.5); ax.set_xticks(range(2016, 2026, 2)); ax.set_ylim(40, 92)
ax.set_ylabel("% ocupado, 25-59 anios"); ax.set_xlabel("")
fs.statbox(ax, [
    "Las personas con discapacidad en edad de trabajar se",
    "ocupan ~30 pp menos y la brecha se ENSANCHA: su empleo",
    f"cayo a {last['emp_dis']:.0f}% mientras el resto sigue ~{last['emp_nodis']:.0f}%.",
    f"Tambien son mas pobres ({last['poor_dis']:.0f}% vs {last['poor_nodis']:.0f}% en {int(last['year'])}).",
    "M04 discapacidad x M05 empleo x M34 pobreza.",
], loc="lower left")
fs.source(fig, "Fuente: ENAHO 2016-2025 (INEI), modulo 04 (Salud, limitacion permanente p401h1-6) x modulo 05 (Empleo) "
               "x modulo 34 (pobreza). % ocupado 25-59 por discapacidad, ponderado por fac500a.")
fig.tight_layout()
for e in ("pdf", "png"):
    fig.savefig(FIG / f"fig_discapacidad_empleo_tiempo.{e}", dpi=200, bbox_inches="tight")
print("OK -> fig_discapacidad_empleo_tiempo.pdf")
