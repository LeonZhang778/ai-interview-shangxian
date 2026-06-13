import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import { logoutApi } from '../api/auth'

export const useAuthStore = defineStore('auth', () => {
  const token = ref(localStorage.getItem('token') || '')
  const refreshTokenValue = ref(localStorage.getItem('refreshToken') || '')
  const userEmail = ref(localStorage.getItem('userEmail') || '')
  const userId = ref(localStorage.getItem('userId') || '')
  const userName = ref(localStorage.getItem('userName') || '')
  const userAvatar = ref(localStorage.getItem('userAvatar') || '')

  const isLoggedIn = computed(() => !!token.value)

  function setAuth(data) {
    token.value = data.access_token
    refreshTokenValue.value = data.refresh_token
    userEmail.value = data.user?.email || ''
    userId.value = data.user?.id || ''
    const u = data.user || {}
    userName.value = ((u.last_name || '') + (u.first_name || '')).trim() || u.email || ''
    const avatar = u.avatar || ''
    userAvatar.value = avatar
    localStorage.setItem('token', data.access_token)
    localStorage.setItem('refreshToken', data.refresh_token)
    localStorage.setItem('userEmail', userEmail.value)
    localStorage.setItem('userId', userId.value)
    localStorage.setItem('userName', userName.value)
    localStorage.setItem('userAvatar', userAvatar.value)
  }

  function setUserInfo(info) {
    userName.value = ((info.last_name || '') + (info.first_name || '')).trim() || info.email || ''
    const avatar = info.avatar || ''
    userAvatar.value = avatar
    localStorage.setItem('userName', userName.value)
    localStorage.setItem('userAvatar', userAvatar.value)
  }

  function updateToken(newToken) {
    token.value = newToken
    localStorage.setItem('token', newToken)
  }

  async function logout() {
    // 调用后端 logout 接口销毁 refresh token
    if (refreshTokenValue.value) {
      try {
        await logoutApi(refreshTokenValue.value)
      } catch (_) {
        // 静默失败，不影响本地登出
      }
    }
    token.value = ''
    refreshTokenValue.value = ''
    userEmail.value = ''
    userId.value = ''
    userName.value = ''
    userAvatar.value = ''
    localStorage.removeItem('token')
    localStorage.removeItem('refreshToken')
    localStorage.removeItem('userEmail')
    localStorage.removeItem('userId')
    localStorage.removeItem('userName')
    localStorage.removeItem('userAvatar')
  }

  return { token, refreshToken: refreshTokenValue, userEmail, userId, userName, userAvatar, isLoggedIn, setAuth, setUserInfo, updateToken, logout }
})
