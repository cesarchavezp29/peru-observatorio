"""
panel_movilidad_ingreso.py
==========================
INCOME MOBILITY from the ENAHO Panel: the quintile transition matrix (where a
household sat in the income distribution in the FIRST wave vs the LAST wave of a
balanced window). A repeated cross-section sees a stable distribution and cannot
tell whether households churn between quintiles or stay put.

Reads datasets/enaho_panel_hogar_long.parquet (build_panel_dataset.py) -- no heavy
file reads. Per-capita income = inghog2d / mieperho. Quintiles are assigned WITHIN
each wave (weighted by w_panel), so nominal income is fine (relative ranks). Uses
the balanced panel (in_balanced==1) and the longitudinal weight w_panel.

Outputs, per release window + a pooled view:
  datasets/panel_movilidad_quintil_<label>.csv     (5x5 row-normalized matrix)
  figures/13_panel/fig_movilidad_quintil_<label>.{pdf,png}   (heatmap)
  console: persistence (diagonal), upward, downward, and bottom/top stickiness.

Run:  py -3.14 panel_movilidad_ingreso.py [--label 2007-2011 | --all]
"""
from __future__ import annotations

import argparse
from pathlib import Path

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from matplotlib.colors import LinearSegmentedColormap

import figstyle as fs

ROOT = Path(__file__).resolve().parents[1]
FIG = ROOT / "figures" / "13_panel"
DATA = ROOT / "datasets"
FIG.mkdir(parents=True, exist_ok=True)
PARQUET = DATA / "enaho_panel_hogar_long.parquet"


def _wquintile(x: np.ndarray, w: np.ndarray) -> np.ndarray:
    """Weighted quintile (1..5) of x. NaN income -> 0 (excluded later)."""
    out = np.zeros(len(x), int)
    ok = np.isfinite(x) & np.isfinite(w) & (w > 0)
    if ok.sum() < 5:
        return out
    xi, wi, idx = x[ok], w[ok], np.where(ok)[0]
    order = np.argsort(xi, kind="mergesort")
    cw = np.cumsum(wi[order]) / wi.sum()
    q = np.searchsorted([0.2, 0.4, 0.6, 0.8], cw, side="right") + 1  # 1..5
    out[idx[order]] = q
    return out


def matrix_for(label: str, df: pd.DataFrame):
    sub = df[(df["window"].astype(str) == df["window"].astype(str)) & (df["in_balanced"] == 1)].copy()
    # restrict to one window matching label years
    y0, y1 = (2000 + int(label[:2]) if False else int(label.split("-")[0]),
              int(label.split("-")[1]) if len(label.split("-")[1]) == 4
              else 2000 + int(label.split("-")[1]))
    sub = sub[(sub["anio"] >= y0) & (sub["anio"] <= y1)]
    sub = sub[sub["release"] == sub["release"].mode().iloc[0]] if len(sub) else sub
    if sub.empty:
        return None
    sub["ypc"] = sub["inghog2d"] / sub["mieperho"].replace(0, np.nan)
    waves = sorted(sub["anio"].unique())
    first, last = waves[0], waves[-1]
    qcols = {}
    for wv in (first, last):
        d = sub[sub["anio"] == wv]
        q = _wquintile(d["ypc"].values, d["w_panel"].fillna(0).values)
        qcols[wv] = pd.Series(q, index=d["hhid"].values)
    a = qcols[first].rename("q0").to_frame().join(qcols[last].rename("q1"), how="inner")
    wlast = sub[sub["anio"] == last].set_index("hhid")["w_panel"]
    a = a.join(wlast.rename("w"), how="left")
    a = a[(a["q0"] >= 1) & (a["q1"] >= 1) & a["w"].notna()]
    M = np.zeros((5, 5))
    for i in range(1, 6):
        for j in range(1, 6):
            M[i - 1, j - 1] = a.loc[(a["q0"] == i) & (a["q1"] == j), "w"].sum()
    row = M.sum(axis=1, keepdims=True)
    P = np.divide(M, row, out=np.zeros_like(M), where=row > 0) * 100
    return P, first, last, int(len(a))


