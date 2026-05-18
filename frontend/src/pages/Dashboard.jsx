import React from 'react'
import { getSummary, getOhlcv, getRegimeHistory } from '../services/api'
import { Card, StatCard, RegimeBadge, Grid, PageSkeleton, ErrorMsg, SectionHeader } from '../components/dashboard/Cards'
import { PriceChart, RegimeChart } from '../components/charts/Charts'
import { useSymbolData } from '../hooks/useSymbolData'
import '../components/dashboard/Cards.css'
import './Pages.css'

function pct(v) {
  if (v == null) return '—'
  return `${(v * 100).toFixed(2)}%`
}
function fmt4(v) {
  if (v == null) return '—'
  return Number(v).toFixed(4)
}

export default function Dashboard({ symbol }) {
  const { data, loading, error } = useSymbolData(symbol, async (sym) => {
    const [s, o, r] = await Promise.all([
      getSummary(sym).catch(() => ({ data: null })),
      getOhlcv(sym, '1d', 365).catch(() => ({ data: [] })),
      getRegimeHistory(sym, 365).catch(() => ({ data: [] })),
    ])
    return {
      summary: s.data,
      ohlcv:   Array.isArray(o.data) ? o.data : [],
      regime:  Array.isArray(r.data) ? r.data : [],
    }
  })

  if (loading) return <PageSkeleton cards={4} charts={2} />
  if (error)   return <ErrorMsg text={`Failed to load: ${error}`} />

  const { summary = null, ohlcv = [], regime = [] } = data ?? {}

  const regime_info = summary?.regime     ?? {}
  const vol         = summary?.volatility ?? {}
  const factors     = summary?.factors    ?? {}

  return (
    <div className="page">
      <SectionHeader
        title={`${symbol} — Overview`}
        sub="Real-time analytics snapshot"
      />

      {/* Stat row */}
      <Grid cols={4}>
        <StatCard
          label="Regime State"
          value={<RegimeBadge state={regime_info.state} label={regime_info.label} />}
          sub={regime_info.ts ? new Date(regime_info.ts).toLocaleDateString() : ''}
        />
        <StatCard
          label="21d Realised Vol"
          value={pct(vol.rv_21d)}
          color={vol.rv_21d > 0.25 ? 'negative' : 'positive'}
          sub="annualised"
        />
        <StatCard
          label="GARCH Forecast"
          value={pct(vol.garch_forecast_ann)}
          color="amber"
          sub="1-day ahead, ann."
        />
        <StatCard
          label="Market Beta"
          value={fmt4(factors.betaMarket)}
          sub={`R² = ${fmt4(factors.rSquared)}`}
        />
      </Grid>

      {/* Price chart */}
      <div style={{ marginTop: 16 }}>
        <Card title={`${symbol} — Close Price (1Y)`}>
          {ohlcv.length > 0
            ? <PriceChart data={ohlcv} height={240} />
            : <div style={{ padding: '40px', textAlign: 'center', color: 'var(--text3)' }}>
                No price data. Run backfill to fetch historical data.
              </div>
          }
        </Card>
      </div>

      {/* Regime probability */}
      {regime.length > 0 && (
        <div style={{ marginTop: 14 }}>
          <Card title="Regime State Probabilities (1Y)">
            <RegimeChart data={regime} height={180} />
          </Card>
        </div>
      )}

      {/* Factor summary table */}
      {factors.betaMarket != null && (
        <div style={{ marginTop: 14 }}>
          <Card title="Latest Factor Loadings (252-day window)">
            <table className="data-table">
              <thead>
                <tr>
                  <th>Factor</th>
                  <th>Beta</th>
                  <th>Interpretation</th>
                </tr>
              </thead>
              <tbody>
                {[
                  ['Market (MKT)', factors.betaMarket, 'Systematic market exposure'],
                  ['Size (SMB)',   factors.betaSize,    '+ = small-cap tilt'],
                  ['Value (HML)', factors.betaValue,   '+ = value tilt'],
                  ['Momentum',    factors.betaMomentum, '+ = momentum tilt'],
                  ['Quality',     factors.betaQuality,  '+ = quality tilt'],
                ].map(([name, val, desc]) => (
                  <tr key={name}>
                    <td className="mono" style={{ color: 'var(--text)' }}>{name}</td>
                    <td className={`mono ${val > 0 ? 'positive' : val < 0 ? 'negative' : ''}`}>
                      {fmt4(val)}
                    </td>
                    <td style={{ color: 'var(--text3)', fontSize: 12 }}>{desc}</td>
                  </tr>
                ))}
                <tr>
                  <td className="mono" style={{ color: 'var(--text)' }}>R-squared</td>
                  <td className="mono">{fmt4(factors.rSquared)}</td>
                  <td style={{ color: 'var(--text3)', fontSize: 12 }}>Factor model fit</td>
                </tr>
              </tbody>
            </table>
          </Card>
        </div>
      )}
    </div>
  )
}
