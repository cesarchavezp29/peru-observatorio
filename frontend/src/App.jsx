import { useEffect, useState } from 'react'
import { Routes, Route, NavLink, useNavigate } from 'react-router-dom'
import { api } from './api'
import Sidebar from './components/Sidebar'
import Home from './components/Home'
import Explorer from './components/Explorer'

export default function App() {
  const [databases, setDatabases] = useState([])
  const [dark, setDark] = useState(() => localStorage.getItem('obs-theme') !== 'light')
  const [navOpen, setNavOpen] = useState(false)

  useEffect(() => {
    api.databases().then(setDatabases).catch(() => setDatabases([]))
  }, [])

  useEffect(() => {
    document.documentElement.dataset.theme = dark ? 'dark' : 'light'
    localStorage.setItem('obs-theme', dark ? 'dark' : 'light')
  }, [dark])

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
        <button className="theme-toggle" onClick={() => setDark((d) => !d)} aria-label="tema">
          {dark ? '☀' : '☾'}
        </button>
      </header>

      <div className="layout">
        <Sidebar databases={databases} open={navOpen} onNavigate={() => setNavOpen(false)} />
        <main className="content">
          <Routes>
            <Route path="/" element={<Home databases={databases} />} />
            <Route path="/db/:schema" element={<Explorer />} />
            <Route path="/db/:schema/:table" element={<Explorer />} />
          </Routes>
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
