import React, { useState } from 'react'
import { Routes, Route, Navigate } from 'react-router-dom'
import Layout from './components/layout/Layout'
import ErrorBoundary from './components/error/ErrorBoundary'
import Dashboard from './pages/Dashboard'
import VolatilityPage from './pages/VolatilityPage'
import RegimePage from './pages/RegimePage'
import FactorPage from './pages/FactorPage'
import InstrumentsPage from './pages/InstrumentsPage'

export default function App() {
  const [activeSymbol, setActiveSymbol] = useState('^NSEI')

  return (
    <Layout activeSymbol={activeSymbol} setActiveSymbol={setActiveSymbol}>
      <Routes>
        <Route path="/" element={
          <ErrorBoundary key={`dashboard-${activeSymbol}`}>
            <Dashboard symbol={activeSymbol} />
          </ErrorBoundary>
        } />
        <Route path="/volatility" element={
          <ErrorBoundary key={`volatility-${activeSymbol}`}>
            <VolatilityPage symbol={activeSymbol} />
          </ErrorBoundary>
        } />
        <Route path="/regime" element={
          <ErrorBoundary key={`regime-${activeSymbol}`}>
            <RegimePage symbol={activeSymbol} />
          </ErrorBoundary>
        } />
        <Route path="/factor" element={
          <ErrorBoundary key={`factor-${activeSymbol}`}>
            <FactorPage symbol={activeSymbol} />
          </ErrorBoundary>
        } />
        <Route path="/instruments" element={
          <ErrorBoundary key="instruments">
            <InstrumentsPage setSymbol={setActiveSymbol} />
          </ErrorBoundary>
        } />
        <Route path="*" element={<Navigate to="/" />} />
      </Routes>
    </Layout>
  )
}
