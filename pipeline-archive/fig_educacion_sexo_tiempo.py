"""
fig_educacion_sexo_tiempo.py - Anios de escolaridad por sexo 2004-2025 (M03)
==============================================================================
Pregunta: las mujeres cerraron la brecha educativa con los hombres? En que momento? Contraste
con la brecha salarial (que SI persiste): ellas alcanzaron a los hombres en educacion pero
siguen ganando menos (ver fig_brecha_salarial_*).

Anios medios de escolaridad de adultos 25+ (edad para tener educacion completa), por sexo (p207),
ponderado por factor07. p301a -> anios via dict estandar INEI. Codigos 1-11 estables todo el
periodo (12 'basica especial' aparece 2017, marginal). Un plot. Run: python fig_educacion_sexo_tiempo.py [--rebuild]
"""
from __future__ import annotations
from pathlib import Path
import sys
import numpy as np, pandas as pd
import figstyle as fs
import enaho_codes as ec

ROOT = Path(__file__).resolve().parents[1]; RAW = ROOT / "raw"
FIG = ROOT / "figures" / "05_demografia_salud_educacion"; FIG.mkdir(parents=True, exist_ok=True)
CSV = ROOT / "datasets" / "educacion_sexo_tiempo_2004_2025.csv"
EDU = {1: 0, 2: 0, 3: 3, 4: 6, 5: 9, 6: 11, 7: 13, 8: 14, 9: 14, 10: 17, 11: 19, 12: 6}


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


def wmean(x, w):
    x = np.asarray(x, float); w = np.asarray(w, float)
    ok = np.isfinite(x) & np.isfinite(w)
    return np.average(x[ok], weights=w[ok]) if ok.any() else np.nan


if CSV.exists() and "--rebuild" not in sys.argv:
    p = pd.read_csv(CSV)
else:
    rows = []
    for y in ec.years():
        df = rd(RAW / "educacion" / f"enaho-{y}-03.dta")
        if df is None or "p301a" not in df.columns:
            continue
        n = lambda c: pd.to_numeric(df[c], errors="coerce")
        anios = n("p301a").map(EDU); edad = n("p208a"); sx = n("p207"); w = n("factor07")
        ad = edad >= 25
        rec = {"year": y}
        rec["Hombres"] = wmean(anios[ad & (sx == 1)], w[ad & (sx == 1)])
        rec["Mujeres"] = wmean(anios[ad & (sx == 2)], w[ad & (sx == 2)])
        rows.append(rec)
        print(f"{y}: Hombres {rec['Hombres']:.2f}  Mujeres {rec['Mujeres']:.2f}  brecha {rec['Hombres']-rec['Mujeres']:.2f} anios")
    p = pd.DataFrame(rows).sort_values("year")
    p.to_csv(CSV, index=False)

fig, ax = fs.fig_ax()
ax.fill_between(p.year, p.Mujeres, p.Hombres, color=fs.GREY, alpha=0.12, zorder=1)
for col, c in [("Hombres", fs.NAVY), ("Mujeres", fs.CRANBERRY)]:
    ax.plot(p.year, p[col], "-o", color=c, lw=2.5, ms=4, mfc="white", mec=c, mew=1.4, zorder=5)
fs.end_labels(ax, [(f"Hombres  {p.Hombres.iloc[-1]:.1f}", p.Hombres.iloc[-1], fs.NAVY),
                   (f"Mujeres  {p.Mujeres.iloc[-1]:.1f}", p.Mujeres.iloc[-1], fs.CRANBERRY)],
              x_end=p.year.iloc[-1], fs=9.5)
g0 = p.Hombres.iloc[0] - p.Mujeres.iloc[0]; g1 = p.Hombres.iloc[-1] - p.Mujeres.iloc[-1]
ax.set_xlim(2003.5, 2031); ax.set_xticks(range(2004, 2026, 3)); ax.set_ylim(6, 12)
ax.set_ylabel("Anios medios de escolaridad (adultos 25+)"); ax.set_xlabel("")
fs.statbox(ax, [
    f"La brecha educativa de genero se cierra: de {g0:.1f} anios a favor",
    f"de los hombres ({int(p.year.iloc[0])}) a solo {g1:.1f} ({int(p.year.iloc[-1])}). Entre los",
    "jovenes ellas ya superan a los hombres (ver cohorte). Pero",
    "ese avance educativo NO cierra la brecha salarial de genero.",
], loc="lower right")
fs.source(fig, "Fuente: ENAHO 2004-2025 (INEI), modulo 03. Adultos 25+, anios de escolaridad (p301a), por sexo (p207). Ponderado por factor07.")
fig.tight_layout()
for e in ("pdf", "png"):
    fig.savefig(FIG / f"fig_educacion_sexo_tiempo.{e}", dpi=200, bbox_inches="tight")
print("OK -> fig_educacion_sexo_tiempo.pdf")
