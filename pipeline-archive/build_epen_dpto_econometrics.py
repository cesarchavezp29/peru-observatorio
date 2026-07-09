"""
build_epen_dpto_econometrics.py
===============================
Analisis econometrico laboral por departamento desde los microdatos EPEN "BD Publicacion
Dpto" (790/874/935/1001 = 2022-2025), pooled, ponderado (fac300_anual).

1. Mincer por departamento: ln(salario/hora) = a + RETORNO*anios_educ + b*exp + c*exp^2.
2. Penalidad de informalidad por departamento: ln(w) = ... + PENAL*informal (+ controles).
3. Curva de Wages (Blanchflower-Oswald): panel depto-ano, ln(w_mediano) vs ln(desempleo) + FE.
4. Oaxaca-Blinder (nacional): brecha de genero = explicada (dotaciones) + no explicada.

Salario/hora = ingtotp / (whorat * 4.33). anios_educ mapeados de c366. exp = edad - educ - 6.
Out: datasets/epen_dpto_econometrics_2022_2025.csv (retorno educ + penalidad informal por depto)
"""
from __future__ import annotations
from pathlib import Path
import glob
import numpy as np
import pandas as pd
import statsmodels.api as sm

ROOT = Path(__file__).resolve().parents[1]
RAW = ROOT / "raw" / "epen_inei"
OUT = ROOT / "datasets" / "epen_dpto_econometrics_2022_2025.csv"
WCURVE = ROOT / "datasets" / "epen_wage_curve_2022_2025.csv"
CODES = {2022: 790, 2023: 874, 2024: 935, 2025: 1001}
DPTO = {1: "Amazonas", 2: "Ancash", 3: "Apurimac", 4: "Arequipa", 5: "Ayacucho",
        6: "Cajamarca", 7: "Callao", 8: "Cusco", 9: "Huancavelica", 10: "Huanuco",
        11: "Ica", 12: "Junin", 13: "La Libertad", 14: "Lambayeque", 15: "Lima",
        16: "Loreto", 17: "Madre de Dios", 18: "Moquegua", 19: "Pasco", 20: "Piura",
        21: "Puno", 22: "San Martin", 23: "Tacna", 24: "Tumbes", 25: "Ucayali"}
YEARS = {1: 0, 2: 0, 3: 3, 4: 6, 5: 9, 6: 11, 7: 6, 8: 13, 9: 14, 10: 15, 11: 17, 12: 19}


def load():
    parts = []
    for y, code in CODES.items():
        fs = glob.glob(str(RAW / f"{code}_*/*.csv"))
        if not fs:
            continue
        df = pd.read_csv(fs[0], encoding="latin-1", low_memory=False)
        df.columns = [c.strip().strip('"').lower() for c in df.columns]
        for c in ["ocup300", "ccdd", "c207", "c208", "c310", "c366", "ingtotp", "whorat", "informal_p", "fac300_anual"]:
            df[c] = pd.to_numeric(df[c], errors="coerce")
        df["anio"] = y
        parts.append(df)
    d = pd.concat(parts, ignore_index=True)
    # ocupados remunerados con salario/hora valido
    # excluir SOLO los no remunerados (c310: 4 ayudante/TFNR, 8 practicante sin remuneracion);
    # el 7 (aprendiz remunerado) se incluye. (dicc. EPEN c310, verificado)
    d = d[(d["c208"] >= 14) & (d["ocup300"] == 1) & (~d["c310"].isin([4, 8]))
          & (d["ingtotp"] > 0) & (d["whorat"] >= 5) & (d["whorat"] <= 98)].copy()
    d["whora"] = d["ingtotp"] / (d["whorat"] * 4.33)
    d = d[d["whora"] > 0]
    d["lw"] = np.log(d["whora"])
    d["educ"] = d["c366"].map(YEARS)
    d["exp"] = (d["c208"] - d["educ"] - 6).clip(lower=0)
    d["exp2"] = d["exp"] ** 2 / 100
    d["female"] = (d["c207"] == 2).astype(float)
    d["informal"] = (d["informal_p"] == 1).astype(float)
    return d.dropna(subset=["lw", "educ", "exp", "ccdd", "fac300_anual"])


def wls(y, X, w):
    X = sm.add_constant(X)
    return sm.WLS(y, X, weights=w).fit()


