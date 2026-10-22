<template>
  <div
    ref="wrapperEl"
    class="bug-report-wrapper"
    :class="{ 'open-down': panelOpenDown, dragging }"
    :style="wrapperStyle"
  >
    <transition name="fade">
      <div v-if="expanded" class="bug-panel" :style="panelStyle">
        <div class="bug-header">
          <span>意见反馈</span>
          <button class="close-btn" aria-label="关闭反馈面板" @click="expanded = false"><BaseIcon name="x" :size="16" /></button>
        </div>
        <div class="form-group">
          <label>反馈类型</label>
          <select v-model="form.feedback_type">
            <option value="bug">Bug 反馈</option>
            <option value="suggestion">功能建议</option>
            <option value="other">其他</option>
          </select>
        </div>
        <div class="form-group">
          <label>内容 <span style="color:var(--red)">*</span></label>
          <textarea v-model="form.content" rows="4" placeholder="请描述你遇到的问题或建议..."></textarea>
        </div>
        <div class="form-group">
          <label>联系方式（选填）</label>
          <input v-model="form.contact" placeholder="邮箱或手机号，方便我们联系你" />
        </div>
        <button class="submit-btn" @click="submitFeedback" :disabled="!form.content || submitting">
          {{ submitting ? '提交中...' : '提交反馈' }}
        </button>
        <p v-if="submitSuccess" class="success-msg">感谢反馈！我们会尽快处理</p>
        <p class="bug-note">所有反馈都会被记录，帮助我们持续改进</p>
      </div>
    </transition>
    <button
      ref="toggleEl"
      class="bug-toggle"
      title="意见反馈（按住可拖动调整位置）"
      aria-label="意见反馈，可拖动调整位置"
      @pointerdown="onPointerDown"
      @pointermove="onPointerMove"
      @pointerup="onPointerUp"
      @pointercancel="onPointerUp"
      @click="onClick"
    >
      <BaseIcon name="snake" :size="22" />
    </button>
  </div>
</template>

<script setup>
import { ref, reactive, computed, onMounted, onBeforeUnmount } from 'vue'
import api from '../api/request'
import BaseIcon from './BaseIcon.vue'

const expanded = ref(false)
const submitting = ref(false)
const submitSuccess = ref(false)

const form = reactive({
  feedback_type: 'bug',
  content: '',
  contact: '',
  page_url: window.location.href,
})

/* ---------- 悬浮按钮拖拽定位 ---------- */
const POSITION_KEY = 'ai-interview:feedback-fab-pos'
const EDGE = 8              // 距屏幕边缘最小留白
const DRAG_THRESHOLD = 4    // 移动超过 4px 才算拖拽，否则视为点击
const FAB_SIZE = 48         // 与 .bug-toggle 尺寸保持一致
const PANEL_WIDTH = 300     // 与 .bug-panel width 保持一致
const PANEL_HEIGHT = 380    // 面板高度估算值，用于决定向上还是向下展开

const wrapperEl = ref(null)
const toggleEl = ref(null)
const pos = ref(null)       // { x, y } 按钮左上角坐标；null 表示用 CSS 默认的右下角
const dragging = ref(false)
let dragState = null
let lastDragEndAt = 0

const wrapperStyle = computed(() => (
  pos.value
    ? { left: `${pos.value.x}px`, top: `${pos.value.y}px`, right: 'auto', bottom: 'auto' }
    : {}
))

// 面板水平位置：默认与按钮右边缘对齐；靠近屏幕左/右侧时整体平移，保证不超出视口
const panelStyle = computed(() => {
  if (!pos.value) return {}
  const width = Math.min(PANEL_WIDTH, window.innerWidth - EDGE * 2)
  const desiredLeft = pos.value.x + FAB_SIZE - width
  const maxLeft = Math.max(EDGE, window.innerWidth - width - EDGE)
  const left = Math.min(Math.max(desiredLeft, EDGE), maxLeft)
  // 竖向可用空间：面板向上展开时取按钮上方的距离，向下时取下方的距离
  const maxHeight = panelOpenDown.value
    ? window.innerHeight - (pos.value.y + FAB_SIZE + 10) - EDGE
    : pos.value.y - 10 - EDGE
  return {
    left: `${left - pos.value.x}px`,
    right: 'auto',
    maxHeight: `${Math.max(200, maxHeight)}px`,
  }
})

