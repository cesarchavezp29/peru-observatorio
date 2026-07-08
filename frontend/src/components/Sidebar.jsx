import { useEffect, useState } from 'react'
import { NavLink, useLocation, useParams } from 'react-router-dom'
import { AnimatePresence, motion } from 'framer-motion'
import { api } from '../api'

// one collapsible sub-section (theme) inside a database group — 83 tables in a
// flat list was unusable, so each theme folds
function ThemeGroup({ schema, theme, onNavigate, single }) {
  const location = useLocation()
  const holdsActive = theme.tables.some((tb) =>
    location.pathname === `/db/${schema}/${tb.table}`)
  const [open, setOpen] = useState(single || holdsActive)
  useEffect(() => { if (holdsActive) setOpen(true) }, [holdsActive])

  return (
    <div className="nav-theme">
      {!single && (
        <button className={'nav-theme-toggle' + (open ? ' open' : '')}
          onClick={() => setOpen((o) => !o)}>
          <span className={`nav-caret sm ${open ? 'up' : ''}`}>▾</span>
          <span className="nav-theme-name">{theme.theme_label}</span>
          <span className="nav-theme-n">{theme.tables.length}</span>
        </button>
      )}
      <AnimatePresence initial={false}>
        {open && (
          <motion.div
            initial={{ height: 0, opacity: 0 }}
            animate={{ height: 'auto', opacity: 1 }}
            exit={{ height: 0, opacity: 0 }}
            transition={{ duration: 0.22, ease: [0.22, 0.61, 0.36, 1] }}>
            {theme.tables.map((tb) => (
              <NavLink key={tb.table} onClick={onNavigate}
                to={`/db/${schema}/${tb.table}`}
                className={({ isActive }) => 'nav-table' + (isActive ? ' active' : '')}
                title={tb.title}>
                {tb.title}
              </NavLink>
            ))}
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  )
}

function DatabaseGroup({ db, onNavigate }) {
  const { schema } = useParams()
  const [open, setOpen] = useState(false)
  const [detail, setDetail] = useState(null)

  useEffect(() => {
    if (schema === db.schema) setOpen(true)
  }, [schema, db.schema])

  useEffect(() => {
    if (open && !detail) api.database(db.schema).then(setDetail).catch(() => {})
  }, [open, detail, db.schema])

  return (
    <div className="nav-group">
      <button className="nav-db" onClick={() => setOpen((o) => !o)}
        style={{ '--accent': db.color }}>
        <span className="nav-dot" style={{ background: db.color }} />
        <span className="nav-db-title">{db.title}</span>
        <span className="nav-count">{db.n_tables}</span>
        <span className={`nav-caret ${open ? 'up' : ''}`}>▾</span>
      </button>
      <AnimatePresence initial={false}>
        {open && detail && (
          <motion.div className="nav-themes"
            initial={{ height: 0, opacity: 0 }}
            animate={{ height: 'auto', opacity: 1 }}
            exit={{ height: 0, opacity: 0 }}
            transition={{ duration: 0.28, ease: [0.22, 0.61, 0.36, 1] }}>
            {detail.themes.map((t) => (
              <ThemeGroup key={t.theme_key} schema={db.schema} theme={t}
                onNavigate={onNavigate} single={detail.themes.length === 1} />
            ))}
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  )
}

export default function Sidebar({ databases, open, onNavigate }) {
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
        {databases.map((db) => (
          <DatabaseGroup key={db.schema} db={db} onNavigate={onNavigate} />
        ))}
      </div>
    </aside>
  )
}
