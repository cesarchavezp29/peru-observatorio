"""
fig_educacion_superior_sexo_tiempo.py - Educacion superior por sexo 2004-2025 (M03)
=====================================================================================
Pregunta: la expansion de la educacion superior favorecio a las mujeres? Cerraron (o
superaron) a los hombres en acceso a educacion superior?

% de adultos 25+ con algun nivel de educacion SUPERIOR (p301a in 7-11), por sexo (p207),
ponderado por factor07. Codigos 7-11 estables. Un plot. Run: python fig_educacion_superior_sexo_tiempo.py [--rebuild]
"""
from __future__ import annotations
from pathlib import Path
import sys
import numpy as np, pandas as pd
import figstyle as fs
import enaho_codes as ec

ROOT = Path(__file__).resolve().parents[1]; RAW = ROOT / "raw"
FIG = ROOT / "figures" / "05_demografia_salud_educacion"; FIG.mkdir(parents=True, exist_ok=True)
CSV = ROOT / "datasets" / "educacion_superior_sexo_tiempo_2004_2025.csv"


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
        if df is None or "p301a" not in df.columns:
            continue
        n = lambda c: pd.to_numeric(df[c], errors="coerce")
        edu = n("p301a"); edad = n("p208a"); sx = n("p207"); w = n("factor07")
        ad = edad >= 25
        sup = edu.isin([7, 8, 9, 10, 11])
        rec = {"year": y,
               "Hombres": wshare(sup[ad & (sx == 1)], w[ad & (sx == 1)]),
               "Mujeres": wshare(sup[ad & (sx == 2)], w[ad & (sx == 2)])}
        rows.append(rec)
        print(f"{y}: Hombres {rec['Hombres']:.1f}%  Mujeres {rec['Mujeres']:.1f}%  brecha {rec['Hombres']-rec['Mujeres']:.1f}pp")
    p = pd.DataFrame(rows).sort_values("year")
    p.to_csv(CSV, index=False)

fig, ax = fs.fig_ax()
ax.fill_between(p.year, p.Mujeres, p.Hombres, color=fs.GREY, alpha=0.12, zorder=1)
for col, c in [("Hombres", fs.NAVY), ("Mujeres", fs.CRANBERRY)]:
    ax.plot(p.year, p[col], "-o", color=c, lw=2.5, ms=4, mfc="white", mec=c, mew=1.4, zorder=5)
fs.end_labels(ax, [(f"Hombres  {p.Hombres.iloc[-1]:.0f}%", p.Hombres.iloc[-1], fs.NAVY),
                   (f"Mujeres  {p.Mujeres.iloc[-1]:.0f}%", p.Mujeres.iloc[-1], fs.CRANBERRY)],
              x_end=p.year.iloc[-1], fs=9.5)
g0 = p.Hombres.iloc[0] - p.Mujeres.iloc[0]; g1 = p.Hombres.iloc[-1] - p.Mujeres.iloc[-1]
ax.set_xlim(2003.5, 2031); ax.set_xticks(range(2004, 2026, 3)); ax.set_ylim(0, 40)
ax.set_ylabel("Adultos 25+ con educacion superior (%)"); ax.set_xlabel("")
fs.statbox(ax, [
    f"Las mujeres acortaron la brecha en educacion superior: de {g0:.0f}pp",
    f"({int(p.year.iloc[0])}) a {abs(g1):.0f}pp ({int(p.year.iloc[-1])}). No la cierran del todo en el stock",
    "25+ (cohortes viejas pesan), pero entre jovenes ya la",
    "invirtieron. Aun asi, ganan menos (la brecha salarial sigue).",
], loc="upper left")
fs.source(fig, "Fuente: ENAHO 2004-2025 (INEI), modulo 03. Adultos 25+ con educacion superior (p301a 7-11), por sexo (p207). Ponderado por factor07.")
fig.tight_layout()
for e in ("pdf", "png"):
    fig.savefig(FIG / f"fig_educacion_superior_sexo_tiempo.{e}", dpi=200, bbox_inches="tight")
print("OK -> fig_educacion_superior_sexo_tiempo.pdf")
