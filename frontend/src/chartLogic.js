// Heuristics that turn an arbitrary analytical table into a sensible chart.
import { PALETTE, SEQ, tokens, tooltip, FONT } from './echartsTheme'

const TEMPORAL = ['year', 'anio', 'ano', 'ym', 'periodo', 'period', 'trimestre', 'fecha', 'window', 'label']

// null/'' -> NaN (so Number.isFinite filters them out; Number(null) is 0!)
export function toNum(v) {
  return (v == null || v === '') ? NaN : Number(v)
}

export function isNumeric(type) {
  if (!type) return false
  const t = type.toUpperCase()
  return /INT|DOUBLE|DECIMAL|FLOAT|REAL|NUMERIC|BIGINT|HUGEINT/.test(t)
}

// pick the default x column: first temporal-looking, else first non-numeric,
// else the first column.
const NAME_KEYS = ['industria', 'institution', 'institucion', 'nombre', 'name',
  'ciudad', 'producto', 'cultivo', 'sector', 'grupo', 'categoria', 'nivel',
  'nivel_educativo', 'departamento']
export function guessX(columns, types) {
  const lower = columns.map((c) => c.toLowerCase())
  for (const key of TEMPORAL) {
    const i = lower.findIndex((c) => c === key || c.startsWith(key))
    if (i >= 0) return columns[i]
  }
  // prefer a human name column (e.g. 'industria') over an id/code column
  const ni = lower.findIndex((c) => NAME_KEYS.includes(c))
  if (ni >= 0) return columns[ni]
  const cat = columns.find((c) => !isNumeric(types[c]))
  return cat || columns[0]
}

export function numericCols(columns, types, exclude = []) {
  return columns.filter((c) => isNumeric(types[c]) && !exclude.includes(c))
}

// sample-size / id / weight columns that shouldn't be plotted by default
// (they stay selectable, just off unless the user turns them on)
const COUNT_LIKE = /^(n|nn|obs|count|total|wt|peso|pop|poblacion|population|id|codigo|cod|code|cluster|caseid)$/i
export function isCountLike(col) {
  return COUNT_LIKE.test(col.trim())
}

// helper / internal columns that shouldn't be offered as chart series
const HIDE = new Set(['cob_peso', 'wt', 'wt_raw', 'cluster', 'caseid', 'codigo',
  'n_obs', 'n_depto', 'n_hh', 'n_m', 'n_h', 'waves', 'p103_missing', 'fuente',
  'codciudad', 'oficial', 'pet', 'release', 'wave', 'window'])
export function isHiddenSeries(col) {
  return HIDE.has(col) || col === 'n' || col.endsWith('_missing') || col.endsWith('_raw')
}

// choose default series: numeric, not the x, not count-like, not hidden
export function defaultSeries(columns, types, exclude = []) {
  const nums = numericCols(columns, types, exclude)
  const signal = nums.filter((c) => !isCountLike(c) && !isHiddenSeries(c))
  const pick = signal.length ? signal : nums.filter((c) => !isHiddenSeries(c))
  return pick.slice(0, pick.length <= 6 ? pick.length : 4)
}

// ---- human-readable labels for cryptic column names --------------------
const DEPT_NAMES = ['', 'Amazonas', 'Ancash', 'Apurimac', 'Arequipa', 'Ayacucho',
  'Cajamarca', 'Callao', 'Cusco', 'Huancavelica', 'Huanuco', 'Ica', 'Junin',
  'La Libertad', 'Lambayeque', 'Lima', 'Loreto', 'Madre de Dios', 'Moquegua',
  'Pasco', 'Piura', 'Puno', 'San Martin', 'Tacna', 'Tumbes', 'Ucayali']
export function deptName(code) {
  const i = Number(code)
  return Number.isInteger(i) && i >= 1 && i <= 25 ? DEPT_NAMES[i] : String(code)
}

