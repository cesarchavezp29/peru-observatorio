"""
fig_brecha_salarial_sector.py - La brecha salarial de genero por industria (Peru 2025, M05)
=============================================================================================
Pregunta: en que ramas de actividad es mayor la brecha salarial entre hombres y mujeres?
Es parejo o hay industrias donde las mujeres quedan mucho mas rezagadas?

Razon ingreso laboral mediano mujer/hombre entre asalariados (ocu500==1, i524a1>0) por gran
sector CIIU rev4 (p506r4//100, mismo mapeo que fig_empleo_sectores). Intra-anual -> sin
deflactar. Se anota la participacion femenina del empleo asalariado de cada sector. Un plot.
Run: python fig_brecha_salarial_sector.py
"""
from __future__ import annotations
from pathlib import Path
import numpy as np, pandas as pd
import figstyle as fs

ROOT = Path(__file__).resolve().parents[1]; RAW = ROOT / "raw"
FIG = ROOT / "figures" / "07_empleo"; FIG.mkdir(parents=True, exist_ok=True)
CSV = ROOT / "datasets" / "brecha_salarial_sector_2025.csv"
YEAR = 2025

SECTORS = {
    "Agro, pesca y mineria": range(1, 10), "Manufactura": range(10, 34),
    "Construccion": range(41, 44), "Comercio": range(45, 48),
    "Transporte y comunic.": range(49, 64),
}
DIV2SEC = {d: name for name, rng in SECTORS.items() for d in rng}


def wmed(x, w):
    x = np.asarray(x, float); w = np.asarray(w, float)
    ok = np.isfinite(x) & np.isfinite(w) & (x > 0); x, w = x[ok], w[ok]
    if not len(x):
        return np.nan
    o = np.argsort(x); cw = np.cumsum(w[o]) / w[o].sum()
    return x[o][np.searchsorted(cw, 0.5)]


import pyreadstat
df, _ = pyreadstat.read_dta(str(RAW / "empleo_ingreso" / f"enaho-{YEAR}-05.dta"), encoding="latin1")
df.columns = [c.lower() for c in df.columns]
n = lambda c: pd.to_numeric(df[c], errors="coerce")
w = n("fac500a"); sx = n("p207"); wage = n("i524a1"); oc = n("ocu500")
div = (n("p506r4") // 100)
df["sector"] = div.map(DIV2SEC).fillna("Otros servicios")
base = (oc == 1) & (wage > 0)

rows = []
for sec in list(SECTORS) + ["Otros servicios"]:
    b = base & (df["sector"] == sec)
    mh = wmed(wage[b & (sx == 1)], w[b & (sx == 1)])
    mm = wmed(wage[b & (sx == 2)], w[b & (sx == 2)])
    wf = w[b & (sx == 2)].sum(); wt = w[b].sum()
    rows.append({"sector": sec, "ratio": mm / mh if mh else np.nan,
                 "share_fem": 100 * wf / wt if wt else np.nan,
                 "n": int(b.sum())})
    print(f"{sec:24} razon M/H={mm/mh:.2f}  brecha {100*(1-mm/mh):.0f}%  fem {100*wf/wt:.0f}%  n={int(b.sum())}")

r = pd.DataFrame(rows).dropna(subset=["ratio"]).sort_values("ratio").reset_index(drop=True)
r.to_csv(CSV, index=False)

fig, ax = fs.fig_ax(w=10.5, h=6.2)
y = np.arange(len(r))
ax.axvline(1.0, color=fs.GREY, lw=1.3, ls="--", zorder=1)
for yi, (_, row) in zip(y, r.iterrows()):
    rat = row["ratio"]
    c = fs.CRANBERRY if rat < 0.85 else fs.NAVY
    ax.plot([rat, 1.0], [yi, yi], "-", color=fs.GREY, lw=1.4, alpha=0.5, zorder=2)
    ax.plot(rat, yi, "o", color=c, ms=10, mfc="white", mec=c, mew=2.2, zorder=5)
    ax.annotate(f"{rat:.2f}", (rat, yi), textcoords="offset points", xytext=(0, 9),
                ha="center", fontsize=8.5, color=c)
    ax.annotate(f"{row['share_fem']:.0f}% mujeres", (1.005, yi), va="center", ha="left",
                fontsize=8, color=fs.GREY)
    if row["sector"] == "Construccion":   # paradoja de Simpson: aclarar la composicion
        ax.annotate("composicion: las pocas mujeres son\nempleadas de oficina (79%) vs obreros\nhombres (89%). Dentro de categoria la\nmujer gana menos (empleado 0.80, obrero 0.74)",
                    (rat, yi), textcoords="offset points", xytext=(-12, -6), ha="right", va="top",
                    fontsize=7.2, color=fs.GREY, style="italic")
ax.set_yticks(y); ax.set_yticklabels(r["sector"], fontsize=9.5)
ax.set_xlim(0.55, 1.18); ax.set_xlabel("Ingreso laboral mediano: mujer / hombre (asalariados, 2025)")
ax.set_ylabel("")
fs.source(fig, "Fuente: ENAHO 2025 (INEI), modulo 05. Asalariados (ocu500=1), ingreso dependiente i524a1, sector CIIU rev4 (p506r4). Mediana ponderada por fac500a.")
fig.tight_layout()
for e in ("pdf", "png"):
    fig.savefig(FIG / f"fig_brecha_salarial_sector.{e}", dpi=200, bbox_inches="tight")
print("OK -> fig_brecha_salarial_sector.pdf")
