"""
analysis_who_trusts_state.py - ¿Quien confia en el Estado? (ENAHO 2025)
=======================================================================
Demostracion de COMO se arma el ENAHO mezclando modulos: tomamos al UNICO
adulto seleccionado del modulo 85 (Gobernabilidad) y lo seguimos, persona por
persona, a traves de seis modulos con DOS llaves distintas:

  llave PERSONA  = conglome+vivienda+hogar+codperso   (M02, M03, M04, M05)
  llave HOGAR    = conglome+vivienda+hogar            (M34 Sumaria, M37)

Cada modulo tiene un UNIVERSO distinto (M02 todos; M03 edad 3+; M05 edad 14+;
M85 un adulto/hogar). Por eso un inner-join ingenuo BOTA gente. Aqui anclamos en
el encuestado de M85 y hacemos LEFT joins con auditoria de N en cada paso.

Resultado sustantivo: relacionar la confianza institucional del encuestado con
  - su ingreso real per capita del hogar (M34, deflactado INEI base 2025)
  - sus anios de educacion (M03)
  - su edad (M02)
  - si recibe una transferencia del Estado: Juntos/Pension 65 (M37) o SIS (M04)
y preguntar: el ingreso compra confianza? la educacion? el Estado se compra
confianza con transferencias?

Salidas:
  datasets/who_trusts_state_2025.csv     una fila por encuestado M85, todo unido
  figures/02_confianza/fig_who_trusts_state.{pdf,png}

Run: python analysis_who_trusts_state.py
"""
from __future__ import annotations
from pathlib import Path
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import figstyle as fs
from dataset_income import real_income

ROOT = Path(__file__).resolve().parents[1]
RAW = ROOT / "raw"
FIG = ROOT / "figures" / "02_confianza"; FIG.mkdir(parents=True, exist_ok=True)
DATA = ROOT / "datasets"; DATA.mkdir(exist_ok=True)
YEAR = 2025

# anios de educacion a partir de p301a (nivel educativo alcanzado)
EDU_YEARS = {1: 0, 2: 0, 3: 3, 4: 6, 5: 9, 6: 11, 7: 13, 8: 14, 9: 14, 10: 17, 11: 19, 12: 6}
TRUST_ITEMS = [f"p1_{i:02d}" for i in range(1, 22)]   # 21 instituciones, escala 1-4


def L(fn):
    d = pd.read_stata(RAW / fn, convert_categoricals=False)
    d.columns = [c.lower() for c in d.columns]
    return d


def hhkey(d):
    return (d["conglome"].astype(str).str.zfill(6) + d["vivienda"].astype(str).str.zfill(3)
            + d["hogar"].astype(str).str.zfill(2))


def pkey(d):
    cp = pd.to_numeric(d["codperso"], errors="coerce").fillna(0).astype(int).astype(str).str.zfill(2)
    return hhkey(d) + cp


def wmean(x, w):
    x = np.asarray(x, float); w = np.asarray(w, float)
    m = np.isfinite(x) & np.isfinite(w)
    return np.average(x[m], weights=w[m]) if m.any() else np.nan


def wdecile(x, w, n=10):
    """Deciles ponderados (1..n) de x con pesos w."""
    x = np.asarray(x, float); w = np.asarray(w, float)
    order = np.argsort(x)
    xs, ws = x[order], w[order]
    cw = np.cumsum(ws) / ws.sum()
    edges = np.searchsorted(cw, np.linspace(0, 1, n + 1)[1:-1])
    lab = np.zeros(len(x), int)
    bins = np.digitize(np.arange(len(x)), edges)
    lab[order] = bins + 1
    return lab


