"""
fig_endes_correlaciones.py
==========================
Department-level correlations across ENDES modules (pooled 2016-2024, weighted):
builds datasets/endes_dept_indicadores.csv, then a correlation heatmap + scatters.

  fig_endes_corr_heatmap     heatmap of correlations among department indicators
  fig_endes_corr_desnut_educ desnutricion vs educacion femenina, x departamento
  fig_endes_corr_anemia_des  anemia infantil vs desnutricion cronica, x departamento
"""
from __future__ import annotations
from pathlib import Path
import numpy as np, pandas as pd, pyreadstat
import matplotlib.pyplot as plt
from matplotlib.colors import LinearSegmentedColormap
import figstyle as fs
import endes_codes as ec
import fig_endes_mapas as M   # reuse DEP, find, read, dept_anemia, dept_caseid

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "datasets"
FIG = ROOT / "figures" / "14_endes"; FIG.mkdir(parents=True, exist_ok=True)


def women_dept():
    """Education (15-49) + adolescent motherhood + CEB by department, pooled."""
    mu = pd.read_csv(DATA / "endes_mujeres_2004_2024.csv",
                     usecols=["anio", "edad", "wt", "educ_anios", "hijos_nacidos", "embarazada", "region_dhs"])
    mu = mu[mu.anio.between(2016, 2024)].copy(); mu["dep"] = mu.region_dhs.map(M.DEP)
    out = {}
    for dep, g in mu.groupby("dep"):
        ed = g[g.edad.between(15, 49)].dropna(subset=["educ_anios", "wt"])
        a = g[g.edad.between(15, 19)]; wa = a.wt.fillna(0)
        adol = ((pd.to_numeric(a.hijos_nacidos, errors="coerce") > 0) | (pd.to_numeric(a.embarazada, errors="coerce") == 1)).values
        ceb = pd.to_numeric(g.hijos_nacidos, errors="coerce"); gc = g.dropna(subset=["wt"]); cebv = pd.to_numeric(gc.hijos_nacidos, errors="coerce")
        out[dep] = {"educ": np.average(ed.educ_anios, weights=ed.wt) if len(ed) else np.nan,
                    "adol_madre": 100 * wa[adol].sum() / wa.sum() if wa.sum() else np.nan,
                    "hijos_ceb": np.average(cebv.fillna(0), weights=gc.wt) if gc.wt.sum() else np.nan}
    return pd.DataFrame(out).T


def build_table():
    an = M.dept_anemia()
    des = M.dept_caseid(["hw70"], lambda g: (pd.to_numeric(g.hw70, errors="coerce").lt(-200).astype(float),
                                              pd.to_numeric(g.hw70, errors="coerce").lt(9990)))
    par = M.dept_caseid(["m15"], lambda g: ((pd.to_numeric(g.m15, errors="coerce") >= 21).astype(float),
                                            pd.to_numeric(g.m15, errors="coerce").notna()))
    w = women_dept()
    t = w.copy()
    t["anemia"] = pd.Series(an); t["desnutricion"] = pd.Series(des); t["parto_inst"] = pd.Series(par)
    t = t.reset_index().rename(columns={"index": "dep"})
    t.to_csv(DATA / "endes_dept_indicadores.csv", index=False)
    return t


def heatmap(t):
    cols = ["educ", "hijos_ceb", "adol_madre", "anemia", "desnutricion", "parto_inst"]
    labs = ["Educacion", "Hijos (CEB)", "Mat. adolesc.", "Anemia", "Desnutricion", "Parto inst."]
    C = t[cols].astype(float).corr()
    cmap = LinearSegmentedColormap.from_list("d", [fs.CRANBERRY, "#ffffff", fs.NAVY])
    fs.use(); fig, ax = plt.subplots(figsize=(7.6, 6.6))
    im = ax.imshow(C.values, cmap=cmap, vmin=-1, vmax=1)
    ax.set_xticks(range(len(cols))); ax.set_xticklabels(labs, rotation=35, ha="right", fontsize=9)
    ax.set_yticks(range(len(cols))); ax.set_yticklabels(labs, fontsize=9)
    for i in range(len(cols)):
        for j in range(len(cols)):
            v = C.values[i, j]
            ax.text(j, i, f"{v:.2f}", ha="center", va="center", fontsize=8.5,
                    color="white" if abs(v) > 0.6 else fs.INK)
    fig.colorbar(im, ax=ax, shrink=0.7, label="correlacion")
    fs.source(fig, "Correlaciones entre indicadores departamentales: educacion alta va con menos hijos, menos anemia, "
                   "menos desnutricion y mas parto institucional.\nFuente: ENDES 2016-2024 (INEI), 25 departamentos, ponderado.")
    fig.tight_layout(rect=(0, 0.06, 1, 1))
    for e in ("pdf", "png"):
        try: fig.savefig(FIG / f"fig_endes_corr_heatmap.{e}", dpi=200, bbox_inches="tight")
        except PermissionError: print(f"  [skip .{e}: locked]")
    print("OK -> fig_endes_corr_heatmap")


def scatter(t, xcol, ycol, xlab, ylab, name, takeaway):
    d = t.dropna(subset=[xcol, ycol]); r = np.corrcoef(d[xcol], d[ycol])[0, 1]
    fs.use(); fig, ax = fs.fig_ax()
    ax.scatter(d[xcol], d[ycol], s=46, color=fs.NAVY, alpha=0.85, edgecolor="white", linewidth=0.8, zorder=5)
    b, a = np.polyfit(d[xcol].astype(float), d[ycol].astype(float), 1)
    xs = np.linspace(d[xcol].min(), d[xcol].max(), 50); ax.plot(xs, a + b * xs, color=fs.CRANBERRY, lw=2, zorder=4)
    fs.repel_labels(ax, d[xcol].values, d[ycol].values, [x.title() for x in d.dep], fs=7.5)
    ax.set_xlabel(xlab); ax.set_ylabel(ylab)
    fs.source(fig, f"{takeaway} (correlacion r = {r:.2f}, 25 departamentos).\nFuente: ENDES 2016-2024 (INEI), ponderado.")
    fig.tight_layout(rect=(0, 0.05, 1, 1))
    for e in ("pdf", "png"):
        try: fig.savefig(FIG / f"{name}.{e}", dpi=200, bbox_inches="tight")
        except PermissionError: print(f"  [skip .{e}: locked]")
    print(f"OK -> {name} (r={r:.2f})")


if __name__ == "__main__":
    t = build_table()
    print(t.round(1).to_string(index=False))
    heatmap(t)
    scatter(t, "educ", "desnutricion", "Anios de educacion, mujeres 15-49", "% desnutricion cronica <5",
            "fig_endes_corr_desnut_educ", "A mas educacion femenina, menos desnutricion infantil")
    scatter(t, "desnutricion", "anemia", "% desnutricion cronica <5", "% anemia infantil 6-35m",
            "fig_endes_corr_anemia_des", "Desnutricion y anemia no coinciden del todo: la anemia (altitud) golpea aun donde la talla mejoro")
