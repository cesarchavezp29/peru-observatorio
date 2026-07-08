// Curated editorial content. Every table/column reference is real and the
// numbers are pulled live from the API — nothing here is hardcoded data.

// Topic navigation metadata: icon + a question a NON-economist would ask.
// Keys mirror catalog.TOPICS on the backend.
export const TOPIC_META = {
  pobreza: { icon: '⚖️', desc: '¿Cuántos peruanos son pobres y qué tan repartida está la torta?' },
  ingreso: { icon: '💰', desc: '¿Cuánto gana y en qué gasta una familia peruana?' },
  empleo: { icon: '👷', desc: '¿Quién trabaja, en qué, y cuánto le pagan?' },
  educacion: { icon: '🎓', desc: '¿Cuánto estudian los peruanos y quiénes llegan más lejos?' },
  salud: { icon: '🩺', desc: 'Salud, fertilidad, migración y cómo cambia la población.' },
  sociedad: { icon: '🗳️', desc: '¿En quién confiamos, cómo votamos y a quién ayuda el Estado?' },
  vivienda: { icon: '🏠', desc: '¿Cómo son las casas: agua, luz, con qué se cocina?' },
  agro: { icon: '🌾', desc: 'Qué se siembra, qué se cría y cuánto llega al mercado.' },
  empresas: { icon: '🏭', desc: 'El lado de las empresas: ventas, productividad y salarios.' },
  territorio: { icon: '🗺️', desc: 'Todos los indicadores lado a lado, región por región.' },
}

// Per-section hero: a few headline indicators + a featured lead chart.
export const SECTION_HERO = {
  enaho: {
    kpis: [
      { table: 'official_poverty_replication', col: 'poverty_pct', tcol: 'year', label: 'Pobreza monetaria', unit: '%', color: '#c85a34' },
      { table: 'seguro_salud_2004_2025', col: 'Algun seguro de salud', tcol: 'year', label: 'Con algún seguro de salud', unit: '%', color: '#157a6e' },
      { table: 'neet_juvenil_tiempo_2004_2025', col: 'Total', tcol: 'year', label: 'Jóvenes que ni estudian ni trabajan', unit: '%', color: '#9c6b2f' },
    ],
    featured: { table: 'official_poverty_replication', series: 'poverty_pct', x: 'year', type: 'line',
      caption: 'La pobreza monetaria cayó de 58.7% a ~26% en dos décadas, con el salto del COVID en 2020.' },
  },
  endes: {
    kpis: [
      { table: 'endes_indicadores', col: 'tfr', tcol: 'anio', label: 'Fecundidad (hijos por mujer)', unit: '', color: '#157a6e' },
      { table: 'endes_indicadores', col: 'desnutricion', tcol: 'anio', label: 'Desnutrición crónica infantil', unit: '%', color: '#9c6b2f' },
      { table: 'endes_indicadores', col: 'adol_madre', tcol: 'anio', label: 'Maternidad adolescente', unit: '%', color: '#c85a34' },
      { table: 'endes_indicadores', col: 'superior_pct', tcol: 'anio', label: 'Educación superior', unit: '%', color: '#3f5aa6' },
    ],
    featured: { table: 'endes_indicadores', series: 'tfr', x: 'anio', type: 'line',
      caption: 'La fecundidad cruzó el nivel de reemplazo (2.1) hacia 2018 y sigue bajando.' },
  },
  epen: {
    kpis: [
      { table: 'epen_lima_movil_2001_2026', col: 'tasa_desempleo', tcol: 'ym', label: 'Desempleo · Lima', unit: '%', color: '#8a4a6b' },
      { table: 'epen_lima_movil_2001_2026', col: 'tasa_actividad', tcol: 'ym', label: 'Tasa de actividad · Lima', unit: '%', color: '#157a6e' },
      { table: 'epen_lima_movil_2001_2026', col: 'ing_nominal', tcol: 'ym', label: 'Ingreso nominal · Lima', unit: '', color: '#9c6b2f' },
    ],
    featured: { table: 'epen_lima_movil_2001_2026', series: 'tasa_desempleo', x: 'ym', type: 'line',
      caption: 'El desempleo limeño saltó a 16.5% en la pandemia y recién dos años después volvió a ~5%.' },
  },
  panel: {
    stats: [
      { table: 'panel_pobreza_dinamica_2019_2023', col: 'chronic_pct', label: 'Pobreza crónica', unit: '%', color: '#c85a34' },
      { table: 'panel_pobreza_dinamica_2019_2023', col: 'transient_pct', label: 'Pobreza transitoria', unit: '%', color: '#9c6b2f' },
      { table: 'panel_pobreza_dinamica_2019_2023', col: 'never_pct', label: 'Nunca pobre', unit: '%', color: '#157a6e' },
    ],
    note: 'La pobreza es rotacional: muchos más hogares entran y salen de la pobreza que los que quedan atrapados en ella (ventana 2019–2023).',
  },
  eea: {
    featured: { table: 'eea_productividad_sector', series: 'va_x_trab', x: 'sector', type: 'bar',
      caption: 'La productividad —valor agregado por trabajador— varía enormemente entre sectores.' },
  },
}

