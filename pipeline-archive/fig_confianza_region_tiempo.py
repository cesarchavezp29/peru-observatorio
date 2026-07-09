"""
fig_confianza_region_tiempo.py - Confianza institucional por region natural 2007-2025 (M85)
=============================================================================================
Pregunta: la desconfianza en las instituciones es pareja en el territorio, o la Sierra (mas
rural e indigena) desconfia mas del Estado que la Costa? Como evoluciono?

Indice de confianza = % de instituciones (bateria comun p1_01-16) que el encuestado califica
Suficiente/Bastante (3-4); NoSabe(5)=no confia (en denominador, anti-artefacto). Por region
natural (dominio: Costa={1,2,3,8} incl. Lima, Sierra={4,5,6}, Selva={7}) y anio, ponderado por
factor07 (propio del modulo si existe, si no de Sumaria). Un plot. Bateria 2007-2011 y 2014-2025.
Run: python fig_confianza_region_tiempo.py [--rebuild]
"""
from __future__ import annotations
from pathlib import Path
import sys
import numpy as np, pandas as pd
import figstyle as fs
import enaho_codes as ec

ROOT = Path(__file__).resolve().parents[1]; RAW = ROOT / "raw"
FIG = ROOT / "figures" / "02_confianza"; FIG.mkdir(parents=True, exist_ok=True)
CSV = ROOT / "datasets" / "confianza_region_tiempo_2007_2025.csv"
HH = ["conglome", "vivienda", "hogar"]
ITEMS = [f"p1_{i:02d}" for i in range(1, 17)]
REGS = [("Costa", [1, 2, 3, 8]), ("Sierra", [4, 5, 6]), ("Selva", [7])]


def rd(p, cols=None):
    if not p.exists():
        return None
    try:
        import pyreadstat
        d, _ = pyreadstat.read_dta(str(p), encoding="latin1", usecols=cols) if cols else \
            pyreadstat.read_dta(str(p), encoding="latin1")
    except Exception:
        d = pd.read_stata(p, convert_categoricals=False)
        if cols:
            d = d[[c for c in d.columns if c.lower() in [x.lower() for x in cols]]]
    d.columns = [c.lower() for c in d.columns]
    return d


if CSV.exists() and "--rebuild" not in sys.argv:
    p = pd.read_csv(CSV)
else:
    rows = []
    for y in ec.years():
        gov = rd(RAW / "gobernabilidad" / f"enaho-{y}-85.dta")
        if gov is None or "p1_12" not in gov.columns or "dominio" not in gov.columns:
            continue
        items = [c for c in ITEMS if c in gov.columns]
        Traw = gov[items].apply(pd.to_numeric, errors="coerce")
        answered = Traw.isin([1, 2, 3, 4, 5]).sum(axis=1)
        gov["trust"] = Traw.isin([3, 4]).sum(axis=1) / answered.replace(0, np.nan)
        gov["dom"] = pd.to_numeric(gov["dominio"], errors="coerce")
        for c in HH:
            gov[c] = pd.to_numeric(gov[c], errors="coerce")
        su = rd(RAW / "sumaria" / f"enaho-{y}-34.dta", cols=HH + ["factor07"])
        su = su.drop_duplicates(HH).rename(columns={"factor07": "f_su"})
        for c in HH:
            su[c] = pd.to_numeric(su[c], errors="coerce")
        g = gov.merge(su[HH + ["f_su"]], on=HH, how="left")
        own = pd.to_numeric(g["factor07"], errors="coerce") if "factor07" in g.columns else pd.Series(np.nan, index=g.index)
        g["w"] = own.where(own.notna() & (own > 0), pd.to_numeric(g["f_su"], errors="coerce"))
        rec = {"year": y}
        for lab, codes in REGS:
            sub = g[g["dom"].isin(codes) & g["trust"].notna()]
            ww = pd.to_numeric(sub["w"], errors="coerce").fillna(0).values
            rec[lab] = 100 * np.average(sub["trust"].values, weights=ww) if len(sub) and ww.sum() > 0 else np.nan
        rows.append(rec)
        print(f"{y}: Costa {rec['Costa']:.1f}%  Sierra {rec['Sierra']:.1f}%  Selva {rec['Selva']:.1f}%")
    p = pd.DataFrame(rows).sort_values("year")
    p.to_csv(CSV, index=False)

fig, ax = fs.fig_ax()
cols = [fs.PALETTE[0], fs.PALETTE[1], fs.PALETTE[4]]
labels = []
for (lab, _), c in zip(REGS, cols):
    s = p.dropna(subset=[lab])
    ax.plot(s.year, s[lab], "-o", color=c, lw=2.3, ms=3.6, mfc="white", mec=c, mew=1.2, zorder=5)
    labels.append((f"{lab}  {s[lab].iloc[-1]:.0f}%", s[lab].iloc[-1], c))
fs.end_labels(ax, labels, x_end=p.year.max(), fs=8.5)
ax.set_xlim(2006.5, 2033); ax.set_xticks(range(2007, 2026, 3)); ax.set_ylim(0, 35)
ax.set_ylabel("Indice de confianza institucional (% instituciones que confia)"); ax.set_xlabel("")
fs.statbox(ax, [
    "La Sierra (mas rural e indigena) es la que MENOS confia en",
    "el Estado, de forma persistente. Costa y Selva confian algo",
    "mas y van casi parejas. Las tres caen juntas: la crisis",
    "erosiono la confianza en todo el pais (pico 2020, COVID).",
], loc="upper right")
fs.source(fig, "Fuente: ENAHO 2007-2025 (INEI), modulo 85. Indice = % instituciones (bateria comun p1_01-16) con confianza 3-4; NoSabe=no confia. Region natural (dominio), Costa incl. Lima. Ponderado factor07.")
fig.tight_layout()
for e in ("pdf", "png"):
    fig.savefig(FIG / f"fig_confianza_region_tiempo.{e}", dpi=200, bbox_inches="tight")
print("OK -> fig_confianza_region_tiempo.pdf")
