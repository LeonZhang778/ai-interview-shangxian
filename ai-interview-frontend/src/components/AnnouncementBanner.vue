<template>
  <Transition name="banner-slide">
    <div
      v-if="visible && currentAnnouncement"
      class="announcement-banner"
      :class="[`level-${currentAnnouncement.level}`]"
      role="alert"
      :aria-label="`公告: ${currentAnnouncement.title}`"
    >
      <div class="banner-inner">
        <!-- 图标 -->
        <div class="banner-icon">
          <svg v-if="currentAnnouncement.level === 'P0'" width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round">
            <path d="M10.29 3.86L1.82 18a2 2 0 0 0 1.71 3h16.94a2 2 0 0 0 1.71-3L13.71 3.86a2 2 0 0 0-3.42 0z"/>
            <line x1="12" y1="9" x2="12" y2="13"/><line x1="12" y1="17" x2="12.01" y2="17"/>
          </svg>
          <svg v-else-if="currentAnnouncement.level === 'P1'" width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
            <circle cx="12" cy="12" r="10"/><line x1="12" y1="8" x2="12" y2="12"/><line x1="12" y1="16" x2="12.01" y2="16"/>
          </svg>
          <svg v-else width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
            <path d="M18 8A6 6 0 0 0 6 8c0 7-3 9-3 9h18s-3-2-3-9"/>
            <path d="M13.73 21a2 2 0 0 1-3.46 0"/>
          </svg>
        </div>

        <!-- 内容区 -->
        <div class="banner-content">
          <span class="banner-label" v-if="currentAnnouncement.level !== 'P2'">
            {{ currentAnnouncement.level === 'P0' ? '紧急通知' : '重要通知' }}
          </span>
          <span class="banner-title">{{ currentAnnouncement.title }}</span>
        </div>

        <!-- 操作区 -->
        <div class="banner-actions">
          <router-link
            :to="`/announcements/${currentAnnouncement.id}`"
            class="banner-detail-btn"
          >
            查看详情
            <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round">
              <polyline points="9 18 15 12 9 6"/>
            </svg>
          </router-link>

          <!-- 关闭按钮 (P0 不可关闭) -->
          <button
            v-if="currentAnnouncement.level !== 'P0'"
            class="banner-close"
            @click.stop="closeBanner"
            aria-label="关闭公告"
          >
            <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
              <line x1="18" y1="6" x2="6" y2="18"/><line x1="6" y1="6" x2="18" y2="18"/>
            </svg>
          </button>
        </div>

        <!-- P1/P2 多条轮播指示器 -->
        <div v-if="announcements.length > 1" class="banner-dots">
          <span
            v-for="(a, i) in announcements"
            :key="a.id"
            class="dot"
            :class="{ active: i === currentIndex }"
            @click.stop="currentIndex = i"
          ></span>
        </div>
      </div>
    </div>
  </Transition>
</template>

<script setup>
import { ref, computed, onMounted, onUnmounted, watch } from 'vue'
import { getAnnouncements } from '../api/announcement'

const announcements = ref([])
const currentIndex = ref(0)
const visible = ref(false)
let rotateTimer = null

const currentAnnouncement = computed(() => {
  if (!announcements.value.length) return null
  return announcements.value[currentIndex.value] || announcements.value[0]
})

// localStorage key: 用公告 id + 更新时间做版本控制
function getStorageKey() {
  return 'announcement_closed'
}

function isClosed(announcement) {
  try {
    const saved = JSON.parse(localStorage.getItem(getStorageKey()) || '{}')
    // 如果公告版本（id+发布时间）匹配且在 24 小时内，则不显示
    if (saved.id === announcement.id && saved.version === announcement.published_at) {
      const elapsed = Date.now() - (saved.closedAt || 0)
      if (elapsed < 24 * 60 * 60 * 1000) return true
    }
    return false
  } catch { return false }
}

function closeBanner() {
  if (!currentAnnouncement.value) return
  const a = currentAnnouncement.value
  localStorage.setItem(getStorageKey(), JSON.stringify({
    id: a.id,
    version: a.published_at,
    closedAt: Date.now()
  }))
  visible.value = false
}

function startRotation() {
  stopRotation()
  if (announcements.value.length <= 1) return
  rotateTimer = setInterval(() => {
    currentIndex.value = (currentIndex.value + 1) % announcements.value.length
  }, 5000)
}

function stopRotation() {
  if (rotateTimer) {
    clearInterval(rotateTimer)
    rotateTimer = null
  }
}

// 键盘 ESC 关闭
function onKeydown(e) {
  if (e.key === 'Escape' && visible.value && currentAnnouncement.value?.level !== 'P0') {
    closeBanner()
  }
}

