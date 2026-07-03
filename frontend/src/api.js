const API_BASE = '/api'
const DEFAULT_TIMEOUT_MS = 12000
const TOKEN_KEY = 'stock_session_token'

export function getAuthToken() {
  return window.localStorage.getItem(TOKEN_KEY)
}

export function setAuthToken(token) {
  if (token) {
    window.localStorage.setItem(TOKEN_KEY, token)
  } else {
    window.localStorage.removeItem(TOKEN_KEY)
  }
}

export async function fetchApi(path, options = {}) {
  const url = `${API_BASE}${path}`
  const { timeoutMs = DEFAULT_TIMEOUT_MS, ...fetchOptions } = options
  const controller = new AbortController()
  const timeoutId = window.setTimeout(() => controller.abort(), timeoutMs)

  try {
    const response = await fetch(url, {
      ...fetchOptions,
      signal: fetchOptions.signal || controller.signal,
      headers: {
        'Content-Type': 'application/json',
        ...(getAuthToken() ? { Authorization: `Bearer ${getAuthToken()}` } : {}),
        ...fetchOptions.headers,
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
    if (error.name === 'AbortError') {
      throw new Error('行情数据源响应超时，请稍后刷新重试')
    }
    if (error.name === 'TypeError' && error.message.includes('fetch')) {
      throw new Error('无法连接到后端服务，请稍后重试')
    }
    throw error
  } finally {
    window.clearTimeout(timeoutId)
  }
}

export const api = {
  // Auth
  getAuthConfig: () => fetchApi('/auth/config'),
  loginWithGoogle: (credential) => fetchApi('/auth/google', {
    method: 'POST',
    body: JSON.stringify({ credential }),
  }),
  loginDev: (email) => fetchApi('/auth/dev', {
    method: 'POST',
    body: JSON.stringify({ email }),
  }),
  getMe: () => fetchApi('/auth/me'),

  // Market
  getMarketOverview: () => fetchApi('/market/overview'),

  // Stock
  searchStock: (keyword) => fetchApi(`/stock/search?keyword=${encodeURIComponent(keyword)}`),
  getStockRealtime: (symbol) => fetchApi(`/stock/${symbol}/realtime`),
  getStockHistory: (symbol, period = 'daily') =>
    fetchApi(`/stock/${symbol}/history?period=${period}`),
  getStockIndicators: (symbol) => fetchApi(`/stock/${symbol}/indicators`),
  getStockSignal: (symbol) => fetchApi(`/stock/${symbol}/signal`),
  getStockDetail: (symbol) => fetchApi(`/stock/${symbol}/detail`, { timeoutMs: 15000 }),

  // Sector
  getSectorList: () => fetchApi('/sector/list'),

  // Quant
  getQuantRequirements: () => fetchApi('/quant/requirements'),
  getQuantAnalysis: (symbol) => fetchApi(`/quant/${symbol}/analysis`, { timeoutMs: 15000 }),
}

export default api
