<template>
  <StarryBackground />
  <div class="container">
    <div v-if="loading" class="loading">加载报告中...</div>

    <div v-else-if="report" style="max-width:700px;margin:30px auto">
      <!-- 总分 -->
      <div class="card score-card">
        <div class="score-circle">
          <span class="score-num">{{ data.overall_score }}</span>
          <span class="score-label">/10</span>
        </div>
        <div class="score-info">
          <h2>面试评估报告</h2>
          <p class="hire-rec" v-if="report.hire_recommendation">
            {{ report.hire_recommendation }}
          </p>
        </div>
      </div>

      <!-- 总结 -->
      <div class="card" style="margin-top:16px" v-if="report.summary">
        <h3 style="margin-bottom:10px;color:var(--accent-light)">总体评价</h3>
        <p style="font-size:14px;line-height:1.8;color:var(--text-secondary)">{{ report.summary }}</p>
      </div>

      <!-- 优势 & 不足 -->
      <div class="two-col" style="margin-top:16px">
        <div class="card" v-if="report.strengths?.length">
          <h3 style="margin-bottom:10px;color:var(--green)">优势</h3>
          <ul>
            <li v-for="(s, i) in report.strengths" :key="i">{{ s }}</li>
          </ul>
        </div>
        <div class="card" v-if="report.weaknesses?.length">
          <h3 style="margin-bottom:10px;color:var(--red)">不足</h3>
          <ul>
            <li v-for="(w, i) in report.weaknesses" :key="i">{{ w }}</li>
          </ul>
        </div>
      </div>

      <!-- 建议 -->
      <div class="card" style="margin-top:16px" v-if="report.suggestions?.length">
        <h3 style="margin-bottom:10px;color:var(--accent-light)">改进建议</h3>
        <ul>
          <li v-for="(s, i) in report.suggestions" :key="i">{{ s }}</li>
        </ul>
      </div>

      <!-- 各题得分 -->
      <div class="card" style="margin-top:16px" v-if="report.question_scores?.length">
        <h3 style="margin-bottom:12px">📊 各题得分</h3>
        <div v-for="(q, i) in report.question_scores" :key="i" class="q-score-item">
          <div class="q-score-header">
            <span class="q-index">Q{{ i + 1 }}</span>
            <span class="q-text">{{ q.question }}</span>
            <span class="q-score" :style="{ color: q.score >= 7 ? '#059669' : q.score >= 5 ? '#d97706' : '#dc2626' }">
              {{ q.score }}
            </span>
          </div>
          <div class="q-bar">
            <div class="q-bar-fill" :style="{ width: (q.score * 10) + '%', background: q.score >= 7 ? '#10b981' : q.score >= 5 ? '#f59e0b' : '#ef4444' }"></div>
          </div>
        </div>
      </div>

      <!-- 分享卡片（隐藏，用于截图） -->
      <div ref="shareCard" class="share-card" v-if="report">
        <!-- 背景装饰 -->
        <div class="share-bg-circle share-bg-1"></div>
        <div class="share-bg-circle share-bg-2"></div>

        <!-- 头部品牌 -->
        <div class="share-brand">
          <div class="share-logo">
            <span class="share-logo-icon">🎯</span>
            <span class="share-logo-text">智面 AI</span>
          </div>
          <div class="share-tag">面试评估报告</div>
        </div>

        <!-- 分数区域 -->
        <div class="share-score-section">
          <div class="share-score-ring">
            <svg viewBox="0 0 120 120" class="share-score-svg">
              <circle cx="60" cy="60" r="52" fill="none" stroke="rgba(255,255,255,0.15)" stroke-width="8"/>
              <circle cx="60" cy="60" r="52" fill="none" stroke="url(#scoreGrad)" stroke-width="8"
                stroke-linecap="round" stroke-dasharray="326.7"
                :stroke-dashoffset="326.7 - (326.7 * (data.overall_score || 0) / 10)"
                transform="rotate(-90 60 60)"/>
              <defs>
                <linearGradient id="scoreGrad" x1="0%" y1="0%" x2="100%" y2="100%">
                  <stop offset="0%" stop-color="#fbbf24"/>
                  <stop offset="100%" stop-color="#f59e0b"/>
                </linearGradient>
              </defs>
            </svg>
            <div class="share-score-inner">
              <span class="share-score-num">{{ data.overall_score }}</span>
              <span class="share-score-unit">/10</span>
            </div>
          </div>
        </div>

        <!-- 信息区 -->
        <div class="share-info">
          <div class="share-position">{{ data.target_position || '模拟面试' }}</div>
          <div class="share-rec" v-if="report.hire_recommendation">{{ report.hire_recommendation }}</div>
        </div>

        <!-- 亮点摘要 -->
        <div class="share-highlights" v-if="report.strengths?.length">
          <div class="share-highlight-item" v-for="(s, i) in report.strengths.slice(0, 2)" :key="i">
            <span class="share-highlight-dot"></span>
            <span>{{ s }}</span>
          </div>
        </div>

        <!-- 底部二维码 + 品牌 -->
        <div class="share-bottom">
          <div class="share-qr" ref="qrCanvas"></div>
          <div class="share-bottom-info">
            <div class="share-bottom-title">扫码查看完整报告</div>
            <div class="share-bottom-sub">免费体验 AI 模拟面试</div>
          </div>
        </div>
      </div>

      <!-- 分享链接面板 -->
      <div class="card share-link-panel" style="margin-top:16px">
        <h3 style="margin-bottom:12px;color:var(--accent-light)">🔗 分享报告</h3>
        <p style="font-size:13px;color:var(--text-muted);margin-bottom:14px">生成分享链接，发给朋友查看你的面试表现</p>

        <div v-if="isShared && shareToken" class="share-link-box">
          <div class="share-link-url">
            <input :value="shareUrl" readonly class="share-input" />
            <button @click="copyShareLink" class="btn-copy" :class="{ copied: copyStatus === 'done' }">
              {{ copyStatus === 'done' ? '已复制' : '复制' }}
            </button>
          </div>
          <button @click="handleUnshare" class="btn-unshare">取消分享</button>
        </div>

        <button v-else @click="handleShareLink" class="btn-generate" :disabled="shareLinkStatus === 'loading'">
          {{ shareLinkStatus === 'loading' ? '生成中...' : '生成分享链接' }}
        </button>
      </div>

      <!-- 保存到学习笔记 -->
      <div class="card save-note-panel" style="margin-top:16px">
        <h3 style="margin-bottom:12px;color:var(--accent-light)">📝 保存到学习笔记</h3>
        <p style="font-size:13px;color:var(--text-muted);margin-bottom:14px">
          将本次面试结果自动生成复盘笔记草稿，含逐题记录、错题标记和 AI 改进建议
        </p>
        <button @click="handleSaveToNote" class="btn-generate" :disabled="noteStatus === 'loading'">
          {{ noteStatus === 'loading' ? '生成中...' : '生成学习笔记' }}
        </button>
        <p v-if="noteMessage" :class="['note-msg', noteMessageType]">{{ noteMessage }}</p>
      </div>

      <!-- 操作 -->
      <div style="text-align:center;margin-top:24px;margin-bottom:40px">
        <button @click="handleShareImage" class="btn-share" style="padding:10px 24px;border-radius:8px;margin-right:12px">
          截图分享
        </button>
        <router-link to="/resume/upload" class="btn-primary" style="display:inline-block;padding:10px 24px;color:white;border-radius:8px;margin-right:12px">
          再来一次
        </router-link>
        <router-link to="/dashboard" class="btn-secondary" style="display:inline-block;padding:10px 24px;border-radius:8px">
          返回首页
        </router-link>
      </div>

      <!-- 截图预览弹窗 -->
      <Teleport to="body">
        <div v-if="previewImage" class="preview-overlay" @click.self="closePreview">
          <div class="preview-modal">
            <div class="preview-header">
              <span>截图预览</span>
              <button class="preview-close" @click="closePreview">&times;</button>
            </div>
            <div class="preview-body">
              <img :src="previewImage" class="preview-img" alt="截图预览" />
            </div>
            <div class="preview-footer">
              <button class="btn-copy" @click="copyPreviewImage">复制到剪贴板</button>
              <a :href="previewImage" download="interview-report.png" class="btn-primary" style="display:inline-block;padding:10px 20px;color:white;border-radius:8px;text-decoration:none;font-size:14px">下载图片</a>
            </div>
          </div>
        </div>
      </Teleport>
    </div>

    <div v-else class="card" style="text-align:center;padding:60px;max-width:500px;margin:60px auto;color:var(--text-muted)">
      <p>报告加载失败</p>
      <router-link to="/dashboard" style="margin-top:12px;display:inline-block">返回首页</router-link>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted, computed } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { getReport, shareInterview, unshareInterview } from '../api/interview'
