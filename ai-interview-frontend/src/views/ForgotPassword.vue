<template>
  <div class="auth-page">
    <div class="auth-card">
      <!-- Step 1: 输入邮箱 -->
      <template v-if="step === 1">
        <h2>🔑 忘记密码</h2>
        <p class="subtitle">输入您的注册邮箱，我们将发送验证码</p>
        <form @submit.prevent="handleSendCode">
          <div class="form-group">
            <label>邮箱</label>
            <input v-model="email" type="email" placeholder="请输入注册邮箱" required />
          </div>
          <p v-if="error" class="error">{{ error }}</p>
          <button type="submit" class="btn-glow" :disabled="loading">
            {{ loading ? '发送中...' : '发送验证码' }}
          </button>
        </form>
        <p class="auth-link"><router-link to="/login">返回登录</router-link></p>
      </template>

      <!-- Step 2: 输入验证码 -->
      <template v-else-if="step === 2">
        <h2>📧 验证码</h2>
        <p class="subtitle">验证码已发送至 <strong>{{ email }}</strong></p>
        <form @submit.prevent="handleVerifyCode">
          <div class="form-group">
            <label>验证码</label>
            <input v-model="code" type="text" placeholder="请输入6位验证码" maxlength="6" required class="code-input" />
          </div>
          <p v-if="error" class="error">{{ error }}</p>
          <button type="submit" class="btn-glow" :disabled="loading">
            {{ loading ? '验证中...' : '验证' }}
          </button>
        </form>
        <p class="auth-link">
          <span v-if="resendCountdown > 0">{{ resendCountdown }}s 后可重新发送</span>
          <a v-else href="#" @click.prevent="handleResend" class="resend-link">重新发送验证码</a>
          <span> | </span>
          <router-link to="/login">返回登录</router-link>
        </p>
      </template>

      <!-- Step 3: 设置新密码 -->
      <template v-else-if="step === 3">
        <h2>🔒 设置新密码</h2>
        <p class="subtitle">请输入新密码</p>
        <form @submit.prevent="handleReset">
          <div class="form-group">
            <label>新密码</label>
            <input v-model="newPassword" type="password" placeholder="至少8位，含字母+数字+特殊字符" required />
          </div>
          <div class="form-group">
            <label>确认密码</label>
            <input v-model="confirmPassword" type="password" placeholder="再次输入新密码" required />
          </div>
          <p v-if="error" class="error">{{ error }}</p>
          <button type="submit" class="btn-glow" :disabled="loading">
            {{ loading ? '重置中...' : '重置密码' }}
          </button>
        </form>
      </template>

      <!-- Step 4: 成功 -->
      <template v-else-if="step === 4">
        <h2>✅ 重置成功</h2>
        <p class="subtitle">密码已重置，请使用新密码登录</p>
        <router-link to="/login" class="btn-glow" style="display:block;text-decoration:none;margin-top:16px">去登录</router-link>
      </template>
    </div>
  </div>
</template>

<script setup>
import { ref, onUnmounted } from 'vue'
import { sendPasswordResetCode, verifyPasswordResetCode, resetPassword } from '../api/auth'

const step = ref(1)
const email = ref('')
const code = ref('')
const resetToken = ref('')
const newPassword = ref('')
const confirmPassword = ref('')
const error = ref('')
const loading = ref(false)
const resendCountdown = ref(0)
let countdownTimer = null

function startCountdown(seconds = 60) {
  resendCountdown.value = seconds
  countdownTimer = setInterval(() => {
    resendCountdown.value--
    if (resendCountdown.value <= 0) clearInterval(countdownTimer)
  }, 1000)
}

async function handleSendCode() {
  error.value = ''; loading.value = true
  try {
    await sendPasswordResetCode(email.value)
    step.value = 2
    startCountdown(60)
  } catch (e) { error.value = e.message }
  finally { loading.value = false }
}

async function handleVerifyCode() {
  error.value = ''; loading.value = true
  try {
    const data = await verifyPasswordResetCode(email.value, code.value)
    resetToken.value = data.reset_token
    step.value = 3
  } catch (e) { error.value = e.message }
  finally { loading.value = false }
}

async function handleResend() {
  error.value = ''
  try {
    await sendPasswordResetCode(email.value)
    startCountdown(60)
  } catch (e) { error.value = e.message }
}

async function handleReset() {
  error.value = ''
  if (newPassword.value !== confirmPassword.value) {
    error.value = '两次密码输入不一致'
    return
  }
  loading.value = true
  try {
    await resetPassword(resetToken.value, newPassword.value, confirmPassword.value)
    step.value = 4
  } catch (e) { error.value = e.message }
  finally { loading.value = false }
}

onUnmounted(() => { if (countdownTimer) clearInterval(countdownTimer) })
</script>

<style scoped>
.auth-page { display: flex; align-items: center; justify-content: center; min-height: 100vh; background: linear-gradient(135deg, #f5f7fa 0%, #e4e8f0 100%); }
.auth-card { width: 420px; background: white; border-radius: 16px; padding: 36px; text-align: center; box-shadow: 0 4px 24px rgba(0,0,0,0.08); }
.auth-card h2 { font-size: 24px; color: #4f46e5; margin-bottom: 4px; }
.subtitle { color: #6b7280; margin-bottom: 24px; font-size: 14px; }
.subtitle strong { color: #374151; }
.form-group { margin-bottom: 16px; text-align: left; }
.form-group label { display: block; margin-bottom: 6px; font-size: 14px; font-weight: 500; color: #374151; }
.form-group input { width: 100%; padding: 11px 14px; border: 1px solid #e5e7eb; border-radius: 10px; font-size: 14px; outline: none; transition: all 0.3s; background: #f9fafb; }
.form-group input:focus { border-color: #4f46e5; box-shadow: 0 0 0 3px rgba(79,70,229,0.1); background: white; }
.code-input { font-size: 24px; letter-spacing: 8px; text-align: center; font-weight: 700; }
.error { color: #ef4444; font-size: 13px; margin-bottom: 12px; }
.btn-glow { width: 100%; padding: 12px; border: none; border-radius: 10px; font-size: 15px; font-weight: 600; color: white; background: linear-gradient(135deg, #4f46e5, #7c3aed, #6366f1); background-size: 200% 200%; animation: gradientShift 3s ease infinite; cursor: pointer; transition: all 0.3s; box-shadow: 0 4px 15px rgba(79,70,229,0.4); }
.btn-glow:hover { transform: translateY(-1px); box-shadow: 0 6px 25px rgba(79,70,229,0.5); }
.btn-glow:disabled { opacity: 0.6; cursor: not-allowed; transform: none; }
@keyframes gradientShift { 0% { background-position: 0% 50%; } 50% { background-position: 100% 50%; } 100% { background-position: 0% 50%; } }
.auth-link { margin-top: 18px; font-size: 14px; color: #6b7280; }
.auth-link a { color: #4f46e5; font-weight: 500; }
.resend-link { cursor: pointer; }
</style>
