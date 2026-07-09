"""
fig_subempleo_horas.py - Subempleo visible y horas de trabajo 2004-2025 (M05)
==============================================================================
Modulo 05 (Empleo). Ocupados (ocu500==1), peso fac500a (fallback factor07).
  - HORAS: i518 (imputado) = total de horas trabajadas la semana pasada en todas las
    ocupaciones. Media ~40h. Tambien % con jornada excesiva (>48h, OIT).
  - SUBEMPLEO VISIBLE (por horas, def. INEI/OIT): ocupado que trabaja <35h, QUERIA
    trabajar mas (p521==1) y estuvo DISPONIBLE (p521a==1).
(El subempleo por INGRESOS necesita el ingreso minimo referencial por anio; no se calcula
aqui -> esta figura cubre solo el subempleo VISIBLE por horas + la jornada.)
Dos figuras, un plot c/u, paleta figstyle.
Run: python fig_subempleo_horas.py
"""
from __future__ import annotations
from pathlib import Path
import numpy as np, pandas as pd
import figstyle as fs
import enaho_codes as ec

ROOT = Path(__file__).resolve().parents[1]; RAW = ROOT / "raw"
FIG = ROOT / "figures" / "07_empleo"; FIG.mkdir(parents=True, exist_ok=True)
DATA = ROOT / "datasets"


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


CSV = DATA / "subempleo_horas_2004_2025.csv"
import sys
if CSV.exists() and "--rebuild" not in sys.argv:
    p = pd.read_csv(CSV)
    rows = None
else:
    rows = []
for y in (ec.years() if rows is not None else []):
    df = L(y)
    if df is None:
        continue
    n = lambda c: pd.to_numeric(df[c], errors="coerce") if c in df.columns else pd.Series(np.nan, index=df.index)
    oc = (n("ocu500") == 1).values
    w = n("fac500a"); w = w.where(w.notna(), n("factor07"))
    # HORAS TOTALES = ocupacion principal (i513t) + secundarias (i518). i518 solo NO es total.
    h_pri = n("i513t"); h_pri = h_pri.where(h_pri.notna(), n("p513t"))
    h_sec = n("i518"); h_sec = h_sec.where(h_sec.notna(), n("p518"))
    hrs = (h_pri.fillna(0) + h_sec.fillna(0)).where(h_pri.notna())   # valido si hay horas de ocup. principal
    quiere = n("p521") == 1; dispo = n("p521a") == 1
    sub = (hrs < 35) & quiere & dispo
    ww = w.fillna(0).values
    m = oc & np.isfinite(ww) & hrs.notna().values
    def share(mask):
        return 100 * np.average(np.asarray(mask, float)[m], weights=ww[m])
    rec = {"year": y,
           "horas_media": np.average(hrs.fillna(0).values[m], weights=ww[m]),
           "subempleo_visible": share(sub.values),
           "jornada_excesiva": share((hrs > 48).values),
           "corta_<35": share((hrs < 35).values)}
    rows.append(rec)
    print(f"{y}: horas {rec['horas_media']:4.1f}  subempleo {rec['subempleo_visible']:4.1f}%  "
          f">48h {rec['jornada_excesiva']:4.1f}%  <35h {rec['corta_<35']:4.1f}%")

if rows is not None:
    p = pd.DataFrame(rows)
    p.to_csv(CSV, index=False)

# ---- (A) subempleo visible por horas ----
fig, ax = fs.fig_ax()
ax.plot(p.year, p.subempleo_visible, "-o", color=fs.CRANBERRY, lw=2.4, ms=4, mfc="white", mec=fs.CRANBERRY, mew=1.4, zorder=5)
fs.halo_label(ax, p.year.iloc[0], p.subempleo_visible.iloc[0], f"{p.subempleo_visible.iloc[0]:.0f}% ({p.year.iloc[0]})", dy=9, dx=2, fs=9)
fs.halo_label(ax, p.year.iloc[-1], p.subempleo_visible.iloc[-1], f"{p.subempleo_visible.iloc[-1]:.0f}% ({p.year.iloc[-1]})", dy=-15, dx=-2, fs=9, color=fs.CRANBERRY)
ax.set_xlim(2003.5, 2026); ax.set_xticks(range(2004, 2026, 2)); ax.set_ylim(0, max(18, p.subempleo_visible.max() * 1.2))
ax.set_ylabel("Subempleo visible por horas  (% de ocupados)"); ax.set_xlabel("")
fs.statbox(ax, [
    "Subempleo visible (def. OIT/INEI): ocupado que",
    "trabaja <35h, QUERIA trabajar mas y estaba",
    "disponible. Cae 11%(2007)->4%(2025) con el desarrollo.",
    "En 2020 NO sube: la pandemia destruyo empleo (no",
    "subempleo) y limito la disponibilidad para mas horas.",
], loc="upper right")
fs.source(fig, "Fuente: ENAHO 2004-2025 (INEI), modulo 05. Ocupados, ponderado por fac500a. Subempleo por ingresos no incluido.")
fig.tight_layout()
for e in ("pdf", "png"):
    fig.savefig(FIG / f"fig_subempleo_visible.{e}", dpi=200, bbox_inches="tight")
print("OK -> fig_subempleo_visible.pdf")

# ---- (B) horas de trabajo: media + jornada excesiva ----
fig, ax = fs.fig_ax()
ax.plot(p.year, p.horas_media, "-o", color=fs.NAVY, lw=2.4, ms=4, mfc="white", mec=fs.NAVY, mew=1.4, zorder=5)
ax.axhline(48, color=fs.GREY, lw=1, ls="--", zorder=1)
fs.halo_label(ax, 2004.5, 48.6, "limite OIT 48h/semana", fs=8.2, color=fs.GREY)
fs.halo_label(ax, p.year.iloc[-1], p.horas_media.iloc[-1], f"{p.horas_media.iloc[-1]:.0f}h ({p.year.iloc[-1]})", dy=-14, dx=-2, fs=9, color=fs.NAVY)
fs.halo_label(ax, p.year.iloc[0], p.horas_media.iloc[0], f"{p.horas_media.iloc[0]:.0f}h ({p.year.iloc[0]})", dy=10, dx=2, fs=9, color=fs.NAVY)
ax.set_xlim(2003.5, 2026); ax.set_xticks(range(2004, 2026, 2)); ax.set_ylim(30, 50)
ax.set_ylabel("Horas trabajadas por semana (promedio, ocupados)"); ax.set_xlabel("")
fs.statbox(ax, [
    f"Jornada media baja de {p.horas_media.iloc[0]:.0f}h a {p.horas_media.iloc[-1]:.0f}h/semana.",
    f"Jornada excesiva (>48h): {p.jornada_excesiva.iloc[0]:.0f}% -> {p.jornada_excesiva.iloc[-1]:.0f}%.",
    "Caida fuerte en 2020 (COVID).",
], loc="lower left")
fs.source(fig, "Fuente: ENAHO 2004-2025 (INEI), modulo 05, i518 (horas totales). Ocupados, ponderado por fac500a.")
fig.tight_layout()
for e in ("pdf", "png"):
    fig.savefig(FIG / f"fig_horas_trabajo.{e}", dpi=200, bbox_inches="tight")
print("OK -> fig_horas_trabajo.pdf")