import { generateFromInterview } from '../api/learningNote'
import StarryBackground from '../components/StarryBackground.vue'

const route = useRoute()
const router = useRouter()
const interviewId = route.params.id
const data = ref(null)
const report = ref(null)
const loading = ref(true)
const shareCard = ref(null)
const qrCanvas = ref(null)
const shareStatus = ref('idle')
const shareLinkStatus = ref('idle')
const shareToken = ref(null)
const isShared = ref(false)
const copyStatus = ref('idle')
const previewImage = ref(null)
const noteStatus = ref('idle')
const noteMessage = ref('')
const noteMessageType = ref('')

const shareUrl = computed(() => {
  if (!shareToken.value) return ''
  return `${window.location.origin}/shared/${shareToken.value}`
})

onMounted(async () => {
  try {
    const res = await getReport(interviewId)
    data.value = res
    report.value = res.report || {}
    // 如果已有分享token
    if (res.share_token) {
      shareToken.value = res.share_token
      isShared.value = true
    }
  } catch (e) {
    console.error(e)
  } finally {
    loading.value = false
  }
})

async function handleShareImage() {
  if (shareStatus.value === 'generating') return
  shareStatus.value = 'generating'
  try {
    // 如果还没有分享链接，先生成
    if (!shareToken.value) {
      const res = await shareInterview(interviewId)
      shareToken.value = res.share_token
      isShared.value = true
    }

    // 生成二维码到 canvas
    await generateQRCode(shareUrl.value)

    const html2canvas = (await import('html2canvas')).default
    const canvas = await html2canvas(shareCard.value, {
      backgroundColor: '#4f46e5',
      scale: 2
    })
    const blob = await new Promise(resolve => canvas.toBlob(resolve, 'image/png'))
    const url = URL.createObjectURL(blob)
    previewImage.value = url
    shareStatus.value = 'idle'
  } catch (e) {
    console.error(e)
    shareStatus.value = 'idle'
  }
}

