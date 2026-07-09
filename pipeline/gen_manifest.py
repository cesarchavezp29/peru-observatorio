"""Genera pipeline/manifest.csv: la espina de la Fase 1.

Una fila por tabla analitica committeada: quien la produce, de que fuente sale,
con que cadencia se refresca y contra que se valida. Primer pase mecanico por
familias (spec: docs/PIPELINE_SPEC.md), lo no clasificado queda `pending`.

Run:  python pipeline/gen_manifest.py
"""
from __future__ import annotations

import csv
from pathlib import Path

HERE = Path(__file__).resolve().parent
DATASETS = HERE.parent / "data" / "datasets"

# (prefijo o predicado, script, fuente, cadencia, validacion)
SUMARIA = {
    "official_poverty_replication", "gini_nacional_tiempo", "gini_departamento_tiempo",
    "income_percentiles_tiempo", "gic_periodos", "income_real_national",
    "income_real_province_2021_2025", "income_real_district_2021_2025",
    "budget_composition_2004_2025", "validation_income_gasto", "income_change_ranked",
    "convergencia_departamental_2004_2025",
}
EMPLEO_KEYS = ("brecha_salarial", "informalidad", "estructura_empleo", "pea_",
               "neet", "subempleo", "empleo_", "trabajo_adolescente",
               "penalidad_maternidad", "evento_maternidad", "discapacidad_empleo",
               "retornos")
VIVSALUD_KEYS = ("vivienda", "calidad_vivienda", "combustible", "bienes_durables",
                 "seguro_salud", "sis_", "atencion_salud", "salud_cronica",
                 "cuidados", "razones_no_atencion", "jefatura")
GOBERN_KEYS = ("confianza", "trust_", "participacion", "who_trusts", "dept_income_social_vote",
               "district_vote", "electoral")
TRANSF_KEYS = ("transferencias", "social_")
EDU_KEYS = ("educacion", "analfabetismo", "movilidad_educativa", "cohorte")
DEMO_KEYS = ("migracion", "transicion_demografica", "demographic", "poblacion_indigena",
             "brecha_ingreso_etnico", "engel", "consumo", "scatter_", "sintesis",
             "indicadores_departamento", "corr_", "panel_departamento", "panel_indicators",
             "panel_validation")


def classify(stem: str) -> tuple[str, str, str, str]:
    s = stem.lstrip("_").lower()
    if stem.lstrip("_") in SUMARIA:
        return ("pipeline/build_sumaria.py", "ENAHO modulo 34 (sumaria) 2004-2025",
                "annual", "INEI pobreza monetaria y gasto real (0.0pp / +-0.5)")
    if s.startswith("panel_") or s.startswith("enaho_panel"):
        return ("pipeline/build_panel_familias.py", "ENAHO Panel releases 2011-2023",
                "annual", "pobreza anual por ola vs INEI (panel_validate)")
    if s.startswith("censo_"):
        return ("pipeline/static/ (frozen)", "Censos INEI 1981/1993/2007/2017",
                "frozen", "urbanizacion y lengua vs INEI censal (<0.5pp)")
    if s.startswith("voto_keiko"):
        return ("pipeline/static/ (frozen)", "ONPE 2V 2021 y 2026 (freeze 99.44%)",
                "frozen", "totales nacionales ONPE")
    if s.startswith("paises_"):
        return ("pipeline/build_wdi.py", "Banco Mundial WDI API", "annual",
                "valores publicados WDI")
    if s.startswith("bcrp") or s.startswith("ipc_"):
        return ("pipeline/build_bcrp.py", "BCRP series estadisticas API", "monthly",
                "serie oficial BCRP")
    if s.startswith("epen_"):
        return ("pipeline/build_epen.py", "EPE/EPEN CSV (catalogo perudata) 2001-2026",
                "monthly", "desempleo Lima vs informe INEI")
    if s.startswith("endes_"):
        return ("pipeline/build_endes.py", "ENDES SPSS 2004-2024", "annual",
                "TFR y desnutricion vs informes ENDES")
    if s.startswith("eea_"):
        return ("pipeline/build_eea.py", "EEA CSV (catalogo perudata) 2023", "annual", "")
    if s.startswith("agro_"):
        return ("pipeline/build_agro.py", "ENAHO modulos 22-28 (agro)", "annual", "")
    if any(k in s for k in TRANSF_KEYS):
        return ("pipeline/build_transferencias.py", "ENAHO modulo 37 (trampa p710)",
                "annual", "cobertura Juntos/Pension65 vs INEI")
    if any(k in s for k in GOBERN_KEYS):
        return ("pipeline/build_gobernabilidad.py", "ENAHO modulos 84-85", "annual", "")
    if any(k in s for k in EMPLEO_KEYS):
        return ("pipeline/build_empleo.py", "ENAHO modulo 05 (empleo e ingreso)",
                "annual", "informalidad vs serie oficial")
    if any(k in s for k in VIVSALUD_KEYS):
        return ("pipeline/build_vivienda_salud.py", "ENAHO modulos 01 y 04",
                "annual", "bitacora validacion.md (agua/luz/celular vs INEI)")
    if any(k in s for k in EDU_KEYS):
        return ("pipeline/build_educacion.py", "ENAHO modulo 03", "annual", "")
    if s == "module_keys":
        return ("interno (excluido de la app)", "referencia de llaves de merge", "frozen", "")
    if s.startswith("engel"):
        return ("pipeline/build_sumaria.py", "ENAHO modulo 34 (grupos de gasto)",
                "annual", "elasticidades vs literatura Engel Peru")
    if any(k in s for k in DEMO_KEYS):
        return ("pipeline/build_demografia_sintesis.py", "ENAHO multi-modulo (01-05, 34)",
                "annual", "")
    return ("pending", "", "", "")


def main() -> None:
    rows = []
    for p in sorted(DATASETS.glob("*.csv")):
        script, source, cadence, val = classify(p.stem)
        rows.append({"table": p.stem, "producing_script": script, "source": source,
                     "cadence": cadence, "validation_target": val})
    out = HERE / "manifest.csv"
    with open(out, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=["table", "producing_script", "source",
                                          "cadence", "validation_target"])
        w.writeheader()
        w.writerows(rows)
    from collections import Counter
    c = Counter(r["producing_script"] for r in rows)
    print(f"{len(rows)} tablas -> {out.name}")
    for k, v in c.most_common():
        print(f"  {v:3d}  {k}")


if __name__ == "__main__":
    main()
