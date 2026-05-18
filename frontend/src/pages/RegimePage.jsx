import React, { useEffect, useState } from 'react'
import { getRegimeHistory, getOhlcv } from '../services/api'
import { Card, StatCard, RegimeBadge, Grid, Loading, ErrorMsg, SectionHeader } from '../components/dashboard/Cards'
import { RegimeChart, PriceChart, SeriesChart } from '../components/charts/Charts'
import '../components/dashboard/Cards.css'
import './Pages.css'

const STATE_META = {
  0: { label: 'Low-Volatility',  color: 'positive', desc: 'Calm, mean-reverting market. Options relatively cheap.' },
  1: { label: 'Trending',        color: 'accent',   desc: 'Directional momentum. Consider trend-following strategies.' },
  2: { label: 'High-Volatility', color: 'negative', desc: 'Stressed market. Fat-tail risks elevated.' },
}

export default function RegimePage({ symbol }) {
  const [data,    setData]    = useState(null)
  const [ohlcv,   setOhlcv]   = useState([])
  const [loading, setLoading] = useState(true)
  const [error,   setError]   = useState(null)

  useEffect(() => {
    setLoading(true); setError(null)
    Promise.all([
      getRegimeHistory(symbol, 1000),
      getOhlcv(symbol, '1d', 365),
    ]).then(([r, o]) => {
      setData(Array.isArray(r.data) ? r.data : [])
      setOhlcv(Array.isArray(o.data) ? o.data : [])
    }).catch(e => setError(e.message))
    .finally(() => setLoading(false))
  }, [symbol])

  if (loading) return <Loading />
  if (error)   return <ErrorMsg text={error} />

  const current = data && data.length > 0 ? data[data.length - 1] : null
  const meta     = current ? STATE_META[current.state] || {} : {}

  // Compute time in each state (%)
  const stateCounts = data ? data.reduce((acc, r) => {
    acc[r.state] = (acc[r.state] || 0) + 1; return acc
  }, {}) : {}
  const total = data ? data.length : 1

  // Transition matrix from data.transition_matrix (not in list — fetch separately if needed)

  return (
    <div className="page">
      <SectionHeader
        title={`${symbol} — Market Regime`}
        sub="3-state Gaussian HMM — low-vol | trending | high-vol"
      />

      {current && (
        <div className="regime-current-card">
          <div>
            <div style={{ fontSize: 12, color: 'var(--text3)', marginBottom: 6 }}>Current regime</div>
            <RegimeBadge state={current.state} label={current.state_label} />
            <div style={{ marginTop: 8, fontSize: 13, color: 'var(--text2)' }}>{meta.desc}</div>
          </div>
          <div className="regime-probs">
            {[0, 1, 2].map(s => (
              <div key={s} className="prob-row">
                <span style={{ color: s === 0 ? 'var(--green)' : s === 1 ? 'var(--accent)' : 'var(--red)', fontSize: 12 }}>
                  {STATE_META[s].label}
                </span>
                <div className="prob-bar-wrap">
                  <div className="prob-bar" style={{
                    width: `${(current[`prob_state${s}`] || 0) * 100}%`,
                    background: s === 0 ? 'var(--green)' : s === 1 ? 'var(--accent)' : 'var(--red)',
                  }} />
                </div>
                <span className="mono" style={{ fontSize: 12, minWidth: 44, textAlign: 'right' }}>
                  {((current[`prob_state${s}`] || 0) * 100).toFixed(1)}%
                </span>
              </div>
            ))}
          </div>
        </div>
      )}

      <Grid cols={3} style={{ marginTop: 14 }}>
        {[0, 1, 2].map(s => (
          <StatCard key={s}
            label={STATE_META[s].label}
            value={`${((stateCounts[s] || 0) / total * 100).toFixed(1)}%`}
            sub={`${stateCounts[s] || 0} days`}
            color={s === 0 ? 'positive' : s === 1 ? 'accent' : 'negative'}
          />
        ))}
      </Grid>

      {data && data.length > 0 && (
        <div style={{ marginTop: 16 }}>
          <Card title="State Probabilities — Historical">
            <RegimeChart data={data} height={220} />
          </Card>
        </div>
      )}

      {ohlcv.length > 0 && (
        <div style={{ marginTop: 14 }}>
          <Card title="Price Chart (1Y)">
            <PriceChart data={ohlcv} height={200} />
          </Card>
        </div>
      )}

      {data && data.length > 0 && (
        <div style={{ marginTop: 14 }}>
          <Card title="State Classification — Raw Signal">
            <SeriesChart
              data={data.map(r => ({ ...r, ts: r.ts }))}
              height={160}
              series={[{ key: 'state', label: 'State (0/1/2)', color: '#8b5cf6' }]}
            />
          </Card>
        </div>
      )}

      {/* Methodology note */}
      <div style={{ marginTop: 14 }}>
        <Card title="Methodology">
          <p style={{ fontSize: 13, color: 'var(--text2)', lineHeight: 1.8 }}>
            <strong>Model:</strong> 3-state Gaussian HMM on daily log-returns + 5d/21d realised volatility.<br />
            <strong>State labels:</strong> Assigned post-hoc by ascending conditional vol mean.<br />
            <strong>Fitting:</strong> Baum-Welch EM algorithm (200 iterations) on full history.<br />
            <strong>Posteriors:</strong> Viterbi path + forward-backward smoothed probabilities.<br />
            <strong>Caution:</strong> HMM states are data-driven, not predictive. Use for state awareness, not trading signals.
          </p>
        </Card>
      </div>
    </div>
  )
}
