<template>
  <div class="space-login">
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
    <div class="login-page">
      <div class="auth-card" ref="authCard">
        <div class="card-glow"></div>
        <div class="card-outer-glow"></div>
        <div class="card-mouse-glow" ref="cardMouseGlow"></div>
        <div class="card-body">
          <div class="card-content">
            <div class="logo-icon" ref="logoIcon" @click="handleLogoClick">&#x1F3AF;</div>
            <h2>欢迎回来</h2>
            <p class="subtitle">登录智面 AI 账号</p>

            <form @submit.prevent="handleLogin" id="loginForm">
              <div class="form-group">
                <label>邮箱</label>
                <div class="input-wrap">
                  <input v-model="email" type="email" placeholder="your@email.com" @focus="onInputFocus" />
                </div>
              </div>
              <div class="form-group">
                <label>密码</label>
                <div class="input-wrap">
                  <input v-model="password" type="password" placeholder="输入密码" autocomplete="current-password" @focus="onInputFocus" />
                </div>
              </div>
              <div v-if="error" class="error-msg">
                {{ error }}，若确认无误请反馈至 <a href="mailto:1448203623@qq.com">1448203623@qq.com</a>
              </div>
              <button type="submit" class="btn-primary" ref="loginBtn" :disabled="loading" @click="onBtnClick">
                <span>{{ loading ? '登录中...' : '登录' }}</span>
              </button>
            </form>

            <div class="auth-links">
              <router-link to="/forgot-password">忘记密码？</router-link>
              <router-link v-if="registerEnabled" to="/register">还没有账号？<strong>立即注册</strong></router-link>
              <router-link v-else to="/waiting-list">想要体验？<strong>加入候选名单</strong></router-link>
            </div>

            <div class="divider">或</div>

            <button class="btn-guest" ref="guestBtn" @click="handleGuest" :disabled="guestLoading" @mousedown="onBtnClick">
              {{ guestLoading ? '进入中...' : '先体验一下？游客模式进入' }}
            </button>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted, onUnmounted } from 'vue'
import { useRouter } from 'vue-router'
import { useAuthStore } from '../stores/auth'
import { login, guestLogin } from '../api/auth'
import { getProfile } from '../api/user'
import { getSiteInfo } from '../api/config'

const router = useRouter()
const authStore = useAuthStore()
const email = ref('')
const password = ref('')
const error = ref('')
const loading = ref(false)
const guestLoading = ref(false)
const registerEnabled = ref(true)

// Refs
const starCanvas = ref(null)
const particleCanvas = ref(null)
const authCard = ref(null)
const cardMouseGlow = ref(null)
const flashOverlay = ref(null)
const logoIcon = ref(null)
const loginBtn = ref(null)
const guestBtn = ref(null)

// ===== 登录逻辑 =====
async function handleLogin() {
  error.value = ''
  loading.value = true
  try {
    const data = await login(email.value, password.value)
    authStore.setAuth(data)
    try {
      const profile = await getProfile()
      authStore.setUserInfo(profile)
    } catch (_) {}
    router.push('/dashboard')
  } catch (e) {
    error.value = e.message
  } finally {
    loading.value = false
  }
}

