import { useEffect, useMemo, useState } from 'react'
import { motion } from 'framer-motion'

const W = 480, PAD = 12

// project the departments geojson into SVG paths (equirectangular w/ cos-lat).
function project(geo) {
  let minLon = 180, maxLon = -180, minLat = 90, maxLat = -90
  const rings = []
  const push = (coords, name) => {
    // coords: array of [lon,lat]
    for (const [lon, lat] of coords) {
      if (lon < minLon) minLon = lon; if (lon > maxLon) maxLon = lon
      if (lat < minLat) minLat = lat; if (lat > maxLat) maxLat = lat
    }
    rings.push({ coords, name })
  }
  for (const f of geo.features) {
    const g = f.geometry, nm = f.properties.name
    if (g.type === 'Polygon') g.coordinates.forEach((r) => push(r, nm))
    else if (g.type === 'MultiPolygon') g.coordinates.forEach((p) => p.forEach((r) => push(r, nm)))
  }
  const midLat = ((minLat + maxLat) / 2) * Math.PI / 180
  const k = Math.cos(midLat)
  const lonW = (maxLon - minLon) * k, latH = maxLat - minLat
  const scale = (W - 2 * PAD) / lonW
  const H = latH * scale + 2 * PAD
  const X = (lon) => PAD + (lon * k - minLon * k) * scale
  const Y = (lat) => PAD + (maxLat - lat) * scale
  // group rings back by department so each dept is one <path> (draws as a unit)
  const byDept = {}
  for (const { coords, name } of rings) {
    const d = coords.map(([lon, lat], i) =>
      `${i ? 'L' : 'M'}${X(lon).toFixed(1)} ${Y(lat).toFixed(1)}`).join('') + 'Z'
    byDept[name] = (byDept[name] || '') + d
  }
  return { paths: Object.entries(byDept).map(([name, d]) => ({ name, d })), H }
}

export default function PeruMapHero() {
  const [geo, setGeo] = useState(null)
  const [hover, setHover] = useState(null)
  useEffect(() => {
    fetch('geo/peru_departments.geojson').then((r) => r.json()).then(setGeo).catch(() => {})
  }, [])
  const proj = useMemo(() => (geo ? project(geo) : null), [geo])
  if (!proj) return <div className="hero-map" />

  return (
    <div className="hero-map">
      <svg viewBox={`0 0 ${W} ${proj.H}`} className="peru-svg"
        style={{ width: '100%', maxWidth: 460 }}>
        <defs>
          <linearGradient id="andes" x1="0" y1="0" x2="1" y2="1">
            <stop offset="0%" stopColor="#e6ac6b" />
            <stop offset="55%" stopColor="#d97f3f" />
            <stop offset="100%" stopColor="#c25728" />
          </linearGradient>
        </defs>
        {proj.paths.map((p, i) => (
          <motion.path key={p.name} d={p.d}
            initial={{ pathLength: 0, fillOpacity: 0 }}
            animate={{ pathLength: 1, fillOpacity: hover === p.name ? 0.95 : 0.85 }}
            transition={{
              pathLength: { delay: 0.15 + i * 0.045, duration: 1.1, ease: [0.22, 0.61, 0.36, 1] },
              fillOpacity: { delay: hover === p.name ? 0 : 0.9 + i * 0.045, duration: 0.5 },
            }}
            onMouseEnter={() => setHover(p.name)}
            onMouseLeave={() => setHover(null)}
            fill={hover === p.name ? '#157a6e' : 'url(#andes)'}
            stroke="#fffdf7" strokeWidth={0.8}
            style={{ cursor: 'pointer' }} />
        ))}
      </svg>
      <motion.div className="hero-map-tag"
        initial={{ opacity: 0, y: 8 }} animate={{ opacity: 1, y: 0 }}
        transition={{ delay: 2 }}>
        {hover || '25 departamentos'}
      </motion.div>
    </div>
  )
}
