"""Catalog: maps each analytical CSV to a database schema, a thematic section,
and a human-readable title. Single source of truth for how the ~200 ENAHO/INEI
analytical tables are organized in the Observatorio web app.

Schemas (top-level databases / site sections):
  enaho  -> Ingreso, Pobreza y Sociedad (cross-section household survey)
  panel  -> Dinamica de Pobreza (longitudinal panel)
  endes  -> Salud y Fertilidad (DHS)
  epen   -> Empleo y Mercado Laboral (employment surveys)
  eea    -> Empresas (firm economic survey)
"""
import re

# ---------------------------------------------------------------- databases
DATABASES = {
    "enaho": {
        "title": "Ingreso, Pobreza y Sociedad",
        "source": "ENAHO - Encuesta Nacional de Hogares",
        "desc": "Ingreso real, pobreza, educacion, salud, confianza, vivienda, "
                "consumo, participacion y elecciones. Corte transversal 2004-2025.",
        "color": "#c85a34",
    },
    "panel": {
        "title": "Dinamica de Pobreza",
        "source": "ENAHO Panel (longitudinal)",
        "desc": "Hogares reentrevistados: pobreza cronica vs transitoria, "
                "transiciones, movilidad de ingresos y de seguro. 2007-2023.",
        "color": "#9c6b2f",
    },
    "endes": {
        "title": "Salud y Fertilidad",
        "source": "ENDES - Encuesta Demografica y de Salud",
        "desc": "Fecundidad, salud materno-infantil, desnutricion, anticoncepcion "
                "y violencia. Indicadores nacionales y por departamento 2004-2024.",
        "color": "#157a6e",
    },
    "epen": {
        "title": "Empleo y Mercado Laboral",
        "source": "EPE / EPEN - Encuesta Permanente de Empleo",
        "desc": "Lima trimestre movil 2001-2026 (desempleo, ingreso, informalidad) "
                "y corte departamental 2022-2025.",
        "color": "#8a4a6b",
    },
    "eea": {
        "title": "Empresas",
        "source": "EEA - Encuesta Economica Anual",
        "desc": "Lado empresa: productividad, valor agregado, concentracion, "
                "brecha de genero y remuneraciones por sector. Ano fiscal 2023.",
        "color": "#3f5aa6",
    },
}

# microdata (individual-level, huge, not chart-ready) + internal key tables
# -> excluded from the web DB
EXCLUDE = {
    "endes_miembros_2004_2024",
    "endes_nacimientos_2004_2024",
    "endes_mujeres_2004_2024",
    "endes_mujeres_2004_2006",
    "enaho_panel_hogar_long_sample",
    "module_keys",         # internal merge-key reference, not an indicator
    "panel_file_keys",     # internal panel-file reference, not an indicator
    "epen_codciudad_dict",     # city-code lookup, not an indicator
    "epen_codciudad_inferred", # city-inference reference, not an indicator
    "panel_evento_hijo_empleo", # 48k person-event microdata (use the _profile aggregates)
    "panel_intergen_pooled",    # group×age profile with CI — no sensible generic chart
    "panel_intergen_educacion_2007-2011",  # hyphenated CSV stem (matched pre-table_name)
    "trust_income_2025",        # 30k household-level microdata (binscatter source)
    "who_trusts_state_2025",    # 30k person-level microdata (regression source)
}
MAX_MB = 8.0  # any CSV larger than this is treated as microdata and skipped

# per-table column renames applied at build time — fixes cryptic headers that
# come from the source builders (durable-good codes, single-letter event vars).
# keyed by file stem. Durable codes verified in fig_bienes_durables.py / M18.
COLUMN_RENAMES = {
    "bienes_durables_decil_2025": {
        "12": "Refrigeradora", "7": "Computadora", "13": "Lavadora",
        "17": "Auto/camioneta", "14": "Microondas", "2": "TV a color",
    },
    "panel_evento_hijo_empleo_profile_madre": {"e": "anios_desde_hijo", "level": "empleo_pct"},
    "panel_evento_hijo_empleo_profile_padre": {"e": "anios_desde_hijo", "level": "empleo_pct"},
}

