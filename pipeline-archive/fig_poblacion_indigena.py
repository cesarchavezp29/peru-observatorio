"""
fig_poblacion_indigena.py - Poblacion indigena por lengua materna 2004-2025
============================================================================
Lengua materna (M03 p300a): 1 Quechua, 2 Aimara, 3 Otra lengua nativa => INDIGENA;
4 Castellano => no indigena. Llave PERSONA, ponderado por factor07.
Cuatro paneles: (a) % indigena en el tiempo (desplazamiento linguistico),
(b) brecha de pobreza indigena vs no indigena, (c) razon de ingreso, (d) % por
departamento 2025.

Run: python fig_poblacion_indigena.py
"""
from __future__ import annotations
from pathlib import Path
import numpy as np, pandas as pd, matplotlib.pyplot as plt
import figstyle as fs
import enaho_codes as ec

ROOT = Path(__file__).resolve().parents[1]; RAW = ROOT / "raw"
FIG = ROOT / "figures" / "10_indigena"; FIG.mkdir(parents=True, exist_ok=True)
DATA = ROOT / "datasets"
DEPTO = {"01": "Amazonas", "02": "Ancash", "03": "Apurimac", "04": "Arequipa", "05": "Ayacucho",
         "06": "Cajamarca", "07": "Callao", "08": "Cusco", "09": "Huancavelica", "10": "Huanuco",
         "11": "Ica", "12": "Junin", "13": "La Libertad", "14": "Lambayeque", "15": "Lima",
         "16": "Loreto", "17": "M.de Dios", "18": "Moquegua", "19": "Pasco", "20": "Piura",
         "21": "Puno", "22": "San Martin", "23": "Tacna", "24": "Tumbes", "25": "Ucayali"}


def read_dta(p):
    try:
        return pd.read_stata(p, convert_categoricals=False)
    except ValueError:
        import pyreadstat; df, _ = pyreadstat.read_dta(str(p), encoding="latin1"); return df


def hh(d):
    return (d["conglome"].astype(str).str.zfill(6) + d["vivienda"].astype(str).str.zfill(3)
            + d["hogar"].astype(str).str.zfill(2))


def wmean(x, w):
    x = np.asarray(x, float); w = np.asarray(w, float); ok = np.isfinite(x) & np.isfinite(w)
    return np.average(x[ok], weights=w[ok]) if ok.any() else np.nan


rows = []
for y in ec.years():
    pe = RAW / "educacion" / f"enaho-{y}-03.dta"
    ps = RAW / "sumaria" / f"enaho-{y}-34.dta"
    if not pe.exists() or not ps.exists():
        continue
    e = read_dta(pe); e.columns = [c.lower() for c in e.columns]
    if "p300a" not in e.columns:
        continue
    e["hh"] = hh(e); e["indig"] = pd.to_numeric(e["p300a"], errors="coerce").isin([1, 2, 3]).astype(float)
    e["lengua_ok"] = pd.to_numeric(e["p300a"], errors="coerce").isin([1, 2, 3, 4])
    s = read_dta(ps); s.columns = [c.lower() for c in s.columns]; s["hh"] = hh(s)
    s["pobre"] = pd.to_numeric(s["pobreza"], errors="coerce").isin([1, 2]).astype(float)
    s["incpc"] = pd.to_numeric(s["inghog2d"], errors="coerce") / pd.to_numeric(s["mieperho"], errors="coerce")
    m = e.merge(s[["hh", "pobre", "incpc"]], on="hh", how="left")   # M03 ya trae factor07
    m = m[m["lengua_ok"] & m["factor07"].notna()]
    ind, non = m[m["indig"] == 1], m[m["indig"] == 0]
    rows.append({"year": y,
                 "share": 100 * wmean(m["indig"], m["factor07"]),
                 "pov_ind": 100 * wmean(ind["pobre"], ind["factor07"]),
                 "pov_non": 100 * wmean(non["pobre"], non["factor07"]),
                 "inc_ind": wmean(ind["incpc"], ind["factor07"]),
                 "inc_non": wmean(non["incpc"], non["factor07"])})
ev = pd.DataFrame(rows).sort_values("year")
ev["inc_ratio"] = ev["inc_ind"] / ev["inc_non"]
ev.to_csv(DATA / "poblacion_indigena_2004_2025.csv", index=False)
print(ev[["year", "share", "pov_ind", "pov_non", "inc_ratio"]].round(2).to_string(index=False))

