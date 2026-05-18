import axios from 'axios'

const api = axios.create({
  baseURL: '/api',
  timeout: 30000,
})

// ── Market Data ──────────────────────────────────
export const getInstruments  = ()                     => api.get('/market/instruments')
export const getSymbols      = ()                     => api.get('/market/symbols')
export const getOhlcv        = (symbol, interval='1d', days=365) =>
  api.get(`/market/ohlcv/${encodeURIComponent(symbol)}`, { params: { interval, days } })
export const getLatestBar    = (symbol, interval='1d') =>
  api.get(`/market/ohlcv/${encodeURIComponent(symbol)}/latest`, { params: { interval } })

// ── Analytics ────────────────────────────────────
export const getVolatility   = (symbol, days=365)  =>
  api.get(`/analytics/volatility/${encodeURIComponent(symbol)}`, { params: { days } })
export const getVolMetric    = (symbol, metric, days=365) =>
  api.get(`/analytics/volatility/${encodeURIComponent(symbol)}/${metric}`, { params: { days } })
export const getRegimeHistory = (symbol, days=365) =>
  api.get(`/analytics/regime/${encodeURIComponent(symbol)}`, { params: { days } })
export const getCurrentRegime = (symbol)           =>
  api.get(`/analytics/regime/${encodeURIComponent(symbol)}/current`)
export const getFactorLoadings = (symbol, window=252, days=730) =>
  api.get(`/analytics/factor/${encodeURIComponent(symbol)}`, { params: { window, days } })
export const getLatestFactor  = (symbol, window=252) =>
  api.get(`/analytics/factor/${encodeURIComponent(symbol)}/latest`, { params: { window } })
export const getSummary       = (symbol)           =>
  api.get(`/analytics/summary/${encodeURIComponent(symbol)}`)

// ── Workers ──────────────────────────────────────
export const triggerAll      = (symbol) =>
  api.post(`/analytics/run/all/${encodeURIComponent(symbol)}`)
export const triggerIngest   = (symbol) =>
  api.post(`/ingestion/ingest/${encodeURIComponent(symbol)}`)
export const triggerBackfill = ()       => api.post('/ingestion/backfill')

export default api
