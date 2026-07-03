import { useState, useEffect } from 'react'
import api from '../api'

function SectorHeat() {
  const [sectors, setSectors] = useState([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)

  useEffect(() => {
    loadData()
  }, [])

  async function loadData() {
    try {
      setLoading(true)
      setError(null)
      const data = await api.getSectorList()
      setSectors(data)
    } catch (err) {
      setError(err.message)
    } finally {
      setLoading(false)
    }
  }

  if (loading) return <div className="loading">正在加载板块数据...</div>

  // Split into gainers and losers
  const gainers = sectors.filter(s => s.change_pct > 0)
  const losers = sectors.filter(s => s.change_pct < 0).reverse()

  return (
    <div>
      {error && <div className="error-msg">{error}</div>}

      <div className="grid-2">
        {/* Top Gainers */}
        <div className="card">
          <div className="card-title">涨幅排名</div>
          {gainers.length > 0 ? (
            <div>
              {gainers.slice(0, 15).map((sector, idx) => (
                <div key={sector.code || idx} className="sector-item">
                  <div style={{ display: 'flex', alignItems: 'center' }}>
                    <span className={`sector-rank ${idx < 3 ? 'top3' : ''}`}>{idx + 1}</span>
                    <div>
                      <div style={{ fontWeight: 500 }}>{sector.name}</div>
                      {sector.leader && (
                        <div style={{ fontSize: '0.8rem', color: 'var(--text-secondary)' }}>
                          领涨: {sector.leader} ({sector.leader_pct > 0 ? '+' : ''}{sector.leader_pct?.toFixed(2)}%)
                        </div>
                      )}
                    </div>
                  </div>
                  <span className="text-up" style={{ fontWeight: 600 }}>
                    +{sector.change_pct?.toFixed(2)}%
                  </span>
                </div>
              ))}
            </div>
          ) : (
            <div style={{ color: 'var(--text-secondary)', textAlign: 'center', padding: '20px' }}>
              暂无上涨板块
            </div>
          )}
        </div>

        {/* Top Losers */}
        <div className="card">
          <div className="card-title">跌幅排名</div>
          {losers.length > 0 ? (
            <div>
              {losers.slice(0, 15).map((sector, idx) => (
                <div key={sector.code || idx} className="sector-item">
                  <div style={{ display: 'flex', alignItems: 'center' }}>
                    <span className={`sector-rank ${idx < 3 ? 'top3' : ''}`}>{idx + 1}</span>
                    <div>
                      <div style={{ fontWeight: 500 }}>{sector.name}</div>
                      {sector.leader && (
                        <div style={{ fontSize: '0.8rem', color: 'var(--text-secondary)' }}>
                          领涨: {sector.leader}
                        </div>
                      )}
                    </div>
                  </div>
                  <span className="text-down" style={{ fontWeight: 600 }}>
                    {sector.change_pct?.toFixed(2)}%
                  </span>
                </div>
              ))}
            </div>
          ) : (
            <div style={{ color: 'var(--text-secondary)', textAlign: 'center', padding: '20px' }}>
              暂无下跌板块
            </div>
          )}
        </div>
      </div>

      <div style={{ textAlign: 'center', marginTop: '12px' }}>
        <button
          onClick={loadData}
          style={{ background: 'none', border: 'none', color: 'var(--accent-blue)', cursor: 'pointer', fontSize: '0.9rem' }}
        >
          刷新数据
        </button>
      </div>
    </div>
  )
}

export default SectorHeat
