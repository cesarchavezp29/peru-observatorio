"""
fig_seguro_salud_evolution.py - La gran expansion del aseguramiento en salud 2004-2025
=======================================================================================
Modulo 04 (Salud). Bateria de afiliacion p4191..p4198 (cada una "esta afiliado a X",
1=si). Slots VERIFICADOS por trayectoria empirica + cuestionario: p4191=EsSalud
(contributivo), p4195=SIS (publico, subsidiado). "Algun seguro" = cualquiera de
p4191..p4198 ==1. Ponderado por factor07.

La etiqueta de columna se vuelve generica en anios nuevos ("El sistema de prestacion de
seguro...") y el value-label de p4195 esta mal escrito en 2005, pero la variable es SIS
todo el periodo (ver docs/INCONSISTENCIES.md). Tres series, un eje, paleta figstyle.
Run: python fig_seguro_salud_evolution.py
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
    p = RAW / "salud" / f"enaho-{year}-04.dta"
    if not p.exists():
        return None
    try:
        import pyreadstat
        df, _ = pyreadstat.read_dta(str(p), encoding="latin1")
    except Exception:
        df = pd.read_stata(p, convert_categoricals=False)
    df.columns = [c.lower() for c in df.columns]
    return df


SERIES = {"Algun seguro de salud": fs.PALETTE[0], "SIS (publico)": fs.PALETTE[1],
          "EsSalud (contributivo)": fs.PALETTE[2]}

rows = []
for y in ec.years():
    df = L(y)
    if df is None or "factor07" not in df.columns:
        continue
    w = pd.to_numeric(df["factor07"], errors="coerce").fillna(0).values
    sis = (pd.to_numeric(df.get("p4195"), errors="coerce") == 1).values
    ess = (pd.to_numeric(df.get("p4191"), errors="coerce") == 1).values
    any_ = np.zeros(len(df), bool)
    for k in range(1, 9):
        c = f"p419{k}"
        if c in df.columns:
            any_ = any_ | (pd.to_numeric(df[c], errors="coerce") == 1).values
    rows.append({"year": y, "Algun seguro de salud": 100 * np.average(any_, weights=w),
                 "SIS (publico)": 100 * np.average(sis, weights=w),
                 "EsSalud (contributivo)": 100 * np.average(ess, weights=w)})
    print(f"{y}: any {rows[-1]['Algun seguro de salud']:4.1f}  SIS {rows[-1]['SIS (publico)']:4.1f}  EsSalud {rows[-1]['EsSalud (contributivo)']:4.1f}")

panel = pd.DataFrame(rows).set_index("year")
panel.to_csv(DATA / "seguro_salud_2004_2025.csv")

fig, ax = fs.fig_ax()
for name, col in SERIES.items():
    s = panel[name].dropna()
    ax.plot(s.index, s.values, "-o", color=col, lw=2.4, ms=4, mfc="white", mec=col, mew=1.4, zorder=4)
    fs.halo_label(ax, s.index[-1], s.values[-1], f"{name}  {s.values[-1]:.0f}%", dx=6, dy=-3, fs=9, color=col)
ax.set_xlim(2003.5, 2032)
ax.set_ylim(0, 100)
ax.set_xticks(range(2004, 2026, 2))
ax.set_ylabel("% de la poblacion afiliada")
ax.set_xlabel("")
fs.source(fig, "Fuente: ENAHO 2004-2025 (INEI), modulo 04 (Salud), bateria p4191-p4198. Ponderado por factor07.")
fig.tight_layout()
for e in ("pdf", "png"):
    fig.savefig(FIG / f"fig_seguro_salud_evolution.{e}", dpi=200, bbox_inches="tight")
print("OK -> figures/05_demografia_salud_educacion/fig_seguro_salud_evolution.pdf")
