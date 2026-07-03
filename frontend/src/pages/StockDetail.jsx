import { useState, useEffect, useRef } from 'react'
import { useParams, useNavigate } from 'react-router-dom'
import { createChart, CrosshairMode } from 'lightweight-charts'
import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, BarChart, Bar, Cell, ReferenceLine } from 'recharts'
import api from '../api'

function StockDetail() {
  const { symbol } = useParams()
  const navigate = useNavigate()
  const chartContainerRef = useRef(null)
  const chartRef = useRef(null)

  const [realtime, setRealtime] = useState(null)
  const [history, setHistory] = useState([])
  const [indicators, setIndicators] = useState(null)
  const [signal, setSignal] = useState(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)
  const [partialErrors, setPartialErrors] = useState({})

  useEffect(() => {
    loadAllData()
    return () => {
      if (chartRef.current) {
        chartRef.current.remove()
        chartRef.current = null
      }
    }
  }, [symbol])

  useEffect(() => {
    if (history.length > 0 && chartContainerRef.current) {
      renderChart()
    }
  }, [history])

  async function loadAllData() {
    try {
      setLoading(true)
      setError(null)
      setPartialErrors({})

      const data = await api.getStockDetail(symbol)
      setRealtime(data.realtime || null)
      setHistory(data.history || [])
      setIndicators(data.indicators || null)
      setSignal(data.signal || null)
      setPartialErrors(data.errors || {})

      if (!data.realtime && !(data.history || []).length) {
        setError('无法加载股票数据')
      }
    } catch (err) {
      setError(err.message)
    } finally {
      setLoading(false)
    }
  }

  function renderChart() {
    if (chartRef.current) {
      chartRef.current.remove()
    }

    const container = chartContainerRef.current
    if (!container) return

    const chart = createChart(container, {
      width: container.clientWidth,
      height: 400,
      layout: {
        background: { color: '#1f2940' },
        textColor: '#a0a0a0',
      },
      grid: {
        vertLines: { color: '#2d3748' },
        horzLines: { color: '#2d3748' },
      },
      crosshair: {
        mode: CrosshairMode.Normal,
      },
      rightPriceScale: {
        borderColor: '#2d3748',
      },
      timeScale: {
        borderColor: '#2d3748',
        timeVisible: false,
      },
    })

    // Candlestick series
    const candleSeries = chart.addCandlestickSeries({
      upColor: '#ef5350',
      downColor: '#66bb6a',
      borderUpColor: '#ef5350',
      borderDownColor: '#66bb6a',
      wickUpColor: '#ef5350',
      wickDownColor: '#66bb6a',
    })

    const candleData = history.map(item => ({
      time: item.date,
      open: item.open,
      high: item.high,
      low: item.low,
      close: item.close,
    }))

    candleSeries.setData(candleData)

    // MA lines
    if (indicators) {
      const maColors = { ma5: '#ffa726', ma10: '#4fc3f7', ma20: '#ab47bc', ma60: '#26a69a' }
      const maNames = { ma5: 'MA5', ma10: 'MA10', ma20: 'MA20', ma60: 'MA60' }

      for (const [key, color] of Object.entries(maColors)) {
        if (indicators[key] && indicators[key].length > 0) {
          const lineSeries = chart.addLineSeries({
            color: color,
            lineWidth: 1,
            title: maNames[key],
          })

          const lineData = indicators.dates
            .map((date, i) => ({
              time: date,
              value: indicators[key][i],
            }))
            .filter(d => d.value !== null && d.value !== undefined)

          if (lineData.length > 0) {
            lineSeries.setData(lineData)
          }
        }
      }
    }

    // Volume series
    const volumeSeries = chart.addHistogramSeries({
      color: '#4fc3f7',
      priceFormat: { type: 'volume' },
      priceScaleId: '',
    })

    chart.priceScale('').applyOptions({
      scaleMargins: { top: 0.8, bottom: 0 },
    })

    const volumeData = history.map(item => ({
      time: item.date,
      value: item.volume,
      color: item.close >= item.open ? 'rgba(239,83,80,0.5)' : 'rgba(102,187,106,0.5)',
    }))

    volumeSeries.setData(volumeData)

    chart.timeScale().fitContent()
    chartRef.current = chart

    // Handle resize
    const handleResize = () => {
      if (chartRef.current && container) {
        chartRef.current.applyOptions({ width: container.clientWidth })
      }
    }
    window.addEventListener('resize', handleResize)
    return () => window.removeEventListener('resize', handleResize)
  }

  if (loading) return <div className="loading">正在加载股票数据...</div>
  if (error && !realtime && !history.length) return <div className="error-msg">{error}</div>

  const signalClass = signal ? `signal-${signal.signal.replace('_', '-')}` : ''

  return (
    <div>
      {/* Header with stock info */}
      <div className="card">
        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', flexWrap: 'wrap' }}>
          <div>
            <h2 style={{ fontSize: '1.3rem', marginBottom: '4px' }}>
              {realtime?.name || symbol}
              <span style={{ fontSize: '0.85rem', color: 'var(--text-secondary)', marginLeft: '12px' }}>{symbol}</span>
            </h2>
            {realtime && (
              <div style={{ display: 'flex', gap: '20px', alignItems: 'baseline', flexWrap: 'wrap' }}>
                <span style={{ fontSize: '1.8rem', fontWeight: 700 }} className={realtime.change_pct > 0 ? 'text-up' : realtime.change_pct < 0 ? 'text-down' : 'text-flat'}>
                  {realtime.price?.toFixed(2)}
                </span>
                <span className={realtime.change_pct > 0 ? 'text-up' : realtime.change_pct < 0 ? 'text-down' : 'text-flat'}>
                  {realtime.change > 0 ? '+' : ''}{realtime.change?.toFixed(2)}
                  ({realtime.change_pct > 0 ? '+' : ''}{realtime.change_pct?.toFixed(2)}%)
                </span>
              </div>
            )}
          </div>
          {realtime && (
            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(3, 1fr)', gap: '8px 24px', fontSize: '0.85rem' }}>
              <div><span style={{ color: 'var(--text-secondary)' }}>今开:</span> {realtime.open?.toFixed(2)}</div>
              <div><span style={{ color: 'var(--text-secondary)' }}>最高:</span> <span className="text-up">{realtime.high?.toFixed(2)}</span></div>
              <div><span style={{ color: 'var(--text-secondary)' }}>最低:</span> <span className="text-down">{realtime.low?.toFixed(2)}</span></div>
              <div><span style={{ color: 'var(--text-secondary)' }}>昨收:</span> {realtime.pre_close?.toFixed(2)}</div>
              <div><span style={{ color: 'var(--text-secondary)' }}>成交量:</span> {(realtime.volume / 10000).toFixed(0)}万手</div>
              <div><span style={{ color: 'var(--text-secondary)' }}>换手率:</span> {realtime.turnover?.toFixed(2)}%</div>
            </div>
          )}
        </div>
      </div>

      {/* K-line Chart */}
      <div className="card">
        <div className="card-title">K线图 + 均线</div>
        <div ref={chartContainerRef} className="chart-container" />
      </div>

      {/* Indicators + Signal */}
      <div className="grid-2">
        {/* MACD */}
        <div className="card">
          <div className="card-title">MACD</div>
          {indicators && indicators.dif ? (
            <ResponsiveContainer width="100%" height={180}>
              <BarChart data={indicators.dates.map((date, i) => ({
                date: date.slice(5),
                dif: indicators.dif[i],
                dea: indicators.dea[i],
                macd: indicators.macd[i],
              })).slice(-60)} margin={{ top: 5, right: 5, bottom: 5, left: 5 }}>
                <CartesianGrid strokeDasharray="3 3" stroke="#2d3748" />
                <XAxis dataKey="date" tick={{ fill: '#a0a0a0', fontSize: 10 }} interval={9} />
                <YAxis tick={{ fill: '#a0a0a0', fontSize: 10 }} />
                <Tooltip contentStyle={{ background: '#1f2940', border: '1px solid #2d3748', fontSize: '0.85rem' }} />
                <ReferenceLine y={0} stroke="#4a5568" />
                <Bar dataKey="macd" name="MACD柱">
                  {indicators.dates.slice(-60).map((_, i) => {
                    const val = indicators.macd[indicators.macd.length - 60 + i]
                    return <Cell key={i} fill={val >= 0 ? '#ef5350' : '#66bb6a'} />
                  })}
                </Bar>
                <Line type="monotone" dataKey="dif" stroke="#ffa726" dot={false} name="DIF" strokeWidth={1.5} />
                <Line type="monotone" dataKey="dea" stroke="#4fc3f7" dot={false} name="DEA" strokeWidth={1.5} />
              </BarChart>
            </ResponsiveContainer>
          ) : (
            <div style={{ color: 'var(--text-secondary)', textAlign: 'center', padding: '20px' }}>暂无数据</div>
          )}
        </div>

        {/* RSI */}
        <div className="card">
          <div className="card-title">RSI (14)</div>
          {indicators && indicators.rsi ? (
            <ResponsiveContainer width="100%" height={180}>
              <LineChart data={indicators.dates.map((date, i) => ({
                date: date.slice(5),
                rsi: indicators.rsi[i],
              })).slice(-60)} margin={{ top: 5, right: 5, bottom: 5, left: 5 }}>
                <CartesianGrid strokeDasharray="3 3" stroke="#2d3748" />
                <XAxis dataKey="date" tick={{ fill: '#a0a0a0', fontSize: 10 }} interval={9} />
                <YAxis domain={[0, 100]} tick={{ fill: '#a0a0a0', fontSize: 10 }} />
                <Tooltip contentStyle={{ background: '#1f2940', border: '1px solid #2d3748', fontSize: '0.85rem' }} />
                <ReferenceLine y={70} stroke="#ef5350" strokeDasharray="3 3" label={{ value: '超买', fill: '#ef5350', fontSize: 10 }} />
                <ReferenceLine y={30} stroke="#66bb6a" strokeDasharray="3 3" label={{ value: '超卖', fill: '#66bb6a', fontSize: 10 }} />
                <Line type="monotone" dataKey="rsi" stroke="#ab47bc" dot={false} strokeWidth={1.5} name="RSI" />
              </LineChart>
            </ResponsiveContainer>
          ) : (
            <div style={{ color: 'var(--text-secondary)', textAlign: 'center', padding: '20px' }}>暂无数据</div>
          )}
        </div>

        {/* KDJ */}
        <div className="card">
          <div className="card-title">KDJ</div>
          {indicators && indicators.k ? (
            <ResponsiveContainer width="100%" height={180}>
              <LineChart data={indicators.dates.map((date, i) => ({
                date: date.slice(5),
                K: indicators.k[i],
                D: indicators.d[i],
                J: indicators.j[i],
              })).slice(-60)} margin={{ top: 5, right: 5, bottom: 5, left: 5 }}>
                <CartesianGrid strokeDasharray="3 3" stroke="#2d3748" />
                <XAxis dataKey="date" tick={{ fill: '#a0a0a0', fontSize: 10 }} interval={9} />
                <YAxis tick={{ fill: '#a0a0a0', fontSize: 10 }} />
                <Tooltip contentStyle={{ background: '#1f2940', border: '1px solid #2d3748', fontSize: '0.85rem' }} />
                <ReferenceLine y={80} stroke="#ef5350" strokeDasharray="3 3" />
                <ReferenceLine y={20} stroke="#66bb6a" strokeDasharray="3 3" />
                <Line type="monotone" dataKey="K" stroke="#ffa726" dot={false} strokeWidth={1.5} />
                <Line type="monotone" dataKey="D" stroke="#4fc3f7" dot={false} strokeWidth={1.5} />
                <Line type="monotone" dataKey="J" stroke="#ab47bc" dot={false} strokeWidth={1.5} />
              </LineChart>
            </ResponsiveContainer>
          ) : (
            <div style={{ color: 'var(--text-secondary)', textAlign: 'center', padding: '20px' }}>暂无数据</div>
          )}
        </div>

        {/* Trading Signal */}
        <div className="card">
          <div className="card-title">综合交易信号</div>
          {signal ? (
            <div className="signal-panel">
              <div className={`signal-label ${signal.signal === 'strong_buy' || signal.signal === 'buy' ? 'text-up' : signal.signal === 'strong_sell' || signal.signal === 'sell' ? 'text-down' : ''}`}>
                {signal.signal_cn}
              </div>
              <div className={`signal-badge ${signalClass}`}>
                评分: {signal.score}/6 | 置信度: {signal.confidence}%
              </div>
              <div className="confidence" style={{ marginTop: '8px' }}>
                {signal.explanation}
              </div>
              {signal.details && signal.details.length > 0 && (
                <ul className="signal-details">
                  {signal.details.map((detail, i) => (
                    <li key={i}>{detail}</li>
                  ))}
                </ul>
              )}
            </div>
          ) : (
            <div style={{ color: 'var(--text-secondary)', textAlign: 'center', padding: '20px' }}>
              {partialErrors.signal || partialErrors.history || '暂无交易信号'}
            </div>
          )}
        </div>
      </div>

      {/* Back button */}
      <div style={{ marginTop: '16px', textAlign: 'center' }}>
        <button
          onClick={() => navigate('/search')}
          style={{
            background: 'var(--bg-card)',
            color: 'var(--accent-blue)',
            border: '1px solid var(--border-color)',
            padding: '8px 24px',
            borderRadius: '6px',
            cursor: 'pointer',
            fontSize: '0.9rem',
          }}
        >
          返回搜索
        </button>
      </div>

      {/* Disclaimer */}
      <div style={{ marginTop: '24px', padding: '12px', background: 'rgba(255,167,38,0.08)', borderRadius: '6px', fontSize: '0.8rem', color: 'var(--accent-orange)' }}>
        免责声明：本系统提供的交易信号仅供参考，不构成投资建议。股市有风险，投资需谨慎。请结合自身判断做出投资决策。
      </div>
    </div>
  )
}

export default StockDetail
