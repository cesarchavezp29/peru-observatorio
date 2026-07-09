"""
fig_educacion_superior_area_tiempo.py - Expansion de la educacion superior por area 2004-2025 (M03)
====================================================================================================
Pregunta: el boom de la educacion superior en el Peru llego al campo, o se concentro en la ciudad?
Como evoluciono la brecha urbano-rural en acceso a educacion superior?

% de adultos 25+ con algun nivel de educacion SUPERIOR (p301a in 7-11: sup. no univ., univ.,
postgrado), por area (estrato 1-5 urbano, 6-8 rural), ponderado por factor07. Codigos 7-11
estables todo el periodo. Un plot. Run: python fig_educacion_superior_area_tiempo.py [--rebuild]
"""
from __future__ import annotations
from pathlib import Path
import sys
import numpy as np, pandas as pd
import figstyle as fs
import enaho_codes as ec

ROOT = Path(__file__).resolve().parents[1]; RAW = ROOT / "raw"
FIG = ROOT / "figures" / "05_demografia_salud_educacion"; FIG.mkdir(parents=True, exist_ok=True)
CSV = ROOT / "datasets" / "educacion_superior_area_tiempo_2004_2025.csv"


def rd(p):
    if not p.exists():
        return None
    try:
        import pyreadstat
        d, _ = pyreadstat.read_dta(str(p), encoding="latin1")
    except Exception:
        d = pd.read_stata(p, convert_categoricals=False)
    d.columns = [c.lower() for c in d.columns]
    return d


def wshare(mask01, w):
    m = np.asarray(mask01, float); w = np.asarray(w, float)
    ok = np.isfinite(m) & np.isfinite(w)
    return 100 * np.average(m[ok], weights=w[ok]) if ok.any() else np.nan


if CSV.exists() and "--rebuild" not in sys.argv:
    p = pd.read_csv(CSV)
else:
    rows = []
    for y in ec.years():
        df = rd(RAW / "educacion" / f"enaho-{y}-03.dta")
        if df is None or "p301a" not in df.columns or "estrato" not in df.columns:
            continue
        n = lambda c: pd.to_numeric(df[c], errors="coerce")
        edu = n("p301a"); edad = n("p208a"); est = n("estrato"); w = n("factor07")
        ad = edad >= 25
        sup = edu.isin([7, 8, 9, 10, 11])
        urb = ad & est.between(1, 5); rur = ad & est.between(6, 8)
        rec = {"year": y,
               "Urbano": wshare(sup[urb], w[urb]),
               "Rural": wshare(sup[rur], w[rur])}
        rows.append(rec)
        print(f"{y}: Urbano {rec['Urbano']:.1f}%  Rural {rec['Rural']:.1f}%  brecha {rec['Urbano']-rec['Rural']:.1f}pp")
    p = pd.DataFrame(rows).sort_values("year")
    p.to_csv(CSV, index=False)

fig, ax = fs.fig_ax()
ax.fill_between(p.year, p.Rural, p.Urbano, color=fs.GREY, alpha=0.12, zorder=1)
for col, c in [("Urbano", fs.NAVY), ("Rural", fs.CRANBERRY)]:
    ax.plot(p.year, p[col], "-o", color=c, lw=2.5, ms=4, mfc="white", mec=c, mew=1.4, zorder=5)
fs.end_labels(ax, [(f"Urbano  {p.Urbano.iloc[-1]:.0f}%", p.Urbano.iloc[-1], fs.NAVY),
                   (f"Rural  {p.Rural.iloc[-1]:.0f}%", p.Rural.iloc[-1], fs.CRANBERRY)],
              x_end=p.year.iloc[-1], fs=9.5)
g0 = p.Urbano.iloc[0] - p.Rural.iloc[0]; g1 = p.Urbano.iloc[-1] - p.Rural.iloc[-1]
ax.set_xlim(2003.5, 2031); ax.set_xticks(range(2004, 2026, 3)); ax.set_ylim(0, 45)
ax.set_ylabel("Adultos 25+ con educacion superior (%)"); ax.set_xlabel("")
gmax = (p["Urbano"] - p["Rural"]).max()
fs.statbox(ax, [
    "La educacion superior es un fenomeno casi URBANO: 1 de cada 3",
    f"adultos en la ciudad ({p.Urbano.iloc[-1]:.0f}%) vs 1 de cada 13 en el campo ({p.Rural.iloc[-1]:.0f}%).",
    f"La urbana se estanco (~34% desde 2008); la rural sube lento",
    f"desde una base minima. Brecha enorme y persistente (~{gmax:.0f}pp).",
], loc="upper left")
fs.source(fig, "Fuente: ENAHO 2004-2025 (INEI), modulo 03. Adultos 25+ con educacion superior (p301a 7-11), por area (estrato). Ponderado por factor07.")
fig.tight_layout()
for e in ("pdf", "png"):
    fig.savefig(FIG / f"fig_educacion_superior_area_tiempo.{e}", dpi=200, bbox_inches="tight")
print("OK -> fig_educacion_superior_area_tiempo.pdf")
