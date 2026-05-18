import React, { useEffect, useState } from 'react'
import { getSymbols } from '../../services/api'
import { ChevronDown } from 'lucide-react'
import './SymbolPicker.css'

export default function SymbolPicker({ value, onChange }) {
  const [symbols, setSymbols] = useState([])
  const [open, setOpen]       = useState(false)
  const [search, setSearch]   = useState('')

  useEffect(() => {
    getSymbols().then(r => setSymbols(r.data)).catch(() => {
      setSymbols(['^NSEI', '^NSEBANK', 'RELIANCE.NS', 'TCS.NS', 'INFY.NS',
                  'HDFCBANK.NS', 'ICICIBANK.NS', 'SBIN.NS'])
    })
  }, [])

  const filtered = symbols.filter(s =>
    s.toLowerCase().includes(search.toLowerCase())
  )

  const select = (sym) => { onChange(sym); setOpen(false); setSearch('') }

  return (
    <div className="symbol-picker">
      <button className="sp-trigger" onClick={() => setOpen(o => !o)}>
        <span className="sp-value">{value}</span>
        <ChevronDown size={13} className={`sp-chevron ${open ? 'open' : ''}`} />
      </button>

      {open && (
        <div className="sp-dropdown">
          <input
            className="sp-search"
            placeholder="Search symbol…"
            value={search}
            onChange={e => setSearch(e.target.value)}
            autoFocus
          />
          <div className="sp-list">
            {filtered.map(sym => (
              <div
                key={sym}
                className={`sp-item ${sym === value ? 'active' : ''}`}
                onClick={() => select(sym)}
              >
                {sym}
              </div>
            ))}
            {filtered.length === 0 && (
              <div className="sp-empty">No symbols found</div>
            )}
          </div>
        </div>
      )}
    </div>
  )
}
