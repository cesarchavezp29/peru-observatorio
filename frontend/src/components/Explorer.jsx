import { useEffect, useMemo, useRef, useState } from 'react'
import { useParams, useNavigate, useSearchParams } from 'react-router-dom'
import { motion } from 'framer-motion'
import { api } from '../api'
import EChart from './EChart'
import MapChart from './MapChart'
import NetworkChart from './NetworkChart'
import FlowMapChart from './FlowMapChart'
import BarRaceChart from './BarRaceChart'
import { deptCode } from './Departamento'
import SectionHero from './SectionHero'
import MiniSpark from './MiniSpark'
import { guessX, numericCols, defaultSeries, smartDefaultSeries, guessChartType, buildOption, buildHeatmapOption, matrixInfo, fromToInfo, flowInfo, isDeptNodes, isNumeric, isTemporal, labelFor, isHiddenSeries, isCountLike, fmtNum, toNum, deptName } from '../chartLogic'

const CHART_TYPES = [
  { k: 'line', l: 'Líneas' },
  { k: 'bar', l: 'Barras' },
  { k: 'barh', l: 'Barras H.' },
]
const MAP_TYPE = { k: 'map', l: 'Mapa' }

const stagger = { hidden: {}, show: { transition: { staggerChildren: 0.035 } } }
const rise = {
  hidden: { opacity: 0, y: 14 },
  show: { opacity: 1, y: 0, transition: { duration: 0.4, ease: [0.22, 0.61, 0.36, 1] } },
}

function DatabaseOverview({ schema }) {
  const nav = useNavigate()
  const [detail, setDetail] = useState(null)
  const [prev, setPrev] = useState({})
  useEffect(() => {
    setDetail(null); setPrev({})
    api.database(schema).then(setDetail).catch(() => {})
    api.previews(schema).then(setPrev).catch(() => {})
  }, [schema])
  if (!detail) return (
    <div className="db-overview">
      <div className="skeleton sk-line" style={{ width: 300, height: 34, marginBottom: 16 }} />
      <div className="table-cards">
        {Array.from({ length: 8 }).map((_, i) =>
          <div key={i} className="skeleton" style={{ height: 74, borderRadius: 12 }} />)}
      </div>
    </div>
  )
  const db = detail.database
  return (
    <div className="db-overview">
      <motion.div className="db-head" style={{ '--accent': db.color }}
        initial={{ opacity: 0, x: -12 }} animate={{ opacity: 1, x: 0 }}
        transition={{ duration: 0.45, ease: [0.22, 0.61, 0.36, 1] }}>
        <h1>{db.title}</h1>
        <div className="db-source" style={{ color: db.color }}>{db.source}</div>
        <p>{db.desc}</p>
      </motion.div>
      <SectionHero schema={schema} />
      <div className="section-label" style={{ marginTop: 36 }}>Todos los indicadores</div>
      {detail.themes.map((t) => (
        <section key={t.theme_key} className="theme-block">
          <h2>{t.theme_label}</h2>
          <motion.div className="table-cards"
            variants={stagger} initial="hidden" animate="show">
            {t.tables.map((tb) => (
              <motion.button key={tb.table} className="table-card" variants={rise}
                whileHover={{ y: -3 }} whileTap={{ scale: 0.98 }}
                style={{ '--accent': db.color }}
                onClick={() => nav(`/db/${schema}/${tb.table}`)}>
                <div className="table-card-title">{tb.title}</div>
                {prev[tb.table]
                  ? <div className="tc-spark"><MiniSpark values={prev[tb.table]} color={db.color} height={34} /></div>
                  : <div className="tc-spark-empty" />}
                <div className="table-card-meta">
                  {tb.n_rows} filas · {tb.n_cols} columnas
                  {tb.mappable && <span className="tc-map"> · mapa</span>}
                </div>
              </motion.button>
            ))}
          </motion.div>
        </section>
      ))}
    </div>
  )
}

