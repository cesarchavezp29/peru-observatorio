"""
panel_evento_hijo_empleo.py
===========================
TRUE within-person CHILD-PENALTY event study from the ENAHO Panel -- the honest
panel analogue of the cross-section pseudo-panel fig_evento_maternidad_empleo.py.

The cross-section script could only read a SYNTHETIC profile by the age of the
youngest child in the household (it never follows the same woman before/after a
birth). The panel DOES: we track the SAME woman across waves (key
conglome+vivienda+p201p), date the birth of a child she heads/parents, and read
her employment (ocu500) at event time e = wave_year - birth_year. Reference =
women head/spouse 18-45 whose household never has a newborn in the window.

BIRTH DETECTION (roster module "200" / 1314, present 2016->2023 releases only;
the 2007-2011 and 2011-2015 releases ship NO roster so they are skipped):
  newborn in household h, wave t  <=>  a roster member with p203==3 (hijo/a) and
  p208a==0 (age under 1 => born in year t). The "mother" is the female (p207==2)
  head (p203==1) or spouse (p203==2), age 18-45, in that household that wave.
  We CANNOT perfectly assign maternity (could be a household with a young
  grandmother etc.); restricting to female head/spouse 18-45 keeps the likely
  mother and drops grandparent contamination. Birth wave t* = first wave her
  household shows a newborn. Fathers = male head/spouse 18-55, same rule.

EMPLOYMENT (empleo module "500"): ocu500==1 = ocupado, per wave, joined to the
mother by conglome+vivienda+p201p. We restrict to the longest BALANCED person
window (perpanel<win>==1) and weight by the longitudinal facpanel<win> (carried
to persons) -- same discipline as panel_empleo_informalidad.py.

Releases are OVERLAPPING windows; pooling stacks (release, woman) event-time
observations. We do NOT link ids across releases (we don't need to: each
trajectory is within its own release). Overlap means the precision is optimistic
-- reported honestly in the figure note. n per event-time bin is printed and bins
with n < MIN_CELL are not plotted.

Run:  py -3.14 panel_evento_hijo_empleo.py [--release 2023_912] [--rebuild]
Outputs: figures/13_panel/fig_evento_hijo_empleo_panel.{pdf,png}
         datasets/panel_evento_hijo_empleo.csv
"""
from __future__ import annotations

import argparse
import re
import warnings
from pathlib import Path

import numpy as np
import pandas as pd
import pyreadstat

import figstyle as fs
import panel_keys as pk

warnings.filterwarnings("ignore")

ROOT = Path(__file__).resolve().parents[1]
RAWP = ROOT / "raw" / "panel"
FIG = ROOT / "figures" / "13_panel"
DATA = ROOT / "datasets"
FIG.mkdir(parents=True, exist_ok=True)
DATA.mkdir(exist_ok=True)
CSV = DATA / "panel_evento_hijo_empleo.csv"

EMIN, EMAX = -3, 3          # event-time window to report
MIN_CELL = 25               # min weighted-unit count to plot a bin
HIJO, JEFE, ESPOSO = 3, 1, 2


def _wave_suffixes(cl: dict, bases: list[str]) -> list[str]:
    """2-digit year suffixes present for ANY of the per-wave bases (union)."""
    out = set()
    for base in bases:
        for c in cl:
            m = re.match(rf"^{re.escape(base)}_(\d{{2}})$", c)
            if m:
                out.add(m.group(1))
    return sorted(out)


