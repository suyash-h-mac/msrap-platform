import React, { useEffect, useState } from 'react'
import { getVolatility, getOhlcv } from '../services/api'
import { Card, StatCard, Grid, Loading, ErrorMsg, SectionHeader } from '../components/dashboard/Cards'
import { SeriesChart, VolConeChart, PriceChart } from '../components/charts/Charts'
import '../components/dashboard/Cards.css'
import './Pages.css'

function pct(v) { return v != null ? `${(v * 100).toFixed(2)}%` : '—' }

export default function VolatilityPage({ symbol }) {
  const [data,    setData]    = useState(null)
  const [ohlcv,   setOhlcv]   = useState([])
  const [loading, setLoading] = useState(true)
  const [error,   setError]   = useState(null)
  const [window_, setWindow]  = useState(21)

  useEffect(() => {
    setLoading(true); setError(null)
    Promise.all([
      getVolatility(symbol, 730, window_),
      getOhlcv(symbol, '1d', 365),
    ]).then(([v, o]) => {
      setData(v.data)
      setOhlcv(Array.isArray(o.data) ? o.data : [])
    }).catch(e => setError(e.message))
    .finally(() => setLoading(false))
  }, [symbol, window_])

  if (loading) return <Loading />
  if (error)   return <ErrorMsg text={error} />
  if (!data)   return null

  const latest  = data.latest || {}
  const garch   = data.garch  || {}
  const cone    = data.cone   || []
  const series  = (data.series || []).map(r => ({ ...r, ts: r.ts || r.date }))

  return (
    <div className="page">
      <SectionHeader
        title={`${symbol} — Volatility Analytics`}
        sub="Realised vol estimators, GARCH conditional volatility, and vol cone"
      />

      {/* Window picker */}
      <div className="window-picker" style={{ marginBottom: 14 }}>
        {[5, 10, 21, 42, 63].map(w => (
          <button
            key={w}
            className={`window-btn ${window_ === w ? 'active' : ''}`}
            onClick={() => setWindow(w)}
          >{w}d</button>
        ))}
      </div>

      <Grid cols={4}>
        <StatCard label="Close-to-Close Vol"  value={pct(latest.cc_vol)}   sub={`${window_}d window, ann.`} />
        <StatCard label="Parkinson Vol"        value={pct(latest.park_vol)} sub="H/L range estimator" />
        <StatCard label="Rogers-Satchell Vol"  value={pct(latest.rs_vol)}   sub="Drift-adjusted" />
        <StatCard label="Yang-Zhang Vol"       value={pct(latest.yz_vol)}   sub="Overnight gap adj." />
      </Grid>

      {garch.model && (
        <Grid cols={3} style={{ marginTop: 12 }}>
          <StatCard label="Best GARCH Model"     value={garch.model}          color="accent" />
          <StatCard label="GARCH Forecast (Ann)" value={pct(garch.forecast_ann)} color="amber" sub="1-day ahead" />
          <StatCard label="AIC"                  value={garch.aic?.toFixed(2)} mono />
        </Grid>
      )}

      {/* Realised vol series */}
      {series.length > 0 && (
        <div style={{ marginTop: 16 }}>
          <Card title="Realised Volatility — Estimator Comparison">
            <SeriesChart
              data={series}
              height={240}
              yFormatter={v => `${(v * 100).toFixed(0)}%`}
              series={[
                { key: 'cc_vol',   label: 'C-to-C',          color: '#3b82f6' },
                { key: 'park_vol', label: 'Parkinson',        color: '#10b981' },
                { key: 'rs_vol',   label: 'Rogers-Satchell',  color: '#f59e0b' },
                { key: 'yz_vol',   label: 'Yang-Zhang',       color: '#8b5cf6' },
              ]}
            />
          </Card>
        </div>
      )}

      {/* Multi-window RV */}
      {series.length > 0 && (
        <div style={{ marginTop: 14 }}>
          <Card title="Realised Volatility — Multiple Windows">
            <SeriesChart
              data={series}
              height={220}
              yFormatter={v => `${(v * 100).toFixed(0)}%`}
              series={[
                { key: 'rv_5d',   label: '5d',  color: '#ef4444' },
                { key: 'rv_21d',  label: '21d', color: '#f59e0b' },
                { key: 'rv_63d',  label: '63d', color: '#3b82f6' },
                { key: 'rv_126d', label: '126d',color: '#10b981' },
                { key: 'rv_252d', label: '252d',color: '#8b5cf6' },
              ]}
            />
          </Card>
        </div>
      )}

      {/* Vol cone */}
      {cone.length > 0 && (
        <div style={{ marginTop: 14 }}>
          <Card title="Volatility Cone — Percentile Distribution">
            <p style={{ fontSize: 12, color: 'var(--text3)', marginBottom: 8 }}>
              Orange dot = current realised vol. Bars show historical percentile distribution.
              Dot above bars = vol is elevated vs history.
            </p>
            <VolConeChart data={cone} height={220} />
          </Card>
        </div>
      )}

      {/* Price chart */}
      {ohlcv.length > 0 && (
        <div style={{ marginTop: 14 }}>
          <Card title="Price Chart (1Y)">
            <PriceChart data={ohlcv} height={200} />
          </Card>
        </div>
      )}
    </div>
  )
}
