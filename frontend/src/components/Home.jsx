import { useNavigate } from 'react-router-dom'

const HIGHLIGHTS = [
  { k: '5', l: 'bases de datos oficiales' },
  { k: '200+', l: 'indicadores analíticos' },
  { k: '2001–2026', l: 'cobertura temporal' },
  { k: '0.00pp', l: 'error vs cifras INEI' },
]

export default function Home({ databases }) {
  const nav = useNavigate()
  return (
    <div className="home">
      <section className="hero">
        <h1>Observatorio de Datos del Perú</h1>
        <p className="hero-lead">
          Veinte años de encuestas oficiales del INEI —hogares, salud, empleo y
          empresas— limpiadas, armonizadas y validadas contra las estadísticas
          publicadas. Explora los indicadores de forma interactiva.
        </p>
        <div className="hero-stats">
          {HIGHLIGHTS.map((h) => (
            <div key={h.l} className="stat">
              <div className="stat-k">{h.k}</div>
              <div className="stat-l">{h.l}</div>
            </div>
          ))}
        </div>
      </section>

      <section className="db-grid">
        {databases.map((db) => (
          <button key={db.schema} className="db-card"
            style={{ '--accent': db.color }}
            onClick={() => nav(`/db/${db.schema}`)}>
            <div className="db-card-bar" style={{ background: db.color }} />
            <h3>{db.title}</h3>
            <div className="db-card-source">{db.source}</div>
            <p>{db.desc}</p>
            <div className="db-card-foot">
              <span>{db.n_tables} indicadores</span>
              <span className="db-card-go">Explorar →</span>
            </div>
          </button>
        ))}
      </section>
    </div>
  )
}
