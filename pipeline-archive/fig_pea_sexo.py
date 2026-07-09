"""
fig_pea_sexo.py - Participacion en la fuerza de trabajo por sexo 2004-2025 (M05)
================================================================================
Desagregacion por SEXO. Tasa de participacion = PEA / poblacion en edad de trabajar (14+).
PEA = ocu500 in {1,2,3} (ocupado + desocupado abierto/oculto); p207 sexo (1=H,2=M),
peso fac500a. Conecta con la expansion educativa de las mujeres (ver fig_educacion_cohorte):
muestra si esas ganancias se tradujeron en entrada al mercado laboral. Un plot, figstyle.
Run: python fig_pea_sexo.py [--rebuild]
"""
from __future__ import annotations
from pathlib import Path
import sys
import numpy as np, pandas as pd
import figstyle as fs
import enaho_codes as ec

ROOT = Path(__file__).resolve().parents[1]; RAW = ROOT / "raw"
FIG = ROOT / "figures" / "07_empleo"; FIG.mkdir(parents=True, exist_ok=True)
DATA = ROOT / "datasets"; CSV = DATA / "pea_sexo_2004_2025.csv"


def L(year):
    p = RAW / "empleo_ingreso" / f"enaho-{year}-05.dta"
    if not p.exists():
        return None
    try:
        import pyreadstat
        df, _ = pyreadstat.read_dta(str(p), encoding="latin1")
    except Exception:
        df = pd.read_stata(p, convert_categoricals=False)
    df.columns = [c.lower() for c in df.columns]
    return df


if CSV.exists() and "--rebuild" not in sys.argv:
    p = pd.read_csv(CSV)
else:
    rows = []
    for y in ec.years():
        df = L(y)
        if df is None or "ocu500" not in df.columns:
            continue
        n = lambda c: pd.to_numeric(df[c], errors="coerce") if c in df.columns else pd.Series(np.nan, index=df.index)
        oc = n("ocu500"); sx = n("p207")
        w = n("fac500a"); w = w.where(w.notna(), n("factor07"))
        edad = n("p208a")
        wt = (edad >= 14) if edad.notna().any() else oc.isin([1, 2, 3, 4])   # poblacion en edad de trabajar
        pea = oc.isin([1, 2, 3])
        ww = w.fillna(0).values
        rec = {"year": y}
        for s, name in [(1, "Hombres"), (2, "Mujeres")]:
            m = (sx == s) & wt
            mm = m.values & np.isfinite(ww)
            rec[name] = 100 * np.average(pea[mm].values, weights=ww[mm]) if mm.any() else np.nan
        rows.append(rec)
        print(f"{y}: Hombres {rec['Hombres']:.1f}%  Mujeres {rec['Mujeres']:.1f}%  brecha {rec['Hombres']-rec['Mujeres']:.1f}pp")
    p = pd.DataFrame(rows)
    p.to_csv(CSV, index=False)

fig, ax = fs.fig_ax()
ax.fill_between(p.year, p.Mujeres, p.Hombres, color=fs.GREY, alpha=0.12, zorder=1)
ax.plot(p.year, p.Hombres, "-o", color=fs.NAVY, lw=2.4, ms=4, mfc="white", mec=fs.NAVY, mew=1.4, zorder=5)
ax.plot(p.year, p.Mujeres, "-o", color=fs.CRANBERRY, lw=2.4, ms=4, mfc="white", mec=fs.CRANBERRY, mew=1.4, zorder=5)
fs.end_labels(ax, [
    (f"Hombres  {p.Hombres.iloc[-1]:.0f}%", p.Hombres.iloc[-1], fs.NAVY),
    (f"Mujeres  {p.Mujeres.iloc[-1]:.0f}%", p.Mujeres.iloc[-1], fs.CRANBERRY),
], x_end=p.year.iloc[-1], fs=9.5)
g0 = p.Hombres.iloc[0] - p.Mujeres.iloc[0]; g1 = p.Hombres.iloc[-1] - p.Mujeres.iloc[-1]
fs.halo_label(ax, p.year.iloc[len(p) // 2], (p.Hombres + p.Mujeres).iloc[len(p) // 2] / 2,
              "brecha de genero", fs=9, color=fs.GREY)
ax.set_xlim(2003.5, 2031); ax.set_xticks(range(2004, 2026, 2)); ax.set_ylim(40, 90)
ax.set_ylabel("Tasa de participacion laboral (% de 14+ anios)"); ax.set_xlabel("")
fs.statbox(ax, [
    f"Brecha de genero en participacion: {g0:.0f}pp (2004) -> {g1:.0f}pp ({int(p.year.iloc[-1])}).",
    "Las mujeres entran mas al mercado pero la brecha",
    "persiste pese a que ya superan a los hombres en",
    "educacion (ver fig_educacion_cohorte). Caida COVID 2020.",
], loc="lower left")
fs.source(fig, "Fuente: ENAHO 2004-2025 (INEI), modulo 05. PEA=ocu500 in {1,2,3} sobre 14+. Por sexo (p207). Ponderado por fac500a.")
fig.tight_layout()
for e in ("pdf", "png"):
    fig.savefig(FIG / f"fig_pea_sexo.{e}", dpi=200, bbox_inches="tight")
print("OK -> fig_pea_sexo.pdf")
