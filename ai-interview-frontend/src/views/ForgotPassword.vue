<template>
  <div class="space-forgot">
    <!-- 主内容 -->
    <div class="forgot-page">
      <div class="auth-card">
        <div class="card-body">
          <div class="card-content">
            <!-- Step 1: 输入邮箱 -->
            <template v-if="step === 1">
              <div class="logo-icon">
                <img src="/site-logo.png" alt="智面 AI" />
              </div>
              <h2>忘记密码</h2>
              <p class="subtitle">输入您的注册邮箱，我们将发送验证码</p>
              <form @submit.prevent="handleSendCode">
                <div class="form-group">
                  <label>邮箱</label>
                  <div class="input-wrap">
                    <input v-model="email" type="email" placeholder="your@email.com" required @focus="onInputFocus" />
                  </div>
                </div>
                <div v-if="error" class="error-msg">{{ error }}</div>
        <button type="submit" class="btn-primary" :disabled="loading">
                  <span>{{ loading ? '发送中...' : '发送验证码' }}</span>
                </button>
              </form>
            </template>

            <!-- Step 2: 输入验证码 -->
            <template v-else-if="step === 2">
              <div class="logo-icon">
                <img src="/site-logo.png" alt="智面 AI" />
              </div>
              <h2>验证邮箱</h2>
              <p class="subtitle">验证码已发送至 <strong>{{ email }}</strong></p>
              <form @submit.prevent="handleVerifyCode">
                <div class="form-group">
                  <label>验证码</label>
                  <div class="input-wrap">
                    <input v-model="code" type="text" placeholder="请输入6位验证码" maxlength="6" required class="code-input" @focus="onInputFocus" />
                  </div>
                </div>
                <div v-if="error" class="error-msg">{{ error }}</div>
                <button type="submit" class="btn-primary" :disabled="loading">
                  <span>{{ loading ? '验证中...' : '验证' }}</span>
                </button>
              </form>
              <div class="auth-links">
                <span v-if="resendCountdown > 0" class="countdown">{{ resendCountdown }}s 后可重新发送</span>
                <a v-else href="#" @click.prevent="handleResend">重新发送验证码</a>
              </div>
            </template>

            <!-- Step 3: 设置新密码 -->
            <template v-else-if="step === 3">
              <div class="logo-icon">
                <img src="/site-logo.png" alt="智面 AI" />
              </div>
              <h2>设置新密码</h2>
              <p class="subtitle">请输入新密码</p>
              <form @submit.prevent="handleReset">
                <div class="form-group">
                  <label>新密码</label>
                  <div class="input-wrap">
                    <input v-model="newPassword" type="password" placeholder="至少8位，含字母+数字+特殊字符" autocomplete="new-password" required @focus="onInputFocus" />
                  </div>
                </div>
                <div class="form-group">
                  <label>确认密码</label>
                  <div class="input-wrap">
                    <input v-model="confirmPassword" type="password" placeholder="再次输入新密码" autocomplete="new-password" required @focus="onInputFocus" />
                  </div>
                </div>
                <div v-if="error" class="error-msg">{{ error }}</div>
                <button type="submit" class="btn-primary" :disabled="loading">
                  <span>{{ loading ? '重置中...' : '重置密码' }}</span>
                </button>
              </form>
            </template>

            <!-- Step 4: 成功 -->
            <template v-else-if="step === 4">
              <div class="logo-icon success-logo">&#x2705;</div>
              <h2>重置成功</h2>
              <p class="subtitle">密码已重置，请使用新密码登录</p>
              <router-link to="/login" class="btn-primary" style="display:block;text-align:center;text-decoration:none">
                <span>去登录</span>
              </router-link>
            </template>

            <div class="auth-links" v-if="step !== 4">
              <router-link to="/login">返回登录</router-link>
            </div>
          </div>
        </div>
      </div>
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

// Refs

// ===== 业务逻辑 =====
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

// ===== 互动特效 =====
let pCtx = null
let particles = []
let stars = []
let animId1 = null
let animId2 = null

function spawnParticles(x, y, count, color) {
  for (let i = 0; i < count; i++) {
    const angle = (Math.PI * 2 / count) * i + Math.random() * 0.5
    const speed = Math.random() * 4 + 2
    particles.push({ x, y, vx: Math.cos(angle) * speed, vy: Math.sin(angle) * speed, life: 1, decay: Math.random() * 0.02 + 0.015, r: Math.random() * 3 + 1, color })
  }
}

