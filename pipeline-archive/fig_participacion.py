"""
fig_participacion.py - El tejido asociativo del Peru (Modulo 84)
================================================================
Modulo 84 (Participacion Ciudadana, Capitulo 800), llave HOGAR. Bateria p801_1..20:
"Usted o algun miembro de su hogar pertenece a ...". % de hogares que pertenece a
cada tipo de organizacion, ponderado por factor07 (el modulo lo trae). Tambien la
brecha pobre / no pobre (union 1:1 a Sumaria por hogar).

Run: python fig_participacion.py
"""
from __future__ import annotations
from pathlib import Path
import numpy as np, pandas as pd, matplotlib.pyplot as plt
import figstyle as fs

ROOT = Path(__file__).resolve().parents[1]; RAW = ROOT / "raw"
FIG = ROOT / "figures" / "09_participacion"; FIG.mkdir(parents=True, exist_ok=True)
DATA = ROOT / "datasets"
YEAR = 2025

ORG = {1: "Club/asoc. deportiva", 2: "Partido politico", 3: "Club cultural",
       4: "Junta vecinal", 5: "Ronda campesina", 6: "Asoc. de regantes",
       7: "Asoc. profesional", 8: "Sindicato", 9: "Club de madres",
       10: "APAFA (padres de familia)", 11: "Vaso de leche", 12: "Comedor popular",
       13: "Comite local de salud", 16: "Comunidad campesina", 17: "Asoc. agropecuaria"}


def hh(d):
    return (d["conglome"].astype(str).str.zfill(6) + d["vivienda"].astype(str).str.zfill(3)
            + d["hogar"].astype(str).str.zfill(2))


def wshare(m, w):
    m = np.asarray(m, float); w = np.asarray(w, float); ok = np.isfinite(m) & np.isfinite(w)
    return 100 * np.average(m[ok], weights=w[ok]) if ok.any() else np.nan


d = pd.read_stata(RAW / "participacion_ciudadana" / f"enaho-{YEAR}-84.dta", convert_categoricals=False)
d.columns = [c.lower() for c in d.columns]; d["hh"] = hh(d)
su = pd.read_stata(RAW / "sumaria" / f"enaho-{YEAR}-34.dta", convert_categoricals=False)
su.columns = [c.lower() for c in su.columns]; su["hh"] = hh(su)
su["pobre"] = pd.to_numeric(su["pobreza"], errors="coerce").isin([1, 2]).astype(float)
d = d.merge(su[["hh", "pobre"]], on="hh", how="left")
w = pd.to_numeric(d["factor07"], errors="coerce")

rows = []
for code, name in ORG.items():
    v = pd.to_numeric(d.get(f"p801_{code}"), errors="coerce")
    yes = (v == code).astype(float)   # se marca con el CODIGO de la organizacion, no con 1
    rows.append({"org": name,
                 "all": wshare(yes, w),
                 "pobre": wshare(yes[d["pobre"] == 1], w[d["pobre"] == 1]),
                 "nopobre": wshare(yes[d["pobre"] == 0], w[d["pobre"] == 0])})
g = pd.DataFrame(rows).sort_values("all")
# % que no pertenece a nada
nada = wshare((pd.to_numeric(d.get("p801_19"), errors="coerce") == 19).astype(float), w)
g.to_csv(DATA / "participacion_2025.csv", index=False)
print(g.round(1).to_string(index=False))
print(f"\nNo pertenece a ninguna organizacion: {nada:.1f}%")

fs.use()
fig, ax = plt.subplots(figsize=(11, 7))
ys = np.arange(len(g))
ax.barh(ys, g["all"].values, color=fs.NAVY, edgecolor="white", zorder=3)
# puntos pobre vs no pobre
ax.scatter(g["pobre"], ys, color=fs.CRANBERRY, s=26, zorder=5, label="Hogares pobres")
ax.scatter(g["nopobre"], ys, color=fs.GOLD, s=26, zorder=5, label="Hogares no pobres")
for i, v in enumerate(g["all"].values):
    ax.text(v + 0.3, i, f"{v:.0f}%", va="center", fontsize=8.5, color=fs.NAVY)
ax.set_yticks(ys); ax.set_yticklabels(g["org"], fontsize=9.5)
ax.set_xlabel("% de hogares que pertenece (barra = total; puntos = por condicion de pobreza)")
ax.set_xlim(0, max(g["all"].max(), g["pobre"].max()) * 1.15)
ax.set_title("El tejido asociativo del Peru: a que pertenecen los hogares - ENAHO 2025",
             loc="left", fontsize=12.5)
ax.grid(axis="y", alpha=0); ax.legend(loc="lower right")
fs.halo_label(ax, ax.get_xlim()[1] * 0.5, 0.3,
              f"{nada:.0f}% de los hogares no pertenece a ninguna organizacion", fs=9, color=fs.GREY)
fs.source(fig, "Fuente: ENAHO Modulo 84 (Participacion Ciudadana) x Sumaria (INEI) 2025. Llave hogar; "
          "ponderado por factor07.")
fig.tight_layout()
for e in ("pdf", "png"):
    fig.savefig(FIG / f"fig_participacion.{e}", dpi=140, bbox_inches="tight")
print("OK -> figures/09_participacion/fig_participacion.pdf")
