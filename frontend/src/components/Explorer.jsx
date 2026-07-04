import { useEffect, useMemo, useState } from 'react'
import { useParams, useNavigate } from 'react-router-dom'
import { api } from '../api'
import EChart from './EChart'
import { guessX, numericCols, guessChartType, buildOption, isNumeric, isTemporal } from '../chartLogic'

const CHART_TYPES = [
  { k: 'line', l: 'Líneas' },
  { k: 'bar', l: 'Barras' },
  { k: 'barh', l: 'Barras H.' },
  { k: 'scatter', l: 'Dispersión' },
]

function DatabaseOverview({ schema }) {
  const nav = useNavigate()
  const [detail, setDetail] = useState(null)
  useEffect(() => { setDetail(null); api.database(schema).then(setDetail).catch(() => {}) }, [schema])
  if (!detail) return <div className="loading">Cargando…</div>
  const db = detail.database
  return (
    <div className="db-overview">
      <div className="db-head" style={{ '--accent': db.color }}>
        <h1>{db.title}</h1>
        <div className="db-source">{db.source}</div>
        <p>{db.desc}</p>
      </div>
      {detail.themes.map((t) => (
        <section key={t.theme_key} className="theme-block">
          <h2>{t.theme_label}</h2>
          <div className="table-cards">
            {t.tables.map((tb) => (
              <button key={tb.table} className="table-card"
                onClick={() => nav(`/db/${schema}/${tb.table}`)}>
                <div className="table-card-title">{tb.title}</div>
                <div className="table-card-meta">{tb.n_rows} filas · {tb.n_cols} columnas</div>
              </button>
            ))}
          </div>
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
  const [dark, setDark] = useState(() => document.documentElement.dataset.theme !== 'light')

  useEffect(() => {
    const obs = new MutationObserver(() =>
      setDark(document.documentElement.dataset.theme !== 'light'))
    obs.observe(document.documentElement, { attributes: true, attributeFilter: ['data-theme'] })
    return () => obs.disconnect()
  }, [])

  // load meta + data on table change
  useEffect(() => {
    setMeta(null); setData(null); setErr(null)
    let alive = true
    api.tableMeta(schema, table).then((m) => {
      if (!alive) return
      const types = m.column_types
      const x = guessX(m.columns, types)
      const nums = numericCols(m.columns, types, [x])
      const ys = nums.slice(0, nums.length <= 6 ? nums.length : 4)
      setMeta(m); setXCol(x); setYCols(ys)
      setCtype(guessChartType(x, m.columns, types))
      return api.data(schema, table, {
        order: isTemporal(x) ? x : undefined, limit: 8000,
      })
    }).then((d) => { if (alive && d) setData(d) })
      .catch((e) => alive && setErr(String(e)))
    return () => { alive = false }
  }, [schema, table])

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

  const option = useMemo(() => {
    if (!xCol || !yCols.length || !cleanRows.length) return null
    return buildOption({
      rows: cleanRows, x: xCol, series: yCols,
      type: ctype === 'scatter' ? 'scatter' : ctype,
      ytitle: yCols.length === 1 ? yCols[0] : '', dark,
    })
  }, [cleanRows, xCol, yCols, ctype, dark])

  if (err) return <div className="error">No se pudo cargar: {err}</div>
  if (!meta) return <div className="loading">Cargando indicador…</div>

  const allCols = meta.columns
  const numCols = allCols.filter((c) => isNumeric(types[c]))

  const toggleY = (c) =>
    setYCols((cur) => cur.includes(c) ? cur.filter((x) => x !== c) : [...cur, c])

  return (
    <div className="explorer">
      <div className="exp-head">
        <div className="exp-crumb">{schema.toUpperCase()}</div>
        <h1>{meta.title}</h1>
        <div className="exp-sub">
          <span>{meta.n_rows} filas · {meta.n_cols} columnas</span>
          <span className="exp-file">{meta.source_file}</span>
          <a className="exp-dl" href={api.downloadUrl(schema, table)}>Descargar CSV</a>
        </div>
      </div>

      <div className="exp-body">
        <div className="controls">
          <div className="ctrl">
            <label>Tipo de gráfico</label>
            <div className="seg">
              {CHART_TYPES.map((t) => (
                <button key={t.k} className={ctype === t.k ? 'on' : ''}
                  onClick={() => setCtype(t.k)}>{t.l}</button>
              ))}
            </div>
          </div>
          <div className="ctrl">
            <label>Eje X</label>
            <select value={xCol} onChange={(e) => {
              const nx = e.target.value
              setXCol(nx); setYCols((ys) => ys.filter((y) => y !== nx))
            }}>
              {allCols.map((c) => <option key={c} value={c}>{c}</option>)}
            </select>
          </div>
          <div className="ctrl grow">
            <label>Series (eje Y)</label>
            <div className="chips">
              {numCols.filter((c) => c !== xCol).map((c) => (
                <button key={c} className={'chip' + (yCols.includes(c) ? ' on' : '')}
                  onClick={() => toggleY(c)}>{c}</button>
              ))}
            </div>
          </div>
        </div>

        <div className="chart-wrap">
          {option ? <EChart option={option} />
            : <div className="loading">Selecciona al menos una serie numérica.</div>}
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
