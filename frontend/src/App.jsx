import { useEffect, useState } from 'react'
import { Routes, Route, NavLink, useLocation } from 'react-router-dom'
import { AnimatePresence, motion } from 'framer-motion'
import { api } from './api'
import Sidebar from './components/Sidebar'
import SearchBar from './components/SearchBar'
import Home from './components/Home'
import Explorer from './components/Explorer'
import Comparador from './components/Comparador'
import Correlacion from './components/Correlacion'
import Datos from './components/Datos'
import Departamento from './components/Departamento'
import Ensayos from './components/Ensayos'
import Historia from './components/Historia'
import Desigualdad from './components/Desigualdad'
import Metodologia from './components/Metodologia'
import Ficha from './components/Ficha'
import Graficos from './components/Graficos'
import Tema from './components/Tema'
import Distrito from './components/Distrito'
import Preguntas from './components/Preguntas'
import QuienVoto from './components/QuienVoto'
import TuVida from './components/TuVida'
import Adivina from './components/Adivina'
import { LangProvider, useLang } from './i18n'

function LangToggle() {
  const { lang, setLang } = useLang()
  return (
    <button className="lang-toggle" aria-label="Cambiar idioma / switch language" onClick={() => setLang(lang === 'es' ? 'en' : 'es')}
      title={lang === 'es' ? 'Switch to English' : 'Cambiar a español'}>
      {lang === 'es' ? 'EN' : 'ES'}
    </button>
  )
}

export default function App() {
  return <LangProvider><AppShell /></LangProvider>
}

function AppShell() {
  const { t } = useLang()
  const [databases, setDatabases] = useState([])
  const [navOpen, setNavOpen] = useState(false)
  const location = useLocation()
  // ?embed=1 -> bare chart for iframes: no topbar, sidebar or footer
  const embed = new URLSearchParams(location.search).get('embed') === '1'

  useEffect(() => {
    api.databases().then(setDatabases).catch(() => setDatabases([]))
  }, [])

  useEffect(() => {
    setNavOpen(false); window.scrollTo({ top: 0 })
    const path = location.pathname
    const titles = [
      ['/comparar', 'Comparar departamentos'], ['/correlacion', 'Correlaciones'],
      ['/ensayos', 'Ensayos'], ['/historia', 'Historia de la pobreza'],
      ['/desigualdad', 'Historia de la desigualdad'],
      ['/metodologia', 'Metodología'], ['/dpto/', 'Ficha departamental'],
      ['/graficos', 'Gráficos'], ['/tema/', 'Temas'], ['/distrito', 'Mi distrito'], ['/preguntas', 'El Perú en preguntas'], ['/quienvoto', 'Quién votó por Keiko'], ['/tuvida', 'El Perú de tu vida'], ['/adivina', 'Adivina el Perú'],
    ]
    const hit = titles.find(([p]) => path.startsWith(p))
    document.title = (hit ? hit[1] + ' · ' : '') + 'Observatorio de Datos del Perú'
  }, [location.pathname])

  if (embed) {
    return (
      <div className="app embed-shell">
        <Routes location={location}>
          <Route path="/db/:schema/:table" element={<Explorer />} />
          <Route path="*" element={<Home databases={databases} />} />
        </Routes>
        <a className="embed-brand" href={window.location.origin + '/#' + location.pathname}
          target="_blank" rel="noreferrer">
          ◆ Observatorio de Datos del Perú
        </a>
      </div>
    )
  }

  return (
    <div className="app">
      <header className="topbar">
        <button className="hamburger" onClick={() => setNavOpen((o) => !o)} aria-label="menu">☰</button>
        <NavLink to="/" className="brand">
          <span className="brand-mark">◆</span>
          <span className="brand-text">
            <strong>Observatorio de Datos del Perú</strong>
            <small>{t('tagline')}</small>
          </span>
        </NavLink>
        <div className="topbar-spacer" />
        <SearchBar />
        <LangToggle />
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
                <Route path="/comparar" element={<Comparador />} />
                <Route path="/correlacion" element={<Correlacion />} />
                <Route path="/ensayos" element={<Ensayos />} />
                <Route path="/dpto/:code" element={<Departamento />} />
                <Route path="/metodologia" element={<Metodologia />} />
                <Route path="/metodologia/:name" element={<Ficha />} />
                <Route path="/graficos" element={<Graficos />} />
                <Route path="/tema/:key" element={<Tema />} />
                <Route path="/distrito" element={<Distrito />} />
                <Route path="/preguntas" element={<Preguntas />} />
                <Route path="/quienvoto" element={<QuienVoto />} />
                <Route path="/tuvida" element={<TuVida />} />
                <Route path="/adivina" element={<Adivina />} />
                <Route path="/datos" element={<Datos />} />
                <Route path="/historia" element={<Historia />} />
                <Route path="/desigualdad" element={<Desigualdad />} />
                <Route path="/db/:schema" element={<Explorer />} />
                <Route path="/db/:schema/:table" element={<Explorer />} />
              </Routes>
            </motion.div>
          </AnimatePresence>
          <footer className="site-footer">
            Fuente: microdatos INEI (ENAHO, ENAHO Panel, ENDES, EPE/EPEN, EEA).
            Indicadores propios validados contra estadísticas oficiales — ver{' '}
            <NavLink to="/metodologia" className="footer-link">metodología</NavLink>.
            Datos por <a className="footer-link" href="/docs" target="_blank" rel="noreferrer">API</a>.
            Construido por Carlos Chávez.
          </footer>
        </main>
      </div>
    </div>
  )
}
