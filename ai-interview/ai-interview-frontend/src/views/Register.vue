<template>
  <div class="auth-page">
    <div class="auth-card">
      <h2>🎯 注册智面</h2>
      <p class="subtitle">创建账号开始 AI 模拟面试</p>

      <form @submit.prevent="handleRegister">
        <div class="form-row">
          <div class="form-group">
            <label>名</label>
            <input v-model="form.first_name" placeholder="名" required />
          </div>
          <div class="form-group">
            <label>姓</label>
            <input v-model="form.last_name" placeholder="姓" required />
          </div>
        </div>
        <div class="form-group">
          <label>邮箱</label>
          <div class="input-with-btn">
            <input v-model="form.email" type="email" placeholder="请输入邮箱" required />
            <button type="button" class="btn-send-code" :disabled="sendCooldown > 0 || sendingCode" @click="handleSendCode">
              {{ sendCooldown > 0 ? sendCooldown + 's' : sendingCode ? '发送中...' : '发送验证码' }}
            </button>
          </div>
        </div>
        <div class="form-group">
          <label>验证码</label>
          <input v-model="form.code" type="text" placeholder="请输入6位验证码" maxlength="6" required class="code-input" />
        </div>
        <div class="form-group">
          <label>密码</label>
          <input v-model="form.password" type="password" placeholder="至少8位，含字母+数字+特殊字符" required />
        </div>
        <p v-if="error" class="error">{{ error }}</p>
        <p v-if="success" class="success">{{ success }}</p>
        <button type="submit" class="btn-glow" :disabled="loading">
          {{ loading ? '注册中...' : '注册' }}
        </button>
      </form>

      <p class="auth-link">已有账号？<router-link to="/login">去登录</router-link></p>
    </div>
  </div>
</template>

<script setup>
import { ref, reactive, onUnmounted } from 'vue'
import { useRouter } from 'vue-router'
import { useAuthStore } from '../stores/auth'
import { sendVerificationCode, register } from '../api/auth'

const router = useRouter()
const authStore = useAuthStore()
const form = reactive({ first_name: '', last_name: '', email: '', password: '', code: '' })
const error = ref('')
const success = ref('')
const loading = ref(false)
const sendingCode = ref(false)
const sendCooldown = ref(0)
let cooldownTimer = null

function startCooldown(seconds = 60) {
  sendCooldown.value = seconds
  cooldownTimer = setInterval(() => {
    sendCooldown.value--
    if (sendCooldown.value <= 0) clearInterval(cooldownTimer)
  }, 1000)
}

async function handleSendCode() {
  if (!form.email) { error.value = '请先填写邮箱'; return }
  error.value = ''; success.value = ''; sendingCode.value = true
  try {
    await sendVerificationCode(form.email, 'registration')
    success.value = '验证码已发送至您的邮箱'
    startCooldown(60)
  } catch (e) {
    error.value = e.message
  } finally {
    sendingCode.value = false
  }
}

async function handleRegister() {
  if (!form.first_name || !form.last_name) { error.value = '请填写姓名'; return }
  if (!form.email) { error.value = '请填写邮箱'; return }
  if (!form.code || form.code.length !== 6) { error.value = '请输入6位验证码'; return }
  if (!form.password) { error.value = '请填写密码'; return }
  error.value = ''; success.value = ''; loading.value = true
  try {
    const data = await register({
      first_name: form.first_name,
      last_name: form.last_name,
      email: form.email,
      password: form.password,
      code: form.code
    })
    authStore.setAuth(data)
    success.value = '注册成功，正在跳转...'
    setTimeout(() => router.push('/dashboard'), 800)
  } catch (e) {
    error.value = e.message
  } finally {
    loading.value = false
  }
}

onUnmounted(() => { if (cooldownTimer) clearInterval(cooldownTimer) })
</script>

<style scoped>
.auth-page { display: flex; align-items: center; justify-content: center; min-height: 100vh; background: linear-gradient(135deg, #f5f7fa 0%, #e4e8f0 100%); }
.auth-card { width: 440px; background: white; border-radius: 16px; padding: 36px; text-align: center; box-shadow: 0 4px 24px rgba(0,0,0,0.08); }
.auth-card h2 { font-size: 24px; color: #4f46e5; margin-bottom: 4px; }
.subtitle { color: #6b7280; margin-bottom: 24px; font-size: 14px; }
.form-row { display: flex; gap: 12px; }
.form-group { margin-bottom: 16px; text-align: left; flex: 1; }
.form-group label { display: block; margin-bottom: 6px; font-size: 14px; font-weight: 500; color: #374151; }
.form-group input { width: 100%; padding: 11px 14px; border: 1px solid #e5e7eb; border-radius: 10px; font-size: 14px; outline: none; transition: all 0.3s; background: #f9fafb; }
.form-group input:focus { border-color: #4f46e5; box-shadow: 0 0 0 3px rgba(79,70,229,0.1); background: white; }
.code-input { font-size: 20px; letter-spacing: 8px; text-align: center; font-weight: 700; }
.input-with-btn { display: flex; gap: 10px; }
.input-with-btn input { flex: 1; }
.btn-send-code {
  white-space: nowrap;
  padding: 11px 16px;
  border: 1px solid #4f46e5;
  border-radius: 10px;
  background: white;
  color: #4f46e5;
  font-size: 13px;
  font-weight: 600;
  cursor: pointer;
  transition: all 0.2s;
}
.btn-send-code:hover:not(:disabled) { background: #eef2ff; }
.btn-send-code:disabled { border-color: #d1d5db; color: #9ca3af; cursor: not-allowed; }
.error { color: #ef4444; font-size: 13px; margin-bottom: 12px; }
.success { color: #10b981; font-size: 13px; margin-bottom: 12px; }
.btn-glow { width: 100%; padding: 12px; border: none; border-radius: 10px; font-size: 15px; font-weight: 600; color: white; background: linear-gradient(135deg, #4f46e5, #7c3aed, #6366f1); background-size: 200% 200%; animation: gradientShift 3s ease infinite; cursor: pointer; transition: all 0.3s; box-shadow: 0 4px 15px rgba(79,70,229,0.4); }
.btn-glow:hover { transform: translateY(-1px); box-shadow: 0 6px 25px rgba(79,70,229,0.5); }
.btn-glow:disabled { opacity: 0.6; cursor: not-allowed; transform: none; }
@keyframes gradientShift { 0% { background-position: 0% 50%; } 50% { background-position: 100% 50%; } 100% { background-position: 0% 50%; } }
.auth-link { margin-top: 18px; font-size: 14px; color: #6b7280; }
.auth-link a { color: #4f46e5; font-weight: 500; }
</style>
