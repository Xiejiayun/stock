import { useEffect, useState } from 'react'
import api from '../api'

function QuantDashboard() {
  const [requirements, setRequirements] = useState(null)
  const [symbol, setSymbol] = useState('600519')
  const [analysis, setAnalysis] = useState(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState(null)

  useEffect(() => {
    loadRequirements()
  }, [])

  async function loadRequirements() {
    try {
      setRequirements(await api.getQuantRequirements())
    } catch (err) {
      setError(err.message)
    }
  }

  async function loadAnalysis(e) {
    e?.preventDefault()
    if (!symbol.trim()) return
    try {
      setLoading(true)
      setError(null)
      setAnalysis(await api.getQuantAnalysis(symbol.trim()))
    } catch (err) {
      setError(err.message)
    } finally {
      setLoading(false)
    }
  }

  return (
    <div>
      <div className="grid-2">
        <RequirementCard title="真实系统需求" items={requirements?.system?.product_scope || []} />
        <RequirementCard title="认证与白名单" items={requirements?.system?.auth_requirements || []} />
        <RequirementCard title="量化能力" items={requirements?.system?.quant_requirements || []} />
        <RequirementCard title="数据处理需求" items={requirements?.data?.quality_controls || []} />
      </div>

      <div className="card">
        <div className="card-title">量化分析</div>
        <form className="search-box" onSubmit={loadAnalysis}>
          <input value={symbol} onChange={(e) => setSymbol(e.target.value)} placeholder="输入股票代码，如 600519" />
          <button type="submit" disabled={loading}>{loading ? '分析中...' : '运行分析'}</button>
        </form>
        {error && <div className="error-msg">{error}</div>}
        {loading && <div className="loading">正在计算量化信号...</div>}
      </div>

      {analysis && (
        <div className="grid-2">
          <div className="card">
            <div className="card-title">交易决策</div>
            <div className={`signal-label ${analysis.decision.action.includes('buy') ? 'text-up' : analysis.decision.action.includes('sell') ? 'text-down' : 'text-flat'}`}>
              {analysis.decision.label}
            </div>
            <div className="metric-row"><span>置信度</span><strong>{analysis.decision.confidence_pct}%</strong></div>
            <div className="metric-row"><span>趋势</span><strong>{analysis.trend}</strong></div>
            <p className="text-secondary" style={{ marginTop: 12 }}>{analysis.decision.summary}</p>
          </div>

          <div className="card">
            <div className="card-title">风险与仓位</div>
            <div className="metric-row"><span>风险等级</span><strong>{analysis.risk.level}</strong></div>
            <div className="metric-row"><span>年化波动率</span><strong>{analysis.risk.annualized_volatility_pct}%</strong></div>
            <div className="metric-row"><span>最大回撤</span><strong>{analysis.risk.max_drawdown_pct}%</strong></div>
            <div className="metric-row"><span>建议仓位</span><strong>{analysis.position.suggested_position_pct}%</strong></div>
            <div className="metric-row"><span>止损参考</span><strong>{analysis.position.stop_loss_pct}%</strong></div>
          </div>

          <div className="card">
            <div className="card-title">风险说明</div>
            <ul className="signal-details">
              {analysis.risk.notes.map((note, idx) => <li key={idx}>{note}</li>)}
            </ul>
          </div>

          <div className="card">
            <div className="card-title">数据质量</div>
            <div className="metric-row"><span>样本数</span><strong>{analysis.data_quality.sample_count}</strong></div>
            <div className="metric-row"><span>起始日期</span><strong>{analysis.data_quality.first_date}</strong></div>
            <div className="metric-row"><span>最新日期</span><strong>{analysis.data_quality.last_date}</strong></div>
            {analysis.partial && <div className="warning-msg">部分数据源不可用，结果已降级。</div>}
          </div>
        </div>
      )}
    </div>
  )
}

function RequirementCard({ title, items }) {
  return (
    <div className="card">
      <div className="card-title">{title}</div>
      {items.length ? (
        <ul className="signal-details">
          {items.map((item, idx) => <li key={idx}>{item}</li>)}
        </ul>
      ) : (
        <div className="text-secondary">暂无配置</div>
      )}
    </div>
  )
}

export default QuantDashboard
