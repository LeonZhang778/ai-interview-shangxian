<template>
  <div class="container">
    <div class="page-header">
      <h1>📢 公告中心</h1>
      <router-link to="/dashboard" class="back-link">← 返回</router-link>
    </div>

    <div v-if="loading" class="loading">加载中...</div>

    <div v-else-if="announcements.length === 0" class="empty card">
      <p style="font-size:48px;margin-bottom:12px">📭</p>
      <p>暂无公告</p>
    </div>

    <div v-else class="announcement-list">
      <div
        v-for="item in announcements"
        :key="item.id"
        class="card announcement-item"
        @click="$router.push(`/announcements/${item.id}`)"
      >
        <div class="item-header">
          <span class="tag" :class="`type-${item.type}`">{{ typeLabels[item.type] || '通知' }}</span>
          <span v-if="item.is_pinned" class="pin-badge">📌 置顶</span>
        </div>
        <h3 class="item-title">{{ item.title }}</h3>
        <p class="item-preview">{{ item.content.slice(0, 100) }}{{ item.content.length > 100 ? '...' : '' }}</p>
        <div class="item-footer">
          <span class="item-date">{{ formatDate(item.published_at) }}</span>
          <span class="read-more">查看详情 →</span>
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
.page-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin: 20px 0;
}
.page-header h1 { font-size: 22px; }
.back-link { color: #6b7280; font-size: 14px; text-decoration: none; }
.back-link:hover { color: #4f46e5; }

.loading, .empty { text-align: center; padding: 60px 20px; }

.announcement-list {
  display: flex;
  flex-direction: column;
  gap: 12px;
}
.announcement-item {
  cursor: pointer;
  transition: all 0.2s;
}
.announcement-item:hover {
  box-shadow: 0 4px 12px rgba(0,0,0,0.08);
  transform: translateY(-1px);
}
.item-header {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-bottom: 8px;
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
.pin-badge {
  font-size: 11px;
  color: #f59e0b;
  font-weight: 600;
}
.item-title {
  font-size: 16px;
  font-weight: 600;
  margin-bottom: 6px;
  color: #1f2937;
}
.item-preview {
  font-size: 14px;
  color: #6b7280;
  line-height: 1.5;
  margin-bottom: 8px;
}
.item-footer {
  display: flex;
  justify-content: space-between;
  align-items: center;
}
.item-date { font-size: 12px; color: #9ca3af; }
.read-more { font-size: 13px; color: #4f46e5; }
</style>
