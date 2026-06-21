const SESSION_KEY = 'admin_pv_session_id'
const SESSION_TTL = 24 * 60 * 60 * 1000

function getSessionId() {
  try {
    const raw = localStorage.getItem(SESSION_KEY)
    if (raw) {
      const { id, ts } = JSON.parse(raw)
      if (Date.now() - ts < SESSION_TTL) return id
    }
  } catch (_) {}
  const id = crypto.randomUUID ? crypto.randomUUID() : Math.random().toString(36).slice(2)
  localStorage.setItem(SESSION_KEY, JSON.stringify({ id, ts: Date.now() }))
  return id
}

export function trackPageView(path) {
  const body = JSON.stringify({ page_path: '/admin' + path, session_id: getSessionId() })
  if (navigator.sendBeacon) {
    navigator.sendBeacon('/api/v1/track/pageview', new Blob([body], { type: 'application/json' }))
  } else {
    fetch('/api/v1/track/pageview', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body,
      keepalive: true,
    }).catch(() => {})
  }
}
