"""
fig_confianza_educacion_tiempo.py - Confianza institucional por nivel educativo 2007-2025 (M85)
=================================================================================================
Pregunta: confian mas (o menos) en las instituciones los mas educados, y como evoluciono ese
gradiente mientras la confianza general se desplomaba?

Indice de confianza del encuestado = % de instituciones que califica Suficiente/Bastante (3-4)
sobre las que responde. CLAVE (anti-artefacto, ver analysis_who_trusts_state): "No sabe" (5)
cuenta como NO confia (esta en el denominador), porque los menos educados dejan mas instituciones
en "No sabe" y excluirlas inflaria espuriamente su confianza. Indice sobre la bateria COMUN
p1_01..p1_16 (presente todos los anios; en 2014 se agregaron p1_17-21 -> se excluyen para que el
set no cambie). Educacion del encuestado = M03 p301a por llave-persona. Peso factor07 (propio del
modulo si existe, si no de Sumaria). Un plot (3 niveles). Run: python fig_confianza_educacion_tiempo.py [--rebuild]
"""
from __future__ import annotations
from pathlib import Path
import sys
import numpy as np, pandas as pd
import figstyle as fs
import enaho_codes as ec

ROOT = Path(__file__).resolve().parents[1]; RAW = ROOT / "raw"
FIG = ROOT / "figures" / "02_confianza"; FIG.mkdir(parents=True, exist_ok=True)
CSV = ROOT / "datasets" / "confianza_educacion_tiempo_2007_2025.csv"
HH = ["conglome", "vivienda", "hogar"]
ITEMS = [f"p1_{i:02d}" for i in range(1, 17)]   # bateria comun 2007-2025
EDU_G = {"Primaria o menos": [1, 2, 3, 4, 12], "Secundaria": [5, 6], "Superior": [7, 8, 9, 10, 11]}


def rd(p, cols=None):
    if not p.exists():
        return None
    try:
        import pyreadstat
        d, _ = pyreadstat.read_dta(str(p), encoding="latin1", usecols=cols) if cols else \
            pyreadstat.read_dta(str(p), encoding="latin1")
    except Exception:
        d = pd.read_stata(p, convert_categoricals=False)
        if cols:
            d = d[[c for c in d.columns if c.lower() in [x.lower() for x in cols]]]
    d.columns = [c.lower() for c in d.columns]
    return d


def pkey(d):
    k = (d["conglome"].astype("Int64").astype(str).str.zfill(6) + d["vivienda"].astype("Int64").astype(str).str.zfill(3)
         + d["hogar"].astype("Int64").astype(str).str.zfill(2) + d["codperso"].astype("Int64").astype(str).str.zfill(2))
    return k


def wshare(mask01, w):
    m = np.asarray(mask01, float); w = np.asarray(w, float)
    ok = np.isfinite(m) & np.isfinite(w)
    return 100 * np.average(m[ok], weights=w[ok]) if ok.any() else np.nan


if CSV.exists() and "--rebuild" not in sys.argv:
    p = pd.read_csv(CSV)
else:
    rows = []
    for y in ec.years():
        gov = rd(RAW / "gobernabilidad" / f"enaho-{y}-85.dta")
        if gov is None or "p1_12" not in gov.columns or "codperso" not in gov.columns:
            continue
        items = [c for c in ITEMS if c in gov.columns]
        for c in HH + ["codperso"]:
            gov[c] = pd.to_numeric(gov[c], errors="coerce")
        Traw = gov[items].apply(pd.to_numeric, errors="coerce")
        answered = Traw.isin([1, 2, 3, 4, 5]).sum(axis=1)
        gov["trust"] = Traw.isin([3, 4]).sum(axis=1) / answered.replace(0, np.nan)   # NoSabe en denom
        gov["pk"] = pkey(gov)
        # educacion del encuestado (M03 p301a)
        m3 = rd(RAW / "educacion" / f"enaho-{y}-03.dta", cols=HH + ["codperso", "p301a"])
        for c in HH + ["codperso"]:
            m3[c] = pd.to_numeric(m3[c], errors="coerce")
        m3["pk"] = pkey(m3); m3["edu"] = pd.to_numeric(m3["p301a"], errors="coerce")
        g = gov.merge(m3[["pk", "edu"]].drop_duplicates("pk"), on="pk", how="left")
        # peso
        su = rd(RAW / "sumaria" / f"enaho-{y}-34.dta", cols=HH + ["factor07"])
        su = su.drop_duplicates(HH).rename(columns={"factor07": "f_su"})
        for c in HH:
            su[c] = pd.to_numeric(su[c], errors="coerce")
        g = g.merge(su[HH + ["f_su"]], on=HH, how="left")
        own = pd.to_numeric(g["factor07"], errors="coerce") if "factor07" in g.columns else pd.Series(np.nan, index=g.index)
        g["w"] = own.where(own.notna() & (own > 0), pd.to_numeric(g["f_su"], errors="coerce"))
        rec = {"year": y}
        for lab, codes in EDU_G.items():
            sub = g[g["edu"].isin(codes) & g["trust"].notna()].copy()
            ww = pd.to_numeric(sub["w"], errors="coerce").fillna(0).values
            rec[lab] = 100 * np.average(sub["trust"].values, weights=ww) if len(sub) and ww.sum() > 0 else np.nan
        rows.append(rec)
        print(f"{y}: Primaria- {rec['Primaria o menos']:.1f}%  Secundaria {rec['Secundaria']:.1f}%  Superior {rec['Superior']:.1f}%")
    p = pd.DataFrame(rows).sort_values("year")
    p.to_csv(CSV, index=False)

fig, ax = fs.fig_ax()
cols = [fs.PALETTE[1], fs.PALETTE[3], fs.PALETTE[0]]
labels = []
for (lab, _), c in zip(EDU_G.items(), cols):
    s = p.dropna(subset=[lab])
    ax.plot(s.year, s[lab], "-o", color=c, lw=2.3, ms=3.6, mfc="white", mec=c, mew=1.2, zorder=5)
    labels.append((f"{lab}  {s[lab].iloc[-1]:.0f}%", s[lab].iloc[-1], c))
fs.end_labels(ax, labels, x_end=p.year.max(), fs=8.5)
ax.set_xlim(2006.5, 2033); ax.set_xticks(range(2007, 2026, 3)); ax.set_ylim(0, 35)
ax.set_ylabel("Indice de confianza institucional (% instituciones que confia)"); ax.set_xlabel("")
fs.statbox(ax, [
    "Gradiente educativo MONOTONO: los mas educados confian",
    "mas en las instituciones (al contar 'No sabe' como no-",
    "confia, no como dato perdido). Pero todos caen: la crisis",
    "politica erosiono la confianza en cada nivel educativo.",
], loc="upper right")
fs.source(fig, "Fuente: ENAHO 2007-2025 (INEI), modulo 85. Indice = % de instituciones (bateria comun p1_01-16) con confianza Suficiente/Bastante; NoSabe=no confia. Educacion M03. Ponderado factor07.")
fig.tight_layout()
for e in ("pdf", "png"):
    fig.savefig(FIG / f"fig_confianza_educacion_tiempo.{e}", dpi=200, bbox_inches="tight")
print("OK -> fig_confianza_educacion_tiempo.pdf")