// 面板默认在按钮上方；上方放不下且下方空间更宽裕时改为向下展开
const panelOpenDown = computed(() => {
  if (!pos.value) return false
  const above = pos.value.y - 10 - EDGE
  const below = window.innerHeight - (pos.value.y + FAB_SIZE + 10) - EDGE
  return above < PANEL_HEIGHT && below > above
})

function clampPosition(x, y) {
  const width = wrapperEl.value?.offsetWidth || FAB_SIZE
  const height = wrapperEl.value?.offsetHeight || FAB_SIZE
  const maxX = Math.max(EDGE, window.innerWidth - width - EDGE)
  const maxY = Math.max(EDGE, window.innerHeight - height - EDGE)
  return {
    x: Math.min(Math.max(x, EDGE), maxX),
    y: Math.min(Math.max(y, EDGE), maxY),
  }
}

function savePosition() {
  if (!pos.value) return
  try {
    localStorage.setItem(POSITION_KEY, JSON.stringify(pos.value))
  } catch (e) {
    // 隐私模式等场景无法写入存储，忽略即可
  }
}

function loadPosition() {
  try {
    const raw = localStorage.getItem(POSITION_KEY)
    if (!raw) return
    const saved = JSON.parse(raw)
    if (typeof saved?.x === 'number' && typeof saved?.y === 'number') {
      pos.value = clampPosition(saved.x, saved.y)
    }
  } catch (e) {
    // 存储内容损坏时回退到默认位置
  }
}

function onPointerDown(event) {
  if (event.button !== undefined && event.button !== 0) return
  const rect = wrapperEl.value.getBoundingClientRect()
  dragState = {
    pointerId: event.pointerId,
    startX: event.clientX,
    startY: event.clientY,
    originX: rect.left,
    originY: rect.top,
    moved: false,
  }
  event.currentTarget.setPointerCapture?.(event.pointerId)
}

function onPointerMove(event) {
  if (!dragState || event.pointerId !== dragState.pointerId) return
  const dx = event.clientX - dragState.startX
  const dy = event.clientY - dragState.startY
  if (!dragState.moved) {
    if (Math.hypot(dx, dy) < DRAG_THRESHOLD) return
    dragState.moved = true
    dragging.value = true
    expanded.value = false // 拖动时先收起面板，避免面板跟着晃
  }
  pos.value = clampPosition(dragState.originX + dx, dragState.originY + dy)
  event.preventDefault()
}

function onPointerUp(event) {
  if (!dragState || event.pointerId !== dragState.pointerId) return
  const moved = dragState.moved
  dragState = null
  dragging.value = false
  if (moved) {
    lastDragEndAt = Date.now()
    savePosition()
  }
}

function onClick() {
  // 刚拖动结束时浏览器仍会补发一次 click，这里过滤掉，避免松手就弹出面板
  if (Date.now() - lastDragEndAt < 300) return
  expanded.value = !expanded.value
}

function onWindowResize() {
  if (pos.value) {
    pos.value = clampPosition(pos.value.x, pos.value.y)
  }
}

onMounted(() => {
  loadPosition()
  window.addEventListener('resize', onWindowResize)
})

onBeforeUnmount(() => {
  window.removeEventListener('resize', onWindowResize)
})

async function submitFeedback() {
  if (!form.content) return
  submitting.value = true
  submitSuccess.value = false
  try {
    await api.post('/feedbacks', {
      content: form.content,
      feedback_type: form.feedback_type,
      contact: form.contact || undefined,
      page_url: window.location.href,
    })
    submitSuccess.value = true
    form.content = ''
    form.contact = ''
    setTimeout(() => { submitSuccess.value = false }, 3000)
  } catch (e) {
    alert('提交失败，请稍后重试')
  } finally {
    submitting.value = false
  }
}
</script>

<style scoped>
.bug-report-wrapper {
  position: fixed;
  bottom: 24px;
  right: 24px;
  z-index: 9999;
  /* 只包裹按钮本体：面板用绝对定位浮在外面，拖动时按钮位置不会跳动 */
}