async function handleGuest() {
  guestLoading.value = true
  try {
    // 复用已有的游客 token，避免重复创建匿名用户
    if (authStore.isLoggedIn && authStore.isGuest) {
      router.push('/dashboard')
      return
    }
    const data = await guestLogin()
    authStore.setAuth(data)
    router.push('/dashboard')
  } catch (e) {
    error.value = e.message
  } finally {
    guestLoading.value = false
  }
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
    particles.push({
      x, y,
      vx: Math.cos(angle) * speed,
      vy: Math.sin(angle) * speed,
      life: 1,
      decay: Math.random() * 0.02 + 0.015,
      r: Math.random() * 3 + 1,
      color
    })
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
    stars.push({
      x: Math.random() * canvas.width,
      y: Math.random() * canvas.height,
      r: Math.random() * 1.5 + 0.3,
      speed: Math.random() * 0.005 + 0.002,
      phase: Math.random() * Math.PI * 2
    })
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

// ===== 粒子渲染 =====
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
      p.x += p.vx
      p.y += p.vy
      p.vy += 0.05
      p.life -= p.decay
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

onMounted(async () => {
  initStars()
  initParticles()
  try {
    const info = await getSiteInfo()
    registerEnabled.value = info.register_enabled !== false
  } catch (_) {}
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
  const card = authCard.value
  if (card) {
    card.removeEventListener('mousemove', onCardMouseMove)
    card.removeEventListener('mouseleave', onCardMouseLeave)
  }
  window.removeEventListener('resize', onResize)
})
</script>

<style scoped>
.space-login {
  position: relative;
  min-height: 100vh;
  background: #030014;
  overflow: hidden;
}

/* ===== 画布 ===== */
.star-canvas, .particle-canvas {
  position: fixed;
  inset: 0;
  z-index: 0;
  pointer-events: none;
}
.particle-canvas { z-index: 9; }

/* ===== 极光 ===== */
.aurora {
  position: fixed;
  top: -30%; left: -10%;
  width: 120%; height: 60%;
  background: radial-gradient(ellipse at 30% 50%, rgba(139,92,246,0.15) 0%, transparent 50%),
              radial-gradient(ellipse at 70% 50%, rgba(6,182,212,0.1) 0%, transparent 50%);
  filter: blur(80px);
  animation: auroraDrift 12s ease-in-out infinite alternate;
  z-index: 1;
  pointer-events: none;
}
@keyframes auroraDrift {
  0% { transform: translateX(-3%) rotate(-2deg); }
  100% { transform: translateX(3%) rotate(2deg); }
}

/* ===== 轨道环 ===== */
.orbit-ring {
  position: fixed;
  border-radius: 50%;
  border: 1px solid rgba(139,92,246,0.08);
  z-index: 2;
  animation: orbitSpin linear infinite;
  pointer-events: none;
}
.orbit-ring.r1 {
  width: 700px; height: 700px;
  top: 50%; left: 50%;
  margin-top: -350px; margin-left: -350px;
  animation-duration: 60s;
}
.orbit-ring.r2 {
  width: 500px; height: 500px;
  top: 50%; left: 50%;
  margin-top: -250px; margin-left: -250px;
  border-color: rgba(6,182,212,0.06);
  animation-duration: 45s;
  animation-direction: reverse;
}
.orbit-ring.r3 {
  width: 900px; height: 900px;
  top: 50%; left: 50%;
  margin-top: -450px; margin-left: -450px;
  border-color: rgba(245,158,11,0.04);
  animation-duration: 80s;
}
.orbit-ring::after {
  content: '';
  position: absolute;
  top: 0; left: 50%;
  width: 6px; height: 6px;
  margin-left: -3px; margin-top: -3px;
  background: #a855f7;
  border-radius: 50%;
  box-shadow: 0 0 15px #a855f7, 0 0 30px rgba(168,85,247,0.3);
}
.orbit-ring.r2::after {
  background: #06b6d4;
  box-shadow: 0 0 15px #06b6d4, 0 0 30px rgba(6,182,212,0.3);
  width: 4px; height: 4px; margin-left: -2px; margin-top: -2px;
}
.orbit-ring.r3::after {
  background: #f59e0b;
  box-shadow: 0 0 15px #f59e0b;
  width: 5px; height: 5px; margin-left: -2.5px; margin-top: -2.5px;
}
@keyframes orbitSpin { from { transform: rotate(0deg); } to { transform: rotate(360deg); } }

/* ===== 流星 ===== */
.meteor {
  position: fixed;
  width: 120px; height: 1px;
  background: linear-gradient(90deg, rgba(168,85,247,0.8), transparent);
  z-index: 3;
  animation: meteorFall linear infinite;
  opacity: 0;
  pointer-events: none;
}
.m1 { top: 10%; left: 20%; animation-delay: 0s; animation-duration: 6s; }
.m2 { top: 30%; left: 60%; animation-delay: 3s; animation-duration: 5s; width: 80px; }
.m3 { top: 5%; left: 80%; animation-delay: 7s; animation-duration: 7s; }
@keyframes meteorFall {
  0% { transform: translate(-100px, -100px) rotate(-35deg); opacity: 0; }
  5% { opacity: 1; }
  30% { opacity: 1; }
  40% { transform: translate(calc(100vw + 100px), calc(100vh + 100px)) rotate(-35deg); opacity: 0; }
  100% { opacity: 0; }
}

/* ===== 闪光 ===== */
.flash-overlay {
  position: fixed;
  inset: 0;
  z-index: 100;
  pointer-events: none;
  opacity: 0;
  background: radial-gradient(circle at var(--fx, 50%) var(--fy, 50%), rgba(168,85,247,0.3), transparent 60%);
  transition: opacity 0.1s;
}
.flash-overlay.active {
  opacity: 1;
  transition: opacity 0s;
}

/* ===== 布局 ===== */
.login-page {
  position: relative;
  z-index: 10;
  display: flex;
  min-height: 100vh;
  align-items: center;
  justify-content: center;
}

/* ===== 卡片 ===== */
.auth-card {
  width: 420px;
  padding: 0;
  border-radius: 24px;
  position: relative;
  transition: transform 0.1s ease-out;
  transform-style: preserve-3d;
}
.card-glow {
  position: absolute;
  inset: -2px;
  border-radius: 26px;
  background: conic-gradient(
    from var(--card-angle, 0deg),
    transparent 0%, #a855f7 10%, #06b6d4 20%, transparent 30%,
    transparent 70%, #f59e0b 80%, #a855f7 90%, transparent 100%
  );
  opacity: 0.5;
  filter: blur(1px);
  animation: glowRotate 6s linear infinite;
  z-index: -1;
}
@keyframes glowRotate {
  from { --card-angle: 0deg; }
  to { --card-angle: 360deg; }
}
@property --card-angle {
  syntax: '<angle>';
  initial-value: 0deg;
  inherits: false;
}
.card-outer-glow {
  position: absolute;
  inset: -20px;
  border-radius: 40px;
  background: radial-gradient(ellipse at center, rgba(139,92,246,0.08), transparent 70%);
  z-index: -2;
  transition: opacity 0.4s;
  pointer-events: none;
}
.card-mouse-glow {
  position: absolute;
  width: 300px; height: 300px;
  border-radius: 50%;
  background: radial-gradient(circle, rgba(139,92,246,0.12), transparent 70%);
  pointer-events: none;
  transform: translate(-50%, -50%);
  opacity: 0;
  transition: opacity 0.3s;
  z-index: 0;
}
.auth-card:hover .card-mouse-glow { opacity: 1; }
.card-body {
  background: rgba(8, 5, 25, 0.85);
  border: 1px solid rgba(139, 92, 246, 0.1);
  border-radius: 24px;
  padding: 44px 40px;
  backdrop-filter: blur(40px);
  position: relative;
  overflow: hidden;
}
.card-body::before {
  content: '';
  position: absolute;
  top: 0; left: 0; right: 0;
  height: 1px;
  background: linear-gradient(90deg, transparent 10%, rgba(168,85,247,0.4) 30%, rgba(6,182,212,0.3) 50%, rgba(168,85,247,0.4) 70%, transparent 90%);
}
.card-content {
  position: relative;
  z-index: 1;
}

/* Logo */
.logo-icon {
  width: 52px; height: 52px;
  margin: 0 auto 16px;
  background: linear-gradient(135deg, rgba(139,92,246,0.2), rgba(6,182,212,0.2));
  border: 1px solid rgba(139,92,246,0.25);
  border-radius: 16px;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 24px;
  cursor: pointer;
  position: relative;
  transition: transform 0.3s, box-shadow 0.3s;
}
.logo-icon:hover {
  transform: scale(1.1) rotate(5deg);
  box-shadow: 0 0 30px rgba(139,92,246,0.3);
}
.logo-icon::after {
  content: '';
  position: absolute;
  inset: -5px;
  border-radius: 20px;
  border: 1px solid rgba(139,92,246,0.15);
  animation: logoPulse 2.5s ease-in-out infinite;
}
@keyframes logoPulse {
  0%, 100% { transform: scale(1); opacity: 1; }
  50% { transform: scale(1.15); opacity: 0; }
}

h2 {
  font-family: 'Space Grotesk', sans-serif;
  font-size: 24px;
  font-weight: 700;
  text-align: center;
  margin-bottom: 4px;
  background: linear-gradient(135deg, #fff, #c4b5fd);
  -webkit-background-clip: text;
  -webkit-text-fill-color: transparent;
}
.subtitle {
  text-align: center;
  font-size: 13px;
  color: #6b7280;
  margin-bottom: 32px;
}

/* ===== 表单 ===== */
.form-group { margin-bottom: 18px; }
.form-group label {
  display: block;
  font-size: 12px;
  font-weight: 600;
  color: #9ca3af;
  margin-bottom: 8px;
  letter-spacing: 0.5px;
  transition: color 0.3s;
}
.form-group:focus-within label { color: #a855f7; }
.input-wrap {
  position: relative;
  border-radius: 12px;
  overflow: hidden;
}
.input-wrap::after {
  content: '';
  position: absolute;
  bottom: 0; left: 50%; right: 50%;
  height: 2px;
  background: linear-gradient(90deg, #a855f7, #06b6d4);
  border-radius: 2px;
  transition: left 0.4s, right 0.4s;
  z-index: 1;
}
.input-wrap:focus-within::after {
  left: 0;
  right: 0;
}
.form-group input {
  width: 100%;
  padding: 13px 16px;
  background: rgba(139,92,246,0.04);
  border: 1px solid rgba(139,92,246,0.12);
  border-radius: 12px;
  font-size: 14px;
  color: #e2e8f0;
  outline: none;
  transition: all 0.3s;
  position: relative;
  z-index: 1;
}
.form-group input::placeholder { color: #4a4a6a; }
.form-group input:focus {
  border-color: rgba(139,92,246,0.35);
  box-shadow: 0 0 20px rgba(139,92,246,0.1), 0 0 40px rgba(139,92,246,0.04);
  background: rgba(139,92,246,0.07);
}

/* 错误 */
.error-msg {
  background: rgba(248,113,113,0.08);
  border: 1px solid rgba(248,113,113,0.15);
  border-radius: 10px;
  padding: 10px 14px;
  color: #f87171;
  font-size: 13px;
  margin-bottom: 14px;
  line-height: 1.5;
}
.error-msg a { color: #a855f7; }

/* ===== 按钮 ===== */
.btn-primary {
  width: 100%;
  padding: 14px;
  border: none;
  border-radius: 12px;
  font-size: 15px;
  font-weight: 600;
  font-family: 'Space Grotesk', sans-serif;
  cursor: pointer;
  background: linear-gradient(135deg, #7c3aed, #6366f1);
  color: white;
  position: relative;
  overflow: hidden;
  transition: all 0.3s;
  box-shadow: 0 4px 20px rgba(124,58,237,0.3);
  margin-top: 4px;
}
.btn-primary:hover:not(:disabled) {
  transform: translateY(-2px);
  box-shadow: 0 8px 32px rgba(124,58,237,0.45);
}
.btn-primary:active:not(:disabled) {
  transform: translateY(0) scale(0.98);
  box-shadow: 0 2px 12px rgba(124,58,237,0.3);
}
.btn-primary:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}
.btn-primary::before {
  content: '';
  position: absolute;
  top: -50%; left: -50%;
  width: 200%; height: 200%;
  background: conic-gradient(transparent, rgba(255,255,255,0.12), transparent 30%);
  animation: btnRotate 4s linear infinite;
}
@keyframes btnRotate { from { transform: rotate(0deg); } to { transform: rotate(360deg); } }
.btn-primary span { position: relative; z-index: 1; }

/* 涟漪 */
.ripple {
  position: absolute;
  border-radius: 50%;
  background: rgba(255,255,255,0.3);
  transform: scale(0);
  animation: rippleAnim 0.6s ease-out;
  pointer-events: none;
}
@keyframes rippleAnim {
  to { transform: scale(4); opacity: 0; }
}

.auth-links {
  margin-top: 18px;
  display: flex;
  justify-content: space-between;
  font-size: 13px;
}
.auth-links a {
  color: #6b7280;
  text-decoration: none;
  transition: all 0.2s;
  position: relative;
}
.auth-links a:hover { color: #a855f7; }
.auth-links a::after {
  content: '';
  position: absolute;
  bottom: -2px; left: 0;
  width: 0; height: 1px;
  background: #a855f7;
  transition: width 0.3s;
}
.auth-links a:hover::after { width: 100%; }

.divider {
  display: flex; align-items: center; gap: 12px;
  margin: 22px 0; color: #4a4a6a; font-size: 12px;
}
.divider::before, .divider::after {
  content: ''; flex: 1; height: 1px;
  background: linear-gradient(90deg, transparent, rgba(139,92,246,0.15), transparent);
}

.btn-guest {
  width: 100%; padding: 12px;
  border: 1px solid rgba(6,182,212,0.2);
  border-radius: 12px;
  background: transparent;
  color: #06b6d4;
  font-size: 13px; font-family: 'Space Grotesk', sans-serif;
  cursor: pointer; transition: all 0.3s;
  position: relative; overflow: hidden;
}
.btn-guest:hover:not(:disabled) {
  border-color: rgba(6,182,212,0.5);
  box-shadow: 0 0 20px rgba(6,182,212,0.15);
  background: rgba(6,182,212,0.05);
}
.btn-guest:active:not(:disabled) { transform: scale(0.98); }
.btn-guest:disabled { opacity: 0.4; cursor: not-allowed; }

@media (max-width: 480px) {
  .card-body { padding: 32px 24px; }
  .auth-card { margin: 16px; }
}
</style>

<style>
/* @property 必须全局定义，scoped 里不生效 */
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
:root[data-theme="light"] .btn-guest {
  color: #0891B2;
  border-color: rgba(6, 182, 212, 0.25);
}
:root[data-theme="light"] .btn-guest:hover:not(:disabled) {
  border-color: rgba(6, 182, 212, 0.5);
  background: rgba(6, 182, 212, 0.05);
}
:root[data-theme="light"] .orbit-ring { opacity: 0.3; }
:root[data-theme="light"] .meteor { opacity: 0.3; }
:root[data-theme="light"] .aurora { opacity: 0.4; }
</style>
