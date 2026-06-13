import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import { authApi } from '../api'

export const useAuthStore = defineStore('auth', () => {
  const token = ref(localStorage.getItem('admin_token') || '')
  const refreshTokenValue = ref(localStorage.getItem('admin_refresh_token') || '')
  const email = ref(localStorage.getItem('admin_email') || '')
  const adminId = ref(localStorage.getItem('admin_id') || '')

  const isLoggedIn = computed(() => !!token.value)

  function setAuth(data) {
    token.value = data.access_token
    refreshTokenValue.value = data.refresh_token || ''
    email.value = data.email || ''
    if (data.id) adminId.value = data.id
    localStorage.setItem('admin_token', data.access_token)
    if (data.refresh_token) localStorage.setItem('admin_refresh_token', data.refresh_token)
    localStorage.setItem('admin_email', email.value)
    if (data.id) localStorage.setItem('admin_id', data.id)
  }

  function setAdminInfo(info) {
    if (info.id) {
      adminId.value = info.id
      localStorage.setItem('admin_id', info.id)
    }
  }

  function updateToken(newToken) {
    token.value = newToken
    localStorage.setItem('admin_token', newToken)
  }

  async function logout() {
    if (refreshTokenValue.value) {
      try {
        await authApi.logout(refreshTokenValue.value)
      } catch (_) {}
    }
    token.value = ''
    refreshTokenValue.value = ''
    email.value = ''
    adminId.value = ''
    localStorage.removeItem('admin_token')
    localStorage.removeItem('admin_refresh_token')
    localStorage.removeItem('admin_email')
    localStorage.removeItem('admin_id')
  }

  return { token, refreshToken: refreshTokenValue, email, adminId, isLoggedIn, setAuth, setAdminInfo, updateToken, logout }
})
