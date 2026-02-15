import { useState, useRef } from 'react'

function ProgressBar({ label, current, total }) {
  const percent = total > 0 ? Math.round((current / total) * 100) : 0
  return (
    <div className="progress-section">
      <div className="progress-label">
        <span>{label}</span>
        <span>{total > 0 ? `${current}/${total} (${percent}%)` : '---'}</span>
      </div>
      <div className="progress-track">
        <div className="progress-fill" style={{ width: `${percent}%` }} />
      </div>
    </div>
  )
}

export default function App() {
  const [termo, setTermo] = useState('')
  const [cidade, setCidade] = useState('')
  const [loading, setLoading] = useState(false)
  const [stage1, setStage1] = useState({ current: 0, total: 0 })
  const [stage2, setStage2] = useState({ current: 0, total: 0 })
  const [message, setMessage] = useState('')
  const [status, setStatus] = useState('idle') // idle | running | completed | error
  const jobIdRef = useRef(null)

  async function handleStart() {
    if (!termo.trim() || !cidade.trim()) return

    setLoading(true)
    setStatus('running')
    setStage1({ current: 0, total: 0 })
    setStage2({ current: 0, total: 0 })
    setMessage('Iniciando busca...')

    try {
      const res = await fetch('/api/search', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ termo: termo.trim(), cidade: cidade.trim() }),
      })
      const data = await res.json()
      if (!res.ok) {
        setMessage(data.error || 'Erro ao iniciar busca.')
        setStatus('error')
        setLoading(false)
        return
      }

      jobIdRef.current = data.job_id
      listenProgress(data.job_id)
    } catch (err) {
      setMessage('Erro de conexão com o servidor.')
      setStatus('error')
      setLoading(false)
    }
  }

  function listenProgress(jobId) {
    const evtSource = new EventSource(`/api/progress/${jobId}`)

    evtSource.onmessage = (event) => {
      const msg = JSON.parse(event.data)
      if (msg.keepalive) return

      if (msg.message) setMessage(msg.message)

      if (msg.stage === 1) {
        setStage1({ current: msg.current, total: msg.total })
      } else if (msg.stage === 2) {
        setStage2({ current: msg.current, total: msg.total })
      }

      if (msg.status === 'completed') {
        setStatus('completed')
        setLoading(false)
        evtSource.close()
      } else if (msg.status === 'error') {
        setStatus('error')
        setLoading(false)
        evtSource.close()
      }
    }

    evtSource.onerror = () => {
      setMessage('Conexão com o servidor perdida.')
      setStatus('error')
      setLoading(false)
      evtSource.close()
    }
  }

  function handleDownload() {
    if (jobIdRef.current) {
      window.open(`/api/download/${jobIdRef.current}`, '_blank')
    }
  }

  return (
    <div className="container">
      <img src="/logo.png" alt="Google Maps Scraper" className="logo" />

      <div className="form">
        <div className="field">
          <label htmlFor="termo">Termo de busca</label>
          <input
            id="termo"
            type="text"
            placeholder="Ex: confecções"
            value={termo}
            onChange={(e) => setTermo(e.target.value)}
            disabled={loading}
          />
        </div>
        <div className="field">
          <label htmlFor="cidade">Cidade</label>
          <input
            id="cidade"
            type="text"
            placeholder="Ex: Nova Friburgo"
            value={cidade}
            onChange={(e) => setCidade(e.target.value)}
            disabled={loading}
          />
        </div>
        <button onClick={handleStart} disabled={loading || !termo.trim() || !cidade.trim()}>
          {loading ? 'Buscando...' : 'Iniciar Busca'}
        </button>
      </div>

      {status !== 'idle' && (
        <div className="results">
          <ProgressBar label="Etapa 1 — Scraping Google Maps" current={stage1.current} total={stage1.total} />
          <ProgressBar label="Etapa 2 — Extração de Contatos" current={stage2.current} total={stage2.total} />

          <p className={`message ${status}`}>{message}</p>

          {status === 'completed' && (
            <button className="download-btn" onClick={handleDownload}>
              Baixar Arquivo Excel
            </button>
          )}
        </div>
      )}
    </div>
  )
}
