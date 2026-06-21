<template>
  <div class="announcement-detail-page">
    <div class="container">
      <div class="page-header">
        <router-link to="/announcements" class="back-link">&larr; 返回公告列表</router-link>
      </div>

      <div v-if="loading" class="loading">
        <div class="loading-spinner"></div>
        <span>加载中...</span>
      </div>

      <div v-else-if="!announcement" class="empty-state">
        <div class="empty-icon">&#x1F615;</div>
        <p>公告不存在或已过期</p>
      </div>

      <div v-else class="detail-card">
        <div class="card-top-line"></div>
        <div class="card-inner">
          <div class="detail-header">
            <span class="tag" :class="`type-${announcement.type}`">{{ typeLabels[announcement.type] || '通知' }}</span>
            <span v-if="announcement.is_pinned" class="pin-badge">&#x1F4CC; 置顶</span>
          </div>
          <h1 class="detail-title">{{ announcement.title }}</h1>
          <div class="detail-meta">
            <span>发布时间：{{ formatDate(announcement.published_at) }}</span>
          </div>
          <div class="detail-content" v-html="renderContent(announcement.content)"></div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { useRoute } from 'vue-router'
import { getAnnouncementDetail } from '../api/announcement'

const route = useRoute()
const announcement = ref(null)
const loading = ref(true)
const typeLabels = { info: '通知', update: '更新', maintenance: '维护', activity: '活动' }

function formatDate(str) {
  if (!str) return ''
  return new Date(str).toLocaleString('zh-CN', { year: 'numeric', month: '2-digit', day: '2-digit', hour: '2-digit', minute: '2-digit' })
}

function renderContent(text) {
  if (!text) return ''
  return text
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/\n/g, '<br>')
    .replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>')
}

onMounted(async () => {
  try {
    const data = await getAnnouncementDetail(route.params.id)
    announcement.value = data
  } catch (e) {
    console.error(e)
  } finally {
    loading.value = false
  }
})
</script>

<style scoped>
.announcement-detail-page {
  min-height: 100vh;
  background: var(--bg-base);
  color: var(--text-primary);
}

.container {
  max-width: 800px;
  margin: 0 auto;
  padding: 32px 20px;
}

.page-header {
  margin-bottom: 24px;
}
.back-link {
  color: var(--text-muted);
  font-size: 14px;
  text-decoration: none;
  transition: color 0.2s;
}
.back-link:hover { color: var(--accent-primary); }

/* 加载 */
.loading {
  text-align: center;
  padding: 80px 20px;
  color: var(--text-muted);
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 16px;
}
.loading-spinner {
  width: 32px; height: 32px;
  border: 3px solid rgba(139,92,246,0.15);
  border-top-color: var(--accent-primary);
  border-radius: 50%;
  animation: spin 0.8s linear infinite;
}
@keyframes spin { to { transform: rotate(360deg); } }

/* 空状态 */
.empty-state {
  text-align: center;
  padding: 80px 20px;
  color: var(--text-dim);
}
.empty-icon {
  font-size: 48px;
  margin-bottom: 12px;
}

/* 详情卡片 */
.detail-card {
  background: rgba(139, 92, 246, 0.04);
  border: 1px solid rgba(139, 92, 246, 0.1);
  border-radius: 16px;
  overflow: hidden;
}
.card-top-line {
  height: 2px;
  background: linear-gradient(90deg, #a855f7, #06b6d4);
}
.card-inner {
  padding: 32px;
}

.detail-header {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-bottom: 16px;
}
.tag {
  font-size: 11px;
  padding: 3px 10px;
  border-radius: 6px;
  font-weight: 600;
  letter-spacing: 0.3px;
}
.tag.type-info { background: rgba(139,92,246,0.1); color: var(--accent-purple); }
.tag.type-update { background: var(--bg-hover); color: var(--accent-purple); }
.tag.type-maintenance { background: var(--bg-hover); color: var(--accent-purple); }
.tag.type-activity { background: rgba(6,182,212,0.08); color: var(--accent-cyan); }
.pin-badge { font-size: 11px; color: #f59e0b; font-weight: 600; }

.detail-title {
  font-family: 'Space Grotesk', sans-serif;
  font-size: 26px;
  font-weight: 700;
  color: #f8fafc;
  margin-bottom: 12px;
  line-height: 1.3;
}
.detail-meta {
  font-size: 13px;
  color: var(--text-dim);
  padding-bottom: 20px;
  border-bottom: 1px solid var(--border-default);
  margin-bottom: 24px;
}
.detail-content {
  font-size: 15px;
  line-height: 1.8;
  color: var(--text-secondary);
}
.detail-content :deep(strong) {
  color: var(--text-primary);
  font-weight: 600;
}

@media (max-width: 640px) {
  .container { padding: 20px 16px; }
  .card-inner { padding: 20px; }
  .detail-title { font-size: 22px; }
}
</style>