function closePreview() {
  if (previewImage.value) {
    URL.revokeObjectURL(previewImage.value)
    previewImage.value = null
  }
}

async function copyPreviewImage() {
  if (!previewImage.value) return
  try {
    const resp = await fetch(previewImage.value)
    const blob = await resp.blob()
    await navigator.clipboard.write([new ClipboardItem({ 'image/png': blob })])
    copyStatus.value = 'done'
    setTimeout(() => { copyStatus.value = 'idle' }, 2000)
  } catch {
    const a = document.createElement('a')
    a.href = previewImage.value
    a.download = 'interview-report.png'
    a.click()
  }
}

// 纯 Canvas 实现的二维码生成器
async function generateQRCode(text) {
  const container = qrCanvas.value
  if (!container) return
  container.innerHTML = ''

  const canvas = document.createElement('canvas')
  const size = 80
  canvas.width = size
  canvas.height = size
  canvas.style.width = size + 'px'
  canvas.style.height = size + 'px'
  container.appendChild(canvas)

  const ctx = canvas.getContext('2d')
  const modules = encodeQR(text)
  const moduleCount = modules.length
  const cellSize = size / moduleCount

  ctx.fillStyle = '#ffffff'
  ctx.fillRect(0, 0, size, size)
  ctx.fillStyle = '#1a1a2e'

  for (let row = 0; row < moduleCount; row++) {
    for (let col = 0; col < moduleCount; col++) {
      if (modules[row][col]) {
        ctx.fillRect(col * cellSize, row * cellSize, cellSize + 0.5, cellSize + 0.5)
      }
    }
  }
}

