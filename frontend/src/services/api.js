const API_BASE = import.meta.env.VITE_API_BASE_URL || 'http://127.0.0.1:8000'

async function request(path, options = {}) {
  const response = await fetch(`${API_BASE}${path}`, {
    headers: { 'Content-Type': 'application/json', ...(options.headers || {}) },
    ...options,
  })
  const body = await response.json().catch(() => ({}))
  if (!response.ok) {
    const detail = body.detail
    throw new Error(typeof detail === 'string' ? detail : `Request failed (${response.status})`)
  }
  return body
}
export const getRegions = () => request('/regions')
export const getCarbonRegions = () => request('/carbon-regions')
export const calculateWorkload = (payload) => request('/calculate', { method: 'POST', body: JSON.stringify(payload) })
export const optimizeWorkload = (payload) => request('/optimize', { method: 'POST', body: JSON.stringify(payload) })
