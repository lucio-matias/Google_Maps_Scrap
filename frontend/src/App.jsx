import { useState, useRef, useEffect } from 'react'
import AuthForm from './AuthForm.jsx'

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

function ThemeToggle({ theme, toggleTheme }) {
  return (
    <button className="theme-toggle" onClick={toggleTheme} title={`Mudar para modo ${theme === 'light' ? 'escuro' : 'claro'}`}>
      {theme === 'light' ? (
        <svg xmlns="http://www.w3.org/2000/svg" width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><path d="M21 12.79A9 9 0 1 1 11.21 3 7 7 0 0 0 21 12.79z"></path></svg>
      ) : (
        <svg xmlns="http://www.w3.org/2000/svg" width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><circle cx="12" cy="12" r="5"></circle><line x1="12" y1="1" x2="12" y2="3"></line><line x1="12" y1="21" x2="12" y2="23"></line><line x1="4.22" y1="4.22" x2="5.64" y2="5.64"></line><line x1="18.36" y1="18.36" x2="19.78" y2="19.78"></line><line x1="1" y1="12" x2="3" y2="12"></line><line x1="21" y1="12" x2="23" y2="12"></line><line x1="4.22" y1="18.36" x2="5.64" y2="16.92"></line><line x1="18.36" y1="5.64" x2="19.78" y2="4.22"></line></svg>
      )}
    </button>
  )
}

export default function App() {
  const [token, setToken] = useState(() => localStorage.getItem('token') || null)
  const [username, setUsername] = useState(() => localStorage.getItem('username') || '')
  const [theme, setTheme] = useState(() => {
    const savedTheme = localStorage.getItem('theme')
    if (savedTheme) return savedTheme
    return window.matchMedia('(prefers-color-scheme: dark)').matches ? 'dark' : 'light'
  })

  const [termo, setTermo] = useState('')
  const [cidade, setCidade] = useState('')
  const [loading, setLoading] = useState(false)
  const [stage1, setStage1] = useState({ current: 0, total: 0 })
  const [stage2, setStage2] = useState({ current: 0, total: 0 })
  const [message, setMessage] = useState('')
  const [status, setStatus] = useState('idle') // idle | running | completed | error
  const jobIdRef = useRef(null)

  useEffect(() => {
    document.body.setAttribute('data-theme', theme)
    localStorage.setItem('theme', theme)
  }, [theme])

  function toggleTheme() {
    setTheme(prev => prev === 'light' ? 'dark' : 'light')
  }

  function handleAuth(newToken, newUsername) {
    setToken(newToken)
    setUsername(newUsername)
  }

  function handleLogout() {
    localStorage.removeItem('token')
    localStorage.removeItem('username')
    setToken(null)
    setUsername('')
    setStatus('idle')
    setMessage('')
    setStage1({ current: 0, total: 0 })
    setStage2({ current: 0, total: 0 })
    jobIdRef.current = null
  }

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
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${token}`,
        },
        body: JSON.stringify({ termo: termo.trim(), cidade: cidade.trim() }),
      })
      const data = await res.json()

      if (res.status === 401) {
        handleLogout()
        return
      }
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
    const evtSource = new EventSource(`/api/progress/${jobId}?token=${encodeURIComponent(token)}`)

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
      // Append token as query param since fetch with custom headers can't be used for direct downloads
      window.open(`/api/download/${jobIdRef.current}?token=${encodeURIComponent(token)}`, '_blank')
    }
  }

  if (!token) {
    return (
      <div className="auth-theme-wrapper">
        <div style={{ position: 'absolute', top: '24px', right: '24px' }}>
          <ThemeToggle theme={theme} toggleTheme={toggleTheme} />
        </div>
        <AuthForm onAuth={handleAuth} />
      </div>
    )
  }

  return (
    <div className="container">
      <div className="topbar">
        <img src="/logo.png" alt="Google Maps Scraper" className="logo" />
        <div className="user-info">
          <ThemeToggle theme={theme} toggleTheme={toggleTheme} />
          <span className="user-greeting">Olá, <strong>{username}</strong></span>
          <button className="logout-btn" onClick={handleLogout}>Sair</button>
        </div>
      </div>

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
