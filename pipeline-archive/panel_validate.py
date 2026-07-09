"""
panel_validate.py
=================
VALIDATION GATE for the ENAHO Panel. For each panel release's sumaria, compute
per-wave monetary poverty TWO ways and compare against (a) OFFICIAL INEI national
poverty and (b) OUR cross-section ENAHO estimate (datasets/official_poverty_
replication.csv — already validated to match official to 0.0pp):

  * `xsec_poverty_pct` = FULL per-wave sample weighted by the PER-WAVE
    CROSS-SECTIONAL weight (fac_NN in old releases, factor07_NN/factor07 in newer),
    person-expanded by mieperho. This is the correct way to reproduce an annual
    marginal -> matches official to 0.0pp (the data validation).
  * `balanced_poverty_pct` = the BALANCED survivor sub-panel weighted by the
    LONGITUDINAL weight fac_panel<window>. This is NOT meant to equal the
    cross-section; the gap MEASURES survivor composition (panel households are
    poorer / escape slower). Reported as a caveat, not a target.

LESSON (2026-06-19): an earlier version used the longitudinal weight on the
balanced subsample to reproduce annual poverty and saw a spurious ~2.6pp "drift".
That was a weight/sample mismatch, not a data problem -- the per-wave
cross-sectional weight reproduces official exactly. Use the right weight for the
question: fac_NN/factor07_NN for marginals, fac_panel<window> for dynamics.

Run:  py -3.14 panel_validate.py            # every downloaded panel sumaria
Output: datasets/panel_validation_poverty.csv + console table.
"""
from __future__ import annotations

import csv
import re
from pathlib import Path

import pandas as pd
import pyreadstat

import panel_codes as pc
import panel_keys as pk

ROOT = Path(__file__).resolve().parents[1]
PANEL = ROOT / "raw" / "panel"
DATA = ROOT / "datasets"
OFFICIAL = DATA / "official_poverty_replication.csv"


def _official() -> dict:
    """year -> (official_poverty, our_cross_section_poverty)."""
    out = {}
    if not OFFICIAL.exists():
        return out
    for r in csv.DictReader(open(OFFICIAL, encoding="utf-8")):
        y = int(float(r["year"]))
        off = r.get("official_poverty") or r.get("poverty_pct")
        ours = r.get("poverty_pct")
        out[y] = (float(off) if off else None, float(ours) if ours else None)
    return out


def _sumaria_path(release: int) -> Path | None:
    code = pc.PANEL_CODE[release]
    d = PANEL / f"{release}_{code}"
    if not d.exists():
        return None
    cands = [p for p in d.glob("*.dta") if "sumaria" in p.name.lower() and "12g" not in p.name.lower()]
    return cands[0] if cands else None