def _fig(label, P, first, last, n):
    fs.use()
    fig, ax = plt.subplots(figsize=(7.6, 6.6))
    cmap = LinearSegmentedColormap.from_list("nv", ["#ffffff", fs.NAVY])
    im = ax.imshow(P, cmap=cmap, vmin=0, vmax=max(60, P.max()))
    for i in range(5):
        for j in range(5):
            v = P[i, j]
            ax.text(j, i, f"{v:.0f}", ha="center", va="center", fontsize=11,
                    color="white" if v > P.max() * 0.55 else fs.INK,
                    fontweight="bold" if i == j else "normal")
    labs = ["Q1\n(mas pobre)", "Q2", "Q3", "Q4", "Q5\n(mas rico)"]
    ax.set_xticks(range(5)); ax.set_xticklabels(labs, fontsize=9)
    ax.set_yticks(range(5)); ax.set_yticklabels([l.replace("\n", " ") for l in labs], fontsize=9)
    ax.set_xlabel(f"Quintil de ingreso en {last}", fontsize=10.5)
    ax.set_ylabel(f"Quintil de ingreso en {first}", fontsize=10.5)
    diag = np.diag(P).mean()
    up = sum(P[i, j] for i in range(5) for j in range(5) if j > i) / 5
    down = sum(P[i, j] for i in range(5) for j in range(5) if j < i) / 5
    ax.set_title(f"Movilidad de ingresos {first}-{last}  (n={n:,} hogares panel)\n"
                 f"permanece {diag:.0f}%  ·  sube {up:.0f}%  ·  baja {down:.0f}%  "
                 f"·  Q1->Q1 {P[0,0]:.0f}%  ·  Q5->Q5 {P[4,4]:.0f}%",
                 fontsize=10.5, color=fs.INK)
    cb = fig.colorbar(im, ax=ax, fraction=0.046, pad=0.03)
    cb.set_label("% de la fila (destino dado el origen)", fontsize=9)
    fs.source(fig, "Fuente: ENAHO Panel (INEI), Sumaria. Ingreso per capita inghog2d/mieperho, "
                   "quintiles ponderados (fac_panel) por ola; panel balanceado.")
    fig.tight_layout()
    for e in ("pdf", "png"):
        fig.savefig(FIG / f"fig_movilidad_quintil_{label}.{e}", dpi=200, bbox_inches="tight")
    plt.close(fig)


def run(label: str, df: pd.DataFrame):
    res = matrix_for(label, df)
    if res is None:
        print(f"[skip] {label}: no data"); return
    P, first, last, n = res
    pd.DataFrame(P, index=[f"q{i}_origen" for i in range(1, 6)],
                 columns=[f"q{j}_destino" for j in range(1, 6)]).round(1).to_csv(
        DATA / f"panel_movilidad_quintil_{label}.csv")
    diag = np.diag(P).mean()
    print(f"[{label}] n={n:,} permanece={diag:.0f}% Q1->Q1={P[0,0]:.0f}% Q5->Q5={P[4,4]:.0f}% "
          f"Q1->Q5={P[0,4]:.0f}% Q5->Q1={P[4,0]:.0f}%")
    _fig(label, P, first, last, n)
    print(f"  wrote fig_movilidad_quintil_{label}")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--label", default="2007-2011")
    ap.add_argument("--all", action="store_true")
    a = ap.parse_args()
    df = pd.read_parquet(PARQUET)
    if a.all:
        labels = []
        for w in sorted(df["window"].dropna().unique()):
            ws = str(int(w)).zfill(4)
            labels.append(f"20{ws[:2]}-20{ws[2:]}")
        for lab in labels:
            run(lab, df)
    else:
        run(a.label, df)


if __name__ == "__main__":
    main()
