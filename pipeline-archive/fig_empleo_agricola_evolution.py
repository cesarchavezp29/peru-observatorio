"""
fig_empleo_agricola_evolution.py - Empleo agricola 2004-2025 (transformacion estructural)
==========================================================================================
Modulo 05 (Empleo e Ingreso), llave PERSONA. Entre los OCUPADOS (ocu500==1), la
participacion de la agricultura/ganaderia/silvicultura/pesca en el empleo, definida
por la rama de actividad CIIU rev4 (p506r4, seccion A = codigos 111-322). Ponderado
por el factor de empleo propio del modulo, fac500a (no requiere Sumaria).

Validado 2025: 23.3% (INEI publica ~24-25% de PEA ocupada en agropecuario).

Run: python fig_empleo_agricola_evolution.py
"""
from __future__ import annotations
from pathlib import Path
import numpy as np, pandas as pd, matplotlib.pyplot as plt
import figstyle as fs
import enaho_codes as ec

ROOT = Path(__file__).resolve().parents[1]
RAW = ROOT / "raw"
FIG = ROOT / "figures" / "07_empleo"; FIG.mkdir(parents=True, exist_ok=True)
DATA = ROOT / "datasets"

AGRI_LO, AGRI_HI = 111, 322   # CIIU rev4 seccion A: agricultura, silvicultura y pesca


def wshare(mask, w):
    mask = np.asarray(mask, float); w = np.asarray(w, float)
    ok = np.isfinite(mask) & np.isfinite(w)
    return 100 * np.average(mask[ok], weights=w[ok]) if ok.any() else np.nan


rows = []
for y in ec.years():
    p = RAW / "empleo_ingreso" / f"enaho-{y}-05.dta"
    if not p.exists():
        continue
    d = pd.read_stata(p, convert_categoricals=False); d.columns = [c.lower() for c in d.columns]
    if "ocu500" not in d.columns or "p506r4" not in d.columns:
        continue
    w = pd.to_numeric(d["fac500a"], errors="coerce") if "fac500a" in d.columns else pd.Series(1.0, index=d.index)
    occ = pd.to_numeric(d["ocu500"], errors="coerce")
    br = pd.to_numeric(d["p506r4"], errors="coerce")
    emp = occ == 1
    agri = (br >= AGRI_LO) & (br <= AGRI_HI)
    rec = {"year": y,
           "ag_share": wshare(agri[emp], w[emp]),
           "n_emp": int(emp.sum())}
    # heterogeneidad por sexo del trabajador (p207 en el propio M05)
    if "p207" in d.columns:
        sex = pd.to_numeric(d["p207"], errors="coerce")
        rec["ag_men"] = wshare(agri[emp & (sex == 1)], w[emp & (sex == 1)])
        rec["ag_women"] = wshare(agri[emp & (sex == 2)], w[emp & (sex == 2)])
    rows.append(rec)
ev = pd.DataFrame(rows).sort_values("year")
ev.to_csv(DATA / "empleo_agricola_2004_2025.csv", index=False)
print(ev.round(1).to_string(index=False))

fs.use()
fig, ax = plt.subplots(figsize=(11, 6.2))
ax.plot(ev["year"], ev["ag_share"], "-o", color=fs.NAVY, lw=2.6, ms=5, mfc="white",
        mec=fs.NAVY, mew=1.6, label="Total ocupados", zorder=5)
if "ag_women" in ev.columns:
    ax.plot(ev["year"], ev["ag_men"], "--", color=fs.GOLD, lw=1.8, label="Hombres", zorder=4)
    ax.plot(ev["year"], ev["ag_women"], ":", color=fs.CRANBERRY, lw=1.8, label="Mujeres", zorder=4)
y0, y1 = ev["ag_share"].iloc[0], ev["ag_share"].iloc[-1]
fs.halo_label(ax, ev["year"].iloc[0], y0, f"{y0:.0f}%", dx=-4, dy=8, color=fs.NAVY)
fs.halo_label(ax, ev["year"].iloc[-1], y1, f"{y1:.0f}%", dx=4, dy=8, color=fs.NAVY)
ax.set_ylim(0, max(ev[[c for c in ['ag_share','ag_men','ag_women'] if c in ev]].max()) + 6)
ax.set_xlim(2003.5, 2026.5); ax.set_xticks(range(2004, 2026, 2))
ax.set_ylabel("% de los ocupados en agricultura")
ax.set_title("Transformacion estructural: cae el empleo agricola, 2004-2025",
             loc="left", fontsize=13)
fs.statbox(ax, ["Rama CIIU rev4 seccion A (agric./silv./pesca)",
                "entre ocupados (ocu500=1), ponderado fac500a",
                f"caida {y0-y1:.0f} pp en 21 anios"], loc="upper right")
ax.legend(loc="lower left")
# pico 2020: retorno al campo durante el confinamiento COVID (migracion inversa), no es ruido
y2020 = ev.loc[ev["year"] == 2020, "ag_share"]
if len(y2020):
    fs.halo_label(ax, 2020, float(y2020.iloc[0]), "Pico 2020: retorno al\ncampo en el confinamiento",
                  dx=-86, dy=6, fs=8, color=fs.GREY)
fs.source(fig, "Fuente: ENAHO Modulo 05 (INEI), 2004-2025. Rama de actividad principal CIIU rev4 (p506r4), "
          "entre ocupados (ocu500=1), ponderado por fac500a.")
fig.tight_layout()
for e in ("pdf", "png"):
    fig.savefig(FIG / f"fig_empleo_agricola_evolution.{e}", dpi=140, bbox_inches="tight")
print("\nOK -> figures/07_empleo/fig_empleo_agricola_evolution.pdf")
