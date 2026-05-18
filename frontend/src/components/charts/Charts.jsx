import React from 'react'
import {
  ComposedChart, LineChart, BarChart, AreaChart,
  Line, Bar, Area, XAxis, YAxis, Tooltip,
  CartesianGrid, ResponsiveContainer, ReferenceLine, Legend, Cell,
} from 'recharts'
import { format } from 'date-fns'

const fmt = (ts) => {
  try { return format(new Date(ts), 'dd MMM yy') }
  catch { return ts }
}

const tooltipStyle = {
  backgroundColor: '#1c2330',
  border: '1px solid #2d3748',
  borderRadius: 6,
  fontSize: 12,
  fontFamily: 'JetBrains Mono, monospace',
  color: '#e2e8f0',
}

// ── Generic time series line chart ──────────────────────────
export function SeriesChart({ data, series, title, height = 260, yFormatter }) {
  const colors = ['#3b82f6', '#10b981', '#f59e0b', '#8b5cf6', '#14b8a6', '#ef4444']
  return (
    <div className="chart-wrap">
      {title && <div className="chart-title">{title}</div>}
      <ResponsiveContainer width="100%" height={height}>
        <LineChart data={data} margin={{ top: 4, right: 8, left: 0, bottom: 0 }}>
          <CartesianGrid strokeDasharray="3 3" stroke="#1f2937" />
          <XAxis dataKey="ts" tickFormatter={fmt} tick={{ fontSize: 10, fill: '#64748b' }} minTickGap={50} />
          <YAxis tick={{ fontSize: 10, fill: '#64748b' }} tickFormatter={yFormatter} width={58} />
          <Tooltip contentStyle={tooltipStyle} labelFormatter={fmt} />
          <Legend wrapperStyle={{ fontSize: 11 }} />
          {series.map((s, i) => (
            <Line key={s.key} type="monotone" dataKey={s.key} name={s.label || s.key}
              stroke={s.color || colors[i % colors.length]}
              dot={false} strokeWidth={1.5} connectNulls />
          ))}
        </LineChart>
      </ResponsiveContainer>
    </div>
  )
}

// ── OHLCV price chart (close line) ──────────────────────────
export function PriceChart({ data, height = 220 }) {
  return (
    <div className="chart-wrap">
      <ResponsiveContainer width="100%" height={height}>
        <AreaChart data={data} margin={{ top: 4, right: 8, left: 0, bottom: 0 }}>
          <defs>
            <linearGradient id="priceGrad" x1="0" y1="0" x2="0" y2="1">
              <stop offset="5%"  stopColor="#3b82f6" stopOpacity={0.15} />
              <stop offset="95%" stopColor="#3b82f6" stopOpacity={0} />
            </linearGradient>
          </defs>
          <CartesianGrid strokeDasharray="3 3" stroke="#1f2937" />
          <XAxis dataKey="ts" tickFormatter={fmt} tick={{ fontSize: 10, fill: '#64748b' }} minTickGap={50} />
          <YAxis tick={{ fontSize: 10, fill: '#64748b' }} width={70}
            tickFormatter={v => v >= 1000 ? `₹${(v/1000).toFixed(1)}k` : `₹${v.toFixed(0)}`} />
          <Tooltip contentStyle={tooltipStyle} labelFormatter={fmt}
            formatter={(v) => [`₹${Number(v).toLocaleString('en-IN', {maximumFractionDigits:2})}`, 'Close']} />
          <Area type="monotone" dataKey="close" stroke="#3b82f6" fill="url(#priceGrad)"
            strokeWidth={1.5} dot={false} />
        </AreaChart>
      </ResponsiveContainer>
    </div>
  )
}

// ── Regime state overlay ─────────────────────────────────────
const REGIME_COLORS = { 'low-vol': '#10b981', 'trending': '#3b82f6', 'high-vol': '#ef4444' }
const STATE_COLOR   = ['#10b981', '#3b82f6', '#ef4444']