// Home "Hallazgos": narrated findings, each with a live mini-visual.
export const FINDINGS = [
  {
    kicker: 'Pobreza', title: 'Es rotacional, no fija', link: 'panel/panel_pobreza_dinamica_2007_2011',
    insight: 'Solo 1 de cada 7 hogares es pobre de forma crónica. Muchos más entran y salen de la pobreza de un año a otro.',
    viz: { kind: 'stat3', schema: 'panel', table: 'panel_pobreza_dinamica_2007_2011',
      parts: [{ col: 'chronic_pct', label: 'Crónica', color: '#c85a34' },
        { col: 'transient_pct', label: 'Transitoria', color: '#d99a2b' },
        { col: 'never_pct', label: 'Nunca', color: '#157a6e' }] },
  },
  {
    kicker: 'Salud infantil', title: 'El colapso de la desnutrición', link: 'endes/endes_indicadores',
    insight: 'La desnutrición crónica infantil cayó de 29% a 11% en menos de dos décadas — uno de los grandes logros del período.',
    viz: { kind: 'spark', schema: 'endes', table: 'endes_indicadores', col: 'desnutricion', tcol: 'anio', color: '#9c6b2f' },
  },
  {
    kicker: 'Demografía', title: 'El Perú cruzó el reemplazo', link: 'endes/endes_indicadores',
    insight: 'La fecundidad bajó de 2.5 a 1.7 hijos por mujer, por debajo del nivel de reemplazo generacional.',
    viz: { kind: 'spark', schema: 'endes', table: 'endes_indicadores', col: 'tfr', tcol: 'anio', color: '#157a6e' },
  },
  {
    kicker: 'Empleo', title: 'El golpe del COVID', link: 'epen/epen_lima_movil_2001_2026',
    insight: 'El desempleo en Lima se disparó a 16.5% en 2020 y recién dos años después volvió a su nivel previo de ~5%.',
    viz: { kind: 'spark', schema: 'epen', table: 'epen_lima_movil_2001_2026', col: 'tasa_desempleo', tcol: 'ym', color: '#8a4a6b' },
  },
  {
    kicker: 'Conectividad', title: 'El boom del celular', link: 'enaho/vivienda_servicios_2004_2025',
    insight: 'El acceso a teléfono celular pasó de 16% a 95% de los hogares — la transformación más rápida del hogar peruano.',
    viz: { kind: 'spark', schema: 'enaho', table: 'vivienda_servicios_2004_2025', col: 'p1142', tcol: 'year', color: '#3f5aa6' },
  },
  {
    kicker: 'Elecciones', title: 'La grieta no es pobreza', link: 'enaho/voto_keiko_departamento',
    insight: 'El voto por Keiko Fujimori en 2026 va de 13.7% en Puno a 65.9% en el Callao, pero su correlación con la pobreza departamental es cero. La línea que divide el mapa es etnolingüística y urbana, no económica.',
    viz: { kind: 'spark', schema: 'enaho', table: 'voto_keiko_departamento', col: 'keiko_share_2026', tcol: 'keiko_share_2026', color: '#3f5aa6' },
  },
  {
    kicker: 'Crecimiento', title: 'El crecimiento favoreció a los pobres', link: 'enaho/gic_periodos',
    insight: 'Entre 2004 y 2025 el ingreso real del percentil 5 creció 4.2% al año, el triple que el del percentil 95 (1.4%). La curva baja de izquierda a derecha: cuanto más pobre el hogar, más creció su ingreso.',
    viz: { kind: 'spark', schema: 'enaho', table: 'gic_periodos', col: 'crec_2004_2025', tcol: 'percentil', color: '#c85a34' },
  },
]
