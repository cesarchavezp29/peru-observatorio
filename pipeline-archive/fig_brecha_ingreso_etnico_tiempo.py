"""
fig_brecha_ingreso_etnico_tiempo.py - La brecha etnica de ingresos es de educacion, no de paga
================================================================================================
MULTI-MODULO (M05 ingreso laboral x M03 lengua materna): ingreso de los trabajadores de lengua
indigena como % del de los castellano-hablantes, crudo y DENTRO de la educacion superior,
2007-2025.

Pregunta: los trabajadores indigenas ganan menos; cuanto de esa brecha es educacion/oportunidad
y cuanto persiste a igual nivel educativo (senal de discriminacion de paga)?

CONSTRUCCION (anclado en M05, asalariados 25-59):
  - M05 (empleo): i524a1 ingreso laboral anual (dependiente, deflactado), p507 categoria
    (asalariado = 3 empleado / 4 obrero), p301a educacion, p208a edad, fac500a peso, ocu500.
  - M03 (educacion): p300a LENGUA MATERNA. INDIGENA = 1 quechua / 2 aimara / 3 otra lengua
    nativa; NO INDIGENA = 4 castellano. Merge por llave-persona.
  - RATIO = mediana ponderada del ingreso indigena / mediana no-indigena (intra-anual, el
    deflactor se cancela). RAW vs DENTRO de educacion superior (p301a 7-11).
CODIGOS VERIFICADOS: p300a indigena 1-3 estable (el code 5 ingles cae tras 2013 y 8/9 cambian
en 2018, pero 1-3 no se tocan); p507 (3 empleado/4 obrero), ocu500, p301a estables. CAVEAT:
mediana cruda sin control de horas/experiencia/region/ocupacion; "dentro de superior" es control
grueso; los indigenas que llegan a superior pueden estar positivamente seleccionados. Un plot.
Run: python fig_brecha_ingreso_etnico_tiempo.py [--rebuild]
"""
from __future__ import annotations
from pathlib import Path
import sys
import numpy as np, pandas as pd
import figstyle as fs

ROOT = Path(__file__).resolve().parents[1]; RAW = ROOT / "raw"
FIG = ROOT / "figures" / "10_indigena"; FIG.mkdir(parents=True, exist_ok=True)
CSV = ROOT / "datasets" / "brecha_ingreso_etnico_tiempo.csv"
HK = ["conglome", "vivienda", "hogar"]; PK = HK + ["codperso"]
YEARS = list(range(2007, 2026))


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


def wmed(v, w):
    v = np.asarray(v, float); w = np.asarray(w, float)
    ok = np.isfinite(v) & np.isfinite(w) & (w > 0)
    v, w = v[ok], w[ok]
    if w.sum() == 0:
        return np.nan
    o = np.argsort(v); v, w = v[o], w[o]
    return float(np.interp(0.5 * w.sum(), np.cumsum(w), v))


if CSV.exists() and "--rebuild" not in sys.argv:
    p = pd.read_csv(CSV)
else:
    rows = []
    for y in YEARS:
        m5 = rd("empleo_ingreso", "05", y, PK + ["ocu500", "p208a", "p301a", "i524a1", "fac500a", "p507"])
        m3 = rd("educacion", "03", y, PK + ["p300a"])
        if m5 is None or m3 is None:
            continue
        m5["pk"] = key(m5, PK); m3["pk"] = key(m3, PK)
        d = m5.merge(m3.drop_duplicates("pk")[["pk", "p300a"]], on="pk", how="left")
        a = num(d["p208a"]); inc = num(d["i524a1"]); w = num(d["fac500a"]).fillna(0); lg = num(d["p300a"])
        sal = num(d["p507"]).isin([3, 4]); base = (num(d["ocu500"]) == 1) & a.between(25, 59) & sal & inc.gt(0)
        ind = lg.isin([1, 2, 3]); nei = lg.eq(4); sup = num(d["p301a"]).between(7, 11)

        def ratio(extra=None):
            m = base if extra is None else base & extra
            mi = wmed(inc[m & ind], w[m & ind]); mn = wmed(inc[m & nei], w[m & nei])
            return 100 * mi / mn if mn else np.nan
        rec = {"year": y, "raw": ratio(), "within_sup": ratio(sup), "n_ind": int((base & ind).sum())}
        rows.append(rec)
        print(f"{y}: raw {rec['raw']:5.1f}%  within-superior {rec['within_sup']:5.1f}%  (n_ind {rec['n_ind']:,})")
    p = pd.DataFrame(rows).sort_values("year")
    p.to_csv(CSV, index=False)

fs.use()
fig, ax = fs.fig_ax()
ax.axhline(100, color=fs.GREY, lw=1.0, ls=(0, (4, 3)), alpha=0.8, zorder=1)
lines = [("Dentro de educacion superior", "within_sup", fs.NAVY), ("Crudo (todos los asalariados)", "raw", fs.CRANBERRY)]
labels = []
for name, col, c in lines:
    s = p.dropna(subset=[col])
    ax.plot(s.year, s[col], "-o", color=c, lw=2.4, ms=4.0, mfc="white", mec=c, mew=1.2, zorder=5)
    labels.append((f"{name}  {s[col].iloc[-1]:.0f}%", s[col].iloc[-1], c))
fs.end_labels(ax, labels, x_end=p.year.max(), gap=5, fs=8.3)
ax.axvspan(2019.6, 2020.4, color=fs.GREY, alpha=0.10, zorder=0)
fs.halo_label(ax, 2012, 100, "Paridad (=100%)", dy=1.6, fs=8, color=fs.GREY)
ax.set_xlim(2006.6, 2030); ax.set_xticks(range(2007, 2026, 3)); ax.set_ylim(60, 110)
ax.set_ylabel("Ingreso indigena como % del no indigena"); ax.set_xlabel("")
fs.statbox(ax, [
    "La brecha de ingresos por lengua indigena es sobre todo",
    "de EDUCACION, no de paga: cruda subio de 68% a ~92%",
    "del ingreso no indigena, pero ENTRE universitarios ya",
    "habia paridad (~100%) todo el periodo. Cierra la brecha",
    "educativa y casi desaparece. M05 ingreso x M03 lengua.",
], loc="lower right")
fs.source(fig, "Fuente: ENAHO 2007-2025 (INEI), modulo 05 (ingreso laboral i524a1, asalariados 25-59) x modulo 03 (lengua "
               "materna p300a). Mediana ponderada por fac500a; ratio intra-anual. Indigena = quechua/aimara/otra nativa.")
fig.tight_layout()
for e in ("pdf", "png"):
    fig.savefig(FIG / f"fig_brecha_ingreso_etnico_tiempo.{e}", dpi=200, bbox_inches="tight")
print("OK -> fig_brecha_ingreso_etnico_tiempo.pdf")
