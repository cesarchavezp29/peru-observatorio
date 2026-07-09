"""Produce las familias del ENAHO Panel (60 tablas: pobreza/informalidad/seguro
x dinamica/transicion, 10 ventanas cada una).

PORTADO SIN REFACTORIZAR de ENAHO_ANALYSIS/scripts/panel_pobreza_dinamica.py,
panel_empleo_informalidad.py y panel_salud_seguro.py: los analyze() son copia
literal menos las figuras. La deteccion de llaves/flags/pesos vive en
_panel_keys.py (copia verbatim de panel_keys.py).

Entradas crudas: PANEL_RAW (dirs <release>_<code> con sumaria*panel.dta,
*-400-panel.dta salud, *-500-panel.dta empleo — el layout que descarga
perudata.panel o el archivo local del proyecto).

Nota: panel_movilidad_quintil_* NO se produce aqui — depende del parquet largo
(build_panel_dataset.py), pendiente de porteo (W2b), declarado en el manifest.

Run:
  PANEL_RAW=... python pipeline/build_panel_familias.py               # escribe
  PANEL_RAW=... python pipeline/build_panel_familias.py --check-against data/datasets
"""
from __future__ import annotations

import argparse
import os
import re
import sys
import tempfile
import warnings
from pathlib import Path

import numpy as np
import pandas as pd
import pyreadstat

sys.path.insert(0, str(Path(__file__).resolve().parent))
import _panel_keys as pk  # noqa: E402

warnings.filterwarnings("ignore")

DATASETS = Path(__file__).resolve().parent.parent / "data" / "datasets"


# --------------------------------------------------------------------------- #
# pobreza (copia de panel_pobreza_dinamica.analyze, sin figuras)
# --------------------------------------------------------------------------- #
def pobreza(path: Path, label: str, outdir: Path) -> None:
    _, meta = pyreadstat.read_dta(str(path), metadataonly=True)
    cl = {c.lower(): c for c in meta.column_names}
    window, flag = pk.longest_window(cl)
    if not window:
        print(f"[{label}] sin flag de membresia balanceada, salto")
        return
    years = pk.window_years(window)
    yy = [f"{y % 100:02d}" for y in years]
    pobr = [f"pobreza_{s}" for s in yy if f"pobreza_{s}" in cl]
    miep = f"mieperho_{yy[0]}"
    wname = pk.lweight_col(cl, window)
    if not wname:
        print(f"[{label}] sin peso longitudinal para {window}, salto")
        return
    anch = pk.anchors(cl)
    need = anch + [flag] + pobr
    need = [cl.get(c.lower(), c) for c in need if c.lower() in cl] + [cl[wname]]
    if miep in cl:
        need.append(cl[miep])
    df, _ = pyreadstat.read_dta(str(path), usecols=list(dict.fromkeys(need)))

    df = df[df[cl[flag]] == 1].copy()
    w = df[cl[wname]].fillna(0)
    mp = df[cl[miep]].fillna(1) if miep in cl else 1.0
    pw = w * mp

    poor = pd.DataFrame({s: df[f"pobreza_{s}"].isin([1, 2]).astype(float)
                         for s in yy if f"pobreza_{s}" in df.columns})
    valid = pd.DataFrame({s: df[f"pobreza_{s}"].notna()
                          for s in yy if f"pobreza_{s}" in df.columns})
    nwaves = valid.sum(axis=1)
    keep = nwaves == len(poor.columns)
    poor, pw, df = poor[keep], pw[keep], df[keep]
    times_poor = poor.sum(axis=1).astype(int)
    nW = poor.shape[1]

    def wshare(mask):
        return float(pw[mask].sum() / pw.sum()) * 100

    never = wshare(times_poor == 0)
    chronic = wshare(times_poor == nW)
    transient = wshare((times_poor >= 1) & (times_poor < nW))
    ever = 100 - never
    annual = float((poor.mul(pw, axis=0).sum().sum()) / (pw.sum() * nW)) * 100
    dist = {k: wshare(times_poor == k) for k in range(nW + 1)}

    trans = []
    ycols = list(poor.columns)
    for a, b in zip(ycols[:-1], ycols[1:]):
        pa, pb = poor[a] == 1, poor[b] == 1
        denom_np = pw[~pa].sum()
        denom_p = pw[pa].sum()
        entry = float(pw[(~pa) & pb].sum() / denom_np) * 100 if denom_np else np.nan
        exit_ = float(pw[pa & (~pb)].sum() / denom_p) * 100 if denom_p else np.nan
        trans.append({"from": 2000 + int(a), "to": 2000 + int(b),
                      "entry_rate": entry, "exit_rate": exit_})
    tdf = pd.DataFrame(trans)

    pd.DataFrame([{"label": label, "window": window, "n_hh": len(df),
                   "waves": nW, "annual_static_pct": annual, "ever_poor_pct": ever,
                   "chronic_pct": chronic, "transient_pct": transient,
                   "never_pct": never, **{f"poor_{k}w_pct": v for k, v in dist.items()}}]
                 ).to_csv(outdir / f"panel_pobreza_dinamica_{label}.csv", index=False)
    tdf.to_csv(outdir / f"panel_pobreza_transicion_{label}.csv", index=False)
    print(f"[{label}] pobreza n_hh={len(df)} chronic={chronic:.1f}% transient={transient:.1f}%")


