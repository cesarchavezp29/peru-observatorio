import { useNavigate } from 'react-router-dom'
import { motion } from 'framer-motion'
import CountUp from './CountUp'
import PeruMapHero from './PeruMapHero'
import Kpi from './Kpi'
import Finding from './Finding'
import StoryChart from './StoryChart'
import { FINDINGS } from '../content'

// the front-page story: full-size live charts, not hidden behind a click
const STORY = [
  { kicker: 'Pobreza', title: 'La pobreza se partió a la mitad', kind: 'line',
    schema: 'enaho', table: 'official_poverty_replication', series: 'poverty_pct', x: 'year',
    lede: 'En 2004, seis de cada diez peruanos eran pobres. Para 2025 son menos de tres. El descenso fue sostenido hasta que la pandemia lo interrumpió en 2020, y luego siguió cayendo.' },
  { kicker: 'Migración', title: 'Todos los caminos llevan a Lima', kind: 'flowmap', reverse: true,
    schema: 'enaho', table: 'migracion_od_departamento', timeCol: 'anio',
    flow: { source: 'origen', target: 'destino', value: 'personas' },
    lede: 'La migración interna tiene un centro que no admite competencia. Cada año decenas de miles de personas se mueven entre departamentos, y casi todas las líneas terminan en la capital.' },
  { kicker: 'Desigualdad', title: 'La desigualdad tiene geografía', kind: 'map',
    schema: 'enaho', table: 'gini_departamento_tiempo', mapCol: 'gini', level: 'dept',
    lede: 'El ingreso se reparte de forma muy distinta según la región. Los departamentos andinos y amazónicos concentran la mayor desigualdad, mientras la costa se reparte de forma más pareja.' },
  { kicker: 'Demografía', title: 'Menos hijos, más escuela', kind: 'line', reverse: true,
    schema: 'endes', table: 'endes_indicadores', series: 'tfr', x: 'anio',
    lede: 'En 2004 una mujer tenía en promedio 2.5 hijos. Hoy son 1.73, por debajo del reemplazo. El Perú entró en la transición demográfica que ya reordena el mercado laboral y las pensiones.' },
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
  const total = databases.reduce((s, d) => s + (d.n_tables || 0), 0)

  return (
    <div className="home">
      <section className="hero">
        <motion.div variants={container} initial="hidden" animate="show">
          <motion.div className="hero-eyebrow" variants={item}>
            Observatorio abierto · microdatos INEI
          </motion.div>
          <motion.h1 variants={item}>
            El Perú, <em>en datos</em> que se pueden explorar.
          </motion.h1>
          <motion.p className="hero-lead" variants={item}>
            Veinte años de encuestas oficiales —hogares, salud, empleo y empresas—
            limpiadas, armonizadas y contrastadas contra las cifras publicadas.
            Elige un indicador y míralo cambiar.
          </motion.p>
          <motion.div className="hero-stats" variants={item}>
            <div>
              <div className="stat-k"><CountUp to={databases.length || 5} /></div>
              <div className="stat-l">bases de datos</div>
            </div>
            <div>
              <div className="stat-k"><CountUp to={total || 207} /></div>
              <div className="stat-l">indicadores</div>
            </div>
            <div>
              <div className="stat-k"><CountUp to={25} /></div>
              <div className="stat-l">años · 2001–2026</div>
            </div>
            <div>
              <div className="stat-k"><CountUp to={100} decimals={0} suffix="%" /></div>
              <div className="stat-l">validado vs INEI</div>
            </div>
          </motion.div>
        </motion.div>
        <PeruMapHero />
      </section>

      <div className="section-label">La historia en cuatro gráficos</div>
      <div className="story-list">
        {STORY.map((s) => <StoryChart key={s.table + (s.series || s.mapCol)} {...s} />)}
      </div>

      <div className="section-label">Panorama nacional · dos décadas de cambio</div>
      <motion.section className="kpi-grid"
        variants={container} initial="hidden" whileInView="show"
        viewport={{ once: true, margin: '-60px' }}>
        {PANORAMA.map((k) => <Kpi key={k.table + k.col} {...k} variants={item} />)}
      </motion.section>

      <div className="section-label">Hallazgos · lo que dicen los datos</div>
      <motion.section className="findings-grid"
        variants={container} initial="hidden" whileInView="show"
        viewport={{ once: true, margin: '-60px' }}>
        {FINDINGS.map((f) => <Finding key={f.title} {...f} variants={item} />)}
      </motion.section>

      <div className="section-label">Explora por fuente</div>
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
