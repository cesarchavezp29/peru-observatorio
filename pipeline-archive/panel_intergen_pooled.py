"""
panel_intergen_pooled.py
========================
POOLED intergenerational education transmission: the same 13-17 youth cohort
followed across waves, but pooled over ALL panel release windows so the
head-with-superior group is no longer a tiny noisy cell (n~55 in one window ->
n~500+ pooled). Plots enrollment by YEARS-SINCE-BASELINE (t=0..4) for each
head-education group, with bootstrap 95% CI bands so the remaining noise is honest.

Same single-module method as panel_intergen_educacion.py (M03/1475: p203, p208a,
p301a, p306, p307; key cong+vivi+p201p; balanced perpanel; weight fac_panel, or
merged from Sumaria if the file lacks it).

Run:  py -3.14 panel_intergen_pooled.py <m03_file:label> [<m03_file:label> ...]
Outputs: figures/13_panel/fig_intergen_matricula_pooled.{pdf,png}
         datasets/panel_intergen_pooled.csv
"""
from __future__ import annotations

import sys
import warnings
from pathlib import Path

import numpy as np
import pandas as pd
import pyreadstat

import figstyle as fs
import panel_keys as pk

warnings.filterwarnings("ignore")

ROOT = Path(__file__).resolve().parents[1]
FIG = ROOT / "figures" / "13_panel"
DATA = ROOT / "datasets"
FIG.mkdir(parents=True, exist_ok=True)
SUPERIOR = {7, 8, 9, 10, 11}


def cohort_rows(path: str):
    """Return a long DataFrame [t, enrolled, w, sup] for the 13-17 baseline cohort."""
    path = Path(path)
    _, meta = pyreadstat.read_dta(str(path), metadataonly=True)
    cl = {c.lower(): c for c in meta.column_names}
    win, pflag = pk.longest_person_window(cl)
    if not win:
        return None
    years = pk.window_years(win); yy = [f"{y % 100:02d}" for y in years]
    wname = pk.lweight_col(cl, win)
    anch = pk.person_anchors(cl); hh = [a for a in anch if a in ("cong", "vivi", "conglome", "vivienda")]
    need = [cl[a] for a in anch if a in cl] + [cl[pflag]]
    if wname:
        need.append(cl[wname])
    else:
        need += [cl[a] for a in pk.dwelling_key(cl) if a in cl]
    for s in yy:
        for b in ["p203", "p208a", "p301a", "p306", "p307"]:
            if f"{b}_{s}" in cl:
                need.append(cl[f"{b}_{s}"])
    df, _ = pyreadstat.read_dta(str(path), usecols=list(dict.fromkeys(need)))
    df.columns = [c.lower() for c in df.columns]
    df = df[df[pflag.lower()] == 1].copy()
    if wname:
        wv = df[wname.lower()].fillna(0).values
    else:
        hw = pk.hh_panel_weight(path.parent, win)
        if hw is None:
            return None
        df = df.merge(hw, on=[a for a in pk.dwelling_key(cl)], how="left")
        wv = df["w_panel_hh"].fillna(0).values
    N = lambda b, s: pd.to_numeric(df.get(f"{b}_{s}"), errors="coerce")
    s0 = yy[0]
    head = N("p203", s0) == 1
    hs = (N("p301a", s0).isin(SUPERIOR)) & head
    he = df.loc[head, hh].copy(); he["hs"] = hs[head].astype(int).values
    hhsup = he.groupby(hh)["hs"].max()
    df["_hs"] = df[hh].apply(lambda r: tuple(r), axis=1).map(hhsup.to_dict())
    age0 = N("p208a", s0)
    coh = (age0 >= 13) & (age0 <= 17) & df["_hs"].notna()
    sub = df[coh].reset_index(drop=True)
    wv = wv[coh.values]
    out = []
    for t, s in enumerate(yy):
        enr = ((pd.to_numeric(sub.get(f"p306_{s}"), errors="coerce") == 1) &
               (pd.to_numeric(sub.get(f"p307_{s}"), errors="coerce") == 1)).values
        out.append(pd.DataFrame({"t": t, "enrolled": enr.astype(float),
                                 "w": wv, "sup": sub["_hs"].values}))
    return pd.concat(out, ignore_index=True)


