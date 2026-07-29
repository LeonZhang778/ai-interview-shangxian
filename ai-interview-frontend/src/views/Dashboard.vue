<template>
  <StarryBackground />
  <div class="container">
    <div class="page-header">
      <h1>📋 面试记录</h1>
      <router-link to="/resume/upload" class="btn-primary" style="display:inline-block;padding:10px 24px;color:white;border-radius:8px">
        + 开始新面试
      </router-link>
    </div>

    <div v-if="authStore.isGuest" class="guest-hint" style="background:var(--bg-hover);border:1px solid var(--border-default);border-radius:10px;padding:12px 16px;margin-bottom:16px;font-size:13px;color:var(--accent-purple)">
      游客模式下数据临时保存，<router-link to="/register" style="color:var(--accent-primary);font-weight:600">注册账号</router-link>后永久保留
    </div>

    <!-- 快捷入口 -->
    <div class="quick-entries">
      <router-link to="/learning-notes" class="quick-entry-card">
        <span class="entry-icon">📝</span>
        <div class="entry-info">
          <span class="entry-title">学习笔记</span>
          <span class="entry-desc">复盘面试、记录错题</span>
        </div>
      </router-link>
      <router-link to="/collections" class="quick-entry-card">
        <span class="entry-icon">⭐</span>
        <div class="entry-info">
          <span class="entry-title">我的收藏</span>
          <span class="entry-desc">整理收藏的面经</span>
        </div>
      </router-link>
      <router-link to="/experiences" class="quick-entry-card">
        <span class="entry-icon">📚</span>
        <div class="entry-info">
          <span class="entry-title">面经广场</span>
          <span class="entry-desc">浏览真实面经</span>
        </div>
      </router-link>
    </div>

    <div v-if="loading" class="loading">加载中...</div>

    <div v-else-if="interviews.length === 0" class="empty card">
      <p style="font-size:48px;margin-bottom:12px">🎯</p>
      <p>还没有面试记录</p>
      <p style="color:var(--text-muted);font-size:14px;margin-top:8px">上传简历开始你的第一次 AI 模拟面试</p>
    </div>

    <div v-else class="interview-list">
      <div v-for="item in interviews" :key="item.interview_id" class="card interview-item">
        <div class="item-header">
          <span class="position">{{ item.target_position }}</span>
          <span :class="['status', item.status]">{{ item.status === 'completed' ? '已完成' : '进行中' }}</span>
        </div>
        <div class="item-meta">
          <span>难度：{{ difficultyMap[item.difficulty] || item.difficulty }}</span>
          <span>题数：{{ item.total_questions }}</span>
          <span v-if="item.overall_score">得分：{{ item.overall_score }}</span>
          <span>{{ formatDate(item.created_at) }}</span>
        </div>
        <div class="item-actions">
          <router-link v-if="item.status === 'in_progress'" :to="`/interview/${item.interview_id}`" class="btn-primary" style="padding:6px 16px;font-size:13px;color:white;display:inline-block;border-radius:6px">
            继续面试
          </router-link>
          <router-link v-else :to="`/interview/${item.interview_id}/report`" class="btn-secondary" style="padding:6px 16px;font-size:13px;display:inline-block;border-radius:6px">
            查看报告
          </router-link>
          <button class="btn-danger" style="padding:6px 16px;font-size:13px;border-radius:6px" @click="handleDelete(item.interview_id)">
            删除
          </button>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { getInterviews, deleteInterview } from '../api/interview'
import { useAuthStore } from '../stores/auth'
import StarryBackground from '../components/StarryBackground.vue'

const authStore = useAuthStore()

const interviews = ref([])
const loading = ref(true)
const difficultyMap = { easy: '简单', medium: '中等', hard: '困难' }

function formatDate(str) {
  if (!str) return ''
  return new Date(str).toLocaleString('zh-CN', { month: '2-digit', day: '2-digit', hour: '2-digit', minute: '2-digit' })
}

onMounted(async () => {
  try {
    const data = await getInterviews()
    interviews.value = data.items || []
  } catch (e) {
    console.error(e)
  } finally {
    loading.value = false
  }
})

async function handleDelete(interviewId) {
  if (!confirm('确定要删除这条面试记录吗？删除后无法恢复。')) return
  try {
    await deleteInterview(interviewId)
    interviews.value = interviews.value.filter(i => i.interview_id !== interviewId)
  } catch (e) {
    alert('删除失败: ' + e.message)
  }
}
</script>

<style scoped>
.page-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin: 20px 0;
}
.page-header h1 {
  font-family: 'Space Grotesk', sans-serif;
  font-size: 22px;
  background:var(--title-gradient);
  -webkit-background-clip: text;
  -webkit-text-fill-color: transparent;
}
.loading, .empty {
  text-align: center;
  padding: 60px 20px;
  color: var(--text-muted);
}

/* 快捷入口 */
.quick-entries {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 12px;
  margin-bottom: 24px;
}
.quick-entry-card {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 16px;
  background: rgba(255,255,255,0.04);
  border: 1px solid rgba(255,255,255,0.08);
  border-radius: 12px;
  text-decoration: none;
  transition: all 0.2s;
}
.quick-entry-card:hover {
  border-color: rgba(99,102,241,0.3);
  background: rgba(255,255,255,0.06);
  transform: translateY(-2px);
}
.entry-icon {
  font-size: 28px;
  flex-shrink: 0;
}
.entry-info {
  display: flex;
  flex-direction: column;
  gap: 2px;
  overflow: hidden;
}
.entry-title {
  font-size: 15px;
  font-weight: 600;
  color: var(--text-primary);
}
.entry-desc {
  font-size: 12px;
  color: var(--text-muted);
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
@media (max-width: 640px) {
  .quick-entries {
    grid-template-columns: 1fr;
  }
}
.interview-list {
  display: flex;
  flex-direction: column;
  gap: 12px;
}
.interview-item {
  display: flex;
  flex-direction: column;
  gap: 10px;
  transition: all 0.2s;
}
.interview-item:hover {
  border-color: var(--border-hover);
  transform: translateY(-1px);
}
.item-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}
.position {
  font-weight: 600;
  font-size: 16px;
  color: var(--text-primary);
}
.status {
  font-size: 12px;
  padding: 3px 10px;
  border-radius: 12px;
}
.status.completed {
  background: rgba(16,185,129,0.1);
  color: var(--green);
}
.status.in_progress {
  background: rgba(245,158,11,0.1);
  color: var(--amber);
}
.item-meta {
  display: flex;
  gap: 16px;
  font-size: 13px;
  color: var(--text-muted);
}
.item-actions {
  display: flex;
  gap: 8px;
}
.btn-danger {
  background: rgba(239,68,68,0.1);
  color: var(--red);
  border: 1px solid rgba(239,68,68,0.15);
}
.btn-danger:hover {
  background: rgba(239,68,68,0.2);
  border-color: rgba(239,68,68,0.3);
}
</style>
