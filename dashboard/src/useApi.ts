import { useEffect, useState } from 'react'

interface State<T> {
  data: T | null
  error: string | null
  loading: boolean
}

export function useApi<T>(fetcher: () => Promise<T>, deps: unknown[]): State<T> {
  const [state, setState] = useState<State<T>>({
    data: null,
    error: null,
    loading: true,
  })

  useEffect(() => {
    let active = true
    setState((prev) => ({ ...prev, loading: true }))
    fetcher()
      .then((data) => {
        if (active) setState({ data, error: null, loading: false })
      })
      .catch((error: unknown) => {
        if (active) setState({ data: null, error: String(error), loading: false })
      })
    return () => {
      active = false
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, deps)

  return state
}
