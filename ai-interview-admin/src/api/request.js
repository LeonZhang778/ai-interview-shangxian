import axios from 'axios'
import { useAuthStore } from '../stores/auth'
import router from '../router'

const api = axios.create({ baseURL: '/api/v1/backoffice', timeout: 30000 })

api.interceptors.request.use(config => {
  const authStore = useAuthStore()
  if (authStore.token) config.headers.Authorization = `Bearer ${authStore.token}`
  return config
})

let isRefreshing = false
let failedQueue = []

function processQueue(error, token) {
  failedQueue.forEach(({ resolve, reject }) => {
    if (error) reject(error)
    else resolve(token)
  })
  failedQueue = []
}

api.interceptors.response.use(
  res => {
    const data = res.data
    if (data.code === 200) return data.data
    return Promise.reject(new Error(data.message || '请求失败'))
  },
  async err => {
    const originalRequest = err.config
    if (err.response?.status === 401 && !originalRequest._retry) {
      const authStore = useAuthStore()
      if (!authStore.refreshToken) {
        authStore.logout()
        router.push('/login')
        return Promise.reject(err)
      }
      if (isRefreshing) {
        return new Promise((resolve, reject) => {
          failedQueue.push({ resolve, reject })
        }).then(token => {
          originalRequest.headers.Authorization = `Bearer ${token}`
          return api(originalRequest)
        })
      }
      originalRequest._retry = true
      isRefreshing = true
      try {
        const { authApi } = await import('../api')
        const data = await authApi.refresh(authStore.refreshToken)
        authStore.updateToken(data.access_token)
        processQueue(null, data.access_token)
        originalRequest.headers.Authorization = `Bearer ${data.access_token}`
        return api(originalRequest)
      } catch (refreshErr) {
        processQueue(refreshErr, null)
        authStore.logout()
        router.push('/login')
        return Promise.reject(refreshErr)
      } finally {
        isRefreshing = false
      }
    }
    // 403 means the session is valid but the current admin lacks permission.
    // Keep the page and let the caller render the actionable error instead of logging out.
    const data = err.response?.data
    let msg = data?.message || err.message || '网络错误'
    if (data?.detail) {
      msg = Array.isArray(data.detail) ? data.detail.map(d => d.msg).join('; ') : data.detail
    }
    return Promise.reject(new Error(msg))
  }
)

export default api
