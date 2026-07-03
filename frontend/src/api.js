const API_BASE = '/api'

export async function fetchApi(path, options = {}) {
  const url = `${API_BASE}${path}`
  try {
    const response = await fetch(url, {
      ...options,
      headers: {
        'Content-Type': 'application/json',
        ...options.headers,
      },
    })

    if (!response.ok) {
      const errorData = await response.json().catch(() => ({}))
      throw new Error(errorData.detail || `请求失败 (${response.status})`)
    }

    const data = await response.json()
    if (data.code !== 0) {
      throw new Error(data.message || '服务器返回错误')
    }

    return data.data
  } catch (error) {
    if (error.name === 'TypeError' && error.message.includes('fetch')) {
      throw new Error('无法连接到后端服务，请确认后端已启动 (localhost:8000)')
    }
    throw error
  }
}

export const api = {
  // Market
  getMarketOverview: () => fetchApi('/market/overview'),

  // Stock
  searchStock: (keyword) => fetchApi(`/stock/search?keyword=${encodeURIComponent(keyword)}`),
  getStockRealtime: (symbol) => fetchApi(`/stock/${symbol}/realtime`),
  getStockHistory: (symbol, period = 'daily') =>
    fetchApi(`/stock/${symbol}/history?period=${period}`),
  getStockIndicators: (symbol) => fetchApi(`/stock/${symbol}/indicators`),
  getStockSignal: (symbol) => fetchApi(`/stock/${symbol}/signal`),

  // Sector
  getSectorList: () => fetchApi('/sector/list'),
}

export default api
