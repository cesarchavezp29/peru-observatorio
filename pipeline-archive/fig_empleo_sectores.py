"""
fig_empleo_sectores.py - Transformacion estructural: empleo por sector 2004-2025 (M05)
=======================================================================================
Modulo 05 (Empleo). Rama de actividad CIIU rev4 = p506r4 (3-4 digitos). INEI trae p506r4
en TODOS los anios (ademas de p506 rev3) -> sin ruptura: se usa rev4 todo el periodo.
Division CIIU = p506r4 // 100 (111->01 agro, 1010->10 manufactura, 4500->45 comercio).
Se agregan en 6 grandes sectores y se grafica la participacion del empleo por sector
(ocupados, fac500a). Muestra la TRANSFORMACION ESTRUCTURAL (cae lo agropecuario, suben
comercio y servicios). Un plot, paleta figstyle (6 series).
Run: python fig_empleo_sectores.py [--rebuild]
"""
from __future__ import annotations
from pathlib import Path
import sys
import numpy as np, pandas as pd
import figstyle as fs
import enaho_codes as ec

ROOT = Path(__file__).resolve().parents[1]; RAW = ROOT / "raw"
FIG = ROOT / "figures" / "07_empleo"; FIG.mkdir(parents=True, exist_ok=True)
DATA = ROOT / "datasets"
CSV = DATA / "empleo_sectores_2004_2025.csv"

SECTORS = {  # nombre -> (rango de divisiones CIIU rev4, color)
    "Agro, pesca y mineria": (range(1, 10), fs.PALETTE[4]),
    "Manufactura": (range(10, 34), fs.PALETTE[3]),
    "Construccion": (range(41, 44), fs.PALETTE[5]),
    "Comercio": (range(45, 48), fs.PALETTE[1]),
    "Transporte y comunic.": (range(49, 64), fs.PALETTE[2]),
}  # 'Otros servicios' = el resto (residual)
DIV2SEC = {}
for name, (rng, _) in SECTORS.items():
    for d in rng:
        DIV2SEC[d] = name


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


if CSV.exists() and "--rebuild" not in sys.argv:
    p = pd.read_csv(CSV)
else:
    rows = []
    for y in ec.years():
        df = L(y)
        if df is None or "p506r4" not in df.columns:
            continue
        oc = (pd.to_numeric(df["ocu500"], errors="coerce") == 1).values
        w = pd.to_numeric(df.get("fac500a"), errors="coerce")
        w = w.where(w.notna(), pd.to_numeric(df.get("factor07"), errors="coerce"))
        div = (pd.to_numeric(df["p506r4"], errors="coerce") // 100)
        sec = div.map(DIV2SEC).fillna("Otros servicios")
        ww = w.fillna(0).values
        m = oc & np.isfinite(ww) & pd.to_numeric(df["p506r4"], errors="coerce").notna().values
        rec = {"year": y}
        tot = ww[m].sum()
        for name in list(SECTORS) + ["Otros servicios"]:
            rec[name] = 100 * ww[m & (sec == name).values].sum() / tot
        rows.append(rec)
        print(f"{y}: " + "  ".join(f"{k[:5]} {rec[k]:.0f}" for k in list(SECTORS) + ["Otros servicios"]))
    p = pd.DataFrame(rows)
    p.to_csv(CSV, index=False)

COLORS = {**{k: v[1] for k, v in SECTORS.items()}, "Otros servicios": fs.PALETTE[0]}
fig, ax = fs.fig_ax(w=10.8, h=6.6)
ends = []
for name in ["Otros servicios"] + list(SECTORS):
    ax.plot(p.year, p[name], "-o", color=COLORS[name], lw=2.2, ms=3.5, mfc="white", mec=COLORS[name], mew=1.2, zorder=4)
    ends.append((f"{name}  {p[name].iloc[-1]:.0f}%", p[name].iloc[-1], COLORS[name]))
fs.end_labels(ax, ends, x_end=p.year.iloc[-1], fs=8.8)
ax.set_xlim(2003.5, 2032.5); ax.set_xticks(range(2004, 2026, 2))
ax.set_ylim(0, max(40, p[list(COLORS)].max().max() * 1.12))
ax.set_ylabel("% del empleo total (ocupados)"); ax.set_xlabel("")
fs.source(fig, "Fuente: ENAHO 2004-2025 (INEI), modulo 05, rama CIIU rev4 (p506r4). Ocupados, ponderado por fac500a.")
fig.tight_layout()
for e in ("pdf", "png"):
    fig.savefig(FIG / f"fig_empleo_sectores.{e}", dpi=200, bbox_inches="tight")
print("OK -> fig_empleo_sectores.pdf")