// 最小 QR Code 编码器（支持数字/字母/字节模式）
function encodeQR(text) {
  const data = encodeData(text)
  // QR版本选择：根据数据bit数查表（byte mode, EC level L）
  // 版本1=152 bits, 版本2=272, 版本3=440, 版本4=640, 版本5=864,
  // 版本6=1088, 版本7=1248, 版本8=1552, 版本9=1856, 版本10=2192
  const versionCaps = [0, 152, 272, 440, 640, 864, 1088, 1248, 1552, 1856, 2192]
  let version = 1
  while (version < versionCaps.length && data.length > versionCaps[version]) version++
  const moduleCount = version * 4 + 17
  const matrix = Array.from({ length: moduleCount }, () => Array(moduleCount).fill(null))
  const reserved = Array.from({ length: moduleCount }, () => Array(moduleCount).fill(false))

  // 放置定位图案
  placeFinder(matrix, reserved, 0, 0)
  placeFinder(matrix, reserved, moduleCount - 7, 0)
  placeFinder(matrix, reserved, 0, moduleCount - 7)

  // 放置对齐图案（version >= 2）
  if (version >= 2) {
    const alignPos = getAlignmentPositions(version)
    for (const r of alignPos) {
      for (const c of alignPos) {
        if (reserved[r][c]) continue
        placeAlignment(matrix, reserved, r, c)
      }
    }
  }

  // 时序图案
  for (let i = 8; i < moduleCount - 8; i++) {
    if (!reserved[6][i]) { matrix[6][i] = i % 2 === 0; reserved[6][i] = true }
    if (!reserved[i][6]) { matrix[i][6] = i % 2 === 0; reserved[i][6] = true }
  }

  // 暗模块
  if (moduleCount >= 9) {
    matrix[moduleCount - 8][8] = true
    reserved[moduleCount - 8][8] = true
  }

  // 格式信息（简化：使用 mask 0, 纠错 L）
  placeFormatInfo(matrix, reserved, moduleCount, 0)

  // 放置数据
  placeData(matrix, reserved, data, moduleCount)

  // 应用 mask
  applyMask(matrix, reserved, moduleCount, 0)

  return matrix.map(row => row.map(cell => cell === true))
}

function encodeData(text) {
  const bytes = new TextEncoder().encode(text)
  const bits = []
  // 模式指示符 0100 (字节模式)
  bits.push(0, 1, 0, 0)
  // 字符计数
  const countBits = 8
  for (let i = countBits - 1; i >= 0; i--) bits.push((bytes.length >> i) & 1)
  // 数据
  for (const b of bytes) {
    for (let i = 7; i >= 0; i--) bits.push((b >> i) & 1)
  }
  // 终止符
  for (let i = 0; i < 4 && bits.length < 200; i++) bits.push(0)
  // 填充到字节边界
  while (bits.length % 8 !== 0) bits.push(0)
  // 填充字节
  const padBytes = [0xEC, 0x11]
  let padIdx = 0
  while (bits.length < 200) {
    const b = padBytes[padIdx % 2]
    for (let i = 7; i >= 0; i--) bits.push((b >> i) & 1)
    padIdx++
  }
  return bits
}

function placeFinder(matrix, reserved, row, col) {
  for (let r = -1; r <= 7; r++) {
    for (let c = -1; c <= 7; c++) {
      const mr = row + r, mc = col + c
      if (mr < 0 || mr >= matrix.length || mc < 0 || mc >= matrix.length) continue
      const val = (r >= 0 && r <= 6 && (c === 0 || c === 6)) ||
                  (c >= 0 && c <= 6 && (r === 0 || r === 6)) ||
                  (r >= 2 && r <= 4 && c >= 2 && c <= 4)
      matrix[mr][mc] = val ? true : false
      reserved[mr][mc] = true
    }
  }
}