function TableExplorer({ schema, table }) {
  const navigate = useNavigate()
  const [meta, setMeta] = useState(null)
  const [data, setData] = useState(null)
  const [err, setErr] = useState(null)
  const [xCol, setXCol] = useState(null)
  const [yCols, setYCols] = useState([])
  const [ctype, setCtype] = useState('line')
  const [showTable, setShowTable] = useState(false)
  const [mapRes, setMapRes] = useState(null)
  const [period, setPeriod] = useState(null)
  const [periods, setPeriods] = useState([])
  const [category, setCategory] = useState(null)
  const [categories, setCategories] = useState([])
  const [matrix, setMatrix] = useState(null)
  const [flow, setFlow] = useState(null)
  const [playing, setPlaying] = useState(false)
  const [copied, setCopied] = useState(false)
  // shareable view state: ?c=<type>&x=<col>&s=<a|b>&cat=<v>&p=<year> — applied
  // once after auto-detection, then kept in sync so the URL is always shareable
  const urlApplied = useRef(false)

  // load meta + data on table change
  useEffect(() => {
    urlApplied.current = false
    setMeta(null); setData(null); setErr(null)
    setMapRes(null); setPeriod(null); setPeriods([])
    setCategory(null); setCategories([]); setMatrix(null); setFlow(null); setPlaying(false)
    let alive = true
    let capMeta, capX, capYs, capCand, capFlow
    api.tableMeta(schema, table).then((m) => {
      if (!alive) return
      const types = m.column_types
      let x = guessX(m.columns, types)
      // ALL plottable candidate series (not just the first 6) so the
      // magnitude-aware default can pick the headline metric wherever it sits
      let cand = numericCols(m.columns, types, [x, m.dept_col])
        .filter((c) => !isCountLike(c) && !isHiddenSeries(c))
      let ys = defaultSeries(m.columns, types, [x, m.dept_col])
      // from/to transition table: x = the ending period, series = the rates
      const ft = fromToInfo(m.columns)
      if (ft) {
        x = ft.to
        cand = m.columns.filter((c) => c !== ft.from && c !== ft.to
          && isNumeric(types[c]) && !isHiddenSeries(c) && !isCountLike(c))
        ys = cand
      }
      capMeta = m; capX = x; capYs = ys; capCand = cand
      setMeta(m); setXCol(x); setYCols(ys)
      // origin->destination flow table -> network (chord) chart
      const fl = flowInfo(m.columns, types, m.n_rows)
      if (fl) setFlow(fl)
      capFlow = fl
      // dept-keyed tables open as a map (avoids a 1..25 code axis)
      setCtype(fl ? 'red' : m.mappable ? 'map' : (ft ? 'line' : guessChartType(x, m.columns, types)))
      // periods for map / flow-map year filtering
      if ((m.mappable || fl) && m.temporal_col) {
        api.distinct(schema, table, m.temporal_col).then((r) => {
          if (!alive) return
          const vals = r.values
          setPeriods(vals)
          // keep a period restored from the URL; default to the latest otherwise
          setPeriod((cur) => cur != null && vals.some((v) => String(v) === String(cur))
            ? vals.find((v) => String(v) === String(cur)) : vals[vals.length - 1])
        }).catch(() => {})
      }
      // long-format indicator selector
      if (m.category_col) {
        api.distinct(schema, table, m.category_col).then((r) => {
          if (!alive) return
          setCategories(r.values)
          setCategory((cur) => cur != null && r.values.some((v) => String(v) === String(cur))
            ? r.values.find((v) => String(v) === String(cur)) : r.values[0])
        }).catch(() => {})
      }
      return api.data(schema, table, {
        order: isTemporal(x) ? x : undefined, limit: 8000,
      })
    }).then((d) => {
      if (!alive || !d) return
      setData(d)
      // geographic flow (departments) -> default to the animated flow map
      if (capFlow && isDeptNodes(d.rows, capFlow)) { setCtype('flowmap'); return }
      // square origin×destination matrix -> heatmap
      const mi = matrixInfo(capMeta.columns, capMeta.column_types, d.rows)
      if (mi && !capMeta.mappable) { setMatrix(mi); setCtype('heat'); return }
      // a single-row table is a composition, not a series -> horizontal bars
      if (d.rows.length === 1 && !capMeta.mappable) { setCtype('barh'); return }
      // many string categories (industries, cities) -> ranked horizontal bars
      if (!capMeta.mappable && !isTemporal(capX)
          && typeof d.rows[0]?.[capX] === 'string' && d.rows.length > 15) setCtype('barh')
      // refine default series now that we can see magnitudes. Consider ALL
      // candidates so the headline metric wins wherever it sits, and apply it
      // to long-format tables too (their value columns can differ in scale).
      if (capMeta && capCand && capCand.length > 1) {
        const src = capMeta.category_col
          ? d.rows.filter((r) => String(r[capMeta.category_col]) === String(d.rows[0][capMeta.category_col]))
          : d.rows
        const refined = smartDefaultSeries(src, capCand, capMeta.title)
        if (refined.length && !(refined.length === capYs.length
            && refined.every((c, i) => c === capYs[i]))) setYCols(refined)
      }
    }).catch((e) => alive && setErr(String(e)))
    return () => { alive = false }
  }, [schema, table])

  const [searchParams, setSearchParams] = useSearchParams()

  // restore a shared view once auto-detection has run (invalid values are
  // ignored; an off-shape chart type gets coerced by the availTypes effect)
  useEffect(() => {
    if (!data || !meta || urlApplied.current) return
    const g = (k) => searchParams.get(k)
    const x = g('x'), s = g('s'), c = g('c'), cat = g('cat'), p = g('p')
    if (x && meta.columns.includes(x)) setXCol(x)
    if (s) {
      const cols = s.split('|').filter((k) => meta.columns.includes(k))
      if (cols.length) setYCols(cols)
    }
    if (c) setCtype(c)
    if (cat != null) setCategory(cat)
    if (p != null) setPeriod(Number.isNaN(+p) ? p : +p)
    urlApplied.current = true
  }, [data, meta]) // eslint-disable-line

  // keep the URL in sync with the current view -> the address is always shareable
  useEffect(() => {
    if (!urlApplied.current || !meta) return
    const p = { c: ctype }
    if (xCol) p.x = xCol
    if (yCols.length) p.s = yCols.join('|')
    if (category != null) p.cat = String(category)
    if (period != null) p.p = String(period)
    setSearchParams(p, { replace: true })
  }, [ctype, xCol, yCols, category, period, meta]) // eslint-disable-line

  const copyLink = () => {
    navigator.clipboard?.writeText(window.location.href)
      .then(() => { setCopied(true); setTimeout(() => setCopied(false), 1800) })
      .catch(() => {})
  }

  // filters shared by chart (client-side) and map (server-side)
  const buildFilters = () => {
    const f = []
    if (meta?.temporal_col && period != null && ctype === 'map')
      f.push({ col: meta.temporal_col, op: 'eq', val: period })
    if (meta?.category_col && category != null)
      f.push({ col: meta.category_col, op: 'eq', val: category })
    return f
  }

  // ▶ play: animate the choropleth through its periods
  useEffect(() => {
    if (!playing || !['map', 'flowmap', 'red'].includes(ctype) || periods.length < 2) return
    const id = setInterval(() => {
      setPeriod((p) => {
        const i = periods.indexOf(p)
        return periods[(i + 1) % periods.length]
      })
    }, 950)
    return () => clearInterval(id)
  }, [playing, ctype, periods])

  // fetch choropleth data when in map mode
  const mapValueCol = yCols[0]
  useEffect(() => {
    if (ctype !== 'map' || !meta?.mappable || !mapValueCol) return
    let alive = true
    const f = buildFilters()
    api.map(schema, table, mapValueCol, f.length ? f : null)
      .then((r) => { if (alive) setMapRes(r) })
      .catch(() => alive && setMapRes(null))
    return () => { alive = false }
  }, [ctype, meta, mapValueCol, period, category, schema, table])

  const types = meta?.column_types || {}
  const rows = data?.rows || []

  // coerce string-numeric cells so charts render
  const cleanRows = useMemo(() => {
    if (!rows.length) return rows
    return rows.map((r) => {
      const o = { ...r }
      for (const c of yCols) {
        const v = o[c]
        if (typeof v === 'string' && v.trim() !== '' && !isNaN(v)) o[c] = Number(v)
      }
      return o
    })
  }, [rows, yCols])

  // for long-format tables, keep only the selected indicator's rows; for flow
  // tables with a year axis, keep only the selected year
  const viewRows = useMemo(() => {
    let r = cleanRows
    if (meta?.category_col && category != null)
      r = r.filter((row) => String(row[meta.category_col]) === String(category))
    if (flow && meta?.temporal_col && period != null)
      r = r.filter((row) => String(row[meta.temporal_col]) === String(period))
    return r
  }, [cleanRows, meta, category, flow, period])

  // a one-row table is a composition: transpose its columns into labelled bars
  const singleRow = ctype !== 'map' && ctype !== 'heat' && viewRows.length === 1
  const option = useMemo(() => {
    if (!viewRows.length || ctype === 'red' || ctype === 'flowmap' || ctype === 'race') return null
    if (ctype === 'heat' && matrix) {
      return buildHeatmapOption({ rows: viewRows, rowKey: matrix.rowKey, cols: matrix.cols })
    }
    if (singleRow) {
      const r = viewRows[0]
      const nums = (meta?.columns || []).filter((c) => isNumeric(types[c]))
      const pct = nums.filter((c) => c.endsWith('_pct'))
      const use = (pct.length ? pct : nums).filter((c) => !isHiddenSeries(c) && !isCountLike(c))
      const trows = use.map((c) => ({ metric: labelFor(c), value: toNum(r[c]) }))
        .filter((d) => Number.isFinite(d.value))
      if (!trows.length) return null
      const horiz = ctype !== 'bar'
      const opt = buildOption({ rows: trows, x: 'metric', series: ['value'],
        type: horiz ? 'barh' : 'bar', ytitle: '' })
      opt.series[0].label = { show: true, position: horiz ? 'right' : 'top',
        color: '#34291c', fontSize: 11, fontWeight: 700, formatter: (p) => fmtNum(p.value) }
      opt.grid.left = horiz ? 168 : opt.grid.left
      opt.grid.right = horiz ? 46 : opt.grid.right
      return opt
    }
    if (!xCol || !yCols.length) return null
    return buildOption({
      rows: viewRows, x: xCol, series: yCols,
      type: ctype === 'scatter' ? 'scatter' : ctype,
      ytitle: yCols.length === 1 ? yCols[0] : '',
      xIsDept: xCol === meta?.dept_col,
      // rank + cap category bars with a long tail (e.g. 112 industries)
      rankBars: !isTemporal(xCol) && xCol !== meta?.dept_col
        && (ctype === 'bar' || ctype === 'barh') && viewRows.length > 15,
    })
  }, [viewRows, xCol, yCols, ctype, meta, singleRow, types, matrix])

  // summary stats for a temporal single-series view
  const summary = useMemo(() => {
    if (ctype === 'map' || ctype === 'flowmap' || ctype === 'red' || flow
      || !isTemporal(xCol) || !yCols.length || viewRows.length < 2) return null
    const col = yCols[0]
    // toNum: nulls stay NaN and drop out (Number(null) is 0 and skewed min/cambio)
    const pts = viewRows.map((r) => toNum(r[col])).filter((v) => Number.isFinite(v))
    if (pts.length < 2) return null
    return {
      col, latest: pts[pts.length - 1], first: pts[0],
      min: Math.min(...pts), max: Math.max(...pts),
    }
  }, [viewRows, xCol, yCols, ctype, flow])

  // chart types available for THIS table's shape (not a fixed set for all)
  const flowGeo = useMemo(() => isDeptNodes(cleanRows, flow), [cleanRows, flow])
  const availTypes = useMemo(() => {
    if (flow) return flowGeo
      ? [{ k: 'flowmap', l: 'Mapa de flujos' }, { k: 'red', l: 'Red' }]
      : [{ k: 'red', l: 'Red' }]
    if (matrix) return [{ k: 'heat', l: 'Matriz' }]
    if (rows.length === 1 && !meta?.mappable) return [{ k: 'bar', l: 'Barras' }, { k: 'barh', l: 'Barras H.' }]
    // dept-keyed tables: map only when temporal (a bar/line would zig-zag across
    // departments within each year); map + dept bars when one row per dept
    if (meta?.mappable) {
      return meta.temporal_col
        ? [{ k: 'map', l: 'Mapa' }, { k: 'race', l: 'Carrera' }]
        : [{ k: 'map', l: 'Mapa' }, { k: 'bar', l: 'Barras' }, { k: 'barh', l: 'Barras H.' }]
    }
    const arr = []
    // 'Líneas' + 'Apilado' only make sense on a temporal / ordered numeric axis
    if (isTemporal(xCol) || isNumeric(types[xCol])) {
      arr.push({ k: 'line', l: 'Líneas' }, { k: 'stacked', l: 'Apilado' })
    }
    arr.push({ k: 'bar', l: 'Barras' }, { k: 'barh', l: 'Barras H.' })
    return arr
  }, [flow, flowGeo, matrix, rows.length, xCol, types, meta])

  // if the current type isn't valid for this shape (e.g. line on a category
  // axis after switching X), fall back to the first sensible one
  useEffect(() => {
    if (availTypes.length && !availTypes.some((t) => t.k === ctype)) setCtype(availTypes[0].k)
  }, [availTypes]) // eslint-disable-line

  // a plain-language caption that explains what the current figure shows
  const caption = useMemo(() => {
    if (!meta) return ''
    if (ctype === 'map' && mapRes?.data?.length) {
      const d = [...mapRes.data].sort((a, b) => b.value - a.value)
      const unit = meta.geo_level === 'prov' ? 'provincia' : 'departamento'
      return `Muestra ${labelFor(mapValueCol).toLowerCase()} por ${unit}. Más alto en ${d[0].name} (${fmtNum(d[0].value)}) y más bajo en ${d[d.length - 1].name} (${fmtNum(d[d.length - 1].value)}).`
    }
    if (ctype === 'heat') return 'Matriz de transición: cada celda es el % que pasa de la fila (origen) a la columna (destino). La diagonal marca la persistencia; fuera de ella, la movilidad.'
    if (ctype === 'race') return `Ranking animado de ${labelFor(mapValueCol).toLowerCase()} por departamento. Cada barra corre y se reordena año a año, del primero al último dato disponible.`
    if ((ctype === 'red' || ctype === 'flowmap') && flow) {
      const es = viewRows.map((r) => ({ s: r[flow.source], t: r[flow.target], v: toNum(r[flow.value]) }))
        .filter((e) => Number.isFinite(e.v) && e.s !== e.t).sort((a, b) => b.v - a.v)
      const top = es[0]
      const nodes = new Set(viewRows.flatMap((r) => [r[flow.source], r[flow.target]])).size
      const lead = ctype === 'flowmap'
        ? `Mapa de flujos entre ${nodes} departamentos.` : `Red de flujos entre ${nodes} nodos.`
      return `${lead} ` + (top
        ? `El mayor flujo es ${top.s} → ${top.t} (${fmtNum(top.v)}). El grosor de cada línea es la magnitud del flujo.` : '')
    }
    const col = yCols[0]
    if (!col || viewRows.length < 2) return ''
    const vals = viewRows.map((r) => ({ x: r[xCol], v: toNum(r[col]) })).filter((o) => Number.isFinite(o.v))
    if (vals.length < 2) return ''
    const nm = (x) => xCol === meta.dept_col ? deptName(x) : (typeof x === 'string' ? labelFor(x) : x)
    if (isTemporal(xCol)) {
      const f = vals[0], l = vals[vals.length - 1]
      const dir = l.v >= f.v ? 'subió' : 'bajó'
      const yr = (x) => String(x).slice(0, 4)
      return `Evolución de ${labelFor(col).toLowerCase()}: ${dir} de ${fmtNum(f.v)} en ${yr(f.x)} a ${fmtNum(l.v)} en ${yr(l.x)}.`
    }
    const s = [...vals].sort((a, b) => b.v - a.v)
    return `${labelFor(col)} por ${labelFor(xCol).toLowerCase()}. Mayor en ${nm(s[0].x)} (${fmtNum(s[0].v)}) y menor en ${nm(s[s.length - 1].x)} (${fmtNum(s[s.length - 1].v)}).`
  }, [meta, viewRows, xCol, yCols, ctype, mapRes, mapValueCol])

  if (err) return <div className="error">No se pudo cargar: {err}</div>
  if (!meta) return <TableSkeleton />

  const allCols = meta.columns
  const numCols = allCols.filter((c) => isNumeric(types[c]))

  const isMap = ctype === 'map'
  const isHeat = ctype === 'heat'
  const chartTypes = availTypes
  const valueCols = numCols.filter((c) =>
    c !== meta.dept_col && c !== meta.temporal_col && !isHiddenSeries(c))
  const seriesCols = numCols.filter((c) => c !== xCol && !isHiddenSeries(c))

  const clickChip = (c) => {
    if (isMap) setYCols([c])
    else setYCols((cur) => cur.includes(c) ? cur.filter((x) => x !== c) : [...cur, c])
  }

  return (
    <div className="explorer">
      <div className="exp-head">
        <div className="exp-crumb">{schema.toUpperCase()}</div>
        <h1>{meta.title}</h1>
        <div className="exp-sub">
          <span>{meta.n_rows} filas · {meta.n_cols} columnas</span>
          {meta.mappable && <span className="exp-badge">mapa disponible</span>}
          <span className="exp-file">{meta.source_file}</span>
          <a className="exp-dl" href={api.downloadUrl(schema, table)}>Descargar CSV</a>
          <button className={'exp-share' + (copied ? ' ok' : '')} onClick={copyLink}
            title="Copia un enlace que reproduce exactamente esta vista">
            {copied ? '✓ Enlace copiado' : '⧉ Compartir vista'}
          </button>
        </div>
      </div>

      <motion.div className="exp-body"
        initial={{ opacity: 0, y: 12 }} animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.4, ease: [0.22, 0.61, 0.36, 1] }}>
        <div className="controls">
          <div className="ctrl">
            <label>Tipo de gráfico</label>
            <div className="seg">
              {chartTypes.map((t) => (
                <button key={t.k} className={ctype === t.k ? 'on' : ''}
                  onClick={() => setCtype(t.k)}>{t.l}</button>
              ))}
            </div>
          </div>
          {meta.category_col && categories.length > 1 && (
            <div className="ctrl">
              <label>Indicador</label>
              <select value={category ?? ''} onChange={(e) => setCategory(
                categories.find((c) => String(c) === e.target.value))}>
                {categories.map((c) => <option key={c} value={c}>{labelFor(c)}</option>)}
              </select>
            </div>
          )}
          {!isMap && !singleRow && !isHeat && ctype !== 'red' && ctype !== 'flowmap' && ctype !== 'race' && (
            <div className="ctrl">
              <label>Eje X</label>
              <select value={xCol} onChange={(e) => {
                const nx = e.target.value
                setXCol(nx); setYCols((ys) => ys.filter((y) => y !== nx))
              }}>
                {allCols.map((c) => <option key={c} value={c}>{labelFor(c)}</option>)}
              </select>
            </div>
          )}
          {(isMap || ctype === 'flowmap' || ctype === 'red') && periods.length > 1 && (
            <div className="ctrl">
              <label>{labelFor(meta.temporal_col)}</label>
              <div className="period-row">
                <button className={'play-btn' + (playing ? ' on' : '')}
                  onClick={() => setPlaying((v) => !v)} title="Animar en el tiempo">
                  {playing ? '❚❚' : '▶'}
                </button>
                <select value={period ?? ''} onChange={(e) => {
                  setPlaying(false)
                  setPeriod(periods.find((p) => String(p) === e.target.value))
                }}>
                  {periods.map((p) => <option key={p} value={p}>{p}</option>)}
                </select>
              </div>
            </div>
          )}
          {singleRow || isHeat || ctype === 'red' || ctype === 'flowmap' || ctype === 'race'
            ? <div className="ctrl grow"><label>Vista</label>
                <div className="single-note">{isHeat
                  ? 'Matriz de transición: cada celda es el % que va de la fila (origen) a la columna (destino).'
                  : ctype === 'race'
                  ? 'Ranking animado: las barras se reordenan solas conforme avanza el año. Usa ❚❚ para pausar.'
                  : ctype === 'flowmap'
                  ? 'Mapa de flujos: las líneas animadas van del departamento de origen al de destino. Arrastra para desplazar y usa la rueda para acercar.'
                  : ctype === 'red'
                  ? 'Red origen → destino: pasa el cursor sobre un nodo para resaltar sus flujos. Arrastra para rotar y usa la rueda para acercar.'
                  : 'Composición de una sola observación — cada barra es una columna de la tabla.'}</div></div>
            : <div className="ctrl grow">
                <label>{isMap ? 'Indicador (color)' : 'Series (eje Y)'}</label>
                <div className="chips">
                  {(isMap ? valueCols : seriesCols).map((c) => (
                    <button key={c} className={'chip' + (yCols.includes(c) ? ' on' : '')}
                      onClick={() => clickChip(c)} title={c}>{labelFor(c)}</button>
                  ))}
                </div>
              </div>}
        </div>

        {summary && (
          <div className="exp-stats">
            <div className="stat-cell"><span className="stat-lbl">Último</span><span className="stat-num">{fmtNum(summary.latest)}</span></div>
            <div className="stat-cell"><span className="stat-lbl">Cambio</span>
              <span className={'stat-num ' + (summary.latest >= summary.first ? 'up' : 'down')}>
                {summary.latest >= summary.first ? '▲' : '▼'} {fmtNum(Math.abs(summary.latest - summary.first))}
              </span></div>
            <div className="stat-cell"><span className="stat-lbl">Máximo</span><span className="stat-num">{fmtNum(summary.max)}</span></div>
            <div className="stat-cell"><span className="stat-lbl">Mínimo</span><span className="stat-num">{fmtNum(summary.min)}</span></div>
            <div className="stat-cell stat-series"><span className="stat-lbl">Serie</span><span className="stat-num-sm">{labelFor(summary.col)}</span></div>
          </div>
        )}

        {caption && <p className="exp-caption">{caption}</p>}

        <div className="chart-wrap">
          {ctype === 'race'
            ? <BarRaceChart rows={viewRows} entityCol={meta.dept_col}
                valueCol={mapValueCol} timeCol={meta.temporal_col} nameFn={deptName} />
            : ctype === 'flowmap' && flow
            ? <FlowMapChart rows={viewRows} flow={flow} />
            : ctype === 'red' && flow
            ? <NetworkChart rows={viewRows} flow={flow} />
            : isMap
            ? (mapRes && mapRes.data.length
                ? <MapChart data={mapRes.data} level={meta.geo_level || 'dept'}
                    title={meta.category_col && category != null ? labelFor(category) : labelFor(mapValueCol)}
                    min={mapRes.min} max={mapRes.max}
                    onSelect={meta.geo_level !== 'prov' ? (nm) => {
                      const c = deptCode(nm)
                      if (c) navigate(`/dpto/${c}`)
                    } : undefined} />
                : <div className="loading">Sin datos para esta selección.</div>)
            : (option ? <EChart option={option} />
                : <div className="loading">Selecciona al menos una serie numérica.</div>)}
        </div>

        <button className="table-toggle" onClick={() => setShowTable((s) => !s)}>
          {showTable ? 'Ocultar' : 'Ver'} datos ({rows.length} filas)
        </button>
        {showTable && (
          <div className="data-table-wrap">
            <table className="data-table">
              <thead><tr>{allCols.map((c) => <th key={c}>{c}</th>)}</tr></thead>
              <tbody>
                {rows.slice(0, 300).map((r, i) => (
                  <tr key={i}>{allCols.map((c) => <td key={c}>{fmt(r[c])}</td>)}</tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </motion.div>
    </div>
  )
}

function TableSkeleton() {
  return (
    <div className="explorer">
      <div className="exp-head">
        <div className="skeleton sk-line" style={{ width: 90 }} />
        <div className="skeleton sk-line" style={{ width: 340, height: 26, margin: '10px 0' }} />
        <div className="skeleton sk-line" style={{ width: 220 }} />
      </div>
      <div className="exp-body">
        <div className="skeleton sk-line" style={{ width: '55%', height: 34 }} />
        <div className="skeleton sk-chart" style={{ marginTop: 18 }} />
      </div>
    </div>
  )
}

function fmt(v) {
  if (v === null || v === undefined) return ''
  if (typeof v === 'number') return Number.isInteger(v) ? v : v.toFixed(2)
  return String(v)
}

export default function Explorer() {
  const { schema, table } = useParams()
  if (!table) return <DatabaseOverview schema={schema} />
  return <TableExplorer key={`${schema}/${table}`} schema={schema} table={table} />
}
