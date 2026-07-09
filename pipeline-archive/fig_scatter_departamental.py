"""
fig_scatter_departamental.py - Educacion vs pobreza por departamento (M03 x M34)
=================================================================================
Scatter de los 25 departamentos cruzando DOS modulos con DOS llaves:
  x = anios promedio de educacion de adultos 25+ (M03, llave PERSONA, p301a->anios)
  y = incidencia de pobreza monetaria (M34 Sumaria, persona-ponderada pobreza in {1,2})
Agregado a departamento (2 primeros digitos de ubigeo), ponderado por factor07
(x) y factor07*mieperho (y). Recta de ajuste + r de Pearson ponderado.

Run: python fig_scatter_departamental.py
"""
from __future__ import annotations
from pathlib import Path
import numpy as np, pandas as pd, matplotlib.pyplot as plt
import figstyle as fs
from dataset_income import real_income

ROOT = Path(__file__).resolve().parents[1]; RAW = ROOT / "raw"
FIG = ROOT / "figures" / "01_ingreso_pobreza"; FIG.mkdir(parents=True, exist_ok=True)
DATA = ROOT / "datasets"
YEAR = 2025
EDU_YEARS = {1: 0, 2: 0, 3: 3, 4: 6, 5: 9, 6: 11, 7: 13, 8: 14, 9: 14, 10: 17, 11: 19, 12: 6}
DEPTO = {"01": "Amazonas", "02": "Ancash", "03": "Apurimac", "04": "Arequipa", "05": "Ayacucho",
         "06": "Cajamarca", "07": "Callao", "08": "Cusco", "09": "Huancavelica", "10": "Huanuco",
         "11": "Ica", "12": "Junin", "13": "La Libertad", "14": "Lambayeque", "15": "Lima",
         "16": "Loreto", "17": "M. de Dios", "18": "Moquegua", "19": "Pasco", "20": "Piura",
         "21": "Puno", "22": "San Martin", "23": "Tacna", "24": "Tumbes", "25": "Ucayali"}


def hh(d):
    return (d["conglome"].astype(str).str.zfill(6) + d["vivienda"].astype(str).str.zfill(3)
            + d["hogar"].astype(str).str.zfill(2))


def wmean(x, w):
    x = np.asarray(x, float); w = np.asarray(w, float); ok = np.isfinite(x) & np.isfinite(w)
    return np.average(x[ok], weights=w[ok]) if ok.any() else np.nan


# educacion (M03 persona, adultos 25+) + factor07
m3 = pd.read_stata(RAW / "educacion" / f"enaho-{YEAR}-03.dta", convert_categoricals=False)
m3.columns = [c.lower() for c in m3.columns]; m3["hh"] = hh(m3)
m3["edu"] = pd.to_numeric(m3["p301a"], errors="coerce").map(EDU_YEARS)
m2 = pd.read_stata(RAW / "miembros" / f"enaho-{YEAR}-02.dta", convert_categoricals=False)
m2.columns = [c.lower() for c in m2.columns]
m2["pk"] = hh(m2) + pd.to_numeric(m2["codperso"], errors="coerce").fillna(0).astype(int).astype(str).str.zfill(2)
m2["edad"] = pd.to_numeric(m2["p208a"], errors="coerce")
m3["pk"] = hh(m3) + pd.to_numeric(m3["codperso"], errors="coerce").fillna(0).astype(int).astype(str).str.zfill(2)
m3 = m3.merge(m2[["pk", "edad"]], on="pk", how="left")
inc = real_income(YEAR); inc["hh"] = hh(inc)   # para pobreza (M34)
m3["dep"] = m3["ubigeo"].astype(str).str.zfill(6).str[:2]   # M03 ya trae ubigeo y factor07
adult = m3[(m3["edad"] >= 25) & m3["edu"].notna()]

# pobreza (M34 persona-ponderada)
su = inc.copy(); su["dep"] = su["ubigeo"].astype(str).str.zfill(6).str[:2]
su["pobre"] = pd.to_numeric(su["pobreza"], errors="coerce").isin([1, 2]).astype(float)
su["pw"] = pd.to_numeric(su["factor07"], errors="coerce") * pd.to_numeric(su["mieperho"], errors="coerce")

rows = []
for dep in sorted(DEPTO):
    a = adult[adult["dep"] == dep]; s = su[su["dep"] == dep]
    if len(a) < 30 or len(s) < 30:
        continue
    rows.append({"dep": dep, "name": DEPTO[dep],
                 "edu": wmean(a["edu"], a["factor07"]),
                 "pov": 100 * wmean(s["pobre"], s["pw"])})
df = pd.DataFrame(rows)
df.to_csv(DATA / "scatter_edu_pobreza_dep_2025.csv", index=False)

# regresion ponderada (por poblacion ~ suma de pesos de pobreza)
popw = su.groupby("dep")["pw"].sum()
df["popw"] = df["dep"].map(popw)
b1, b0 = np.polyfit(df["edu"], df["pov"], 1, w=df["popw"])
r = np.corrcoef(df["edu"], df["pov"])[0, 1]
print(df.round(1).to_string(index=False))
print(f"\npendiente={b1:.1f} pp por anio, r={r:.2f}")

fs.use()
fig, ax = plt.subplots(figsize=(10.5, 7))
ax.scatter(df["edu"], df["pov"], s=np.sqrt(df["popw"]) / 12, color=fs.NAVY, alpha=0.55,
           edgecolor="white", lw=0.8, zorder=4)
xs = np.linspace(df["edu"].min() - 0.2, df["edu"].max() + 0.2, 50)
ax.plot(xs, b0 + b1 * xs, color=fs.CRANBERRY, lw=2, zorder=3)
try:
    fs.repel_labels(ax, df["edu"].values, df["pov"].values, df["name"].values, fs=8)
except Exception:
    for _, r_ in df.iterrows():
        fs.halo_label(ax, r_["edu"], r_["pov"], r_["name"], dx=3, dy=3)
fs.statbox(ax, [f"r = {r:.2f}  (ponderado por poblacion)",
                f"pendiente = {b1:.1f} pp de pobreza por anio de educacion",
                "tamano del punto ~ poblacion del departamento"], loc="upper right")
ax.set_xlabel("Anios promedio de educacion (adultos 25+)")
ax.set_ylabel("Pobreza monetaria (% de personas)")
ax.set_title("Mas educacion, menos pobreza: los 25 departamentos del Peru - ENAHO 2025",
             loc="left", fontsize=13)
fs.source(fig, "Fuente: ENAHO Modulos 03 (Educacion) y 34 (Sumaria), INEI 2025. Educacion ponderada por factor07; "
          "pobreza persona-ponderada (factor07*mieperho). Inferencia ecologica, n=25.")
fig.tight_layout()
for e in ("pdf", "png"):
    fig.savefig(FIG / f"fig_scatter_edu_pobreza.{e}", dpi=140, bbox_inches="tight")
print("OK -> figures/01_ingreso_pobreza/fig_scatter_edu_pobreza.pdf")
