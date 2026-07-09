"""
fig_brecha_tiempo_grupos.py - Brecha salarial de genero en el tiempo: etnia y educacion superior
=================================================================================================
Preguntas (Carlos): como evoluciono 2004-2025 la brecha salarial mujer/hombre (a) entre
trabajadores de lengua INDIGENA vs NO indigena, y (b) entre los de educacion UNIVERSITARIA?

Razon ingreso laboral mediano M/H entre asalariados (ocu500==1, i524a1>0) por subgrupo y anio,
ponderado por fac500a. Intra-grupo intra-anual -> sin deflactar. Etnia = lengua materna p300a
(M03, merge llave-persona; indigena=1-3 estable, castellano=4); educacion = p301a (M05 propio;
universitaria+=9-11, primaria o menos=1-4,12; ambos rangos estables todo el periodo).
Produce 2 figuras. Run: python fig_brecha_tiempo_grupos.py [--rebuild]
"""
from __future__ import annotations
from pathlib import Path
import sys
import numpy as np, pandas as pd
import figstyle as fs
import enaho_codes as ec

ROOT = Path(__file__).resolve().parents[1]; RAW = ROOT / "raw"
FIG = ROOT / "figures" / "07_empleo"; DATA = ROOT / "datasets"
CSV = DATA / "brecha_salarial_grupos_tiempo_2004_2025.csv"
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


def wmed(x, w):
    x = np.asarray(x, float); w = np.asarray(w, float)
    ok = np.isfinite(x) & np.isfinite(w) & (x > 0); x, w = x[ok], w[ok]
    if not len(x):
        return np.nan
    o = np.argsort(x); cw = np.cumsum(w[o]) / w[o].sum()
    return x[o][np.searchsorted(cw, 0.5)]


def ratio(wage, sx, w, mask):
    mh = wmed(wage[mask & (sx == 1)], w[mask & (sx == 1)])
    mm = wmed(wage[mask & (sx == 2)], w[mask & (sx == 2)])
    nm = int((mask & (sx == 2)).sum()); nh = int((mask & (sx == 1)).sum())
    return (mm / mh if mh else np.nan), nm, nh


def ratio_ci(wage, sx, w, mask, B=400, seed=7):
    """IC95 por bootstrap del cociente de medianas (remuestreo de filas dentro del grupo)."""
    idx = np.where(np.asarray(mask))[0]
    if len(idx) < 30:
        return np.nan, np.nan
    wv = np.asarray(wage, float)[idx]; sv = np.asarray(sx, float)[idx]; wt = np.asarray(w, float)[idx]
    rng = np.random.default_rng(seed); out = []
    for _ in range(B):
        s = rng.integers(0, len(idx), len(idx))
        mh = wmed(wv[s][sv[s] == 1], wt[s][sv[s] == 1]); mm = wmed(wv[s][sv[s] == 2], wt[s][sv[s] == 2])
        if mh and np.isfinite(mh):
            out.append(mm / mh)
    if not out:
        return np.nan, np.nan
    return float(np.percentile(out, 2.5)), float(np.percentile(out, 97.5))


if CSV.exists() and "--rebuild" not in sys.argv:
    p = pd.read_csv(CSV)
