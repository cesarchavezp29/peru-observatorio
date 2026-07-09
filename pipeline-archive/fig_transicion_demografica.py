"""
fig_transicion_demografica.py - Transicion demografica del Peru 2004-2025 (M02)
================================================================================
Modulo 02 (Miembros del hogar). Edad p208a, peso POBLACIONAL facpob07 (M02 NO trae
factor07). Verificado estable todos los anios. Construye dos figuras (un plot c/u):
  (A) estructura por edad: % 0-14 (ninos) vs % 60+ (adultos mayores) -> el cruce de
      la transicion demografica (cae la base, crece la cuspide).
  (B) edad mediana 2004-2025.

CAVEAT (clave, ver memoria): la ENAHO SOBRE-REPRESENTA adultos mayores ~3-4pp vs el
Censo 2025 (60+ Censo 14.8% vs ENAHO ~18%). La DIRECCION (envejecimiento) si calza; los
NIVELES no -> se grafican como TENDENCIA, no nivel absoluto. Para niveles citar Censo.
Figura cita SOLO ENAHO (la comparacion con Censo va en nota/docs).

Run: python fig_transicion_demografica.py
"""
from __future__ import annotations
from pathlib import Path
import numpy as np, pandas as pd
import figstyle as fs
import enaho_codes as ec

ROOT = Path(__file__).resolve().parents[1]; RAW = ROOT / "raw"
FIG = ROOT / "figures" / "05_demografia_salud_educacion"; FIG.mkdir(parents=True, exist_ok=True)
DATA = ROOT / "datasets"


def L(year):
    p = RAW / "miembros" / f"enaho-{year}-02.dta"
    if not p.exists():
        return None
    try:
        import pyreadstat
        df, _ = pyreadstat.read_dta(str(p), encoding="latin1", usecols=None)
    except Exception:
        df = pd.read_stata(p, convert_categoricals=False)
    df.columns = [c.lower() for c in df.columns]
    return df


def wshare(mask, w):
    mask = np.asarray(mask, float); w = np.asarray(w, float)
    ok = np.isfinite(mask) & np.isfinite(w)
    return 100 * np.average(mask[ok], weights=w[ok]) if ok.any() else np.nan


def wmedian(x, w):
    x = np.asarray(x, float); w = np.asarray(w, float); ok = np.isfinite(x) & np.isfinite(w)
    x, w = x[ok], w[ok]
    o = np.argsort(x); cw = np.cumsum(w[o]) / w[o].sum()
    return x[o][np.searchsorted(cw, 0.5)]


rows = []
for y in ec.years():
    df = L(y)
    if df is None:
        continue
    w = pd.to_numeric(df.get("facpob07"), errors="coerce")
    edad = pd.to_numeric(df.get("p208a"), errors="coerce")
    dep = (edad <= 14) | (edad >= 65); act = (edad >= 15) & (edad <= 64)
    rows.append({"year": y,
                 "pct_0a14": wshare(edad <= 14, w),
                 "pct_60mas": wshare(edad >= 60, w),
                 "edad_mediana": wmedian(edad, w),
                 "razon_dependencia": 100 * np.nansum(w.where(dep)) / np.nansum(w.where(act))})
    print(f"{y}: 0-14 {rows[-1]['pct_0a14']:4.1f}%  60+ {rows[-1]['pct_60mas']:4.1f}%  "
          f"mediana {rows[-1]['edad_mediana']:.0f}  dep {rows[-1]['razon_dependencia']:.0f}")

p = pd.DataFrame(rows)
p.to_csv(DATA / "transicion_demografica_2004_2025.csv", index=False)

# ---- (A) estructura por edad: ninos vs mayores ----
fig, ax = fs.fig_ax()
ax.plot(p.year, p.pct_0a14, "-o", color=fs.NAVY, lw=2.4, ms=4, mfc="white", mec=fs.NAVY, mew=1.4, zorder=5)
ax.plot(p.year, p.pct_60mas, "-o", color=fs.CRANBERRY, lw=2.4, ms=4, mfc="white", mec=fs.CRANBERRY, mew=1.4, zorder=5)
fs.end_labels(ax, [
    (f"Ninos (0-14)  {p.pct_0a14.iloc[-1]:.0f}%", p.pct_0a14.iloc[-1], fs.NAVY),
    (f"Adultos mayores (60+)  {p.pct_60mas.iloc[-1]:.0f}%", p.pct_60mas.iloc[-1], fs.CRANBERRY),
], x_end=p.year.iloc[-1], fs=9.5)
ax.set_xlim(2003.5, 2031.5)
ax.set_ylim(10, 35)
ax.set_xticks(range(2004, 2026, 2))
ax.set_ylabel("% de la poblacion")
ax.set_xlabel("")
# nota en la banda VACIA entre ambas lineas (izquierda), sin tocar las series
ax.text(0.035, 0.46, "\n".join([
    "Transicion demografica: la base (ninos) cae",
    "y la cuspide (mayores) crece -> envejecimiento.",
    "Nota: ENAHO sobre-representa adultos mayores",
    "~3-4pp vs Censo 2025; leer como TENDENCIA.",
]), transform=ax.transAxes, ha="left", va="center", fontsize=9.3, color=fs.INK,
    bbox=dict(boxstyle="round,pad=0.4", fc="white", ec="#cfd3d8", lw=0.8, alpha=0.95))
fs.source(fig, "Fuente: ENAHO 2004-2025 (INEI), modulo 02. Ponderado por facpob07.")
fig.tight_layout()
for e in ("pdf", "png"):
    fig.savefig(FIG / f"fig_transicion_demografica.{e}", dpi=200, bbox_inches="tight")
print("OK -> fig_transicion_demografica.pdf")

# ---- (B) edad mediana ----
fig, ax = fs.fig_ax()
ax.plot(p.year, p.edad_mediana, "-o", color=fs.NAVY, lw=2.4, ms=5, mfc="white", mec=fs.NAVY, mew=1.4, zorder=5)
fs.halo_label(ax, p.year.iloc[0], p.edad_mediana.iloc[0], f"{p.edad_mediana.iloc[0]:.0f} anios ({p.year.iloc[0]})", dy=9, dx=2, fs=9)
fs.halo_label(ax, p.year.iloc[-1], p.edad_mediana.iloc[-1], f"{p.edad_mediana.iloc[-1]:.0f} anios ({p.year.iloc[-1]})", dy=-15, dx=-2, fs=9, color=fs.CRANBERRY)
ax.set_xlim(2003.5, 2026)
ax.set_xticks(range(2004, 2026, 2))
ax.set_ylabel("Edad mediana de la poblacion (anios)")
ax.set_xlabel("")
fs.source(fig, "Fuente: ENAHO 2004-2025 (INEI), modulo 02. Ponderado por facpob07. Tendencia (ENAHO sobre-representa mayores vs Censo).")
fig.tight_layout()
for e in ("pdf", "png"):
    fig.savefig(FIG / f"fig_edad_mediana.{e}", dpi=200, bbox_inches="tight")
print("OK -> fig_edad_mediana.pdf")
