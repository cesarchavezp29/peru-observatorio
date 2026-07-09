"""
fig_cuidados_corte_tiempo.py - El corte de cabello pagado y la cicatriz del confinamiento
================================================================================================
Pregunta: que porcentaje de hogares paga por un corte de cabello en un mes, y como lo golpeo la
pandemia? Margen extensivo del consumo de servicios de arreglo personal.

% de HOGARES con al menos una compra de "corte de cabello" (M78 producto p606n==10, obtenido el
mes anterior y comprado p606e1==1) en el mes, por anio, ponderado por factor07. Lee el CSV que
arma fig_cuidados_servicios_tiempo.py (--rebuild ahi para reconstruir). Un plot.
Run: python fig_cuidados_corte_tiempo.py
"""
from __future__ import annotations
from pathlib import Path
import numpy as np, pandas as pd
import figstyle as fs

ROOT = Path(__file__).resolve().parents[1]
FIG = ROOT / "figures" / "11_consumo"; FIG.mkdir(parents=True, exist_ok=True)
CSV = ROOT / "datasets" / "cuidados_personales_tiempo.csv"

p = pd.read_csv(CSV).dropna(subset=["haircut_part"]).sort_values("year")

fs.use()
fig, ax = fs.fig_ax()
ax.plot(p.year, p.haircut_part, "-o", color=fs.NAVY, lw=2.4, ms=4.4, mfc="white",
        mec=fs.NAVY, mew=1.3, zorder=5)
fs.end_labels(ax, [(f"Corte pagado  {p.haircut_part.iloc[-1]:.0f}%", p.haircut_part.iloc[-1], fs.NAVY)],
              x_end=p.year.max(), fs=9)
pre = float(p.loc[p.year == 2019, "haircut_part"].iloc[0])
ax.axhline(pre, color=fs.GREY, lw=1.0, ls=(0, (4, 3)), zorder=1)
ax.axvspan(2019.6, 2020.4, color=fs.GREY, alpha=0.10, zorder=0)
ax.set_xlim(2003.4, 2028.5); ax.set_xticks(range(2004, 2026, 3))
ax.set_ylim(0, 72)
ax.set_ylabel("% de hogares que paga un corte de cabello en el mes"); ax.set_xlabel("")
fs.halo_label(ax, 2013, pre, f"Pico pre-pandemia {pre:.0f}% (2019)", dy=2.2, fs=8.5, color=fs.GREY)
fs.statbox(ax, [
    "El corte de cabello pagado subio de 43% a 61% de",
    "hogares (2004-2019). El confinamiento 2020 lo hundio",
    "a 44% de golpe y, a diferencia del gasto total, NO",
    "volvio al pico: se estanco cerca de 50% (DIY en casa,",
    "presion de presupuesto). Cicatriz que aun no cierra.",
], loc="lower right")
fs.source(fig, "Fuente: ENAHO 2004-2025 (INEI), modulo 78 (gastos en cuidados personales, 606D). "
               "% de hogares con compra de corte de cabello (p606n=10) en el mes, ponderado por factor07. "
               "Faltan 2005, 2007-2010, 2012 (modulo no recolectado).")
fig.tight_layout()
for e in ("pdf", "png"):
    fig.savefig(FIG / f"fig_cuidados_corte_tiempo.{e}", dpi=200, bbox_inches="tight")
print("OK -> fig_cuidados_corte_tiempo.pdf")
