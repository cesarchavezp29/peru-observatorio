import { useNavigate } from 'react-router-dom'
import { motion } from 'framer-motion'
import CountUp from './CountUp'
import PeruMapHero from './PeruMapHero'
import HeroCine from './HeroCine'
import CifraDelDia from './CifraDelDia'
import Kpi from './Kpi'
import Finding from './Finding'
import StoryChart from './StoryChart'
import { FINDINGS, TOPIC_META } from '../content'
import { useEffect, useState } from 'react'
import { api } from '../api'
import { useLang } from '../i18n'

// the front-page story: full-size live charts, not hidden behind a click
const STORY = [
  { kicker: 'Pobreza', title: 'La pobreza se partió a la mitad', kind: 'line',
    schema: 'enaho', table: 'official_poverty_replication', series: 'poverty_pct', x: 'year',
    lede: 'En 2004, seis de cada diez peruanos eran pobres. Para 2025 son menos de tres. El descenso fue sostenido hasta que la pandemia lo interrumpió en 2020, y luego siguió cayendo.' },
  { kicker: 'Migración', title: 'Todos los caminos llevan a Lima', kind: 'flowmap', reverse: true,
    schema: 'enaho', table: 'migracion_od_departamento', timeCol: 'anio',
    flow: { source: 'origen', target: 'destino', value: 'personas' },
    lede: 'La migración interna tiene un centro que no admite competencia. Cada año decenas de miles de personas se mueven entre departamentos, y casi todas las líneas terminan en la capital.' },
    lede: 'El ingreso se reparte de forma muy distinta según la región. Los departamentos andinos y amazónicos concentran la mayor desigualdad, mientras la costa se reparte de forma más pareja.' },
  { kicker: 'Elecciones', title: 'La grieta no es pobreza', kind: 'map', reverse: true,
    schema: 'enaho', table: 'voto_keiko_departamento', mapCol: 'keiko_share_2026', level: 'dept',
    href: '/quienvoto', cta: 'Lee la historia completa →',
    lede: 'El voto por Keiko Fujimori en 2026 fue de 13.7% en Puno a 65.9% en el Callao, y su correlación con la pobreza es cero. La línea que parte el mapa electoral es etnolingüística y urbana: costa norte y Lima de un lado, sur andino del otro.' },
]

// live national snapshot — validated temporal series, pulled from the API
const PANORAMA = [
  { schema: 'enaho', table: 'official_poverty_replication', col: 'poverty_pct', tcol: 'year', label: 'Pobreza monetaria', unit: '%', color: '#c85a34' },
  { schema: 'endes', table: 'endes_indicadores', col: 'tfr', tcol: 'anio', label: 'Fecundidad (hijos por mujer)', unit: '', color: '#157a6e' },
  { schema: 'endes', table: 'endes_indicadores', col: 'desnutricion', tcol: 'anio', label: 'Desnutrición crónica infantil', unit: '%', color: '#9c6b2f' },
  { schema: 'epen', table: 'epen_lima_movil_2001_2026', col: 'tasa_desempleo', tcol: 'ym', label: 'Desempleo · Lima', unit: '%', color: '#8a4a6b' },
  { schema: 'endes', table: 'endes_indicadores', col: 'educ_anios', tcol: 'anio', label: 'Años de educación', unit: '', color: '#3f5aa6' },
]

const container = {
  hidden: {},
  show: { transition: { staggerChildren: 0.09, delayChildren: 0.1 } },
}
const item = {
  hidden: { opacity: 0, y: 20 },
  show: { opacity: 1, y: 0, transition: { duration: 0.6, ease: [0.22, 0.61, 0.36, 1] } },
}