# ---------------------------------------------------------------- themes (enaho sub-sections)
# keyword -> (theme_key, theme_label). First match wins.
_THEME_RULES = [
    ("income",        ("ingreso_pobreza", "Ingreso y Pobreza")),
    ("ingreso",       ("ingreso_pobreza", "Ingreso y Pobreza")),
    ("pobreza",       ("ingreso_pobreza", "Ingreso y Pobreza")),
    ("poverty",       ("ingreso_pobreza", "Ingreso y Pobreza")),
    ("convergencia",  ("ingreso_pobreza", "Ingreso y Pobreza")),
    ("brecha_salarial",("empleo", "Empleo e Ingresos Laborales")),
    ("brecha_ingreso",("empleo", "Empleo e Ingresos Laborales")),
    ("empleo",        ("empleo", "Empleo e Ingresos Laborales")),
    ("neet",          ("empleo", "Empleo e Ingresos Laborales")),
    ("pea",           ("empleo", "Empleo e Ingresos Laborales")),
    ("informalidad",  ("empleo", "Empleo e Ingresos Laborales")),
    ("subempleo",     ("empleo", "Empleo e Ingresos Laborales")),
    ("estructura_empleo",("empleo", "Empleo e Ingresos Laborales")),
    ("retornos",      ("empleo", "Empleo e Ingresos Laborales")),
    ("confianza",     ("confianza", "Confianza e Instituciones")),
    ("trust",         ("confianza", "Confianza e Instituciones")),
    ("who_trusts",    ("confianza", "Confianza e Instituciones")),
    ("vote",          ("elecciones", "Elecciones")),
    ("electoral",     ("elecciones", "Elecciones")),
    ("district_vote", ("elecciones", "Elecciones")),
    ("social",        ("programas", "Programas Sociales")),
    ("transferencias",("programas", "Programas Sociales")),
    ("participacion", ("participacion", "Participacion Ciudadana")),
    ("educacion",     ("educacion_salud", "Educacion, Salud y Demografia")),
    ("analfabetismo", ("educacion_salud", "Educacion, Salud y Demografia")),
    ("movilidad_educativa",("educacion_salud", "Educacion, Salud y Demografia")),
    ("cohorte",       ("educacion_salud", "Educacion, Salud y Demografia")),
    ("salud",         ("educacion_salud", "Educacion, Salud y Demografia")),
    ("atencion_salud",("educacion_salud", "Educacion, Salud y Demografia")),
    ("seguro_salud",  ("educacion_salud", "Educacion, Salud y Demografia")),
    ("sis_",          ("educacion_salud", "Educacion, Salud y Demografia")),
    ("discapacidad",  ("educacion_salud", "Educacion, Salud y Demografia")),
    ("demographic",   ("educacion_salud", "Educacion, Salud y Demografia")),
    ("transicion_demografica",("educacion_salud", "Educacion, Salud y Demografia")),
    ("demografia",    ("educacion_salud", "Educacion, Salud y Demografia")),
    ("migracion",     ("educacion_salud", "Educacion, Salud y Demografia")),
    ("maternidad",    ("educacion_salud", "Educacion, Salud y Demografia")),
    ("jefatura",      ("educacion_salud", "Educacion, Salud y Demografia")),
    ("cuidados",      ("educacion_salud", "Educacion, Salud y Demografia")),
    ("trabajo_adolescente",("educacion_salud", "Educacion, Salud y Demografia")),
    ("indigena",      ("indigena", "Poblacion Indigena")),
    ("etnico",        ("indigena", "Poblacion Indigena")),
    ("vivienda",      ("vivienda", "Vivienda y Servicios")),
    ("calidad_vivienda",("vivienda", "Vivienda y Servicios")),
    ("combustible",   ("vivienda", "Vivienda y Servicios")),
    ("bienes_durables",("vivienda", "Vivienda y Servicios")),
    ("agro",          ("agro", "Agropecuario")),
    ("engel",         ("consumo", "Consumo")),
    ("consumo",       ("consumo", "Consumo")),
    ("budget",        ("consumo", "Consumo")),
    ("gasto",         ("consumo", "Consumo")),
    ("departamento",  ("territorio", "Sintesis Territorial")),
    ("indicadores_departamento",("territorio", "Sintesis Territorial")),
    ("scatter",       ("territorio", "Sintesis Territorial")),
    ("sintesis",      ("territorio", "Sintesis Territorial")),
]


def schema_for(stem: str) -> str:
    n = stem.lower()
    if n.startswith("panel_") or n.startswith("enaho_panel"):
        return "panel"
    if n.startswith("endes_"):
        return "endes"
    if n.startswith("eea_"):
        return "eea"
    if n.startswith("epen_") or n.startswith("_bcrp") or n.startswith("_ipc"):
        return "epen"
    return "enaho"


def theme_for(stem: str, schema: str) -> tuple[str, str]:
    """Thematic sub-section. Only enaho is split by theme; the other databases
    are cohesive enough to be one section each (theme == schema)."""
    if schema != "enaho":
        return (schema, DATABASES[schema]["title"])
    n = stem.lower()
    for kw, theme in _THEME_RULES:
        if kw in n:
            return theme
    return ("otros", "Otros Indicadores")


def table_name(stem: str) -> str:
    """DuckDB-safe table identifier."""
    t = stem.lstrip("_")
    t = re.sub(r"[^0-9a-zA-Z]+", "_", t).strip("_").lower()
    return t


# curated titles for flagship tables; everything else is prettified from the stem
_TITLES = {
    "income_real_national": "Ingreso real per capita nacional (2004-2025)",
    "income_real_province_2021_2025": "Ingreso real por provincia (2021 vs 2025)",
    "income_real_district_2021_2025": "Ingreso real por distrito (2021 vs 2025)",
    "official_poverty_replication": "Pobreza: replica propia vs oficial INEI",
    "convergencia_departamental_2004_2025": "Convergencia de ingresos entre departamentos",
    "confianza_instituciones_tiempo_2007_2025": "Confianza en instituciones (2007-2025)",
    "epen_lima_movil_2001_2026": "Lima: empleo trimestre movil (2001-2026)",
    "endes_indicadores": "Indicadores ENDES nacionales (2004-2024)",
    "endes_dept_indicadores": "Indicadores ENDES por departamento",
    "eea_productividad_sector": "Productividad por sector (VA/trabajador)",
    "eea_concentracion_industria": "Concentracion por industria (CR4)",
    "indicadores_departamento_2025": "Sintesis de indicadores por departamento (2025)",
    "endes_adol_maternidad_riqueza_2016_2024": "Maternidad adolescente por quintil de riqueza",
    "endes_hijos_educacion_tiempo": "Hijos por mujer segun educacion (2004-2024)",
    "endes_hijos_area_tiempo": "Hijos por mujer: urbano vs rural (2004-2024)",
    "endes_edad_primer_hijo_educacion": "Edad al primer hijo segun educacion",
}


def title_for(stem: str) -> str:
    if stem in _TITLES:
        return _TITLES[stem]
    t = stem.lstrip("_")
    # drop trailing year ranges like _2004_2025 / _2007-2011 / _2025
    t = re.sub(r"[_-](\d{4})([_-]\d{4})?$", "", t)
    t = t.replace("_", " ").strip()
    return t[:1].upper() + t[1:] if t else stem
