"""
fig_brecha_salarial_grupos.py - La brecha salarial de genero por subgrupos (Peru 2025, M05)
=============================================================================================
Preguntas (Carlos): la brecha salarial mujer/hombre, como varia por (a) NIVEL EDUCATIVO
-- la educacion la cierra o persiste arriba?, (b) TIPO DE EMPLEO -- empleado vs obrero vs
trabajador del hogar, (c) ETNIA -- lengua materna indigena vs no indigena.

Razon ingreso laboral mediano mujer/hombre entre asalariados (ocu500==1, i524a1>0), por
subgrupo, ponderado por fac500a. Intra-grupo intra-anual -> sin deflactar. Educacion y tipo
de empleo desde M05 (p301a, p507); etnia desde M03 (p300a, lengua materna) por llave-persona.
Produce 3 figuras (una por dimension, un plot c/u). Run: python fig_brecha_salarial_grupos.py
"""
from __future__ import annotations
from pathlib import Path
import numpy as np, pandas as pd
import figstyle as fs
import pyreadstat

ROOT = Path(__file__).resolve().parents[1]; RAW = ROOT / "raw"
FIG = ROOT / "figures" / "07_empleo"; DATA = ROOT / "datasets"
YEAR = 2025
KEY = ["conglome", "vivienda", "hogar", "codperso"]


def rd(p, cols=None):
    d, _ = pyreadstat.read_dta(str(p), encoding="latin1", usecols=cols) if cols else \
        pyreadstat.read_dta(str(p), encoding="latin1")
    d.columns = [c.lower() for c in d.columns]
    return d


def wmed(x, w):
    x = np.asarray(x, float); w = np.asarray(w, float)
    ok = np.isfinite(x) & np.isfinite(w) & (x > 0); x, w = x[ok], w[ok]
    if not len(x):
        return np.nan
    o = np.argsort(x); cw = np.cumsum(w[o]) / w[o].sum()
    return x[o][np.searchsorted(cw, 0.5)]


m5 = rd(RAW / "empleo_ingreso" / f"enaho-{YEAR}-05.dta")
m3 = rd(RAW / "educacion" / f"enaho-{YEAR}-03.dta", cols=KEY + ["p300a"])
for d in (m5, m3):
    for k in KEY:
        d[k] = pd.to_numeric(d[k], errors="coerce")
df = m5.merge(m3, on=KEY, how="left")
n = lambda c: pd.to_numeric(df[c], errors="coerce")
w = n("fac500a"); sx = n("p207"); wage = n("i524a1"); oc = n("ocu500")
base = (oc == 1) & (wage > 0)

# --- definiciones de subgrupos por dimension ---
edu = n("p301a")
edu_grp = pd.Series(np.nan, index=df.index)
edu_grp = edu_grp.mask(edu.isin([1, 2, 3, 4, 12]), 0)   # Primaria o menos
edu_grp = edu_grp.mask(edu.isin([5, 6]), 1)             # Secundaria
edu_grp = edu_grp.mask(edu.isin([7, 8]), 2)             # Superior tecnica
edu_grp = edu_grp.mask(edu.isin([9, 10, 11]), 3)        # Universitaria+
EDU_L = {0: "Primaria o menos", 1: "Secundaria", 2: "Superior tecnica", 3: "Universitaria+"}

cat = n("p507")
CAT_L = {3: "Empleado", 4: "Obrero", 6: "Trabajador del hogar"}

leng = n("p300a")
etn = pd.Series(np.nan, index=df.index)
etn = etn.mask(leng.isin([1, 2, 3]), 1)                 # indigena (quechua/aymara/amazonica)
etn = etn.mask(leng.isin([4, 6]), 0)                    # no indigena (castellano/portugues/extranjera)
ETN_L = {0: "No indigena (castellano)", 1: "Indigena (lengua originaria)"}


def gaps(grouper, labels):
    rows = []
    for code, lab in labels.items():
        b = base & (grouper == code)
        mh = wmed(wage[b & (sx == 1)], w[b & (sx == 1)])
        mm = wmed(wage[b & (sx == 2)], w[b & (sx == 2)])
        wf, wt = w[b & (sx == 2)].sum(), w[b].sum()
        rows.append({"grupo": lab, "ratio": mm / mh if mh else np.nan,
                     "share_fem": 100 * wf / wt if wt else np.nan,
                     "n_m": int((b & (sx == 2)).sum()), "n_h": int((b & (sx == 1)).sum())})
    return pd.DataFrame(rows).dropna(subset=["ratio"])


def dumbbell(r, fname, xlabel, note):
    r = r.sort_values("ratio").reset_index(drop=True)
    r.to_csv(DATA / f"{fname}.csv", index=False)
    fig, ax = fs.fig_ax(w=10.5, h=5.6)
    y = np.arange(len(r))
    ax.axvline(1.0, color=fs.GREY, lw=1.3, ls="--", zorder=1)
    for yi, (_, row) in zip(y, r.iterrows()):
        rat = row["ratio"]; c = fs.CRANBERRY if rat < 0.95 else fs.NAVY
        ax.plot([rat, 1.0], [yi, yi], "-", color=fs.GREY, lw=1.4, alpha=0.5, zorder=2)
        ax.plot(rat, yi, "o", color=c, ms=10, mfc="white", mec=c, mew=2.2, zorder=5)
        ax.annotate(f"{rat:.2f}", (rat, yi), textcoords="offset points", xytext=(0, 9),
                    ha="center", fontsize=8.5, color=c)
        ax.annotate(f"{row['share_fem']:.0f}% mujeres  (n_M={row['n_m']})", (1.01, yi),
                    va="center", ha="left", fontsize=7.8, color=fs.GREY)
    ax.set_yticks(y); ax.set_yticklabels(r["grupo"], fontsize=9.5)
    ax.set_xlim(0.55, 1.25); ax.set_xlabel(xlabel); ax.set_ylabel("")
    fs.source(fig, note)
    fig.tight_layout()
    for e in ("pdf", "png"):
        fig.savefig(FIG / f"{fname}.{e}", dpi=200, bbox_inches="tight")
    print(f"OK -> {fname}.pdf")
    print(r[["grupo", "ratio", "share_fem", "n_m", "n_h"]].to_string(index=False))


SRC = "Fuente: ENAHO 2025 (INEI), modulo 05. Asalariados (ocu500=1), ingreso dependiente i524a1. Mediana ponderada por fac500a."
dumbbell(gaps(edu_grp, EDU_L), "fig_brecha_salarial_educacion",
         "Ingreso laboral mediano: mujer / hombre (2025)", SRC + " Nivel educativo (p301a).")
dumbbell(gaps(cat, CAT_L), "fig_brecha_salarial_tipoempleo",
         "Ingreso laboral mediano: mujer / hombre (2025)", SRC + " Categoria ocupacional (p507).")
dumbbell(gaps(etn, ETN_L), "fig_brecha_salarial_etnico",
         "Ingreso laboral mediano: mujer / hombre (2025)", SRC + " Lengua materna (M03 p300a).")
