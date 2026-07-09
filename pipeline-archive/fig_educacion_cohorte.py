"""
fig_educacion_cohorte.py - Anios de educacion por cohorte de nacimiento y sexo (M03)
=====================================================================================
Cohorte sintetica de la ENAHO 2025: para los adultos 25-69 anios, anio de nacimiento =
2025 - edad. Se promedian los anios de escolaridad por cohorte (bins de 5 anios) y sexo.
Muestra la EXPANSION educativa intergeneracional y el CRUCE de genero (las mujeres jovenes
alcanzan y superan a los hombres). p301a->anios con el diccionario oficial; codigos 1-11
estables (verificado), cod 12 (basica especial) raro. Ponderado por factor07.

Restringido a 25-69: <25 aun no completan educacion; >69 tiene seleccion por mortalidad.
Run: python fig_educacion_cohorte.py
"""
from __future__ import annotations
from pathlib import Path
import numpy as np, pandas as pd
import figstyle as fs

ROOT = Path(__file__).resolve().parents[1]; RAW = ROOT / "raw"
FIG = ROOT / "figures" / "05_demografia_salud_educacion"; FIG.mkdir(parents=True, exist_ok=True)
DATA = ROOT / "datasets"
YEAR = 2025
EDU = {1: 0, 2: 0, 3: 3, 4: 6, 5: 9, 6: 11, 7: 13, 8: 14, 9: 14, 10: 17, 11: 19, 12: 6}

import pyreadstat
df, _ = pyreadstat.read_dta(str(RAW / "educacion" / f"enaho-{YEAR}-03.dta"), encoding="latin1")
df.columns = [c.lower() for c in df.columns]
n = lambda c: pd.to_numeric(df[c], errors="coerce")
df["anios"] = n("p301a").map(EDU)
df["edad"] = n("p208a"); df["nac"] = YEAR - df["edad"]
df["sexo"] = n("p207"); df["w"] = n("factor07")
d = df[(df.edad >= 25) & (df.edad <= 69)].dropna(subset=["anios", "nac", "sexo", "w"]).copy()
d["coh"] = (d["nac"] // 5) * 5                                # bins quinquenales

rows = []
for coh, g in d.groupby("coh"):
    if coh < 1956:
        continue
    rec = {"cohorte": int(coh)}
    for sx, name in [(1, "Hombres"), (2, "Mujeres")]:
        s = g[g.sexo == sx]
        rec[name] = np.average(s["anios"], weights=s["w"]) if len(s) else np.nan
    rec["n"] = len(g)
    rows.append(rec)
p = pd.DataFrame(rows).sort_values("cohorte")
p.to_csv(DATA / "educacion_cohorte_2025.csv", index=False)
print(p.round(1).to_string(index=False))

fig, ax = fs.fig_ax()
x = p.cohorte.values + 2                                       # centro del quinquenio
ax.plot(x, p.Hombres, "-o", color=fs.NAVY, lw=2.4, ms=5, mfc="white", mec=fs.NAVY, mew=1.4, zorder=5)
ax.plot(x, p.Mujeres, "-o", color=fs.CRANBERRY, lw=2.4, ms=5, mfc="white", mec=fs.CRANBERRY, mew=1.4, zorder=5)
# marcar el cruce (primera cohorte donde mujeres >= hombres)
cross = p[p.Mujeres >= p.Hombres]
if len(cross):
    cx = int(cross.cohorte.iloc[0]) + 2; cy = cross.Mujeres.iloc[0]
    ax.scatter([cx], [cy], s=90, color=fs.GOLD, zorder=7, edgecolor="white", lw=1.3)
    fs.halo_label(ax, cx, cy, f"cruce de genero ~{int(cross.cohorte.iloc[0])}", dx=-8, dy=-20, fs=9, color=fs.GOLD)
fs.end_labels(ax, [
    (f"Hombres  {p.Hombres.iloc[-1]:.1f}", p.Hombres.iloc[-1], fs.NAVY),
    (f"Mujeres  {p.Mujeres.iloc[-1]:.1f}", p.Mujeres.iloc[-1], fs.CRANBERRY),
], x_end=x[-1], fs=9.5)
ax.set_xlim(x[0] - 2, x[-1] + 9)
ax.set_ylabel("Anios de escolaridad (promedio)")
ax.set_xlabel("Cohorte de nacimiento")
fs.statbox(ax, [
    "Cohorte sintetica (ENAHO 2025, adultos 25-69).",
    "La escolaridad sube ~6 anios en dos generaciones;",
    "las mujeres pasan de rezago a superar a los hombres.",
], loc="upper left")
fs.source(fig, "Fuente: ENAHO 2025 (INEI), modulo 03. Anios de escolaridad por p301a. Ponderado por factor07.")
fig.tight_layout()
for e in ("pdf", "png"):
    fig.savefig(FIG / f"fig_educacion_cohorte.{e}", dpi=200, bbox_inches="tight")
print("OK -> fig_educacion_cohorte.pdf")
