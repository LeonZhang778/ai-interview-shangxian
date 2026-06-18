<template>
  <div class="container">
    <div class="page-header">
      <router-link to="/announcements" class="back-link">← 返回公告列表</router-link>
    </div>

    <div v-if="loading" class="loading">加载中...</div>

    <div v-else-if="!announcement" class="empty card">
      <p style="font-size:48px;margin-bottom:12px">😕</p>
      <p>公告不存在或已过期</p>
    </div>

    <div v-else class="card detail-card">
      <div class="detail-header">
        <span class="tag" :class="`type-${announcement.type}`">{{ typeLabels[announcement.type] || '通知' }}</span>
        <span v-if="announcement.is_pinned" class="pin-badge">📌 置顶</span>
      </div>
      <h1 class="detail-title">{{ announcement.title }}</h1>
      <div class="detail-meta">
        <span>发布时间：{{ formatDate(announcement.published_at) }}</span>
      </div>
      <div class="detail-content" v-html="renderContent(announcement.content)"></div>
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
.page-header {
  margin: 20px 0;
}
.back-link { color: #6b7280; font-size: 14px; text-decoration: none; }
.back-link:hover { color: #4f46e5; }

.loading, .empty { text-align: center; padding: 60px 20px; }

.detail-card {
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
  padding: 2px 8px;
  border-radius: 4px;
  font-weight: 600;
}
.tag.type-info { background: #dbeafe; color: #1e40af; }
.tag.type-update { background: #d1fae5; color: #065f46; }
.tag.type-maintenance { background: #fef3c7; color: #92400e; }
.tag.type-activity { background: #fce7f3; color: #9d174d; }
.pin-badge { font-size: 11px; color: #f59e0b; font-weight: 600; }

.detail-title {
  font-size: 24px;
  font-weight: 700;
  color: #1f2937;
  margin-bottom: 12px;
}
.detail-meta {
  font-size: 13px;
  color: #9ca3af;
  padding-bottom: 20px;
  border-bottom: 1px solid #e5e7eb;
  margin-bottom: 24px;
}
.detail-content {
  font-size: 15px;
  line-height: 1.8;
  color: #374151;
}
</style>