const LABELS = {
  adol_madre_pct: 'Madres adolescentes (%)', adol_madre: 'Madres adolescentes (%)',
  va_x_trab: 'VA por trabajador', va: 'Valor agregado', trab: 'Trabajadores',
  ceb: 'Hijos por mujer', hijos_ceb: 'Hijos por mujer', hijos_nacidos: 'Hijos por mujer',
  tasa_desempleo: 'Tasa de desempleo', tasa_actividad: 'Tasa de actividad',
  tasa_informalidad: 'Informalidad (%)', ing_nominal: 'Ingreso nominal',
  ingtotp: 'Ingreso laboral', real_pc_income_national: 'Ingreso real per cápita',
  poverty_pct: 'Pobreza (%)', official_poverty: 'Pobreza oficial INEI (%)',
  extreme_pct: 'Pobreza extrema (%)', official_extreme: 'Extrema oficial INEI (%)',
  educ_anios: 'Años de educación', educ: 'Años de educación',
  superior_pct: 'Educación superior (%)', desnutricion: 'Desnutrición crónica (%)',
  anticon_mod: 'Anticoncepción moderna (%)', edad_1er_hijo: 'Edad al primer hijo',
  edad_primer_hijo: 'Edad al primer hijo', anemia: 'Anemia infantil (%)',
  parto_inst: 'Parto institucional (%)', tfr: 'Tasa de fecundidad',
  urban: 'Urbano', rural: 'Rural', urbano: 'Urbano',
  poblacion: 'Población', population: 'Población', quintil: 'Quintil de riqueza',
  value: 'Valor', valor: 'Valor', pobreza: 'Pobreza (%)', pobreza_extrema: 'Pobreza extrema (%)',
  analfabetismo_15: 'Analfabetismo (%)', ingreso_real_pc: 'Ingreso real per cápita',
  lengua_indigena: 'Lengua indígena (%)', pct_sis: 'Afiliación SIS (%)',
  pct_60mas: 'Población 60+ (%)', educ_anios_25: 'Años de educación (25+)',
  // vivienda (verified in source builder, validated vs INEI)
  p110: 'Agua de red pública (dentro)', p1121: 'Alumbrado eléctrico',
  p1142: 'Teléfono celular',
  // panel poverty dynamics (single-row composition tables)
  chronic_pct: 'Crónica', transient_pct: 'Transitoria', never_pct: 'Nunca pobre',
  ever_poor_pct: 'Alguna vez pobre', annual_static_pct: 'Pobreza anual (estática)',
  poor_0w_pct: 'Pobre 0 de 5 años', poor_1w_pct: 'Pobre 1 de 5 años',
  poor_2w_pct: 'Pobre 2 de 5 años', poor_3w_pct: 'Pobre 3 de 5 años',
  poor_4w_pct: 'Pobre 4 de 5 años', poor_5w_pct: 'Pobre 5 de 5 años',
  anios_desde_hijo: 'Años desde el 1er hijo', empleo_pct: 'Empleo (%)',
  desempleo: 'Desempleo (%)', informalidad: 'Informalidad (%)', ingreso: 'Ingreso laboral',
  ciudad: 'Ciudad', cohorte: 'Cohorte de nacimiento', decil: 'Decil de ingreso',
  // Engel elasticities by ENAHO gran-grupo (i01=Alimentos, i05/i07 confirmed in builder)
  i01: 'Alimentos', i02: 'Vestido y calzado', i03: 'Alquiler, vivienda y combustible',
  i04: 'Muebles y enseres', i05: 'Salud', i06: 'Transporte y comunicaciones',
  i07: 'Esparcimiento, educación y cultura', i08: 'Otros bienes y servicios',
  // EEA concentration
  cr4: 'CR4 (4 mayores, %)', cr8: 'CR8 (8 mayores, %)', hhi: 'Índice HHI',
  ventas_mmM: 'Ventas (mil M S/)', industria: 'Industria', sec: 'Sector',
  // epen econ summary (Oaxaca + Mincer + wage curve)
  brecha_total_log: 'Brecha de género (log)', explicada_log: 'Parte explicada (composición)',
  no_explicada_log: 'Parte no explicada (discriminación)',
  mincer_nacional_pct: 'Retorno a la educación (%/año)',
  wage_curve_elasticidad: 'Elasticidad curva de salarios',
  pct_trust: 'Confianza (%)', institution: 'Institución', pct_empleo: 'Empleo (%)',
  pct_informal: 'Informalidad (%)', ing_medio: 'Ingreso medio', pct_sold: 'Vendido al mercado (%)',
  share: 'Participación (%)', share_fem: 'Participación femenina (%)', ratio: 'Ratio salarial (M/H)',
}
const SUFFIX = [
  ['_pct', ' (%)'], ['_h', ' (hombres)'], ['_m', ' (mujeres)'],
  ['_joven', ' (jóvenes)'], ['_adulto', ' (adultos)'], ['_mayor', ' (mayores)'],
  ['_pc', ' per cápita'],
]
export function labelFor(col) {
  if (LABELS[col]) return LABELS[col]
  let c = col, suff = ''
  for (const [s, l] of SUFFIX) {
    if (c.endsWith(s) && c.length > s.length) { suff = l; c = c.slice(0, -s.length); break }
  }
  if (LABELS[c]) return LABELS[c] + suff
  c = c.replace(/_/g, ' ').trim()
  return (c.charAt(0).toUpperCase() + c.slice(1)) + suff
}