function flashAt(x, y) {
  const el = flashOverlay.value
  if (!el) return
  el.style.setProperty('--fx', (x / window.innerWidth * 100) + '%')
  el.style.setProperty('--fy', (y / window.innerHeight * 100) + '%')
  el.classList.add('active')
  setTimeout(() => el.classList.remove('active'), 150)
}

function addRipple(btn, e) {
  const rect = btn.getBoundingClientRect()
  const ripple = document.createElement('span')
  ripple.className = 'ripple'
  const size = Math.max(rect.width, rect.height)
  ripple.style.width = ripple.style.height = size + 'px'
  ripple.style.left = (e.clientX - rect.left - size / 2) + 'px'
  ripple.style.top = (e.clientY - rect.top - size / 2) + 'px'
  btn.appendChild(ripple)
  ripple.addEventListener('animationend', () => ripple.remove())
}

function onBtnClick(e) {
  const btn = e.currentTarget
  addRipple(btn, e)
  flashAt(e.clientX, e.clientY)
  spawnParticles(e.clientX, e.clientY, 20, 'rgba(128, 128, 128, 1)')
  spawnParticles(e.clientX, e.clientY, 12, 'rgba(128, 128, 128, 1)')
}

function handleLogoClick(e) {
  if (!logoIcon.value) return
  const rect = logoIcon.value.getBoundingClientRect()
  const cx = rect.left + rect.width / 2
  const cy = rect.top + rect.height / 2
  flashAt(cx, cy)
  spawnParticles(cx, cy, 30, 'rgba(128, 128, 128, 1)')
  spawnParticles(cx, cy, 20, 'rgba(128, 128, 128, 1)')
  spawnParticles(cx, cy, 10, 'rgba(128, 128, 128, 1)')
  logoIcon.value.style.transition = 'transform 0.6s cubic-bezier(0.34, 1.56, 0.64, 1)'
  logoIcon.value.style.transform = 'scale(1.2) rotate(360deg)'
  setTimeout(() => {
    if (logoIcon.value) {
      logoIcon.value.style.transition = 'transform 0.3s'
      logoIcon.value.style.transform = ''
    }
  }, 600)
}

function onInputFocus(e) {
  const rect = e.target.getBoundingClientRect()
  spawnParticles(rect.left + rect.width / 2, rect.top, 8, 'rgba(128, 128, 128, 1)')
}

// ===== 卡片 3D 倾斜 =====
function onCardMouseMove(e) {
  const card = authCard.value
  const glow = cardMouseGlow.value
  if (!card || !glow) return
  const rect = card.getBoundingClientRect()
  const cx = rect.left + rect.width / 2
  const cy = rect.top + rect.height / 2
  const dx = (e.clientX - cx) / rect.width
  const dy = (e.clientY - cy) / rect.height
  card.style.transform = `perspective(800px) rotateY(${dx * 8}deg) rotateX(${-dy * 8}deg)`
  glow.style.left = (e.clientX - rect.left) + 'px'
  glow.style.top = (e.clientY - rect.top) + 'px'
}

function onCardMouseLeave() {
  if (authCard.value) authCard.value.style.transform = 'perspective(800px) rotateY(0) rotateX(0)'
}

// ===== 星空 =====
function initStars() {
  const canvas = starCanvas.value
  if (!canvas) return
  const ctx = canvas.getContext('2d')
  canvas.width = window.innerWidth
  canvas.height = window.innerHeight
  stars = []
  for (let i = 0; i < 200; i++) {
    stars.push({ x: Math.random() * canvas.width, y: Math.random() * canvas.height, r: Math.random() * 1.5 + 0.3, speed: Math.random() * 0.005 + 0.002, phase: Math.random() * Math.PI * 2 })
  }
  function draw() {
    ctx.clearRect(0, 0, canvas.width, canvas.height)
    const t = Date.now() * 0.001
    stars.forEach(s => {
      const alpha = 0.3 + 0.7 * (0.5 + 0.5 * Math.sin(t * s.speed * 100 + s.phase))
      ctx.beginPath()
      ctx.arc(s.x, s.y, s.r, 0, Math.PI * 2)
      ctx.fillStyle = `rgba(128, 128, 128, ${alpha})`
      ctx.fill()
    })
    animId1 = requestAnimationFrame(draw)
  }
  draw()
}

