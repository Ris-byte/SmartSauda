let csrfToken = ''
export const setCsrf = (token: string) => { csrfToken = token }
export class ApiError extends Error {
  status: number
  fields: { field: string; type: string; message?: string }[]
  constructor(status: number, message: string, fields: { field: string; type: string; message?: string }[] = []) {
    super(message); this.status = status; this.fields = fields
  }
}
export async function api<T>(path: string, options: RequestInit = {}): Promise<T> {
  const headers = new Headers(options.headers)
  if (options.method && options.method !== 'GET') { headers.set('Content-Type', 'application/json'); if (csrfToken) headers.set('X-CSRF-Token', csrfToken) }
  let response: Response
  try { response = await fetch(`/api/v1${path}`, { ...options, credentials: 'include', headers }) }
  catch (error) { if (error instanceof DOMException && error.name === 'AbortError') throw error; throw new ApiError(0, 'We couldn’t reach SmartSauda. Check your connection and try again.') }
  const body = await response.json().catch(() => null)
  if (!response.ok) {
    if (response.status === 401) window.dispatchEvent(new Event('smartsauda:session-expired'))
    throw new ApiError(response.status, body?.error?.message || 'Something went wrong. Please try again.', body?.error?.fields)
  }
  return body.data as T
}
export async function downloadReport(id: string): Promise<void> {
  const response = await fetch(`/api/v1/predictions/${encodeURIComponent(id)}/report.pdf`, { credentials: 'include' })
  if (!response.ok) {
    if (response.status === 401) window.dispatchEvent(new Event('smartsauda:session-expired'))
    const body = await response.json().catch(() => null)
    throw new ApiError(response.status, body?.error?.message || 'Your report could not be downloaded. Please try again.')
  }
  const url = URL.createObjectURL(await response.blob())
  const link = document.createElement('a')
  link.href = url; link.download = `smartsauda-${id}.pdf`; document.body.append(link); link.click(); link.remove()
  setTimeout(() => URL.revokeObjectURL(url), 30000)
}
export const errorMessage = (error: unknown) => error instanceof Error ? error.message : 'Something went wrong. Please try again.'
