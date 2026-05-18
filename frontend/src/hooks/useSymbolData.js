/**
 * useSymbolData — shared data-fetching hook for MSRAP pages.
 *
 * Eliminates the repeated Promise.all / useState / useEffect boilerplate
 * that appears in every page component.
 *
 * Usage:
 *   const { data, loading, error } = useSymbolData(symbol, fetchers, deps)
 *
 * @param {string}   symbol   — active ticker symbol (triggers refetch on change)
 * @param {Function} fetchers — async function (symbol) => data object
 * @param {Array}    deps     — extra dependency values beyond symbol (optional)
 *
 * Returns { data, loading, error, refetch }
 *
 * Example — Dashboard:
 *   const { data, loading, error } = useSymbolData(symbol, async (sym) => {
 *     const [summary, ohlcv, regime] = await Promise.all([
 *       getSummary(sym).catch(() => ({ data: null })),
 *       getOhlcv(sym, '1d', 365).catch(() => ({ data: [] })),
 *       getRegimeHistory(sym, 365).catch(() => ({ data: [] })),
 *     ])
 *     return { summary: summary.data, ohlcv: ohlcv.data, regime: regime.data }
 *   })
 */

import { useState, useEffect, useCallback, useRef } from 'react'

/**
 * @template T
 * @param {string}              symbol
 * @param {(sym: string) => Promise<T>} fetcher
 * @param {any[]}               [extraDeps=[]]
 * @returns {{ data: T|null, loading: boolean, error: string|null, refetch: () => void }}
 */
export function useSymbolData(symbol, fetcher, extraDeps = []) {
  const [data,    setData]    = useState(null)
  const [loading, setLoading] = useState(true)
  const [error,   setError]   = useState(null)

  // Stable ref to always use the latest fetcher without adding it as a dep
  const fetcherRef = useRef(fetcher)
  fetcherRef.current = fetcher

  // Counter used to cancel stale responses (symbol changed while in-flight)
  const reqId = useRef(0)

  const load = useCallback(() => {
    if (!symbol) return
    const id = ++reqId.current
    setLoading(true)
    setError(null)

    fetcherRef.current(symbol)
      .then(result => {
        if (id !== reqId.current) return   // stale — discard
        setData(result)
      })
      .catch(err => {
        if (id !== reqId.current) return
        setError(err?.response?.data?.detail ?? err?.message ?? 'Unknown error')
      })
      .finally(() => {
        if (id === reqId.current) setLoading(false)
      })
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [symbol, ...extraDeps])

  useEffect(() => { load() }, [load])

  return { data, loading, error, refetch: load }
}


/**
 * Convenience hook for a single API call that returns an array.
 * Falls back to an empty array on error.
 *
 * Example:
 *   const { items, loading } = useList(symbol, (sym) => getVolatility(sym))
 */
export function useList(symbol, fetcher, extraDeps = []) {
  const { data, loading, error, refetch } = useSymbolData(
    symbol,
    async (sym) => {
      const res = await fetcher(sym)
      return Array.isArray(res.data) ? res.data : []
    },
    extraDeps,
  )
  return { items: data ?? [], loading, error, refetch }
}


/**
 * Convenience hook for a single API call that returns a single object.
 * Falls back to null on error.
 *
 * Example:
 *   const { item, loading } = useItem(symbol, (sym) => getSummary(sym))
 */
export function useItem(symbol, fetcher, extraDeps = []) {
  const { data, loading, error, refetch } = useSymbolData(
    symbol,
    async (sym) => {
      const res = await fetcher(sym)
      return res.data ?? null
    },
    extraDeps,
  )
  return { item: data ?? null, loading, error, refetch }
}
