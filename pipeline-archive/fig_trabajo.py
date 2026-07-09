"""
fig_trabajo.py - Estructura del empleo 2004-2025 (Modulo 05)
============================================================
Entre los ocupados (ocu500==1), categoria ocupacional p507:
  1 Empleador  2 Independiente  3 Empleado  4 Obrero  5 Trab. familiar no remunerado
  6 Trabajador del hogar. Se agrupan y se grafica el area apilada 2004-2025, mas el
empleo VULNERABLE (independiente + familiar no remunerado, definicion OIT).
Ponderado por fac500a.

Run: python fig_trabajo.py
"""
from __future__ import annotations
from pathlib import Path
import numpy as np, pandas as pd, matplotlib.pyplot as plt
import figstyle as fs
import enaho_codes as ec

ROOT = Path(__file__).resolve().parents[1]; RAW = ROOT / "raw"
FIG = ROOT / "figures" / "07_empleo"; FIG.mkdir(parents=True, exist_ok=True)
DATA = ROOT / "datasets"

CATS = [("Asalariado (empleado+obrero)", [3, 4], fs.PALETTE[0]),
        ("Independiente", [2], fs.PALETTE[1]),
        ("Trab. familiar no remunerado", [5], fs.PALETTE[2]),
        ("Empleador", [1], fs.PALETTE[3]),
        ("Trabajador del hogar", [6], fs.PALETTE[4])]


def read_dta(p):
    try:
        return pd.read_stata(p, convert_categoricals=False)
    except ValueError:
        import pyreadstat; df, _ = pyreadstat.read_dta(str(p), encoding="latin1"); return df


def W(mask, w):
    mask = np.asarray(mask, float); w = np.asarray(w, float); ok = np.isfinite(mask) & np.isfinite(w)
    return 100 * np.average(mask[ok], weights=w[ok]) if ok.any() else np.nan


rows = []
for y in ec.years():
    p = RAW / "empleo_ingreso" / f"enaho-{y}-05.dta"
    if not p.exists():
        continue
    d = read_dta(p); d.columns = [c.lower() for c in d.columns]
    w = pd.to_numeric(d.get("fac500a"), errors="coerce")
    if w.isna().all():
        w = pd.to_numeric(d.get("factor07"), errors="coerce")
    occ = pd.to_numeric(d.get("ocu500"), errors="coerce") == 1
    p507 = pd.to_numeric(d.get("p507"), errors="coerce")
    rec = {"year": y}
    for name, codes, _ in CATS:
        rec[name] = W(p507.isin(codes).where(occ), w.where(occ))
    rec["vulnerable"] = W(p507.isin([2, 5]).where(occ), w.where(occ))
    rows.append(rec)
ev = pd.DataFrame(rows).sort_values("year")
ev.to_csv(DATA / "estructura_empleo_2004_2025.csv", index=False)
print(ev.round(1).to_string(index=False))

SRC = ("Fuente: ENAHO Modulo 05 (INEI) 2004-2025. Categoria ocupacional p507, ocupados (ocu500=1). "
       "Ponderado por fac500a.")


def save(fig, name):
    fs.source(fig, SRC); fig.tight_layout()
    for e in ("pdf", "png"):
        fig.savefig(FIG / f"{name}.{e}", dpi=140, bbox_inches="tight")
    print(f"OK -> figures/07_empleo/{name}.pdf")


# chart 1: estructura ocupacional (area apilada, un eje)
fig, ax = fs.fig_ax(11, 6.4)
names = [c[0] for c in CATS]; colss = [c[2] for c in CATS]
ax.stackplot(ev["year"], [ev[n] for n in names], labels=names, colors=colss, alpha=0.9)
ax.set_xlim(2004, 2025); ax.set_ylim(0, 100); ax.set_xticks(range(2004, 2026, 3))
ax.set_ylabel("% de los ocupados")
ax.set_title("Estructura del empleo por categoria ocupacional, 2004-2025", loc="left")
ax.legend(loc="upper center", bbox_to_anchor=(0.5, -0.09), ncol=3, fontsize=9)
save(fig, "fig_trabajo_estructura")

# chart 2: empleo vulnerable (un eje)
fig, ax = fs.fig_ax(11, 6.0)
ax.plot(ev["year"], ev["vulnerable"], "-o", color=fs.NAVY, lw=2.6, ms=4, mfc="white", mec=fs.NAVY, mew=1.5)
for yy in (ev["year"].iloc[0], ev["year"].iloc[-1]):
    vv = ev.loc[ev["year"] == yy, "vulnerable"].iloc[0]
    fs.halo_label(ax, yy, vv, f"{vv:.0f}%", dy=9, dx=(-16 if yy == ev["year"].iloc[-1] else 2))
ax.set_xlim(2003.5, 2026.5); ax.set_xticks(range(2004, 2026, 3))
ax.set_ylim(ev["vulnerable"].min() - 6, ev["vulnerable"].max() + 6)
ax.set_ylabel("% de los ocupados")
ax.set_title("Empleo vulnerable (independiente + familiar no remunerado, OIT), 2004-2025", loc="left")
save(fig, "fig_trabajo_vulnerable")