function placeAlignment(matrix, reserved, row, col) {
  for (let r = -2; r <= 2; r++) {
    for (let c = -2; c <= 2; c++) {
      const val = Math.abs(r) === 2 || Math.abs(c) === 2 || (r === 0 && c === 0)
      matrix[row + r][col + c] = val
      reserved[row + r][col + c] = true
    }
  }
}

function getAlignmentPositions(version) {
  if (version <= 1) return []
  const positions = [6]
  const last = version * 4 + 10
  if (version <= 6) {
    positions.push(last)
  } else {
    const step = Math.ceil((last - 6) / (version - 1))
    for (let i = 1; i < version; i++) positions.push(6 + i * step)
    positions.push(last)
  }
  return positions
}

function placeFormatInfo(matrix, reserved, moduleCount, mask) {
  const formatBits = getFormatBits(0, mask) // EC level L = 0
  // 水平格式信息（第8行）
  for (let i = 0; i < 15; i++) {
    const col = i < 6 ? i : (i === 6 ? 7 : (i < 8 ? 8 : moduleCount - 15 + i))
    if (!reserved[8][col]) {
      matrix[8][col] = (formatBits >> (14 - i)) & 1 ? true : false
      reserved[8][col] = true
    }
  }
  // 垂直格式信息（第8列）
  for (let i = 0; i < 15; i++) {
    const row = i < 6 ? i : (i === 6 ? 7 : (i < 8 ? 8 : moduleCount - 15 + i))
    if (!reserved[row][8]) {
      matrix[row][8] = (formatBits >> (14 - i)) & 1 ? true : false
      reserved[row][8] = true
    }
  }
}

function getFormatBits(ecLevel, mask) {
  let data = (ecLevel << 3) | mask
  let bits = data << 10
  let gen = 0x537 // 生成多项式
  for (let i = 4; i >= 0; i--) {
    if (bits & (1 << (i + 10))) bits ^= gen << i
  }
  return ((data << 10) | bits) ^ 0x5412
}

function placeData(matrix, reserved, data, moduleCount) {
  let bitIdx = 0
  let upward = true
  for (let col = moduleCount - 1; col >= 0; col -= 2) {
    if (col === 6) col = 5
    const rows = upward
      ? Array.from({ length: moduleCount }, (_, i) => moduleCount - 1 - i)
      : Array.from({ length: moduleCount }, (_, i) => i)
    for (const row of rows) {
      for (let c = 0; c < 2; c++) {
        const cc = col - c
        if (cc < 0 || cc >= moduleCount) continue
        if (reserved[row][cc]) continue
        matrix[row][cc] = bitIdx < data.length ? data[bitIdx] === 1 : false
        bitIdx++
      }
    }
    upward = !upward
  }
}

function applyMask(matrix, reserved, moduleCount, mask) {
  for (let r = 0; r < moduleCount; r++) {
    for (let c = 0; c < moduleCount; c++) {
      if (reserved[r][c]) continue
      if (mask === 0 && (r + c) % 2 === 0) matrix[r][c] = !matrix[r][c]
    }
  }
}

async function handleShareLink() {
  if (shareLinkStatus.value === 'loading') return
  shareLinkStatus.value = 'loading'
  try {
    const res = await shareInterview(interviewId)
    shareToken.value = res.share_token
    isShared.value = true
    shareLinkStatus.value = 'done'
  } catch (e) {
    console.error(e)
    shareLinkStatus.value = 'idle'
  }
}

async function handleUnshare() {
  try {
    await unshareInterview(interviewId)
    shareToken.value = null
    isShared.value = false
  } catch (e) {
    console.error(e)
  }
}

