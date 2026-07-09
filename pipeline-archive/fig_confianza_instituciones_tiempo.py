"""
fig_confianza_instituciones_tiempo.py - Colapso de la confianza institucional 2007-2025 (M85)
================================================================================================
Pregunta: en dos decadas de crisis politica recurrente, como cambio la confianza de los peruanos
en sus instituciones clave (Congreso, partidos, Poder Judicial, policia) frente al ancla social
(Iglesia)?

% que confia (responde Suficiente=3 o Bastante=4, sobre los que responden 1-4; NoSabe=5->NaN) en
cada institucion, por anio, ponderado por factor07. Modulo 85 (Gobernabilidad, enaho01b): 1
encuestado por hogar, SIN peso propio -> se trae factor07 de Sumaria por llave-hogar. Bateria de
confianza disponible 2007-2011 y 2014-2025 (ausente 2004-06 y 2012-13). Mapeo p1_NN->institucion
VERIFICADO estable todos los anios (p1_06 policia, p1_09 PJ, p1_12 Congreso, p1_13 partidos,
p1_16 Iglesia). Un plot. Run: python fig_confianza_instituciones_tiempo.py [--rebuild]
"""
from __future__ import annotations
from pathlib import Path
import sys
import numpy as np, pandas as pd
import figstyle as fs
import enaho_codes as ec

ROOT = Path(__file__).resolve().parents[1]; RAW = ROOT / "raw"
FIG = ROOT / "figures" / "02_confianza"; FIG.mkdir(parents=True, exist_ok=True)
CSV = ROOT / "datasets" / "confianza_instituciones_tiempo_2007_2025.csv"
KEY = ["conglome", "vivienda", "hogar"]
INST = {"p1_06": "Policia Nacional", "p1_09": "Poder Judicial", "p1_12": "Congreso",
        "p1_13": "Partidos politicos", "p1_16": "Iglesia catolica"}


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
        if gov is None or "p1_12" not in gov.columns:
            continue
        su = rd(RAW / "sumaria" / f"enaho-{y}-34.dta", cols=KEY + ["factor07"])
        if su is None:
            continue
        for k in KEY:
            gov[k] = pd.to_numeric(gov[k], errors="coerce")
            su[k] = pd.to_numeric(su[k], errors="coerce")
        su = su.drop_duplicates(KEY).rename(columns={"factor07": "factor07_su"})
        g = gov.merge(su[KEY + ["factor07_su"]], on=KEY, how="left")
        own = pd.to_numeric(g["factor07"], errors="coerce") if "factor07" in g.columns else pd.Series(np.nan, index=g.index)
        frm = pd.to_numeric(g["factor07_su"], errors="coerce")
        w = own.where(own.notna() & (own > 0), frm)   # peso propio del modulo si existe, si no el de Sumaria
        rec = {"year": y, "cob_peso": float(w.notna().mean())}
        for var, name in INST.items():
            if var not in g.columns:
                rec[name] = np.nan; continue
            v = pd.to_numeric(g[var], errors="coerce").where(lambda s: s.isin([1, 2, 3, 4]))
            rec[name] = wshare((v >= 3).where(v.notna()), w)
        rows.append(rec)
        print(f"{y}: Congreso {rec['Congreso']:.1f}%  Partidos {rec['Partidos politicos']:.1f}%  "
              f"PJ {rec['Poder Judicial']:.1f}%  Policia {rec['Policia Nacional']:.1f}%  "
              f"Iglesia {rec['Iglesia catolica']:.1f}%  (peso {100*rec['cob_peso']:.0f}%)")
    p = pd.DataFrame(rows).sort_values("year")
    p.to_csv(CSV, index=False)

fig, ax = fs.fig_ax()
order = ["Iglesia catolica", "Policia Nacional", "Poder Judicial", "Congreso", "Partidos politicos"]
cols = [fs.PALETTE[i] for i in (4, 2, 3, 0, 1)]
labels = []
for name, c in zip(order, cols):
    s = p.dropna(subset=[name])
    ax.plot(s.year, s[name], "-o", color=c, lw=2.3, ms=3.6, mfc="white", mec=c, mew=1.2, zorder=5)
    labels.append((f"{name}  {s[name].iloc[-1]:.0f}%", s[name].iloc[-1], c))
fs.end_labels(ax, labels, x_end=p.year.max(), fs=8.2)
ax.set_xlim(2006.5, 2034); ax.set_xticks(range(2007, 2026, 3)); ax.set_ylim(0, 60)
ax.set_ylabel("% que confia (Suficiente o Bastante)"); ax.set_xlabel("")
fs.statbox(ax, [
    "La confianza en las instituciones politicas es minima y",
    "siguio cayendo: el Congreso y los partidos viven debajo",
    "del 10%. Solo la Iglesia conserva confianza mayoritaria-ish,",
    "y aun ella se erosiona. (2012-13 sin bateria de confianza.)",
], loc="upper right")
fs.source(fig, "Fuente: ENAHO 2007-2025 (INEI), modulo 85 (Gobernabilidad). % que confia (3-4 en escala 1-4; NoSabe excluido), ponderado por factor07 de Sumaria.")
fig.tight_layout()
for e in ("pdf", "png"):
    fig.savefig(FIG / f"fig_confianza_instituciones_tiempo.{e}", dpi=200, bbox_inches="tight")
print("OK -> fig_confianza_instituciones_tiempo.pdf")