export function RegimeChart({ data, height = 200 }) {
  // data: [{ts, state, prob_state0, prob_state1, prob_state2}]
  return (
    <div className="chart-wrap">
      <ResponsiveContainer width="100%" height={height}>
        <AreaChart data={data} margin={{ top: 4, right: 8, left: 0, bottom: 0 }}>
          <CartesianGrid strokeDasharray="3 3" stroke="#1f2937" />
          <XAxis dataKey="ts" tickFormatter={fmt} tick={{ fontSize: 10, fill: '#64748b' }} minTickGap={50} />
          <YAxis tick={{ fontSize: 10, fill: '#64748b' }} domain={[0, 1]} width={40}
            tickFormatter={v => `${(v * 100).toFixed(0)}%`} />
          <Tooltip contentStyle={tooltipStyle} labelFormatter={fmt}
            formatter={(v, n) => [`${(v * 100).toFixed(1)}%`, n]} />
          <Legend wrapperStyle={{ fontSize: 11 }} />
          <Area type="monotone" dataKey="prob_state0" name="Low-vol"     stackId="1"
            stroke="#10b981" fill="#10b98122" strokeWidth={1} />
          <Area type="monotone" dataKey="prob_state1" name="Trending"    stackId="1"
            stroke="#3b82f6" fill="#3b82f622" strokeWidth={1} />
          <Area type="monotone" dataKey="prob_state2" name="High-vol"    stackId="1"
            stroke="#ef4444" fill="#ef444422" strokeWidth={1} />
        </AreaChart>
      </ResponsiveContainer>
    </div>
  )
}

// ── Vol cone bar chart ───────────────────────────────────────
export function VolConeChart({ data, height = 220 }) {
  // data: [{window, current, p5, p25, p50, p75, p95}]
  return (
    <div className="chart-wrap">
      <ResponsiveContainer width="100%" height={height}>
        <ComposedChart data={data} margin={{ top: 4, right: 8, left: 0, bottom: 0 }}>
          <CartesianGrid strokeDasharray="3 3" stroke="#1f2937" />
          <XAxis dataKey="window" tick={{ fontSize: 10, fill: '#64748b' }}
            tickFormatter={v => `${v}d`} />
          <YAxis tick={{ fontSize: 10, fill: '#64748b' }} width={50}
            tickFormatter={v => `${(v * 100).toFixed(0)}%`} />
          <Tooltip contentStyle={tooltipStyle}
            formatter={(v, n) => [`${(v * 100).toFixed(1)}%`, n]} />
          <Legend wrapperStyle={{ fontSize: 11 }} />
          <Bar dataKey="p5"  name="5th pct"  fill="#2d3748" radius={[2,2,0,0]} />
          <Bar dataKey="p25" name="25th pct" fill="#374151" radius={[2,2,0,0]} />
          <Bar dataKey="p50" name="Median"   fill="#4b5563" radius={[2,2,0,0]} />
          <Bar dataKey="p75" name="75th pct" fill="#374151" radius={[2,2,0,0]} />
          <Bar dataKey="p95" name="95th pct" fill="#2d3748" radius={[2,2,0,0]} />
          <Line type="monotone" dataKey="current" name="Current RV"
            stroke="#f59e0b" dot={{ fill: '#f59e0b', r: 4 }} strokeWidth={2} />
        </ComposedChart>
      </ResponsiveContainer>
    </div>
  )
}

// ── Factor beta bar chart ───────────────────────────────────
export function FactorBetaChart({ data, height = 220 }) {
  // data: [{factor, beta}]
  return (
    <div className="chart-wrap">
      <ResponsiveContainer width="100%" height={height}>
        <BarChart data={data} margin={{ top: 4, right: 8, left: 0, bottom: 0 }} layout="vertical">
          <CartesianGrid strokeDasharray="3 3" stroke="#1f2937" horizontal={false} />
          <XAxis type="number" tick={{ fontSize: 10, fill: '#64748b' }} />
          <YAxis dataKey="factor" type="category" tick={{ fontSize: 11, fill: '#94a3b8' }} width={80} />
          <Tooltip contentStyle={tooltipStyle} formatter={(v) => [v.toFixed(4), 'Beta']} />
          <ReferenceLine x={0} stroke="#64748b" strokeDasharray="3 3" />
          <Bar dataKey="beta" radius={[0,3,3,0]}>
            {data.map((entry, index) => (
              <Cell
                key={`cell-${index}`}
                fill={entry.beta >= 0 ? '#3b82f6' : '#ef4444'}
              />
            ))}
          </Bar>
        </BarChart>
      </ResponsiveContainer>
    </div>
  )
}