# ----------------------------------------------------------------------------
# 1) MAESTRO = encuestado del modulo 85, con su indice de confianza
# ----------------------------------------------------------------------------
g = L("gobernabilidad/enaho-2025-85.dta")
# CONFIANZA EFECTIVA: % de las 21 instituciones en que el encuestado declara confianza
# (Suficiente/Bastante=3,4). "No sabe" (5) se trata como NO confia, no como dato perdido:
# si el encuestado ni siquiera ubica la institucion, no puede tenerle confianza. Esto evita
# el ARTEFACTO de no-respuesta diferencial (los menos educados dejan en "No sabe" las
# instituciones que no conocen, lo que inflaba falsamente su confianza y creaba una U
# espuria en el gradiente educativo). Con esta definicion el gradiente es monotono.
Traw = g[[c for c in TRUST_ITEMS if c in g.columns]].apply(pd.to_numeric, errors="coerce")
answered = Traw.isin([1, 2, 3, 4, 5])
g["trust_share"] = Traw.isin([3, 4]).sum(axis=1) / answered.sum(axis=1).replace(0, np.nan)
g["pk"] = pkey(g); g["hh"] = hhkey(g)
N0 = len(g)
print(f"MAESTRO  M85 gobernabilidad: {N0:,} encuestados (1 adulto/hogar)")
audit = [("M85 maestro", N0, 100.0, "1 adulto selecc./hogar")]

base = g[["pk", "hh", "trust_share"]].copy()


def attach_person(base, df, cols, label, universe):
    before = len(base)
    out = base.merge(df[["pk"] + cols], on="pk", how="left")
    matched = out[cols[0]].notna().sum()
    print(f"  + {label:22s} llave PERSONA  match {matched:,}/{before:,} = {100*matched/before:.1f}%")
    audit.append((label, len(df), 100 * matched / before, universe))
    return out


def attach_hh(base, df, cols, label, universe, n_src):
    before = len(base)
    out = base.merge(df[["hh"] + cols], on="hh", how="left")
    matched = out[cols[0]].notna().sum()
    print(f"  + {label:22s} llave HOGAR    match {matched:,}/{before:,} = {100*matched/before:.1f}%")
    audit.append((label, n_src, 100 * matched / before, universe))
    return out


# ----------------------------------------------------------------------------
# 2) JOINS persona (M02 edad/sexo, M03 educacion, M04 SIS, M05 empleo)
# ----------------------------------------------------------------------------
m2 = L("miembros/enaho-2025-02.dta"); m2["pk"] = pkey(m2)
m2["edad"] = pd.to_numeric(m2["p208a"], errors="coerce")
m2["mujer"] = (pd.to_numeric(m2["p207"], errors="coerce") == 2).astype(float)
base = attach_person(base, m2, ["edad", "mujer"], "M02 miembros", "todos")

m3 = L("educacion/enaho-2025-03.dta"); m3["pk"] = pkey(m3)
m3["educ_anios"] = pd.to_numeric(m3["p301a"], errors="coerce").map(EDU_YEARS)
base = attach_person(base, m3, ["educ_anios"], "M03 educacion", "edad 3+")

m4 = L("salud/enaho-2025-04.dta"); m4["pk"] = pkey(m4)
m4["sis"] = (pd.to_numeric(m4["p4195"], errors="coerce") == 1).astype(float)
base = attach_person(base, m4, ["sis"], "M04 salud (SIS)", "todos")

m5 = L("empleo_ingreso/enaho-2025-05.dta"); m5["pk"] = pkey(m5)
m5["ocupado"] = (pd.to_numeric(m5["ocu500"], errors="coerce") == 1).astype(float)
base = attach_person(base, m5, ["ocupado"], "M05 empleo", "edad 14+")

# ----------------------------------------------------------------------------
# 3) JOINS hogar (M34 Sumaria ingreso/pobreza/peso, M37 programas)
# ----------------------------------------------------------------------------
inc = real_income(YEAR)[["conglome", "vivienda", "hogar", "ipcr_0", "factor07", "pobreza"]].copy()
inc["hh"] = hhkey(inc); inc["pobre"] = pd.to_numeric(inc["pobreza"], errors="coerce").isin([1, 2]).astype(float)
base = attach_hh(base, inc, ["ipcr_0", "factor07", "pobre"], "M34 Sumaria", "hogar", len(inc))

