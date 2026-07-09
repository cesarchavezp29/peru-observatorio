"""
fig_confianza_grupos_tiempo.py - Confianza institucional por sexo, etnia y area 2007-2025 (M85)
=================================================================================================
Preguntas (Carlos): la confianza en las instituciones difiere por (a) SEXO, (b) ETNIA (lengua
materna indigena vs no), (c) AREA urbano/rural, y como evoluciono cada corte?

Indice de confianza = % de instituciones (bateria comun p1_01-16) calificadas Suficiente/Bastante
(3-4); NoSabe(5)=no confia (anti-artefacto). Sexo del encuestado = M02 p207; etnia = M03 p300a
(lengua materna); area = estrato propio de M85 (1-5 urbano, 6-8 rural). Ponderado por factor07
(propio del modulo si existe, si no de Sumaria). Produce 3 figuras. Bateria 2007-2011 y 2014-2025.
Run: python fig_confianza_grupos_tiempo.py [--rebuild]
"""
from __future__ import annotations
from pathlib import Path
import sys
import numpy as np, pandas as pd
import figstyle as fs
import enaho_codes as ec

ROOT = Path(__file__).resolve().parents[1]; RAW = ROOT / "raw"
FIG = ROOT / "figures" / "02_confianza"; FIG.mkdir(parents=True, exist_ok=True)
CSV = ROOT / "datasets" / "confianza_grupos_tiempo_2007_2025.csv"
HH = ["conglome", "vivienda", "hogar"]
ITEMS = [f"p1_{i:02d}" for i in range(1, 17)]


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
    return (d["conglome"].astype("Int64").astype(str).str.zfill(6) + d["vivienda"].astype("Int64").astype(str).str.zfill(3)
            + d["hogar"].astype("Int64").astype(str).str.zfill(2) + d["codperso"].astype("Int64").astype(str).str.zfill(2))


def wsh(sub, col="trust"):
    ww = pd.to_numeric(sub["w"], errors="coerce").fillna(0).values
    s = sub[col].values
    return 100 * np.average(s, weights=ww) if len(sub) and ww.sum() > 0 else np.nan


if CSV.exists() and "--rebuild" not in sys.argv:
    p = pd.read_csv(CSV)
else:
    rows = []
    for y in ec.years():
        gov = rd(RAW / "gobernabilidad" / f"enaho-{y}-85.dta")
        if gov is None or "p1_12" not in gov.columns or "codperso" not in gov.columns:
            continue
        items = [c for c in ITEMS if c in gov.columns]
        Traw = gov[items].apply(pd.to_numeric, errors="coerce")
        answered = Traw.isin([1, 2, 3, 4, 5]).sum(axis=1)
        gov["trust"] = Traw.isin([3, 4]).sum(axis=1) / answered.replace(0, np.nan)
        for c in HH + ["codperso"]:
            gov[c] = pd.to_numeric(gov[c], errors="coerce")
        gov["pk"] = pkey(gov)
        gov["estr"] = pd.to_numeric(gov.get("estrato"), errors="coerce")
        m2 = rd(RAW / "miembros" / f"enaho-{y}-02.dta", cols=HH + ["codperso", "p207"])
        for c in HH + ["codperso"]:
            m2[c] = pd.to_numeric(m2[c], errors="coerce")
        m2["pk"] = pkey(m2); m2["sexo"] = pd.to_numeric(m2["p207"], errors="coerce")
        m3 = rd(RAW / "educacion" / f"enaho-{y}-03.dta", cols=HH + ["codperso", "p300a"])
        for c in HH + ["codperso"]:
            m3[c] = pd.to_numeric(m3[c], errors="coerce")
        m3["pk"] = pkey(m3); m3["leng"] = pd.to_numeric(m3["p300a"], errors="coerce")
        g = gov.merge(m2[["pk", "sexo"]].drop_duplicates("pk"), on="pk", how="left")
        g = g.merge(m3[["pk", "leng"]].drop_duplicates("pk"), on="pk", how="left")
        su = rd(RAW / "sumaria" / f"enaho-{y}-34.dta", cols=HH + ["factor07"])
        su = su.drop_duplicates(HH).rename(columns={"factor07": "f_su"})
        for c in HH:
            su[c] = pd.to_numeric(su[c], errors="coerce")
        g = g.merge(su[HH + ["f_su"]], on=HH, how="left")
        own = pd.to_numeric(g["factor07"], errors="coerce") if "factor07" in g.columns else pd.Series(np.nan, index=g.index)
        g["w"] = own.where(own.notna() & (own > 0), pd.to_numeric(g["f_su"], errors="coerce"))
        gv = g[g["trust"].notna()]
        rec = {"year": y}
        rec["Hombres"] = wsh(gv[gv["sexo"] == 1]); rec["Mujeres"] = wsh(gv[gv["sexo"] == 2])
        rec["Indigena"] = wsh(gv[gv["leng"].isin([1, 2, 3])]); rec["No indigena"] = wsh(gv[gv["leng"].isin([4, 6])])
        rec["Urbano"] = wsh(gv[gv["estr"].between(1, 5)]); rec["Rural"] = wsh(gv[gv["estr"].between(6, 8)])
        rows.append(rec)
        print(f"{y}: H {rec['Hombres']:.1f} M {rec['Mujeres']:.1f} | Ind {rec['Indigena']:.1f} NoInd {rec['No indigena']:.1f} | Urb {rec['Urbano']:.1f} Rur {rec['Rural']:.1f}")
    p = pd.DataFrame(rows).sort_values("year")
    p.to_csv(CSV, index=False)


