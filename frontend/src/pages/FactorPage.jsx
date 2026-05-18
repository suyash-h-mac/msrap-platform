import React, { useEffect, useState } from 'react'
import { getFactorLoadings } from '../services/api'
import { Card, StatCard, Grid, Loading, ErrorMsg, SectionHeader } from '../components/dashboard/Cards'
import { SeriesChart, FactorBetaChart } from '../components/charts/Charts'
import '../components/dashboard/Cards.css'
import './Pages.css'

function fmt(v, d=4) { return v != null && !isNaN(v) ? Number(v).toFixed(d) : '—' }

const FACTOR_META = {
  beta_mkt:  { label: 'Market (MKT)', desc: 'Exposure to broad market risk' },
  beta_smb:  { label: 'Size (SMB)',   desc: 'Small cap tilt. + = small, - = large' },
  beta_hml:  { label: 'Value (HML)',  desc: 'Value tilt. + = value, - = growth' },
  beta_mom:  { label: 'Momentum',     desc: '12-1 month price momentum' },
  beta_qmj:  { label: 'Quality (QMJ)', desc: 'Quality tilt via Sharpe proxy' },
}

export default function FactorPage({ symbol }) {
  const [data,    setData]    = useState(null)
  const [loading, setLoading] = useState(true)
  const [error,   setError]   = useState(null)
  const [window_, setWindow]  = useState(252)

  useEffect(() => {
    setLoading(true); setError(null)
    getFactorLoadings(symbol, window_, 1825)
      .then(r => setData(r.data))
      .catch(e => setError(e.message))
      .finally(() => setLoading(false))
  }, [symbol, window_])

  if (loading) return <Loading />
  if (error)   return <ErrorMsg text={error} />
  if (!data)   return null

  const latest  = data.latest   || {}
  const full    = data.full_period || {}
  const rolling = data.rolling  || []

  const betaBarData = Object.entries(FACTOR_META)
    .map(([key, meta]) => ({ factor: meta.label, beta: latest[key] || full[key] || 0 }))
    .filter(d => d.beta !== 0)

  return (
    <div className="page">
      <SectionHeader
        title={`${symbol} — Factor Risk Decomposition`}
        sub="Rolling OLS on India equity factors — market, size, value, momentum, quality"
      />

      <div className="window-picker" style={{ marginBottom: 14 }}>
        {[126, 252, 504].map(w => (
          <button key={w}
            className={`window-btn ${window_ === w ? 'active' : ''}`}
            onClick={() => setWindow(w)}>
            {w}d
          </button>
        ))}
      </div>

      <Grid cols={4}>
        <StatCard label="Alpha (Ann.)"    value={fmt(latest.alpha || full.alpha, 4)}    sub="vs factor model" />
        <StatCard label="R-squared"       value={fmt(latest.r_squared || full.r_squared, 4)} sub="Factor model fit" />
        <StatCard label="Residual Vol"    value={`${fmt((latest.residual_vol || full.residual_vol || 0) * 100, 2)}%`} sub="Specific risk (ann.)" />
        <StatCard label="Market Beta"     value={fmt(latest.beta_mkt || full.beta_mkt, 4)} color="accent" />
      </Grid>

      {/* Beta bar chart */}
      {betaBarData.length > 0 && (
        <div style={{ marginTop: 16 }}>
          <Card title="Current Factor Betas">
            <FactorBetaChart data={betaBarData} height={200} />
          </Card>
        </div>
      )}

      {/* Rolling betas */}
      {rolling.length > 0 && (
        <div style={{ marginTop: 14 }}>
          <Card title={`Rolling Beta — Market (${window_}d window)`}>
            <SeriesChart
              data={rolling.map(r => ({ ...r, ts: r.date || r.ts }))}
              height={200}
              series={[{ key: 'beta_mkt', label: 'Market Beta', color: '#3b82f6' }]}
              yFormatter={v => v.toFixed(2)}
            />
          </Card>
        </div>
      )}

      {rolling.length > 0 && (
        <div style={{ marginTop: 14 }}>
          <Card title={`Rolling Factor Betas — All Factors (${window_}d window)`}>
            <SeriesChart
              data={rolling.map(r => ({ ...r, ts: r.date || r.ts }))}
              height={240}
              series={[
                { key: 'beta_mkt', label: 'MKT',      color: '#3b82f6' },
                { key: 'beta_smb', label: 'SMB (Size)', color: '#10b981' },
                { key: 'beta_mom', label: 'MOM',       color: '#f59e0b' },
                { key: 'beta_hml', label: 'HML (Value)', color: '#8b5cf6' },
              ]}
              yFormatter={v => v.toFixed(2)}
            />
          </Card>
        </div>
      )}

      {rolling.length > 0 && (
        <div style={{ marginTop: 14 }}>
          <Card title="Rolling R-squared">
            <SeriesChart
              data={rolling.map(r => ({ ...r, ts: r.date || r.ts }))}
              height={160}
              series={[{ key: 'r_squared', label: 'R²', color: '#14b8a6' }]}
              yFormatter={v => `${(v * 100).toFixed(0)}%`}
            />
          </Card>
        </div>
      )}

      {/* Detailed factor table */}
      <div style={{ marginTop: 14 }}>
        <Card title="Full-Period Factor Loadings">
          <table className="data-table">
            <thead>
              <tr>
                <th>Factor</th>
                <th>Beta</th>
                <th>Description</th>
              </tr>
            </thead>
            <tbody>
              {Object.entries(FACTOR_META).map(([key, meta]) => (
                <tr key={key}>
                  <td style={{ color: 'var(--text)' }}>{meta.label}</td>
                  <td className={`mono ${(full[key] || 0) > 0 ? 'positive' : 'negative'}`}>
                    {fmt(full[key])}
                  </td>
                  <td style={{ color: 'var(--text3)', fontSize: 12 }}>{meta.desc}</td>
                </tr>
              ))}
              <tr>
                <td>Alpha (Ann.)</td>
                <td className={`mono ${(full.alpha || 0) > 0 ? 'positive' : 'negative'}`}>
                  {fmt(full.alpha)}
                </td>
                <td style={{ color: 'var(--text3)', fontSize: 12 }}>Unexplained return</td>
              </tr>
              <tr>
                <td>R-squared</td>
                <td className="mono">{fmt(full.r_squared)}</td>
                <td style={{ color: 'var(--text3)', fontSize: 12 }}>Variance explained by factors</td>
              </tr>
            </tbody>
          </table>
        </Card>
      </div>

      <div style={{ marginTop: 14 }}>
        <Card title="Methodology">
          <p style={{ fontSize: 13, color: 'var(--text2)', lineHeight: 1.8 }}>
            <strong>Factor construction:</strong> Fama-French style, built from NSE universe via cross-sectional sorts.<br />
            <strong>MKT:</strong> Equal-weighted universe return minus risk-free rate (6.5% p.a. proxy).<br />
            <strong>SMB:</strong> High-vol (small cap proxy) minus low-vol stocks.<br />
            <strong>HML:</strong> 36-month return reversal spread (low past return = high B/M proxy).<br />
            <strong>MOM:</strong> 12-1 month momentum: winner decile minus loser decile.<br />
            <strong>OLS:</strong> Rolling {window_}-day window. Alpha annualised. Residual vol = specific risk.
          </p>
        </Card>
      </div>
    </div>
  )
}