# --------------------------------------------------------------------------- #
# informalidad (copia de panel_empleo_informalidad, sin figuras)
# --------------------------------------------------------------------------- #
def _informal_wave(df, dcl, s, year):
    def col(base):
        return df[dcl[f"{base}_{s}"]] if f"{base}_{s}" in dcl else pd.Series(np.nan, index=df.index)
    occ = (pd.to_numeric(col("ocu500"), errors="coerce") == 1).values
    cat = pd.to_numeric(col("p507"), errors="coerce").values
    formal_contract = [1, 2] if year <= 2011 else [1, 2, 6]
    cf = pd.to_numeric(col("p511a"), errors="coerce").isin(formal_contract).values
    if f"p510a1_{s}" in dcl:
        sector_formal = pd.to_numeric(col("p510a1"), errors="coerce").isin([1, 2]).values
    else:
        sector_formal = (pd.to_numeric(col("p510a"), errors="coerce") == 1).values
    informal = np.zeros(len(df), bool)
    informal[np.isin(cat, [5, 7])] = True
    dep = np.isin(cat, [3, 4, 6])
    informal[dep] = ~cf[dep]
    emp = np.isin(cat, [1, 2])
    informal[emp] = ~sector_formal[emp]
    return occ, informal


def informalidad(path: Path, label: str, outdir: Path) -> None:
    _, meta = pyreadstat.read_dta(str(path), metadataonly=True)
    cl = {c.lower(): c for c in meta.column_names}
    win, pflag = pk.longest_person_window(cl)
    if not win:
        print(f"[{label}] sin flag de persona (perpanel), salto")
        return
    years = pk.window_years(win)
    yy = [f"{y % 100:02d}" for y in years]
    wname = pk.lweight_col(cl, win)
    if not wname:
        print(f"[{label}] sin peso longitudinal para {win}, salto")
        return
    anch = pk.person_anchors(cl)

    bases = ["ocu500", "p507", "p511a", "p510a", "p510a1"]
    need = [cl[a] for a in anch if a in cl] + [cl[pflag], cl[wname]]
    for s in yy:
        for b in bases:
            if f"{b}_{s}" in cl:
                need.append(cl[f"{b}_{s}"])
    df, _ = pyreadstat.read_dta(str(path), usecols=list(dict.fromkeys(need)))
    dcl = {c.lower(): c for c in df.columns}

    df = df[df[dcl[pflag]] == 1].copy()
    w = df[dcl[wname]].fillna(0).values

    occ = {}
    inf = {}
    for y, s in zip(years, yy):
        o, i = _informal_wave(df, dcl, s, y)
        occ[y] = o
        inf[y] = i
    occ_all = np.logical_and.reduce([occ[y] for y in years])
    if occ_all.sum() == 0:
        print(f"[{label}] sin ocupados todas las olas")
        return
    wf = w[occ_all]
    infmat = np.column_stack([inf[y][occ_all].astype(float) for y in years])
    times_inf = infmat.sum(axis=1).astype(int)
    nW = len(years)

    def wsh(mask):
        return float(wf[mask].sum() / wf.sum()) * 100

    always_formal = wsh(times_inf == 0)
    chronic = wsh(times_inf == nW)
    transitional = wsh((times_inf >= 1) & (times_inf < nW))
    ever_inf = 100 - always_formal
    static = float((infmat * wf[:, None]).sum() / (wf.sum() * nW)) * 100
    dist = {k: wsh(times_inf == k) for k in range(nW + 1)}

    trans = []
    for a, b in zip(years[:-1], years[1:]):
        both = occ[a] & occ[b]
        wb = w[both]
        ia, ib = inf[a][both], inf[b][both]
        formal_a = wb[~ia].sum()
        inf_a = wb[ia].sum()
        informaliz = float(wb[(~ia) & ib].sum() / formal_a) * 100 if formal_a else np.nan
        formaliz = float(wb[ia & (~ib)].sum() / inf_a) * 100 if inf_a else np.nan
        trans.append({"from": a, "to": b, "informalizacion": informaliz, "formalizacion": formaliz})
    tdf = pd.DataFrame(trans)

    pd.DataFrame([{"label": label, "window": win, "n_workers_allwaves": int(occ_all.sum()),
                   "waves": nW, "static_informal_pct": static, "ever_informal_pct": ever_inf,
                   "chronic_pct": chronic, "transitional_pct": transitional,
                   "always_formal_pct": always_formal,
                   **{f"inf_{k}w_pct": v for k, v in dist.items()}}]
                 ).to_csv(outdir / f"panel_informalidad_dinamica_{label}.csv", index=False)
    tdf.to_csv(outdir / f"panel_informalidad_transicion_{label}.csv", index=False)
    print(f"[{label}] informalidad n={int(occ_all.sum())} chronic={chronic:.1f}%")