export default function Home({ databases }) {
  const nav = useNavigate()
  const { t, topic: tt } = useLang()
  const total = databases.reduce((s, d) => s + (d.n_tables || 0), 0)
  const [topics, setTopics] = useState([])
  useEffect(() => {
    api.topics().then(setTopics).catch(() => {})
  }, [])

  return (
    <div className="home">
      <CifraDelDia />
      <section className="hero">
        <motion.div variants={container} initial="hidden" animate="show">
          <motion.div className="hero-eyebrow" variants={item}>
            {t('hero_eyebrow')}
          </motion.div>
          <motion.h1 variants={item}>
            El Perú, <em>en datos</em> que se pueden explorar.
          </motion.h1>
          <motion.p className="hero-lead" variants={item}>
            {t('hero_lead')}
          </motion.p>
          <motion.div variants={item}>
            <button className="hero-cta" onClick={() => nav('/preguntas')}>
              ¿Nuevo aquí? El Perú en 10 preguntas →
            </button>
          </motion.div>
          <motion.div className="hero-stats" variants={item}>
            <div>
              <div className="stat-k"><CountUp to={databases.length || 6} /></div>
              <div className="stat-l">bases de datos</div>
            </div>
            <div>
              <div className="stat-k"><CountUp to={total || 214} /></div>
              <div className="stat-l">indicadores</div>
            </div>
            <div>
              <div className="stat-k"><CountUp to={26} /></div>
              <div className="stat-l">años de datos · 2001–2026</div>
            </div>
            <div>
              <div className="stat-k"><CountUp to={22} suffix="/22" /></div>
              <div className="stat-l">años de pobreza oficial replicada exacta</div>
            </div>
          </motion.div>
        </motion.div>
        <HeroCine />
      </section>

      {topics.length > 0 && (
        <>
          <div className="section-label">{t('q_peru')}</div>
          <motion.div className="topic-grid"
            variants={container} initial="hidden" whileInView="show"
            viewport={{ once: true, margin: '-40px' }}>
            {topics.map((tp) => (
              <motion.button key={tp.topic_key} className="topic-card" variants={item}
                whileHover={{ y: -4 }} onClick={() => nav(`/tema/${tp.topic_key}`)}>
                <span className="topic-card-ico">{TOPIC_META[tp.topic_key]?.icon}</span>
                <span className="topic-card-name">{tt(tp.topic_key, 'label', tp.topic_label)}</span>
                <span className="topic-card-desc">{tt(tp.topic_key, 'desc', TOPIC_META[tp.topic_key]?.desc)}</span>
                <span className="topic-card-n">{tp.tables.length} {t('graficos_n')}</span>
              </motion.button>
            ))}
          </motion.div>
        </>
      )}

      <div className="section-label">{t('story4')}</div>
      <div className="story-list">
        {STORY.map((s) => <StoryChart key={s.table + (s.series || s.mapCol)} {...s} />)}
      </div>

      <div className="section-label">{t('panorama')}</div>
      <motion.section className="kpi-grid"
        variants={container} initial="hidden" whileInView="show"
        viewport={{ once: true, margin: '-60px' }}>
        {PANORAMA.map((k) => <Kpi key={k.table + k.col} {...k} variants={item} />)}
      </motion.section>

      <div className="section-label">{t('hallazgos')}</div>
      <motion.section className="findings-grid"
        variants={container} initial="hidden" whileInView="show"
        viewport={{ once: true, margin: '-60px' }}>
        {FINDINGS.map((f) => <Finding key={f.title} {...f} variants={item} />)}
      </motion.section>

      <div className="section-label">{t('por_fuente')}</div>
      <motion.section className="db-grid"
        variants={container} initial="hidden" animate="show">
        {databases.map((db, i) => (
          <motion.button key={db.schema} className="db-card"
            variants={item}
            whileHover={{ y: -5 }}
            whileTap={{ scale: 0.985 }}
            transition={{ type: 'spring', stiffness: 320, damping: 22 }}
            style={{ '--accent': db.color }}
            onClick={() => nav(`/db/${db.schema}`)}>
            <div className="db-card-idx">0{i + 1}</div>
            <h3>{db.title}</h3>
            <div className="db-card-source" style={{ color: db.color }}>{db.source}</div>
            <p>{db.desc}</p>
            <div className="db-card-foot">
              <span>{db.n_tables} indicadores</span>
              <span className="db-card-go" style={{ color: db.color }}>Explorar →</span>
            </div>
          </motion.button>
        ))}
      </motion.section>
    </div>
  )
}