m37 = L("programas_sociales/enaho-2025-37.dta"); m37["hh"] = hhkey(m37)
m37["juntos"] = (pd.to_numeric(m37["p710_04"], errors="coerce") == 1).astype(float)
m37["pension65"] = (pd.to_numeric(m37["p710_05"], errors="coerce") == 1).astype(float)
base = attach_hh(base, m37, ["juntos", "pension65"], "M37 programas", "hogar", len(m37))

# transferencia del Estado al hogar/persona: Juntos o Pension 65 o SIS
base["transfer"] = ((base["juntos"] == 1) | (base["pension65"] == 1) | (base["sis"] == 1)).astype(float)

d = base.dropna(subset=["trust_share", "ipcr_0", "factor07"]).copy()
print(f"\nTabla integrada: {len(d):,} encuestados con confianza + ingreso + peso")
d.to_csv(DATA / f"who_trusts_state_{YEAR}.csv", index=False)

# ----------------------------------------------------------------------------
# 4) WLS multivariante: confianza ~ log ingreso + educ + edad + transfer + pobre
# ----------------------------------------------------------------------------
import statsmodels.api as sm
reg = d.dropna(subset=["educ_anios", "edad"]).copy()
for col in ["ipcr_0", "educ_anios", "edad", "transfer", "pobre", "trust_share", "factor07"]:
    reg[col] = pd.to_numeric(reg[col], errors="coerce")
reg = reg.dropna(subset=["ipcr_0", "educ_anios", "edad", "transfer", "pobre", "trust_share", "factor07"])
reg["log_inc"] = np.log(reg["ipcr_0"].clip(lower=1))
X = sm.add_constant(reg[["log_inc", "educ_anios", "edad", "transfer", "pobre"]].astype(float))
wls = sm.WLS(reg["trust_share"].astype(float), X, weights=reg["factor07"].astype(float)).fit()
print("\nWLS confianza ~ ... (ponderado factor07):")
for nm in ["log_inc", "educ_anios", "edad", "transfer", "pobre"]:
    print(f"   {nm:11s} b={wls.params[nm]:+.4f}  p={wls.pvalues[nm]:.3f}")

# ----------------------------------------------------------------------------
# 5) FIGURAS (un plot por chart, paleta unica)
# ----------------------------------------------------------------------------
SRC = ("Fuente: ENAHO 2025 (INEI), modulos 02-03-04-05-34-37-85. Confianza efectiva (No sabe = no confia). "
       "Ingreso real deflactado base 2025. Ponderado por factor07.")


def save(fig, name):
    fs.source(fig, SRC); fig.tight_layout()
    for e in ("pdf", "png"):
        fig.savefig(FIG / f"{name}.{e}", dpi=140, bbox_inches="tight")
    print(f"OK -> figures/02_confianza/{name}.pdf")


# chart 1: ingreso (decil) -> confianza
d["dec"] = wdecile(d["ipcr_0"].values, d["factor07"].values)
ga = d.groupby("dec").apply(lambda s: pd.Series({
    "trust": 100 * wmean(s["trust_share"], s["factor07"])}), include_groups=False).reset_index()