async function copyShareLink() {
  if (!shareUrl.value) return
  try {
    await navigator.clipboard.writeText(shareUrl.value)
    copyStatus.value = 'done'
    setTimeout(() => { copyStatus.value = 'idle' }, 2000)
  } catch {
    // Fallback
    const input = document.createElement('input')
    input.value = shareUrl.value
    document.body.appendChild(input)
    input.select()
    document.execCommand('copy')
    document.body.removeChild(input)
    copyStatus.value = 'done'
    setTimeout(() => { copyStatus.value = 'idle' }, 2000)
  }
}

async function handleSaveToNote() {
  if (noteStatus.value === 'loading') return
  noteStatus.value = 'loading'
  noteMessage.value = ''
  try {
    const res = await generateFromInterview({
      interview_id: interviewId,
      note_type: 'review',
    })
    noteMessage.value = res.message || '学习笔记草稿已生成'
    noteMessageType.value = 'success'
    // 若返回笔记 id，3 秒后跳转或保留查看链接
    if (res.id) {
      setTimeout(() => {
        router.push(`/learning-notes/${res.id}`)
      }, 1500)
    }
  } catch (e) {
    noteMessage.value = e.response?.data?.detail || '生成失败，请重试'
    noteMessageType.value = 'error'
  } finally {
    noteStatus.value = 'idle'
  }
}
</script>

