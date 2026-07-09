"""
fig_neet_juvenil_tiempo.py - Jovenes que ni estudian ni trabajan (NEET/ninis) 2004-2025
=========================================================================================
Pregunta: que fraccion de los jovenes 15-24 ni estudia ni trabaja, como evoluciono, y por que
la cifra de las MUJERES es mucho mayor (carga de cuidados/trabajo domestico)?

NEET = joven 15-24 que NO esta en educacion (no matriculado+asistiendo: ~(p306==1 & p307==1),
M03) Y NO esta ocupado (ocu500!=1, M05), por persona via llave-persona. Por sexo (p207),
ponderado por factor07. Un plot. Run: python fig_neet_juvenil_tiempo.py [--rebuild]
"""
from __future__ import annotations
from pathlib import Path
import sys
import numpy as np, pandas as pd
import figstyle as fs
import enaho_codes as ec

ROOT = Path(__file__).resolve().parents[1]; RAW = ROOT / "raw"
FIG = ROOT / "figures" / "05_demografia_salud_educacion"; FIG.mkdir(parents=True, exist_ok=True)
CSV = ROOT / "datasets" / "neet_juvenil_tiempo_2004_2025.csv"
KEY = ["conglome", "vivienda", "hogar", "codperso"]


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


def wshare(mask01, w):
    m = np.asarray(mask01, float); w = np.asarray(w, float)
    ok = np.isfinite(m) & np.isfinite(w)
    return 100 * np.average(m[ok], weights=w[ok]) if ok.any() else np.nan


if CSV.exists() and "--rebuild" not in sys.argv:
    p = pd.read_csv(CSV)
else:
    rows = []
    for y in ec.years():
        m3 = rd(RAW / "educacion" / f"enaho-{y}-03.dta")
        m5 = rd(RAW / "empleo_ingreso" / f"enaho-{y}-05.dta", cols=KEY + ["ocu500"])
        if m3 is None or m5 is None or "p306" not in m3.columns:
            continue
        for c in KEY:
            m3[c] = pd.to_numeric(m3[c], errors="coerce"); m5[c] = pd.to_numeric(m5[c], errors="coerce")
        m3["pk"] = pkey(m3); m5["pk"] = pkey(m5)
        n = lambda d, c: pd.to_numeric(d[c], errors="coerce") if c in d.columns else pd.Series(np.nan, index=d.index)
        g = m3.merge(m5[["pk", "ocu500"]].drop_duplicates("pk"), on="pk", how="left")
        edad = n(g, "p208a"); sx = n(g, "p207"); w = n(g, "factor07")
        mat = n(g, "p306"); asi = n(g, "p307"); oc = n(g, "ocu500")
        estudia = (mat == 1) & (asi == 1)
        trabaja = (oc == 1)
        neet = (~estudia) & (~trabaja)
        you = (edad >= 15) & (edad <= 24)
        rec = {"year": y,
               "Total": wshare(neet[you], w[you]),
               "Hombres": wshare(neet[you & (sx == 1)], w[you & (sx == 1)]),
               "Mujeres": wshare(neet[you & (sx == 2)], w[you & (sx == 2)])}
        rows.append(rec)
        print(f"{y}: Total {rec['Total']:.1f}%  Hombres {rec['Hombres']:.1f}%  Mujeres {rec['Mujeres']:.1f}%")
    p = pd.DataFrame(rows).sort_values("year")
    p.to_csv(CSV, index=False)

fig, ax = fs.fig_ax()
ax.fill_between(p.year, p.Hombres, p.Mujeres, color=fs.GREY, alpha=0.12, zorder=1)
series = [("Mujeres", fs.CRANBERRY), ("Total", fs.GREY), ("Hombres", fs.NAVY)]
labels = []
for col, c in series:
    s = p.dropna(subset=[col])
    ax.plot(s.year, s[col], "-o", color=c, lw=2.3, ms=3.6, mfc="white", mec=c, mew=1.2, zorder=5)
    labels.append((f"{col}  {s[col].iloc[-1]:.0f}%", s[col].iloc[-1], c))
fs.end_labels(ax, labels, x_end=p.year.max(), fs=8.5)
ax.set_xlim(2003.5, 2031); ax.set_xticks(range(2004, 2026, 3)); ax.set_ylim(0, 35)
ax.set_ylabel("Jovenes 15-24 que ni estudian ni trabajan (%)"); ax.set_xlabel("")
fs.statbox(ax, [
    f"Los 'ninis' siguen altos y estables (total ~{p.Total.iloc[-1]:.0f}%; salto COVID 2020).",
    "La cifra de MUJERES es siempre mayor (hasta +11pp), por el",
    "trabajo domestico y de cuidados no remunerado, aunque la",
    "brecha de genero se angosta (de ~11pp a ~6pp).",
], loc="upper right")
fs.source(fig, "Fuente: ENAHO 2004-2025 (INEI), modulos 03 y 05. Jovenes 15-24 no matriculados/asistiendo (p306,p307) y no ocupados (ocu500). Por sexo (p207). Ponderado por factor07.")
fig.tight_layout()
for e in ("pdf", "png"):
    fig.savefig(FIG / f"fig_neet_juvenil_tiempo.{e}", dpi=200, bbox_inches="tight")
print("OK -> fig_neet_juvenil_tiempo.pdf")