def _melt_waves(path: Path, wave_bases: list[str], key_base: str,
                extra_const: dict | None = None) -> pd.DataFrame:
    """Read only the columns needed and melt per-wave bases into a tidy long panel.

    wave_bases: per-wave variables to carry. Each is read from `<base>_<NN>` if
        present, else from an unsuffixed constant `<base>` (handles ids that INEI
        stores constant in some releases, e.g. p201p in the 2013-2017 roster).
    key_base: the per-wave variable whose non-null value marks PRESENCE in a wave
        (codperso); rows where it is null are dropped (person absent that wave).
    extra_const: {out_name: source_lower} unsuffixed columns carried constant
        (a weight, a balanced flag).
    Returns long df with columns: cong, vivi, anio, <wave_bases>, <extra_const>.
    """
    extra_const = extra_const or {}
    _, meta = pyreadstat.read_dta(str(path), metadataonly=True)
    cl = {c.lower(): c for c in meta.column_names}
    waves = _wave_suffixes(cl, wave_bases)
    usel = []
    for src in ("conglome", "vivienda"):
        if src in cl:
            usel.append(cl[src])
    for v, src in extra_const.items():
        if src in cl:
            usel.append(cl[src])
    for b in wave_bases:                       # suffixed and/or constant form
        if b in cl:
            usel.append(cl[b])
        for s in waves:
            if f"{b}_{s}" in cl:
                usel.append(cl[f"{b}_{s}"])
    usel = list(dict.fromkeys(usel))
    df, _ = pyreadstat.read_dta(str(path), usecols=usel)
    df.columns = [c.lower() for c in df.columns]

    rows = []
    for s in waves:
        d = pd.DataFrame({"cong": df["conglome"], "vivi": df["vivienda"],
                          "anio": 2000 + int(s)})
        for b in wave_bases:
            col = f"{b}_{s}"
            if col in df.columns:
                d[b] = pd.to_numeric(df[col], errors="coerce")
            elif b in df.columns:              # constant across waves
                d[b] = pd.to_numeric(df[b], errors="coerce")
            else:
                d[b] = np.nan
        for v, src in extra_const.items():
            d[v] = df[src.lower()].values if src.lower() in df.columns else np.nan
        rows.append(d.dropna(subset=[key_base]))
    out = pd.concat(rows, ignore_index=True) if rows else pd.DataFrame()
    # integer-cast the join keys so roster<->empleo merges match exactly
    for k in ("hogar", "codperso", "p201p", "p201pcor"):
        if k in out.columns:
            out[k] = pd.to_numeric(out[k], errors="coerce").round().astype("Int64")
    return out


def _roster_long(roster_path: Path) -> pd.DataFrame:
    """Tidy long roster keyed per wave by codperso, carrying the stable p201p.

    Columns: cong, vivi, anio, hogar, codperso, p201p, p203, p207, p208a.
    The stable person id drifts p201p <-> p201pcor across releases; coalesce them.
    """
    ro = _melt_waves(roster_path,
                     ["p201p", "p201pcor", "codperso", "hogar", "p203", "p207", "p208a"],
                     key_base="codperso")
    if ro.empty:
        return ro
    if "p201pcor" in ro.columns:
        if "p201p" in ro.columns:
            ro["p201p"] = ro["p201p"].fillna(ro["p201pcor"])
        else:
            ro["p201p"] = ro["p201pcor"]
        ro = ro.drop(columns=["p201pcor"])
    return ro


def _events_from_roster(ro: pd.DataFrame):
    """Return (mothers, fathers, ref_women) frames keyed by person with birth wave.

    mothers/fathers: columns [cong, vivi, p201p, tstar]
    ref_women: columns [cong, vivi, p201p]  (head/spouse women, no newborn ever)
    """
    ro = ro.copy()
    ro["newborn"] = ((ro["p203"] == HIJO) & (ro["p208a"] == 0)).astype(int)
    # household-wave birth flag
    hb = (ro.groupby(["cong", "vivi", "hogar", "anio"])["newborn"].max()
          .rename("hh_birth").reset_index())
    ro = ro.merge(hb, on=["cong", "vivi", "hogar", "anio"], how="left")

    def parent_set(sex, amin, amax):
        m = ((ro["p207"] == sex) & (ro["p203"].isin([JEFE, ESPOSO]))
             & ro["p208a"].between(amin, amax))
        return ro[m]

    wom = parent_set(2, 18, 45)
    men = parent_set(1, 18, 55)

    def with_birth(par):
        b = par[par["hh_birth"] == 1]
        if b.empty:
            return pd.DataFrame(columns=["cong", "vivi", "p201p", "tstar"])
        t = (b.groupby(["cong", "vivi", "p201p"])["anio"].min()
             .rename("tstar").reset_index())
        return t

    mothers = with_birth(wom)
    fathers = with_birth(men)
    # reference: head/spouse women who NEVER have a newborn in any observed wave
    ever = wom.groupby(["cong", "vivi", "p201p"])["hh_birth"].max().rename("ever").reset_index()
    ref_women = ever[ever["ever"] == 0][["cong", "vivi", "p201p"]].copy()
    return mothers, fathers, ref_women


