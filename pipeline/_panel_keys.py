"""
panel_keys.py
=============
Centralized, spelling-tolerant detection of ENAHO Panel longitudinal keys, balanced
membership flags and weights. INEI renamed these EVERY few releases; this module is
the single place that knows all the spellings so the analysis scripts don't hardcode.

Observed naming drift across releases (verified 2026-06-19/20):

  balanced membership flag (==1 in window):
    hpan0711   (2011 release)          hpan + 4 digits
    hpan1216   (2016 release)
    hpanel_1519 / hpanel_1519s (2019+) hpanel + _ + 4 digits (+ optional 's' subsample)

  longitudinal weight (window):
    fac_panel0711 (2011-2016)          fac_panel + digits
    facpanel1317  (2017)               facpanel + digits
    facpan1519    (2019+)              facpan + digits

  per-wave cross-sectional weight:
    fac_07        (2011 release)
    factor07_15   (2015+)              and bare factor07 for the terminal wave

  longitudinal anchor (constant across waves):
    cong+vivi+num_hog  (2011, 2015)    a constant panel household number
    conglome+vivienda  (2016+)         the DWELLING (hogar_NN is per-wave)

All helpers take a set/dict of LOWER-CASE column names.
"""
from __future__ import annotations

import re

# Membership-flag naming drifts across releases (verified 2026):
#   hpan0711 / hpan1216           (2011-2016)  hpan + 4 digits
#   hpanel_1519 / hpanel_1519s    (2019)       hpanel + _ + 4 digits (+ 's' subsample)
#   hpanel_18_22 / hpanel_18_22s  (2022-2023)  hpanel + _YY_YY ; multi-year window
#                                              ONLY exists with the 's' suffix here
# So 's' is NOT reliably a subsample marker -- we keep both spellings and prefer the
# non-'s' flag when a window has both. Valid windows are cross-checked against the
# longitudinal weights (lweight_col), which exist for every real window.
FLAG_RE = re.compile(r"^hpan(?:el)?_?(\d{2})_?(\d{2})(s?)$")  # -> (yy0, yy1, 's'?)
# Household/dwelling anchor schemes, most-specific first. Sumaria carries the panel
# household number num_hog; the person modules (M03/04/05) key the dwelling by
# cong+vivi only (no num_hog) -- hence the cong+vivi fallback.
ANCHOR_SETS = [["cong", "vivi", "num_hog"], ["conglome", "vivienda"], ["cong", "vivi"]]


def membership_flags(cols_lower) -> dict:
    """Map window-digits (YYYY) -> {flag_col: is_subsample}. Keeps all spellings."""
    out = {}
    for c in cols_lower:
        m = FLAG_RE.match(c)
        if m:
            win = m.group(1) + m.group(2)
            out.setdefault(win, {})[c] = bool(m.group(3))
    return out


def _best_flag(flagdict: dict) -> str:
    """Prefer a non-'s' flag, else accept the 's' one."""
    nons = [c for c, sub in flagdict.items() if not sub]
    return nons[0] if nons else next(iter(flagdict))


def longest_window(cols_lower) -> tuple[str, str]:
    """Return (window_digits, flag_col) for the longest balanced window, or ('', '')."""
    flags = membership_flags(cols_lower)
    if not flags:
        return "", ""
    span = lambda w: int(w[2:]) - int(w[:2])
    win = max(flags, key=span)
    return win, _best_flag(flags[win])


def window_years(window: str) -> list[int]:
    y0, y1 = 2000 + int(window[:2]), 2000 + int(window[2:])
    return list(range(y0, y1 + 1))


def lweight_col(cols_lower, window: str) -> str | None:
    """Longitudinal (panel) weight column for a window, across spellings."""
    for cand in (f"fac_panel{window}", f"facpanel{window}", f"facpan{window}"):
        if cand in cols_lower:
            return cand
    return None


