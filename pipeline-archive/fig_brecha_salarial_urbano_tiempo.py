"""
fig_brecha_salarial_urbano_tiempo.py - Brecha salarial de genero: urbano vs rural 2004-2025
=============================================================================================
Pregunta (Carlos): la brecha salarial mujer/hombre difiere entre el Peru URBANO y el RURAL, y
como evoluciono cada una?

Razon ingreso laboral mediano M/H entre asalariados (ocu500==1, i524a1>0), por area y anio,
ponderado por fac500a. Intra-grupo intra-anual -> sin deflactar. Area = estrato (1-5 urbano,
6-8 rural; corte estandar INEI estable todo el periodo, 7-8 = AER rural). Un plot.
Run: python fig_brecha_salarial_urbano_tiempo.py [--rebuild]
"""
from __future__ import annotations
from pathlib import Path
import sys
import numpy as np, pandas as pd
import figstyle as fs
import enaho_codes as ec

ROOT = Path(__file__).resolve().parents[1]; RAW = ROOT / "raw"
FIG = ROOT / "figures" / "07_empleo"; DATA = ROOT / "datasets"
CSV = DATA / "brecha_salarial_urbano_tiempo_2004_2025.csv"


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


def ratio(wage, sx, w, mask):
    mh = wmed(wage[mask & (sx == 1)], w[mask & (sx == 1)])
    mm = wmed(wage[mask & (sx == 2)], w[mask & (sx == 2)])
    return (mm / mh if mh else np.nan), int((mask & (sx == 2)).sum())


if CSV.exists() and "--rebuild" not in sys.argv:
    p = pd.read_csv(CSV)
else:
    rows = []
    for y in ec.years():
        df = rd(RAW / "empleo_ingreso" / f"enaho-{y}-05.dta")
        if df is None or "i524a1" not in df.columns or "estrato" not in df.columns:
            continue
        n = lambda c: pd.to_numeric(df[c], errors="coerce") if c in df.columns else pd.Series(np.nan, index=df.index)
        w = n("fac500a"); sx = n("p207"); wage = n("i524a1"); oc = n("ocu500"); est = n("estrato")
        urb = est.between(1, 5); rur = est.between(6, 8)
        base = (oc == 1) & (wage > 0)
        ru, nu = ratio(wage, sx, w, base & urb)
        rr, nr = ratio(wage, sx, w, base & rur)
        rows.append({"year": y, "urbano": ru, "rural": rr, "n_urb_m": nu, "n_rur_m": nr})
        print(f"{y}: urbano {ru:.2f} (n_M={nu})  rural {rr:.2f} (n_M={nr})")
    p = pd.DataFrame(rows).sort_values("year")
    p.to_csv(CSV, index=False)

fig, ax = fs.fig_ax()
ax.axhline(1.0, color=fs.GREY, lw=1.2, ls="--", zorder=1)
ax.annotate("paridad", (p.year.min() + 0.2, 1.0), fontsize=9, color=fs.GREY, style="italic", va="bottom")
labels = []
for col, lab, c in [("urbano", "Urbano", fs.NAVY), ("rural", "Rural", fs.CRANBERRY)]:
    s = p.dropna(subset=[col])
    ax.plot(s.year, s[col], "-o", color=c, lw=2.4, ms=4, mfc="white", mec=c, mew=1.4, zorder=5)
    labels.append((f"{lab}  {s[col].iloc[-1]:.2f}", s[col].iloc[-1], c))
fs.end_labels(ax, labels, x_end=p.year.max(), fs=8.5)
ax.set_xlim(2003.5, 2032); ax.set_xticks(range(2004, 2026, 3)); ax.set_ylim(0.5, 1.05)
ax.set_ylabel("Ingreso laboral mediano: mujer / hombre (asalariados)"); ax.set_xlabel("")
u0, u1 = p["urbano"].iloc[0], p["urbano"].iloc[-1]
r0, r1 = p["rural"].iloc[0], p["rural"].iloc[-1]
fs.statbox(ax, [
    "La brecha de genero entre asalariados es mas ancha y",
    "volatil en el campo (muestra rural chica) que en la ciudad.",
    f"Urbano {u0:.2f}->{u1:.2f}, rural {r0:.2f}->{r1:.2f}.",
], loc="lower right")
fs.source(fig, "Fuente: ENAHO 2004-2025 (INEI), modulo 05. Asalariados (ocu500=1), i524a1, mediana ponderada por fac500a. Area = estrato (1-5 urbano, 6-8 rural).")
fig.tight_layout()
for e in ("pdf", "png"):
    fig.savefig(FIG / f"fig_brecha_salarial_urbano_tiempo.{e}", dpi=200, bbox_inches="tight")
print("OK -> fig_brecha_salarial_urbano_tiempo.pdf")
