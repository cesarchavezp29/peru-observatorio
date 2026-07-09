"""
fig_agro_mercado.py - Subsistencia vs mercado: el destino de la cosecha (M22)
==============================================================================
Modulo 22, destino de la produccion agricola por VALOR (S/):
  venta      = p21002b      autoconsumo = p21002f      total (item) = p21002n
(p21002t es el total a nivel HOGAR, casi todo NaN en filas-item; el total-item es
p21002n.) Para los cultivos de mayor valor se grafica el % del valor que se VENDE
(orientacion al mercado) vs el % autoconsumido (subsistencia). Ponderado por
factor07 de Sumaria. Linea de referencia = % vendido nacional.

Run: python fig_agro_mercado.py
"""
from __future__ import annotations
from pathlib import Path
import numpy as np, pandas as pd, pyreadstat, matplotlib.pyplot as plt
import figstyle as fs

ROOT = Path(__file__).resolve().parents[1]; RAW = ROOT / "raw"
FIG = ROOT / "figures" / "08_agro"; FIG.mkdir(parents=True, exist_ok=True)
DATA = ROOT / "datasets"
YEAR = 2025


def rd(p):
    df, _ = pyreadstat.read_dta(str(p), encoding="latin1"); df.columns = [c.lower() for c in df.columns]
    return df


def hh(d):
    return (d["conglome"].astype(str).str.zfill(6) + d["vivienda"].astype(str).str.zfill(3)
            + d["hogar"].astype(str).str.zfill(2))


import unicodedata
def deaccent(s):
    return unicodedata.normalize("NFKD", str(s)).encode("ascii", "ignore").decode("ascii")
dic = rd(RAW / "prod_agricola" / "enaho_tabla_agropecuario.dta")
cmap = {int(c): deaccent(p).strip().title() for c, p in zip(dic["codigo"], dic["producto"])}
su = pd.read_stata(RAW / "sumaria" / f"enaho-{YEAR}-34.dta", convert_categoricals=False)
su.columns = [c.lower() for c in su.columns]; su["hh"] = hh(su)
w = su.set_index("hh")["factor07"]

d = rd(RAW / "prod_agricola" / f"enaho-{YEAR}-22.dta"); d["hh"] = hh(d)
d["code"] = pd.to_numeric(d["p2100b"], errors="coerce")
d["fw"] = d["hh"].map(w)
for c, nm in [("p21002b", "venta"), ("p21002f", "auto"), ("p21002n", "total")]:
    d[nm] = pd.to_numeric(d[c], errors="coerce").fillna(0) * d["fw"]
d = d.dropna(subset=["code", "fw"])

# validacion de consistencia interna: venta+auto+resto = total
tot = d["total"].sum()
print(f"Destino del valor agricola nacional: vendido {100*d['venta'].sum()/tot:.1f}%, "
      f"autoconsumo {100*d['auto'].sum()/tot:.1f}%, resto {100*(tot-d['venta'].sum()-d['auto'].sum())/tot:.1f}%")
nat_sold = 100 * d["venta"].sum() / tot

g = d.groupby("code").agg(total=("total", "sum"), venta=("venta", "sum"), auto=("auto", "sum"))
g = g[g["total"] > 0]
g["pct_sold"] = 100 * g["venta"] / g["total"]
g["pct_auto"] = 100 * g["auto"] / g["total"]
g["name"] = g.index.astype(int).map(cmap)
top = g.sort_values("total", ascending=False).head(14).sort_values("pct_sold")
top.to_csv(DATA / "agro_mercado_2025.csv")
for _, r in top.iterrows():
    nm = str(r["name"]).encode("ascii", "replace").decode("ascii")
    print(f"  {nm:26s} vendido {r['pct_sold']:5.1f}%  autoconsumo {r['pct_auto']:5.1f}%")

fs.use()
fig, ax = plt.subplots(figsize=(11, 7))
ys = np.arange(len(top))
cols = [fs.CRANBERRY if p < nat_sold else fs.NAVY for p in top["pct_sold"]]
ax.barh(ys, top["pct_sold"].values, color=cols, edgecolor="white", zorder=3)
for i, (v, a) in enumerate(zip(top["pct_sold"].values, top["pct_auto"].values)):
    ax.text(v + 1, i, f"{v:.0f}% vendido", va="center", fontsize=8.5, color="#33373b")
ax.axvline(nat_sold, color=fs.GREY, ls="--", lw=1.2, zorder=2)
fs.halo_label(ax, nat_sold, len(top) - 0.5, f"nacional {nat_sold:.0f}%", dx=4, dy=0, fs=8.5, color=fs.GREY)
ax.set_yticks(ys); ax.set_yticklabels(top["name"], fontsize=9.5)
ax.set_xlim(0, 105); ax.set_xlabel("% del valor de la cosecha destinado a la VENTA")
ax.set_title("Subsistencia o mercado: el destino de cada cultivo - ENAHO 2025", loc="left", fontsize=12.5)
ax.grid(axis="y", alpha=0)
fs.halo_label(ax, 3, 0.4, "Rojo = bajo el promedio nacional (mas de subsistencia)", fs=8.5, color=fs.CRANBERRY)
fs.source(fig, "Fuente: ENAHO Modulo 22 (INEI) 2025, destino de la produccion por valor (venta p21002b / total p21002n). "
          "Codigos: enaho_tabla_agropecuario.dta. Ponderado por factor07.")
fig.tight_layout()
for e in ("pdf", "png"):
    fig.savefig(FIG / f"fig_agro_mercado.{e}", dpi=140, bbox_inches="tight")
print("OK -> figures/08_agro/fig_agro_mercado.pdf")
