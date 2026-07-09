"""
fig_bienes_durables.py - Tenencia de bienes durables por decil de ingreso (M18 x M34)
======================================================================================
Modulo 18 (Equipamiento del Hogar), llave HOGAR-ITEM: una fila por (hogar, bien)
con p612n=codigo del bien y p612=tiene(1)/no(2). Se PIVOTA a hogar (un dummy por
bien), se une 1:1 a Sumaria (decil de ingreso real per capita) y se grafica el
gradiente de tenencia: para cada bien, % de hogares que lo posee por decil D1->D10.
Demuestra la regla "agregar el modulo-item a hogar antes de unir".

Run: python fig_bienes_durables.py
"""
from __future__ import annotations
from pathlib import Path
import numpy as np, pandas as pd, matplotlib.pyplot as plt
import figstyle as fs
from dataset_income import real_income

ROOT = Path(__file__).resolve().parents[1]; RAW = ROOT / "raw"
FIG = ROOT / "figures" / "06_vivienda"; FIG.mkdir(parents=True, exist_ok=True)
DATA = ROOT / "datasets"
YEAR = 2025

# bienes a mostrar: codigo p612n -> etiqueta corta + color
ITEMS = {12: ("Refrigeradora", fs.PALETTE[0]), 7: ("Computadora/laptop", fs.PALETTE[1]),
         13: ("Lavadora de ropa", fs.PALETTE[2]), 17: ("Auto/camioneta", fs.PALETTE[3]),
         14: ("Horno microondas", fs.PALETTE[4]), 2: ("TV a color", fs.PALETTE[5])}


def hh(d):
    return (d["conglome"].astype(str).str.zfill(6) + d["vivienda"].astype(str).str.zfill(3)
            + d["hogar"].astype(str).str.zfill(2))


def wdecile(x, w, n=10):
    x = np.asarray(x, float); w = np.asarray(w, float)
    o = np.argsort(x); cw = np.cumsum(w[o]) / w[o].sum()
    edges = np.searchsorted(cw, np.linspace(0, 1, n + 1)[1:-1])
    lab = np.zeros(len(x), int); lab[o] = np.digitize(np.arange(len(x)), edges) + 1
    return lab


m18 = pd.read_stata(RAW / "equipamiento_hogar" / f"enaho-{YEAR}-18.dta", convert_categoricals=False)
m18.columns = [c.lower() for c in m18.columns]; m18["hh"] = hh(m18)
m18["code"] = pd.to_numeric(m18["p612n"], errors="coerce")
m18["tiene"] = (pd.to_numeric(m18["p612"], errors="coerce") == 1).astype(float)
# pivote item -> hogar (un dummy por bien)
piv = m18.pivot_table(index="hh", columns="code", values="tiene", aggfunc="max")
piv = piv[[c for c in ITEMS if c in piv.columns]].rename(columns={c: f"b{c}" for c in ITEMS})

inc = real_income(YEAR); inc["hh"] = hh(inc)
d = piv.merge(inc[["hh", "ipcr_0", "factor07"]], on="hh", how="left").dropna(subset=["ipcr_0", "factor07"])
print(f"hogares: {len(d):,} (M18 pivotado x Sumaria 1:1)")
d["dec"] = wdecile(d["ipcr_0"].values, d["factor07"].values)

rows = []
for dec in range(1, 11):
    s = d[d["dec"] == dec]; w = s["factor07"].values
    rec = {"dec": dec}
    for c in ITEMS:
        rec[c] = 100 * np.average(s[f"b{c}"].fillna(0).values, weights=w)
    rows.append(rec)
g = pd.DataFrame(rows).set_index("dec")
g.to_csv(DATA / "bienes_durables_decil_2025.csv")
print("D1 vs D10:", {ITEMS[c][0]: (round(g.loc[1, c]), round(g.loc[10, c])) for c in ITEMS})

fs.use()
fig, ax = plt.subplots(figsize=(11, 6.4))
xs = np.arange(1, 11)
for c in ITEMS:
    lab, col = ITEMS[c]
    ax.plot(xs, g[c].values, "-o", color=col, lw=2.2, ms=4, mfc="white", mec=col, mew=1.4, label=lab)
    fs.halo_label(ax, 10, g.loc[10, c], f"{g.loc[10,c]:.0f}%", dx=6, dy=-3, color=col)
ax.set_xticks(xs); ax.set_xlim(0.6, 10.9); ax.set_ylim(0, 102)
ax.set_xlabel("Decil de ingreso real per capita"); ax.set_ylabel("% de hogares que posee el bien")
ax.set_title("Quien tiene que: bienes durables por decil de ingreso - ENAHO 2025", loc="left", fontsize=13)
ax.legend(loc="upper left", ncol=2)
fs.source(fig, "Fuente: ENAHO Modulo 18 (Equipamiento) x Sumaria (INEI) 2025. Modulo-item pivotado a hogar. "
          "Ponderado por factor07.")
fig.tight_layout()
for e in ("pdf", "png"):
    fig.savefig(FIG / f"fig_bienes_durables.{e}", dpi=140, bbox_inches="tight")
print("OK -> figures/06_vivienda/fig_bienes_durables.pdf")
