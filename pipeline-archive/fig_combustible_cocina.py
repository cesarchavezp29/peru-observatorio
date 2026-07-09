"""
fig_combustible_cocina.py - Transicion energetica en la cocina 2004-2025 (M01)
===============================================================================
Modulo 01, bateria de combustible para cocinar (p1131..p1139, 0/1 por hogar):
  gas limpio = GLP (p1132) o gas natural (p1133)
  biomasa    = lena (p1136), carbon (p1135), bosta (p1139), residuos (p1137)
% de hogares que usa cada fuente, ponderado por factor07. Llave HOGAR.

Run: python fig_combustible_cocina.py
"""
from __future__ import annotations
from pathlib import Path
import numpy as np, pandas as pd, matplotlib.pyplot as plt
import figstyle as fs
import enaho_codes as ec

ROOT = Path(__file__).resolve().parents[1]; RAW = ROOT / "raw"
FIG = ROOT / "figures" / "06_vivienda"; FIG.mkdir(parents=True, exist_ok=True)
DATA = ROOT / "datasets"


def read_dta(p):
    try:
        return pd.read_stata(p, convert_categoricals=False)
    except ValueError:
        import pyreadstat; df, _ = pyreadstat.read_dta(str(p)); return df


def wshare(m, w):
    m = np.asarray(m, float); w = np.asarray(w, float); ok = np.isfinite(m) & np.isfinite(w)
    return 100 * np.average(m[ok], weights=w[ok]) if ok.any() else np.nan


rows = []
for y in ec.years():
    p = RAW / "vivienda_hogar" / f"enaho-{y}-01.dta"
    if not p.exists():
        continue
    d = read_dta(p); d.columns = [c.lower() for c in d.columns]
    if "factor07" not in d.columns:
        continue
    g = lambda c: pd.to_numeric(d[c], errors="coerce") if c in d.columns else pd.Series(np.nan, index=d.index)
    anyresp = g("p1132").notna() | g("p1136").notna()
    gas = ((g("p1132") == 1) | (g("p1133") == 1)).where(anyresp)
    bio = ((g("p1136") == 1) | (g("p1135") == 1) | (g("p1139") == 1) | (g("p1137") == 1)).where(anyresp)
    rows.append({"year": y, "gas": wshare(gas, d["factor07"]), "biomasa": wshare(bio, d["factor07"])})
ev = pd.DataFrame(rows).sort_values("year")
ev.to_csv(DATA / "combustible_cocina_2004_2025.csv", index=False)
print(ev.round(1).to_string(index=False))

fs.use()
fig, ax = plt.subplots(figsize=(11, 6.2))
ax.plot(ev["year"], ev["gas"], "-o", color=fs.NAVY, lw=2.6, ms=4, mfc="white", mec=fs.NAVY, mew=1.5,
        label="Gas (GLP o natural) - limpio")
ax.plot(ev["year"], ev["biomasa"], "-o", color=fs.CRANBERRY, lw=2.6, ms=4, mfc="white", mec=fs.CRANBERRY,
        mew=1.5, label="Lena, carbon, bosta - biomasa")
ax.fill_between(ev["year"], ev["gas"], ev["biomasa"], color=fs.NAVY, alpha=0.04, zorder=0)
for c, col, dyl in [("gas", fs.NAVY, 9), ("biomasa", fs.CRANBERRY, -14)]:
    fs.halo_label(ax, ev["year"].iloc[-1], ev[c].iloc[-1], f"{ev[c].iloc[-1]:.0f}%", dx=6, dy=-3, color=col)
    fs.halo_label(ax, ev["year"].iloc[0], ev[c].iloc[0], f"{ev[c].iloc[0]:.0f}%", dx=-2, dy=dyl, color=col)
ax.set_ylim(0, 100); ax.set_xlim(2003.5, 2027.0); ax.set_xticks(range(2004, 2026, 2))
ax.set_ylabel("% de hogares (uso, no exclusivo)")
ax.set_title("La cocina peruana cambia de lena a gas, 2004-2025", loc="left", fontsize=13)
ax.legend(loc="lower left")
fs.source(fig, "Fuente: ENAHO Modulo 01 (INEI), 2004-2025. Bateria de combustible para cocinar. "
          "Llave hogar; ponderado por factor07.")
fig.tight_layout()
for e in ("pdf", "png"):
    fig.savefig(FIG / f"fig_combustible_cocina.{e}", dpi=140, bbox_inches="tight")
print("OK -> figures/06_vivienda/fig_combustible_cocina.pdf")
