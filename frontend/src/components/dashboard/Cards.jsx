import React from 'react'
import './Cards.css'

export function Card({ title, children, className = '' }) {
  return (
    <div className={`card ${className}`}>
      {title && <div className="card-title">{title}</div>}
      <div className="card-body">{children}</div>
    </div>
  )
}

export function StatCard({ label, value, sub, color, mono }) {
  return (
    <div className="stat-card">
      <div className="stat-label">{label}</div>
      <div className={`stat-value ${color ? color : ''} ${mono ? 'mono' : ''}`}>{value ?? '—'}</div>
      {sub && <div className="stat-sub">{sub}</div>}
    </div>
  )
}

export function RegimeBadge({ state, label }) {
  const cls = state === 0 ? 'badge-green' : state === 1 ? 'badge-blue' : 'badge-red'
  return <span className={`badge ${cls}`}>{label || '—'}</span>
}

export function SectionHeader({ title, sub }) {
  return (
    <div className="section-header">
      <div className="section-title">{title}</div>
      {sub && <div className="section-sub">{sub}</div>}
    </div>
  )
}

export function Loading({ text = 'Loading…' }) {
  return <div className="loading-state">{text}</div>
}

export function Empty({ text = 'No data' }) {
  return <div className="empty-state">{text}</div>
}

export function ErrorMsg({ text }) {
  return <div className="error-state">{text}</div>
}

export function Grid({ cols = 4, children }) {
  return <div className={`grid-${cols}`}>{children}</div>
}

// ── Skeleton components ───────────────────────────────────────────────────────

/** Inline shimmer block — compose into larger skeletons. */
export function Skeleton({ width = '100%', height = 14, style = {} }) {
  return (
    <div
      className="skeleton"
      style={{ width, height, ...style }}
    />
  )
}

/** Full-page skeleton matching the stat-card row + two charts layout. */
export function PageSkeleton({ cards = 4, charts = 2 }) {
  return (
    <div className="page">
      {/* Section header */}
      <div style={{ marginBottom: 14 }}>
        <Skeleton width="30%" height={20} style={{ marginBottom: 6 }} />
        <Skeleton width="18%" height={13} />
      </div>

      {/* Stat cards */}
      <div className={`grid-${cards}`} style={{ marginBottom: 16 }}>
        {Array.from({ length: cards }).map((_, i) => (
          <div key={i} className="skeleton-stat-card">
            <Skeleton width="55%" height={11} style={{ marginBottom: 10 }} />
            <Skeleton width="70%" height={26} style={{ marginBottom: 6 }} />
            <Skeleton width="40%" height={10} />
          </div>
        ))}
      </div>

      {/* Chart placeholders */}
      {Array.from({ length: charts }).map((_, i) => (
        <div key={i} style={{ marginBottom: 14 }}>
          <div className="card">
            <div className="card-title">
              <Skeleton width="25%" height={12} />
            </div>
            <div className="card-body">
              <Skeleton
                className="skeleton-chart"
                width="100%"
                height={220}
              />
            </div>
          </div>
        </div>
      ))}
    </div>
  )
}

/** Skeleton for a single card with a chart inside. */
export function ChartSkeleton({ height = 220 }) {
  return (
    <div className="card">
      <div className="card-title">
        <Skeleton width="30%" height={12} />
      </div>
      <div className="card-body">
        <Skeleton width="100%" height={height} style={{ borderRadius: 8 }} />
      </div>
    </div>
  )
}
