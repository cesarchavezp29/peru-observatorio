"""
fig_correlaciones.py - Correlaciones cruzadas entre modulos (departamental 2025)
=================================================================================
Construye ~15 indicadores por DEPARTAMENTO (25) en 2025, cruzando modulos, y grafica
la matriz de correlaciones (Pearson) como heatmap. Revela que cosas de distintos
modulos se mueven juntas en el territorio (p.ej. lengua indigena <-> pobreza,
educacion <-> ingreso, agua <-> SIS). Ponderado por factor07.

Run: python fig_correlaciones.py
"""
from __future__ import annotations
from pathlib import Path
import numpy as np, pandas as pd, matplotlib.pyplot as plt
import figstyle as fs
from dataset_income import real_income

ROOT = Path(__file__).resolve().parents[1]; RAW = ROOT / "raw"
FIG = ROOT / "figures" / "00_panorama"; FIG.mkdir(parents=True, exist_ok=True)
DATA = ROOT / "datasets"
Y = 2025


def rd(folder, mod):
    p = RAW / folder / f"enaho-{Y}-{mod}.dta"
    try:
        d = pd.read_stata(p, convert_categoricals=False)
    except ValueError:
        import pyreadstat; d, _ = pyreadstat.read_dta(str(p), encoding="latin1")
    d.columns = [c.lower() for c in d.columns]; return d


def num(s): return pd.to_numeric(s, errors="coerce")
def dep(d): return d["ubigeo"].astype(str).str.zfill(6).str[:2]
def hh(d): return d["conglome"].astype(str).str.zfill(6) + d["vivienda"].astype(str).str.zfill(3) + d["hogar"].astype(str).str.zfill(2)


def wmean_by(df, col, wcol, depcol):
    df = df.dropna(subset=[col, wcol])
    return df.groupby(depcol).apply(
        lambda g: np.average(g[col].astype(float), weights=g[wcol]) if len(g) else np.nan,
        include_groups=False)


cols = {}
# Sumaria: pobreza, ingreso real
su = rd("sumaria", "34"); su["dep"] = dep(su); su["hh"] = hh(su)
su["pobre"] = num(su["pobreza"]).isin([1, 2]).astype(float)
su["pw"] = num(su["factor07"]) * num(su["mieperho"])
cols["Pobreza"] = wmean_by(su, "pobre", "pw", "dep") * 100
inc = real_income(Y); inc["dep"] = dep(inc)
cols["Ingreso real pc"] = wmean_by(inc.assign(f=num(inc["factor07"])), "ipcr_0", "f", "dep")
# Educacion
e = rd("educacion", "03"); e["dep"] = dep(e)
EDU = {1: 0, 2: 0, 3: 3, 4: 6, 5: 9, 6: 11, 7: 13, 8: 14, 9: 14, 10: 17, 11: 19, 12: 6}
e["anios"] = num(e["p301a"]).map(EDU); e["f"] = num(e["factor07"])
e["ad"] = num(e.get("p208a")) >= 25
cols["Educacion (anios)"] = wmean_by(e[e["ad"]], "anios", "f", "dep")
e["anlf"] = (num(e["p302"]) == 2).astype(float)
cols["Analfabetismo"] = wmean_by(e, "anlf", "f", "dep") * 100
e["indig"] = num(e["p300a"]).isin([1, 2, 3]).astype(float)
cols["Lengua indigena"] = wmean_by(e[num(e["p300a"]).isin([1, 2, 3, 4])], "indig", "f", "dep") * 100
# Vivienda
v = rd("vivienda_hogar", "01"); v["dep"] = dep(v); v["f"] = num(v["factor07"])
cols["Agua dentro"] = wmean_by(v.assign(x=(num(v["p110"]) == 1).astype(float)), "x", "f", "dep") * 100
cols["Cocina a gas"] = wmean_by(v.assign(x=((num(v["p1132"]) == 1) | (num(v["p1133"]) == 1)).astype(float)), "x", "f", "dep") * 100
# Salud
s = rd("salud", "04"); s["dep"] = dep(s); s["f"] = num(s["factor07"])
cols["Afiliado SIS"] = wmean_by(s.assign(x=(num(s["p4195"]) == 1).astype(float)), "x", "f", "dep") * 100
# Empleo
m5 = rd("empleo_ingreso", "05"); m5["dep"] = dep(m5); m5["fa"] = num(m5.get("fac500a"))
occ = num(m5["ocu500"]) == 1; br = num(m5["p506r4"])
m5o = m5[occ].copy(); m5o["agr"] = ((br[occ] >= 111) & (br[occ] <= 322)).astype(float)
m5o["ind"] = (num(m5o["p507"]) == 2).astype(float)
cols["Empleo agricola"] = wmean_by(m5o, "agr", "fa", "dep") * 100
cols["Independiente"] = wmean_by(m5o, "ind", "fa", "dep") * 100
# Gobernabilidad
g = rd("gobernabilidad", "85"); g["dep"] = dep(g)
TI = [f"p1_{i:02d}" for i in range(1, 22)]; T = g[[c for c in TI if c in g.columns]].apply(num)
g["ts"] = T.isin([3, 4]).sum(axis=1) / T.isin([1, 2, 3, 4, 5]).sum(axis=1).replace(0, np.nan)
g = g.merge(su[["conglome", "vivienda", "hogar", "factor07"]], on=["conglome", "vivienda", "hogar"], how="left")
g["fw"] = num(g["factor07"])
cols["Confianza inst."] = wmean_by(g, "ts", "fw", "dep") * 100

M = pd.DataFrame(cols)
M.to_csv(DATA / "indicadores_departamento_2025.csv")
C = M.corr()
print(C.round(2).to_string())

fs.use()
fig, ax = plt.subplots(figsize=(11, 9.5))
im = ax.imshow(C, cmap="RdBu_r", vmin=-1, vmax=1)
ax.set_xticks(range(len(C))); ax.set_xticklabels(C.columns, rotation=45, ha="right", fontsize=9)
ax.set_yticks(range(len(C))); ax.set_yticklabels(C.index, fontsize=9)
for i in range(len(C)):
    for j in range(len(C)):
        r = C.iloc[i, j]
        ax.text(j, i, f"{r:.2f}", ha="center", va="center", fontsize=7.5,
                color="white" if abs(r) > 0.55 else fs.INK)
cb = fig.colorbar(im, fraction=0.046, pad=0.04); cb.set_label("correlacion de Pearson (entre departamentos)")
ax.set_title("Como se entrelazan los modulos del ENAHO: correlaciones entre 25 departamentos (2025)",
             loc="left", fontsize=12.5, pad=12)
fs.source(fig, "Fuente: ENAHO modulos 01,03,04,05,34,85 (INEI) 2025, agregados a departamento, ponderados por "
          "factor07. n=25 departamentos. Inferencia ecologica.")
fig.tight_layout()
for e_ in ("pdf", "png"):
    fig.savefig(FIG / f"fig_correlaciones.{e_}", dpi=140, bbox_inches="tight")
print("OK -> figures/00_panorama/fig_correlaciones.pdf")
