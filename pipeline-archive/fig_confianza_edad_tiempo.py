"""
fig_confianza_edad_tiempo.py - Confianza institucional por grupo de edad 2007-2025 (M85)
==========================================================================================
Pregunta: los jovenes confian menos en las instituciones que los mayores (desencanto
generacional), o al reves? Como evoluciono?

Indice de confianza = % de instituciones (bateria comun p1_01-16) calificadas Suficiente/
Bastante (3-4); NoSabe(5)=no confia (anti-artefacto). Edad del encuestado = M02 p208a por
llave-persona (M85 no trae edad). Tres grupos: 18-34, 35-54, 55+. Ponderado por factor07
(propio del modulo si existe, si no de Sumaria). Un plot. Bateria 2007-2011 y 2014-2025.
Run: python fig_confianza_edad_tiempo.py [--rebuild]
"""
from __future__ import annotations
from pathlib import Path
import sys
import numpy as np, pandas as pd
import figstyle as fs
import enaho_codes as ec

ROOT = Path(__file__).resolve().parents[1]; RAW = ROOT / "raw"
FIG = ROOT / "figures" / "02_confianza"; FIG.mkdir(parents=True, exist_ok=True)
CSV = ROOT / "datasets" / "confianza_edad_tiempo_2007_2025.csv"
HH = ["conglome", "vivienda", "hogar"]
ITEMS = [f"p1_{i:02d}" for i in range(1, 17)]
GROUPS = [("18-34", 18, 34), ("35-54", 35, 54), ("55+", 55, 120)]


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


def pkey(d):
    return (d["conglome"].astype("Int64").astype(str).str.zfill(6) + d["vivienda"].astype("Int64").astype(str).str.zfill(3)
            + d["hogar"].astype("Int64").astype(str).str.zfill(2) + d["codperso"].astype("Int64").astype(str).str.zfill(2))


if CSV.exists() and "--rebuild" not in sys.argv:
    p = pd.read_csv(CSV)
else:
    rows = []
    for y in ec.years():
        gov = rd(RAW / "gobernabilidad" / f"enaho-{y}-85.dta")
        if gov is None or "p1_12" not in gov.columns or "codperso" not in gov.columns:
            continue
        items = [c for c in ITEMS if c in gov.columns]
        Traw = gov[items].apply(pd.to_numeric, errors="coerce")
        answered = Traw.isin([1, 2, 3, 4, 5]).sum(axis=1)
        gov["trust"] = Traw.isin([3, 4]).sum(axis=1) / answered.replace(0, np.nan)
        for c in HH + ["codperso"]:
            gov[c] = pd.to_numeric(gov[c], errors="coerce")
        gov["pk"] = pkey(gov)
        m2 = rd(RAW / "miembros" / f"enaho-{y}-02.dta", cols=HH + ["codperso", "p208a"])
        for c in HH + ["codperso"]:
            m2[c] = pd.to_numeric(m2[c], errors="coerce")
        m2["pk"] = pkey(m2); m2["edad"] = pd.to_numeric(m2["p208a"], errors="coerce")
        g = gov.merge(m2[["pk", "edad"]].drop_duplicates("pk"), on="pk", how="left")
        su = rd(RAW / "sumaria" / f"enaho-{y}-34.dta", cols=HH + ["factor07"])
        su = su.drop_duplicates(HH).rename(columns={"factor07": "f_su"})
        for c in HH:
            su[c] = pd.to_numeric(su[c], errors="coerce")
        g = g.merge(su[HH + ["f_su"]], on=HH, how="left")
        own = pd.to_numeric(g["factor07"], errors="coerce") if "factor07" in g.columns else pd.Series(np.nan, index=g.index)
        g["w"] = own.where(own.notna() & (own > 0), pd.to_numeric(g["f_su"], errors="coerce"))
        rec = {"year": y}
        for lab, lo, hi in GROUPS:
            sub = g[(g["edad"] >= lo) & (g["edad"] <= hi) & g["trust"].notna()]
            ww = pd.to_numeric(sub["w"], errors="coerce").fillna(0).values
            rec[lab] = 100 * np.average(sub["trust"].values, weights=ww) if len(sub) and ww.sum() > 0 else np.nan
        rows.append(rec)
        print(f"{y}: 18-34 {rec['18-34']:.1f}%  35-54 {rec['35-54']:.1f}%  55+ {rec['55+']:.1f}%")
    p = pd.DataFrame(rows).sort_values("year")
    p.to_csv(CSV, index=False)

fig, ax = fs.fig_ax()
cols = [fs.PALETTE[1], fs.PALETTE[3], fs.PALETTE[0]]
labels = []
for (lab, _, _), c in zip(GROUPS, cols):
    s = p.dropna(subset=[lab])
    ax.plot(s.year, s[lab], "-o", color=c, lw=2.3, ms=3.6, mfc="white", mec=c, mew=1.2, zorder=5)
    labels.append((f"{lab}  {s[lab].iloc[-1]:.0f}%", s[lab].iloc[-1], c))
fs.end_labels(ax, labels, x_end=p.year.max(), fs=8.5)
ax.set_xlim(2006.5, 2033); ax.set_xticks(range(2007, 2026, 3)); ax.set_ylim(0, 35)
ax.set_ylabel("Indice de confianza institucional (% instituciones que confia)"); ax.set_xlabel("")
fs.statbox(ax, [
    "Al reves del 'desencanto juvenil': los JOVENES (18-34) confian",
    "MAS en las instituciones que los mayores, todos los anios. Y la",
    "brecha se ABRE: la confianza de los mayores cae mas rapido",
    "(55+ 25->13%). Todos bajan. (Pico 2020 COVID; 2012-13 sin bateria.)",
], loc="upper right")
fs.source(fig, "Fuente: ENAHO 2007-2025 (INEI), modulo 85. Indice = % instituciones (bateria comun p1_01-16) con confianza 3-4; NoSabe=no confia. Edad del encuestado (M02 p208a). Ponderado factor07.")
fig.tight_layout()
for e in ("pdf", "png"):
    fig.savefig(FIG / f"fig_confianza_edad_tiempo.{e}", dpi=200, bbox_inches="tight")
print("OK -> fig_confianza_edad_tiempo.pdf")
