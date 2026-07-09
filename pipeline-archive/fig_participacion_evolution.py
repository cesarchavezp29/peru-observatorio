"""
fig_participacion_evolution.py - Participacion en organizaciones sociales 2004-2025
===================================================================================
Modulo 84 (Participacion ciudadana), pregunta 801 (jefe/conyuge responde por el hogar).
Encoding VERIFICADO (CED-01-800 2004/2013/2025 + distribuciones): p801_<k> guarda el
valor <k> si el hogar pertenece a la organizacion <k>, si no 0. Es decir el indice del
slot ES el codigo de la organizacion -> pertenece = (p801_k == k).

COMPARABILIDAD (verificada en cuestionarios): los codigos 1-12 son IDENTICOS en el
esquema viejo (2004-2011) y nuevo (2013-2025). Los codigos 13+ y el de "no pertenece"
(18 viejo / 19 nuevo) SI cambian -> esta figura usa solo organizaciones con codigo 1-12.

Foco: organizaciones de supervivencia (vaso de leche, comedor popular, club de madres)
vs civicas (partido, ronda, APAFA). Ponderado por factor07 del hogar.
Run: python fig_participacion_evolution.py
"""
from __future__ import annotations
from pathlib import Path
import numpy as np, pandas as pd
import figstyle as fs
import enaho_codes as ec

ROOT = Path(__file__).resolve().parents[1]; RAW = ROOT / "raw"
FIG = ROOT / "figures" / "09_participacion"; FIG.mkdir(parents=True, exist_ok=True)
DATA = ROOT / "datasets"

# codigo (=indice de slot) -> (nombre, color). Solo codigos 1-12 (estables todos los anios).
ORGS = {
    11: ("Vaso de leche", fs.PALETTE[0]),
    12: ("Comedor popular", fs.PALETTE[1]),
    9:  ("Club de madres", fs.PALETTE[2]),
    10: ("APAFA (padres de familia)", fs.PALETTE[3]),
    5:  ("Ronda campesina", fs.PALETTE[4]),
    2:  ("Agrupacion/partido politico", fs.PALETTE[5]),
}


def L(folder, mod, year):
    p = RAW / folder / f"enaho-{year}-{mod}.dta"
    if not p.exists():
        return None
    try:
        import pyreadstat
        df, _ = pyreadstat.read_dta(str(p), encoding="latin1")
    except Exception:
        df = pd.read_stata(p, convert_categoricals=False)
    df.columns = [c.lower() for c in df.columns]
    return df


rows = []
for y in ec.years():
    g = L("participacion_ciudadana", "84", y)
    if g is None or "p801_11" not in g.columns:
        continue
    f = pd.to_numeric(g.get("factor07"), errors="coerce")
    if f is None or f.isna().all():
        continue
    w = f.values
    rec = {"year": y}
    for code, (name, _) in ORGS.items():
        v = f"p801_{code}"
        if v in g.columns:
            belongs = (pd.to_numeric(g[v], errors="coerce") == code).astype(float).values
            ok = np.isfinite(belongs) & np.isfinite(w)
            rec[name] = 100 * np.average(belongs[ok], weights=w[ok])
    rows.append(rec)
    print(f"{y}: " + "  ".join(f"{n[:10]} {rec.get(n, float('nan')):4.1f}%" for _, (n, _) in ORGS.items()))

panel = pd.DataFrame(rows).set_index("year")
panel.to_csv(DATA / "participacion_organizaciones_2004_2025.csv")

fig, ax = fs.fig_ax()
ends = []
for code, (name, col) in ORGS.items():
    s = panel[name].dropna()
    ax.plot(s.index, s.values, "-o", color=col, lw=2.2, ms=4, mfc="white", mec=col, mew=1.3, zorder=4)
    ends.append([s.values[-1], name, col, s.values[-1]])  # [label_y, name, col, true_y]
# separar etiquetas con un gap minimo (de mayor a menor)
ends.sort(key=lambda r: -r[0])
GAP = 0.9
for i in range(1, len(ends)):
    if ends[i - 1][0] - ends[i][0] < GAP:
        ends[i][0] = ends[i - 1][0] - GAP
xend = panel.index[-1]
for label_y, name, col, true_y in ends:
    ax.annotate(f"{name}  {true_y:.0f}%", xy=(xend, true_y), xytext=(xend + 1.0, label_y),
                fontsize=8.8, color=col, va="center",
                arrowprops=dict(arrowstyle="-", color=col, lw=0.6, alpha=0.5,
                                shrinkA=0, shrinkB=2)).set_zorder(6)
ax.set_xlim(2003.5, 2032.5)
ax.set_ylim(0, max(12, panel.max().max() * 1.15))
ax.set_xticks(range(2004, 2026, 2))
ax.set_ylabel("% de hogares con algun miembro que participa")
ax.set_xlabel("")
fs.source(fig, "Fuente: ENAHO 2004-2025 (INEI), modulo 84 (Participacion ciudadana), pgta 801. Codigos 1-12 estables. Ponderado por factor07.")
fig.tight_layout()
for e in ("pdf", "png"):
    fig.savefig(FIG / f"fig_participacion_evolution.{e}", dpi=200, bbox_inches="tight")
print("OK -> figures/09_participacion/fig_participacion_evolution.pdf")