def xsec_weight_col(cols_lower, yy: str) -> str | None:
    """Per-wave cross-sectional weight column for 2-digit year `yy`."""
    for cand in (f"fac_{yy}", f"factor07_{yy}"):
        if cand in cols_lower:
            return cand
    if "factor07" in cols_lower:                       # bare terminal-wave weight
        return "factor07"
    return None


def anchors(cols_lower) -> list[str]:
    """Constant longitudinal anchor columns present, normalized scheme."""
    for s in ANCHOR_SETS:
        if all(a in cols_lower for a in s):
            return s
    return []


# --- person-level panel (M05/03/04 etc.) ---------------------------------- #
# The PERSON longitudinal key is the dwelling anchor + p201p (stable person-panel
# id). Person balanced-membership flag drifts perpanel<win> / perpan<win> /
# perpanel_<win> (+ 's' subsamples). The person weight is the HOUSEHOLD
# longitudinal weight fac_panel<win> carried onto persons (lweight_col handles its
# spellings). Per-wave person cross-sectional weight is fac5_NN (M05's own) or
# facpob_NN (population).
PFLAG_RE = re.compile(r"^perpane?l?_?(\d{2})_?(\d{2})(s?)$")  # same drift as household flags


def person_anchors(cols_lower) -> list[str]:
    base = anchors(cols_lower)
    if "p201p" in cols_lower:
        return base + ["p201p"]
    if "codperso" in cols_lower:
        return base + ["codperso"]
    return base


def person_flags(cols_lower) -> dict:
    """window-digits (YYYY) -> {flag_col: is_subsample}. Keeps all spellings."""
    out = {}
    for c in cols_lower:
        m = PFLAG_RE.match(c)
        if m:
            out.setdefault(m.group(1) + m.group(2), {})[c] = bool(m.group(3))
    return out


def longest_person_window(cols_lower) -> tuple[str, str]:
    flags = person_flags(cols_lower)
    if not flags:
        return "", ""
    win = max(flags, key=lambda w: int(w[2:]) - int(w[:2]))
    return win, _best_flag(flags[win])


def pwave_weight_col(cols_lower, yy: str) -> str | None:
    """Per-wave person cross-sectional weight (fac5_NN, else facpob_NN, else fac_NN)."""
    for cand in (f"fac5_{yy}", f"facpob_{yy}", f"fac_{yy}", f"factor07_{yy}"):
        if cand in cols_lower:
            return cand
    return None


def dwelling_key(cols_lower) -> list[str]:
    """The 2-column dwelling key (conglome+vivienda or cong+vivi), for merges."""
    for s in (["conglome", "vivienda"], ["cong", "vivi"]):
        if all(a in cols_lower for a in s):
            return s
    return []


def hh_panel_weight(release_dir, win: str):
    """Household longitudinal weight from the release's Sumaria, keyed by the dwelling
    key, for person files that ship the membership flag but NOT the panel weight
    (e.g. 2019 salud). Returns a DataFrame [<dwelling cols>, 'w_panel_hh'] or None.
    The Sumaria's dwelling key matches the person file's (same conglome/vivienda).
    """
    import pyreadstat
    from pathlib import Path
    d = Path(release_dir)
    sums = [p for p in d.glob("*.dta") if "sumaria" in p.name.lower() and "12g" not in p.name.lower()]
    if not sums:
        return None
    _, m = pyreadstat.read_dta(str(sums[0]), metadataonly=True)
    cl = {c.lower(): c for c in m.column_names}
    wcol = lweight_col(cl, win)
    dk = dwelling_key(cl)
    if not wcol or not dk:
        return None
    cols = [cl[a] for a in dk] + [cl[wcol]]
    df, _ = pyreadstat.read_dta(str(sums[0]), usecols=cols)
    df.columns = [c.lower() for c in df.columns]
    df = df.rename(columns={cl[wcol].lower(): "w_panel_hh"})
    return df
