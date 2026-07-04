import { useEffect, useRef, useState } from 'react'
import * as echarts from 'echarts'
import { buildMapOption } from '../chartLogic'

const MAP_NAME = 'peru_dept'
let _registered = null // Promise, so we register the geojson only once

function ensureMap() {
  if (_registered) return _registered
  _registered = fetch('geo/peru_departments.geojson')
    .then((r) => r.json())
    .then((geo) => { echarts.registerMap(MAP_NAME, geo); return true })
  return _registered
}

export default function MapChart({ data, title, min, max, dark, height = 560 }) {
  const el = useRef(null)
  const chart = useRef(null)
  const [ready, setReady] = useState(false)

  useEffect(() => {
    chart.current = echarts.init(el.current, null, { renderer: 'canvas' })
    const ro = new ResizeObserver(() => chart.current && chart.current.resize())
    ro.observe(el.current)
    ensureMap().then(() => setReady(true))
    return () => { ro.disconnect(); chart.current.dispose() }
  }, [])

  useEffect(() => {
    if (ready && chart.current) {
      chart.current.setOption(
        buildMapOption({ data, mapName: MAP_NAME, title, min, max, dark }), true)
    }
  }, [ready, data, title, min, max, dark])

  return (
    <div style={{ position: 'relative' }}>
      {!ready && <div className="loading">Cargando mapa…</div>}
      <div ref={el} style={{ width: '100%', height }} />
    </div>
  )
}
