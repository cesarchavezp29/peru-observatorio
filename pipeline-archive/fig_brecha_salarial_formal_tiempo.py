"""
fig_brecha_salarial_formal_tiempo.py - Brecha salarial de genero: formal vs informal 2007-2025
================================================================================================
Pregunta (Carlos): la brecha salarial mujer/hombre es distinta en el empleo FORMAL que en el
INFORMAL, y como evoluciono cada una?

Razon ingreso laboral mediano M/H entre asalariados (ocu500==1, i524a1>0 -> dependientes), por
condicion de formalidad y anio, ponderado por fac500a. Intra-grupo intra-anual -> sin deflactar.
Formalidad: ocupinf OFICIAL donde existe (2007-2023, 1=informal/2=formal); 2024-2025 reconstruida
con la regla INEI validada (build_informalidad.reconstruct, maneja el cambio de codigo p511a).
Entre dependientes, informal = sin contrato formal. 2004-2006 excluidos (no construible: p511a
~50% ausente en 2004, p510a1 inexistente). Un plot. Run: python fig_brecha_salarial_formal_tiempo.py [--rebuild]
"""
from __future__ import annotations
from pathlib import Path
import sys
import numpy as np, pandas as pd
import figstyle as fs
import enaho_codes as ec
from build_informalidad import reconstruct

ROOT = Path(__file__).resolve().parents[1]; RAW = ROOT / "raw"
FIG = ROOT / "figures" / "07_empleo"; DATA = ROOT / "datasets"
CSV = DATA / "brecha_salarial_formal_tiempo_2007_2025.csv"


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
        if y < 2007:
            continue
        df = rd(RAW / "empleo_ingreso" / f"enaho-{y}-05.dta")
        if df is None or "i524a1" not in df.columns:
            continue
        n = lambda c: pd.to_numeric(df[c], errors="coerce") if c in df.columns else pd.Series(np.nan, index=df.index)
        w = n("fac500a"); sx = n("p207"); wage = n("i524a1"); oc = n("ocu500")
        if "ocupinf" in df.columns and n("ocupinf").notna().mean() > 0.5:
            informal = (n("ocupinf") == 1).values; src = "oficial"
        else:
            informal = reconstruct(df, y); src = "reconstruido"
        base = (oc == 1) & (wage > 0)
        rf, nf = ratio(wage, sx, w, base & ~pd.Series(informal, index=df.index))
        ri, ni = ratio(wage, sx, w, base & pd.Series(informal, index=df.index))
        rows.append({"year": y, "formal": rf, "informal": ri, "n_form_m": nf, "n_inf_m": ni, "fuente": src})
        print(f"{y}: formal {rf:.2f} (n_M={nf})  informal {ri:.2f} (n_M={ni})  [{src}]")
    p = pd.DataFrame(rows).sort_values("year")
    p.to_csv(CSV, index=False)

fig, ax = fs.fig_ax()
ax.axhline(1.0, color=fs.GREY, lw=1.2, ls="--", zorder=1)
ax.annotate("paridad", (p.year.min() + 0.2, 1.0), fontsize=9, color=fs.GREY, style="italic", va="bottom")
labels = []
for col, lab, c in [("formal", "Empleo formal", fs.NAVY), ("informal", "Empleo informal", fs.CRANBERRY)]:
    s = p.dropna(subset=[col])
    ax.plot(s.year, s[col], "-o", color=c, lw=2.4, ms=4, mfc="white", mec=c, mew=1.4, zorder=5)
    labels.append((f"{lab}  {s[col].iloc[-1]:.2f}", s[col].iloc[-1], c))
fs.end_labels(ax, labels, x_end=p.year.max(), fs=8.5)
ax.set_xlim(2006.5, 2032); ax.set_xticks(range(2007, 2026, 3)); ax.set_ylim(0.5, 1.02)
ax.set_ylabel("Ingreso laboral mediano: mujer / hombre (asalariados)"); ax.set_xlabel("")
fs.statbox(ax, [
    "La brecha de genero es mas ancha en el empleo INFORMAL",
    "(sin contrato) que en el formal, y mas volatil. El contrato",
    "formal protege parcialmente el salario de las mujeres.",
    "2024-25: formalidad reconstruida (INEI dejo de publicar ocupinf).",
], loc="lower right")
fs.source(fig, "Fuente: ENAHO 2007-2025 (INEI), modulo 05. Asalariados (ocu500=1), i524a1, mediana ponderada por fac500a. Formalidad: ocupinf oficial 2007-23, reconstruida 2024-25.")
fig.tight_layout()
for e in ("pdf", "png"):
    fig.savefig(FIG / f"fig_brecha_salarial_formal_tiempo.{e}", dpi=200, bbox_inches="tight")
print("OK -> fig_brecha_salarial_formal_tiempo.pdf")
