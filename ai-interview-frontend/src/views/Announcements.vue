<template>
  <StarryBackground />
  <div class="announcements-page">
    <div class="container">
      <div class="page-header">
        <h1>公告中心</h1>
        <router-link to="/dashboard" class="back-link"><BaseIcon name="chevron-left" :size="16" /> 返回</router-link>
      </div>

      <div v-if="loading" class="loading">
        <div class="loading-spinner"></div>
        <span>加载中...</span>
      </div>

      <div v-else-if="announcements.length === 0" class="empty-state">
        <div class="empty-icon"><BaseIcon name="inbox" :size="40" /></div>
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
              <span v-if="item.is_pinned" class="pin-badge"><BaseIcon name="pin" :size="13" /> 置顶</span>
            </div>
            <h3 class="item-title">{{ item.title }}</h3>
            <p class="item-preview">{{ stripMarkdown(item.content).slice(0, 100) }}{{ stripMarkdown(item.content).length > 100 ? '...' : '' }}</p>
            <div class="item-footer">
              <span class="item-date">{{ formatDate(item.published_at) }}</span>
              <span class="read-more">查看详情 <BaseIcon name="arrow-right" :size="14" /></span>
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
import StarryBackground from '../components/StarryBackground.vue'
import BaseIcon from '../components/BaseIcon.vue'
import { stripMarkdown } from '../utils/text'

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
  color: var(--text-primary);
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
  font-family: Inter, sans-serif;
  font-size: 24px;
  font-weight: 700;
  background:var(--title-gradient);

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
  border: 3px solid rgba(128, 128, 128,0.15);
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

/* 列表 */
.announcement-list {
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.announcement-card {
  background: rgba(128, 128, 128, 0.04);
  border: 1px solid rgba(128, 128, 128, 0.1);
  border-radius: 8px;
  overflow: hidden;
  cursor: pointer;
  transition: all 0.3s;
  position: relative;
}
.announcement-card:hover {
  border-color: rgba(128, 128, 128, 0.25);
  background: rgba(128, 128, 128, 0.07);
  transform: translateY(-2px);
  box-shadow: var(--shadow-sm);
}
.card-top-line {
  height: 2px;
  background: var(--accent-primary);
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
.tag.type-info { background: rgba(128, 128, 128,0.1); color: var(--accent-purple); }
.tag.type-update { background: var(--bg-hover); color: var(--accent-purple); }
.tag.type-maintenance { background: var(--bg-hover); color: var(--accent-purple); }
.tag.type-activity { background: rgba(128, 128, 128,0.08); color: var(--accent-cyan); }
.pin-badge {
  font-size: 11px;
  color: #A3A3A3;
  font-weight: 600;
}
.item-title {
  font-family: Inter, sans-serif;
  font-size: 17px;
  font-weight: 600;
  margin-bottom: 8px;
  color: var(--text-primary);
}
.item-preview {
  font-size: 14px;
  color: var(--text-muted);
  line-height: 1.6;
  margin-bottom: 12px;
}
.item-footer {
  display: flex;
  justify-content: space-between;
  align-items: center;
}
.item-date { font-size: 12px; color: var(--text-dim); }
.read-more { font-size: 13px; color: var(--accent-primary); transition: color 0.2s; }
.announcement-card:hover .read-more { color: var(--accent-light); }

@media (max-width: 640px) {
  .container { padding: 20px 16px; }
  .card-inner { padding: 16px; }
}
</style>
