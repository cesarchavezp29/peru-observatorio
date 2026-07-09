"""
panel_intergen_educacion.py
===========================
INTERGENERATIONAL transmission of educational (dis)advantage, the panel way: follow
the SAME co-resident youth across waves and ask whether their enrollment trajectory
depends on the HOUSEHOLD HEAD's education at baseline. The cross-section can only
take a snapshot (fig_movilidad_educativa_tiempo); the panel watches the same child
stay in or drop out of school as they age.

All from the education module (M03 old / 1475 new), which carries p203 (parentesco),
p208a (age), p301a (head's education), p306/p307 (enrollment) -- no cross-module
merge. Person key cong+vivi+p201p; household = cong+vivi. Balanced persons
(perpanel<window>==1), weight fac_panel<window>.

Cohort: youth aged 13-17 in the FIRST wave (schooling-decision ages), co-resident.
Head education at baseline: head (p203==1) has SUPERIOR (p301a in 7..11) vs not.
Outcome: enrolled = p306==1 (matriculado) AND p307==1 (asiste). We plot weighted
enrollment by wave for each head-education group -> the gap is the transmission.

Run:  py -3.14 panel_intergen_educacion.py <m03_panel.dta> --label 2007-2011
Outputs: figures/13_panel/fig_intergen_matricula_<label>.{pdf,png}
         datasets/panel_intergen_educacion_<label>.csv
"""
from __future__ import annotations

import argparse
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
DATA.mkdir(exist_ok=True)

SUPERIOR = {7, 8, 9, 10, 11}   # p301a codes = educacion superior


def analyze(path, label):
    path = Path(path)
    _, meta = pyreadstat.read_dta(str(path), metadataonly=True)
    cl = {c.lower(): c for c in meta.column_names}
    win, pflag = pk.longest_person_window(cl)
    if not win:
        print("no person membership flag - is this a panel educacion file?"); return
    years = pk.window_years(win); yy = [f"{y % 100:02d}" for y in years]
    wname = pk.lweight_col(cl, win)
    if not wname:
        print(f"no longitudinal weight for {win}"); return
    anch = pk.person_anchors(cl)
    hh = [a for a in anch if a in ("cong", "vivi", "conglome", "vivienda")]

    bases = ["p203", "p208a", "p301a", "p306", "p307"]
    need = [cl[a] for a in anch if a in cl] + [cl[pflag], cl[wname]]
    for s in yy:
        for b in bases:
            if f"{b}_{s}" in cl:
                need.append(cl[f"{b}_{s}"])
    df, _ = pyreadstat.read_dta(str(path), usecols=list(dict.fromkeys(need)))
    dcl = {c.lower(): c for c in df.columns}
    df = df[df[dcl[pflag]] == 1].copy()
    hhcols = [dcl[a] for a in hh]

    s0 = yy[0]
    num = lambda b, s: pd.to_numeric(df[dcl[f"{b}_{s}"]], errors="coerce") if f"{b}_{s}" in dcl else pd.Series(np.nan, index=df.index)

    # head education at baseline, broadcast to household
    head = num("p203", s0) == 1
    head_edu_sup = (num("p301a", s0).isin(SUPERIOR)) & head
    he = df.loc[head, hhcols].copy()
    he["head_sup"] = head_edu_sup[head].astype(int).values
    hh_sup = he.groupby(hhcols)["head_sup"].max()           # 1 if head has superior
    key = df[hhcols].apply(lambda r: tuple(r), axis=1)
    df["_hsup"] = key.map(hh_sup.to_dict())

    # cohort: co-resident youth aged 13-17 at baseline
    age0 = num("p208a", s0)
    cohort = (age0 >= 13) & (age0 <= 17) & df["_hsup"].notna()
    sub = df[cohort].copy()
    w = sub[dcl[wname]].fillna(0).values
    hsup = sub["_hsup"].values

    rows = []
    for y, s in zip(years, yy):
        enr = ((pd.to_numeric(sub[dcl[f"p306_{s}"]], errors="coerce") == 1) &
               (pd.to_numeric(sub[dcl[f"p307_{s}"]], errors="coerce") == 1)).values \
            if f"p306_{s}" in dcl and f"p307_{s}" in dcl else np.zeros(len(sub), bool)
        for grp, name in [(hsup == 1, "jefe_superior"), (hsup == 0, "jefe_no_superior")]:
            ww = w[grp]
            rate = float((enr[grp] * ww).sum() / ww.sum()) * 100 if ww.sum() else np.nan
            rows.append({"anio": y, "edad_aprox": 13 + (y - years[0]) + 2, "grupo": name,
                         "matricula_pct": rate, "n": int(grp.sum())})
    rdf = pd.DataFrame(rows)
    rdf.to_csv(DATA / f"panel_intergen_educacion_{label}.csv", index=False)
    piv = rdf.pivot(index="anio", columns="grupo", values="matricula_pct")
    gap0 = piv.iloc[0]["jefe_superior"] - piv.iloc[0]["jefe_no_superior"]
    gap1 = piv.iloc[-1]["jefe_superior"] - piv.iloc[-1]["jefe_no_superior"]
    n_sup = int((hsup == 1).sum()); n_no = int((hsup == 0).sum())
    print(f"[{label}] cohorte 13-17 en {years[0]}: n_sup={n_sup} n_no={n_no} "
          f"matricula brecha {gap0:.0f}pp -> {gap1:.0f}pp")
    _fig(label, rdf, years, gap0, gap1, n_sup, n_no)