<style scoped>
.loading {
  text-align: center;
  padding: 80px;
  color: var(--text-muted);
}
.score-card {
  display: flex;
  align-items: center;
  gap: 24px;
}
.score-circle {
  width: 90px;
  height: 90px;
  border-radius: 50%;
  background: linear-gradient(135deg, #7c3aed, #6366f1);
  display: flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
  box-shadow: 0 0 24px rgba(124,58,237,0.3);
}
.score-num {
  font-size: 32px;
  font-weight: 700;
  color: white;
}
.score-label {
  font-size: 14px;
  color: rgba(255,255,255,0.7);
}
.score-info h2 {
  font-family: 'Space Grotesk', sans-serif;
  font-size: 20px;
  margin-bottom: 4px;
  color: var(--text-primary);
}
.hire-rec {
  font-size: 14px;
  color: var(--text-muted);
  margin-top: 4px;
}
.two-col {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 16px;
}
ul {
  list-style: none;
  padding: 0;
}
ul li {
  font-size: 14px;
  line-height: 1.8;
  padding-left: 16px;
  position: relative;
  color: var(--text-secondary);
}
ul li::before {
  content: '•';
  position: absolute;
  left: 0;
  color: var(--text-muted);
}
.q-score-item {
  margin-bottom: 14px;
}
.q-score-header {
  display: flex;
  align-items: center;
  gap: 10px;
  margin-bottom: 6px;
  font-size: 14px;
  color: var(--text-primary);
}
.q-index {
  background: rgba(139,92,246,0.1);
  padding: 2px 8px;
  border-radius: 4px;
  font-weight: 600;
  font-size: 12px;
  color: var(--accent-purple);
}
.q-text {
  flex: 1;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  color: var(--text-secondary);
}
.q-score {
  font-weight: 700;
  font-size: 16px;
  color: var(--text-primary);
}
.q-bar {
  height: 6px;
  background: var(--bg-hover);
  border-radius: 3px;
  overflow: hidden;
}
.q-bar-fill {
  height: 100%;
  border-radius: 3px;
  transition: width 0.5s ease;
}

/* Share card */
.share-card {
  position: absolute;
  left: -9999px;
  top: 0;
  width: 380px;
  padding: 32px 28px 24px;
  background: linear-gradient(150deg, #1a1a2e 0%, #16213e 40%, #0f3460 100%);
  color: white;
  text-align: center;
  border-radius: 20px;
  font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
  overflow: hidden;
  position: absolute;
  left: -9999px;
  top: 0;
}
.share-bg-circle {
  position: absolute;
  border-radius: 50%;
  pointer-events: none;
}
.share-bg-1 {
  width: 200px; height: 200px;
  top: -60px; right: -40px;
  background: radial-gradient(circle, rgba(99,102,241,0.3) 0%, transparent 70%);
}
.share-bg-2 {
  width: 150px; height: 150px;
  bottom: 20px; left: -30px;
  background: radial-gradient(circle, rgba(236,72,153,0.2) 0%, transparent 70%);
}
.share-brand {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 24px;
  position: relative;
}
.share-logo {
  display: flex;
  align-items: center;
  gap: 6px;
}
.share-logo-icon { font-size: 18px; }
.share-logo-text {
  font-size: 16px;
  font-weight: 700;
  background: linear-gradient(135deg, #a78bfa, #60a5fa);
  -webkit-background-clip: text;
  -webkit-text-fill-color: transparent;
  background-clip: text;
}
.share-tag {
  font-size: 11px;
  padding: 4px 10px;
  background: rgba(255,255,255,0.1);
  border: 1px solid rgba(255,255,255,0.15);
  border-radius: 20px;
  color: rgba(255,255,255,0.7);
}
.share-score-section {
  display: flex;
  justify-content: center;
  margin-bottom: 20px;
  position: relative;
}
.share-score-ring {
  position: relative;
  width: 120px;
  height: 120px;
}
.share-score-svg {
  width: 100%;
  height: 100%;
}
.share-score-inner {
  position: absolute;
  inset: 0;
  display: flex;
  align-items: center;
  justify-content: center;
  flex-direction: column;
}
.share-score-num {
  font-size: 36px;
  font-weight: 800;
  line-height: 1;
  background: linear-gradient(135deg, #fbbf24, #f59e0b);
  -webkit-background-clip: text;
  -webkit-text-fill-color: transparent;
  background-clip: text;
}
.share-score-unit {
  font-size: 13px;
  color: rgba(255,255,255,0.5);
  margin-top: 2px;
}
.share-info {
  margin-bottom: 16px;
  position: relative;
}
.share-position {
  font-size: 18px;
  font-weight: 600;
  color: rgba(255,255,255,0.95);
  margin-bottom: 8px;
}
.share-rec {
  font-size: 13px;
  background: linear-gradient(135deg, rgba(99,102,241,0.25), rgba(236,72,153,0.2));
  border: 1px solid rgba(255,255,255,0.1);
  border-radius: 20px;
  padding: 5px 16px;
  display: inline-block;
  color: rgba(255,255,255,0.85);
}
.share-highlights {
  background: rgba(255,255,255,0.05);
  border: 1px solid rgba(255,255,255,0.08);
  border-radius: 12px;
  padding: 12px 16px;
  margin-bottom: 20px;
  text-align: left;
  position: relative;
}
.share-highlight-item {
  display: flex;
  align-items: flex-start;
  gap: 8px;
  font-size: 12px;
  color: rgba(255,255,255,0.75);
  line-height: 1.5;
  margin-bottom: 4px;
}
.share-highlight-item:last-child { margin-bottom: 0; }
.share-highlight-dot {
  width: 4px;
  height: 4px;
  border-radius: 50%;
  background: #a78bfa;
  margin-top: 6px;
  flex-shrink: 0;
}
.share-bottom {
  display: flex;
  align-items: center;
  gap: 14px;
  padding-top: 16px;
  border-top: 1px solid rgba(255,255,255,0.1);
  position: relative;
}
.share-qr {
  width: 80px;
  height: 80px;
  background: white;
  border-radius: 8px;
  padding: 4px;
  flex-shrink: 0;
  display: flex;
  align-items: center;
  justify-content: center;
}
.share-qr canvas {
  display: block;
}
.share-bottom-info {
  text-align: left;
}
.share-bottom-title {
  font-size: 13px;
  font-weight: 600;
  color: rgba(255,255,255,0.9);
  margin-bottom: 3px;
}
.share-bottom-sub {
  font-size: 11px;
  color: rgba(255,255,255,0.5);
}

.btn-share {
  background: linear-gradient(135deg, #f59e0b, #f97316);
  color: white;
  border: none;
  font-size: 14px;
  font-weight: 600;
  cursor: pointer;
  transition: all 0.3s;
}
.btn-share:hover {
  transform: translateY(-1px);
  box-shadow: 0 4px 15px rgba(245,158,11,0.4);
}

/* Share link panel */
.share-link-panel {
  background: rgba(99, 102, 241, 0.08);
  border: 1px solid rgba(99, 102, 241, 0.2);
}
.share-link-box {
  display: flex;
  flex-direction: column;
  gap: 10px;
}
.share-link-url {
  display: flex;
  gap: 8px;
}
.share-input {
  flex: 1;
  padding: 10px 14px;
  background: rgba(0, 0, 0, 0.3);
  border: 1px solid rgba(255, 255, 255, 0.1);
  border-radius: 8px;
  color: var(--text-primary);
  font-size: 13px;
  outline: none;
}
.btn-copy {
  padding: 10px 18px;
  background: rgba(99, 102, 241, 0.3);
  border: 1px solid rgba(99, 102, 241, 0.5);
  border-radius: 8px;
  color: var(--accent-light);
  font-size: 13px;
  font-weight: 600;
  cursor: pointer;
  transition: all 0.2s;
  white-space: nowrap;
}
.btn-copy:hover {
  background: rgba(99, 102, 241, 0.5);
}
.btn-copy.copied {
  background: rgba(16, 185, 129, 0.3);
  border-color: rgba(16, 185, 129, 0.5);
  color: #10b981;
}
.btn-unshare {
  align-self: flex-end;
  padding: 6px 14px;
  background: transparent;
  border: 1px solid rgba(239, 68, 68, 0.3);
  border-radius: 6px;
  color: #ef4444;
  font-size: 12px;
  cursor: pointer;
  transition: all 0.2s;
}
.btn-unshare:hover {
  background: rgba(239, 68, 68, 0.1);
}
.btn-generate {
  padding: 12px 24px;
  background: linear-gradient(135deg, #6366f1, #8b5cf6);
  border: none;
  border-radius: 8px;
  color: white;
  font-size: 14px;
  font-weight: 600;
  cursor: pointer;
  transition: all 0.3s;
}
.btn-generate:hover {
  transform: translateY(-1px);
  box-shadow: 0 4px 15px rgba(99, 102, 241, 0.4);
}
.btn-generate:disabled {
  opacity: 0.6;
  cursor: not-allowed;
  transform: none;
}

/* 保存到学习笔记 */
.save-note-panel {
  margin-top: 16px;
}
.note-msg {
  margin-top: 12px;
  font-size: 13px;
  font-weight: 500;
}
.note-msg.success {
  color: #10b981;
}
.note-msg.error {
  color: #ef4444;
}

/* 截图预览弹窗 */
.preview-overlay {
  position: fixed;
  inset: 0;
  background: rgba(0,0,0,0.6);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 9999;
}
.preview-modal {
  background: var(--bg-surface);
  border-radius: 16px;
  max-width: 450px;
  width: 90%;
  overflow: hidden;
  box-shadow: 0 20px 60px rgba(0,0,0,0.5);
}
.preview-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 16px 20px;
  font-size: 16px;
  font-weight: 600;
  color: var(--text-primary);
  border-bottom: 1px solid var(--border-default);
}
.preview-close {
  background: none;
  border: none;
  font-size: 24px;
  color: var(--text-muted);
  cursor: pointer;
  padding: 0;
  line-height: 1;
}
.preview-close:hover {
  color: var(--text-primary);
}
.preview-body {
  padding: 20px;
  display: flex;
  justify-content: center;
}
.preview-img {
  max-width: 100%;
  border-radius: 12px;
  box-shadow: 0 4px 20px rgba(0,0,0,0.3);
}
.preview-footer {
  display: flex;
  gap: 12px;
  padding: 16px 20px;
  border-top: 1px solid var(--border-default);
  justify-content: center;
}
.preview-footer .btn-copy {
  flex: 1;
  text-align: center;
}
</style>