def _empleo_panel(empleo_paths: list[Path]):
    """Read ocu500 per wave for the longest balanced person window.

    Keyed by the per-wave locator (cong, vivi, anio, hogar, codperso) -- the
    employment files do NOT all carry the stable p201p id (the 2013-2017 file has
    none, 2015-2019 uses p201pcor), so we never key on p201p here; the roster
    crosswalk attaches it. Returns (long_emp, win) with columns
    [cong, vivi, anio, hogar, codperso, emp, w] restricted to perpanel<win>==1.
    """
    _, meta = pyreadstat.read_dta(str(empleo_paths[0]), metadataonly=True)
    cl = {c.lower(): c for c in meta.column_names}
    win, pflag = pk.longest_person_window(cl)
    if not win:
        return None, None
    wname = pk.lweight_col(cl, win)
    if not wname:
        return None, None

    parts = [
        _melt_waves(p, ["codperso", "hogar", "ocu500"], key_base="codperso",
                    extra_const={"flag": pflag.lower(), "w": wname.lower()})
        for p in empleo_paths
    ]
    parts = [d for d in parts if not d.empty]
    if not parts:
        return None, None
    df = pd.concat(parts, ignore_index=True)
    if df.empty:
        return None, None
    df = df[df["flag"] == 1].copy()               # balanced person panel
    df["w"] = pd.to_numeric(df["w"], errors="coerce").fillna(0.0)
    df["emp"] = np.where(df["ocu500"].isna(), np.nan, (df["ocu500"] == 1).astype(float))
    return df[["cong", "vivi", "anio", "hogar", "codperso", "emp", "w"]], win


def process_release(rel_dir: Path) -> pd.DataFrame:
    """Return event-time person-wave rows for one release (empty if no roster)."""
    files = list(rel_dir.glob("*.dta"))
    # file names vary: -200-, _200_, -200_PANEL, 1314 ; -500-, -500_PANEL, _500_ ...
    roster = [f for f in files if re.search(r"(?i)([-_]200[-_]|1314)", f.name)]
    empleo = sorted(f for f in files if re.search(r"(?i)[-_]500[-_]", f.name))
    if not roster or not empleo:
        return pd.DataFrame()

    ro = _roster_long(roster[0])
    mothers, fathers, ref_women = _events_from_roster(ro)
    long_emp, win = _empleo_panel(empleo)
    if long_emp is None:
        print(f"  {rel_dir.name}: no balanced person window in empleo -> skip")
        return pd.DataFrame()

    # attach the stable p201p to employment rows via the per-wave locator
    xwalk = (ro.dropna(subset=["p201p", "codperso"])
             [["cong", "vivi", "anio", "hogar", "codperso", "p201p"]]
             .drop_duplicates(["cong", "vivi", "anio", "hogar", "codperso"]))
    long_emp = long_emp.merge(xwalk, on=["cong", "vivi", "anio", "hogar", "codperso"], how="inner")
    if long_emp.empty:
        print(f"  {rel_dir.name}: roster<->empleo join empty -> skip")
        return pd.DataFrame()

    out = []

    def attach(parents, group):
        if parents.empty:
            return
        m = long_emp.merge(parents, on=["cong", "vivi", "p201p"], how="inner")
        if m.empty:
            return
        m = m.dropna(subset=["emp"])
        m["e"] = m["anio"] - m["tstar"]
        m["group"] = group
        m["release"] = rel_dir.name
        out.append(m[["release", "group", "cong", "vivi", "p201p", "e", "emp", "w"]])

    attach(mothers, "madre")
    attach(fathers, "padre")
    # reference women: flat level, no event time -> e = NaN sentinel handled later
    if not ref_women.empty:
        r = long_emp.merge(ref_women, on=["cong", "vivi", "p201p"], how="inner").dropna(subset=["emp"])
        if not r.empty:
            r = r.assign(group="ref_madre", release=rel_dir.name, e=np.nan,
                         tstar=np.nan)
            out.append(r[["release", "group", "cong", "vivi", "p201p", "e", "emp", "w"]])

    res = pd.concat(out, ignore_index=True) if out else pd.DataFrame()
    if not res.empty:
        nm = res[res.group == "madre"]["p201p"].nunique()
        nf = res[res.group == "padre"]["p201p"].nunique()
        nr = res[res.group == "ref_madre"]["p201p"].nunique()
        print(f"  {rel_dir.name} [win {win}]: madres={nm} padres={nf} ref_mujeres={nr}")
    return res


