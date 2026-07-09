"""
fig_agro_volumen_valor.py - Volumen vs valor: el mapa economico de los cultivos (M22)
======================================================================================
Scatter de cultivos: x = numero de hogares que lo siembra (volumen, miles), y = valor
promedio de la cosecha por hogar productor (S/, escala log). Separa los STAPLES de
muchos hogares y bajo valor (papa, maiz) de los cultivos COMERCIALES de nicho y alto
valor por hogar (cafe, cacao, palto). Tamano del punto ~ valor total nacional.
Ponderado por factor07 de Sumaria.

Run: python fig_agro_volumen_valor.py
"""
from __future__ import annotations
import unicodedata
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


def deaccent(s):
    return unicodedata.normalize("NFKD", str(s)).encode("ascii", "ignore").decode("ascii")


def hh(d):
    return (d["conglome"].astype(str).str.zfill(6) + d["vivienda"].astype(str).str.zfill(3)
            + d["hogar"].astype(str).str.zfill(2))


dic = rd(RAW / "prod_agricola" / "enaho_tabla_agropecuario.dta")
cmap = {int(c): deaccent(p).strip().title() for c, p in zip(dic["codigo"], dic["producto"])}
su = pd.read_stata(RAW / "sumaria" / f"enaho-{YEAR}-34.dta", convert_categoricals=False)
su.columns = [c.lower() for c in su.columns]; su["hh"] = hh(su)
w = su.set_index("hh")["factor07"]

d = rd(RAW / "prod_agricola" / f"enaho-{YEAR}-22.dta"); d["hh"] = hh(d)
d["code"] = pd.to_numeric(d["p2100b"], errors="coerce")
d["fw"] = d["hh"].map(w)
d["val"] = pd.to_numeric(d["p21002n"], errors="coerce").fillna(0)
d = d.dropna(subset=["code", "fw"]); d["code"] = d["code"].astype(int)

# valor total por cultivo (ponderado) y N hogares (dedup hh x cultivo, ponderado)
val = d.assign(vw=d["val"] * d["fw"]).groupby("code")["vw"].sum()
nhh = d.drop_duplicates(["hh", "code"]).groupby("code")["fw"].sum()
g = pd.DataFrame({"val_total": val, "n_hh": nhh}).dropna()
g = g[g["n_hh"] >= 20000].sort_values("val_total", ascending=False).head(22)   # los 22 de mayor valor
g["val_per_hh"] = g["val_total"] / g["n_hh"]               # S/ por hogar productor
g["name"] = g.index.map(cmap)
g.to_csv(DATA / "agro_volumen_valor_2025.csv")
print(g.sort_values("val_per_hh", ascending=False)[["name", "n_hh", "val_per_hh"]].round(0).to_string(index=False))

fs.use()
fig, ax = plt.subplots(figsize=(11, 7.2))
x = g["n_hh"] / 1000
y = g["val_per_hh"]
sz = np.sqrt(g["val_total"]) / np.sqrt(g["val_total"]).max() * 900 + 30
ax.scatter(x, y, s=sz, color=fs.GOLD, alpha=0.55, edgecolor=fs.INK, lw=0.6, zorder=4)
ax.set_yscale("log")
try:
    fs.repel_labels(ax, x.values, y.values, g["name"].values, fs=8.5)
except Exception:
    for xi, yi, nm in zip(x, y, g["name"]):
        fs.halo_label(ax, xi, yi, nm, dx=3, dy=3)
medv = g["val_per_hh"].median()
ax.axhline(medv, color=fs.GREY, ls="--", lw=1, zorder=2)
ax.set_xlabel("Numero de hogares que lo siembra (miles)")
ax.set_ylabel("Valor de la cosecha por hogar productor (S/ , escala log)")
ax.set_title("Volumen vs valor: el mapa economico de los cultivos - ENAHO 2025", loc="left", fontsize=12.5)
fs.statbox(ax, ["Arriba-izq: nicho de alto valor (cafe, cacao)",
                "Abajo-der: staples de subsistencia (papa, maiz)",
                "tamano del punto ~ valor total nacional"], loc="upper right")
fs.source(fig, "Fuente: ENAHO Modulo 22 (INEI) 2025. Valor de produccion p21002n; hogares dedup por cultivo. "
          "Codigos: enaho_tabla_agropecuario.dta. Ponderado por factor07.")
fig.tight_layout()
for e in ("pdf", "png"):
    fig.savefig(FIG / f"fig_agro_volumen_valor.{e}", dpi=140, bbox_inches="tight")
print("OK -> figures/08_agro/fig_agro_volumen_valor.pdf")
