<template>
  <div class="login-page">
    <div class="login-card">
      <h2><img src="/site-logo.png" class="login-logo" alt="智面" />智面后台</h2>
      <form @submit.prevent="handleLogin">
        <div class="form-group">
          <label>邮箱</label>
          <input v-model="email" type="email" placeholder="admin@ai-interview.com" required />
        </div>
        <div class="form-group">
          <label>密码</label>
          <input v-model="password" type="password" placeholder="密码" required />
        </div>
        <p v-if="error" class="error">{{ error }}</p>
        <button type="submit" class="btn-glow" :disabled="loading">
          {{ loading ? '登录中...' : '登录' }}
        </button>
      </form>
    </div>
  </div>
</template>

<script setup>
import { ref } from 'vue'
import { useRouter } from 'vue-router'
import { useAuthStore } from '../stores/auth'
import { authApi } from '../api'

const router = useRouter()
const authStore = useAuthStore()
const email = ref('admin@ai-interview.com')
const password = ref('')
const error = ref('')
const loading = ref(false)

async function handleLogin() {
  error.value = ''; loading.value = true
  try {
    const data = await authApi.login(email.value, password.value)
    authStore.setAuth({ ...data, email: email.value })
    try {
      const me = await authApi.me()
      authStore.setAdminInfo(me)
    } catch (_) {}
    router.push('/')
  } catch (e) { error.value = e.message }
  finally { loading.value = false }
}
</script>

<style scoped>
.login-page { display: flex; align-items: center; justify-content: center; min-height: 100vh; background: var(--admin-bg-page); }
.login-card { width: 400px; background: var(--admin-bg-card); border: 1px solid var(--admin-border); border-radius: var(--admin-radius-lg); padding: 40px 36px; text-align: center; box-shadow: var(--admin-shadow-card); }
.login-card h2 { font-size: 24px; color: var(--admin-text-primary); margin-bottom: 28px; display: flex; align-items: center; justify-content: center; gap: 10px; }
.login-logo { width: 40px; height: 40px; border-radius: 50%; object-fit: cover; }
.form-group { margin-bottom: 18px; text-align: left; }
.form-group label { display: block; margin-bottom: 6px; font-size: 14px; font-weight: 500; color: var(--admin-text-primary); }
.form-group input { width: 100%; padding: 11px 14px; border: 1px solid var(--admin-border); border-radius: var(--admin-radius-md); font-size: 14px; outline: none; transition: border-color 0.15s, background-color 0.15s; background: var(--admin-bg-content); }
.form-group input:focus { border-color: var(--admin-primary); outline: 2px solid var(--admin-primary); outline-offset: 2px; box-shadow: none; background: var(--admin-bg-content); }
.error { color: var(--admin-text-primary); font-size: 13px; margin-bottom: 12px; }
.btn-glow { width: 100%; padding: 12px; border: none; border-radius: var(--admin-radius-md); font-size: 15px; font-weight: 500; color: #FFFFFF; background: var(--admin-primary); cursor: pointer; transition: background 0.15s, opacity 0.15s; box-shadow: none; }
.btn-glow:hover { background: var(--admin-primary-hover); transform: none; box-shadow: none; }
.btn-glow:disabled { opacity: 0.4; cursor: not-allowed; transform: none; }
</style>
