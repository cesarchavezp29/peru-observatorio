"""
fig_trabajo_adolescente_escuela_tiempo.py - Adolescentes 14-17: estudiar y trabajar dejaron
de ser excluyentes
================================================================================================
MULTI-MODULO (M05 empleo x M03 educacion x edad): descomposicion de la situacion de los
adolescentes 14-17 en cuatro estados, 2004-2025.

  - solo estudia        (M03: matriculado p306==1 y asiste p307==1; M05: ocu500!=1)
  - estudia y trabaja   (estudia Y ocu500==1)
  - solo trabaja        (ocu500==1 y NO estudia)
  - ni estudia ni trabaja (el grupo de mayor riesgo)

Lee el CSV que arma fig_trabajo_adolescente_pobreza_tiempo.py (--rebuild alla). Ponderado por
fac500a. Codigos p306/p307 (1=si/2=no) y ocu500 (1=ocupado) VERIFICADOS estables 2004-2025
(verify_codes.py). Un plot. Run: python fig_trabajo_adolescente_escuela_tiempo.py
"""
from __future__ import annotations
from pathlib import Path
import pandas as pd
import figstyle as fs

ROOT = Path(__file__).resolve().parents[1]
FIG = ROOT / "figures" / "07_empleo"; FIG.mkdir(parents=True, exist_ok=True)
CSV = ROOT / "datasets" / "trabajo_adolescente_tiempo.csv"

p = pd.read_csv(CSV).sort_values("year")

fs.use()
fig, ax = fs.fig_ax()
lines = [("Solo estudia", "only_study", fs.NAVY),
         ("Estudia y trabaja", "study_work", fs.GOLD),
         ("Solo trabaja", "only_work", fs.CRANBERRY),
         ("Ni estudia ni trabaja", "neither", fs.STEEL)]
labels = []
for name, col, c in lines:
    s = p.dropna(subset=[col])
    ax.plot(s.year, s[col], "-o", color=c, lw=2.3, ms=3.8, mfc="white", mec=c, mew=1.2, zorder=5)
    labels.append((f"{name}  {s[col].iloc[-1]:.0f}%", s[col].iloc[-1], c))
fs.end_labels(ax, labels, x_end=p.year.max(), fs=8.2)
ax.axvspan(2019.6, 2020.4, color=fs.GREY, alpha=0.10, zorder=0)
ax.set_xlim(2003.4, 2029); ax.set_xticks(range(2004, 2026, 3)); ax.set_ylim(0, 78)
ax.set_ylabel("% de adolescentes 14-17"); ax.set_xlabel("")
fs.statbox(ax, [
    "La escuela gano: 'solo estudia' subio de 41% a 59% y",
    "'solo trabaja' (abandono por trabajo) cayo de 24% a 9%.",
    "Pero el 'ni estudia ni trabaja' NO mejoro: sigue ~20%,",
    "un nucleo adolescente al margen que el crecimiento no",
    "redujo. M05 empleo x M03 educacion (matricula+asiste).",
], loc="upper left")
fs.source(fig, "Fuente: ENAHO 2004-2025 (INEI), modulo 05 (Empleo) x modulo 03 (Educacion). Estados de 14-17 anios "
               "(estudia = matriculado y asiste; trabaja = ocupado), ponderado por fac500a.")
fig.tight_layout()
for e in ("pdf", "png"):
    fig.savefig(FIG / f"fig_trabajo_adolescente_escuela_tiempo.{e}", dpi=200, bbox_inches="tight")
print("OK -> fig_trabajo_adolescente_escuela_tiempo.pdf")
