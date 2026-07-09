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
    "censos": {
        "title": "Censos de Población",
        "source": "Censos Nacionales INEI 1981-2017",
        "desc": "Las fotos completas del país: educación, lengua materna y "
                "urbanización comparadas a través de cuatro censos.",
        "color": "#6b4a8a",
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
    # headerless first column from a pandas index dump
    "epen_informal_sector_dpto_2025": {"column0": "departamento", "column00": "departamento"},
}

# ---------------------------------------------------------------- themes (enaho sub-sections)
# keyword -> (theme_key, theme_label). First match wins.
_THEME_RULES = [
    ("gic_",          ("ingreso_pobreza", "Ingreso y Pobreza")),
    ("percentil",     ("ingreso_pobreza", "Ingreso y Pobreza")),
    ("gini",          ("ingreso_pobreza", "Ingreso y Pobreza")),
    ("desigualdad",   ("ingreso_pobreza", "Ingreso y Pobreza")),
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
    ("voto",          ("elecciones", "Elecciones")),
    ("keiko",         ("elecciones", "Elecciones")),
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


# ---------------------------------------------------------------- topics
# Cross-survey TOPIC layer. Schemas answer "which survey produced this";
# topics answer "what is this about", which is how readers navigate. Employment
# lives in enaho+epen+eea, poverty in enaho+panel — the topic view reunites
# them without touching schemas or URLs. Dict order = narrative order.
TOPICS = {
    "pobreza":     "Pobreza y Desigualdad",
    "ingreso":     "Ingreso y Consumo",
    "empleo":      "Empleo y Salarios",
    "educacion":   "Educación",
    "salud":       "Salud y Demografía",
    "sociedad":    "Confianza, Estado y Elecciones",
    "vivienda":    "Vivienda y Servicios",
    "agro":        "Agropecuario",
    "empresas":    "Empresas",
    "territorio":  "Territorio y Síntesis",
}

# explicit stem -> topic (wins over rules; for stragglers the keywords misfile)
_TOPIC_OVERRIDES = {
    "official_poverty_replication": "pobreza",
    "eea_epen_cruce_sector": "empleo",          # firm vs household wages
    "eea_brecha_genero_sector": "empleo",       # gender gap belongs with wages
    "eea_remuneraciones_sector": "empleo",
    "demographic_transition": "salud",
    "transicion_demografica_2004_2025": "salud",
    "budget_composition_2004_2025": "ingreso",
    "bienes_durables_decil_2025": "ingreso",
    "bienes_durables_difusion_2004_2025": "ingreso",
    "sis_expansion": "salud",
    "panel_indicators": "territorio",
}

# keyword -> topic, first match wins (checked on the lower-cased stem).
# ORDER MATTERS: sociedad before ingreso (trust_income_vote is a trust table),
# sociedad before educacion (confianza_educacion is a trust table), pobreza
# first (brecha_ingreso/indigena are equity tables, not income levels).
_TOPIC_RULES = [
    # pobreza y desigualdad (incluye movilidad y brechas entre grupos)
    ("pobreza", "pobreza"), ("poverty", "pobreza"), ("gini", "pobreza"),
    ("gic_", "pobreza"), ("percentil", "pobreza"), ("convergencia", "pobreza"),
    ("theil", "pobreza"), ("movilidad_quintil", "pobreza"),
    ("movilidad_ingreso", "pobreza"), ("brecha_ingreso", "pobreza"),
    ("desigualdad", "pobreza"), ("indigena", "pobreza"),
    # empleo y salarios
    ("brecha_salarial", "empleo"), ("empleo", "empleo"), ("informalidad", "empleo"),
    ("neet", "empleo"), ("pea_", "empleo"), ("subempleo", "empleo"),
    ("desempleo", "empleo"), ("retornos", "empleo"), ("maternidad_", "empleo"),
    ("evento_maternidad", "empleo"), ("penalidad", "empleo"),
    ("trabajo_adolescente", "empleo"), ("oaxaca", "empleo"), ("wage", "empleo"),
    ("evento_hijo", "empleo"), ("sector_flujo", "empleo"),
    # sociedad: confianza, estado, elecciones, programas
    ("lengua", "sociedad"),
    ("confianza", "sociedad"), ("trust", "sociedad"), ("vote", "sociedad"),
    ("voto", "sociedad"), ("keiko", "sociedad"),
    ("electoral", "sociedad"), ("participacion", "sociedad"),
    ("social", "sociedad"), ("transferencias", "sociedad"),
    ("who_trusts", "sociedad"),
    # ingreso y consumo
    ("income", "ingreso"), ("ingreso", "ingreso"), ("engel", "ingreso"),
    ("consumo", "ingreso"), ("gasto", "ingreso"), ("ipc_", "ingreso"),
    # educacion
    ("educacion", "educacion"), ("educativa", "educacion"),
    ("analfabetismo", "educacion"), ("cohorte", "educacion"), ("intergen", "educacion"),
    # salud y demografia
    ("urbanizacion", "salud"),
    ("salud", "salud"), ("seguro", "salud"),
    ("discapacidad", "salud"), ("cuidados", "salud"), ("demografia", "salud"),
    ("migracion", "salud"), ("jefatura", "salud"), ("atencion", "salud"),
    # vivienda
    ("vivienda", "vivienda"), ("combustible", "vivienda"), ("bienes_durables", "vivienda"),
    # agro
    ("agro", "agro"),
    # territorio / sintesis
    ("departamento", "territorio"), ("scatter", "territorio"),
    ("sintesis", "territorio"), ("indicadores_departamento", "territorio"),
    ("correlacion", "territorio"), ("corr_", "territorio"),
]

# schema fallback when no keyword matches
_TOPIC_SCHEMA_DEFAULT = {
    "endes": "salud", "eea": "empresas", "epen": "empleo",
    "panel": "pobreza", "enaho": "territorio",
}


def topic_for(stem: str, schema: str) -> tuple[str, str]:
    key = stem.lstrip("_").lower()
    t = _TOPIC_OVERRIDES.get(stem.lstrip("_"))
    if t is None and schema in ("endes", "eea"):
        # cohesive source sections: keep them whole except explicit overrides
        t = _TOPIC_SCHEMA_DEFAULT[schema]
    if t is None:
        for kw, topic in _TOPIC_RULES:
            if kw in key:
                t = topic
                break
    if t is None:
        t = _TOPIC_SCHEMA_DEFAULT.get(schema, "territorio")
    return (t, TOPICS[t])


# panel indicator families: one FAMILY shown once in navigation, its
# re-interview windows offered as chips inside the chart page.
def family_for(stem: str) -> tuple[str | None, str | None]:
    m = re.match(r"^(.*)[_-](\d{4})[_-](\d{4})$", stem.lstrip("_"))
    if m and m.group(1) in _FAMILIES:
        return m.group(1), f"{m.group(2)}–{m.group(3)}"
    return None, None


def schema_for(stem: str) -> str:
    n = stem.lower()
    if n.startswith("panel_") or n.startswith("enaho_panel"):
        return "panel"
    if n.startswith("endes_"):
        return "endes"
    if n.startswith("eea_"):
        return "eea"
    if n.startswith("censo_"):
        return "censos"
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


# per-table cleanup SQL applied right after load ({t} = schema.table).
# For raw kitchen-sink files that mix revisions or weighting variants no chart
# can present honestly -> keep only the publishable slice.
TRANSFORMS = {
    "eea_demografia_sector": [
        "CREATE OR REPLACE TABLE {t} AS "
        "SELECT year, sector, n, share FROM {t} WHERE pond ORDER BY year, sector",
    ],
    # fmt marks which ENAHO module format produced each year -> not a dimension
    "transferencias_cobertura_2013_2025": [
        'CREATE OR REPLACE TABLE {t} AS SELECT year, n_hh, "Juntos", "Pension 65" '
        "FROM {t} ORDER BY year",
    ],
    # fuente is a per-year status note, not a dimension -> plain year series
    "informalidad_reconstruida": [
        'CREATE OR REPLACE TABLE {t} AS SELECT year, informal_reconstruido, '
        'informal_oficial, "concordancia_%" FROM {t} ORDER BY year',
    ],
    # event-study long table -> one column per sex, x = years since first child
    "evento_maternidad_empleo": [
        "CREATE OR REPLACE TABLE {t} AS SELECT evt AS anios_desde_primer_hijo, "
        "max(CASE WHEN sexo='mujer' THEN emp END) AS empleo_madre, "
        "max(CASE WHEN sexo='hombre' THEN emp END) AS empleo_padre, "
        "max(CASE WHEN sexo='mujer' THEN ref END) AS ref_madre, "
        "max(CASE WHEN sexo='hombre' THEN ref END) AS ref_padre "
        "FROM {t} GROUP BY evt ORDER BY evt",
    ],
}

# panel families: one dataset per re-interview window -> title carries the window
_FAMILIES = {
    "panel_pobreza_dinamica": "Pobreza crónica vs transitoria",
    "panel_pobreza_transicion": "Transiciones de pobreza",
    "panel_informalidad_dinamica": "Informalidad: siempre, a veces, nunca",
    "panel_informalidad_transicion": "Transiciones formal-informal",
    "panel_seguro_dinamica": "Cobertura de seguro en el tiempo",
    "panel_seguro_transicion": "Transiciones de seguro de salud",
    "panel_movilidad_quintil": "Movilidad de ingresos entre quintiles",
}

# curated titles: every table gets an editorial name, never a prettified filename
_TITLES = {
    # ---- EEA (empresas)
    "eea_activos_sector": "Activos e inversión por sector empresarial",
    "eea_brecha_genero_sector": "Empresas: brecha salarial de género por sector",
    "eea_concentracion_sector": "Concentración de mercado por sector (CR4, HHI)",
    "eea_demografia_sector": "Cuántas empresas hay por sector",
    "eea_epen_cruce_sector": "Salario por sector: empresas (EEA) vs hogares (EPEN)",
    "eea_productividad_sector_tamano": "Productividad por sector y tamaño de empresa",
    "eea_productividad_tamano": "Productividad por tamaño de empresa",
    "eea_remuneraciones_sector": "Remuneraciones por sector empresarial",
    "eea_ventas_va_sector": "Ventas y valor agregado por sector",
    # ---- ENAHO: agro
    "agro_comercializacion_2011_2025": "Agro: venta vs autoconsumo (2011-2025)",
    "agro_mercado_2025": "Agro: orientación al mercado (2025)",
    "agro_top_cultivos_2025": "Los cultivos más sembrados (2025)",
    "agro_top_especies_2025": "Las crianzas más comunes (2025)",
    "agro_volumen_valor_2025": "Agro: volumen y valor de la producción (2025)",
    # ---- ENAHO: educacion
    "analfabetismo_region_tiempo_2004_2025": "Analfabetismo por región natural (2004-2025)",
    "educacion_cohorte_2025": "Años de educación por cohorte de nacimiento",
    "educacion_sexo_tiempo_2004_2025": "Años de educación: hombres vs mujeres (2004-2025)",
    "educacion_superior_area_tiempo_2004_2025": "Educación superior: urbano vs rural (2004-2025)",
    "educacion_superior_sexo_tiempo_2004_2025": "Educación superior: hombres vs mujeres (2004-2025)",
    "movilidad_educativa_tiempo": "Movilidad educativa entre generaciones",
    # ---- ENAHO: empleo y salarios
    "brecha_salarial_edad_tiempo_2004_2025": "Brecha salarial por edad (2004-2025)",
    "brecha_salarial_formal_tiempo_2007_2025": "Penalidad salarial de la informalidad (2007-2025)",
    "brecha_salarial_grupos_tiempo_2004_2025": "Brechas salariales entre grupos (2004-2025)",
    "brecha_salarial_hora_tiempo_2004_2025": "Brecha salarial por hora trabajada (2004-2025)",
    "brecha_salarial_region_tiempo_2004_2025": "Brecha salarial entre regiones naturales (2004-2025)",
    "brecha_salarial_sector_2025": "Brecha salarial de género por sector (2025)",
    "brecha_salarial_sexo_2004_2025": "Brecha salarial hombre-mujer (2004-2025)",
    "brecha_salarial_urbano_tiempo_2004_2025": "Brecha salarial urbano-rural (2004-2025)",
    "fig_brecha_salarial_educacion": "Brecha salarial de género por nivel educativo",
    "fig_brecha_salarial_etnico": "Brecha salarial de género por origen étnico",
    "fig_brecha_salarial_tipoempleo": "Brecha salarial de género por tipo de empleo",
    "empleo_agricola_2004_2025": "El empleo agrícola se encoge (2004-2025)",
    "empleo_sectores_2004_2025": "Empleo por sector económico (2004-2025)",
    "estructura_empleo_2004_2025": "Estructura del empleo: asalariados e independientes",
    "evento_maternidad_empleo": "Empleo alrededor del primer hijo (estudio de evento)",
    "penalidad_maternidad_tiempo": "Penalidad de maternidad en el empleo",
    "informalidad_reconstruida": "Informalidad: réplica propia vs oficial",
    "neet_juvenil_tiempo_2004_2025": "Jóvenes que ni estudian ni trabajan (2004-2025)",
    "pea_sexo_2004_2025": "Participación laboral: hombres vs mujeres (2004-2025)",
    "subempleo_horas_2004_2025": "Horas trabajadas y subempleo (2004-2025)",
    "trabajo_adolescente_tiempo": "Trabajo adolescente: estudio, trabajo o ninguno",
    "discapacidad_empleo_tiempo": "Discapacidad: empleo y pobreza en el tiempo",
    # ---- ENAHO: ingreso, pobreza, gasto
    "budget_composition_2004_2025": "En qué gastan los hogares (2004-2025)",
    "engel_elasticidad_tiempo_2004_2025": "Curvas de Engel: elasticidades en el tiempo",
    "engel_elasticidades_2025": "Curvas de Engel por grupo de gasto (2025)",
    "corr_between_within_pobreza": "Qué acompaña a la pobreza: entre y dentro de departamentos",
    "brecha_ingreso_etnico_tiempo": "Brecha de ingreso por origen étnico",
    "poblacion_indigena_2004_2025": "Población indígena: pobreza e ingreso (2004-2025)",
    "jefatura_pobreza_tiempo": "Hogares con jefa mujer y pobreza",
    "income_change_ranked": "Provincias que ganaron y perdieron ingreso (2021-2025)",
    "validation_income_gasto": "Validación: ingreso y gasto vs cifras oficiales",
    "scatter_edu_pobreza_dep_2025": "Educación vs pobreza por departamento (2025)",
    "sintesis_departamento_2025": "Síntesis departamental: todos los indicadores (2025)",
    "dept_income_social_vote": "Ingreso, programas sociales y voto por departamento",
    "district_vote_2021_2026": "Voto de izquierda por distrito: 2021 vs 2026",
    "trust_income_vote_dept_2021": "Confianza, ingreso y voto 2021 por departamento",
    "trust_income_vote_dept_2026": "Confianza, ingreso y voto 2026 por departamento",
    "trust_vote_dept_2021": "Confianza institucional y voto 2021",
    "trust_vote_dept_2026": "Confianza institucional y voto 2026",
    # ---- ENAHO: hogar, vivienda, consumo
    "bienes_durables_decil_2025": "Bienes durables por decil de ingreso (2025)",
    "bienes_durables_difusion_2004_2025": "Difusión de bienes durables (2004-2025)",
    "calidad_vivienda_2004_2025": "Calidad de la vivienda (2004-2025)",
    "combustible_cocina_2004_2025": "Con qué cocinan los hogares (2004-2025)",
    "vivienda_servicios_2004_2025": "Agua, desagüe y luz en la vivienda (2004-2025)",
    "cuidados_personales_tiempo": "Gasto en cuidado personal (2004-2025)",
    # ---- ENAHO: salud y demografia
    "atencion_salud_tiempo": "Dónde se atienden los peruanos cuando enferman",
    "salud_cronica_discapacidad_2004_2025": "Enfermedad crónica y discapacidad (2004-2025)",
    "seguro_salud_2004_2025": "Cobertura de seguro de salud (2004-2025)",
    "sis_expansion": "La expansión del SIS (2004-2025)",
    "social_coverage_by_decile_2025": "Programas sociales por decil de ingreso (2025)",
    "transferencias_cobertura_2013_2025": "Cobertura de transferencias públicas (2013-2025)",
    "demographic_transition": "Transición demográfica por departamento",
    "transicion_demografica_2004_2025": "Transición demográfica del Perú (2004-2025)",
    "migracion_interna_tiempo": "Migración interna reciente por edad",
    # ---- ENAHO: sociedad y confianza
    "confianza_edad_tiempo_2007_2025": "Confianza institucional por edad (2007-2025)",
    "confianza_educacion_tiempo_2007_2025": "Confianza institucional por educación (2007-2025)",
    "confianza_grupos_tiempo_2007_2025": "Confianza institucional por grupos (2007-2025)",
    "confianza_region_tiempo_2007_2025": "Confianza institucional por región (2007-2025)",
    "trust_by_institution_2025": "Confianza por institución (2025)",
    "participacion_2025": "Participación en organizaciones: pobres y no pobres (2025)",
    "participacion_organizaciones_2004_2025": "Participación en organizaciones (2004-2025)",
    # ---- EPEN / EPE / BCRP
    "bcrp_desempleo_lima": "Desempleo de Lima: serie oficial BCRP",
    "bcrp_lima_2026": "Lima 2026: indicadores oficiales BCRP",
    "bcrp_subempleo_lima": "Subempleo de Lima: serie oficial BCRP",
    "ipc_lima_2009base": "IPC de Lima (base 2009)",
    "ipc_lima_linked": "IPC de Lima empalmado a soles de 2001",
    "epen_ciudades_2025": "Empleo por ciudad (2025)",
    "epen_dpto_advanced_2022_2025": "Salario mínimo y distribución salarial por departamento",
    "epen_dpto_annual_2022_2025": "Empleo por departamento: panel anual (2022-2025)",
    "epen_dpto_econometrics_2022_2025": "Retorno a la educación y penalidad informal por departamento",
    "epen_dpto_indicadores2_2022_2025": "Participación laboral por sexo y departamento",
    "epen_dpto_theil_urbano_2022_2025": "Desigualdad salarial urbano-rural por departamento",
    "epen_econ_summary": "Resumen econométrico del mercado laboral",
    "epen_informal_sector_dpto_2025": "Informalidad por sector y departamento (2025)",
    "epen_lima_desempleo_2001_2026": "Desempleo de Lima: réplica vs oficial (2001-2026)",
    "epen_lima_educ_movil_2022_2026": "Ingreso real por nivel educativo en Lima",
    "epen_lima_empleo_trim_2001_2022": "Lima: empleo en trimestre móvil (2001-2022)",
    "epen_lima_estructura_trim_2001_2022": "Lima: estructura del empleo trimestral (2001-2022)",
    "epen_lima_informalidad_trim_2001_2022": "Lima: informalidad trimestral (2001-2022)",
    "epen_lima_ingresos_grupos_trim_2001_2022": "Lima: ingresos por grupos, trimestre móvil",
    "epen_lima_modern_annual_2022_2025": "Lima: indicadores anuales EPEN (2022-2025)",
    "epen_lima_movil_modern_2022_2026": "Lima: trimestre móvil EPEN (2022-2026)",
    "epen_lima_series_2001_2026": "Lima: serie larga empalmada (2001-2026)",
    "epen_sectores_2022_2025": "Empleo nacional por sector (2022-2025)",
    "epen_sectores_dpto_2025": "Empleo por sector y departamento (2025)",
    "epen_theil_decomp_2025": "Desigualdad salarial: descomposición de Theil (2025)",
    "epen_wage_curve_2022_2025": "Curva de salarios: desempleo local y salario",
    # ---- Panel (tablas unicas)
    "panel_departamento_2004_2025": "Panel de indicadores por departamento (2004-2025)",
    "panel_indicators": "Panel de indicadores nacionales",
    "panel_validation_poverty": "Validación del panel contra la pobreza oficial",
    "panel_evento_hijo_empleo_profile_madre": "Empleo de la madre alrededor del primer hijo",
    "panel_evento_hijo_empleo_profile_padre": "Empleo del padre alrededor del primer hijo",
    "income_real_national": "Ingreso real per capita nacional (2004-2025)",
    "gini_nacional_tiempo": "Desigualdad: Gini del ingreso (2004-2025)",
    "gini_departamento_tiempo": "Gini del ingreso por departamento",
    "migracion_od_departamento": "Migración interna: red entre departamentos",
    "empleo_sector_flujo_2007_2011": "Movilidad laboral: red de cambios de sector (2007-2011)",
    "income_real_province_2021_2025": "Ingreso real por provincia (2021 vs 2025)",
    "income_real_district_2021_2025": "Ingreso real por distrito (2021 vs 2025)",
    "official_poverty_replication": "Pobreza: replica propia vs oficial INEI",
    "gic_periodos": "Quién ganó con el crecimiento: curva de incidencia (2004-2025)",
    "voto_keiko_distrito_2021_2026": "Voto por Keiko Fujimori por distrito: 2021 vs 2026",
    "censo_educacion_1981_2017": "Educación a través de los censos (1981-2017)",
    "censo_lengua_materna_1981_2017": "Lengua materna a través de los censos (1981-2017)",
    "censo_urbanizacion_1993_2017": "Urbanización del Perú: tres censos (1993-2017)",
    "censo_urbanizacion_departamento": "Urbanización por departamento (censos 1993-2017)",
    "censo_lengua_departamento": "Lengua originaria por departamento (censos 1981-2017)",
    "paises_gini_tiempo_wdi": "Desigualdad: Perú vs vecinos (Gini, Banco Mundial)",
    "paises_pobreza685_wdi": "Pobreza comparable: Perú vs vecinos ($6.85/día, Banco Mundial)",
    "voto_keiko_departamento": "Voto por Keiko Fujimori por departamento (2021 y 2026)",
    "income_percentiles_tiempo": "Ingreso real por percentil: del p10 al p90 (2004-2025)",
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
    key = stem.lstrip("_")
    if key in _TITLES:
        return _TITLES[key]
    # windowed panel family -> family title + its re-interview window
    m = re.match(r"^(.*)[_-](\d{4})[_-](\d{4})$", key)
    if m and m.group(1) in _FAMILIES:
        return f"{_FAMILIES[m.group(1)]} ({m.group(2)}-{m.group(3)})"
    t = stem.lstrip("_")
    # drop trailing year ranges like _2004_2025 / _2007-2011 / _2025
    t = re.sub(r"[_-](\d{4})([_-]\d{4})?$", "", t)
    t = t.replace("_", " ").strip()
    return t[:1].upper() + t[1:] if t else stem