def build() -> pd.DataFrame:
    frames = []
    for rel in sorted(p for p in RAWP.iterdir() if p.is_dir() and re.match(r"\d{4}_\d+$", p.name)):
        frames.append(process_release(rel))
    pool = pd.concat([f for f in frames if not f.empty], ignore_index=True)
    pool.to_csv(CSV, index=False)
    return pool


# Balanced event-time window: only parents observed at EVERY e in this window are
# kept, so the SAME people appear in every bin -- the level profile is a clean
# within-person comparison (no composition zig-zag) and shows both the gender gap
# (distance madre<->padre) and the maternal dip in actual employment %.
BAL_WINDOW = [-2, -1, 0, 1, 2]


def _balanced_levels(df: pd.DataFrame, window: list[int]) -> tuple[pd.DataFrame, int]:
    """Weighted employment LEVEL (%) by event time on the balanced sub-panel of
    parents observed at every e in `window`. Returns (profile, n_persons)."""
    d = df[df.e.isin(window)].copy()
    d["pid"] = d["release"].astype(str) + "|" + d["p201p"].astype(str)
    present = d.groupby("pid")["e"].apply(lambda s: set(window).issubset(set(s)))
    keep = set(present[present].index)
    b = d[d["pid"].isin(keep)]
    rows = []
    for e in window:
        s = b[b.e == e]
        lvl = 100 * np.average(s["emp"].values, weights=s["w"].values) if s["w"].sum() > 0 else np.nan
        rows.append({"e": e, "level": lvl})
    return pd.DataFrame(rows), len(keep)


