"""
fig_engel_elasticidades.py - Lujo o necesidad? Elasticidad-gasto de cada categoria (Peru 2025)
================================================================================================
Pregunta: cuando un hogar peruano tiene mas recursos, en que gasta el sol adicional? Que
categorias son LUJOS (elasticidad>1, suben mas que proporcional) y cuales NECESIDADES (<1)?

Metodo (Working-Leser, curva de Engel): para cada uno de los 8 grupos de la canasta,
  w_g = a + b * ln(gasto real pc total),  ponderado por factornd07 (hogares-persona).
Elasticidad-gasto = 1 + b / wbar_g. Datos: gasto real pc mensual POR GRUPO del hogar
(gasto_groups_hh, modulos 07-18+78 agregados por la metodologia oficial INEI, deflactados
base 2025, validado S/920.4 vs INEI S/920.0). Un solo plot: punto por grupo + IC95, linea en 1.
Run: python fig_engel_elasticidades.py
"""
from __future__ import annotations
from pathlib import Path
import numpy as np, pandas as pd
import figstyle as fs
from validate_gasto import gasto_groups_hh, GROUP_LABELS

ROOT = Path(__file__).resolve().parents[1]
FIG = ROOT / "figures" / "11_consumo"; FIG.mkdir(parents=True, exist_ok=True)
DATA = ROOT / "datasets"; CSV = DATA / "engel_elasticidades_2025.csv"
YEAR = 2025

df = gasto_groups_hh(YEAR)
gcols = ["g_" + k for k in GROUP_LABELS]
m = df["gpgru0"].gt(0) & df["factornd07"].gt(0) & np.isfinite(df["gpgru0"])
d = df.loc[m].copy()
w = d["factornd07"].values
lnx = np.log(d["gpgru0"].values)          # ln gasto real pc total
W = w.sum()

rows = []
for k in GROUP_LABELS:
    g = d["g_" + k].clip(lower=0).fillna(0).values
    wg = g / d["gpgru0"].values            # budget share del grupo
    wbar = np.sum(w * wg) / W               # share medio (ponderado)
    # WLS de wg ~ a + b*lnx  (ponderado por w)
    X = np.column_stack([np.ones_like(lnx), lnx])
    sw = np.sqrt(w)
    Xw, yw = X * sw[:, None], wg * sw
    beta, *_ = np.linalg.lstsq(Xw, yw, rcond=None)
    resid = yw - Xw @ beta
    dofadj = len(yw) - 2
    sigma2 = (resid @ resid) / dofadj
    cov = sigma2 * np.linalg.inv(Xw.T @ Xw)
    b, seb = beta[1], np.sqrt(cov[1, 1])
    elas = 1 + b / wbar
    se_elas = seb / wbar                     # delta method (wbar tratado como constante)
    rows.append({"grupo": GROUP_LABELS[k], "share_medio": 100 * wbar,
                 "b": b, "elasticidad": elas, "se": se_elas,
                 "lo": elas - 1.96 * se_elas, "hi": elas + 1.96 * se_elas})
    print(f"{GROUP_LABELS[k][:34]:34} w={100*wbar:4.1f}%  elasticidad={elas:.2f} (+-{1.96*se_elas:.2f})")

r = pd.DataFrame(rows).sort_values("elasticidad").reset_index(drop=True)
r.to_csv(CSV, index=False)

fig, ax = fs.fig_ax(w=10.5, h=6.4)
y = np.arange(len(r))
cols = [fs.CRANBERRY if e < 1 else fs.NAVY for e in r["elasticidad"]]
ax.axvline(1.0, color=fs.GREY, lw=1.3, ls="--", zorder=1)
for yi, (_, row), c in zip(y, r.iterrows(), cols):
    ax.plot([row.lo, row.hi], [yi, yi], "-", color=c, lw=2.0, alpha=0.55, zorder=3)
    ax.plot(row.elasticidad, yi, "o", color=c, ms=8, mfc="white", mec=c, mew=2.0, zorder=5)
    ax.annotate(f"{row.elasticidad:.2f}", (row.elasticidad, yi), textcoords="offset points",
                xytext=(0, 9), ha="center", fontsize=8.5, color=c)
ax.set_yticks(y); ax.set_yticklabels([g.replace(", ", ",\n") for g in r["grupo"]], fontsize=9)
ax.set_xlabel("Elasticidad-gasto (Working-Leser)"); ax.set_ylabel("")
ax.set_xlim(0.3, 1.7); ax.set_ylim(-0.6, len(r) - 0.3)
ax.annotate("necesidades", (0.985, -0.5), ha="right", va="center", fontsize=9.5,
            color=fs.CRANBERRY, style="italic")
ax.annotate("lujos", (1.015, -0.5), ha="left", va="center", fontsize=9.5,
            color=fs.NAVY, style="italic")
fs.source(fig, "Fuente: ENAHO 2025 (INEI), Sumaria. Curva de Engel Working-Leser por hogar, gasto real pc por grupo (base 2025), ponderado por factornd07.")
fig.tight_layout()
for e in ("pdf", "png"):
    fig.savefig(FIG / f"fig_engel_elasticidades.{e}", dpi=200, bbox_inches="tight")
print("OK -> fig_engel_elasticidades.pdf")
