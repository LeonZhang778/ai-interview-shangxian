<template>
  <div class="auth-page">
    <div class="auth-card">
      <!-- Step 1: 填写信息 -->
      <template v-if="step === 1">
        <h2>📋 等候名单</h2>
        <p class="subtitle">留下您的信息，我们会在开放后第一时间通知您</p>
        <form @submit.prevent="handleSubmit">
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
            <input v-model="form.email" type="email" placeholder="请输入邮箱" required />
          </div>
          <div class="form-group">
            <label>学校 <span class="optional">(选填)</span></label>
            <input v-model="form.university" placeholder="请输入学校名称" />
          </div>
          <p v-if="error" class="error">{{ error }}</p>
          <button type="submit" class="btn-glow" :disabled="loading">
            {{ loading ? '提交中...' : '提交申请' }}
          </button>
        </form>
        <p class="auth-link"><router-link to="/login">返回登录</router-link></p>
      </template>

      <!-- Step 2: 等待验证 -->
      <template v-else-if="step === 2">
        <h2>📧 查收邮件</h2>
        <p class="subtitle">验证邮件已发送至 <strong>{{ form.email }}</strong></p>
        <p class="hint">请点击邮件中的链接完成验证，验证后您将加入等候名单。</p>
        <p v-if="error" class="error">{{ error }}</p>
        <p v-if="success" class="success">{{ success }}</p>
        <div class="actions">
          <button class="btn-glow" :disabled="resendCooldown > 0" @click="handleResend">
            {{ resendCooldown > 0 ? `${resendCooldown}s 后可重新发送` : '重新发送验证邮件' }}
          </button>
        </div>
        <p class="auth-link"><router-link to="/login">返回登录</router-link></p>
      </template>

      <!-- Step 3: 验证成功 -->
      <template v-else-if="step === 3">
        <h2>✅ 验证成功</h2>
        <p class="subtitle">您已成功加入等候名单！</p>
        <p class="hint">我们会在开放后通过邮件通知您，请留意您的邮箱。</p>
        <router-link to="/login" class="btn-glow" style="display:block;text-decoration:none;margin-top:16px">返回登录</router-link>
      </template>
    </div>
  </div>
</template>

<script setup>
import { ref, reactive, onMounted, onUnmounted } from 'vue'
import { useRoute } from 'vue-router'
import { submitWaitingList, verifyWaitingListEmail, resendWaitingListVerification } from '../api/waitingList'

const route = useRoute()
const step = ref(1)
const form = reactive({ first_name: '', last_name: '', email: '', university: '' })
const error = ref('')
const success = ref('')
const loading = ref(false)
const resendCooldown = ref(0)
let cooldownTimer = null

function startCooldown(seconds = 60) {
  resendCooldown.value = seconds
  cooldownTimer = setInterval(() => {
    resendCooldown.value--
    if (resendCooldown.value <= 0) clearInterval(cooldownTimer)
  }, 1000)
}

async function handleSubmit() {
  error.value = ''; loading.value = true
  try {
    await submitWaitingList({
      first_name: form.first_name,
      last_name: form.last_name,
      email: form.email,
      university: form.university || null
    })
    step.value = 2
    startCooldown(60)
  } catch (e) { error.value = e.message }
  finally { loading.value = false }
}

async function handleResend() {
  error.value = ''; success.value = ''
  try {
    await resendWaitingListVerification(form.email)
    success.value = '验证邮件已重新发送'
    startCooldown(60)
  } catch (e) { error.value = e.message }
}

onMounted(async () => {
  const token = route.query.token
  if (token) {
    try {
      await verifyWaitingListEmail(token)
      step.value = 3
    } catch (e) {
      error.value = e.message
      step.value = 1
    }
  }
})

onUnmounted(() => { if (cooldownTimer) clearInterval(cooldownTimer) })
</script>

<style scoped>
.auth-page { display: flex; align-items: center; justify-content: center; min-height: 100vh; background: linear-gradient(135deg, #f5f7fa 0%, #e4e8f0 100%); }
.auth-card { width: 440px; background: white; border-radius: 16px; padding: 36px; text-align: center; box-shadow: 0 4px 24px rgba(0,0,0,0.08); }
.auth-card h2 { font-size: 24px; color: #4f46e5; margin-bottom: 4px; }
.subtitle { color: #6b7280; margin-bottom: 24px; font-size: 14px; }
.subtitle strong { color: #374151; }
.hint { color: #6b7280; font-size: 13px; margin-bottom: 16px; line-height: 1.6; }
.optional { color: #9ca3af; font-weight: 400; }
.form-row { display: flex; gap: 12px; }
.form-group { margin-bottom: 16px; text-align: left; flex: 1; }
.form-group label { display: block; margin-bottom: 6px; font-size: 14px; font-weight: 500; color: #374151; }
.form-group input { width: 100%; padding: 11px 14px; border: 1px solid #e5e7eb; border-radius: 10px; font-size: 14px; outline: none; transition: all 0.3s; background: #f9fafb; }
.form-group input:focus { border-color: #4f46e5; box-shadow: 0 0 0 3px rgba(79,70,229,0.1); background: white; }
.error { color: #ef4444; font-size: 13px; margin-bottom: 12px; }
.success { color: #10b981; font-size: 13px; margin-bottom: 12px; }
.btn-glow { width: 100%; padding: 12px; border: none; border-radius: 10px; font-size: 15px; font-weight: 600; color: white; background: linear-gradient(135deg, #4f46e5, #7c3aed, #6366f1); background-size: 200% 200%; animation: gradientShift 3s ease infinite; cursor: pointer; transition: all 0.3s; box-shadow: 0 4px 15px rgba(79,70,229,0.4); }
.btn-glow:hover { transform: translateY(-1px); box-shadow: 0 6px 25px rgba(79,70,229,0.5); }
.btn-glow:disabled { opacity: 0.6; cursor: not-allowed; transform: none; }
@keyframes gradientShift { 0% { background-position: 0% 50%; } 50% { background-position: 100% 50%; } 100% { background-position: 0% 50%; } }
.auth-link { margin-top: 18px; font-size: 14px; color: #6b7280; }
.auth-link a { color: #4f46e5; font-weight: 500; }
.actions { margin: 16px 0; }
</style>
