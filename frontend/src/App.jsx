import { useEffect, useState } from 'react'
import { Routes, Route, NavLink, useLocation } from 'react-router-dom'
import { AnimatePresence, motion } from 'framer-motion'
import { api } from './api'
import Sidebar from './components/Sidebar'
import Home from './components/Home'
import Explorer from './components/Explorer'

export default function App() {
  const [databases, setDatabases] = useState([])
  const [navOpen, setNavOpen] = useState(false)
  const location = useLocation()

  useEffect(() => {
    api.databases().then(setDatabases).catch(() => setDatabases([]))
  }, [])

  useEffect(() => { setNavOpen(false) }, [location.pathname])

  return (
    <div className="app">
      <header className="topbar">
        <button className="hamburger" onClick={() => setNavOpen((o) => !o)} aria-label="menu">☰</button>
        <NavLink to="/" className="brand">
          <span className="brand-mark">◆</span>
          <span className="brand-text">
            <strong>Observatorio de Datos del Perú</strong>
            <small>Microdatos oficiales INEI · validados</small>
          </span>
        </NavLink>
        <div className="topbar-spacer" />
        <a className="topbar-link" href="https://github.com/cesarchavezp29" target="_blank" rel="noreferrer">GitHub</a>
      </header>

      <div className="layout">
        <Sidebar databases={databases} open={navOpen} onNavigate={() => setNavOpen(false)} />
        <main className="content">
          <AnimatePresence mode="wait">
            <motion.div key={location.pathname}
              initial={{ opacity: 0, y: 14 }}
              animate={{ opacity: 1, y: 0 }}
              exit={{ opacity: 0, y: -10 }}
              transition={{ duration: 0.32, ease: [0.22, 0.61, 0.36, 1] }}>
              <Routes location={location}>
                <Route path="/" element={<Home databases={databases} />} />
                <Route path="/db/:schema" element={<Explorer />} />
                <Route path="/db/:schema/:table" element={<Explorer />} />
              </Routes>
            </motion.div>
          </AnimatePresence>
          <footer className="site-footer">
            Fuente: microdatos INEI (ENAHO, ENAHO Panel, ENDES, EPE/EPEN, EEA).
            Indicadores propios validados contra estadísticas oficiales.
            Construido por Carlos Chávez.
          </footer>
        </main>
      </div>
    </div>
  )
}
