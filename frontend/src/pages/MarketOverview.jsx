import { useState, useEffect } from 'react'
import { BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, Cell } from 'recharts'
import api from '../api'

function MarketOverview() {
  const [data, setData] = useState(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)

  useEffect(() => {
    loadData()
  }, [])

  async function loadData() {
    try {
      setLoading(true)
      setError(null)
      const result = await api.getMarketOverview()
      setData(result)
    } catch (err) {
      setError(err.message)
    } finally {
      setLoading(false)
    }
  }

  if (loading) return <div className="loading">正在加载市场数据...</div>
  if (error) return <div className="error-msg">{error}</div>
  if (!data) return null

  const { indices = [], rise_fall = {}, distribution } = data

  return (
    <div>
      {data.source_status === 'degraded' && data.message && (
        <div className="error-msg">{data.message}，请稍后刷新重试。</div>
      )}

      {/* Major Indices */}
      <div className="card">
        <div className="card-title">主要指数</div>
        {indices.length > 0 ? (
          <div className="grid-3" style={{ gridTemplateColumns: `repeat(${Math.min(indices.length, 5)}, 1fr)` }}>
            {indices.map((idx) => (
              <div key={idx.code} className="index-card">
                <div className="name">{idx.name}</div>
                <div className={`price ${idx.change_pct > 0 ? 'text-up' : idx.change_pct < 0 ? 'text-down' : 'text-flat'}`}>
                  {idx.price?.toFixed(2)}
                </div>
                <div className={`change ${idx.change_pct > 0 ? 'text-up' : idx.change_pct < 0 ? 'text-down' : 'text-flat'}`}>
                  {idx.change_pct > 0 ? '+' : ''}{idx.change_pct?.toFixed(2)}%
                </div>
              </div>
            ))}
          </div>
        ) : (
          <div className="text-secondary">指数行情暂不可用</div>
        )}
      </div>

      {/* Rise/Fall Statistics */}
      <div className="grid-2">
        <div className="card">
          <div className="card-title">涨跌统计</div>
          {rise_fall.total ? (
            <div style={{ fontSize: '0.95rem' }}>
              <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '12px' }}>
                <span>总数: <strong>{rise_fall.total}</strong></span>
                <span className="text-up">上涨: <strong>{rise_fall.rise}</strong></span>
                <span className="text-down">下跌: <strong>{rise_fall.fall}</strong></span>
                <span className="text-flat">平盘: <strong>{rise_fall.flat}</strong></span>
              </div>
              <div style={{ display: 'flex', justifyContent: 'space-between' }}>
                <span className="text-up">涨停: <strong>{rise_fall.limit_up}</strong></span>
                <span className="text-down">跌停: <strong>{rise_fall.limit_down}</strong></span>
              </div>
              {/* Visual bar */}
              <div style={{ marginTop: '16px', height: '24px', borderRadius: '4px', overflow: 'hidden', display: 'flex' }}>
                <div style={{ width: `${(rise_fall.rise / rise_fall.total) * 100}%`, background: 'var(--accent-red)' }} />
                <div style={{ width: `${(rise_fall.flat / rise_fall.total) * 100}%`, background: 'var(--text-secondary)' }} />
                <div style={{ width: `${(rise_fall.fall / rise_fall.total) * 100}%`, background: 'var(--accent-green)' }} />
              </div>
              <div style={{ display: 'flex', justifyContent: 'space-between', marginTop: '4px', fontSize: '0.8rem', color: 'var(--text-secondary)' }}>
                <span>上涨 {((rise_fall.rise / rise_fall.total) * 100).toFixed(1)}%</span>
                <span>下跌 {((rise_fall.fall / rise_fall.total) * 100).toFixed(1)}%</span>
              </div>
            </div>
          ) : (
            <div className="text-secondary">暂无数据</div>
          )}
        </div>

        {/* Distribution Chart */}
        <div className="card">
          <div className="card-title">涨跌幅分布</div>
          {distribution ? (
            <ResponsiveContainer width="100%" height={200}>
              <BarChart data={distribution.labels.map((label, i) => ({
                name: label,
                value: distribution.values[i],
              }))}>
                <CartesianGrid strokeDasharray="3 3" stroke="#2d3748" />
                <XAxis dataKey="name" tick={{ fill: '#a0a0a0', fontSize: 11 }} />
                <YAxis tick={{ fill: '#a0a0a0', fontSize: 11 }} />
                <Tooltip
                  contentStyle={{ background: '#1f2940', border: '1px solid #2d3748' }}
                  labelStyle={{ color: '#e0e0e0' }}
                />
                <Bar dataKey="value" radius={[2, 2, 0, 0]}>
                  {distribution.labels.map((label, i) => (
                    <Cell
                      key={i}
                      fill={label.startsWith('-') || label.startsWith('<-') ? '#66bb6a' : label.startsWith('>') || (label.startsWith('0') || label.match(/^[1-9]/)) ? '#ef5350' : '#a0a0a0'}
                    />
                  ))}
                </Bar>
              </BarChart>
            </ResponsiveContainer>
          ) : (
            <div className="text-secondary">暂无分布数据</div>
          )}
        </div>
      </div>

      <div style={{ textAlign: 'center', marginTop: '12px', fontSize: '0.8rem', color: 'var(--text-secondary)' }}>
        数据更新时间: {data.timestamp ? new Date(data.timestamp).toLocaleString('zh-CN') : '-'}
        {' | '}
        <button onClick={loadData} style={{ background: 'none', border: 'none', color: 'var(--accent-blue)', cursor: 'pointer' }}>
          刷新数据
        </button>
      </div>
    </div>
  )
}

export default MarketOverview