def _fig(label, rdf, years, gap0, gap1, n_sup, n_no):
    fs.use(); fig, ax = fs.fig_ax()
    piv = rdf.pivot(index="anio", columns="grupo", values="matricula_pct")
    x = piv.index.astype(int).tolist()
    ax.plot(x, piv["jefe_superior"], "-o", color=fs.NAVY, lw=2.4,
            label=f"Jefe con educacion superior (n={n_sup:,})")
    ax.plot(x, piv["jefe_no_superior"], "-o", color=fs.CRANBERRY, lw=2.4,
            label=f"Jefe sin educacion superior (n={n_no:,})")
    for xi in x:
        ax.text(xi, piv.loc[xi, "jefe_superior"] + 2, f"{piv.loc[xi,'jefe_superior']:.0f}",
                ha="center", fontsize=8.2, color=fs.NAVY)
        ax.text(xi, piv.loc[xi, "jefe_no_superior"] - 4, f"{piv.loc[xi,'jefe_no_superior']:.0f}",
                ha="center", fontsize=8.2, color=fs.CRANBERRY)
    ax.set_ylabel("% matriculado y asistiendo (misma cohorte 13-17 al inicio)")
    ax.set_xlabel(f"Ola (la cohorte envejece {13}->{13+len(x)-1+1} anios aprox.)")
    ax.set_xticks(x)
    ax.set_ylim(0, 100)
    ax.legend(loc="lower left", frameon=False, fontsize=9.2)
    fs.statbox(ax, ["Misma cohorte seguida 5 olas",
                    f"Brecha por origen: {gap0:.0f}pp -> {gap1:.0f}pp",
                    "los hijos de jefe sin superior",
                    "abandonan antes (transmision)"], loc="upper right")
    fs.source(fig, "Fuente: ENAHO Panel (INEI), modulo educacion. Cohorte co-residente 13-17 en la ola 1, "
                   "seguida; matricula = p306 & p307; educacion del jefe (p203==1) p301a; peso fac_panel.")
    fig.tight_layout()
    for e in ("pdf", "png"):
        fig.savefig(FIG / f"fig_intergen_matricula_{label}.{e}", dpi=200, bbox_inches="tight")
    print("  wrote fig_intergen_matricula")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("path"); ap.add_argument("--label", default="panel")
    a = ap.parse_args(); analyze(a.path, a.label)


if __name__ == "__main__":
    main()
