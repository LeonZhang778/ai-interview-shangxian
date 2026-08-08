import axios from 'axios'
import { useAuthStore } from '../stores/auth'
import router from '../router'

const api = axios.create({
  baseURL: '/api/v1',
  timeout: 60000
})

// 请求拦截器 - 自动带上 token
api.interceptors.request.use(config => {
  const authStore = useAuthStore()
  // 公开接口（广场、公开笔记详情）即使携带过期 token，后端用 get_current_user_optional 解析，不会 401
  if (authStore.token) {
    config.headers.Authorization = `Bearer ${authStore.token}`
  }
  return config
})

// 是否正在刷新 token
let isRefreshing = false
let pendingRequests = []

// 响应拦截器 - 统一处理错误 + token 刷新
api.interceptors.response.use(
  response => {
    const data = response.data
    if (data.code === 200) {
      return data.data
    }
    return Promise.reject(new Error(data.message || '请求失败'))
  },
  async error => {
    const originalRequest = error.config || {}
    const authStore = useAuthStore()

    // 401 且有 refreshToken 且不是 refresh 请求本身 → 尝试刷新
    if (error.response?.status === 401 && authStore.refreshToken && !originalRequest._retry && !originalRequest.url?.includes('/auth/refresh')) {
      originalRequest._retry = true

      if (isRefreshing) {
        // 已有刷新请求在进行中，排队等待
        return new Promise((resolve, reject) => {
          pendingRequests.push({ resolve, reject })
        }).then(token => {
          originalRequest.headers.Authorization = `Bearer ${token}`
          return api(originalRequest)
        })
      }

      isRefreshing = true
      try {
        const res = await axios.post('/api/v1/auth/refresh', { refresh_token: authStore.refreshToken })
        const data = res.data
        if (data.code === 200) {
          const newToken = data.data.access_token
          authStore.updateToken(newToken)
          // 重试排队的请求
          pendingRequests.forEach(p => p.resolve(newToken))
          pendingRequests = []
          originalRequest.headers.Authorization = `Bearer ${newToken}`
          return api(originalRequest)
        }
      } catch (refreshError) {
        pendingRequests.forEach(p => p.reject(refreshError))
        pendingRequests = []
        authStore.logout()
        router.push('/login')
        return Promise.reject(refreshError)
      } finally {
        isRefreshing = false
      }
    }

    if (error.response?.status === 403 || error.response?.status === 401) {
      // 公开接口（广场、公开笔记详情）即使返回 401/403 也不跳登录页
      const reqUrl = (originalRequest.baseURL || '') + (originalRequest.url || '')
      const isPublic = ['/learning-notes/public', '/experiences/'].some(p => reqUrl.includes(p))
        || /\/learning-notes\/\d+$/.test(reqUrl)
        || /\/experiences\/\d+$/.test(reqUrl)
      if (!isPublic) {
        authStore.logout()
        router.push('/login')
      }
    }
    const data = error.response?.data
    let msg = data?.message || error.message || '网络错误'
    if (data?.detail) {
      if (Array.isArray(data.detail)) {
        msg = data.detail.map(d => d.msg || d.message || JSON.stringify(d)).join('; ')
      } else if (typeof data.detail === 'string') {
        msg = data.detail
      }
    }
    const normalizedError = new Error(msg)
    normalizedError.code = data?.code
    normalizedError.data = data?.data
    return Promise.reject(normalizedError)
  }
)

export default api
