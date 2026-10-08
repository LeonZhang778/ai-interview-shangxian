<template>
  <StarryBackground />
  <div class="container">
    <div class="my-feedbacks-page">
      <div class="page-header">
        <h2>📋 我的反馈</h2>
        <p class="subtitle">查看你提交的反馈及管理员回复</p>
      </div>

      <div v-if="loading" class="loading-state">加载中...</div>

      <div v-else-if="feedbacks.length === 0" class="empty-state">
        <p class="empty-icon">📭</p>
        <p>暂无反馈记录</p>
        <p class="empty-hint">点击右下角 🐛 按钮提交反馈</p>
      </div>

      <div v-else class="feedback-list">
        <div v-for="item in feedbacks" :key="item.id" class="feedback-card">
          <div class="feedback-header">
            <span class="feedback-type" :class="'type-' + item.feedback_type">{{ typeLabel(item.feedback_type) }}</span>
            <span class="feedback-status" :class="'status-' + item.status">{{ statusLabel(item.status) }}</span>
          </div>
          <p class="feedback-content">{{ item.content }}</p>
          <div v-if="item.admin_reply" class="admin-reply">
            <div class="reply-label">💬 管理员回复</div>
            <p class="reply-content">{{ item.admin_reply }}</p>
          </div>
          <div class="feedback-meta">
            <span>{{ formatTime(item.created_at) }}</span>
            <span v-if="item.resolved_at"> · 处理于 {{ formatTime(item.resolved_at) }}</span>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import api from '../api/request'
import StarryBackground from '../components/StarryBackground.vue'

const feedbacks = ref([])
const loading = ref(true)

onMounted(async () => {
  try {
    const data = await api.get('/feedbacks/my')
    feedbacks.value = data.items || []
  } catch (e) {
    console.error('加载反馈列表失败:', e)
  } finally {
    loading.value = false
  }
})

function typeLabel(type) {
  const map = { bug: 'Bug', suggestion: '建议', other: '其他' }
  return map[type] || type
}

function statusLabel(status) {
  const map = { pending: '待处理', processing: '处理中', resolved: '已解决', ignored: '已忽略' }
  return map[status] || status
}

function formatTime(iso) {
  if (!iso) return ''
  const d = new Date(iso)
  return d.toLocaleString('zh-CN', { month: '2-digit', day: '2-digit', hour: '2-digit', minute: '2-digit' })
}
</script>

<style scoped>
.my-feedbacks-page {
  max-width: 640px;
  margin: 20px auto;
  padding: 0 16px;
}
.page-header { margin-bottom: 24px; }
.page-header h2 {
  margin: 0 0 4px;
  font-size: 20px;
  font-family: Inter, sans-serif;
  background:var(--title-gradient);

}
.subtitle { color: var(--text-muted); font-size: 13px; margin: 0; }

.loading-state { text-align: center; padding: 40px; color: var(--text-muted); }
.empty-state { text-align: center; padding: 60px 20px; color: var(--text-dim); }
.empty-icon { font-size: 48px; margin-bottom: 12px; }
.empty-hint { font-size: 12px; color: var(--text-dim); margin-top: 8px; }

.feedback-list { display: flex; flex-direction: column; gap: 12px; }

.feedback-card {
  background: var(--bg-card);
  border: 1px solid var(--border-default);
  border-radius: 8px;
  padding: 16px;
  transition: border-color 0.2s;
}
.feedback-card:hover { border-color: var(--border-hover); }

.feedback-header { display: flex; align-items: center; gap: 8px; margin-bottom: 10px; }
.feedback-type { font-size: 12px; font-weight: 600; padding: 2px 8px; border-radius: 6px; }
.type-bug { background: rgba(128, 128, 128,0.1); color: var(--red); }
.type-suggestion { background: rgba(128, 128, 128,0.1); color: var(--accent-purple); }
.type-other { background: var(--bg-hover); color: var(--accent-purple); }

.feedback-status { font-size: 12px; font-weight: 500; padding: 2px 8px; border-radius: 6px; }
.status-pending { background: rgba(128, 128, 128,0.1); color: var(--amber); }
.status-processing { background: rgba(128, 128, 128,0.1); color: var(--accent-purple); }
.status-resolved { background: rgba(128, 128, 128,0.1); color: var(--green); }
.status-ignored { background: var(--bg-card); color: var(--text-dim); }

.feedback-content {
  font-size: 14px;
  color: var(--text-secondary);
  line-height: 1.6;
  margin: 0 0 10px;
  white-space: pre-wrap;
  word-break: break-word;
}

.admin-reply {
  background: rgba(128, 128, 128,0.06);
  border: 1px solid rgba(128, 128, 128,0.12);
  border-radius: 8px;
  padding: 12px;
  margin-bottom: 10px;
}
.reply-label { font-size: 12px; font-weight: 600; color: var(--green); margin-bottom: 6px; }
.reply-content {
  font-size: 13px;
  color: #A3A3A3;
  line-height: 1.6;
  margin: 0;
  white-space: pre-wrap;
  word-break: break-word;
}

.feedback-meta { font-size: 12px; color: var(--text-dim); }
</style>
