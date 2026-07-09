"""
fig_analfabetismo_region_tiempo.py - Analfabetismo por region natural 2004-2025 (M03)
=======================================================================================
Pregunta: como cayo el analfabetismo en el Peru y cuanto persiste la brecha entre la Sierra/
Selva y la Costa?

% de adultos 15+ que NO sabe leer y escribir (p302==2), por region natural (dominio: Costa=
{1,2,3,8} incl. Lima, Sierra={4,5,6}, Selva={7}), ponderado por factor07. p302 ('sabe leer y
escribir', 1=si/2=no) estable todo el periodo; se restringe a 15+ (la pregunta se hace a 3+,
los ninos chicos elevarian la tasa). Un plot. Run: python fig_analfabetismo_region_tiempo.py [--rebuild]
"""
from __future__ import annotations
from pathlib import Path
import sys
import numpy as np, pandas as pd
import figstyle as fs
import enaho_codes as ec

ROOT = Path(__file__).resolve().parents[1]; RAW = ROOT / "raw"
FIG = ROOT / "figures" / "05_demografia_salud_educacion"; FIG.mkdir(parents=True, exist_ok=True)
CSV = ROOT / "datasets" / "analfabetismo_region_tiempo_2004_2025.csv"
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
        if df is None or "p302" not in df.columns or "dominio" not in df.columns:
            continue
        n = lambda c: pd.to_numeric(df[c], errors="coerce")
        lee = n("p302"); edad = n("p208a"); dom = n("dominio"); w = n("factor07")
        # p302 se pregunta SOLO a un subgrupo (los de baja educacion); a quien no se le
        # pregunta (lee NaN) se le asume alfabeto. Tasa = (lee==2) sobre TODOS los 15+.
        a15 = (edad >= 15)
        ana = (lee == 2).where(a15, np.nan)
        rec = {"year": y}
        for lab, codes in REGS:
            m = a15 & dom.isin(codes)
            rec[lab] = wshare(ana[m], w[m])
        rec["Nacional"] = wshare(ana[a15], w[a15])
        rows.append(rec)
        print(f"{y}: Nacional {rec['Nacional']:.1f}%  Costa {rec['Costa']:.1f}  Sierra {rec['Sierra']:.1f}  Selva {rec['Selva']:.1f}")
    p = pd.DataFrame(rows).sort_values("year")
    p.to_csv(CSV, index=False)

fig, ax = fs.fig_ax()
cols = [fs.PALETTE[0], fs.PALETTE[1], fs.PALETTE[4]]
labels = []
for (lab, _), c in zip(REGS, cols):
    s = p.dropna(subset=[lab])
    ax.plot(s.year, s[lab], "-o", color=c, lw=2.3, ms=3.6, mfc="white", mec=c, mew=1.2, zorder=5)
    labels.append((f"{lab}  {s[lab].iloc[-1]:.0f}%", s[lab].iloc[-1], c))
fs.end_labels(ax, labels, x_end=p.year.max(), fs=8.5)
ax.set_xlim(2003.5, 2031); ax.set_xticks(range(2004, 2026, 3)); ax.set_ylim(0, 25)
ax.set_ylabel("Analfabetismo: adultos 15+ que no sabe leer/escribir (%)"); ax.set_xlabel("")
fs.statbox(ax, [
    f"El analfabetismo cayo en todo el pais (nacional {p.Nacional.iloc[0]:.0f}->{p.Nacional.iloc[-1]:.0f}%)",
    "pero la SIERRA sigue muy por encima de la Costa: la brecha",
    "territorial persiste y se concentra en la poblacion rural",
    "e indigena de mayor edad. La Costa esta casi alfabetizada.",
], loc="upper right")
ax.annotate("2020 atipico\n(ENAHO COVID,\nparcial telefonica)", (2020, 4.0), fontsize=7, color=fs.GREY,
            ha="center", va="top", style="italic")
fs.source(fig, "Fuente: ENAHO 2004-2025 (INEI), modulo 03. Adultos 15+ que no sabe leer y escribir (p302). Region natural (dominio), Costa incl. Lima. Ponderado por factor07. La caida de 2020 es artefacto de recoleccion (COVID).")
fig.tight_layout()
for e in ("pdf", "png"):
    fig.savefig(FIG / f"fig_analfabetismo_region_tiempo.{e}", dpi=200, bbox_inches="tight")
print("OK -> fig_analfabetismo_region_tiempo.pdf")
