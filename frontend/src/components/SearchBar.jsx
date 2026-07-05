import { useEffect, useMemo, useRef, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { AnimatePresence, motion } from 'framer-motion'

// Global indicator search: fetches the flat index once, filters client-side.
export default function SearchBar() {
  const nav = useNavigate()
  const [index, setIndex] = useState([])
  const [q, setQ] = useState('')
  const [open, setOpen] = useState(false)
  const [hi, setHi] = useState(0)
  const box = useRef(null)

  useEffect(() => {
    fetch('/api/index').then((r) => r.json()).then(setIndex).catch(() => {})
  }, [])
  useEffect(() => {
    const onClick = (e) => { if (box.current && !box.current.contains(e.target)) setOpen(false) }
    document.addEventListener('mousedown', onClick)
    return () => document.removeEventListener('mousedown', onClick)
  }, [])

  const results = useMemo(() => {
    const s = q.trim().toLowerCase()
    if (!s) return []
    const terms = s.split(/\s+/)
    return index.map((x) => {
      const t = x.title.toLowerCase(), tb = x.table.toLowerCase()
      const th = (x.theme || '').toLowerCase(), sec = (x.section || '').toLowerCase()
      let score = 0, all = true
      for (const term of terms) {
        // weight where the term matches: title >> table > theme > section
        const s2 = (t.includes(term) ? 6 : 0) + (tb.includes(term) ? 3 : 0)
          + (th.includes(term) ? 1 : 0) + (sec.includes(term) ? 0.3 : 0)
        if (s2 === 0) all = false
        score += s2
      }
      return { x, score, all }
    }).filter((r) => r.all).sort((a, b) => b.score - a.score).slice(0, 8).map((r) => r.x)
  }, [q, index])

  useEffect(() => { setHi(0) }, [q])

  const go = (r) => {
    if (!r) return
    nav(`/db/${r.schema}/${r.table}`)
    setQ(''); setOpen(false)
  }
  const onKey = (e) => {
    if (e.key === 'ArrowDown') { e.preventDefault(); setHi((h) => Math.min(h + 1, results.length - 1)) }
    else if (e.key === 'ArrowUp') { e.preventDefault(); setHi((h) => Math.max(h - 1, 0)) }
    else if (e.key === 'Enter') go(results[hi])
    else if (e.key === 'Escape') setOpen(false)
  }

  return (
    <div className="search" ref={box}>
      <span className="search-ico">⌕</span>
      <input className="search-input" value={q} placeholder="Buscar indicador…"
        onChange={(e) => { setQ(e.target.value); setOpen(true) }}
        onFocus={() => setOpen(true)} onKeyDown={onKey} />
      <AnimatePresence>
        {open && results.length > 0 && (
          <motion.ul className="search-results"
            initial={{ opacity: 0, y: -6 }} animate={{ opacity: 1, y: 0 }} exit={{ opacity: 0, y: -6 }}
            transition={{ duration: 0.15 }}>
            {results.map((r, i) => (
              <li key={r.schema + r.table} className={'search-item' + (i === hi ? ' on' : '')}
                onMouseEnter={() => setHi(i)} onMouseDown={(e) => { e.preventDefault(); go(r) }}>
                <span className="search-title">{r.title}{r.mappable && <span className="search-map"> · mapa</span>}</span>
                <span className="search-sec">{r.section}</span>
              </li>
            ))}
          </motion.ul>
        )}
      </AnimatePresence>
    </div>
  )
}
