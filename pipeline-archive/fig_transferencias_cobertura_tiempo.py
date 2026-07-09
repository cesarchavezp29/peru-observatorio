"""
fig_transferencias_cobertura_tiempo.py - Cobertura de las transferencias monetarias insignia
del Peru 2013-2025 (M37 Programas Sociales no alimentarios, capitulo 700A)
================================================================================================
Pregunta: como evoluciono el alcance de los dos programas-bandera de transferencia directa -
JUNTOS (transferencia condicionada a hogares pobres con ninos) y PENSION 65 (pension no
contributiva a adultos mayores en pobreza)- en los hogares peruanos?

% de HOGARES que reporta haber sido beneficiario, ponderado por factor07, denominador = marco
de hogares de Sumaria (todos los hogares), por anio.

TRAMPA DE CODIGOS (verificada leyendo el CED-01-700A + value-labels del subarchivo 700b de CADA
anio): el modulo tiene DOS formatos y los codigos se renumeraron:
  - 2013-2020, 2025: formato ANCHO, dummies p710_NN (NN = codigo del programa ese anio).
    JUNTOS = p710_03 en 2013, p710_04 en 2014-2025 (Wawa Wasi se partio en diurno+acompanamiento
    en 2014 y corrio a Juntos un lugar). PENSION 65 = p710_05 todos los anios.
  - 2021-2024: formato LARGO, una fila por (persona, programa) recibido, programa en p712 con
    value-labels (4=Juntos, 5=Pension 65). NO trae filas de "no recibio" -> el denominador DEBE
    venir de Sumaria (todos los hogares), no del propio modulo.
Por eso se ancla SIEMPRE en Sumaria (LEFT join, hogar sin marca = no beneficiario). Mapeo de
codigos confirmado empiricamente en raw/_dicc/m37/*700b.dta. Un plot. Run: python ... [--rebuild]
"""
from __future__ import annotations
from pathlib import Path
import sys
import numpy as np, pandas as pd
import figstyle as fs

ROOT = Path(__file__).resolve().parents[1]; RAW = ROOT / "raw"
FIG = ROOT / "figures" / "04_programas_sociales"; FIG.mkdir(parents=True, exist_ok=True)
CSV = ROOT / "datasets" / "transferencias_cobertura_2013_2025.csv"
KEY = ["conglome", "vivienda", "hogar"]
YEARS = list(range(2013, 2026))
# codigo del programa por anio (verificado en los 700b)
JUNTOS = {y: (3 if y == 2013 else 4) for y in YEARS}
PENSION65 = {y: 5 for y in YEARS}


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


def hhid(d):
    return (pd.to_numeric(d["conglome"], errors="coerce").astype("Int64").astype(str).str.zfill(6)
            + pd.to_numeric(d["vivienda"], errors="coerce").astype("Int64").astype(str).str.zfill(3)
            + pd.to_numeric(d["hogar"], errors="coerce").astype("Int64").astype(str).str.zfill(2))


def wshare(mask01, w):
    m = np.asarray(mask01, float); w = np.asarray(w, float)
    ok = np.isfinite(m) & np.isfinite(w)
    return 100 * np.average(m[ok], weights=w[ok]) if ok.any() else np.nan


if CSV.exists() and "--rebuild" not in sys.argv:
    p = pd.read_csv(CSV)
else:
    rows = []
    for y in YEARS:
        m = rd(RAW / "programas_sociales" / f"enaho-{y}-37.dta")
        su = rd(RAW / "sumaria" / f"enaho-{y}-34.dta", cols=KEY + ["factor07"])
        if m is None or su is None:
            print(f"{y}: falta archivo"); continue
        m["hhid"] = hhid(m)
        su["hhid"] = hhid(su)
        su = su.drop_duplicates("hhid")
        jcol = f"p710_{JUNTOS[y]:02d}"; pcol = f"p710_{PENSION65[y]:02d}"
        if jcol in m.columns:  # formato ANCHO
            fmt = "ancho"
            flags = m[["hhid"]].copy()
            flags["juntos"] = (pd.to_numeric(m[jcol], errors="coerce") == 1).astype(float)
            flags["pension65"] = (pd.to_numeric(m[pcol], errors="coerce") == 1).astype(float)
            flags = flags.groupby("hhid", as_index=False).max()
        else:                  # formato LARGO (2021-2024)
            fmt = "largo"
            p712 = pd.to_numeric(m["p712"], errors="coerce")
            tmp = pd.DataFrame({"hhid": m["hhid"],
                                "juntos": (p712 == JUNTOS[y]).astype(float),
                                "pension65": (p712 == PENSION65[y]).astype(float)})
            flags = tmp.groupby("hhid", as_index=False).max()
        d = su.merge(flags, on="hhid", how="left")
        d["juntos"] = d["juntos"].fillna(0.0); d["pension65"] = d["pension65"].fillna(0.0)
        w = pd.to_numeric(d["factor07"], errors="coerce")
        rec = {"year": y, "fmt": fmt, "n_hh": len(d),
               "Juntos": wshare(d["juntos"], w), "Pension 65": wshare(d["pension65"], w)}
        rows.append(rec)
        print(f"{y} [{fmt:5s}] Juntos {rec['Juntos']:5.2f}%  Pension 65 {rec['Pension 65']:5.2f}%  (n_hh {len(d):,})")
    p = pd.DataFrame(rows).sort_values("year")
    p.to_csv(CSV, index=False)

fs.use()
fig, ax = fs.fig_ax()
order = [("Juntos", fs.CRANBERRY), ("Pension 65", fs.NAVY)]
labels = []
for name, c in order:
    s = p.dropna(subset=[name])
    ax.plot(s.year, s[name], "-o", color=c, lw=2.4, ms=4.2, mfc="white", mec=c, mew=1.3, zorder=5)
    labels.append((f"{name}  {s[name].iloc[-1]:.1f}%", s[name].iloc[-1], c))
fs.end_labels(ax, labels, x_end=p.year.max(), fs=9)
ax.axvspan(2019.6, 2020.4, color=fs.GREY, alpha=0.10, zorder=0)
ax.set_xlim(2012.6, 2027.4); ax.set_xticks(range(2013, 2026, 2))
ax.set_ylim(0, max(12, np.nanmax(p[["Juntos", "Pension 65"]].values) * 1.15))
ax.set_ylabel("% de hogares beneficiarios"); ax.set_xlabel("")
fs.statbox(ax, [
    "Pension 65 (pension no contributiva a adultos mayores",
    "pobres) subio de 3.8% a 9.5% de hogares y casi alcanza",
    "a Juntos. Juntos (transferencia condicionada a hogares",
    "con ninos) se estanco cerca de 10-11% y baja despacio.",
    "Cobertura = recibio en los ultimos 3 anos (pgta. 710).",
], loc="lower right")
fs.source(fig, "Fuente: ENAHO 2013-2025 (INEI), modulo 37 (Programas Sociales no alimentarios, 700A). "
               "% de hogares que recibio en los ultimos 3 anos, ponderado por factor07; denominador = todos los hogares (Sumaria).")
fig.tight_layout()
for e in ("pdf", "png"):
    fig.savefig(FIG / f"fig_transferencias_cobertura_tiempo.{e}", dpi=200, bbox_inches="tight")
print("OK -> fig_transferencias_cobertura_tiempo.pdf")
