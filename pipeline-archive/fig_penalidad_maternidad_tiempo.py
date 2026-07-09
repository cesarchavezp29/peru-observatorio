"""
fig_penalidad_maternidad_tiempo.py - La penalidad de la maternidad en el empleo (M02 x M05)
================================================================================================
MULTI-MODULO (M02 composicion del hogar x M05 empleo): tasa de ocupacion de adultos 25-45 por
sexo y por presencia de un nino pequeno (0-5) en el hogar, 2004-2025.

Pregunta: tener un nino pequeno en casa deprime el empleo de las mujeres pero no el de los
hombres? Cambio esa brecha con el tiempo?

CONSTRUCCION (anclado en M02 persona):
  - M02 (miembros): p207 sexo (1=hombre, 2=mujer), p208a edad. has_child_u6 = el hogar tiene
    al menos un miembro de 0-5 anios (llave-hogar conglome+vivienda+hogar).
  - M05 (empleo): ocu500 OCUPADO=1, fac500a peso del modulo empleo. Merge por llave-persona
    (conglome+vivienda+hogar+codperso).
  - Universo = 25-45 (anios primos de crianza y trabajo). Tasa ponderada por fac500a.
CODIGOS VERIFICADOS estables (verify_codes.py): p207 (1=hombre/2=mujer), ocu500 (1=ocupado),
p208a edad. CAVEAT: "nino en el hogar" es proxy de hogar-con-crianza (para 25-45 casi siempre
hijo propio, pero hogares extensos pueden incluir hermano/nieto menor); no usa parentesco p203.
El CSV es datasets/penalidad_maternidad_tiempo.csv. Un plot. Run: python ... [--rebuild]
"""
from __future__ import annotations
from pathlib import Path
import sys
import numpy as np, pandas as pd
import figstyle as fs

ROOT = Path(__file__).resolve().parents[1]; RAW = ROOT / "raw"
FIG = ROOT / "figures" / "07_empleo"; FIG.mkdir(parents=True, exist_ok=True)
CSV = ROOT / "datasets" / "penalidad_maternidad_tiempo.csv"
PK = ["conglome", "vivienda", "hogar", "codperso"]; HK = ["conglome", "vivienda", "hogar"]
YEARS = list(range(2004, 2026))


def num(s):
    return pd.to_numeric(s, errors="coerce")


def rd(folder, mod, year, cols):
    import pyreadstat
    fp = RAW / folder / f"enaho-{year}-{mod}.dta"
    if not fp.exists():
        return None
    have = pyreadstat.read_dta(str(fp), metadataonly=True)[1].column_names
    cl = {c.lower(): c for c in have}
    d, _ = pyreadstat.read_dta(str(fp), encoding="latin1", usecols=[cl[c] for c in cols if c in cl])
    d.columns = [c.lower() for c in d.columns]
    return d


def key(d, keys):
    return d[keys].apply(lambda col: num(col).astype("Int64").astype(str)).agg("-".join, axis=1)


def wr(mask, base, w):
    b = base
    return 100 * w[mask & b].sum() / w[b].sum() if w[b].sum() > 0 else np.nan


if CSV.exists() and "--rebuild" not in sys.argv:
    p = pd.read_csv(CSV)
else:
    rows = []
    for y in YEARS:
        m2 = rd("miembros", "02", y, PK + ["p207", "p208a"])
        m5 = rd("empleo_ingreso", "05", y, PK + ["ocu500", "fac500a"])
        if m2 is None or m5 is None:
            continue
        m2["hk"] = key(m2, HK); m2["pk"] = key(m2, PK)
        childhh = m2.assign(a=num(m2["p208a"])).groupby("hk")["a"].apply(lambda s: bool(s.between(0, 5).any()))
        m2["haschild"] = m2["hk"].map(childhh)
        m5["pk"] = key(m5, PK)
        d = m2.merge(m5.drop_duplicates("pk")[["pk", "ocu500", "fac500a"]], on="pk", how="left")
        a = num(d["p208a"]); w = num(d["fac500a"]).fillna(0); emp = (num(d["ocu500"]) == 1)
        fem = (num(d["p207"]) == 2); male = (num(d["p207"]) == 1); prime = a.between(25, 45)
        hc = d["haschild"].fillna(False).astype(bool)
        rec = {"year": y,
               "w_kid": wr(emp, prime & fem & hc, w), "w_nokid": wr(emp, prime & fem & ~hc, w),
               "m_kid": wr(emp, prime & male & hc, w), "m_nokid": wr(emp, prime & male & ~hc, w),
               "n": int((prime).sum())}
        rec["pen_w"] = rec["w_kid"] - rec["w_nokid"]; rec["pen_m"] = rec["m_kid"] - rec["m_nokid"]
        rows.append(rec)
        print(f"{y}: W+kid {rec['w_kid']:4.1f} W-kid {rec['w_nokid']:4.1f} (pen {rec['pen_w']:+5.1f}) | "
              f"M+kid {rec['m_kid']:4.1f} M-kid {rec['m_nokid']:4.1f} (pen {rec['pen_m']:+5.1f})")
    p = pd.DataFrame(rows).sort_values("year")
    p.to_csv(CSV, index=False)

fs.use()
fig, ax = fs.fig_ax()
specs = [("Hombre, sin nino pequeno", "m_nokid", fs.NAVY, (0, (4, 2))),
         ("Hombre, con nino pequeno", "m_kid", fs.NAVY, "-"),
         ("Mujer, sin nino pequeno", "w_nokid", fs.CRANBERRY, (0, (4, 2))),
         ("Mujer, con nino pequeno", "w_kid", fs.CRANBERRY, "-")]
labels = []
for name, col, c, ls in specs:
    s = p.dropna(subset=[col])
    ax.plot(s.year, s[col], ls=ls, marker="o", color=c, lw=2.2, ms=3.4, mfc="white", mec=c, mew=1.0, zorder=5)
    labels.append((f"{name}  {s[col].iloc[-1]:.0f}%", s[col].iloc[-1], c))
fs.end_labels(ax, labels, x_end=p.year.max(), gap=3.2, fs=7.8)
ax.axvspan(2019.6, 2020.4, color=fs.GREY, alpha=0.10, zorder=0)
ax.set_xlim(2003.4, 2031); ax.set_xticks(range(2004, 2026, 3)); ax.set_ylim(55, 100)
ax.set_ylabel("% ocupado, 25-45 anios"); ax.set_xlabel("")
fs.statbox(ax, [
    "Un nino pequeno en casa BAJA el empleo de la mujer",
    "(~13 pp en 2025) pero lo SUBE en el hombre (efecto",
    "proveedor). La penalidad de la maternidad ni siquiera",
    "se redujo: crecio de 8 a 13 pp porque suben las mujeres",
    "sin ninos, no las madres. M02 hogar x M05 empleo.",
], loc="lower left")
fs.source(fig, "Fuente: ENAHO 2004-2025 (INEI), modulo 02 (Miembros: sexo, edad, nino 0-5 en el hogar) x modulo 05 "
               "(Empleo, ocu500). % ocupado 25-45 por sexo y presencia de nino pequeno, ponderado por fac500a.")
fig.tight_layout()
for e in ("pdf", "png"):
    fig.savefig(FIG / f"fig_penalidad_maternidad_tiempo.{e}", dpi=200, bbox_inches="tight")
print("OK -> fig_penalidad_maternidad_tiempo.pdf")