// Refine the default series using the actual data: if the candidate columns
// span wildly different magnitudes (e.g. a count, a total in billions, and a
// ratio) plotting them together is unreadable, so fall back to a single series
// — preferring the one whose name matches the table title.
export function smartDefaultSeries(rows, candidates, title = '') {
  if (candidates.length <= 1 || !rows.length) return candidates
  const median = (c) => {
    const v = rows.map((r) => Math.abs(Number(r[c])))
      .filter((x) => Number.isFinite(x) && x > 0).sort((a, b) => a - b)
    return v.length ? v[Math.floor(v.length / 2)] : 0
  }
  const meds = candidates.map(median).filter((x) => x > 0)
  const keepAll = candidates.slice(0, candidates.length <= 6 ? candidates.length : 4)
  if (meds.length < 2 || Math.max(...meds) / Math.min(...meds) <= 30) return keepAll

  // a series that is constant across rows is a useless default (e.g. a total
  // that is the same for every group) — pick from the varying ones instead.
  const range = (c) => {
    const v = rows.map((r) => toNum(r[c])).filter(Number.isFinite)
    return v.length ? Math.max(...v) - Math.min(...v) : 0
  }
  const varying = candidates.filter((c) => range(c) > 1e-9)
  const pool = varying.length ? varying : candidates
  const words = (title.toLowerCase().match(/[a-záéíóúñ]{4,}/gi) || [])
  const scored = pool.map((c) => {
    const hay = (labelFor(c) + ' ' + c).toLowerCase()
    let score = words.reduce((s, w) => s + (hay.includes(w) ? w.length : 0), 0)
    if (title.toLowerCase().includes(c.toLowerCase())) score += 5 // e.g. "(CR4)"
    if (/_x_|pct|per_|productiv/.test(c)) score += 0.5 // nudge toward derived metrics
    if (/(^|_)(chg|change|delta|diff|var)(_|$)/i.test(c)) score -= 4 // levels over changes
    return [c, score]
  }).sort((a, b) => b[1] - a[1])
  return [scored[0][1] > 0 ? scored[0][0] : pool[0]]
}

// compact number formatting for axes / tooltips
export function fmtNum(v) {
  if (v == null || Number.isNaN(v)) return ''
  const a = Math.abs(v)
  if (a >= 1e6) return (v / 1e6).toFixed(a >= 1e7 ? 0 : 1) + ' M'
  if (a >= 1e4) return Math.round(v).toLocaleString('es-PE')
  if (Number.isInteger(v)) return String(v)
  return (+v.toFixed(2)).toString()
}

export function isTemporal(col) {
  if (!col) return false
  const c = col.toLowerCase()
  return TEMPORAL.some((k) => c === k || c.startsWith(k))
}

// default chart type from the shape of the data
export function guessChartType(x, columns, types) {
  return isTemporal(x) ? 'line' : 'bar'
}

