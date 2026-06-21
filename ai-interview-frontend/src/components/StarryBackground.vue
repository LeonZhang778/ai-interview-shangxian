<template>
  <Teleport to="body">
    <div class="starry-bg">
      <canvas ref="starCanvas" class="star-canvas"></canvas>
      <div class="aurora"></div>
      <div class="orbit-ring r1"></div>
      <div class="orbit-ring r2"></div>
      <div class="orbit-ring r3"></div>
      <div class="meteor m1"></div>
      <div class="meteor m2"></div>
      <div class="meteor m3"></div>
    </div>
  </Teleport>
</template>

<script setup>
import { ref, onMounted, onUnmounted } from 'vue'

const starCanvas = ref(null)
let stars = []
let animId = null

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
    animId = requestAnimationFrame(draw)
  }
  draw()
}

function onResize() {
  const canvas = starCanvas.value
  if (canvas) { canvas.width = window.innerWidth; canvas.height = window.innerHeight }
}

onMounted(() => {
  initStars()
  window.addEventListener('resize', onResize)
})

onUnmounted(() => {
  if (animId) cancelAnimationFrame(animId)
  window.removeEventListener('resize', onResize)
})
</script>

<style>
.starry-bg {
  position: fixed;
  inset: 0;
  z-index: 0;
  pointer-events: none;
  background: #030014;
}

.star-canvas {
  position: absolute;
  inset: 0;
  z-index: 1;
}

.aurora {
  position: absolute;
  top: -30%; left: -10%;
  width: 120%; height: 60%;
  background: radial-gradient(ellipse at 30% 50%, rgba(139,92,246,0.15) 0%, transparent 50%),
              radial-gradient(ellipse at 70% 50%, rgba(6,182,212,0.1) 0%, transparent 50%);
  filter: blur(80px);
  animation: auroraDrift 12s ease-in-out infinite alternate;
  z-index: 2;
}
@keyframes auroraDrift {
  0% { transform: translateX(-3%) rotate(-2deg); }
  100% { transform: translateX(3%) rotate(2deg); }
}

.orbit-ring {
  position: absolute;
  border-radius: 50%;
  border: 1px solid rgba(139,92,246,0.08);
  z-index: 3;
  animation: orbitSpin linear infinite;
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

.meteor {
  position: absolute;
  width: 120px; height: 1px;
  background: linear-gradient(90deg, rgba(168,85,247,0.8), transparent);
  z-index: 4;
  animation: meteorFall linear infinite;
  opacity: 0;
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

/* Light mode */
:root[data-theme="light"] .starry-bg { background: #f0f0f8; }
:root[data-theme="light"] .star-canvas { opacity: 0.3; }
:root[data-theme="light"] .aurora { opacity: 0.4; }
:root[data-theme="light"] .orbit-ring { opacity: 0.3; }
:root[data-theme="light"] .meteor { opacity: 0.3; }
</style>