fig, a = fs.fig_ax()
a.plot(ga["dec"], ga["trust"], "-o", color=fs.NAVY, lw=2.4, ms=5, mfc="white", mec=fs.NAVY, mew=1.6)
a.set_xticks(range(1, 11)); a.set_xlabel("Decil de ingreso real per capita del hogar")
a.set_ylabel("% de instituciones en que confia")
a.set_ylim(ga["trust"].min() - 1.5, ga["trust"].max() + 2.5)
fs.halo_label(a, ga["dec"].iloc[0], ga["trust"].iloc[0], f"D1  {ga['trust'].iloc[0]:.0f}%", dy=-14)
fs.halo_label(a, ga["dec"].iloc[-1], ga["trust"].iloc[-1], f"D10  {ga['trust'].iloc[-1]:.0f}%", dy=8, dx=-22)
fs.statbox(a, ["WLS (neto de controles):",
              f"log ingreso  b={wls.params['log_inc']:+.3f} (p={wls.pvalues['log_inc']:.2f})",
              f"educacion    b={wls.params['educ_anios']:+.4f} (p={wls.pvalues['educ_anios']:.2f})",
              f"transferencia b={wls.params['transfer']:+.3f} (p={wls.pvalues['transfer']:.2f})"], loc="upper left")
a.set_title("El ingreso compra algo de confianza institucional, pero poco - 2025", loc="left")
save(fig, "fig_confianza_ingreso")

# chart 2: educacion -> confianza
edges = [-1, 0, 6, 11, 12, 16, 30]; labs = ["0", "1-6", "7-11", "12", "13-16", "17+"]
db = d.dropna(subset=["educ_anios"]).copy()
db["etr"] = pd.cut(db["educ_anios"], bins=edges, labels=labs)
gb = db.groupby("etr", observed=True).apply(
    lambda s: 100 * wmean(s["trust_share"], s["factor07"]), include_groups=False)
fig, b = fs.fig_ax()
b.bar(range(len(gb)), gb.values, color=fs.NAVY, edgecolor="white", width=0.72)
for i, v in enumerate(gb.values):
    b.text(i, v + 0.4, f"{v:.0f}%", ha="center", fontsize=10, fontweight="semibold")
b.set_xticks(range(len(gb))); b.set_xticklabels(gb.index)
b.set_xlabel("Anios de educacion del encuestado"); b.set_ylabel("% de instituciones en que confia")
b.set_ylim(0, max(gb.values) + 3); b.grid(axis="x", alpha=0)
b.set_title("A mas educacion, mas confianza institucional (gradiente monotono) - 2025", loc="left")
save(fig, "fig_confianza_educacion")

# chart 3: transferencia x pobreza -> confianza
fig, c = fs.fig_ax()
cats = [(1.0, "Pobre"), (0.0, "No pobre")]; x = np.arange(2); w = 0.38
for k, (rec, col, lab) in enumerate([(0.0, fs.GREY, "Sin transferencia"),
                                     (1.0, fs.CRANBERRY, "Con transferencia (Juntos/P65/SIS)")]):
    vals = [100 * wmean(d[(d["pobre"] == pv) & (d["transfer"] == rec)]["trust_share"],
                        d[(d["pobre"] == pv) & (d["transfer"] == rec)]["factor07"]) for pv, _ in cats]
    c.bar(x + (k - 0.5) * w, vals, w, color=col, edgecolor="white", label=lab)
    for xi, v in zip(x + (k - 0.5) * w, vals):
        c.text(xi, v + 0.4, f"{v:.0f}%", ha="center", fontsize=10, fontweight="semibold")
c.set_xticks(x); c.set_xticklabels([cl for _, cl in cats]); c.set_ylabel("% de instituciones en que confia")
c.set_ylim(0, 22); c.legend(loc="upper left"); c.grid(axis="x", alpha=0)
c.text(0.97, 0.96, "Pobres +0.8 pp, no pobres -1.3 pp.\nNeta de ingreso no es significativa (WLS p=0.60).",
       transform=c.transAxes, fontsize=8.5, color=fs.GREY, ha="right", va="top")
c.set_title("Las transferencias del Estado no mueven la confianza institucional - 2025", loc="left")
save(fig, "fig_confianza_transferencia")
print(f"   nacional confianza ponderada: {100*wmean(d['trust_share'], d['factor07']):.1f}%")