def validate_release(release: int, official: dict) -> list[dict]:
    path = _sumaria_path(release)
    if not path:
        return []
    _, meta = pyreadstat.read_dta(str(path), metadataonly=True)
    cl = {c.lower(): c for c in meta.column_names}
    win, flag = pk.longest_window(cl)
    if not win:
        return []
    years = pk.window_years(win)
    yy = [f"{y % 100:02d}" for y in years]

    pw_col = pk.lweight_col(cl, win)
    need = []
    if flag:
        need.append(cl[flag])
    if pw_col:
        need.append(cl[pw_col])
    for s in yy:
        for nm in (f"pobreza_{s}", f"mieperho_{s}", f"fac_{s}", f"factor07_{s}"):
            if nm in cl:
                need.append(cl[nm])
    if "factor07" in cl:
        need.append(cl["factor07"])
    df, _ = pyreadstat.read_dta(str(path), usecols=list(dict.fromkeys(need)))

    bal_flag = cl.get(flag) if flag else None
    fac_panel = cl.get(pw_col) if pw_col else None
    rows = []
    for y, s in zip(years, yy):
        pc_ = cl.get(f"pobreza_{s}")
        if not pc_:
            continue
        mp_ = cl.get(f"mieperho_{s}")
        miep = df[mp_].fillna(1) if mp_ else 1.0
        poor = df[pc_].isin([1, 2]).astype(float)
        valid = df[pc_].notna()

        # (1) annual marginal: FULL sample + per-wave cross-sectional weight
        wcol = pk.xsec_weight_col(cl, s)
        xsec = None
        if wcol:
            w = (df[cl[wcol]].fillna(0) * miep)[valid]
            xsec = round(float((poor[valid] * w).sum() / w.sum()) * 100, 1)

        # (2) balanced survivors + longitudinal weight (composition diagnostic)
        balanced = None
        if bal_flag and fac_panel:
            b = (df[bal_flag] == 1) & valid
            w = (df[fac_panel].fillna(0) * miep)[b]
            if w.sum() > 0:
                balanced = round(float((poor[b] * w).sum() / w.sum()) * 100, 1)

        off, ours = official.get(y, (None, None))
        rows.append({
            "release": release, "window": win, "wave": y,
            "xsec_poverty_pct": xsec,
            "balanced_poverty_pct": balanced,
            "official_poverty_pct": off,
            "cross_section_enaho_pct": ours,
            "xsec_gap_vs_official": round(xsec - off, 1) if (xsec is not None and off is not None) else None,
            "survivor_gap": round(balanced - xsec, 1) if (balanced is not None and xsec is not None) else None,
            "n_hh_balanced": int((df[bal_flag] == 1).sum()) if bal_flag else None,
        })
    return rows


def main() -> None:
    official = _official()
    all_rows = []
    for rel in pc.releases():
        rows = validate_release(rel, official)
        all_rows += rows

    if not all_rows:
        print("no panel sumaria downloaded yet")
        return

    out = DATA / "panel_validation_poverty.csv"
    cols = ["release", "window", "wave", "xsec_poverty_pct",
            "official_poverty_pct", "cross_section_enaho_pct",
            "xsec_gap_vs_official", "balanced_poverty_pct", "survivor_gap",
            "n_hh_balanced"]
    with open(out, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=cols)
        w.writeheader()
        w.writerows(all_rows)

    print(f"\n{'rel':>5}{'wave':>6}{'xsec':>7}{'offic':>7}{'gap':>6}   "
          f"{'balanced':>9}{'surv.gap':>9}   n_hh")
    print("-" * 64)
    for r in all_rows:
        off = r["official_poverty_pct"]
        xs = r["xsec_poverty_pct"]
        gap = r["xsec_gap_vs_official"]
        bal = r["balanced_poverty_pct"]
        sg = r["survivor_gap"]
        f1 = lambda v, suf="%": (f"{v:.1f}{suf}" if v is not None else "NA")
        print(f"{r['release']:>5}{r['wave']:>6}{f1(xs):>7}{f1(off):>7}"
              f"{(f'{gap:+.1f}' if gap is not None else 'NA'):>6}   "
              f"{f1(bal):>9}{(f'{sg:+.1f}' if sg is not None else 'NA'):>9}   "
              f"{r['n_hh_balanced'] or 'NA'}")
    gaps = [abs(r["xsec_gap_vs_official"]) for r in all_rows
            if r["xsec_gap_vs_official"] is not None]
    sgs = [r["survivor_gap"] for r in all_rows if r["survivor_gap"] is not None]
    if gaps:
        print(f"\nDATA CHECK: mean |xsec gap vs official| = {sum(gaps)/len(gaps):.2f}pp "
              f"over {len(gaps)} waves (should be ~0).")
    if sgs:
        rng = f"{min(sgs):+.1f} to {max(sgs):+.1f}"
        print(f"SURVIVOR COMPOSITION: (balanced - xsec) ranges {rng}pp, sign varies by "
              f"release (longitudinal weight is calibrated to the window, not annual "
              f"marginals) - a composition diagnostic, NOT a data error.")
    print(f"wrote {out}")


if __name__ == "__main__":
    main()
