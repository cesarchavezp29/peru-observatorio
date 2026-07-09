"""
fig_corr_between_within.py - Es la pobreza-desarrollo un hecho REGIONAL o TEMPORAL? (panel dept-anio)
=====================================================================================================
Pregunta: la conocida relacion "mas educacion/ingreso -> menos pobreza" que se ve ENTRE
departamentos, se sostiene tambien DENTRO de cada departamento a lo largo del tiempo, una vez
que se quitan las diferencias regionales fijas y la tendencia nacional comun?

- BETWEEN: correlacion de los promedios 2004-2025 de cada depto (25 puntos). Foto transversal.
- WITHIN: correlacion sobre el residuo de doble-demeaning (resto media del depto y media del anio).
  Aisla el co-movimiento idiosincratico depto-en-el-tiempo, neto de la tendencia nacional.

Lee datasets/panel_departamento_2004_2025.csv. Foco = pobreza. Un plot: dumbbell between vs within.
Run: python fig_corr_between_within.py
"""
from __future__ import annotations
from pathlib import Path
import numpy as np, pandas as pd
import figstyle as fs

ROOT = Path(__file__).resolve().parents[1]
CSV = ROOT / "datasets" / "panel_departamento_2004_2025.csv"
FIG = ROOT / "figures" / "00_panorama"; FIG.mkdir(parents=True, exist_ok=True)
OUTCSV = ROOT / "datasets" / "corr_between_within_pobreza.csv"

FOCAL = "pobreza"
NICE = {"ingreso_real_pc": "Ingreso real pc", "educ_anios_25": "Anios de educacion (25+)",
        "analfabetismo_15": "Analfabetismo", "lengua_indigena": "Lengua indigena",
        "pct_sis": "Afiliacion SIS", "pct_60mas": "Adultos mayores (60+)"}

d = pd.read_csv(CSV)
w = d.pivot_table(index=["dpto", "year"], columns="indicator", values="value").reset_index()


def two_way_within(df, col):
    """residuo = x - media_depto - media_anio + media_global (solo sobre filas con foco y col)."""
    x = df[col]
    x = x - df.groupby("dpto")[col].transform("mean")
    x = x - df.groupby("year")[col].transform("mean") + df[col].mean()
    return x


rows = []
for k, nice in NICE.items():
    if k not in w.columns:
        continue
    sub = w.dropna(subset=[FOCAL, k]).copy()
    # between: medias por depto
    bm = sub.groupby("dpto")[[FOCAL, k]].mean().dropna()
    rb = np.corrcoef(bm[FOCAL], bm[k])[0, 1] if len(bm) > 2 else np.nan
    # within: doble-demean pooled
    fy = two_way_within(sub, FOCAL); xy = two_way_within(sub, k)
    ok = fy.notna() & xy.notna()
    rw = np.corrcoef(fy[ok], xy[ok])[0, 1] if ok.sum() > 3 else np.nan
    rows.append({"indicador": nice, "between": rb, "within": rw, "n_depto": len(bm), "n_obs": int(ok.sum())})
    print(f"{nice:26} between r={rb:+.2f}  within r={rw:+.2f}")

r = pd.DataFrame(rows)
r["sort"] = r["between"].abs(); r = r.sort_values("sort").reset_index(drop=True)  # noqa
r.drop(columns="sort").to_csv(OUTCSV, index=False)

fig, ax = fs.fig_ax(w=10.5, h=6.2)
y = np.arange(len(r))
ax.axvline(0, color=fs.GREY, lw=1.2, zorder=1)
for yi, (_, row) in zip(y, r.iterrows()):
    rb, rw = row["between"], row["within"]
    ax.plot([rb, rw], [yi, yi], "-", color=fs.GREY, lw=1.6, alpha=0.6, zorder=2)
    ax.plot(rb, yi, "o", color=fs.NAVY, ms=9, mfc=fs.NAVY, mec="white", mew=1.2, zorder=5)
    ax.plot(rw, yi, "o", color=fs.CRANBERRY, ms=9, mfc=fs.CRANBERRY, mec="white", mew=1.2, zorder=5)
ax.set_yticks(y); ax.set_yticklabels(r["indicador"], fontsize=9.5)
ax.set_xlim(-1.05, 1.05); ax.set_xlabel(f"Correlacion con la pobreza departamental")
ax.set_ylabel("")
# leyenda manual
ax.plot([], [], "o", color=fs.NAVY, label="ENTRE deptos (corte transversal)")
ax.plot([], [], "o", color=fs.CRANBERRY, label="DENTRO del depto en el tiempo (doble-demean)")
ax.legend(loc="lower left", frameon=False, fontsize=9)
fs.source(fig, "Fuente: ENAHO 2004-2025 (INEI), panel 25 deptos x 22 anios. Within = residuo tras quitar efecto fijo de depto y de anio.")
fig.tight_layout()
for e in ("pdf", "png"):
    fig.savefig(FIG / f"fig_corr_between_within.{e}", dpi=200, bbox_inches="tight")
print("OK -> fig_corr_between_within.pdf")
