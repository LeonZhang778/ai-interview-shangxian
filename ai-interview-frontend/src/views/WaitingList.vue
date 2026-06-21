<template>
  <StarryBackground />
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
        <p class="subtitle">验证邮件已发送至 <strong style="color:var(--accent-light)">{{ form.email }}</strong></p>
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
import StarryBackground from '../components/StarryBackground.vue'

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
.auth-page { display: flex; align-items: center; justify-content: center; min-height: 100vh; }
.auth-card { width: 440px; background: rgba(8,5,25,0.9); border: 1px solid var(--border-default); border-radius: 16px; padding: 36px; text-align: center; backdrop-filter: blur(40px); }
.auth-card h2 { font-family: 'Space Grotesk', sans-serif; font-size: 24px; background:var(--title-gradient); -webkit-background-clip: text; -webkit-text-fill-color: transparent; margin-bottom: 4px; }
.subtitle { color: var(--text-muted); margin-bottom: 24px; font-size: 14px; }
.subtitle strong { color: var(--accent-light); }
.hint { color: var(--text-muted); font-size: 13px; margin-bottom: 16px; line-height: 1.6; }
.optional { color: var(--text-dim); font-weight: 400; }
.form-row { display: flex; gap: 12px; }
.form-group { margin-bottom: 16px; text-align: left; flex: 1; }
.form-group label { display: block; margin-bottom: 6px; font-size: 14px; font-weight: 500; color: var(--text-secondary); }
.form-group input { width: 100%; padding: 11px 14px; border:1px solid var(--border-default); border-radius: 10px; font-size: 14px; outline: none; transition: all 0.3s; background: var(--bg-card); color: var(--text-primary); }
.form-group input::placeholder { color: var(--text-dim); }
.form-group input:focus { border-color: rgba(139,92,246,0.35); box-shadow: 0 0 16px rgba(139,92,246,0.08); background: rgba(139,92,246,0.07); }
.error { color: var(--red); font-size: 13px; margin-bottom: 12px; }
.success { color: var(--green); font-size: 13px; margin-bottom: 12px; }
.btn-glow { width: 100%; padding: 14px; border: none; border-radius: 12px; font-size: 15px; font-weight: 600; font-family: 'Space Grotesk', sans-serif; color: white; background: linear-gradient(135deg, #7c3aed, #6366f1); cursor: pointer; transition: all 0.3s; box-shadow: 0 4px 20px rgba(124,58,237,0.3); }
.btn-glow:hover:not(:disabled) { transform: translateY(-2px); box-shadow: 0 8px 32px rgba(124,58,237,0.45); }
.btn-glow:disabled { opacity: 0.5; cursor: not-allowed; transform: none; }
.auth-link { margin-top: 18px; font-size: 14px; color: var(--text-muted); }
.auth-link a { color: var(--accent-primary); font-weight: 500; }
.actions { margin: 16px 0; }
</style>
