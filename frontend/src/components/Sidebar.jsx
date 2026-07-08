import { useEffect, useState } from 'react'
import { NavLink, useLocation } from 'react-router-dom'
import { AnimatePresence, motion } from 'framer-motion'
import { api } from '../api'
import { TOPIC_META } from '../content'

// One collapsible TOPIC (cross-survey): how readers think — pobreza, empleo,
// salud — regardless of which INEI survey produced each table. Panel window
// families arrive already collapsed to their newest window.
function TopicGroup({ topic, onNavigate }) {
  const location = useLocation()
  const holdsActive = topic.tables.some((tb) =>
    location.pathname === `/db/${tb.schema}/${tb.table}`
    || (tb.windows || []).some((w) => location.pathname === `/db/${tb.schema}/${w.table}`))
  const [open, setOpen] = useState(false)
  useEffect(() => { if (holdsActive) setOpen(true) }, [holdsActive])
  const meta = TOPIC_META[topic.topic_key] || {}

  return (
    <div className="nav-group">
      <button className="nav-db" onClick={() => setOpen((o) => !o)}>
        <span className="nav-topic-ico">{meta.icon || '◆'}</span>
        <span className="nav-db-title">{topic.topic_label}</span>
        <span className="nav-count">{topic.tables.length}</span>
        <span className={`nav-caret ${open ? 'up' : ''}`}>▾</span>
      </button>
      <AnimatePresence initial={false}>
        {open && (
          <motion.div className="nav-themes"
            initial={{ height: 0, opacity: 0 }}
            animate={{ height: 'auto', opacity: 1 }}
            exit={{ height: 0, opacity: 0 }}
            transition={{ duration: 0.28, ease: [0.22, 0.61, 0.36, 1] }}>
            {topic.tables.map((tb) => (
              <NavLink key={tb.schema + tb.table} onClick={onNavigate}
                to={`/db/${tb.schema}/${tb.table}`}
                className={({ isActive }) => 'nav-table' + (isActive ? ' active' : '')}
                title={tb.title}>
                {tb.title}
                {tb.windows && <span className="nav-windows-n">{tb.windows.length} ventanas</span>}
              </NavLink>
            ))}
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  )
}

export default function Sidebar({ databases, open, onNavigate }) {
  const [topics, setTopics] = useState([])
  useEffect(() => {
    api.topics().then(setTopics).catch(() => setTopics([]))
  }, [])

  return (
    <aside className={`sidebar ${open ? 'open' : ''}`}>
      <div className="sidebar-inner">
        <NavLink to="/" onClick={onNavigate} className="nav-home" end>Inicio</NavLink>
        <NavLink to="/dpto/15" onClick={onNavigate}
          className={({ isActive }) => 'nav-tool' + (isActive ? ' active' : '')}>
          <span className="nav-tool-ico">▣</span> Ficha departamental
        </NavLink>
        <NavLink to="/comparar" onClick={onNavigate}
          className={({ isActive }) => 'nav-tool' + (isActive ? ' active' : '')}>
          <span className="nav-tool-ico">⇄</span> Comparar departamentos
        </NavLink>
        <NavLink to="/graficos" onClick={onNavigate}
          className={({ isActive }) => 'nav-tool' + (isActive ? ' active' : '')}>
          <span className="nav-tool-ico">∿</span> Gráficos
        </NavLink>
        <NavLink to="/correlacion" onClick={onNavigate}
          className={({ isActive }) => 'nav-tool' + (isActive ? ' active' : '')}>
          <span className="nav-tool-ico">✦</span> Correlaciones
        </NavLink>
        <NavLink to="/ensayos" onClick={onNavigate}
          className={({ isActive }) => 'nav-tool' + (isActive ? ' active' : '')}>
          <span className="nav-tool-ico">✎</span> Ensayos
        </NavLink>
        <NavLink to="/historia" onClick={onNavigate}
          className={({ isActive }) => 'nav-tool' + (isActive ? ' active' : '')}>
          <span className="nav-tool-ico">▸</span> Historia: la pobreza
        </NavLink>
        <NavLink to="/desigualdad" onClick={onNavigate}
          className={({ isActive }) => 'nav-tool' + (isActive ? ' active' : '')}>
          <span className="nav-tool-ico">▸</span> Historia: la desigualdad
        </NavLink>
        <NavLink to="/metodologia" onClick={onNavigate}
          className={({ isActive }) => 'nav-tool' + (isActive ? ' active' : '')}>
          <span className="nav-tool-ico">✓</span> Metodología
        </NavLink>
        <NavLink to="/datos" onClick={onNavigate}
          className={({ isActive }) => 'nav-tool' + (isActive ? ' active' : '')}>
          <span className="nav-tool-ico">↓</span> Datos abiertos
        </NavLink>

        <div className="nav-sep" />
        <div className="nav-section-label">Temas</div>
        {topics.map((t) => (
          <TopicGroup key={t.topic_key} topic={t} onNavigate={onNavigate} />
        ))}

        <div className="nav-sep" />
        <div className="nav-section-label">Fuentes</div>
        {databases.map((db) => (
          <NavLink key={db.schema} to={`/db/${db.schema}`} onClick={onNavigate}
            className={({ isActive }) => 'nav-source' + (isActive ? ' active' : '')}>
            <span className="nav-dot" style={{ background: db.color }} />
            <span className="nav-source-title">{db.source.split(' - ')[0]}</span>
            <span className="nav-count">{db.n_tables}</span>
          </NavLink>
        ))}
      </div>
    </aside>
  )
}
