import { useEffect, useState } from 'react'
import { NavLink, useLocation } from 'react-router-dom'
import { AnimatePresence, motion } from 'framer-motion'
import { api } from '../api'
import { TOPIC_META } from '../content'
import { useLang } from '../i18n'

// One collapsible TOPIC (cross-survey): how readers think — pobreza, empleo,
// salud — regardless of which INEI survey produced each table. Panel window
// families arrive already collapsed to their newest window.
function TopicGroup({ topic, onNavigate }) {
  const { t, topic: tt } = useLang()
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
        <span className="nav-db-title">{tt(topic.topic_key, 'label', topic.topic_label)}</span>
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
                {tb.windows && <span className="nav-windows-n">{tb.windows.length} {t('ventanas')}</span>}
              </NavLink>
            ))}
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  )
}

export default function Sidebar({ databases, open, onNavigate }) {
  const { t } = useLang()
  const [topics, setTopics] = useState([])
  useEffect(() => {
    api.topics().then(setTopics).catch(() => setTopics([]))
  }, [])

  return (
    <aside className={`sidebar ${open ? 'open' : ''}`}>
      <div className="sidebar-inner">
        <NavLink to="/" onClick={onNavigate} className="nav-home" end>{t('home')}</NavLink>
        <NavLink to="/preguntas" onClick={onNavigate}
          className={({ isActive }) => 'nav-tool' + (isActive ? ' active' : '')}>
          <span className="nav-tool-ico">★</span> {t('preguntas')}
        </NavLink>
        <NavLink to="/tuvida" onClick={onNavigate}
          className={({ isActive }) => 'nav-tool' + (isActive ? ' active' : '')}>
          <span className="nav-tool-ico">☉</span> {t('tuvida')}
        </NavLink>
        <NavLink to="/adivina" onClick={onNavigate}
          className={({ isActive }) => 'nav-tool' + (isActive ? ' active' : '')}>
          <span className="nav-tool-ico">?</span> {t('adivina')}
        </NavLink>
        <NavLink to="/dibuja" onClick={onNavigate}
          className={({ isActive }) => 'nav-tool' + (isActive ? ' active' : '')}>
          <span className="nav-tool-ico">✏</span> {t('dibuja')}
        </NavLink>
        <NavLink to="/dpto/15" onClick={onNavigate}
          className={({ isActive }) => 'nav-tool' + (isActive ? ' active' : '')}>
          <span className="nav-tool-ico">▣</span> {t('ficha')}
        </NavLink>
        <NavLink to="/distrito" onClick={onNavigate}
          className={({ isActive }) => 'nav-tool' + (isActive ? ' active' : '')}>
          <span className="nav-tool-ico">⌂</span> {t('midistrito')}
        </NavLink>
        <NavLink to="/comparar" onClick={onNavigate}
          className={({ isActive }) => 'nav-tool' + (isActive ? ' active' : '')}>
          <span className="nav-tool-ico">⇄</span> {t('comparar')}
        </NavLink>
        <NavLink to="/graficos" onClick={onNavigate}
          className={({ isActive }) => 'nav-tool' + (isActive ? ' active' : '')}>
          <span className="nav-tool-ico">∿</span> {t('graficos')}
        </NavLink>
        <NavLink to="/correlacion" onClick={onNavigate}
          className={({ isActive }) => 'nav-tool' + (isActive ? ' active' : '')}>
          <span className="nav-tool-ico">✦</span> {t('correlaciones')}
        </NavLink>
        <NavLink to="/ensayos" onClick={onNavigate}
          className={({ isActive }) => 'nav-tool' + (isActive ? ' active' : '')}>
          <span className="nav-tool-ico">✎</span> {t('ensayos')}
        </NavLink>
        <NavLink to="/historia" onClick={onNavigate}
          className={({ isActive }) => 'nav-tool' + (isActive ? ' active' : '')}>
          <span className="nav-tool-ico">▸</span> {t('hist_pobreza')}
        </NavLink>
        <NavLink to="/desigualdad" onClick={onNavigate}
          className={({ isActive }) => 'nav-tool' + (isActive ? ' active' : '')}>
          <span className="nav-tool-ico">▸</span> {t('hist_desigualdad')}
        </NavLink>
        <NavLink to="/quienvoto" onClick={onNavigate}
          className={({ isActive }) => 'nav-tool' + (isActive ? ' active' : '')}>
          <span className="nav-tool-ico">▸</span> {t('hist_voto')}
        </NavLink>
        <NavLink to="/metodologia" onClick={onNavigate}
          className={({ isActive }) => 'nav-tool' + (isActive ? ' active' : '')}>
          <span className="nav-tool-ico">✓</span> {t('metodologia')}
        </NavLink>
        <NavLink to="/datos" onClick={onNavigate}
          className={({ isActive }) => 'nav-tool' + (isActive ? ' active' : '')}>
          <span className="nav-tool-ico">↓</span> {t('datos')}
        </NavLink>

        <div className="nav-sep" />
        <div className="nav-section-label">{t('temas')}</div>
        {topics.map((t) => (
          <TopicGroup key={t.topic_key} topic={t} onNavigate={onNavigate} />
        ))}

        <div className="nav-sep" />
        <div className="nav-section-label">{t('fuentes')}</div>
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
