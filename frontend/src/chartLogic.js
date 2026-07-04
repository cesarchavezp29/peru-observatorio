// Heuristics that turn an arbitrary analytical table into a sensible chart.

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

export function isTemporal(col) {
  if (!col) return false
  const c = col.toLowerCase()
  return TEMPORAL.some((k) => c === k || c.startsWith(k))
}

// default chart type from the shape of the data
export function guessChartType(x, columns, types) {
  return isTemporal(x) ? 'line' : 'bar'
}

const PALETTE = ['#2563eb', '#e0603a', '#2e9e83', '#e0a53a', '#8256c4',
  '#3aa0e0', '#d1477a', '#5aa02e', '#9c7b3a', '#54617a']

// Build an ECharts option from rows + chosen encoding.
export function buildOption({ rows, x, series, type, ytitle, dark }) {
  const axisColor = dark ? '#8a93a6' : '#5a6472'
  const gridColor = dark ? '#232a38' : '#e7ebf1'
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
    grid: { left: 58, right: 24, top: series.length > 1 ? 52 : 30, bottom: 64 },
    tooltip: { trigger: 'axis', axisPointer: { type: 'shadow' },
      backgroundColor: dark ? '#141a24' : '#fff',
      borderColor: gridColor, textStyle: { color: dark ? '#e6eaf2' : '#1a2230' } },
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
