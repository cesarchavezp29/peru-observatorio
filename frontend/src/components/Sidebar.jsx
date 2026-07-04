import { useEffect, useState } from 'react'
import { NavLink, useParams } from 'react-router-dom'
import { AnimatePresence, motion } from 'framer-motion'
import { api } from '../api'

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
              <div key={t.theme_key} className="nav-theme">
                <div className="nav-theme-label">{t.theme_label}</div>
                {t.tables.map((tb) => (
                  <NavLink key={tb.table} onClick={onNavigate}
                    to={`/db/${db.schema}/${tb.table}`}
                    className={({ isActive }) => 'nav-table' + (isActive ? ' active' : '')}
                    title={tb.title}>
                    {tb.title}
                  </NavLink>
                ))}
              </div>
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
        <NavLink to="/" onClick={onNavigate} className="nav-home"
          end>Inicio</NavLink>
        {databases.map((db) => (
          <DatabaseGroup key={db.schema} db={db} onNavigate={onNavigate} />
        ))}
      </div>
    </aside>
  )
}
