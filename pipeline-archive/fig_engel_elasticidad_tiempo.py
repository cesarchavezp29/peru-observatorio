"""
fig_engel_elasticidad_tiempo.py - Se volvio el Peru menos "necesitado"? Elasticidad-gasto 2004-2025
====================================================================================================
Pregunta: a medida que el Peru se hizo mas rico (gasto real pc S/659 en 2004 -> ~S/920 en 2025),
cambio el caracter de necesidad de los alimentos? La curva de Engel se aplana?

Para cada anio se estima la elasticidad-gasto Working-Leser de cada grupo (w_g = a + b ln(gasto
real pc); elasticidad = 1 + b/wbar), ponderada por factornd07. Se grafican ALIMENTOS (necesidad)
y ESPARCIMIENTO/EDUCACION/CULTURA (lujo) 2004-2025. Datos: gasto real pc por grupo del hogar
(validate_gasto.gasto_groups_hh, metodologia INEL, deflactado base 2025). Un plot, figstyle.
Run: python fig_engel_elasticidad_tiempo.py [--rebuild]
"""
from __future__ import annotations
from pathlib import Path
import sys
import numpy as np, pandas as pd
import figstyle as fs
import enaho_codes as ec
from validate_gasto import gasto_groups_hh, GROUP_LABELS

ROOT = Path(__file__).resolve().parents[1]
FIG = ROOT / "figures" / "11_consumo"; FIG.mkdir(parents=True, exist_ok=True)
CSV = ROOT / "datasets" / "engel_elasticidad_tiempo_2004_2025.csv"


def elas_year(year):
    df = gasto_groups_hh(year)
    m = df["gpgru0"].gt(0) & df["factornd07"].gt(0) & np.isfinite(df["gpgru0"])
    d = df.loc[m]
    w = d["factornd07"].values; lnx = np.log(d["gpgru0"].values); W = w.sum()
    out = {}
    for k in GROUP_LABELS:
        g = d["g_" + k].clip(lower=0).fillna(0).values
        wg = g / d["gpgru0"].values
        wbar = np.sum(w * wg) / W
        X = np.column_stack([np.ones_like(lnx), lnx]); sw = np.sqrt(w)
        beta, *_ = np.linalg.lstsq(X * sw[:, None], wg * sw, rcond=None)
        out[k] = 1 + beta[1] / wbar
    return out


if CSV.exists() and "--rebuild" not in sys.argv:
    p = pd.read_csv(CSV)
else:
    rows = []
    for y in ec.years():
        try:
            e = elas_year(y)
        except Exception as ex:
            print(f"{y}: FAIL {repr(ex)[:70]}"); continue
        e["year"] = y; rows.append(e)
        print(f"{y}: alimentos {e['i01']:.2f}  esparcim {e['i07']:.2f}  salud {e['i05']:.2f}")
    p = pd.DataFrame(rows).sort_values("year")
    p.to_csv(CSV, index=False)

fig, ax = fs.fig_ax()
ax.axhline(1.0, color=fs.GREY, lw=1.2, ls="--", zorder=1)
series = [("i01", "Alimentos", fs.CRANBERRY), ("i07", "Esparcimiento, educacion y cultura", fs.NAVY)]
labels = []
for k, name, c in series:
    ax.plot(p.year, p[k], "-o", color=c, lw=2.4, ms=4, mfc="white", mec=c, mew=1.4, zorder=5)
    labels.append((f"{name}  {p[k].iloc[-1]:.2f}", p[k].iloc[-1], c))
fs.end_labels(ax, labels, x_end=p.year.max(), fs=8.5)
ax.set_xlim(2003.5, 2032); ax.set_xticks(range(2004, 2026, 3)); ax.set_ylim(0.55, 1.55)
ax.set_ylabel("Elasticidad-gasto (Working-Leser)"); ax.set_xlabel("")
ax.annotate("lujo", (2004.2, 1.02), fontsize=9, color=fs.NAVY, style="italic", va="bottom")
ax.annotate("necesidad", (2004.2, 0.98), fontsize=9, color=fs.CRANBERRY, style="italic", va="top")
f_lo, f_hi = p["i01"].min(), p["i01"].max()
fs.statbox(ax, [
    f"Pese a 20 anios de crecimiento, la elasticidad de los",
    f"alimentos apenas se mueve ({f_lo:.2f}-{f_hi:.2f}): la ley de Engel",
    "es estable y la jerarquia de consumo no cambia.",
    "(La salud si subio a ~1.45 en la pandemia 2021-24.)",
], loc="upper right")
fs.source(fig, "Fuente: ENAHO 2004-2025 (INEI), Sumaria. Curva de Engel Working-Leser anual, gasto real pc por grupo (base 2025), ponderado por factornd07.")
fig.tight_layout()
for e in ("pdf", "png"):
    fig.savefig(FIG / f"fig_engel_elasticidad_tiempo.{e}", dpi=200, bbox_inches="tight")
print("OK -> fig_engel_elasticidad_tiempo.pdf")
