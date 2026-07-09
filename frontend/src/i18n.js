import { createContext, useContext, useEffect, useState } from 'react'
import { createElement } from 'react'

// Minimal i18n: ES is the source of truth, EN covers the chrome + navigation
// so an international reader (perudata users) can find their way. Chart data
// and editorial narratives stay in Spanish.
const STRINGS = {
  es: {
    tagline: 'Microdatos oficiales INEI · validados',
    home: 'Inicio', preguntas: 'Empieza aquí: 10 preguntas', tuvida: 'El Perú de tu vida', adivina: 'Adivina el Perú', dibuja: 'Dibuja la línea', ficha: 'Ficha departamental', midistrito: 'Mi distrito', comparar: 'Comparar departamentos',
    graficos: 'Gráficos', correlaciones: 'Correlaciones', ensayos: 'Ensayos',
    hist_pobreza: 'Historia: la pobreza', hist_desigualdad: 'Historia: la desigualdad', hist_voto: 'Historia: el voto',
    metodologia: 'Metodología', datos: 'Datos abiertos',
    temas: 'Temas', fuentes: 'Fuentes',
    hero_eyebrow: 'Observatorio abierto · microdatos INEI',
    hero_lead: 'Veinte años de encuestas oficiales —hogares, salud, empleo y empresas— limpiadas, armonizadas y contrastadas contra las cifras publicadas. Elige un indicador y míralo cambiar.',
    q_peru: '¿Qué quieres saber del Perú?',
    story4: 'La historia en cinco gráficos', panorama: 'Panorama nacional · dos décadas de cambio',
    hallazgos: 'Hallazgos · lo que dicen los datos', por_fuente: 'Explora por fuente',
    buscar: 'Buscar indicador…  /',
    ventanas: 'ventanas', relacionados: 'Relacionados', graficos_n: 'gráficos',
  },
  en: {
    tagline: 'Official INEI microdata · validated',
    home: 'Home', preguntas: 'Start here: 10 questions', tuvida: 'Peru in your lifetime', adivina: 'Guess Peru', dibuja: 'You draw it', ficha: 'Region profile', midistrito: 'My district', comparar: 'Compare regions',
    graficos: 'Charts', correlaciones: 'Correlations', ensayos: 'Essays',
    hist_pobreza: 'Story: poverty', hist_desigualdad: 'Story: inequality', hist_voto: 'Story: the vote',
    metodologia: 'Methodology', datos: 'Open data',
    temas: 'Topics', fuentes: 'Sources',
    hero_eyebrow: 'Open observatory · INEI microdata',
    hero_lead: 'Twenty years of official surveys — households, health, jobs and firms — cleaned, harmonized and checked against the published figures. Pick an indicator and watch it move.',
    q_peru: 'What do you want to know about Peru?',
    story4: 'The story in five charts', panorama: 'National panorama · two decades of change',
    hallazgos: 'Findings · what the data says', por_fuente: 'Explore by source',
    buscar: 'Search indicators…  /',
    ventanas: 'windows', relacionados: 'Related charts', graficos_n: 'charts',
  },
}

const TOPIC_EN = {
  pobreza: { label: 'Poverty & Inequality', desc: 'How many Peruvians are poor, and how evenly is the pie shared?' },
  ingreso: { label: 'Income & Spending', desc: 'How much does a Peruvian family earn, and what does it buy?' },
  empleo: { label: 'Jobs & Wages', desc: 'Who works, at what, and how much are they paid?' },
  educacion: { label: 'Education', desc: 'How much do Peruvians study, and who gets furthest?' },
  salud: { label: 'Health & Demography', desc: 'Health, fertility, migration and how the population is changing.' },
  sociedad: { label: 'Trust, State & Elections', desc: 'Whom do we trust, how do we vote, whom does the State help?' },
  vivienda: { label: 'Housing & Services', desc: 'What homes are like: water, power, what people cook with.' },
  agro: { label: 'Agriculture', desc: 'What is grown, what is raised, how much reaches the market.' },
  empresas: { label: 'Firms', desc: 'The firm side: sales, productivity and pay by sector.' },
  territorio: { label: 'Territory', desc: 'Every indicator side by side, region by region.' },
}

const LangContext = createContext({ lang: 'es', setLang: () => {}, t: (k) => k })

export function LangProvider({ children }) {
  const [lang, setLang] = useState(() => localStorage.getItem('lang') || 'es')
  useEffect(() => { localStorage.setItem('lang', lang) }, [lang])
  const t = (k) => STRINGS[lang][k] ?? STRINGS.es[k] ?? k
  const topic = (key, field, fallback) =>
    lang === 'en' && TOPIC_EN[key] ? TOPIC_EN[key][field] : fallback
  return createElement(LangContext.Provider, { value: { lang, setLang, t, topic } }, children)
}

export function useLang() {
  return useContext(LangContext)
}
