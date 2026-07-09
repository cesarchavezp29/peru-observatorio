"""
fig_vivienda_evolution.py - Evolucion de las condiciones de la vivienda 2004-2025
==================================================================================
Modulo 01 (Caracteristicas de la Vivienda y el Hogar), llave HOGAR. Una fila por
hogar y anio; ponderado por factor07. Acceso de los hogares a servicios basicos.

Solo se grafican indicadores VALIDADOS contra cifras publicadas por INEI (ENAHO 2024):
  - Agua de red publica DENTRO de la vivienda (p110==1):  mio 82.5%  vs INEI 83.5%  OK
  - Alumbrado electrico cualquier fuente (p1121==1):       mio 96.1%  vs INEI 92.6% (red publica)
  - Telefono celular (p1142==1):                           mio 95.1%  vs INEI ~95%   OK

INTERNET (p1144) se EXCLUYE del grafico: el dato crudo post-2023 (~90%) NO valida
contra la cifra oficial INEI 2024 (58.4% de hogares con internet) porque desde 2023
la pregunta paso a incluir conexion movil (p114b1-b3). Documentado en
docs/NOTES_validacion_externa.md. El internet FIJO se mantiene en ~30%.

Run: python fig_vivienda_evolution.py
"""
from __future__ import annotations
from pathlib import Path
import numpy as np, pandas as pd, matplotlib.pyplot as plt
import figstyle as fs
import enaho_codes as ec

ROOT = Path(__file__).resolve().parents[1]
RAW = ROOT / "raw"
FIG = ROOT / "figures" / "06_vivienda"; FIG.mkdir(parents=True, exist_ok=True)
DATA = ROOT / "datasets"

# solo indicadores validados externamente (ver cabecera)
IND = {"p110":  ("Agua de red publica (dentro de la vivienda)", fs.NAVY),
       "p1121": ("Alumbrado electrico (cualquier fuente)",      fs.GOLD),
       "p1142": ("Telefono celular",                            fs.CRANBERRY)}
# cifras INEI oficiales 2024 para validar (etiqueta en el grafico)
INEI2024 = {"p110": 83.5, "p1121": 92.6, "p1142": 95.0}


def read_dta(path):
    """pandas, con fallback a pyreadstat para formatos Stata viejos (v110, 2005-2009)."""
    try:
        return pd.read_stata(path, convert_categoricals=False)
    except ValueError:
        import pyreadstat
        df, _ = pyreadstat.read_dta(str(path))
        return df


def wshare(mask, w):
    mask = np.asarray(mask, float); w = np.asarray(w, float)
    ok = np.isfinite(mask) & np.isfinite(w)
    return 100 * np.average(mask[ok], weights=w[ok]) if ok.any() else np.nan


rows = []
for y in ec.years():
    p = RAW / "vivienda_hogar" / f"enaho-{y}-01.dta"
    if not p.exists():
        continue
    d = read_dta(p); d.columns = [c.lower() for c in d.columns]
    if "factor07" not in d.columns:
        d["factor07"] = 1.0
    rec = {"year": y}
    for v in IND:
        if v in d.columns:
            x = pd.to_numeric(d[v], errors="coerce")
            rec[v] = wshare((x == 1).where(x.notna()), d["factor07"])
        else:
            rec[v] = np.nan
    rows.append(rec)
ev = pd.DataFrame(rows).sort_values("year")
ev.to_csv(DATA / "vivienda_servicios_2004_2025.csv", index=False)
print(ev.round(1).to_string(index=False))
print("\nValidacion vs INEI 2024 (mio / INEI):")
for v in IND:
    m = ev.loc[ev["year"] == 2024, v]
    if len(m):
        print(f"  {IND[v][0][:32]:32s} {m.iloc[0]:5.1f} / {INEI2024[v]:5.1f}")

fs.use()
fig, ax = plt.subplots(figsize=(11, 6.4))
for v, (lab, col) in IND.items():
    ax.plot(ev["year"], ev[v], "-o", color=col, lw=2.2, ms=4, mfc="white",
            mec=col, mew=1.4, label=lab, zorder=4)
    fs.halo_label(ax, ev["year"].iloc[-1], ev[v].iloc[-1], f"{ev[v].iloc[-1]:.0f}%",
                  dx=6, dy=-3, color=col)
ax.set_ylim(40, 102); ax.set_xlim(2003.5, 2026.5)
ax.set_ylabel("% de hogares con acceso"); ax.set_xlabel("")
ax.set_xticks(range(2004, 2026, 2))
ax.set_title("La vivienda peruana se moderniza: servicios basicos del hogar, 2004-2025",
             loc="left", fontsize=13)
ax.legend(loc="lower right")
fs.source(fig, "Fuente: ENAHO Modulo 01 (INEI), 2004-2025. Llave hogar; ponderado por factor07.")
fig.tight_layout()
for e in ("pdf", "png"):
    fig.savefig(FIG / f"fig_vivienda_evolution.{e}", dpi=140, bbox_inches="tight")
print("\nOK -> figures/06_vivienda/fig_vivienda_evolution.pdf")
