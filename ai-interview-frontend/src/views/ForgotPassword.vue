<template>
  <div class="space-forgot">
    <!-- 星空画布 -->
    <canvas ref="starCanvas" class="star-canvas"></canvas>
    <!-- 点击粒子画布 -->
    <canvas ref="particleCanvas" class="particle-canvas"></canvas>
    <!-- 极光 -->
    <div class="aurora"></div>
    <!-- 轨道环 -->
    <div class="orbit-ring r1"></div>
    <div class="orbit-ring r2"></div>
    <div class="orbit-ring r3"></div>
    <!-- 流星 -->
    <div class="meteor m1"></div>
    <div class="meteor m2"></div>
    <div class="meteor m3"></div>
    <!-- 点击闪光 -->
    <div ref="flashOverlay" class="flash-overlay"></div>

    <!-- 主内容 -->
    <div class="forgot-page">
      <div class="auth-card" ref="authCard">
        <div class="card-glow"></div>
        <div class="card-outer-glow"></div>
        <div class="card-mouse-glow" ref="cardMouseGlow"></div>
        <div class="card-body">
          <div class="card-content">
            <!-- Step 1: 输入邮箱 -->
            <template v-if="step === 1">
              <div class="logo-icon" ref="logoIcon" @click="handleLogoClick">&#x1F511;</div>
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
                <button type="submit" class="btn-primary" :disabled="loading" @mousedown="onBtnClick">
                  <span>{{ loading ? '发送中...' : '发送验证码' }}</span>
                </button>
              </form>
            </template>

            <!-- Step 2: 输入验证码 -->
            <template v-else-if="step === 2">
              <div class="logo-icon" ref="logoIcon" @click="handleLogoClick">&#x1F4E7;</div>
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
                <button type="submit" class="btn-primary" :disabled="loading" @mousedown="onBtnClick">
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
              <div class="logo-icon" ref="logoIcon" @click="handleLogoClick">&#x1F512;</div>
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
                <button type="submit" class="btn-primary" :disabled="loading" @mousedown="onBtnClick">
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
import { ref, onMounted, onUnmounted } from 'vue'
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
const starCanvas = ref(null)
const particleCanvas = ref(null)
const authCard = ref(null)
const cardMouseGlow = ref(null)
const flashOverlay = ref(null)
const logoIcon = ref(null)

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
  spawnParticles(e.clientX, e.clientY, 20, 'rgba(168, 85, 247, 1)')
  spawnParticles(e.clientX, e.clientY, 12, 'rgba(6, 182, 212, 1)')
}