// Build an ECharts option from rows + chosen encoding.
export function buildOption({ rows, x, series, type, ytitle, xIsDept, rankBars }) {
  const t = tokens()
  const axisColor = t.axis
  const gridColor = t.grid
  const horizontal = type === 'barh'
  const stacked = type === 'stacked'
  const base = type === 'barh' ? 'bar' : stacked ? 'line' : type

  // ranked category bars: sort by the primary series and cap the long tail
  let workRows = rows, capped = 0
  if (rankBars && series.length && base === 'bar') {
    workRows = [...rows].sort((a, b) => (toNum(b[series[0]]) || -1e15) - (toNum(a[series[0]]) || -1e15))
    if (workRows.length > 30) { capped = workRows.length; workRows = workRows.slice(0, 30) }
  }
  const cats = workRows.map((r) =>
    xIsDept ? deptName(r[x]) : (typeof r[x] === 'string' ? labelFor(r[x]) : r[x]))

  const seriesArr = series.map((s, i) => ({
    name: labelFor(s),
    type: base,
    data: workRows.map((r) => r[s]),
    stack: stacked ? 'composicion' : undefined,
    smooth: base === 'line' ? (stacked ? 0.15 : 0.25) : false,
    showSymbol: stacked ? false : rows.length <= 40,
    symbolSize: 6,
    lineStyle: base === 'line' ? { width: stacked ? 1 : 2.4 } : undefined,
    areaStyle: stacked ? { opacity: 0.78 }
      : (base === 'line' && series.length === 1 ? { opacity: 0.08 } : undefined),
    barMaxWidth: 46,
    itemStyle: { color: PALETTE[i % PALETTE.length], borderRadius: base === 'bar' ? 3 : 0 },
    // value labels on small single-series bar charts (heterogeneous summaries)
    label: (base === 'bar' && series.length === 1 && workRows.length <= 12)
      ? { show: true, position: horizontal ? 'right' : 'top', color: t.text,
          fontSize: 11, fontWeight: 600, formatter: (p) => fmtNum(p.value) }
      : undefined,
    emphasis: { focus: 'series' },
  }))

  // subtle COVID-2020 marker on temporal line charts
  if (base === 'line' && !horizontal) {
    let covid = cats.find((c) => String(c) === '2020')
    if (!covid) {
      const y20 = cats.filter((c) => String(c).startsWith('2020'))
      covid = y20.find((c) => String(c) === '202003') || y20[Math.floor(y20.length / 2)]
    }
    if (covid != null && seriesArr[0]) {
      seriesArr[0].markLine = {
        symbol: 'none', silent: true,
        lineStyle: { color: axisColor, type: 'dashed', width: 1, opacity: 0.5 },
        label: { formatter: 'COVID', color: axisColor, fontSize: 10, position: 'insideEndTop' },
        data: [{ xAxis: covid }],
      }
    }
  }

  const catAxis = {
    type: 'category', data: cats, boundaryGap: base === 'bar',
    axisLine: { lineStyle: { color: gridColor } },
    axisLabel: { color: axisColor, hideOverlap: true,
      rotate: !horizontal && cats.length > 12 && typeof cats[0] === 'string' ? 35 : 0 },
    axisTick: { show: false },
  }
  const valAxis = {
    type: 'value', name: ytitle ? labelFor(ytitle) : '',
    nameTextStyle: { color: axisColor, align: horizontal ? 'center' : 'left' },
    axisLabel: { color: axisColor, formatter: (v) => fmtNum(v) },
    splitLine: { lineStyle: { color: gridColor } },
    axisLine: { show: false }, axisTick: { show: false },
  }

  return {
    color: PALETTE,
    textStyle: { fontFamily: FONT },
    title: capped ? { text: `Top 30 de ${capped}`, right: 8, top: 4,
      textStyle: { fontSize: 11, fontWeight: 600, color: axisColor } } : undefined,
    grid: {
      left: horizontal && typeof cats[0] === 'string'
        ? Math.min(240, 8 * Math.max(...cats.map((c) => String(c).length))) : 64,
      right: 24, top: series.length > 1 ? 52 : 30, bottom: 64,
    },
    tooltip: { ...tooltip('axis'), valueFormatter: (v) => fmtNum(v) },
    legend: series.length > 1
      ? { top: 12, textStyle: { color: axisColor }, type: 'scroll' } : undefined,
    dataZoom: (base === 'line' && cats.length > 30)
      ? [{ type: 'inside' }, { type: 'slider', height: 16, bottom: 30 }] : undefined,
    xAxis: horizontal ? valAxis : catAxis,
    yAxis: horizontal ? catAxis : valAxis,
    series: seriesArr,
    animationDuration: 500,
  }
}

// Clean quintile/matrix axis labels: q1_destino -> Q1, q3_origen -> Q3.
export function matLabel(c) {
  const m = String(c).match(/^q(\d)/i)
  if (m) return 'Q' + m[1]
  return labelFor(String(c).replace(/_?(origen|destino|from|to)$/i, ''))
}

