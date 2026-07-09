"""
fig_brecha_salarial_sexo.py - La brecha salarial de genero 2004-2025 (modulo empleo M05)
==========================================================================================
Pregunta: las mujeres ya superan a los hombres en educacion (ver fig_educacion_cohorte) y
entran mas al mercado (ver fig_pea_sexo). Se cerro tambien la brecha en lo que GANAN?

Metrica: razon ingreso laboral mediano mujer / hombre entre ASALARIADOS (ocu500==1, ingreso
del trabajo dependiente i524a1>0), por anio, ponderado por fac500a. La razon no requiere
deflactar (es intra-anual: cualquier deflactor comun se cancela). i524a1 = ingreso por trabajo
dependiente principal (mismo constructo INEI ambos sexos cada anio). Un plot, figstyle.
Run: python fig_brecha_salarial_sexo.py [--rebuild]
"""
from __future__ import annotations
from pathlib import Path
import sys
import numpy as np, pandas as pd
import figstyle as fs
import enaho_codes as ec

ROOT = Path(__file__).resolve().parents[1]; RAW = ROOT / "raw"
FIG = ROOT / "figures" / "07_empleo"; FIG.mkdir(parents=True, exist_ok=True)
CSV = ROOT / "datasets" / "brecha_salarial_sexo_2004_2025.csv"


def wmed(x, w):
    x = np.asarray(x, float); w = np.asarray(w, float)
    ok = np.isfinite(x) & np.isfinite(w) & (x > 0)
    x, w = x[ok], w[ok]
    if not len(x):
        return np.nan
    o = np.argsort(x); cw = np.cumsum(w[o]) / w[o].sum()
    return x[o][np.searchsorted(cw, 0.5)]


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
        if df is None or "i524a1" not in df.columns:
            continue
        n = lambda c: pd.to_numeric(df[c], errors="coerce") if c in df.columns else pd.Series(np.nan, index=df.index)
        w = n("fac500a"); sx = n("p207"); wage = n("i524a1"); oc = n("ocu500")
        base = (oc == 1) & (wage > 0)
        mh = wmed(wage[base & (sx == 1)], w[base & (sx == 1)])
        mm = wmed(wage[base & (sx == 2)], w[base & (sx == 2)])
        rows.append({"year": y, "ratio": mm / mh, "med_h": mh, "med_m": mm,
                     "n_h": int((base & (sx == 1)).sum()), "n_m": int((base & (sx == 2)).sum())})
        print(f"{y}: razon M/H={mm/mh:.3f}  (brecha {100*(1-mm/mh):.0f}%)")
    p = pd.DataFrame(rows).sort_values("year")
    p.to_csv(CSV, index=False)

fig, ax = fs.fig_ax()
ax.axhline(1.0, color=fs.GREY, lw=1.2, ls="--", zorder=1)
ax.plot(p.year, p.ratio, "-o", color=fs.CRANBERRY, lw=2.6, ms=4.5, mfc="white", mec=fs.CRANBERRY, mew=1.5, zorder=5)
fs.end_labels(ax, [(f"{p.ratio.iloc[-1]:.2f}", p.ratio.iloc[-1], fs.CRANBERRY)], x_end=p.year.max(), fs=9.5)
ax.annotate("paridad", (2004.2, 1.0), fontsize=9, color=fs.GREY, style="italic", va="bottom")
r0, r1 = p.ratio.iloc[0], p.ratio.iloc[-1]
ax.set_xlim(2003.5, 2031); ax.set_xticks(range(2004, 2026, 3)); ax.set_ylim(0.6, 1.02)
ax.set_ylabel("Ingreso laboral mediano: mujer / hombre (asalariados)"); ax.set_xlabel("")
fs.statbox(ax, [
    f"La brecha se reduce de {100*(1-r0):.0f}% ({int(p.year.iloc[0])}) a {100*(1-r1):.0f}% ({int(p.year.iloc[-1])}),",
    "pero persiste: las mujeres ganan ~20% menos que",
    "los hombres pese a superarlos ya en educacion",
    "(ver fig_educacion_cohorte). Brecha sin ajustar por horas.",
], loc="lower right")
fs.source(fig, "Fuente: ENAHO 2004-2025 (INEI), modulo 05. Asalariados (ocu500=1), ingreso dependiente i524a1. Mediana ponderada por fac500a. Razon intra-anual (sin deflactar).")
fig.tight_layout()
for e in ("pdf", "png"):
    fig.savefig(FIG / f"fig_brecha_salarial_sexo.{e}", dpi=200, bbox_inches="tight")
print("OK -> fig_brecha_salarial_sexo.pdf")
