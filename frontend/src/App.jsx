import { BrowserRouter as Router, Routes, Route, NavLink } from 'react-router-dom'
import MarketOverview from './pages/MarketOverview'
import StockSearch from './pages/StockSearch'
import StockDetail from './pages/StockDetail'
import SectorHeat from './pages/SectorHeat'

function App() {
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
            </nav>
          </div>
        </header>
        <main className="page-content">
          <div className="container">
            <Routes>
              <Route path="/" element={<MarketOverview />} />
              <Route path="/search" element={<StockSearch />} />
              <Route path="/stock/:symbol" element={<StockDetail />} />
              <Route path="/sector" element={<SectorHeat />} />
            </Routes>
          </div>
        </main>
      </div>
    </Router>
  )
}

export default App
