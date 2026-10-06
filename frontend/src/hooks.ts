import { useEffect, useState } from 'react'
import { api, errorMessage } from './api'
export function useRemote<T>(path: string | null, refreshKey = 0) {
  const [result, setResult] = useState<{ path: string; refreshKey: number; data: T | null; error: string } | null>(null)
  useEffect(() => {
    if (!path) return
    const controller = new AbortController()
    api<T>(path, { signal: controller.signal }).then(data => {
      if (!controller.signal.aborted) setResult({ path, refreshKey, data, error: '' })
    }).catch(error => {
      if (!controller.signal.aborted) setResult({ path, refreshKey, data: null, error: errorMessage(error) })
    })
    return () => controller.abort()
  }, [path, refreshKey])
  const current = path && result?.path === path && result.refreshKey === refreshKey ? result : null
  return { data: current?.data ?? null, loading: Boolean(path && !current), error: current?.error ?? '' }
}