def line_fig(pairs, fname, note, story):
    fig, ax = fs.fig_ax()
    labels = []
    for col, lab, c in pairs:
        s = p.dropna(subset=[col])
        ax.plot(s.year, s[col], "-o", color=c, lw=2.3, ms=3.6, mfc="white", mec=c, mew=1.2, zorder=5)
        labels.append((f"{lab}  {s[col].iloc[-1]:.0f}%", s[col].iloc[-1], c))
    fs.end_labels(ax, labels, x_end=p.year.max(), fs=8.5)
    ax.set_xlim(2006.5, 2033); ax.set_xticks(range(2007, 2026, 3)); ax.set_ylim(0, 35)
    ax.set_ylabel("Indice de confianza institucional (% instituciones que confia)"); ax.set_xlabel("")
    fs.statbox(ax, story, loc="upper right")
    fs.source(fig, note)
    fig.tight_layout()
    for e in ("pdf", "png"):
        fig.savefig(FIG / f"{fname}.{e}", dpi=200, bbox_inches="tight")
    print(f"OK -> {fname}.pdf")


SRC = "Fuente: ENAHO 2007-2025 (INEI), modulo 85. Indice = % instituciones (bateria comun p1_01-16) con confianza 3-4; NoSabe=no confia. Ponderado factor07."
line_fig([("Hombres", "Hombres", fs.NAVY), ("Mujeres", "Mujeres", fs.CRANBERRY)],
         "fig_confianza_sexo_tiempo", SRC + " Sexo del encuestado (M02 p207).",
         ["Los hombres confian un poco mas que las mujeres en las",
          "instituciones (~2-3pp), de forma persistente pero modesta.",
          "Ambos caen en paralelo: el desplome es transversal al sexo.",
          "(Pico 2020 COVID; 2012-13 sin bateria.)"])
line_fig([("No indigena", "No indigena", fs.NAVY), ("Indigena", "Lengua indigena", fs.CRANBERRY)],
         "fig_confianza_etnico_tiempo", SRC + " Lengua materna (M03 p300a, indigena=1-3).",
         ["Los hablantes de lengua indigena confian MENOS en el",
          "Estado que el resto, de forma persistente. La brecha",
          "etnica de confianza acompana a la geografica (Sierra).",
          "(Pico 2020 COVID; 2012-13 sin bateria.)"])
line_fig([("Urbano", "Urbano", fs.NAVY), ("Rural", "Rural", fs.CRANBERRY)],
         "fig_confianza_area_tiempo", SRC + " Area (estrato 1-5 urbano, 6-8 rural).",
         ["El campo confia algo MENOS que la ciudad en las",
          "instituciones, de forma persistente (~3-6pp), coherente",
          "con la Sierra rural. La brecha se angosta hacia 2025.",
          "(Pico 2020 COVID; 2012-13 sin bateria.)"])