# --------------------------------------------------------------------------- #
# seguro (copia de panel_salud_seguro, sin figuras)
# --------------------------------------------------------------------------- #
INS_SLOTS = ["p4191", "p4192", "p4193", "p4194", "p4195", "p4196", "p4197", "p4198"]


def _status_wave(df, dcl, s):
    def col(b):
        return pd.to_numeric(df[dcl[f"{b}_{s}"]], errors="coerce") if f"{b}_{s}" in dcl \
            else pd.Series(np.nan, index=df.index)
    any_ins = np.zeros(len(df), bool)
    present = False
    for b in INS_SLOTS:
        if f"{b}_{s}" in dcl:
            any_ins |= (col(b) == 1).values
            present = True
    sis = (col("p4195") == 1).values
    return (any_ins if present else None), sis


def seguro(path: Path, label: str, outdir: Path) -> None:
    _, meta = pyreadstat.read_dta(str(path), metadataonly=True)
    cl = {c.lower(): c for c in meta.column_names}
    win, pflag = pk.longest_person_window(cl)
    if not win:
        print(f"[{label}] sin flag de persona, salto")
        return
    years = pk.window_years(win)
    yy = [f"{y % 100:02d}" for y in years]
    wname = pk.lweight_col(cl, win)
    anch = pk.person_anchors(cl)
    dk = pk.dwelling_key(cl)
    need = [cl[a] for a in anch if a in cl] + [cl[pflag]]
    if wname:
        need.append(cl[wname])
    else:
        need += [cl[a] for a in dk if a in cl]
    for s in yy:
        for b in INS_SLOTS:
            if f"{b}_{s}" in cl:
                need.append(cl[f"{b}_{s}"])
    df, _ = pyreadstat.read_dta(str(path), usecols=list(dict.fromkeys(need)))
    df.columns = [c.lower() for c in df.columns]
    dcl = {c: c for c in df.columns}
    df = df[df[pflag.lower()] == 1].copy()
    if wname:
        w = df[wname.lower()].fillna(0).values
    else:
        hw = pk.hh_panel_weight(path.parent, win)
        if hw is None:
            print(f"[{label}] sin peso longitudinal (ni en sumaria), salto")
            return
        df = df.merge(hw, on=[a for a in dk], how="left")
        w = df["w_panel_hh"].fillna(0).values
        print(f"  [info] ventana {win}: peso panel mergeado desde la sumaria")

    anyins = {}
    sis = {}
    for y, s in zip(years, yy):
        a, si = _status_wave(df, dcl, s)
        anyins[y] = a if a is not None else np.zeros(len(df), bool)
        sis[y] = si
    stock = []
    for y in years:
        ww = w
        stock.append({"anio": y,
                      "any_ins_pct": float((anyins[y] * ww).sum() / ww.sum()) * 100,
                      "sis_pct": float((sis[y] * ww).sum() / ww.sum()) * 100})
    sdf = pd.DataFrame(stock)
    never_ins = np.logical_and.reduce([~anyins[y] for y in years])
    always_ins = np.logical_and.reduce([anyins[y] for y in years])
    chronic_unins = float((never_ins * w).sum() / w.sum()) * 100
    always = float((always_ins * w).sum() / w.sum()) * 100
    trans = []
    for a, b in zip(years[:-1], years[1:]):
        no_a = w[~sis[a]]
        yes_a = w[sis[a]]
        gain = float(w[(~sis[a]) & sis[b]].sum() / no_a.sum()) * 100 if no_a.sum() else np.nan
        lose = float(w[sis[a] & (~sis[b])].sum() / yes_a.sum()) * 100 if yes_a.sum() else np.nan
        trans.append({"from": a, "to": b, "gana_sis": gain, "pierde_sis": lose})
    tdf = pd.DataFrame(trans)

    sdf.assign(chronic_uninsured_pct=chronic_unins, always_insured_pct=always,
               label=label, window=win).to_csv(
        outdir / f"panel_seguro_dinamica_{label}.csv", index=False)
    tdf.to_csv(outdir / f"panel_seguro_transicion_{label}.csv", index=False)
    print(f"[{label}] seguro SIS {sdf['sis_pct'].iloc[0]:.0f}->{sdf['sis_pct'].iloc[-1]:.0f}%")