else:
    rows = []
    for y in ec.years():
        m5 = rd(RAW / "empleo_ingreso" / f"enaho-{y}-05.dta")
        if m5 is None or "i524a1" not in m5.columns:
            continue
        m3 = rd(RAW / "educacion" / f"enaho-{y}-03.dta", cols=KEY + ["p300a"])
        for k in KEY:
            m5[k] = pd.to_numeric(m5[k], errors="coerce")
        if m3 is not None and "p300a" in m3.columns:
            for k in KEY:
                m3[k] = pd.to_numeric(m3[k], errors="coerce")
            df = m5.merge(m3[KEY + ["p300a"]], on=KEY, how="left")
        else:
            df = m5.assign(p300a=np.nan)
        n = lambda c: pd.to_numeric(df[c], errors="coerce") if c in df.columns else pd.Series(np.nan, index=df.index)
        w = n("fac500a"); sx = n("p207"); wage = n("i524a1"); oc = n("ocu500")
        edu = n("p301a"); leng = n("p300a")
        base = (oc == 1) & (wage > 0)
        rec = {"year": y}
        MASKS = {"univ": base & edu.isin([9, 10, 11]), "prim": base & edu.isin([1, 2, 3, 4, 12]),
                 "indigena": base & leng.isin([1, 2, 3]), "no_indigena": base & leng.isin([4, 6])}
        for key, msk in MASKS.items():
            r, nm, _ = ratio(wage, sx, w, msk)
            lo, hi = ratio_ci(wage, sx, w, msk)
            rec[key] = r; rec[f"n_{key}_m"] = nm; rec[f"{key}_lo"] = lo; rec[f"{key}_hi"] = hi
        rows.append(rec)
        print(f"{y}: univ {rec['univ']:.2f}[{rec['univ_lo']:.2f}-{rec['univ_hi']:.2f}] (n={rec['n_univ_m']}) | "
              f"indig {rec['indigena']:.2f}[{rec['indigena_lo']:.2f}-{rec['indigena_hi']:.2f}] (n={rec['n_indigena_m']})")
    p = pd.DataFrame(rows).sort_values("year")
    p.to_csv(CSV, index=False)


def line_fig(cols_labels_colors, fname, ymin, note, story):
    fig, ax = fs.fig_ax()
    ax.axhline(1.0, color=fs.GREY, lw=1.2, ls="--", zorder=1)
    ax.annotate("paridad", (p.year.min() + 0.2, 1.0), fontsize=9, color=fs.GREY, style="italic", va="bottom")
    labels = []
    for col, lab, c in cols_labels_colors:
        s = p.dropna(subset=[col])
        if f"{col}_lo" in s.columns:
            ax.fill_between(s.year, s[f"{col}_lo"], s[f"{col}_hi"], color=c, alpha=0.13, lw=0, zorder=2)
        ax.plot(s.year, s[col], "-o", color=c, lw=2.4, ms=4, mfc="white", mec=c, mew=1.4, zorder=5)
        labels.append((f"{lab}  {s[col].iloc[-1]:.2f}", s[col].iloc[-1], c))
    fs.end_labels(ax, labels, x_end=p.year.max(), fs=8.5)
    ax.set_xlim(2003.5, 2032); ax.set_xticks(range(2004, 2026, 3)); ax.set_ylim(ymin, 1.02)
    ax.set_ylabel("Ingreso laboral mediano: mujer / hombre"); ax.set_xlabel("")
    fs.statbox(ax, story, loc="lower right")
    fs.source(fig, note)
    fig.tight_layout()
    for e in ("pdf", "png"):
        fig.savefig(FIG / f"{fname}.{e}", dpi=200, bbox_inches="tight")
    print(f"OK -> {fname}.pdf")


SRC = "Fuente: ENAHO 2004-2025 (INEI), modulo 05. Asalariados (ocu500=1), ingreso dependiente i524a1, mediana ponderada por fac500a. Bandas = IC95 bootstrap (400 reps)."
line_fig([("indigena", "Lengua indigena", fs.CRANBERRY), ("no_indigena", "No indigena", fs.NAVY)],
         "fig_brecha_salarial_etnico_tiempo", 0.30,
         SRC + " Lengua materna M03 p300a (indigena=1-3).",
         ["La brecha entre trabajadores de lengua indigena se redujo",
          "(0.45 en 2004 a 0.67 en 2025) pero sigue mas ancha que la",
          "no indigena (~0.81). Las bandas IC95 son anchas (muestra",
          "indigena chica): el vaiven anual es ruido, la brecha es real."])
line_fig([("univ", "Universitaria+", fs.NAVY), ("prim", "Primaria o menos", fs.CRANBERRY)],
         "fig_brecha_salarial_universitaria_tiempo", 0.40,
         SRC + " Nivel educativo M05 p301a (universitaria+=9-11).",
         ["Ni la educacion universitaria cierra la brecha:",
          "las profesionales siguen ganando menos que sus pares,",
          "con mejora lenta a lo largo de 20 anios."])
