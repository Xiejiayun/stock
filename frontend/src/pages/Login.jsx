import { useEffect, useRef, useState } from 'react'
import api from '../api'

function Login({ onLogin }) {
  const googleButtonRef = useRef(null)
  const [config, setConfig] = useState(null)
  const [googleReady, setGoogleReady] = useState(false)
  const [devEmail, setDevEmail] = useState('')
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)

  useEffect(() => {
    loadConfig()
    const timer = window.setInterval(() => {
      if (window.google?.accounts?.id) {
        setGoogleReady(true)
        window.clearInterval(timer)
      }
    }, 200)
    return () => window.clearInterval(timer)
  }, [])

  useEffect(() => {
    if (!config?.google_enabled || !googleReady || !googleButtonRef.current) return

    window.google.accounts.id.initialize({
      client_id: config.google_client_id,
      callback: handleGoogleCredential,
    })
    window.google.accounts.id.renderButton(googleButtonRef.current, {
      theme: 'outline',
      size: 'large',
      width: 320,
      text: 'signin_with',
      shape: 'rectangular',
    })
  }, [config, googleReady])

  async function loadConfig() {
    try {
      setLoading(true)
      setError(null)
      setConfig(await api.getAuthConfig())
    } catch (err) {
      setError(err.message)
    } finally {
      setLoading(false)
    }
  }

  async function handleGoogleCredential(response) {
    try {
      setError(null)
      const data = await api.loginWithGoogle(response.credential)
      onLogin(data)
    } catch (err) {
      setError(err.message)
    }
  }

  async function handleDevLogin(e) {
    e.preventDefault()
    if (!devEmail.trim()) return
    try {
      setError(null)
      const data = await api.loginDev(devEmail.trim())
      onLogin(data)
    } catch (err) {
      setError(err.message)
    }
  }

  return (
    <div className="login-shell">
      <div className="login-panel">
        <div className="login-brand">A股量化交易决策系统</div>
        <div className="login-title">白名单账号登录</div>
        <div className="login-copy">使用 Google 登录后，系统会在服务端校验邮箱白名单。</div>

        {loading && <div className="loading">正在加载登录配置...</div>}
        {error && <div className="error-msg">{error}</div>}

        {!loading && config && (
          <>
            {config.google_enabled ? (
              <div className="google-login-slot" ref={googleButtonRef} />
            ) : (
              <div className="warning-msg">Google 登录尚未配置。请在 Azure App Settings 设置 GOOGLE_CLIENT_ID。</div>
            )}

            {!config.whitelist_configured && (
              <div className="warning-msg">白名单尚未配置。请设置 ALLOWED_EMAILS。</div>
            )}

            {config.dev_login_enabled && (
              <form className="dev-login" onSubmit={handleDevLogin}>
                <input
                  type="email"
                  placeholder="开发登录邮箱"
                  value={devEmail}
                  onChange={(e) => setDevEmail(e.target.value)}
                />
                <button type="submit">开发登录</button>
              </form>
            )}
          </>
        )}
      </div>
    </div>
  )
}

export default Login
