import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import api from '../api'

function StockSearch() {
  const [keyword, setKeyword] = useState('')
  const [results, setResults] = useState([])
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState(null)
  const [searched, setSearched] = useState(false)
  const navigate = useNavigate()

  async function handleSearch(e) {
    e?.preventDefault()
    if (!keyword.trim()) return

    try {
      setLoading(true)
      setError(null)
      setSearched(true)
      const data = await api.searchStock(keyword.trim())
      setResults(data)
    } catch (err) {
      setError(err.message)
    } finally {
      setLoading(false)
    }
  }

  function handleKeyDown(e) {
    if (e.key === 'Enter') {
      handleSearch()
    }
  }

  return (
    <div>
      <div className="card">
        <div className="card-title">个股搜索</div>
        <form className="search-box" onSubmit={handleSearch}>
          <input
            type="text"
            placeholder="输入股票代码或名称，如：600519 或 贵州茅台"
            value={keyword}
            onChange={(e) => setKeyword(e.target.value)}
            onKeyDown={handleKeyDown}
          />
          <button type="submit" disabled={loading}>
            {loading ? '搜索中...' : '搜索'}
          </button>
        </form>

        {error && <div className="error-msg">{error}</div>}

        {loading && <div className="loading">正在搜索...</div>}

        {!loading && searched && results.length === 0 && (
          <div style={{ textAlign: 'center', padding: '20px', color: 'var(--text-secondary)' }}>
            未找到匹配的股票
          </div>
        )}

        {results.length > 0 && (
          <table className="data-table">
            <thead>
              <tr>
                <th>代码</th>
                <th>名称</th>
                <th>最新价</th>
                <th>涨跌幅</th>
                <th>操作</th>
              </tr>
            </thead>
            <tbody>
              {results.map((stock) => (
                <tr key={stock.code} onClick={() => navigate(`/stock/${stock.code}`)}>
                  <td>{stock.code}</td>
                  <td>{stock.name}</td>
                  <td>{stock.price?.toFixed(2)}</td>
                  <td className={stock.change_pct > 0 ? 'text-up' : stock.change_pct < 0 ? 'text-down' : 'text-flat'}>
                    {stock.change_pct > 0 ? '+' : ''}{stock.change_pct?.toFixed(2)}%
                  </td>
                  <td>
                    <button
                      onClick={(e) => { e.stopPropagation(); navigate(`/stock/${stock.code}`) }}
                      style={{
                        background: 'var(--accent-blue)',
                        color: '#fff',
                        border: 'none',
                        padding: '4px 12px',
                        borderRadius: '4px',
                        cursor: 'pointer',
                        fontSize: '0.85rem',
                      }}
                    >
                      查看详情
                    </button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>

      <div style={{ marginTop: '16px', fontSize: '0.85rem', color: 'var(--text-secondary)' }}>
        <p>提示：点击搜索结果可查看该股票的K线图、技术指标和交易信号。</p>
        <p style={{ marginTop: '4px' }}>常用示例：600519（贵州茅台）、000001（平安银行）、300750（宁德时代）</p>
      </div>
    </div>
  )
}

export default StockSearch