# panel (d): % indigena por depto 2025
e = read_dta(RAW / "educacion" / "enaho-2025-03.dta"); e.columns = [c.lower() for c in e.columns]
e["indig"] = pd.to_numeric(e["p300a"], errors="coerce").isin([1, 2, 3]).astype(float)
e["ok"] = pd.to_numeric(e["p300a"], errors="coerce").isin([1, 2, 3, 4])
e["dep"] = e["ubigeo"].astype(str).str.zfill(6).str[:2]
e = e[e["ok"]]
dep = e.groupby("dep").apply(lambda g: 100 * wmean(g["indig"], g["factor07"]), include_groups=False)
dep = dep.rename(index=DEPTO).sort_values()

SRC = ("Fuente: ENAHO Modulos 03 (lengua materna p300a) y 34 (Sumaria), INEI. Indigena = quechua/aimara/"
       "otra lengua nativa. Persona, ponderado por factor07.")


def save(fig, name):
    fs.source(fig, SRC); fig.tight_layout()
    for e_ in ("pdf", "png"):
        fig.savefig(FIG / f"{name}.{e_}", dpi=140, bbox_inches="tight")
    print(f"OK -> figures/10_indigena/{name}.pdf")


# chart 1: % indigena en el tiempo
fig, a = fs.fig_ax()
a.plot(ev["year"], ev["share"], "-o", color=fs.NAVY, lw=2.4, ms=4, mfc="white", mec=fs.NAVY, mew=1.4)
fs.halo_label(a, ev["year"].iloc[0], ev["share"].iloc[0], f"{ev['share'].iloc[0]:.0f}%", dy=8)
fs.halo_label(a, ev["year"].iloc[-1], ev["share"].iloc[-1], f"{ev['share'].iloc[-1]:.0f}%", dy=8, dx=-20)
a.set_ylim(0, max(ev["share"]) + 4); a.set_xticks(range(2004, 2026, 3))
a.set_ylabel("% de la poblacion")
a.set_title("La poblacion con lengua materna indigena cae, 2004-2025", loc="left")
save(fig, "fig_indigena_share")

# chart 2: brecha de pobreza
fig, b = fs.fig_ax()
b.plot(ev["year"], ev["pov_ind"], "-o", color=fs.NAVY, lw=2.4, ms=3.5, mfc="white", mec=fs.NAVY, mew=1.3, label="Indigena")
b.plot(ev["year"], ev["pov_non"], "-o", color=fs.CRANBERRY, lw=2.4, ms=3.5, mfc="white", mec=fs.CRANBERRY, mew=1.3, label="No indigena")
b.fill_between(ev["year"], ev["pov_ind"], ev["pov_non"], color=fs.NAVY, alpha=0.06)
b.set_xticks(range(2004, 2026, 3)); b.set_ylabel("% en pobreza monetaria"); b.legend(loc="upper right")
b.set_title("Los indigenas, siempre mas pobres: brecha de pobreza 2004-2025", loc="left")
save(fig, "fig_indigena_pobreza")

# chart 3: razon de ingreso
fig, c = fs.fig_ax()
c.plot(ev["year"], 100 * ev["inc_ratio"], "-o", color=fs.NAVY, lw=2.4, ms=4, mfc="white", mec=fs.NAVY, mew=1.4)
c.axhline(100, color=fs.GREY, ls="--", lw=1)
fs.halo_label(c, ev["year"].iloc[0], 100 * ev["inc_ratio"].iloc[0], f"{100*ev['inc_ratio'].iloc[0]:.0f}%", dy=9)
fs.halo_label(c, ev["year"].iloc[-1], 100 * ev["inc_ratio"].iloc[-1], f"{100*ev['inc_ratio'].iloc[-1]:.0f}%", dy=9, dx=-20)
c.set_xticks(range(2004, 2026, 3)); c.set_ylim(45, 108)
c.set_ylabel("Ingreso indigena / no indigena (%)")
c.set_title("La brecha de ingreso se cierra lento: indigena vs no indigena", loc="left")
save(fig, "fig_indigena_ingreso")

# chart 4: por departamento 2025
fig, d4 = fs.fig_ax(10.5, 7)
d4.barh(range(len(dep)), dep.values, color=fs.NAVY, edgecolor="white")
for i, v in enumerate(dep.values):
    d4.text(v + 0.6, i, f"{v:.0f}", va="center", fontsize=8)
d4.set_yticks(range(len(dep))); d4.set_yticklabels(dep.index, fontsize=8.5)
d4.set_xlabel("% con lengua materna indigena (2025)"); d4.grid(axis="y", alpha=0)
d4.set_title("Donde se concentra la poblacion indigena - ENAHO 2025", loc="left")
save(fig, "fig_indigena_departamento")