onMounted(async () => {
  try {
    const data = await getAnnouncements({ page: 1, size: 10 })
    const items = data?.items || []
    // 过滤掉已关闭的
    const filtered = items.filter(a => !isClosed(a))
    if (filtered.length > 0) {
      // P0 排最前，然后 P1，然后 P2
      filtered.sort((a, b) => {
        const order = { P0: 0, P1: 1, P2: 2 }
        return (order[a.level] ?? 1) - (order[b.level] ?? 1)
      })
      announcements.value = filtered
      visible.value = true
      startRotation()
    }
  } catch (e) { /* silent */ }
  document.addEventListener('keydown', onKeydown)
})

onUnmounted(() => {
  stopRotation()
  document.removeEventListener('keydown', onKeydown)
})

watch(currentIndex, () => {
  // 用户手动切换时重置轮播
  startRotation()
})
</script>

<style scoped>
/* === 动画 === */
.banner-slide-enter-active {
  animation: slideDown 0.4s cubic-bezier(0.16, 1, 0.3, 1);
}
.banner-slide-leave-active {
  animation: slideUp 0.3s cubic-bezier(0.4, 0, 0.2, 1);
}
@keyframes slideDown {
  from { transform: translateY(-100%); opacity: 0; }
  to { transform: translateY(0); opacity: 1; }
}
@keyframes slideUp {
  from { transform: translateY(0); opacity: 1; }
  to { transform: translateY(-100%); opacity: 0; }
}

/* === 容器 === */
.announcement-banner {
  width: 100%;
  border-bottom: 1px solid;
  backdrop-filter: blur(20px);
  -webkit-backdrop-filter: blur(20px);
  position: relative;
  overflow: hidden;
}
/* 发光线 */
.announcement-banner::after {
  content: '';
  position: absolute;
  bottom: 0; left: 0; right: 0;
  height: 1px;
  z-index: 1;
}

