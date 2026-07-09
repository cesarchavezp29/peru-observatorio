"""
fig_migracion_interna_tiempo.py - La migracion interna es cosa de jovenes (M04, 2016-2025)
================================================================================================
Pregunta: que fraccion de la poblacion vivia en otro distrito hace 5 anios (migrante interno
reciente), y como se reparte por edad? Cambio con la pandemia?

Modulo 04 (Salud), p401f "Hace 5 anios, vivia en este distrito?" (1=Si, 2=No=migrante,
3=Aun no habia nacido). Disponible 2016-2025. MIGRANTE RECIENTE = p401f==2; denominador =
quienes ya habian nacido hace 5 anios (p401f in {1,2}, excluye codigo 3). Edad = anio - anio de
nacimiento (p400a3). Tasa ponderada por factor07.

CAVEAT (honesto): mide cambio de DISTRITO en 5 anios (incluye mudanzas entre distritos vecinos de
una misma area metropolitana; no toda migracion). Distritos creados despues de 2015 pueden inflar
levemente. 2020 = ENAHO parcialmente telefonica por COVID. Un plot.
Run: python fig_migracion_interna_tiempo.py [--rebuild]
"""
from __future__ import annotations
from pathlib import Path
import sys
import numpy as np, pandas as pd
import figstyle as fs

ROOT = Path(__file__).resolve().parents[1]; RAW = ROOT / "raw"
FIG = ROOT / "figures" / "05_demografia_salud_educacion"; FIG.mkdir(parents=True, exist_ok=True)
CSV = ROOT / "datasets" / "migracion_interna_tiempo.csv"
SRC = RAW / "salud"
YEARS = list(range(2016, 2026))
GROUPS = [("5-17", 5, 17), ("18-29", 18, 29), ("30-49", 30, 49), ("50+", 50, 200)]


def num(s):
    return pd.to_numeric(s, errors="coerce")


def rd(p, cols):
    import pyreadstat
    have = pyreadstat.read_dta(str(p), metadataonly=True)[1].column_names
    cl = {c.lower(): c for c in have}
    d, _ = pyreadstat.read_dta(str(p), encoding="latin1", usecols=[cl[c] for c in cols if c in cl])
    d.columns = [c.lower() for c in d.columns]
    return d


if CSV.exists() and "--rebuild" not in sys.argv:
    p = pd.read_csv(CSV)
else:
    rows = []
    for y in YEARS:
        f = SRC / f"enaho-{y}-04.dta"
        if not f.exists():
            continue
        df = rd(f, ["p401f", "p400a3", "factor07"])
        fr = num(df["p401f"]); w = num(df["factor07"]).fillna(0)
        age = y - num(df["p400a3"])
        valid = fr.isin([1, 2]); mig = (fr == 2)
        rec = {"year": y, "overall": 100 * w[mig & valid].sum() / w[valid].sum()}
        for name, lo, hi in GROUPS:
            b = valid & age.between(lo, hi)
            rec[name] = 100 * w[mig & b].sum() / w[b].sum() if w[b].sum() > 0 else np.nan
        rows.append(rec)
        print(f"{y}: overall {rec['overall']:4.1f}% | " + "  ".join(f"{g} {rec[g]:4.1f}" for g, _, _ in GROUPS))
    p = pd.DataFrame(rows).sort_values("year")
    p.to_csv(CSV, index=False)

fs.use()
fig, ax = fs.fig_ax()
cols = [("18-29", fs.CRANBERRY), ("30-49", fs.NAVY), ("5-17", fs.GOLD), ("50+", fs.STEEL)]
labels = []
for name, c in cols:
    s = p.dropna(subset=[name])
    ax.plot(s.year, s[name], "-o", color=c, lw=2.3, ms=4.0, mfc="white", mec=c, mew=1.2, zorder=5)
    labels.append((f"{name} anios  {s[name].iloc[-1]:.0f}%", s[name].iloc[-1], c))
fs.end_labels(ax, labels, x_end=p.year.max(), fs=8.4)
ax.axvspan(2019.6, 2020.4, color=fs.GREY, alpha=0.10, zorder=0)
ax.set_xlim(2015.6, 2028.3); ax.set_xticks(range(2016, 2026, 2)); ax.set_ylim(0, 14.5)
ax.set_ylabel("% que vivia en otro distrito hace 5 anios"); ax.set_xlabel("")
fs.statbox(ax, [
    "La migracion interna es de jovenes: a los 18-29 anios",
    "se cambia de distrito al doble-triple que despues de los",
    "50. El confinamiento 2020 la freno (minimo) y rebroto en",
    "2021-22; la tendencia de fondo baja suave (urbanizacion",
    "que madura). Mide mudanza de distrito en 5 anios.",
], loc="upper right")
fs.source(fig, "Fuente: ENAHO 2016-2025 (INEI), modulo 04 (Salud), p401f. % de personas (nacidas hace 5+ anios) que "
               "vivia en otro distrito hace 5 anios, por edad, ponderado por factor07.")
fig.tight_layout()
for e in ("pdf", "png"):
    fig.savefig(FIG / f"fig_migracion_interna_tiempo.{e}", dpi=200, bbox_inches="tight")
print("OK -> fig_migracion_interna_tiempo.pdf")
