<template>
  <StarryBackground />
  <div class="notifications-page">
    <div class="page-header">
      <h1>消息通知</h1>
      <button v-if="notifications.length > 0" class="btn-mark-all" @click="handleMarkAllRead">
        全部已读
      </button>
    </div>

    <div v-if="loading" class="loading-state">加载中...</div>
    <div v-else-if="notifications.length === 0" class="empty-state">
      <div class="empty-icon"><BaseIcon name="bell" :size="40" /></div>
      <p>暂无通知</p>
    </div>

    <div v-else class="notification-list">
      <div
        v-for="n in notifications"
        :key="n.id"
        class="notification-item"
        :class="{ unread: !n.is_read }"
        @click="handleClick(n)"
      >
        <div class="notification-icon">
          <BaseIcon v-if="n.type === 'interview'" name="target" :size="18" />
          <BaseIcon v-else-if="n.type === 'experience'" name="file-text" :size="18" />
          <BaseIcon v-else name="bell" :size="18" />
        </div>
        <div class="notification-body">
          <div class="notification-title">{{ n.title }}</div>
          <div v-if="n.content" class="notification-content">{{ n.content }}</div>
          <div class="notification-time">{{ formatTime(n.created_at) }}</div>
        </div>
        <div class="notification-actions">
          <span v-if="!n.is_read" class="unread-dot"></span>
          <button class="btn-delete" aria-label="删除通知" @click.stop="handleDelete(n.id)" title="删除"><BaseIcon name="x" :size="14" /></button>
        </div>
      </div>
    </div>

    <div v-if="total > page * size" class="load-more">
      <button class="btn-sm" @click="loadMore">加载更多</button>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { getNotifications, markRead, markAllRead, deleteNotification } from '../api/notification'
import StarryBackground from '../components/StarryBackground.vue'
import BaseIcon from '../components/BaseIcon.vue'

const router = useRouter()
const notifications = ref([])
const loading = ref(true)
const page = ref(1)
const size = 20
const total = ref(0)

async function loadNotifications(p = 1) {
  loading.value = true
  try {
    const data = await getNotifications({ page: p, size })
    if (p === 1) {
      notifications.value = data.items
    } else {
      notifications.value = [...notifications.value, ...data.items]
    }
    total.value = data.total
    page.value = p
  } catch (e) {
    console.error('加载通知失败:', e)
  } finally {
    loading.value = false
  }
}

function loadMore() {
  loadNotifications(page.value + 1)
}

async function handleClick(n) {
  if (!n.is_read) {
    try {
      await markRead(n.id)
      n.is_read = true
      window.dispatchEvent(new Event('notifications-updated'))
    } catch (e) { /* ignore */ }
  }
  if (n.related_type === 'interview' && n.related_id) {
    router.push(`/interview/${n.related_id}/report`)
  } else if (n.related_type === 'experience' && n.related_id) {
    router.push(`/experiences/${n.related_id}`)
  }
}

async function handleMarkAllRead() {
  try {
    await markAllRead()
    notifications.value.forEach(n => { n.is_read = true })
    window.dispatchEvent(new Event('notifications-updated'))
  } catch (e) {
    console.error('标记全部已读失败:', e)
  }
}

async function handleDelete(id) {
  try {
    await deleteNotification(id)
    notifications.value = notifications.value.filter(n => n.id !== id)
    total.value--
    window.dispatchEvent(new Event('notifications-updated'))
  } catch (e) {
    console.error('删除通知失败:', e)
  }
}

function formatTime(str) {
  if (!str) return ''
  const d = new Date(str)
  const now = new Date()
  const diff = now - d
  if (diff < 60000) return '刚刚'
  if (diff < 3600000) return Math.floor(diff / 60000) + '分钟前'
  if (diff < 86400000) return Math.floor(diff / 3600000) + '小时前'
  if (diff < 604800000) return Math.floor(diff / 86400000) + '天前'
  return d.toLocaleDateString('zh-CN', { month: '2-digit', day: '2-digit' })
}

onMounted(() => {
  loadNotifications()
})
</script>

<style scoped>
.notifications-page {
  max-width: 700px;
  margin: 0 auto;
  padding: 24px 20px;
  min-height: 100vh;
}
.page-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 20px;
}
.page-header h1 {
  font-family: Inter, sans-serif;
  font-size: 24px;
  font-weight: 700;
  color: var(--text-primary);
  margin: 0;
}
.btn-mark-all {
  padding: 6px 14px;
  font-size: 13px;
  background: var(--bg-hover);
  color: var(--accent-purple);
  border: 1px solid var(--border-default);
  border-radius: 6px;
  cursor: pointer;
  transition: all 0.2s;
}
.btn-mark-all:hover {
  border-color: rgba(128, 128, 128,0.3);
  background: rgba(128, 128, 128,0.12);
}
.loading-state, .empty-state {
  text-align: center;
  padding: 60px 20px;
  color: var(--text-dim);
  font-size: 15px;
}
.empty-icon { font-size: 48px; margin-bottom: 12px; }
.empty-state p { margin: 0; }
.notification-list { display: flex; flex-direction: column; gap: 8px; }
.notification-item {
  display: flex;
  align-items: flex-start;
  gap: 12px;
  padding: 14px 16px;
  background: var(--bg-card);
  border: 1px solid var(--border-default);
  border-radius: 8px;
  cursor: pointer;
  transition: all 0.2s;
}
.notification-item:hover {
  border-color: var(--border-hover);
  background: rgba(128, 128, 128,0.04);
}
.notification-item.unread {
  border-left: 3px solid var(--accent-primary);
  background: rgba(128, 128, 128,0.06);
}
.notification-icon {
  font-size: 20px;
  flex-shrink: 0;
  width: 36px;
  height: 36px;
  display: flex;
  align-items: center;
  justify-content: center;
  background: var(--bg-hover);
  border-radius: 8px;
}
.notification-body { flex: 1; min-width: 0; }
.notification-title {
  font-size: 14px;
  font-weight: 600;
  color: var(--text-primary);
  margin-bottom: 4px;
  line-height: 1.4;
}
.notification-content {
  font-size: 13px;
  color: var(--text-secondary);
  margin-bottom: 4px;
  line-height: 1.4;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.notification-time {
  font-size: 12px;
  color: var(--text-dim);
}
.notification-actions {
  display: flex;
  align-items: center;
  gap: 8px;
  flex-shrink: 0;
}
.unread-dot {
  width: 8px;
  height: 8px;
  border-radius: 50%;
  background: var(--accent-primary);
}
.btn-delete {
  width: 28px;
  height: 28px;
  display: flex;
  align-items: center;
  justify-content: center;
  background: none;
  border: none;
  color: var(--text-dim);
  font-size: 18px;
  cursor: pointer;
  border-radius: 6px;
  transition: all 0.2s;
}
.btn-delete:hover {
  background: rgba(128, 128, 128,0.1);
  color: var(--red);
}
.load-more { text-align: center; padding: 16px 0; }
.btn-sm {
  padding: 8px 20px;
  font-size: 13px;
  border-radius: 6px;
  border: 1px solid var(--border-default);
  background: var(--bg-hover);
  color: var(--accent-purple);
  cursor: pointer;
}
.btn-sm:hover { border-color: rgba(128, 128, 128,0.3); background: rgba(128, 128, 128,0.12); }
</style>
