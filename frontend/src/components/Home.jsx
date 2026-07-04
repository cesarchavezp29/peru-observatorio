import { useNavigate } from 'react-router-dom'
import { motion } from 'framer-motion'
import CountUp from './CountUp'
import PeruMapHero from './PeruMapHero'
import Kpi from './Kpi'

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

      <div className="section-label">Panorama nacional · dos décadas de cambio</div>
      <motion.section className="kpi-grid"
        variants={container} initial="hidden" whileInView="show"
        viewport={{ once: true, margin: '-60px' }}>
        {PANORAMA.map((k) => <Kpi key={k.table + k.col} {...k} variants={item} />)}
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