.bug-toggle {
  width: 48px;
  height: 48px;
  padding: 0;
  border-radius: var(--radius-md);
  border: 1px solid var(--border-default);
  background: var(--accent-primary);
  color: var(--bg-base);
  cursor: grab;
  touch-action: none; /* 触屏拖动时不触发页面滚动 */
  user-select: none;
  box-shadow: var(--shadow-sm);
  transition: opacity 0.15s, background-color 0.15s, box-shadow 0.15s;
  display: flex;
  align-items: center;
  justify-content: center;
}
.bug-toggle:hover {
  transform: none;
  opacity: 0.85;
  box-shadow: var(--shadow-sm);
}
.bug-toggle:active,
.bug-report-wrapper.dragging .bug-toggle {
  cursor: grabbing;
}
.bug-toggle:focus-visible {
  outline: 2px solid var(--border-focus);
  outline-offset: 2px;
}
.bug-report-wrapper.dragging .bug-toggle {
  opacity: 0.9;
}

.bug-panel {
  position: absolute;
  right: 0;
  bottom: calc(100% + 10px);
  background: var(--bg-surface);
  border: 1px solid var(--border-default);
  border-radius: var(--radius-lg);
  padding: 18px 20px;
  box-shadow: var(--shadow-sm);
  width: 300px;
  max-height: calc(100vh - 120px);
  overflow-y: auto;
  font-size: 13px;
  line-height: 1.6;
}
/* 按钮靠近屏幕顶部时，面板改为向下展开 */
.bug-report-wrapper.open-down .bug-panel {
  bottom: auto;
  top: calc(100% + 10px);
}

.bug-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  font-weight: 600;
  font-size: 14px;
  margin-bottom: 14px;
  color: var(--text-primary);
}

.close-btn {
  border: none;
  background: none;
  font-size: 18px;
  color: var(--text-muted);
  cursor: pointer;
  padding: 0 2px;
  transition: color 0.2s;
}
.close-btn:hover { color: var(--text-primary); }

.form-group {
  margin-bottom: 10px;
}
.form-group label {
  display: block;
  font-size: 12px;
  font-weight: 600;
  color: var(--text-secondary);
  margin-bottom: 4px;
}
.form-group input,
.form-group select,
.form-group textarea {
  width: 100%;
  padding: 8px 10px;
  border: 1px solid var(--border-default);
  border-radius: 6px;
  font-size: 13px;
  box-sizing: border-box;
  font-family: inherit;
  background: var(--bg-input);
  color: var(--text-primary);
  transition: border-color 0.2s, background 0.3s;
}
.form-group input:focus,
.form-group select:focus,
.form-group textarea:focus {
  border-color: var(--border-focus);
  background: var(--bg-input-focus);
}
.form-group textarea {
  resize: vertical;
}

/* Dark mode: override browser defaults for select/option */
.bug-panel select option {
  background-color: var(--bg-surface);
  color: var(--text-primary);
}
:root[data-theme="light"] .bug-panel select option {
  background-color: var(--bg-surface);
  color: var(--text-primary);
}

.submit-btn {
  width: 100%;
  padding: 10px;
  background: var(--accent-primary);
  color: var(--bg-base);
  border: 1px solid var(--accent-primary);
  border-radius: var(--radius-md);
  font-size: 14px;
  font-weight: 600;
  cursor: pointer;
  transition: opacity 0.15s;
  box-shadow: var(--shadow-sm);
}
.submit-btn:hover {
  opacity: 0.85;
  transform: none;
  box-shadow: var(--shadow-sm);
}
.submit-btn:disabled {
  background: var(--text-dim);
  border-color: var(--text-dim);
  cursor: not-allowed;
  transform: none;
  box-shadow: var(--shadow-sm);
}

.success-msg {
  color: var(--green);
  font-size: 13px;
  font-weight: 600;
  text-align: center;
  margin: 8px 0 0;
}

.bug-note {
  color: var(--text-dim);
  font-size: 11px;
  margin: 8px 0 0;
}

.fade-enter-active,
.fade-leave-active {
  transition: opacity 0.2s, transform 0.2s;
}
.fade-enter-from,
.fade-leave-to {
  opacity: 0;
  transform: translateY(8px);
}

@media (max-width: 640px) {
  .bug-report-wrapper {
    bottom: 10px;
    right: 10px;
  }
  .bug-toggle {
    width: 40px;
    height: 40px;
    font-size: 18px;
  }
  .bug-panel {
    width: calc(100vw - 32px);
    max-width: 300px;
  }
}
</style>
