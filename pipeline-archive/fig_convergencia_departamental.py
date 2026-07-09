"""
fig_convergencia_departamental.py - Convergen los departamentos? Dispersion regional 2004-2025
===============================================================================================
Pregunta: en estos 20 anios de crecimiento, los departamentos pobres se acercaron a los ricos
(sigma-convergencia) o la brecha regional se mantuvo?

Metrica: desviacion estandar del LOG del ingreso real pc departamental (sigma-convergencia
estandar) entre los 25 departamentos, por anio. Ingreso real pc = ipcr_0 (metodologia INEI,
deflactado base 2025, validado), tomado del panel departamento (build_panel_departamento.py).
Cae => convergencia. Un plot, figstyle.
Run: python fig_convergencia_departamental.py
"""
from __future__ import annotations
from pathlib import Path
import numpy as np, pandas as pd
import figstyle as fs

ROOT = Path(__file__).resolve().parents[1]
FIG = ROOT / "figures" / "00_panorama"; FIG.mkdir(parents=True, exist_ok=True)
PANEL = ROOT / "datasets" / "panel_departamento_2004_2025.csv"
CSV = ROOT / "datasets" / "convergencia_departamental_2004_2025.csv"

d = pd.read_csv(PANEL, dtype={"dpto": str})
inc = d[d.indicator == "ingreso_real_pc"]
rows = []
for y, g in inc.groupby("year"):
    v = g["value"].dropna().values
    if len(v) < 20:
        continue
    lg = np.log(v)
    rows.append({"year": int(y), "std_log": lg.std(ddof=1), "cv": v.std(ddof=1) / v.mean(),
                 "min": v.min(), "max": v.max(), "media": v.mean()})
p = pd.DataFrame(rows).sort_values("year").reset_index(drop=True)
p.to_csv(CSV, index=False)
print(p[["year", "std_log", "cv", "min", "max"]].round(3).to_string(index=False))

fig, ax = fs.fig_ax()
ax.plot(p.year, p.std_log, "-o", color=fs.NAVY, lw=2.6, ms=4.5, mfc="white", mec=fs.NAVY, mew=1.5, zorder=5)
fs.end_labels(ax, [(f"sigma  {p.std_log.iloc[-1]:.2f}", p.std_log.iloc[-1], fs.NAVY)],
              x_end=p.year.max(), fs=9)
s0, s1 = p.std_log.iloc[0], p.std_log.iloc[-1]
ax.set_xlim(2003.5, 2031); ax.set_xticks(range(2004, 2026, 3))
ax.set_ylabel("Desv. estandar del log del ingreso real pc entre deptos"); ax.set_xlabel("")
fs.statbox(ax, [
    f"La dispersion entre departamentos cae de {s0:.2f} ({int(p.year.iloc[0])})",
    f"a {s1:.2f} ({int(p.year.iloc[-1])}): {100*(1-s1/s0):.0f}% menos.",
    "Los departamentos pobres se acercaron a los ricos",
    "(sigma-convergencia en nivel de vida).",
], loc="upper right")
fs.source(fig, "Fuente: ENAHO 2004-2025 (INEI), Sumaria. Ingreso real pc por depto (ipcr_0, base 2025). Sigma = sd(log) entre 25 deptos.")
fig.tight_layout()
for e in ("pdf", "png"):
    fig.savefig(FIG / f"fig_convergencia_departamental.{e}", dpi=200, bbox_inches="tight")
print("OK -> fig_convergencia_departamental.pdf")
