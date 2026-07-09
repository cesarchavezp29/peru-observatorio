"""
fig_jefatura_femenina_pobreza_tiempo.py - Los hogares con jefa NO son mas pobres (M02 x M34)
================================================================================================
MULTI-MODULO (M02 jefatura del hogar x M34 Sumaria pobreza): tasa de pobreza de los hogares
segun el sexo del jefe/jefa, 2004-2025, y la subida de la jefatura femenina.

Pregunta (hipotesis de "feminizacion de la pobreza"): los hogares encabezados por mujeres son
mas pobres? En Peru la respuesta honesta es NO.

CONSTRUCCION:
  - M02 (miembros): jefe = miembro con p203==1; su sexo p207 (2=mujer) -> hogar con jefa.
    Edad del jefe p208a (para el recuadro). Llave-hogar conglome+vivienda+hogar.
  - M34 (Sumaria): pobreza in {1,2}, factor07 (peso del hogar). Merge por llave-hogar.
CODIGOS: p203 codigo 1 = "jefe/jefa" ESTABLE todos los anios (el [DRIFT] que marca verify_codes
es solo el wording del codigo 2 esposo(a)/companero(a), no afecta la jefatura); p207 (1=hombre/
2=mujer) estandar. Ponderado por factor07 (hogar). CAVEAT (honesto): la jefatura es en parte
DEFINICIONAL (a quien se nombra "jefe") y la pobreza es per capita -> los hogares con jefa suelen
ser mas chicos (viudas, parejas con varon migrante que envia remesas) y eso, no un mayor ingreso,
explica buena parte de la menor pobreza. CSV jefatura_pobreza_tiempo.csv (lo usa tambien
fig_jefatura_femenina_share_tiempo.py). Un plot. Run: python ... [--rebuild]
"""
from __future__ import annotations
from pathlib import Path
import sys
import numpy as np, pandas as pd
import figstyle as fs

ROOT = Path(__file__).resolve().parents[1]; RAW = ROOT / "raw"
FIG = ROOT / "figures" / "01_ingreso_pobreza"; FIG.mkdir(parents=True, exist_ok=True)
CSV = ROOT / "datasets" / "jefatura_pobreza_tiempo.csv"
HK = ["conglome", "vivienda", "hogar"]
YEARS = list(range(2004, 2026))


def num(s):
    return pd.to_numeric(s, errors="coerce")


def rd(folder, mod, year, cols):
    import pyreadstat
    fp = RAW / folder / f"enaho-{year}-{mod}.dta"
    if not fp.exists():
        return None
    have = pyreadstat.read_dta(str(fp), metadataonly=True)[1].column_names
    cl = {c.lower(): c for c in have}
    d, _ = pyreadstat.read_dta(str(fp), encoding="latin1", usecols=[cl[c] for c in cols if c in cl])
    d.columns = [c.lower() for c in d.columns]
    return d


def key(d, keys):
    return d[keys].apply(lambda col: num(col).astype("Int64").astype(str)).agg("-".join, axis=1)


def pr(poor, mask, w):
    return 100 * w[poor & mask].sum() / w[mask].sum() if w[mask].sum() > 0 else np.nan


if CSV.exists() and "--rebuild" not in sys.argv:
    p = pd.read_csv(CSV)
else:
    rows = []
    for y in YEARS:
        m2 = rd("miembros", "02", y, HK + ["p203", "p207", "p208a"])
        su = rd("sumaria", "34", y, HK + ["pobreza", "factor07"])
        if m2 is None or su is None:
            continue
        m2["hk"] = key(m2, HK); su["hk"] = key(su, HK)
        head = m2[num(m2["p203"]) == 1].drop_duplicates("hk")
        head["fem"] = (num(head["p207"]) == 2)
        d = su.merge(head[["hk", "fem"]], on="hk", how="left")
        w = num(d["factor07"]).fillna(0); fem = d["fem"].fillna(False)
        poor = num(d["pobreza"]).isin([1, 2])
        rec = {"year": y, "share_fem": 100 * w[fem].sum() / w.sum(),
               "pov_fem": pr(poor, fem, w), "pov_male": pr(poor, ~fem, w)}
        rows.append(rec)
        print(f"{y}: %jefa {rec['share_fem']:4.1f} | pobreza jefa {rec['pov_fem']:4.1f} jefe {rec['pov_male']:4.1f}")
    p = pd.DataFrame(rows).sort_values("year")
    p.to_csv(CSV, index=False)

fs.use()
fig, ax = fs.fig_ax()
lines = [("Hogar con jefe hombre", "pov_male", fs.NAVY), ("Hogar con jefa mujer", "pov_fem", fs.CRANBERRY)]
labels = []
for name, col, c in lines:
    s = p.dropna(subset=[col])
    ax.plot(s.year, s[col], "-o", color=c, lw=2.4, ms=4.0, mfc="white", mec=c, mew=1.2, zorder=5)
    labels.append((f"{name}  {s[col].iloc[-1]:.0f}%", s[col].iloc[-1], c))
fs.end_labels(ax, labels, x_end=p.year.max(), gap=3.0, fs=8.4)
ax.axvspan(2019.6, 2020.4, color=fs.GREY, alpha=0.10, zorder=0)
ax.set_xlim(2003.4, 2029); ax.set_xticks(range(2004, 2026, 3)); ax.set_ylim(0, 60)
ax.set_ylabel("% de hogares en pobreza monetaria"); ax.set_xlabel("")
sh0 = p.dropna(subset=["share_fem"]).iloc[0]; sh1 = p.dropna(subset=["share_fem"]).iloc[-1]
fs.statbox(ax, [
    "La 'feminizacion de la pobreza' no aplica a Peru: los",
    "hogares con jefa son SIEMPRE algo menos pobres que",
    "los de jefe hombre, aun cuando la jefatura femenina",
    f"subio de {sh0['share_fem']:.0f}% a {sh1['share_fem']:.0f}% de los hogares. Suelen ser",
    "mas chicos (viudez, remesas), no de mayor ingreso.",
], loc="upper right")
fs.source(fig, "Fuente: ENAHO 2004-2025 (INEI), modulo 02 (Miembros: jefe p203==1, sexo p207) x modulo 34 (Sumaria, pobreza). "
               "% de hogares en pobreza monetaria por sexo del jefe, ponderado por factor07.")
fig.tight_layout()
for e in ("pdf", "png"):
    fig.savefig(FIG / f"fig_jefatura_femenina_pobreza_tiempo.{e}", dpi=200, bbox_inches="tight")
print("OK -> fig_jefatura_femenina_pobreza_tiempo.pdf")