function handleLogoClick(e) {
  if (!logoIcon.value) return
  const rect = logoIcon.value.getBoundingClientRect()
  const cx = rect.left + rect.width / 2
  const cy = rect.top + rect.height / 2
  flashAt(cx, cy)
  spawnParticles(cx, cy, 30, 'rgba(168, 85, 247, 1)')
  spawnParticles(cx, cy, 20, 'rgba(6, 182, 212, 1)')
  spawnParticles(cx, cy, 10, 'rgba(245, 158, 11, 1)')
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
  spawnParticles(rect.left + rect.width / 2, rect.top, 8, 'rgba(139, 92, 246, 1)')
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
      ctx.fillStyle = `rgba(200, 180, 255, ${alpha})`
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

onMounted(() => {
  initStars()
  initParticles()
  const card = authCard.value
  if (card) {
    card.addEventListener('mousemove', onCardMouseMove)
    card.addEventListener('mouseleave', onCardMouseLeave)
  }
  window.addEventListener('resize', onResize)
})

onUnmounted(() => {
  if (animId1) cancelAnimationFrame(animId1)
  if (animId2) cancelAnimationFrame(animId2)
  if (countdownTimer) clearInterval(countdownTimer)
  const card = authCard.value
  if (card) {
    card.removeEventListener('mousemove', onCardMouseMove)
    card.removeEventListener('mouseleave', onCardMouseLeave)
  }
  window.removeEventListener('resize', onResize)
})
</script>

<style scoped>
.space-forgot {
  position: relative;
  min-height: 100vh;
  background: #030014;
  overflow: hidden;
}

/* ===== 画布 ===== */
.star-canvas, .particle-canvas { position: fixed; inset: 0; z-index: 0; pointer-events: none; }
.particle-canvas { z-index: 9; }

/* ===== 极光 ===== */
.aurora {
  position: fixed; top: -30%; left: -10%; width: 120%; height: 60%;
  background: radial-gradient(ellipse at 30% 50%, rgba(139,92,246,0.15) 0%, transparent 50%),
              radial-gradient(ellipse at 70% 50%, rgba(6,182,212,0.1) 0%, transparent 50%);
  filter: blur(80px); animation: auroraDrift 12s ease-in-out infinite alternate; z-index: 1; pointer-events: none;
}
@keyframes auroraDrift { 0% { transform: translateX(-3%) rotate(-2deg); } 100% { transform: translateX(3%) rotate(2deg); } }

/* ===== 轨道环 ===== */
.orbit-ring { position: fixed; border-radius: 50%; border: 1px solid rgba(139,92,246,0.08); z-index: 2; animation: orbitSpin linear infinite; pointer-events: none; }
.orbit-ring.r1 { width: 700px; height: 700px; top: 50%; left: 50%; margin-top: -350px; margin-left: -350px; animation-duration: 60s; }
.orbit-ring.r2 { width: 500px; height: 500px; top: 50%; left: 50%; margin-top: -250px; margin-left: -250px; border-color: rgba(6,182,212,0.06); animation-duration: 45s; animation-direction: reverse; }
.orbit-ring.r3 { width: 900px; height: 900px; top: 50%; left: 50%; margin-top: -450px; margin-left: -450px; border-color: rgba(245,158,11,0.04); animation-duration: 80s; }
.orbit-ring::after { content: ''; position: absolute; top: 0; left: 50%; width: 6px; height: 6px; margin-left: -3px; margin-top: -3px; background: #a855f7; border-radius: 50%; box-shadow: 0 0 15px #a855f7, 0 0 30px rgba(168,85,247,0.3); }
.orbit-ring.r2::after { background: #06b6d4; box-shadow: 0 0 15px #06b6d4, 0 0 30px rgba(6,182,212,0.3); width: 4px; height: 4px; margin-left: -2px; margin-top: -2px; }
.orbit-ring.r3::after { background: #f59e0b; box-shadow: 0 0 15px #f59e0b; width: 5px; height: 5px; margin-left: -2.5px; margin-top: -2.5px; }
@keyframes orbitSpin { from { transform: rotate(0deg); } to { transform: rotate(360deg); } }

/* ===== 流星 ===== */
.meteor { position: fixed; width: 120px; height: 1px; background: linear-gradient(90deg, rgba(168,85,247,0.8), transparent); z-index: 3; animation: meteorFall linear infinite; opacity: 0; pointer-events: none; }
.m1 { top: 10%; left: 20%; animation-delay: 0s; animation-duration: 6s; }
.m2 { top: 30%; left: 60%; animation-delay: 3s; animation-duration: 5s; width: 80px; }
.m3 { top: 5%; left: 80%; animation-delay: 7s; animation-duration: 7s; }
@keyframes meteorFall { 0% { transform: translate(-100px, -100px) rotate(-35deg); opacity: 0; } 5% { opacity: 1; } 30% { opacity: 1; } 40% { transform: translate(calc(100vw + 100px), calc(100vh + 100px)) rotate(-35deg); opacity: 0; } 100% { opacity: 0; } }

/* ===== 闪光 ===== */
.flash-overlay { position: fixed; inset: 0; z-index: 100; pointer-events: none; opacity: 0; background: radial-gradient(circle at var(--fx, 50%) var(--fy, 50%), rgba(168,85,247,0.3), transparent 60%); transition: opacity 0.1s; }
.flash-overlay.active { opacity: 1; transition: opacity 0s; }

/* ===== 布局 ===== */
.forgot-page { position: relative; z-index: 10; display: flex; min-height: 100vh; align-items: center; justify-content: center; }

/* ===== 卡片 ===== */
.auth-card { width: 420px; padding: 0; border-radius: 24px; position: relative; transition: transform 0.1s ease-out; transform-style: preserve-3d; }
.card-glow { position: absolute; inset: -2px; border-radius: 26px; background: conic-gradient(from var(--card-angle, 0deg), transparent 0%, #a855f7 10%, #06b6d4 20%, transparent 30%, transparent 70%, #f59e0b 80%, #a855f7 90%, transparent 100%); opacity: 0.5; filter: blur(1px); animation: glowRotate 6s linear infinite; z-index: -1; }
@keyframes glowRotate { from { --card-angle: 0deg; } to { --card-angle: 360deg; } }
.card-outer-glow { position: absolute; inset: -20px; border-radius: 40px; background: radial-gradient(ellipse at center, rgba(139,92,246,0.08), transparent 70%); z-index: -2; pointer-events: none; }
.card-mouse-glow { position: absolute; width: 300px; height: 300px; border-radius: 50%; background: radial-gradient(circle, rgba(139,92,246,0.12), transparent 70%); pointer-events: none; transform: translate(-50%, -50%); opacity: 0; transition: opacity 0.3s; z-index: 0; }
.auth-card:hover .card-mouse-glow { opacity: 1; }
.card-body { background: rgba(8, 5, 25, 0.85); border: 1px solid rgba(139, 92, 246, 0.1); border-radius: 24px; padding: 44px 40px; backdrop-filter: blur(40px); position: relative; overflow: hidden; }
.card-body::before { content: ''; position: absolute; top: 0; left: 0; right: 0; height: 1px; background: linear-gradient(90deg, transparent 10%, rgba(168,85,247,0.4) 30%, rgba(6,182,212,0.3) 50%, rgba(168,85,247,0.4) 70%, transparent 90%); }
.card-content { position: relative; z-index: 1; }

/* Logo */
.logo-icon { width: 52px; height: 52px; margin: 0 auto 16px; background: linear-gradient(135deg, rgba(139,92,246,0.2), rgba(6,182,212,0.2)); border: 1px solid rgba(139,92,246,0.25); border-radius: 16px; display: flex; align-items: center; justify-content: center; font-size: 24px; cursor: pointer; position: relative; transition: transform 0.3s, box-shadow 0.3s; }
.logo-icon:hover { transform: scale(1.1) rotate(5deg); box-shadow: 0 0 30px rgba(139,92,246,0.3); }
.logo-icon::after { content: ''; position: absolute; inset: -5px; border-radius: 20px; border: 1px solid rgba(139,92,246,0.15); animation: logoPulse 2.5s ease-in-out infinite; }
@keyframes logoPulse { 0%, 100% { transform: scale(1); opacity: 1; } 50% { transform: scale(1.15); opacity: 0; } }
.success-logo { cursor: default; }
.success-logo:hover { transform: none; box-shadow: none; }
.success-logo::after { animation: none; }

h2 { font-family: 'Space Grotesk', sans-serif; font-size: 24px; font-weight: 700; text-align: center; margin-bottom: 4px; background: linear-gradient(135deg, #fff, #c4b5fd); -webkit-background-clip: text; -webkit-text-fill-color: transparent; }
.subtitle { text-align: center; font-size: 13px; color: #6b7280; margin-bottom: 28px; }
.subtitle strong { color: #c4b5fd; }

/* ===== 表单 ===== */
.form-group { margin-bottom: 18px; }
.form-group label { display: block; font-size: 12px; font-weight: 600; color: #9ca3af; margin-bottom: 8px; letter-spacing: 0.5px; transition: color 0.3s; }
.form-group:focus-within label { color: #a855f7; }
.input-wrap { position: relative; border-radius: 12px; overflow: hidden; }
.input-wrap::after { content: ''; position: absolute; bottom: 0; left: 50%; right: 50%; height: 2px; background: linear-gradient(90deg, #a855f7, #06b6d4); border-radius: 2px; transition: left 0.4s, right 0.4s; z-index: 1; }
.input-wrap:focus-within::after { left: 0; right: 0; }
.form-group input { width: 100%; padding: 13px 16px; background: rgba(139,92,246,0.04); border: 1px solid rgba(139,92,246,0.12); border-radius: 12px; font-size: 14px; color: #e2e8f0; outline: none; transition: all 0.3s; position: relative; z-index: 1; }
.form-group input::placeholder { color: #4a4a6a; }
.form-group input:focus { border-color: rgba(139,92,246,0.35); box-shadow: 0 0 20px rgba(139,92,246,0.1), 0 0 40px rgba(139,92,246,0.04); background: rgba(139,92,246,0.07); }
.code-input { font-size: 24px; letter-spacing: 8px; text-align: center; font-weight: 700; }

/* 错误 */
.error-msg { background: rgba(248,113,113,0.08); border: 1px solid rgba(248,113,113,0.15); border-radius: 10px; padding: 10px 14px; color: #f87171; font-size: 13px; margin-bottom: 14px; line-height: 1.5; }

/* ===== 按钮 ===== */
.btn-primary { width: 100%; padding: 14px; border: none; border-radius: 12px; font-size: 15px; font-weight: 600; font-family: 'Space Grotesk', sans-serif; cursor: pointer; background: linear-gradient(135deg, #7c3aed, #6366f1); color: white; position: relative; overflow: hidden; transition: all 0.3s; box-shadow: 0 4px 20px rgba(124,58,237,0.3); margin-top: 4px; }
.btn-primary:hover:not(:disabled) { transform: translateY(-2px); box-shadow: 0 8px 32px rgba(124,58,237,0.45); }
.btn-primary:active:not(:disabled) { transform: translateY(0) scale(0.98); }
.btn-primary:disabled { opacity: 0.5; cursor: not-allowed; }
.btn-primary::before { content: ''; position: absolute; top: -50%; left: -50%; width: 200%; height: 200%; background: conic-gradient(transparent, rgba(255,255,255,0.12), transparent 30%); animation: btnRotate 4s linear infinite; }
@keyframes btnRotate { from { transform: rotate(0deg); } to { transform: rotate(360deg); } }
.btn-primary span { position: relative; z-index: 1; }

/* 涟漪 */
.ripple { position: absolute; border-radius: 50%; background: rgba(255,255,255,0.3); transform: scale(0); animation: rippleAnim 0.6s ease-out; pointer-events: none; }
@keyframes rippleAnim { to { transform: scale(4); opacity: 0; } }

.auth-links { margin-top: 18px; text-align: center; font-size: 13px; }
.auth-links a { color: #6b7280; text-decoration: none; transition: all 0.2s; position: relative; }
.auth-links a:hover { color: #a855f7; }
.auth-links a::after { content: ''; position: absolute; bottom: -2px; left: 0; width: 0; height: 1px; background: #a855f7; transition: width 0.3s; }
.auth-links a:hover::after { width: 100%; }
.countdown { color: #4a4a6a; }

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
  border-color: rgba(139, 92, 246, 0.15);
}
:root[data-theme="light"] .card-body::before {
  background: linear-gradient(90deg, transparent 10%, rgba(139,92,246,0.25) 30%, rgba(99,102,241,0.2) 50%, rgba(139,92,246,0.25) 70%, transparent 90%);
}
:root[data-theme="light"] .card-outer-glow {
  background: radial-gradient(ellipse at center, rgba(139,92,246,0.05), transparent 70%);
}
:root[data-theme="light"] .card-mouse-glow {
  background: radial-gradient(circle, rgba(139,92,246,0.06), transparent 70%);
}
:root[data-theme="light"] h2 {
  background: linear-gradient(135deg, #1E293B, #7C3AED);
  -webkit-background-clip: text;
  -webkit-text-fill-color: transparent;
}
:root[data-theme="light"] .subtitle {
  color: #64748B;
}
:root[data-theme="light"] .form-group label {
  color: #475569;
}
:root[data-theme="light"] .form-group:focus-within label {
  color: #7C3AED;
}
:root[data-theme="light"] .form-group input {
  background: rgba(139, 92, 246, 0.03);
  border-color: rgba(139, 92, 246, 0.12);
  color: #1E293B;
}
:root[data-theme="light"] .form-group input::placeholder {
  color: #94A3B8;
}
:root[data-theme="light"] .form-group input:focus {
  border-color: rgba(139, 92, 246, 0.35);
  background: rgba(139, 92, 246, 0.06);
}
:root[data-theme="light"] .auth-links a {
  color: #64748B;
}
:root[data-theme="light"] .auth-links a:hover {
  color: #7C3AED;
}
:root[data-theme="light"] .divider {
  color: #94A3B8;
}
:root[data-theme="light"] .orbit-ring { opacity: 0.3; }
:root[data-theme="light"] .meteor { opacity: 0.3; }
:root[data-theme="light"] .aurora { opacity: 0.4; }
</style>
