// Heuristics that turn an arbitrary analytical table into a sensible chart.
import { PALETTE, SEQ, tokens, tooltip, FONT } from './echartsTheme'

const TEMPORAL = ['year', 'anio', 'ano', 'ym', 'periodo', 'period', 'trimestre', 'fecha', 'window', 'label']

export function isNumeric(type) {
  if (!type) return false
  const t = type.toUpperCase()
  return /INT|DOUBLE|DECIMAL|FLOAT|REAL|NUMERIC|BIGINT|HUGEINT/.test(t)
}

// pick the default x column: first temporal-looking, else first non-numeric,
// else the first column.
export function guessX(columns, types) {
  const lower = columns.map((c) => c.toLowerCase())
  for (const key of TEMPORAL) {
    const i = lower.findIndex((c) => c === key || c.startsWith(key))
    if (i >= 0) return columns[i]
  }
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
  'n_obs', 'n_depto', 'p103_missing', 'fuente'])
export function isHiddenSeries(col) {
  return HIDE.has(col) || col.endsWith('_missing') || col.endsWith('_raw')
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
export function buildOption({ rows, x, series, type, ytitle, xIsDept }) {
  const t = tokens()
  const axisColor = t.axis
  const gridColor = t.grid
  const cats = rows.map((r) => (xIsDept ? deptName(r[x]) : r[x]))
  const horizontal = type === 'barh'
  const base = type === 'barh' ? 'bar' : type

  const seriesArr = series.map((s, i) => ({
    name: labelFor(s),
    type: base,
    data: rows.map((r) => r[s]),
    smooth: base === 'line' ? 0.25 : false,
    showSymbol: rows.length <= 40,
    symbolSize: 6,
    lineStyle: base === 'line' ? { width: 2.4 } : undefined,
    areaStyle: base === 'line' && series.length === 1
      ? { opacity: 0.08 } : undefined,
    barMaxWidth: 46,
    itemStyle: { color: PALETTE[i % PALETTE.length], borderRadius: base === 'bar' ? 3 : 0 },
    emphasis: { focus: 'series' },
  }))

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
    grid: { left: 64, right: 24, top: series.length > 1 ? 52 : 30, bottom: 64 },
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
