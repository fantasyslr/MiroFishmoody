import { useCallback, useEffect, useRef, useState } from 'react'

type AsyncState<T> =
  | { status: 'idle' }
  | { status: 'loading' }
  | { status: 'success'; data: T }
  | { status: 'error'; error: string }

export function useAsync<T>(fn: () => Promise<T>, deps: unknown[] = []) {
  const [state, setState] = useState<AsyncState<T>>({ status: 'idle' })
  const mountedRef = useRef(true)

  const run = useCallback(() => {
    setState({ status: 'loading' })
    fn()
      .then((data) => {
        if (mountedRef.current) setState({ status: 'success', data })
      })
      .catch((err: unknown) => {
        if (mountedRef.current) {
          setState({
            status: 'error',
            error: err instanceof Error ? err.message : '未知错误',
          })
        }
      })
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, deps)

  useEffect(() => {
    mountedRef.current = true
    return () => {
      mountedRef.current = false
    }
  }, [])

  return { ...state, run }
}
