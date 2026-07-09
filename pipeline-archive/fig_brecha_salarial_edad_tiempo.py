"""
fig_brecha_salarial_edad_tiempo.py - Brecha salarial de genero por grupo de edad 2004-2025
============================================================================================
Pregunta (Carlos): la brecha salarial mujer/hombre se abre con la edad (penalizacion por
maternidad / divergencia de carrera)? Las cohortes jovenes la estan cerrando?

Razon ingreso laboral mediano M/H entre asalariados (ocu500==1, i524a1>0) por grupo de edad
(p208a) y anio, ponderado por fac500a. Intra-grupo intra-anual -> sin deflactar. Cuatro grupos:
14-24, 25-39, 40-54, 55+. Un plot (4 lineas, paleta figstyle).
Run: python fig_brecha_salarial_edad_tiempo.py [--rebuild]
"""
from __future__ import annotations
from pathlib import Path
import sys
import numpy as np, pandas as pd
import figstyle as fs
import enaho_codes as ec

ROOT = Path(__file__).resolve().parents[1]; RAW = ROOT / "raw"
FIG = ROOT / "figures" / "07_empleo"; DATA = ROOT / "datasets"
CSV = DATA / "brecha_salarial_edad_tiempo_2004_2025.csv"
GROUPS = [("14-24", 14, 24), ("25-39", 25, 39), ("40-54", 40, 54), ("55+", 55, 120)]


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


def ratio_ci(wage, sx, w, mask, B=400, seed=7):
    """IC95 por bootstrap del cociente de medianas (remuestreo de filas dentro del grupo)."""
    idx = np.where(np.asarray(mask))[0]
    if len(idx) < 30:
        return np.nan, np.nan
    wv = np.asarray(wage, float)[idx]; sv = np.asarray(sx, float)[idx]; wt = np.asarray(w, float)[idx]
    rng = np.random.default_rng(seed); out = []
    for _ in range(B):
        s = rng.integers(0, len(idx), len(idx))
        mh = wmed(wv[s][sv[s] == 1], wt[s][sv[s] == 1]); mm = wmed(wv[s][sv[s] == 2], wt[s][sv[s] == 2])
        if mh and np.isfinite(mh):
            out.append(mm / mh)
    if not out:
        return np.nan, np.nan
    return float(np.percentile(out, 2.5)), float(np.percentile(out, 97.5))


if CSV.exists() and "--rebuild" not in sys.argv:
    p = pd.read_csv(CSV)
else:
    rows = []
    for y in ec.years():
        df = rd(RAW / "empleo_ingreso" / f"enaho-{y}-05.dta")
        if df is None or "i524a1" not in df.columns or "p208a" not in df.columns:
            continue
        n = lambda c: pd.to_numeric(df[c], errors="coerce") if c in df.columns else pd.Series(np.nan, index=df.index)
        w = n("fac500a"); sx = n("p207"); wage = n("i524a1"); oc = n("ocu500"); edad = n("p208a")
        base = (oc == 1) & (wage > 0)
        rec = {"year": y}
        for lab, lo, hi in GROUPS:
            msk = base & edad.between(lo, hi)
            r, nm = ratio(wage, sx, w, msk)
            clo, chi = ratio_ci(wage, sx, w, msk)
            rec[lab] = r; rec[f"n_{lab}"] = nm; rec[f"{lab}_lo"] = clo; rec[f"{lab}_hi"] = chi
        rows.append(rec)
        print(f"{y}: " + "  ".join(f"{lab} {rec[lab]:.2f}" for lab, _, _ in GROUPS))
    p = pd.DataFrame(rows).sort_values("year")
    p.to_csv(CSV, index=False)

fig, ax = fs.fig_ax()
ax.axhline(1.0, color=fs.GREY, lw=1.2, ls="--", zorder=1)
ax.annotate("paridad", (p.year.min() + 0.2, 1.0), fontsize=9, color=fs.GREY, style="italic", va="bottom")
# Se grafican 3 grupos confiables; 55+ se excluye del plot (muestra chica, razon muy volatil
# 0.48-1.03) aunque se conserva en el CSV.
PLOT = [("14-24", fs.PALETTE[1]), ("25-39", fs.PALETTE[3]), ("40-54", fs.PALETTE[2])]
labels = []
for lab, c in PLOT:
    s = p.dropna(subset=[lab])
    if f"{lab}_lo" in s.columns:
        ax.fill_between(s.year, s[f"{lab}_lo"], s[f"{lab}_hi"], color=c, alpha=0.12, lw=0, zorder=2)
    ax.plot(s.year, s[lab], "-o", color=c, lw=2.3, ms=3.8, mfc="white", mec=c, mew=1.3, zorder=5)
    labels.append((f"{lab}  {s[lab].iloc[-1]:.2f}", s[lab].iloc[-1], c))
fs.end_labels(ax, labels, x_end=p.year.max(), fs=8.5)
ax.set_xlim(2003.5, 2032); ax.set_xticks(range(2004, 2026, 3)); ax.set_ylim(0.55, 1.0)
ax.set_ylabel("Ingreso laboral mediano: mujer / hombre (asalariados)"); ax.set_xlabel("")
fs.statbox(ax, [
    "Los jovenes (14-24) llegan casi a la paridad y mejoran",
    "fuerte (0.77->0.89); en cambio a los 40-54 la brecha es",
    "la mas ancha y casi no se mueve (~0.75). Compatible con",
    "penalizacion por maternidad y divergencia de carrera.",
], loc="lower right")
fs.source(fig, "Fuente: ENAHO 2004-2025 (INEI), modulo 05. Asalariados (ocu500=1), i524a1, mediana ponderada por fac500a. Grupos de edad (p208a). Bandas = IC95 bootstrap (400 reps). 55+ omitido (muestra chica, muy volatil).")
fig.tight_layout()
for e in ("pdf", "png"):
    fig.savefig(FIG / f"fig_brecha_salarial_edad_tiempo.{e}", dpi=200, bbox_inches="tight")
print("OK -> fig_brecha_salarial_edad_tiempo.pdf")
