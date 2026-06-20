<template>
  <div class="announcements-page">
    <div class="container">
      <div class="page-header">
        <h1>公告中心</h1>
        <router-link to="/dashboard" class="back-link">&larr; 返回</router-link>
      </div>

      <div v-if="loading" class="loading">
        <div class="loading-spinner"></div>
        <span>加载中...</span>
      </div>

      <div v-else-if="announcements.length === 0" class="empty-state">
        <div class="empty-icon">&#x1F4ED;</div>
        <p>暂无公告</p>
      </div>

      <div v-else class="announcement-list">
        <div
          v-for="item in announcements"
          :key="item.id"
          class="announcement-card"
          @click="$router.push(`/announcements/${item.id}`)"
        >
          <div class="card-top-line"></div>
          <div class="card-inner">
            <div class="item-header">
              <span class="tag" :class="`type-${item.type}`">{{ typeLabels[item.type] || '通知' }}</span>
              <span v-if="item.is_pinned" class="pin-badge">&#x1F4CC; 置顶</span>
            </div>
            <h3 class="item-title">{{ item.title }}</h3>
            <p class="item-preview">{{ item.content.slice(0, 100) }}{{ item.content.length > 100 ? '...' : '' }}</p>
            <div class="item-footer">
              <span class="item-date">{{ formatDate(item.published_at) }}</span>
              <span class="read-more">查看详情 &rarr;</span>
            </div>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { getAnnouncements } from '../api/announcement'

const announcements = ref([])
const loading = ref(true)
const typeLabels = { info: '通知', update: '更新', maintenance: '维护', activity: '活动' }

function formatDate(str) {
  if (!str) return ''
  return new Date(str).toLocaleString('zh-CN', { year: 'numeric', month: '2-digit', day: '2-digit' })
}

onMounted(async () => {
  try {
    const data = await getAnnouncements({ page: 1, size: 50 })
    announcements.value = data.items || []
  } catch (e) {
    console.error(e)
  } finally {
    loading.value = false
  }
})
</script>

<style scoped>
.announcements-page {
  min-height: 100vh;
  background: #0a0a1a;
  color: #e2e8f0;
}

.container {
  max-width: 800px;
  margin: 0 auto;
  padding: 32px 20px;
}

.page-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 28px;
}
.page-header h1 {
  font-family: 'Space Grotesk', sans-serif;
  font-size: 24px;
  font-weight: 700;
  background: linear-gradient(135deg, #fff, #c4b5fd);
  -webkit-background-clip: text;
  -webkit-text-fill-color: transparent;
}
.back-link {
  color: #6b7280;
  font-size: 14px;
  text-decoration: none;
  transition: color 0.2s;
}
.back-link:hover { color: #a855f7; }

/* 加载 */
.loading {
  text-align: center;
  padding: 80px 20px;
  color: #6b7280;
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 16px;
}
.loading-spinner {
  width: 32px; height: 32px;
  border: 3px solid rgba(139,92,246,0.15);
  border-top-color: #a855f7;
  border-radius: 50%;
  animation: spin 0.8s linear infinite;
}
@keyframes spin { to { transform: rotate(360deg); } }

/* 空状态 */
.empty-state {
  text-align: center;
  padding: 80px 20px;
  color: #4a4a6a;
}
.empty-icon {
  font-size: 48px;
  margin-bottom: 12px;
}

/* 列表 */
.announcement-list {
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.announcement-card {
  background: rgba(139, 92, 246, 0.04);
  border: 1px solid rgba(139, 92, 246, 0.1);
  border-radius: 16px;
  overflow: hidden;
  cursor: pointer;
  transition: all 0.3s;
  position: relative;
}
.announcement-card:hover {
  border-color: rgba(139, 92, 246, 0.25);
  background: rgba(139, 92, 246, 0.07);
  transform: translateY(-2px);
  box-shadow: 0 8px 32px rgba(139, 92, 246, 0.1);
}
.card-top-line {
  height: 2px;
  background: linear-gradient(90deg, #a855f7, #06b6d4);
  opacity: 0;
  transition: opacity 0.3s;
}
.announcement-card:hover .card-top-line { opacity: 1; }
.card-inner {
  padding: 20px 24px;
}

.item-header {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-bottom: 10px;
}
.tag {
  font-size: 11px;
  padding: 3px 10px;
  border-radius: 6px;
  font-weight: 600;
  letter-spacing: 0.3px;
}
.tag.type-info { background: rgba(59,130,246,0.12); color: #60a5fa; }
.tag.type-update { background: rgba(16,185,129,0.12); color: #34d399; }
.tag.type-maintenance { background: rgba(245,158,11,0.12); color: #fbbf24; }
.tag.type-activity { background: rgba(236,72,153,0.12); color: #f472b6; }
.pin-badge {
  font-size: 11px;
  color: #f59e0b;
  font-weight: 600;
}
.item-title {
  font-family: 'Space Grotesk', sans-serif;
  font-size: 17px;
  font-weight: 600;
  margin-bottom: 8px;
  color: #f1f5f9;
}
.item-preview {
  font-size: 14px;
  color: #6b7280;
  line-height: 1.6;
  margin-bottom: 12px;
}
.item-footer {
  display: flex;
  justify-content: space-between;
  align-items: center;
}
.item-date { font-size: 12px; color: #4a4a6a; }
.read-more { font-size: 13px; color: #a855f7; transition: color 0.2s; }
.announcement-card:hover .read-more { color: #c4b5fd; }

@media (max-width: 640px) {
  .container { padding: 20px 16px; }
  .card-inner { padding: 16px; }
}
</style>