def make_figure(pool: pd.DataFrame) -> None:
    pm, nm = _balanced_levels(pool[pool.group == "madre"], BAL_WINDOW)
    pf, nf = _balanced_levels(pool[pool.group == "padre"], BAL_WINDOW)
    pm.to_csv(DATA / "panel_evento_hijo_empleo_profile_madre.csv", index=False)
    pf.to_csv(DATA / "panel_evento_hijo_empleo_profile_padre.csv", index=False)
    rels = sorted(pool.release.unique())

    print(f"\nreleases pooled ({len(rels)}); balanced window {BAL_WINDOW}")
    print(f"MADRE (n={nm}):  " + "  ".join(f"e{int(r.e):+d}={r.level:.1f}%" for _, r in pm.iterrows()))
    print(f"PADRE (n={nf}):  " + "  ".join(f"e{int(r.e):+d}={r.level:.1f}%" for _, r in pf.iterrows()))

    fs.use()
    fig, ax = fs.fig_ax()
    W = pm.dropna(subset=["level"]); M = pf.dropna(subset=["level"])
    # the birth-year obs (e=0, child age 0) and the year before are GESTATION: the
    # mother was pregnant, so employment is already affected before the child
    # "exists" as age 0. The clean pre-baseline is therefore e=-2, NOT e=-1.
    ax.axvspan(-1, 0, color=fs.GOLD, alpha=0.12, zorder=0)
    fs.halo_label(ax, -0.5, 49.0, "embarazo / nacimiento", dy=0, fs=8, color=fs.GREY)
    base = W.loc[W.e == -2, "level"].iloc[0]            # clean pre-pregnancy baseline
    ax.axhline(base, color=fs.CRANBERRY, lw=1.0, ls=(0, (4, 3)), alpha=0.55, zorder=1)
    fs.halo_label(ax, BAL_WINDOW[0], base, f"base pre-embarazo {base:.0f}%", dy=2.2, fs=8, color=fs.CRANBERRY)
    ax.plot(M.e, M.level, "-o", color=fs.NAVY, lw=2.4, ms=5.2, mfc="white",
            mec=fs.NAVY, mew=1.3, zorder=5)
    ax.plot(W.e, W.level, "-o", color=fs.CRANBERRY, lw=2.4, ms=5.2, mfc="white",
            mec=fs.CRANBERRY, mew=1.3, zorder=5)
    fs.end_labels(ax, [("Padre", M.level.iloc[-1], fs.NAVY),
                       ("Madre", W.level.iloc[-1], fs.CRANBERRY)],
                  x_end=BAL_WINDOW[-1], gap=4.0, fs=9, dx=0.18)
    # penalty vs the clean pre-pregnancy baseline (e=-2), measured at the birth-year trough
    w0 = W.loc[W.e == 0, "level"].iloc[0]
    pen = w0 - base
    ax.annotate("", xy=(0, w0), xytext=(0, base),
                arrowprops=dict(arrowstyle="<->", color=fs.CRANBERRY, lw=1.2, alpha=0.8))
    fs.halo_label(ax, 0.06, (w0 + base) / 2, f"{pen:+.0f} pp", dy=0, fs=9, color=fs.CRANBERRY)
    fs.halo_label(ax, 0, w0, f"{w0:.0f}%", dy=-4.0, fs=9, color=fs.CRANBERRY)
    ax.set_xlim(BAL_WINDOW[0] - 0.4, BAL_WINDOW[-1] + 0.9)
    ax.set_xticks(BAL_WINDOW)
    ax.set_ylim(45, 100)
    ax.set_xlabel("Anios desde el nacimiento del hijo  (0 = nacimiento; -1 y 0 = embarazo)")
    ax.set_ylabel("% ocupado (misma persona seguida en el panel)")
    fs.statbox(ax, [
        "Mismas personas seguidas en 5 olas (panel balanceado).",
        f"Brecha de genero: el padre ~{M.level.mean():.0f}%, la madre {W.level.min():.0f}-{W.level.max():.0f}%.",
        "El ano 0 (y -1) es embarazo: la base limpia es e=-2.",
        f"Penalidad madre vs pre-embarazo: {pen:+.0f}pp. El padre no se mueve.",
        f"n={nm} madres, {nf} padres ({len(rels)} releases solapados).",
    ], loc="lower left")
    fs.source(fig, "Fuente: ENAHO Panel, releases 2012-2016 a 2019-2023 (INEI). Misma persona seguida (conglome+vivienda+"
                   "p201p via codperso); nacimiento = hijo(a) de 0 anios en el hogar; jefa/conyuge 18-45 (madre) / 18-55 "
                   "(padre). % ocupado=ocu500, ponderado por facpanel. Balanceado e in [-2,+2]; e=-1/0 = gestacion, base "
                   "limpia e=-2. ENAHO no observa el embarazo (solo edad del hijo): el ancla es el ano de nacimiento.")
    fig.tight_layout()
    for e in ("png", "pdf"):                # png first; pdf may be locked by a viewer
        try:
            fig.savefig(FIG / f"fig_evento_hijo_empleo_panel.{e}", dpi=200, bbox_inches="tight")
        except PermissionError:
            print(f"  [skip .{e}: file locked -- close the viewer and rerun]")
    print("\nOK -> fig_evento_hijo_empleo_panel.png/.pdf")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--release", default=None, help="process a single release dir, e.g. 2023_912")
    ap.add_argument("--rebuild", action="store_true")
    a = ap.parse_args()
    if a.release:
        pool = process_release(RAWP / a.release)
        if not pool.empty:
            pool.to_csv(CSV, index=False)
    elif CSV.exists() and not a.rebuild:
        pool = pd.read_csv(CSV)
    else:
        pool = build()
    if pool is not None and not pool.empty:
        make_figure(pool)
    else:
        print("no events found")


if __name__ == "__main__":
    main()
