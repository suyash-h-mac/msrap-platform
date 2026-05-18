/**
 * ErrorBoundary — React class component that catches render errors in the
 * component subtree and renders a friendly fallback instead of a blank screen.
 *
 * Usage — wrap each page in App.jsx:
 *   <ErrorBoundary key={activeSymbol}>
 *     <Dashboard symbol={activeSymbol} />
 *   </ErrorBoundary>
 *
 * The `key` prop resets the boundary whenever the symbol changes, so a
 * previous error doesn't block the next page load.
 */

import React from 'react'

export default class ErrorBoundary extends React.Component {
  constructor(props) {
    super(props)
    this.state = { hasError: false, error: null, info: null }
  }

  static getDerivedStateFromError(error) {
    return { hasError: true, error }
  }

  componentDidCatch(error, info) {
    this.setState({ info })
    // In production you'd send this to an error tracking service here
    console.error('[ErrorBoundary]', error, info?.componentStack)
  }

  handleReset = () => {
    this.setState({ hasError: false, error: null, info: null })
  }

  render() {
    const { hasError, error } = this.state
    const { fallback, children } = this.props

    if (!hasError) return children

    if (fallback) return fallback

    return (
      <div className="error-boundary-root">
        <div className="error-boundary-card">
          <div className="error-boundary-icon">⚠</div>
          <div className="error-boundary-title">Something went wrong</div>
          <div className="error-boundary-detail">
            {error?.message || 'An unexpected render error occurred.'}
          </div>
          <button className="error-boundary-btn" onClick={this.handleReset}>
            Try again
          </button>
        </div>
      </div>
    )
  }
}
