"""
fig_calidad_vivienda.py - Calidad de la vivienda 2004-2025 (M01): piso de tierra + hacinamiento
================================================================================================
Modulo 01 (Vivienda y hogar). Dos carencias materiales, ambas con codigo estable:
  - PISO DE TIERRA: p103 (material del piso) == 6 ('tierra'). Codigos 1-7 estables 2004-2025.
  - HACINAMIENTO (def. INEI): mas de 3 personas por habitacion usada para dormir
    = mieperho / p104a > 3.
(Las PAREDES p102 NO se usan: el codigo cambia -en 2004 cod 3='adobe o tapia', en 2025 se
separan adobe=3 y tapia=4-, rompe la serie. Ver docs/INCONSISTENCIES.md.)
Ponderado por factor07. Bajan ambas -> mejora del estandar material de vida.
Run: python fig_calidad_vivienda.py
"""
from __future__ import annotations
from pathlib import Path
import numpy as np, pandas as pd
import figstyle as fs
import enaho_codes as ec

ROOT = Path(__file__).resolve().parents[1]; RAW = ROOT / "raw"
FIG = ROOT / "figures" / "06_vivienda"; FIG.mkdir(parents=True, exist_ok=True)
DATA = ROOT / "datasets"


def _load(path):
    try:
        import pyreadstat
        df, _ = pyreadstat.read_dta(str(path), encoding="latin1")
    except Exception:
        df = pd.read_stata(path, convert_categoricals=False)
    df.columns = [c.lower() for c in df.columns]
    return df


def L(year):
    p = RAW / "vivienda_hogar" / f"enaho-{year}-01.dta"
    return _load(p) if p.exists() else None


def L_su(year):
    p = RAW / "sumaria" / f"enaho-{year}-34.dta"
    return _load(p) if p.exists() else None


def wshare(mask, w):
    mask = np.asarray(mask, float); w = np.asarray(w, float)
    ok = np.isfinite(mask) & np.isfinite(w)
    return 100 * np.average(mask[ok], weights=w[ok]) if ok.any() else np.nan


def hhkey(d):
    return (d["conglome"].astype(str).str.zfill(6) + d["vivienda"].astype(str).str.zfill(3)
            + d["hogar"].astype(str).str.zfill(2))


rows = []
for y in ec.years():
    df = L(y); su = L_su(y)
    if df is None or "p103" not in df.columns:
        continue
    n = lambda c: pd.to_numeric(df[c], errors="coerce") if c in df.columns else pd.Series(np.nan, index=df.index)
    w = n("factor07")
    # mieperho viene de Sumaria (NO esta en M01) -> merge por llave-hogar
    if su is not None and "mieperho" in su.columns:
        su["hh"] = hhkey(su); df["hh"] = hhkey(df)
        mie = df["hh"].map(su.set_index("hh")["mieperho"].pipe(pd.to_numeric, errors="coerce"))
    else:
        mie = pd.Series(np.nan, index=df.index)
    p103 = n("p103")
    tierra = (p103 == 6).where(p103.notna())               # EXCLUIR NaN (no contar como 'no-tierra')
    rooms = n("p104a")
    valid_h = rooms.notna() & (rooms >= 1) & mie.notna()
    hac = ((mie / rooms) > 3).where(valid_h)
    rec = {"year": y, "piso_tierra": wshare(tierra, w),
           "hacinamiento": wshare(hac, w) if valid_h.any() else np.nan,
           "p103_missing": float(p103.isna().mean())}
    rows.append(rec)
    print(f"{y}: piso tierra {rec['piso_tierra']:4.1f}%  hacinamiento {rec['hacinamiento']:4.1f}%  "
          f"(p103 NaN {rec['p103_missing']:.0%})")

p = pd.DataFrame(rows)
p.to_csv(DATA / "calidad_vivienda_2004_2025.csv", index=False)

fig, ax = fs.fig_ax()
ax.plot(p.year, p.piso_tierra, "-o", color=fs.NAVY, lw=2.4, ms=4, mfc="white", mec=fs.NAVY, mew=1.4, zorder=5)
ends = [(f"Piso de tierra  {p.piso_tierra.iloc[-1]:.0f}%", p.piso_tierra.iloc[-1], fs.NAVY)]
if "hacinamiento" in p.columns:
    ax.plot(p.year, p.hacinamiento, "-o", color=fs.CRANBERRY, lw=2.4, ms=4, mfc="white", mec=fs.CRANBERRY, mew=1.4, zorder=5)
    ends.append((f"Hacinamiento  {p.hacinamiento.iloc[-1]:.0f}%", p.hacinamiento.iloc[-1], fs.CRANBERRY))
fs.end_labels(ax, ends, x_end=p.year.iloc[-1], fs=9.5)
ax.set_xlim(2003.5, 2031)
ax.set_ylim(0, max(40, p[["piso_tierra"]].max().max() * 1.15))
ax.set_xticks(range(2004, 2026, 2))
ax.set_ylabel("% de hogares")
ax.set_xlabel("")
fs.statbox(ax, [
    "Carencias materiales de la vivienda (ambas a la baja):",
    "el piso de tierra y el hacinamiento (>3 personas",
    "por cuarto, def. INEI) caen con el desarrollo.",
], loc="upper right")
fs.source(fig, "Fuente: ENAHO 2004-2025 (INEI), modulo 01. Piso p103==tierra; hacinamiento mieperho/p104a>3. Ponderado por factor07.")
fig.tight_layout()
for e in ("pdf", "png"):
    fig.savefig(FIG / f"fig_calidad_vivienda.{e}", dpi=200, bbox_inches="tight")
print("OK -> fig_calidad_vivienda.pdf")