/* === P0 紧急 — 深紫品红脉冲 === */
.level-P0 {
  background: linear-gradient(135deg, rgba(109, 20, 80, 0.88), rgba(76, 10, 100, 0.88));
  border-color: rgba(236, 72, 153, 0.25);
  color: white;
  box-shadow: 0 2px 20px rgba(236, 72, 153, 0.2);
}
.level-P0::after {
  background: linear-gradient(90deg, transparent, rgba(236, 72, 153, 0.6), rgba(168, 85, 247, 0.4), transparent);
  animation: pulseGlow 2s ease-in-out infinite;
}
@keyframes pulseGlow {
  0%, 100% { opacity: 0.6; }
  50% { opacity: 1; }
}
.level-P0 .banner-icon { color: rgba(255, 255, 255, 0.9); }
.level-P0 .banner-detail-btn {
  background: rgba(255, 255, 255, 0.12);
  color: white;
  border: 1px solid rgba(236, 72, 153, 0.35);
}
.level-P0 .banner-detail-btn:hover {
  background: rgba(255, 255, 255, 0.2);
  box-shadow: 0 0 12px rgba(236, 72, 153, 0.3);
}
.level-P0 .banner-label {
  background: rgba(236, 72, 153, 0.25);
  color: #f9a8d4;
}
.level-P0 .dot { background: rgba(255, 255, 255, 0.25); }
.level-P0 .dot.active { background: #f0abfc; box-shadow: 0 0 6px rgba(236, 72, 153, 0.5); }

/* === P1 重要 — 靛蓝青色极光 === */
.level-P1 {
  background: linear-gradient(135deg, rgba(30, 27, 75, 0.88), rgba(49, 46, 129, 0.88));
  border-color: rgba(6, 182, 212, 0.2);
  color: white;
  box-shadow: 0 2px 16px rgba(6, 182, 212, 0.15);
}
.level-P1::after {
  background: linear-gradient(90deg, transparent, rgba(6, 182, 212, 0.5), rgba(99, 102, 241, 0.3), transparent);
}
.level-P1 .banner-icon { color: rgba(6, 182, 212, 0.9); }
.level-P1 .banner-detail-btn {
  background: rgba(6, 182, 212, 0.12);
  color: #67e8f9;
  border: 1px solid rgba(6, 182, 212, 0.3);
}
.level-P1 .banner-detail-btn:hover {
  background: rgba(6, 182, 212, 0.22);
  box-shadow: 0 0 10px rgba(6, 182, 212, 0.25);
}
.level-P1 .banner-label {
  background: rgba(6, 182, 212, 0.2);
  color: #67e8f9;
}
.level-P1 .banner-close { color: rgba(255, 255, 255, 0.5); }
.level-P1 .banner-close:hover { color: white; background: rgba(6, 182, 212, 0.15); }
.level-P1 .dot { background: rgba(255, 255, 255, 0.2); }
.level-P1 .dot.active { background: #67e8f9; box-shadow: 0 0 6px rgba(6, 182, 212, 0.5); }

/* === P2 普通 — 深空灰紫 === */
.level-P2 {
  background: linear-gradient(135deg, rgba(20, 18, 50, 0.85), rgba(30, 27, 75, 0.85));
  border-color: rgba(139, 92, 246, 0.12);
  color: #e2e8f0;
  box-shadow: 0 1px 8px rgba(139, 92, 246, 0.08);
}
.level-P2::after {
  background: linear-gradient(90deg, transparent, rgba(139, 92, 246, 0.3), transparent);
}
.level-P2 .banner-icon { color: #a78bfa; }
.level-P2 .banner-detail-btn {
  background: rgba(139, 92, 246, 0.1);
  color: #c4b5fd;
  border: 1px solid rgba(139, 92, 246, 0.2);
}
.level-P2 .banner-detail-btn:hover {
  background: rgba(139, 92, 246, 0.2);
}
.level-P2 .banner-close { color: #6b7280; }
.level-P2 .banner-close:hover { color: #c4b5fd; background: rgba(139, 92, 246, 0.1); }
.level-P2 .dot { background: rgba(139, 92, 246, 0.25); }
.level-P2 .dot.active { background: #a78bfa; }

/* === Light mode === */
:root[data-theme="light"] .level-P0 {
  background: linear-gradient(135deg, rgba(239, 68, 68, 0.92), rgba(220, 38, 38, 0.92));
  border-color: rgba(239, 68, 68, 0.3);
}
:root[data-theme="light"] .level-P0::after {
  background: linear-gradient(90deg, transparent, rgba(239, 68, 68, 0.5), transparent);
}
:root[data-theme="light"] .level-P1 {
  background: linear-gradient(135deg, rgba(59, 130, 246, 0.9), rgba(99, 102, 241, 0.9));
  border-color: rgba(59, 130, 246, 0.3);
}
:root[data-theme="light"] .level-P1::after {
  background: linear-gradient(90deg, transparent, rgba(59, 130, 246, 0.4), transparent);
}
:root[data-theme="light"] .level-P2 {
  background: linear-gradient(135deg, rgba(241, 245, 249, 0.95), rgba(226, 232, 240, 0.95));
  border-color: rgba(203, 213, 225, 0.5);
  color: #334155;
}
:root[data-theme="light"] .level-P2::after {
  background: linear-gradient(90deg, transparent, rgba(99, 102, 241, 0.25), transparent);
}
:root[data-theme="light"] .level-P2 .banner-icon { color: #6366f1; }
:root[data-theme="light"] .level-P2 .banner-label {
  background: rgba(99, 102, 241, 0.1);
  color: #4f46e5;
}
:root[data-theme="light"] .level-P2 .banner-detail-btn {
  background: rgba(99, 102, 241, 0.08);
  color: #4f46e5;
  border-color: rgba(99, 102, 241, 0.2);
}
:root[data-theme="light"] .level-P2 .dot { background: #cbd5e1; }
:root[data-theme="light"] .level-P2 .dot.active { background: #6366f1; }

/* === 内部布局 === */
.banner-inner {
  max-width: 1200px;
  margin: 0 auto;
  padding: 10px 24px;
  display: flex;
  align-items: center;
  gap: 12px;
  min-height: 48px;
}

.banner-icon {
  flex-shrink: 0;
  display: flex;
  align-items: center;
}

.banner-content {
  flex: 1;
  display: flex;
  align-items: center;
  gap: 10px;
  min-width: 0;
}

.banner-label {
  font-size: 11px;
  font-weight: 700;
  padding: 2px 8px;
  border-radius: 4px;
  white-space: nowrap;
  letter-spacing: 0.02em;
  text-transform: uppercase;
}

.banner-title {
  font-size: 13.5px;
  font-weight: 500;
  line-height: 1.4;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.banner-actions {
  display: flex;
  align-items: center;
  gap: 8px;
  flex-shrink: 0;
}

.banner-detail-btn {
  display: inline-flex;
  align-items: center;
  gap: 4px;
  padding: 5px 14px;
  border-radius: 6px;
  font-size: 12.5px;
  font-weight: 600;
  text-decoration: none;
  white-space: nowrap;
  transition: all 0.2s ease;
}

.banner-close {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 28px;
  height: 28px;
  border: none;
  background: transparent;
  border-radius: 6px;
  cursor: pointer;
  transition: all 0.2s ease;
}

.banner-dots {
  display: flex;
  gap: 5px;
  margin-left: 4px;
}

.dot {
  width: 6px;
  height: 6px;
  border-radius: 50%;
  cursor: pointer;
  transition: all 0.3s ease;
}
.dot:hover { transform: scale(1.3); }

/* === 响应式 === */
@media (max-width: 640px) {
  .banner-inner {
    padding: 10px 16px;
    flex-wrap: wrap;
    gap: 8px;
  }
  .banner-content {
    flex-basis: calc(100% - 40px);
    order: 1;
  }
  .banner-title {
    white-space: normal;
    font-size: 13px;
  }
  .banner-actions {
    order: 2;
    margin-left: auto;
  }
  .banner-dots {
    order: 3;
    width: 100%;
    justify-content: center;
    margin-left: 0;
  }
}
</style>
