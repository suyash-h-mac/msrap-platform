import React, { useState } from 'react'
import { NavLink, useNavigate } from 'react-router-dom'
import {
  LayoutDashboard, TrendingUp, Activity, PieChart,
  List, RefreshCw, ChevronDown, Zap
} from 'lucide-react'
import { triggerAll, triggerIngest } from '../../services/api'
import SymbolPicker from './SymbolPicker'
import './Layout.css'

const NAV = [
  { path: '/',            icon: LayoutDashboard, label: 'Overview'   },
  { path: '/volatility',  icon: TrendingUp,       label: 'Volatility' },
  { path: '/regime',      icon: Activity,         label: 'Regime'     },
  { path: '/factor',      icon: PieChart,         label: 'Factor'     },
  { path: '/instruments', icon: List,             label: 'Instruments'},
]

export default function Layout({ children, activeSymbol, setActiveSymbol }) {
  const [running, setRunning] = useState(false)
  const [msg, setMsg]         = useState('')

  const runAnalytics = async () => {
    setRunning(true)
    setMsg('Running…')
    try {
      await triggerIngest(activeSymbol)
      await triggerAll(activeSymbol)
      setMsg('Done ✓')
    } catch (e) {
      setMsg('Error')
    } finally {
      setRunning(false)
      setTimeout(() => setMsg(''), 3000)
    }
  }

  return (
    <div className="layout">
      <aside className="sidebar">
        <div className="sidebar-brand">
          <Zap size={18} className="brand-icon" />
          <span>MSRAP</span>
        </div>

        <div className="sidebar-section-label">ANALYTICS</div>
        <nav className="sidebar-nav">
          {NAV.map(({ path, icon: Icon, label }) => (
            <NavLink
              key={path}
              to={path}
              end={path === '/'}
              className={({ isActive }) => `nav-item ${isActive ? 'active' : ''}`}
            >
              <Icon size={15} />
              <span>{label}</span>
            </NavLink>
          ))}
        </nav>

        <div className="sidebar-footer">
          <div className="sidebar-section-label">STATUS</div>
          <div className="status-dot-row">
            <span className="dot-green" /> TimescaleDB
          </div>
          <div className="status-dot-row">
            <span className="dot-green" /> Spring Boot
          </div>
          <div className="status-dot-row">
            <span className="dot-green" /> Analytics
          </div>
        </div>
      </aside>

      <div className="main-wrap">
        <header className="topbar">
          <SymbolPicker
            value={activeSymbol}
            onChange={setActiveSymbol}
          />

          <div className="topbar-right">
            {msg && <span className="topbar-msg">{msg}</span>}
            <button
              className={`run-btn ${running ? 'running' : ''}`}
              onClick={runAnalytics}
              disabled={running}
            >
              <RefreshCw size={13} className={running ? 'spin' : ''} />
              {running ? 'Running…' : 'Run Analytics'}
            </button>
          </div>
        </header>

        <main className="content">
          {children}
        </main>
      </div>
    </div>
  )
}
