"""
fig_busqueda_atencion_salud_tiempo.py - Cobertura de seguro no es acceso a la atencion
================================================================================================
Pregunta: el SIS expandio el aseguramiento de 15% a 66% (2004-2025). Subio en paralelo el uso
efectivo de los servicios de salud? Entre quienes se enferman, que fraccion consulta a un
profesional, y cambia eso segun el seguro?

Modulo 04 (Salud). Universo = personas que reportan un problema de salud en las ultimas 4 semanas
(p4021 sintoma / p4022 enfermedad / p4023 recaida cronica / p4024 accidente). BUSCO ATENCION
FORMAL = acudio a un establecimiento o profesional (p4031-p4039 = puestos/centros/hospitales
MINSA/EsSalud/FFAA/privados + p40311 = profesional en domicilio). EXCLUYE farmacia/botica (p40310),
curandero (p40312), otro (p40313) y "no busco" (p40314). Codigos 402/403 VERIFICADOS estables
2007 vs 2025 por el CED-01A-400. Seguro: SIS = p4195==1; EsSalud = p4191==1; sin seguro = ninguno
de p4191-p4198. Tasa ponderada por factor07. Serie 2007-2025 (402/403 presentes desde 2007).
Un plot. Run: python fig_busqueda_atencion_salud_tiempo.py [--rebuild]
"""
from __future__ import annotations
from pathlib import Path
import sys
import numpy as np, pandas as pd
import figstyle as fs

ROOT = Path(__file__).resolve().parents[1]; RAW = ROOT / "raw"
FIG = ROOT / "figures" / "05_demografia_salud_educacion"; FIG.mkdir(parents=True, exist_ok=True)
CSV = ROOT / "datasets" / "atencion_salud_tiempo.csv"
SRC = RAW / "salud"
YEARS = list(range(2007, 2026))
FORMAL = [f"p403{i}" for i in range(1, 10)] + ["p40311"]
SEG = [f"p419{i}" for i in range(1, 9)]
REASONS = {"no_dinero": "p4091", "no_grave": "p4095", "remedios": "p4096",
           "no_seguro": "p4097", "autoreceto": "p4098"}
USE = ["p4021", "p4022", "p4023", "p4024", "p40310", "p40314", "factor07"] + FORMAL + SEG + list(REASONS.values())


def num(s):
    return pd.to_numeric(s, errors="coerce")


def rd(p, cols):
    try:
        import pyreadstat
        have = pyreadstat.read_dta(str(p), metadataonly=True)[1].column_names
        cl = {c.lower(): c for c in have}
        d, _ = pyreadstat.read_dta(str(p), encoding="latin1", usecols=[cl[c] for c in cols if c in cl])
    except Exception:
        d = pd.read_stata(p, convert_categoricals=False)
        d = d[[c for c in d.columns if c.lower() in cols]]
    d.columns = [c.lower() for c in d.columns]
    return d


def wshare(mask, base, w):
    m = (mask & base); b = base
    wm = float(w[m].sum()); wb = float(w[b].sum())
    return 100 * wm / wb if wb > 0 else np.nan


if CSV.exists() and "--rebuild" not in sys.argv:
    p = pd.read_csv(CSV)
else:
    rows = []
    for y in YEARS:
        f = SRC / f"enaho-{y}-04.dta"
        if not f.exists():
            continue
        df = rd(f, USE)
        w = num(df["factor07"]).fillna(0)
        prob = pd.Series(False, index=df.index)
        for c in ["p4021", "p4022", "p4023", "p4024"]:
            prob = prob | (num(df[c]) == 1)
        formal = pd.Series(False, index=df.index)
        for c in FORMAL:
            if c in df.columns:
                formal = formal | (num(df[c]) == 1)
        sis = (num(df.get("p4195")) == 1) if "p4195" in df.columns else pd.Series(False, index=df.index)
        essalud = (num(df.get("p4191")) == 1) if "p4191" in df.columns else pd.Series(False, index=df.index)
        anyseg = pd.Series(False, index=df.index)
        for c in SEG:
            if c in df.columns:
                anyseg = anyseg | (num(df[c]) == 1)
        sinseg = ~anyseg
        nonformal = prob & ~formal
        rec = {"year": y, "n_prob": int(prob.sum()),
               "seek_all": wshare(formal, prob, w),
               "seek_sis": wshare(formal, prob & sis, w),
               "seek_essalud": wshare(formal, prob & essalud, w),
               "seek_sinseg": wshare(formal, prob & sinseg, w)}
        for name, var in REASONS.items():
            rec[f"r_{name}"] = wshare((num(df.get(var)) == 1) if var in df.columns else pd.Series(False, index=df.index),
                                      nonformal, w)
        rows.append(rec)
        print(f"{y}: seek_all {rec['seek_all']:4.1f}  SIS {rec['seek_sis']:4.1f}  EsSalud {rec['seek_essalud']:4.1f}  "
              f"sinSeg {rec['seek_sinseg']:4.1f} | no-dinero {rec['r_no_dinero']:4.1f}  no-grave {rec['r_no_grave']:4.1f}  (n {rec['n_prob']:,})")
    p = pd.DataFrame(rows).sort_values("year")
    p.to_csv(CSV, index=False)

fs.use()
fig, ax = fs.fig_ax()
lines = [("Con EsSalud", "seek_essalud", fs.GOLD), ("Con SIS", "seek_sis", fs.CRANBERRY),
         ("Sin seguro", "seek_sinseg", fs.NAVY)]
labels = []
for name, col, c in lines:
    s = p.dropna(subset=[col])
    ax.plot(s.year, s[col], "-o", color=c, lw=2.3, ms=3.8, mfc="white", mec=c, mew=1.2, zorder=5)
    labels.append((f"{name}  {s[col].iloc[-1]:.0f}%", s[col].iloc[-1], c))
fs.end_labels(ax, labels, x_end=p.year.max(), fs=8.5)
ax.axvspan(2019.6, 2020.4, color=fs.GREY, alpha=0.10, zorder=0)
ax.set_xlim(2006.6, 2029); ax.set_xticks(range(2007, 2026, 3)); ax.set_ylim(0, 55)
ax.set_ylabel("% que consulta a un profesional, entre quienes se enfermaron"); ax.set_xlabel("")
fs.statbox(ax, [
    "El SIS llevo el aseguramiento de 15% a 66%, pero la",
    "consulta profesional entre los enfermos sigue cerca de",
    "un tercio y no subio: ni los asegurados consultan mas.",
    "El seguro removio el costo (ver razones), no las demas",
    "barreras (distancia, espera, 'no era grave'). 2020 = COVID.",
], loc="lower left")
fs.source(fig, "Fuente: ENAHO 2007-2025 (INEI), modulo 04 (Salud). % que acude a un establecimiento o profesional "
               "entre quienes reportan problema de salud en 4 semanas (excluye farmacia y curandero), ponderado por factor07.")
fig.tight_layout()
for e in ("pdf", "png"):
    fig.savefig(FIG / f"fig_busqueda_atencion_salud_tiempo.{e}", dpi=200, bbox_inches="tight")
print("OK -> fig_busqueda_atencion_salud_tiempo.pdf")
