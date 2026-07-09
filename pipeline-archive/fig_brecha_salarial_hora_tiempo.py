"""
fig_brecha_salarial_hora_tiempo.py - Brecha de genero: por mes vs por HORA trabajada 2004-2025
================================================================================================
Pregunta (Carlos): cuanto de la brecha salarial mujer/hombre es porque ellas trabajan menos
HORAS, y cuanto es paga por hora? La brecha por hora corrige las diferencias de jornada.

Sobre el MISMO universo (asalariados ocu500==1, i524a1>0, horas i513t>0), por anio y ponderado
por fac500a, se calcula la razon mediana M/H de: (a) ingreso mensual/anual (i524a1) y (b)
salario por HORA proxy (i524a1 / i513t; el factor de anualizacion 52 se cancela en la razon).
i513t = horas semanales en la ocupacion principal. Un plot (2 lineas). Intra-anual -> sin deflactar.
Run: python fig_brecha_salarial_hora_tiempo.py [--rebuild]
"""
from __future__ import annotations
from pathlib import Path
import sys
import numpy as np, pandas as pd
import figstyle as fs
import enaho_codes as ec

ROOT = Path(__file__).resolve().parents[1]; RAW = ROOT / "raw"
FIG = ROOT / "figures" / "07_empleo"; DATA = ROOT / "datasets"
CSV = DATA / "brecha_salarial_hora_tiempo_2004_2025.csv"


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


def wmed(x, w):
    x = np.asarray(x, float); w = np.asarray(w, float)
    ok = np.isfinite(x) & np.isfinite(w) & (x > 0); x, w = x[ok], w[ok]
    if not len(x):
        return np.nan
    o = np.argsort(x); cw = np.cumsum(w[o]) / w[o].sum()
    return x[o][np.searchsorted(cw, 0.5)]


def rat(val, sx, w, mask):
    mh = wmed(val[mask & (sx == 1)], w[mask & (sx == 1)])
    mm = wmed(val[mask & (sx == 2)], w[mask & (sx == 2)])
    return mm / mh if mh else np.nan


if CSV.exists() and "--rebuild" not in sys.argv:
    p = pd.read_csv(CSV)
else:
    rows = []
    for y in ec.years():
        df = rd(RAW / "empleo_ingreso" / f"enaho-{y}-05.dta")
        if df is None or "i524a1" not in df.columns or "i513t" not in df.columns:
            continue
        n = lambda c: pd.to_numeric(df[c], errors="coerce") if c in df.columns else pd.Series(np.nan, index=df.index)
        w = n("fac500a"); sx = n("p207"); wage = n("i524a1"); oc = n("ocu500"); h = n("i513t")
        base = (oc == 1) & (wage > 0) & (h > 0)
        hourly = wage / h
        rmes = rat(wage, sx, w, base)
        rhora = rat(hourly, sx, w, base)
        # horas medianas por sexo (para narrar)
        hh = wmed(h[base & (sx == 1)], w[base & (sx == 1)]); hm = wmed(h[base & (sx == 2)], w[base & (sx == 2)])
        rows.append({"year": y, "mensual": rmes, "hora": rhora, "horas_h": hh, "horas_m": hm})
        print(f"{y}: mensual {rmes:.2f}  hora {rhora:.2f}  | horas H {hh:.0f} M {hm:.0f}")
    p = pd.DataFrame(rows).sort_values("year")
    p.to_csv(CSV, index=False)

fig, ax = fs.fig_ax()
ax.axhline(1.0, color=fs.GREY, lw=1.2, ls="--", zorder=1)
ax.annotate("paridad", (p.year.min() + 0.2, 1.0), fontsize=9, color=fs.GREY, style="italic", va="bottom")
labels = []
for col, lab, c in [("mensual", "Por ingreso mensual", fs.NAVY), ("hora", "Por hora trabajada", fs.CRANBERRY)]:
    s = p.dropna(subset=[col])
    ax.plot(s.year, s[col], "-o", color=c, lw=2.4, ms=4, mfc="white", mec=c, mew=1.4, zorder=5)
    labels.append((f"{lab}  {s[col].iloc[-1]:.2f}", s[col].iloc[-1], c))
fs.end_labels(ax, labels, x_end=p.year.max(), fs=8.5)
ax.set_xlim(2003.5, 2033); ax.set_xticks(range(2004, 2026, 3)); ax.set_ylim(0.6, 1.05)
ax.set_ylabel("Ingreso laboral mediano: mujer / hombre (asalariados)"); ax.set_xlabel("")
hh1, hm1 = p["horas_h"].iloc[-1], p["horas_m"].iloc[-1]
fs.statbox(ax, [
    "La brecha POR HORA es menor que la mensual: parte de la",
    f"brecha mensual es jornada (en {int(p.year.iloc[-1])} ellos {hh1:.0f}h vs ellas {hm1:.0f}h/sem).",
    "Pero aun por hora persiste una brecha de paga: corregir",
    "horas no elimina la diferencia, solo la reduce.",
], loc="lower right")
fs.source(fig, "Fuente: ENAHO 2004-2025 (INEI), modulo 05. Asalariados (ocu500=1) con horas>0. Salario/hora = i524a1/i513t. Mediana ponderada por fac500a.")
fig.tight_layout()
for e in ("pdf", "png"):
    fig.savefig(FIG / f"fig_brecha_salarial_hora_tiempo.{e}", dpi=200, bbox_inches="tight")
print("OK -> fig_brecha_salarial_hora_tiempo.pdf")
