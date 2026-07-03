import { useEffect, useState } from 'react'
import { BrowserRouter as Router, Routes, Route, NavLink } from 'react-router-dom'
import MarketOverview from './pages/MarketOverview'
import StockSearch from './pages/StockSearch'
import StockDetail from './pages/StockDetail'
import SectorHeat from './pages/SectorHeat'
import QuantDashboard from './pages/QuantDashboard'
import Login from './pages/Login'
import api, { getAuthToken, setAuthToken } from './api'

function App() {
  const [user, setUser] = useState(null)
  const [checking, setChecking] = useState(true)

  useEffect(() => {
    restoreSession()
  }, [])

  async function restoreSession() {
    if (!getAuthToken()) {
      setChecking(false)
      return
    }
    try {
      setUser(await api.getMe())
    } catch (_) {
      setAuthToken(null)
      setUser(null)
    } finally {
      setChecking(false)
    }
  }

  function handleLogin(data) {
    setAuthToken(data.token)
    setUser(data.user)
  }

  function handleLogout() {
    setAuthToken(null)
    setUser(null)
  }

  if (checking) return <div className="loading">正在验证登录状态...</div>
  if (!user) return <Login onLogin={handleLogin} />

  return (
    <Router>
      <div className="app">
        <header className="app-header">
          <div className="container">
            <h1>A股交易决策支持系统</h1>
            <nav className="nav-links">
              <NavLink to="/" end>市场概览</NavLink>
              <NavLink to="/search">个股搜索</NavLink>
              <NavLink to="/sector">板块排名</NavLink>
              <NavLink to="/quant">量化决策</NavLink>
            </nav>
            <div className="user-menu">
              <span>{user.name || user.email}</span>
              <button onClick={handleLogout}>退出</button>
            </div>
          </div>
        </header>
        <main className="page-content">
          <div className="container">
            <Routes>
              <Route path="/" element={<MarketOverview />} />
              <Route path="/search" element={<StockSearch />} />
              <Route path="/stock/:symbol" element={<StockDetail />} />
              <Route path="/sector" element={<SectorHeat />} />
              <Route path="/quant" element={<QuantDashboard />} />
            </Routes>
          </div>
        </main>
      </div>
    </Router>
  )
}

export default App
