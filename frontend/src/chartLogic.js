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

// choose default series: numeric, not the x, not count-like; keep a handful
export function defaultSeries(columns, types, exclude = []) {
  const nums = numericCols(columns, types, exclude)
  const signal = nums.filter((c) => !isCountLike(c))
  const pick = signal.length ? signal : nums
  return pick.slice(0, pick.length <= 6 ? pick.length : 4)
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
export function buildOption({ rows, x, series, type, ytitle, dark }) {
  const t = tokens(dark)
  const axisColor = t.axis
  const gridColor = t.grid
  const cats = rows.map((r) => r[x])
  const horizontal = type === 'barh'
  const base = type === 'barh' ? 'bar' : type

  const seriesArr = series.map((s, i) => ({
    name: s,
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
    type: 'value', name: ytitle || '', nameTextStyle: { color: axisColor },
    axisLabel: { color: axisColor },
    splitLine: { lineStyle: { color: gridColor } },
    axisLine: { show: false }, axisTick: { show: false },
  }

  return {
    color: PALETTE,
    textStyle: { fontFamily: FONT },
    grid: { left: 58, right: 24, top: series.length > 1 ? 52 : 30, bottom: 64 },
    tooltip: tooltip(dark, 'axis'),
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
export function buildMapOption({ data, mapName, title, min, max, dark }) {
  const t = tokens(dark)
  const ramp = dark ? SEQ.dark : SEQ.light
  return {
    textStyle: { fontFamily: FONT },
    tooltip: {
      ...tooltip(dark, 'item'),
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
        label: { show: true, color: t.mapLabel, fontSize: 11, fontWeight: 600 },
        itemStyle: { areaColor: dark ? '#e0a53a' : '#e0603a' },
      },
      select: { disabled: true },
    }],
    animationDuration: 500,
  }
}