function initParticles() {
  const canvas = particleCanvas.value
  if (!canvas) return
  pCtx = canvas.getContext('2d')
  canvas.width = window.innerWidth
  canvas.height = window.innerHeight
  function draw() {
    pCtx.clearRect(0, 0, canvas.width, canvas.height)
    particles = particles.filter(p => p.life > 0)
    particles.forEach(p => {
      p.x += p.vx; p.y += p.vy; p.vy += 0.05; p.life -= p.decay
      pCtx.beginPath()
      pCtx.arc(p.x, p.y, Math.max(0, p.r * p.life), 0, Math.PI * 2)
      pCtx.fillStyle = p.color.replace('1)', `${p.life})`)
      pCtx.fill()
    })
    animId2 = requestAnimationFrame(draw)
  }
  draw()
}

function onResize() {
  const c1 = starCanvas.value
  const c2 = particleCanvas.value
  if (c1) { c1.width = window.innerWidth; c1.height = window.innerHeight }
  if (c2) { c2.width = window.innerWidth; c2.height = window.innerHeight }
}

onUnmounted(() => {
  if (animId1) cancelAnimationFrame(animId1)
  if (animId2) cancelAnimationFrame(animId2)
  if (countdownTimer) clearInterval(countdownTimer)
})
</script>

<style scoped>
.space-forgot {
  position: relative;
  min-height: 100vh;
  background: var(--bg-base);
  overflow: hidden;
}

/* ===== 画布 ===== */
.star-canvas, .particle-canvas { position: fixed; inset: 0; z-index: 0; pointer-events: none; }
.particle-canvas { z-index: 9; }

/* ===== 极光 ===== */
.aurora {
  position: fixed; top: -30%; left: -10%; width: 120%; height: 60%;
  background: var(--accent-primary);
  filter: blur(80px); animation: auroraDrift 12s ease-in-out infinite alternate; z-index: 1; pointer-events: none;
}
@keyframes auroraDrift { 0% { transform: translateX(-3%) rotate(-2deg); } 100% { transform: translateX(3%) rotate(2deg); } }