# --------------------------------------------------------------------------- #
# driver + verificacion
# --------------------------------------------------------------------------- #
def find_inputs(release_dir: Path) -> dict:
    """sumaria / empleo(500) / salud(400) dentro de un dir de release."""
    dtas = list(release_dir.glob("*.dta"))
    out = {}
    sums = [p for p in dtas if "sumaria" in p.name.lower() and "12g" not in p.name.lower()]
    if sums:
        out["sumaria"] = max(sums, key=lambda p: p.stat().st_size)
    for kind, tag in (("empleo", "500"), ("salud", "400")):
        hits = [p for p in dtas if re.search(rf"[-_]{tag}[-_.]", p.name)]
        if hits:
            out[kind] = max(hits, key=lambda p: p.stat().st_size)
    return out


def label_for(path: Path) -> str | None:
    """Etiqueta 20YY-20YY desde la ventana mas larga del archivo."""
    _, meta = pyreadstat.read_dta(str(path), metadataonly=True)
    cl = {c.lower(): c for c in meta.column_names}
    win = pk.longest_window(cl)[0] or pk.longest_person_window(cl)[0]
    if not win:
        return None
    return f"20{win[:2]}-20{win[2:]}"


def compare_dir(newdir: Path, refdir: Path) -> int:
    """Compara cada CSV producido contra el committeado. Tolerancias de ruido float."""
    bad = 0
    produced = sorted(newdir.glob("*.csv"))
    for p in produced:
        ref = refdir / p.name
        if not ref.exists():
            print(f"  NUEVO (sin referencia committeada): {p.name}")
            continue
        a = pd.read_csv(ref)
        b = pd.read_csv(p)
        if list(a.columns) != list(b.columns) or len(a) != len(b):
            print(f"  FAIL forma: {p.name} ref{a.shape} vs new{b.shape}")
            bad += 1
            continue
        for c in a.columns:
            av = pd.to_numeric(a[c], errors="coerce")
            bv = pd.to_numeric(b[c], errors="coerce")
            if av.notna().any():
                d = (av - bv).abs().max()
                if pd.notna(d) and d > 1e-3:
                    print(f"  FAIL {p.name} col {c}: max diff {d}")
                    bad += 1
                    break
            elif not a[c].astype(str).equals(b[c].astype(str)):
                print(f"  FAIL {p.name} col {c}: texto difiere")
                bad += 1
                break
    print(f"comparadas {len(produced)} tablas, {bad} con diferencias")
    return bad


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--check-against", default=None,
                    help="dir de CSVs committeados: produce a temp y compara, no escribe")
    a = ap.parse_args()
    raw = Path(os.environ.get("PANEL_RAW", "peru_raw/enaho_panel"))
    if not raw.exists():
        print(f"FAIL: PANEL_RAW no existe: {raw}")
        sys.exit(1)

    outdir = Path(tempfile.mkdtemp()) if a.check_against else DATASETS
    releases = sorted(d for d in raw.iterdir() if d.is_dir() and not d.name.startswith("_"))
    for rel in releases:
        ins = find_inputs(rel)
        if "sumaria" in ins:
            lab = label_for(ins["sumaria"])
            if lab:
                pobreza(ins["sumaria"], lab, outdir)
        if "empleo" in ins:
            lab = label_for(ins["empleo"])
            if lab:
                informalidad(ins["empleo"], lab, outdir)
        if "salud" in ins:
            lab = label_for(ins["salud"])
            if lab:
                seguro(ins["salud"], lab, outdir)

    if a.check_against:
        bad = compare_dir(outdir, Path(a.check_against))
        sys.exit(1 if bad else 0)


if __name__ == "__main__":
    main()
