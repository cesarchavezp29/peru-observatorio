"""
fig_salud_cronica_discapacidad.py - Enfermedad cronica y discapacidad 2004-2025 (M04)
======================================================================================
Modulo 04 (Salud), nivel persona, peso factor07.
  - ENFERMEDAD CRONICA: p401==1 ('padece de alguna enfermedad o malestar cronico').
    Variable + cuestionario VERIFICADOS identicos 2004-2025 (mismos ejemplos: artritis,
    hipertension, diabetes...). Existe TODOS los anios.
  - DISCAPACIDAD (limitacion permanente): cualquiera de p401h1..p401h6 == 1 (moverse,
    ver, hablar, oir, entender, relacionarse). Bateria recien desde 2014.

LECTURA HONESTA: la cronica sube 18%->43%; el salto 2010-2011 NO es cambio de cuestionario
(identico) sino EFECTO DIAGNOSTICO: con la expansion del aseguramiento (SIS 2008-2009) mas
gente accede a salud y es DIAGNOSTICADA. Mide cronica AUTORREPORTADA/diagnosticada (mas
envejecimiento), no morbilidad objetiva. La discapacidad (~5-6%, limitacion permanente
autorreportada) sube leve por envejecimiento.
Run: python fig_salud_cronica_discapacidad.py
"""
from __future__ import annotations
from pathlib import Path
import numpy as np, pandas as pd
import figstyle as fs
import enaho_codes as ec

ROOT = Path(__file__).resolve().parents[1]; RAW = ROOT / "raw"
FIG = ROOT / "figures" / "05_demografia_salud_educacion"; FIG.mkdir(parents=True, exist_ok=True)
DATA = ROOT / "datasets"


def L(year):
    p = RAW / "salud" / f"enaho-{year}-04.dta"
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
    df = L(y)
    if df is None or "p401" not in df.columns:
        continue
    w = pd.to_numeric(df.get("factor07"), errors="coerce").fillna(0).values
    cron = (pd.to_numeric(df["p401"], errors="coerce") == 1).values
    rec = {"year": y, "cronica": 100 * np.average(cron, weights=w)}
    if "p401h1" in df.columns:
        anyd = np.zeros(len(df), bool)
        for i in range(1, 7):
            c = f"p401h{i}"
            if c in df.columns:
                anyd = anyd | (pd.to_numeric(df[c], errors="coerce") == 1).values
        rec["discapacidad"] = 100 * np.average(anyd, weights=w)
    rows.append(rec)
    print(f"{y}: cronica {rec['cronica']:4.1f}%  discapacidad {rec.get('discapacidad', float('nan')):4.1f}%")

p = pd.DataFrame(rows)
p.to_csv(DATA / "salud_cronica_discapacidad_2004_2025.csv", index=False)

fig, ax = fs.fig_ax()
ax.plot(p.year, p.cronica, "-o", color=fs.NAVY, lw=2.4, ms=4, mfc="white", mec=fs.NAVY, mew=1.4, zorder=5)
dd = p.dropna(subset=["discapacidad"])
ax.plot(dd.year, dd.discapacidad, "-o", color=fs.CRANBERRY, lw=2.4, ms=4, mfc="white", mec=fs.CRANBERRY, mew=1.4, zorder=5)
# marcar la aceleracion por aseguramiento (2008-2011)
ax.axvspan(2008, 2011, color=fs.GOLD, alpha=0.12, zorder=0)
fs.halo_label(ax, 2009.5, 14, "expansion del\naseguramiento\n(efecto diagnostico)", dx=0, dy=0, fs=8.2, color="#9a7d10")
fs.end_labels(ax, [
    (f"Enf. cronica (autorreportada)  {p.cronica.iloc[-1]:.0f}%", p.cronica.iloc[-1], fs.NAVY),
    (f"Discapacidad (2014+)  {dd.discapacidad.iloc[-1]:.0f}%", dd.discapacidad.iloc[-1], fs.CRANBERRY),
], x_end=p.year.iloc[-1], fs=9)
ax.set_xlim(2003.5, 2033)
ax.set_ylim(0, 50)
ax.set_xticks(range(2004, 2026, 2))
ax.set_ylabel("% de la poblacion")
ax.set_xlabel("")
# nota en la banda VACIA entre ambas lineas (centro-derecha)
ax.text(0.97, 0.40, "\n".join([
    "Enf. cronica AUTORREPORTADA (p401, cuestionario",
    "identico todo el periodo). El salto 2010-2011 sigue",
    "a la expansion del SIS: mas acceso -> mas",
    "diagnostico, no necesariamente mas morbilidad.",
    "Discapacidad = limitacion permanente (desde 2014).",
]), transform=ax.transAxes, ha="right", va="center", fontsize=8.8, color=fs.INK,
    bbox=dict(boxstyle="round,pad=0.4", fc="white", ec="#cfd3d8", lw=0.8, alpha=0.95))
fs.source(fig, "Fuente: ENAHO 2004-2025 (INEI), modulo 04. p401 (cronica) y p401h1-6 (discapacidad). Ponderado por factor07.")
fig.tight_layout()
for e in ("pdf", "png"):
    fig.savefig(FIG / f"fig_salud_cronica_discapacidad.{e}", dpi=200, bbox_inches="tight")
print("OK -> fig_salud_cronica_discapacidad.pdf")