def main():
    specs = [a for a in sys.argv[1:] if ":" in a]
    frames = []
    for sp in specs:
        p, lab = sp.rsplit(":", 1)
        print(f"reading {lab} ...", flush=True)
        r = cohort_rows(p)
        if r is not None:
            r["win"] = lab
            frames.append(r)
    pool = pd.concat(frames, ignore_index=True)
    rng = np.random.RandomState(0)
    rows = []
    for t in sorted(pool["t"].unique()):
        for sup, name in [(1, "jefe_superior"), (0, "jefe_no_superior")]:
            d = pool[(pool["t"] == t) & (pool["sup"] == sup)]
            e, w = d["enrolled"].values, d["w"].values
            rate = (e * w).sum() / w.sum() * 100
            n = len(d)
            bs = [(lambda bi: (e[bi] * w[bi]).sum() / w[bi].sum() * 100)(rng.choice(n, n, replace=True))
                  for _ in range(1000)]
            lo, hi = np.percentile(bs, [2.5, 97.5])
            rows.append({"t": t, "edad_aprox": 15 + t, "grupo": name, "n": n,
                         "matricula_pct": rate, "lo": lo, "hi": hi})
    rdf = pd.DataFrame(rows)
    rdf.to_csv(DATA / "panel_intergen_pooled.csv", index=False)
    print(rdf.to_string(index=False))

    fs.use(); fig, ax = fs.fig_ax()
    for sup, name, color, lab in [(1, "jefe_superior", fs.NAVY, "Jefe con educacion superior"),
                                  (0, "jefe_no_superior", fs.CRANBERRY, "Jefe sin educacion superior")]:
        g = rdf[rdf["grupo"] == name].sort_values("t")
        n = int(g["n"].mean())
        ax.plot(g["t"], g["matricula_pct"], "-o", color=color, lw=2.4, label=f"{lab} (n~{n:,})")
        ax.fill_between(g["t"], g["lo"], g["hi"], color=color, alpha=0.15)
    g0 = rdf[rdf.grupo == "jefe_superior"].set_index("t")["matricula_pct"]
    g1 = rdf[rdf.grupo == "jefe_no_superior"].set_index("t")["matricula_pct"]
    gap0, gap1 = g0.iloc[0] - g1.iloc[0], g0.iloc[-1] - g1.iloc[-1]
    ax.set_xticks(sorted(pool["t"].unique()))
    ax.set_xticklabels([f"t+{t}\n~{15+t} anios" for t in sorted(pool["t"].unique())], fontsize=9)
    ax.set_ylabel("% matriculado y asistiendo (misma cohorte 13-17 al inicio)")
    ax.set_xlabel("Olas desde el inicio (la cohorte envejece)")
    ax.set_ylim(0, 100)
    ax.legend(loc="lower left", frameon=False, fontsize=9.5)
    fs.statbox(ax, ["10 ventanas agrupadas (2007-2023)",
                    f"Brecha por origen: {gap0:.0f}pp -> {gap1:.0f}pp",
                    "bandas = IC95 bootstrap"], loc="upper right")
    fs.source(fig, "Fuente: ENAHO Panel (INEI), modulo educacion, 10 ventanas agrupadas. Cohorte co-residente "
                   "13-17 en la ola 1; matricula p306 & p307; educacion del jefe p301a; peso fac_panel.")
    fig.tight_layout()
    for e in ("pdf", "png"):
        fig.savefig(FIG / f"fig_intergen_matricula_pooled.{e}", dpi=200, bbox_inches="tight")
    print("wrote fig_intergen_matricula_pooled")


if __name__ == "__main__":
    main()