/* ===== 轨道环 ===== */
.orbit-ring { position: fixed; border-radius: 50%; border: 1px solid rgba(128, 128, 128,0.08); z-index: 2; animation: orbitSpin linear infinite; pointer-events: none; }
.orbit-ring.r1 { width: 700px; height: 700px; top: 50%; left: 50%; margin-top: -350px; margin-left: -350px; animation-duration: 60s; }
.orbit-ring.r2 { width: 500px; height: 500px; top: 50%; left: 50%; margin-top: -250px; margin-left: -250px; border-color: rgba(128, 128, 128,0.06); animation-duration: 45s; animation-direction: reverse; }
.orbit-ring.r3 { width: 900px; height: 900px; top: 50%; left: 50%; margin-top: -450px; margin-left: -450px; border-color: rgba(128, 128, 128,0.04); animation-duration: 80s; }
.orbit-ring::after { content: ''; position: absolute; top: 0; left: 50%; width: 6px; height: 6px; margin-left: -3px; margin-top: -3px; background: #A3A3A3; border-radius: 50%; box-shadow: var(--shadow-sm); }
.orbit-ring.r2::after { background: #A3A3A3; box-shadow: var(--shadow-sm); width: 4px; height: 4px; margin-left: -2px; margin-top: -2px; }
.orbit-ring.r3::after { background: #A3A3A3; box-shadow: var(--shadow-sm); width: 5px; height: 5px; margin-left: -2.5px; margin-top: -2.5px; }
@keyframes orbitSpin { from { transform: rotate(0deg); } to { transform: rotate(360deg); } }

/* ===== 流星 ===== */
.meteor { position: fixed; width: 120px; height: 1px; background: var(--accent-primary); z-index: 3; animation: meteorFall linear infinite; opacity: 0; pointer-events: none; }
.m1 { top: 10%; left: 20%; animation-delay: 0s; animation-duration: 6s; }
.m2 { top: 30%; left: 60%; animation-delay: 3s; animation-duration: 5s; width: 80px; }
.m3 { top: 5%; left: 80%; animation-delay: 7s; animation-duration: 7s; }
@keyframes meteorFall { 0% { transform: translate(-100px, -100px) rotate(-35deg); opacity: 0; } 5% { opacity: 1; } 30% { opacity: 1; } 40% { transform: translate(calc(100vw + 100px), calc(100vh + 100px)) rotate(-35deg); opacity: 0; } 100% { opacity: 0; } }

/* ===== 闪光 ===== */
.flash-overlay { position: fixed; inset: 0; z-index: 100; pointer-events: none; opacity: 0; background: var(--accent-primary); transition: opacity 0.1s; }
.flash-overlay.active { opacity: 1; transition: opacity 0s; }

/* ===== 布局 ===== */
.forgot-page { position: relative; z-index: 10; display: flex; min-height: 100vh; align-items: center; justify-content: center; }

/* ===== 卡片 ===== */
.auth-card { width: 420px; padding: 0; border-radius: 8px; position: relative; transition: transform 0.1s ease-out; transform-style: preserve-3d; }

@keyframes glowRotate { from { --card-angle: 0deg; } to { --card-angle: 360deg; } }

.auth-card:hover .card-mouse-glow { opacity: 1; }
.card-body { background: var(--bg-card); border: 1px solid var(--border-default); border-radius: 8px; padding: 44px 40px; position: relative; overflow: hidden; }
.card-body::before { content: ''; position: absolute; top: 0; left: 0; right: 0; height: 1px; background: var(--accent-primary); }
.card-content { position: relative; z-index: 1; }

/* Logo */
.logo-icon { width: 52px; height: 52px; margin: 0 auto 16px; background: var(--bg-hover); border: 1px solid var(--border-default); border-radius: 8px; display: flex; align-items: center; justify-content: center; font-size: 24px; cursor: default; position: relative; transition: opacity 0.2s; }
.logo-icon img { width: 44px; height: 44px; border-radius: 50%; object-fit: cover; }
.logo-icon:hover { transform: scale(1.1) rotate(5deg); box-shadow: var(--shadow-sm); }
.logo-icon::after { content: ''; position: absolute; inset: -5px; border-radius: 8px; border: 1px solid rgba(128, 128, 128,0.15); animation: logoPulse 2.5s ease-in-out infinite; }
@keyframes logoPulse { 0%, 100% { transform: scale(1); opacity: 1; } 50% { transform: scale(1.15); opacity: 0; } }
.success-logo { cursor: default; }
.success-logo:hover { transform: none; box-shadow: var(--shadow-sm); }
.success-logo::after { animation: none; }

h2 { font-family: Inter, sans-serif; font-size: 24px; font-weight: 700; text-align: center; margin-bottom: 4px; background: none; color: var(--text-primary); }
.subtitle { text-align: center; font-size: 13px; color: var(--text-muted); margin-bottom: 28px; }
.subtitle strong { color: #A3A3A3; }

/* ===== 表单 ===== */
.form-group { margin-bottom: 18px; }
.form-group label { display: block; font-size: 12px; font-weight: 600; color: var(--text-secondary); margin-bottom: 8px; letter-spacing: 0.5px; transition: color 0.3s; }
.form-group:focus-within label { color: #A3A3A3; }
.input-wrap { position: relative; border-radius: 8px; overflow: hidden; }
.input-wrap::after { content: ''; position: absolute; bottom: 0; left: 50%; right: 50%; height: 2px; background: var(--accent-primary); border-radius: 2px; transition: left 0.4s, right 0.4s; z-index: 1; }
.input-wrap:focus-within::after { left: 0; right: 0; }
.form-group input { width: 100%; padding: 13px 16px; background: var(--bg-input); border: 1px solid var(--border-default); border-radius: 8px; font-size: 14px; color: var(--text-primary); outline: none; transition: all 0.3s; position: relative; z-index: 1; }
.form-group input::placeholder { color: var(--text-dim); }
.form-group input:focus { border-color: var(--border-focus); box-shadow: none; background: var(--bg-input-focus); }
.code-input { font-size: 24px; letter-spacing: 8px; text-align: center; font-weight: 700; }

/* 错误 */
.error-msg { background: rgba(128, 128, 128,0.08); border: 1px solid rgba(128, 128, 128,0.15); border-radius: 8px; padding: 10px 14px; color: #A3A3A3; font-size: 13px; margin-bottom: 14px; line-height: 1.5; }

/* ===== 按钮 ===== */
.btn-primary { width: 100%; padding: 14px; border: none; border-radius: 8px; font-size: 15px; font-weight: 600; font-family: Inter, sans-serif; cursor: pointer; background: var(--accent-primary); color: var(--bg-base); position: relative; overflow: hidden; transition: all 0.3s; box-shadow: var(--shadow-sm); margin-top: 4px; }
.btn-primary:hover:not(:disabled) { transform: none; box-shadow: none; opacity: 0.72; }
.btn-primary:active:not(:disabled) { transform: translateY(0) scale(0.98); }
.btn-primary:disabled { opacity: 0.5; cursor: not-allowed; }
.btn-primary::before { display: none; }
@keyframes btnRotate { from { transform: rotate(0deg); } to { transform: rotate(360deg); } }
.btn-primary span { position: relative; z-index: 1; }

/* 涟漪 */
.ripple { position: absolute; border-radius: 50%; background: rgba(255,255,255,0.3); transform: scale(0); animation: rippleAnim 0.6s ease-out; pointer-events: none; }
@keyframes rippleAnim { to { transform: scale(4); opacity: 0; } }

.auth-links { margin-top: 18px; text-align: center; font-size: 13px; }
.auth-links a { color: var(--text-muted); text-decoration: none; transition: all 0.2s; position: relative; }
.auth-links a:hover { color: #A3A3A3; }
.auth-links a::after { content: ''; position: absolute; bottom: -2px; left: 0; width: 0; height: 1px; background: #A3A3A3; transition: width 0.3s; }
.auth-links a:hover::after { width: 100%; }
.countdown { color: var(--text-muted); }

@media (max-width: 480px) {
  .card-body { padding: 32px 24px; }
  .auth-card { margin: 16px; }
}
</style>

<style>
@property --card-angle {
  syntax: '<angle>';
  initial-value: 0deg;
  inherits: false;
}

/* Light theme overrides for auth pages */
:root[data-theme="light"] .card-body {
  background: rgba(255, 255, 255, 0.92);
  border-color: rgba(128, 128, 128, 0.15);
}
:root[data-theme="light"] .card-body::before {
  background: var(--accent-primary);
}
:root[data-theme="light"] .card-outer-glow {
  background: var(--accent-primary);
}
:root[data-theme="light"] .card-mouse-glow {
  background: var(--accent-primary);
}
:root[data-theme="light"] h2 {
  background: none;
  color: var(--text-primary);

}
:root[data-theme="light"] .subtitle {
  color: var(--text-secondary);
}
:root[data-theme="light"] .form-group label {
  color: var(--text-secondary);
}
:root[data-theme="light"] .form-group:focus-within label {
  color: var(--text-primary);
}
:root[data-theme="light"] .form-group input {
  background: rgba(128, 128, 128, 0.03);
  border-color: rgba(128, 128, 128, 0.12);
  color: var(--text-primary);
}
:root[data-theme="light"] .form-group input::placeholder {
  color: var(--text-muted);
}
:root[data-theme="light"] .form-group input:focus {
  border-color: rgba(128, 128, 128, 0.35);
  background: rgba(128, 128, 128, 0.06);
}
:root[data-theme="light"] .auth-links a {
  color: var(--text-secondary);
}
:root[data-theme="light"] .auth-links a:hover {
  color: var(--text-primary);
}
:root[data-theme="light"] .divider {
  color: var(--text-muted);
}
:root[data-theme="light"] .orbit-ring { opacity: 0.3; }
:root[data-theme="light"] .meteor { opacity: 0.3; }
:root[data-theme="light"] .aurora { opacity: 0.4; }
:root[data-theme="light"] .space-forgot {
  background: var(--bg-base);
}
:root[data-theme="light"] .star-canvas { opacity: 0.15; }
:root[data-theme="light"] .particle-canvas { opacity: 0.25; }

/* Keep authentication focused on the form instead of decorative effects. */
.space-forgot { background: var(--bg-base); overflow: auto; }
.star-canvas, .particle-canvas, .aurora, .orbit-ring, .meteor, .flash-overlay,
.card-glow, .card-outer-glow, .card-mouse-glow { display: none; }

.auth-card { width: min(420px, calc(100vw - 32px)); }
.card-body { background: var(--bg-card); border-color: var(--border-default); }
.card-body::before { background: var(--border-default); }
.logo-icon { background: var(--bg-hover); border-color: var(--border-default); cursor: default; }
.logo-icon::after, .btn-primary::before, .ripple { display: none; }
.logo-icon:hover { transform: none; box-shadow: none; }
h2 { background: none; color: var(--text-primary); }
.form-group input { background: var(--bg-input); border-color: var(--border-default); color: var(--text-primary); }
.form-group input:focus { border-color: var(--border-focus); background: var(--bg-input-focus); }
.btn-primary { background: var(--accent-primary); color: var(--bg-base); }
.btn-primary:hover:not(:disabled) { transform: none; box-shadow: none; opacity: 0.72; }
</style>
