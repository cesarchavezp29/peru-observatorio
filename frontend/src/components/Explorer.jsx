import { useEffect, useMemo, useState } from 'react'
import { useParams, useNavigate } from 'react-router-dom'
import { motion } from 'framer-motion'
import { api } from '../api'
import EChart from './EChart'
import MapChart from './MapChart'
import { guessX, numericCols, defaultSeries, smartDefaultSeries, guessChartType, buildOption, isNumeric, isTemporal, labelFor, isHiddenSeries } from '../chartLogic'

const CHART_TYPES = [
  { k: 'line', l: 'Líneas' },
  { k: 'bar', l: 'Barras' },
  { k: 'barh', l: 'Barras H.' },
  { k: 'scatter', l: 'Dispersión' },
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
  useEffect(() => { setDetail(null); api.database(schema).then(setDetail).catch(() => {}) }, [schema])
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

  // load meta + data on table change
  useEffect(() => {
    setMeta(null); setData(null); setErr(null)
    setMapRes(null); setPeriod(null); setPeriods([])
    setCategory(null); setCategories([])
    let alive = true
    let capMeta, capX, capYs
    api.tableMeta(schema, table).then((m) => {
      if (!alive) return
      const types = m.column_types
      const x = guessX(m.columns, types)
      const ys = defaultSeries(m.columns, types, [x, m.dept_col])
      capMeta = m; capX = x; capYs = ys
      setMeta(m); setXCol(x); setYCols(ys)
      // dept-keyed tables open as a map (avoids a 1..25 code axis)
      setCtype(m.mappable ? 'map' : guessChartType(x, m.columns, types))
      // periods for map filtering
      if (m.mappable && m.temporal_col) {
        api.distinct(schema, table, m.temporal_col).then((r) => {
          if (!alive) return
          const vals = r.values
          setPeriods(vals); setPeriod(vals[vals.length - 1])
        }).catch(() => {})
      }
      // long-format indicator selector
      if (m.category_col) {
        api.distinct(schema, table, m.category_col).then((r) => {
          if (!alive) return
          setCategories(r.values); setCategory(r.values[0])
        }).catch(() => {})
      }
      return api.data(schema, table, {
        order: isTemporal(x) ? x : undefined, limit: 8000,
      })
    }).then((d) => {
      if (!alive || !d) return
      setData(d)
      // refine default series now that we can see magnitudes (skip long-format)
      if (capMeta && !capMeta.category_col && capYs.length > 1) {
        const refined = smartDefaultSeries(d.rows, capYs, capMeta.title)
        if (refined.length && refined.length !== capYs.length) setYCols(refined)
      }
    }).catch((e) => alive && setErr(String(e)))
    return () => { alive = false }
  }, [schema, table])

  // filters shared by chart (client-side) and map (server-side)
  const buildFilters = () => {
    const f = []
    if (meta?.temporal_col && period != null && ctype === 'map')
      f.push({ col: meta.temporal_col, op: 'eq', val: period })
    if (meta?.category_col && category != null)
      f.push({ col: meta.category_col, op: 'eq', val: category })
    return f
  }

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

  // for long-format tables, keep only the selected indicator's rows
  const viewRows = useMemo(() => {
    if (meta?.category_col && category != null)
      return cleanRows.filter((r) => String(r[meta.category_col]) === String(category))
    return cleanRows
  }, [cleanRows, meta, category])

  const option = useMemo(() => {
    if (!xCol || !yCols.length || !viewRows.length) return null
    return buildOption({
      rows: viewRows, x: xCol, series: yCols,
      type: ctype === 'scatter' ? 'scatter' : ctype,
      ytitle: yCols.length === 1 ? yCols[0] : '',
      xIsDept: xCol === meta?.dept_col,
    })
  }, [viewRows, xCol, yCols, ctype, meta])

  if (err) return <div className="error">No se pudo cargar: {err}</div>
  if (!meta) return <TableSkeleton />

  const allCols = meta.columns
  const numCols = allCols.filter((c) => isNumeric(types[c]))

  const isMap = ctype === 'map'
  const chartTypes = meta.mappable ? [...CHART_TYPES, MAP_TYPE] : CHART_TYPES
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
          {!isMap && (
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
          {isMap && periods.length > 1 && (
            <div className="ctrl">
              <label>{meta.temporal_col}</label>
              <select value={period ?? ''} onChange={(e) => setPeriod(
                periods.find((p) => String(p) === e.target.value))}>
                {periods.map((p) => <option key={p} value={p}>{p}</option>)}
              </select>
            </div>
          )}
          <div className="ctrl grow">
            <label>{isMap ? 'Indicador (color)' : 'Series (eje Y)'}</label>
            <div className="chips">
              {(isMap ? valueCols : seriesCols).map((c) => (
                <button key={c} className={'chip' + (yCols.includes(c) ? ' on' : '')}
                  onClick={() => clickChip(c)} title={c}>{labelFor(c)}</button>
              ))}
            </div>
          </div>
        </div>

        <div className="chart-wrap">
          {isMap
            ? (mapRes && mapRes.data.length
                ? <MapChart data={mapRes.data}
                    title={meta.category_col && category != null ? labelFor(category) : labelFor(mapValueCol)}
                    min={mapRes.min} max={mapRes.max} />
                : <div className="loading">Sin datos departamentales para esta selección.</div>)
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