def main():
    d = load()
    print(f"muestra pooled: {len(d):,} ocupados remunerados\n")
    rows = []
    for dd, name in DPTO.items():
        g = d[d["ccdd"] == dd]
        if len(g) < 300:
            continue
        # Mincer
        m = wls(g["lw"], g[["educ", "exp", "exp2"]], g["fac300_anual"])
        ret = m.params["educ"]
        # Penalidad informalidad (controla educ, exp, female)
        gi = g.dropna(subset=["informal"])
        pi = wls(gi["lw"], gi[["informal", "educ", "exp", "exp2", "female"]], gi["fac300_anual"])
        penal = pi.params["informal"]
        rows.append({"ccdd": dd, "departamento": name, "n": len(g),
                     "retorno_educ_pct": round(100 * ret, 1),
                     "penal_informal_pct": round(100 * (np.exp(penal) - 1), 1)})
    res = pd.DataFrame(rows)
    res.to_csv(OUT, index=False, encoding="utf-8")
    print("=== 1. MINCER: retorno a cada anio de educacion (%) ===")
    print(res.sort_values("retorno_educ_pct", ascending=False)[["departamento", "retorno_educ_pct"]].head(6).to_string(index=False))
    print(f"  ... nacional pooled: {100*wls(d['lw'], d[['educ','exp','exp2']], d['fac300_anual']).params['educ']:.1f}% por anio")
    print("\n=== 2. PENALIDAD SALARIAL DE LA INFORMALIDAD (%) ===")
    print(res.sort_values("penal_informal_pct")[["departamento", "penal_informal_pct"]].head(6).to_string(index=False))

    # 3. Curva de Wages: panel depto-ano (desempleo del dataset anual ya construido)
    adv = pd.read_csv(ROOT / "datasets" / "epen_dpto_annual_2022_2025.csv")
    wcd = d.groupby(["ccdd", "anio"]).apply(
        lambda g: np.average(g["lw"], weights=g["fac300_anual"]), include_groups=False).reset_index(name="lw_mean")
    wcd = wcd.merge(adv[["ccdd", "anio", "tasa_desempleo"]], on=["ccdd", "anio"])
    wcd["ln_u"] = np.log(wcd["tasa_desempleo"])
    wcd.to_csv(WCURVE, index=False, encoding="utf-8")
    # wage curve elasticity with dept FE
    X = pd.concat([wcd["ln_u"], pd.get_dummies(wcd["ccdd"], prefix="d", drop_first=True).astype(float)], axis=1)
    wcfit = sm.OLS(wcd["lw_mean"], sm.add_constant(X)).fit()
    print(f"\n=== 3. CURVA DE WAGES (Blanchflower-Oswald): elasticidad = {wcfit.params['ln_u']:.3f} "
          f"(p={wcfit.pvalues['ln_u']:.3f}, n={len(wcd)} depto-ano, con FE depto) ===")
    print("  (la 'ley empirica' clasica es ~ -0.10)")

    # 4. Oaxaca-Blinder nacional (twofold, pooled)
    do = d.dropna(subset=["female"])
    Xcols = ["educ", "exp", "exp2"]
    h = do[do["female"] == 0]; mu = do[do["female"] == 1]
    bh = wls(h["lw"], h[Xcols], h["fac300_anual"]).params
    bm = wls(mu["lw"], mu[Xcols], mu["fac300_anual"]).params
    Xh = np.average(sm.add_constant(h[Xcols]), weights=h["fac300_anual"], axis=0)
    Xm = np.average(sm.add_constant(mu[Xcols]), weights=mu["fac300_anual"], axis=0)
    gap = (bh.values @ Xh) - (bm.values @ Xm)
    explained = (Xh - Xm) @ bh.values
    unexplained = gap - explained
    print(f"\n=== 4. OAXACA-BLINDER (brecha de genero, ln salario/hora) ===")
    print(f"  brecha total H-M = {gap:.3f} log-pts (~{100*(np.exp(gap)-1):.0f}% mas el hombre)")
    print(f"  explicada por dotaciones (educ/exp) = {explained:.3f} ({100*explained/gap:.0f}%)")
    print(f"  NO explicada (estructura/discriminacion) = {unexplained:.3f} ({100*unexplained/gap:.0f}%)")
    pd.DataFrame([
        {"indicador": "brecha_total_log", "valor": round(gap, 4)},
        {"indicador": "explicada_log", "valor": round(explained, 4)},
        {"indicador": "no_explicada_log", "valor": round(unexplained, 4)},
        {"indicador": "mincer_nacional_pct", "valor": round(100 * wls(d['lw'], d[['educ', 'exp', 'exp2']], d['fac300_anual']).params['educ'], 2)},
        {"indicador": "wage_curve_elasticidad", "valor": round(wcfit.params['ln_u'], 4)},
    ]).to_csv(ROOT / "datasets" / "epen_econ_summary.csv", index=False, encoding="utf-8")


if __name__ == "__main__":
    main()
