"""
fig_brecha_salarial_region_tiempo.py - Brecha salarial de genero por region natural 2004-2025
===============================================================================================
Pregunta (Carlos): la brecha salarial mujer/hombre difiere entre Costa, Sierra y Selva, y como
evoluciono cada una?

Razon ingreso laboral mediano M/H entre asalariados (ocu500==1, i524a1>0) por region natural
(dominio) y anio, ponderado por fac500a. Intra-grupo intra-anual -> sin deflactar. Region:
Costa={1,2,3,8} (incluye Lima Metropolitana, costera), Sierra={4,5,6}, Selva={7}; dominio
estable todo el periodo. Un plot (3 lineas, paleta figstyle).
Run: python fig_brecha_salarial_region_tiempo.py [--rebuild]
"""
from __future__ import annotations
from pathlib import Path
import sys
import numpy as np, pandas as pd
import figstyle as fs
import enaho_codes as ec

ROOT = Path(__file__).resolve().parents[1]; RAW = ROOT / "raw"
FIG = ROOT / "figures" / "07_empleo"; DATA = ROOT / "datasets"
CSV = DATA / "brecha_salarial_region_tiempo_2004_2025.csv"
REGS = [("Costa", [1, 2, 3, 8]), ("Sierra", [4, 5, 6]), ("Selva", [7])]


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
    wv = np.asarray(wage, float)[idx]; sv = np.asarray(sx, float)[idx]; wt = np.asarray(w, float)[idx]
    rng = np.random.default_rng(seed)
    out = []
    for _ in range(B):
        s = rng.integers(0, len(idx), len(idx))
        wb, sb, wtb = wv[s], sv[s], wt[s]
        mh = wmed(wb[sb == 1], wtb[sb == 1]); mm = wmed(wb[sb == 2], wtb[sb == 2])
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
        if df is None or "i524a1" not in df.columns or "dominio" not in df.columns:
            continue
        n = lambda c: pd.to_numeric(df[c], errors="coerce") if c in df.columns else pd.Series(np.nan, index=df.index)
        w = n("fac500a"); sx = n("p207"); wage = n("i524a1"); oc = n("ocu500"); dom = n("dominio")
        base = (oc == 1) & (wage > 0)
        rec = {"year": y}
        for lab, codes in REGS:
            msk = base & dom.isin(codes)
            r, nm = ratio(wage, sx, w, msk)
            lo, hi = ratio_ci(wage, sx, w, msk)
            rec[lab] = r; rec[f"n_{lab}"] = nm; rec[f"{lab}_lo"] = lo; rec[f"{lab}_hi"] = hi
        rows.append(rec)
        print(f"{y}: " + "  ".join(f"{lab} {rec[lab]:.2f}[{rec[lab+'_lo']:.2f}-{rec[lab+'_hi']:.2f}] n_M={rec['n_'+lab]}" for lab, _ in REGS))
    p = pd.DataFrame(rows).sort_values("year")
    p.to_csv(CSV, index=False)

fig, ax = fs.fig_ax()
ax.axhline(1.0, color=fs.GREY, lw=1.2, ls="--", zorder=1)
ax.annotate("paridad", (p.year.min() + 0.2, 1.0), fontsize=9, color=fs.GREY, style="italic", va="bottom")
cols = [fs.PALETTE[0], fs.PALETTE[1], fs.PALETTE[4]]   # navy costa, cranberry sierra, sage selva
labels = []
for (lab, _), c in zip(REGS, cols):
    s = p.dropna(subset=[lab])
    if f"{lab}_lo" in s.columns:
        ax.fill_between(s.year, s[f"{lab}_lo"], s[f"{lab}_hi"], color=c, alpha=0.13, lw=0, zorder=2)
    ax.plot(s.year, s[lab], "-o", color=c, lw=2.3, ms=3.6, mfc="white", mec=c, mew=1.3, zorder=5)
    labels.append((f"{lab}  {s[lab].iloc[-1]:.2f}", s[lab].iloc[-1], c))
fs.end_labels(ax, labels, x_end=p.year.max(), fs=8.5)
ax.set_xlim(2003.5, 2032); ax.set_xticks(range(2004, 2026, 3)); ax.set_ylim(0.45, 1.05)
ax.set_ylabel("Ingreso laboral mediano: mujer / hombre (asalariados)"); ax.set_xlabel("")
fs.statbox(ax, [
    "El vaiven anual por region es en gran parte RUIDO MUESTRAL:",
    "las bandas (IC95 bootstrap) son anchas porque cada region",
    "tiene pocas asalariadas (Selva ~1-2 mil). La senal robusta:",
    "Sierra la brecha mas ancha, Costa la menor; todas mejoran.",
], loc="lower right")
fs.source(fig, "Fuente: ENAHO 2004-2025 (INEI), modulo 05. Asalariados (ocu500=1), i524a1, mediana ponderada por fac500a. Region natural (dominio), Costa incl. Lima. Bandas = IC95 bootstrap (400 reps).")
fig.tight_layout()
for e in ("pdf", "png"):
    fig.savefig(FIG / f"fig_brecha_salarial_region_tiempo.{e}", dpi=200, bbox_inches="tight")
print("OK -> fig_brecha_salarial_region_tiempo.pdf")