// Build a heatmap for a square transition/mobility matrix.
export function buildHeatmapOption({ rows, rowKey, cols, xName = 'Destino', yName = 'Origen' }) {
  const t = tokens()
  const yLabels = rows.map((r) => matLabel(r[rowKey]))
  const xLabels = cols.map(matLabel)
  const data = []
  let max = 0
  rows.forEach((r, ri) => cols.forEach((c, ci) => {
    const v = toNum(r[c])
    if (Number.isFinite(v)) { data.push([ci, ri, +v.toFixed(1)]); if (v > max) max = v }
  }))
  return {
    textStyle: { fontFamily: FONT },
    tooltip: {
      position: 'top', backgroundColor: t.tooltipBg, borderColor: t.tooltipBorder,
      textStyle: { color: t.text },
      formatter: (p) => `${yName} ${yLabels[p.value[1]]} → ${xName} ${xLabels[p.value[0]]}<br/><b>${p.value[2]}</b>`,
    },
    grid: { left: 96, right: 24, top: 44, bottom: 56 },
    xAxis: {
      type: 'category', data: xLabels, position: 'top', name: xName, nameGap: 24,
      nameTextStyle: { color: t.axis, fontWeight: 700 },
      axisLine: { show: false }, axisTick: { show: false }, axisLabel: { color: t.axis },
    },
    yAxis: {
      type: 'category', data: yLabels, inverse: true, name: yName, nameGap: 12,
      nameTextStyle: { color: t.axis, fontWeight: 700, align: 'right' },
      axisLine: { show: false }, axisTick: { show: false }, axisLabel: { color: t.axis },
    },
    visualMap: {
      min: 0, max: Math.ceil(max / 10) * 10, calculable: true, orient: 'horizontal',
      left: 'center', bottom: 8, itemHeight: 90, inRange: { color: SEQ.light },
      textStyle: { color: t.axis },
    },
    series: [{
      type: 'heatmap', data,
      label: { show: true, color: '#34291c', fontSize: 11, fontWeight: 600, formatter: (p) => p.value[2] },
      itemStyle: { borderColor: '#fffdf7', borderWidth: 2, borderRadius: 3 },
      emphasis: { itemStyle: { shadowBlur: 8, shadowColor: 'rgba(0,0,0,.2)' } },
    }],
    animationDuration: 500,
  }
}

// Detect a TRUE transition matrix: one label column + N numeric columns + N
// rows, AND the same categories on both axes (rows ≈ columns after cleaning).
// This rejects category tables that merely happen to be square.
export function matrixInfo(columns, types, rows) {
  const nums = columns.filter((c) => isNumeric(types[c]))
  const label = columns.find((c) => !isNumeric(types[c]))
  if (!label || nums.length < 3 || rows.length !== nums.length) return null
  const colSet = new Set(nums.map(matLabel))
  const rowLabels = rows.map((r) => matLabel(r[label]))
  const overlap = rowLabels.filter((l) => colSet.has(l)).length
  if (overlap >= nums.length - 1) return { rowKey: label, cols: nums }
  return null
}

// Detect a from/to transition table.
export function fromToInfo(columns) {
  const lc = columns.map((c) => c.toLowerCase())
  const fi = lc.indexOf('from'), ti = lc.indexOf('to')
  if (fi >= 0 && ti >= 0) return { from: columns[fi], to: columns[ti] }
  return null
}

// Build a choropleth option. `data` = [{name, value}], mapName registered on echarts.
export function buildMapOption({ data, mapName, title, min, max }) {
  const t = tokens()
  const ramp = SEQ.light
  return {
    textStyle: { fontFamily: FONT },
    tooltip: {
      ...tooltip('item'),
      formatter: (p) => {
        const v = p.value
        return `<b>${p.name}</b><br/>${title}: ` +
          (v == null || Number.isNaN(v) ? 'sin dato'
            : (Math.abs(v) >= 100 ? Math.round(v).toLocaleString() : v.toFixed(2)))
      },
    },
    visualMap: {
      type: 'continuous', min: min ?? 0, max: max ?? 1,
      left: 16, bottom: 24, calculable: true,
      itemWidth: 12, itemHeight: 150,
      text: ['alto', 'bajo'],
      textStyle: { color: t.axis, fontSize: 11 },
      inRange: { color: ramp },
    },
    series: [{
      type: 'map', map: mapName, roam: true,
      data,
      nameProperty: 'name',
      label: { show: false },
      itemStyle: { borderColor: t.mapBorder, borderWidth: 0.6, areaColor: t.mapEmpty },
      emphasis: {
        label: { show: true, color: t.mapLabel, fontSize: 11.5, fontWeight: 700 },
        itemStyle: { areaColor: '#157a6e' },
      },
      select: { disabled: true },
    }],
    animationDuration: 500,
  }
}
