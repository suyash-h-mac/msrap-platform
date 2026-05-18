import React, { useEffect, useState } from 'react'
import { getInstruments, triggerIngest } from '../services/api'
import { Card, Loading, ErrorMsg, SectionHeader } from '../components/dashboard/Cards'
import '../components/dashboard/Cards.css'
import './Pages.css'

export default function InstrumentsPage({ setSymbol }) {
  const [instruments, setInstruments] = useState([])
  const [loading, setLoading]   = useState(true)
  const [error,   setError]     = useState(null)
  const [ingesting, setIngesting] = useState({})
  const [filter, setFilter]     = useState('')

  useEffect(() => {
    getInstruments()
      .then(r => setInstruments(Array.isArray(r.data) ? r.data : []))
      .catch(e => setError(e.message))
      .finally(() => setLoading(false))
  }, [])

  const ingest = async (symbol) => {
    setIngesting(p => ({ ...p, [symbol]: true }))
    try { await triggerIngest(symbol) }
    catch {}
    finally { setIngesting(p => ({ ...p, [symbol]: false })) }
  }

  const filtered = instruments.filter(i =>
    i.symbol?.toLowerCase().includes(filter.toLowerCase()) ||
    i.name?.toLowerCase().includes(filter.toLowerCase()) ||
    i.sector?.toLowerCase().includes(filter.toLowerCase())
  )

  if (loading) return <Loading />
  if (error)   return <ErrorMsg text={error} />

  return (
    <div className="page">
      <SectionHeader
        title="Instruments"
        sub={`${instruments.length} instruments configured`}
      />

      <input
        className="filter-input"
        placeholder="Search symbol, name, sector…"
        value={filter}
        onChange={e => setFilter(e.target.value)}
        style={{ marginBottom: 14 }}
      />

      <Card>
        <table className="data-table full">
          <thead>
            <tr>
              <th>Symbol</th>
              <th>Name</th>
              <th>Exchange</th>
              <th>Type</th>
              <th>Sector</th>
              <th>Status</th>
              <th>Actions</th>
            </tr>
          </thead>
          <tbody>
            {filtered.map(inst => (
              <tr key={inst.symbol}>
                <td>
                  <button
                    className="symbol-link"
                    onClick={() => setSymbol(inst.symbol)}
                  >
                    {inst.symbol}
                  </button>
                </td>
                <td style={{ color: 'var(--text2)' }}>{inst.name || '—'}</td>
                <td className="mono" style={{ color: 'var(--text3)' }}>{inst.exchange || '—'}</td>
                <td>
                  <span className={`badge ${inst.assetClass === 'index' ? 'badge-amber' : 'badge-blue'}`}>
                    {inst.assetClass || '—'}
                  </span>
                </td>
                <td style={{ color: 'var(--text3)', fontSize: 12 }}>{inst.sector || '—'}</td>
                <td>
                  <span className={`badge ${inst.isActive ? 'badge-green' : 'badge-red'}`}>
                    {inst.isActive ? 'Active' : 'Inactive'}
                  </span>
                </td>
                <td>
                  <button
                    className="action-btn"
                    disabled={ingesting[inst.symbol]}
                    onClick={() => ingest(inst.symbol)}
                  >
                    {ingesting[inst.symbol] ? 'Ingesting…' : 'Ingest'}
                  </button>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </Card>
    </div>
  )
}
