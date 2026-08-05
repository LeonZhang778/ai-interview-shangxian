import axios from 'axios'
import { useAuthStore } from '../stores/auth'

const downloadApi = axios.create({
  baseURL: '/api/v1',
  timeout: 60000,
})

export async function downloadBinary(url, fallbackName) {
  const authStore = useAuthStore()
  const res = await downloadApi.get(normalizeApiUrl(url), {
    responseType: 'blob',
    headers: authStore.token ? { Authorization: `Bearer ${authStore.token}` } : {},
    validateStatus: () => true,
  })

  if (res.status < 200 || res.status >= 300 || isJsonResponse(res)) {
    throw new Error(await getBlobErrorMessage(res.data, res.status))
  }

  triggerDownload(res, fallbackName)
  return true
}

function normalizeApiUrl(url) {
  return url.startsWith('/api/v1') ? url.replace('/api/v1', '') : url
}

function isJsonResponse(res) {
  const contentType = res.headers['content-type'] || ''
  return contentType.includes('application/json')
}

async function getBlobErrorMessage(blob, status) {
  const fallback = `导出失败（${status}），请稍后重试`
  if (!(blob instanceof Blob)) return fallback
  try {
    const text = await blob.text()
    const data = JSON.parse(text)
    return pickErrorMessage(data, fallback)
  } catch {
    return fallback
  }
}

function pickErrorMessage(data, fallback) {
  if (data?.message) return data.message
  if (typeof data?.detail === 'string') return data.detail
  if (Array.isArray(data?.detail)) {
    return data.detail.map(item => item?.msg || item?.message || JSON.stringify(item)).join('; ')
  }
  return fallback
}

function triggerDownload(res, fallbackName) {
  const filename = extractFilename(res.headers['content-disposition'] || '', fallbackName)
  const url = window.URL.createObjectURL(res.data)
  const a = document.createElement('a')
  a.href = url
  a.download = filename
  document.body.appendChild(a)
  a.click()
  document.body.removeChild(a)
  window.URL.revokeObjectURL(url)
}

function extractFilename(contentDisposition, fallbackName) {
  const encoded = contentDisposition.match(/filename\*=UTF-8''([^;]+)/i)
  if (encoded?.[1]) return decodeURIComponent(encoded[1])

  const plain = contentDisposition.match(/filename="?([^";]+)"?/i)
  if (plain?.[1]) return decodeURIComponent(plain[1])

  return fallbackName
}
