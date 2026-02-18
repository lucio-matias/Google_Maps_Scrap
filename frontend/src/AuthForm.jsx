import { useState } from 'react'

const PASSWORD_RULES = [
  { id: 'length', label: 'Mínimo 8 caracteres', test: (p) => p.length >= 8 },
  { id: 'upper', label: 'Letra maiúscula (A-Z)', test: (p) => /[A-Z]/.test(p) },
  { id: 'lower', label: 'Letra minúscula (a-z)', test: (p) => /[a-z]/.test(p) },
  { id: 'number', label: 'Número (0-9)', test: (p) => /[0-9]/.test(p) },
  { id: 'symbol', label: 'Símbolo (!@#$%...)', test: (p) => /[^A-Za-z0-9]/.test(p) },
]

function EyeIcon({ visible }) {
  return visible ? (
    <svg xmlns="http://www.w3.org/2000/svg" width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
      <path d="M1 12s4-8 11-8 11 8 11 8-4 8-11 8-11-8-11-8z"/>
      <circle cx="12" cy="12" r="3"/>
    </svg>
  ) : (
    <svg xmlns="http://www.w3.org/2000/svg" width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
      <path d="M17.94 17.94A10.07 10.07 0 0 1 12 20c-7 0-11-8-11-8a18.45 18.45 0 0 1 5.06-5.94"/>
      <path d="M9.9 4.24A9.12 9.12 0 0 1 12 4c7 0 11 8 11 8a18.5 18.5 0 0 1-2.16 3.19"/>
      <line x1="1" y1="1" x2="23" y2="23"/>
    </svg>
  )
}

export default function AuthForm({ onAuth }) {
  const [mode, setMode] = useState('login')
  const [name, setName] = useState('')
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [confirmPassword, setConfirmPassword] = useState('')
  const [passwordFocused, setPasswordFocused] = useState(false)
  const [showPassword, setShowPassword] = useState(false)
  const [showConfirmPassword, setShowConfirmPassword] = useState(false)
  const [error, setError] = useState('')
  const [loading, setLoading] = useState(false)

  const passwordChecks = PASSWORD_RULES.map((rule) => ({
    ...rule,
    passed: rule.test(password),
  }))
  const passwordValid = passwordChecks.every((c) => c.passed)
  const passwordsMatch = password === confirmPassword

  async function handleSubmit(e) {
    e.preventDefault()

    if (mode === 'register') {
      if (!name.trim() || !email.trim() || !password || !confirmPassword) return
      if (!passwordValid) {
        setError('A senha não atende aos requisitos de segurança.')
        return
      }
      if (!passwordsMatch) {
        setError('As senhas não coincidem.')
        return
      }
    } else {
      if (!email.trim() || !password) return
    }

    setLoading(true)
    setError('')

    const endpoint = mode === 'login' ? '/api/login' : '/api/register'
    const body =
      mode === 'login'
        ? { email: email.trim(), password }
        : { name: name.trim(), email: email.trim(), password }

    try {
      const res = await fetch(endpoint, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(body),
      })
      const data = await res.json()

      if (!res.ok) {
        setError(data.error || 'Erro ao autenticar.')
        setLoading(false)
        return
      }

      localStorage.setItem('token', data.token)
      localStorage.setItem('username', data.username)
      onAuth(data.token, data.username)
    } catch {
      setError('Erro de conexão com o servidor.')
      setLoading(false)
    }
  }

  function switchMode() {
    setMode(mode === 'login' ? 'register' : 'login')
    setError('')
    setName('')
    setEmail('')
    setPassword('')
    setConfirmPassword('')
    setPasswordFocused(false)
    setShowPassword(false)
    setShowConfirmPassword(false)
  }

  const isSubmitDisabled =
    loading ||
    !email.trim() ||
    !password ||
    (mode === 'register' && (!name.trim() || !confirmPassword || !passwordValid || !passwordsMatch))

  return (
    <div className="auth-wrapper">
      <div className="auth-card">
        <img src="/logo.png" alt="Google Maps Scraper" className="logo" />

        <h2 className="auth-title">
          {mode === 'login' ? 'Entrar na sua conta' : 'Criar conta'}
        </h2>

        <form onSubmit={handleSubmit} className="auth-form">
          {mode === 'register' && (
            <div className="field">
              <label htmlFor="name">Nome</label>
              <input
                id="name"
                type="text"
                placeholder="Digite seu nome completo"
                value={name}
                onChange={(e) => setName(e.target.value)}
                disabled={loading}
                autoComplete="name"
              />
            </div>
          )}

          <div className="field">
            <label htmlFor="email">E-mail</label>
            <input
              id="email"
              type="email"
              placeholder="seu@email.com"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              disabled={loading}
              autoComplete="email"
            />
          </div>

          <div className="field">
            <label htmlFor="password">Senha</label>
            <div className="input-password-wrapper">
              <input
                id="password"
                type={showPassword ? 'text' : 'password'}
                placeholder={mode === 'register' ? 'Crie uma senha segura' : 'Digite sua senha'}
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                onFocus={() => setPasswordFocused(true)}
                onBlur={() => setPasswordFocused(false)}
                disabled={loading}
                autoComplete={mode === 'login' ? 'current-password' : 'new-password'}
              />
              <button
                type="button"
                className="toggle-password"
                onClick={() => setShowPassword(!showPassword)}
                tabIndex={-1}
                aria-label={showPassword ? 'Ocultar senha' : 'Mostrar senha'}
              >
                <EyeIcon visible={showPassword} />
              </button>
            </div>
            {mode === 'register' && (passwordFocused || password.length > 0) && (
              <ul className="password-rules">
                {passwordChecks.map((check) => (
                  <li key={check.id} className={check.passed ? 'rule-ok' : 'rule-fail'}>
                    <span className="rule-icon">{check.passed ? '✓' : '○'}</span>
                    {check.label}
                  </li>
                ))}
              </ul>
            )}
          </div>

          {mode === 'register' && (
            <div className="field">
              <label htmlFor="confirmPassword">Confirmar Senha</label>
              <div className="input-password-wrapper">
                <input
                  id="confirmPassword"
                  type={showConfirmPassword ? 'text' : 'password'}
                  placeholder="Repita a senha"
                  value={confirmPassword}
                  onChange={(e) => setConfirmPassword(e.target.value)}
                  disabled={loading}
                  autoComplete="new-password"
                />
                <button
                  type="button"
                  className="toggle-password"
                  onClick={() => setShowConfirmPassword(!showConfirmPassword)}
                  tabIndex={-1}
                  aria-label={showConfirmPassword ? 'Ocultar senha' : 'Mostrar senha'}
                >
                  <EyeIcon visible={showConfirmPassword} />
                </button>
              </div>
              {confirmPassword.length > 0 && (
                <p className={passwordsMatch ? 'field-success' : 'field-error'}>
                  {passwordsMatch ? '✓ Senhas coincidem' : '✗ As senhas não coincidem'}
                </p>
              )}
            </div>
          )}

          {error && <p className="auth-error">{error}</p>}

          <button type="submit" disabled={isSubmitDisabled}>
            {loading
              ? mode === 'login' ? 'Entrando...' : 'Cadastrando...'
              : mode === 'login' ? 'Entrar' : 'Cadastrar'}
          </button>
        </form>

        <p className="auth-switch">
          {mode === 'login' ? 'Não tem conta?' : 'Já tem conta?'}{' '}
          <button type="button" className="auth-link" onClick={switchMode}>
            {mode === 'login' ? 'Cadastre-se' : 'Entrar'}
          </button>
        </p>
      </div>
    </div>
  )
}
