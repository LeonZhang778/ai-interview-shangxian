<template>
  <StarryBackground />
  <div class="note-detail-page">
    <div v-if="loading" class="loading-state">加载中...</div>

    <div v-else-if="!note" class="empty-state">
      <p>笔记不存在或无权查看</p>
      <router-link to="/learning-notes" class="btn-back">返回笔记列表</router-link>
    </div>

    <div v-else class="main-container">
      <button class="back-btn" @click="goBack">← 返回</button>

      <!-- 标题区 -->
      <div class="note-header">
        <h1>{{ note.title }}</h1>
        <div class="note-meta">
          <span class="meta-tag" :class="`type-${note.note_type}`">{{ typeLabel(note.note_type) }}</span>
          <span v-if="note.source === 'interview'" class="meta-source">面试回流</span>
          <span v-if="note.status === 'draft'" class="meta-draft">草稿</span>
          <span class="meta-visibility">
            {{ note.visibility === 'private' ? '🔒 仅自己' : '🌐 公开' }}
          </span>
          <span class="meta-time">{{ formatTime(note.updated_at) }}</span>
        </div>
        <div class="note-tags" v-if="note.tags">
          <span v-for="(tag, i) in note.tags.split(',')" :key="i" class="tag">{{ tag.trim() }}</span>
        </div>
      </div>

      <!-- 游客提示 -->
      <div v-if="!note.is_owner && note.visibility === 'public'" class="guest-notice">
        🌐 公开笔记 · 无需登录即可阅读
      </div>

      <!-- 面试回流关联入口 -->
      <div v-if="note.interview_id && note.is_owner" class="interview-link">
        <router-link :to="`/report/${note.interview_id}`" class="link-text">
          📋 查看关联的 AI 面试报告 →
        </router-link>
      </div>

<!-- 正文 -->
      <div class="note-body">
        <Viewer :value="note.content" :plugins="plugins" />
      </div>

      <!-- 底部统计 -->
      <div class="note-footer">
        <div class="footer-stats">
          <span>👁 {{ note.view_count || 0 }}</span>
          <span>👍 {{ note.like_count || 0 }}</span>
        </div>
        <div v-if="note.is_owner" class="footer-actions">
          <button class="btn-edit" @click="goEdit">✏️ 编辑</button>
          <button class="btn-delete" @click="handleDelete">🗑️ 删除</button>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import StarryBackground from '../components/StarryBackground.vue'
import { Viewer } from '@bytemd/vue-next'
import gfm from '@bytemd/plugin-gfm'
import highlight from '@bytemd/plugin-highlight'
import 'bytemd/dist/index.css'
import 'highlight.js/styles/github-dark.css'
import { getNoteDetail, deleteNote } from '../api/learningNote'

const plugins = [
  gfm(),
  highlight(),
]

const route = useRoute()
const router = useRouter()

const note = ref(null)
const loading = ref(true)

const typeOptions = [
  { value: 'note', label: '笔记' },
  { value: 'review', label: '复盘' },
  { value: 'mistake', label: '错题' },
  { value: 'experience', label: '面经' },
  { value: 'material', label: '资料' },
]

function typeLabel(t) {
  const opt = typeOptions.find(o => o.value === t)
  return opt ? opt.label : t
}

function formatTime(t) {
  if (!t) return ''
  const d = new Date(t)
  return d.toLocaleString('zh-CN', { dateStyle: 'short', timeStyle: 'short' })
}

function goBack() {
  router.push('/learning-notes')
}

function goEdit() {
  router.push(`/learning-notes/edit/${note.value.id}`)
}

async function handleDelete() {
  if (!confirm('确定删除这篇笔记？此操作不可撤销。')) return
  try {
    await deleteNote(note.value.id)
    router.push('/learning-notes')
  } catch (e) {
    console.error(e)
    alert('删除失败，请重试')
  }
}

async function loadData() {
  loading.value = true
  try {
    note.value = await getNoteDetail(route.params.id)
  } catch (e) {
    console.error(e)
    note.value = null
  } finally {
    loading.value = false
  }
}

onMounted(loadData)
</script>

<style scoped>
.note-detail-page {
  min-height: 100vh;
  padding-bottom: 60px;
}
.loading-state {
  text-align: center;
  padding: 80px;
  color: var(--text-muted);
}
.empty-state {
  text-align: center;
  padding: 80px 20px;
  color: var(--text-muted);
}
.btn-back {
  display: inline-block;
  margin-top: 16px;
  padding: 10px 24px;
  background: linear-gradient(135deg, #6366f1, #8b5cf6);
  color: white;
  border-radius: 8px;
  text-decoration: none;
  font-size: 14px;
  font-weight: 600;
}
.main-container {
  max-width: 800px;
  margin: 0 auto;
  padding: 30px 20px;
}
.back-btn {
  background: none;
  border: 1px solid rgba(255,255,255,0.1);
  border-radius: 8px;
  color: var(--text-secondary);
  font-size: 13px;
  padding: 6px 14px;
  cursor: pointer;
  margin-bottom: 24px;
  transition: all 0.2s;
}
.back-btn:hover {
  background: rgba(99,102,241,0.1);
  border-color: rgba(99,102,241,0.3);
}

/* 标题区 */
.note-header {
  margin-bottom: 24px;
  padding-bottom: 20px;
  border-bottom: 1px solid rgba(255,255,255,0.08);
}
.note-header h1 {
  font-size: 26px;
  font-weight: 700;
  color: var(--text-primary);
  margin-bottom: 12px;
  line-height: 1.4;
}
.note-meta {
  display: flex;
  gap: 10px;
  flex-wrap: wrap;
  align-items: center;
  margin-bottom: 10px;
}
.meta-tag {
  font-size: 12px;
  padding: 2px 10px;
  border-radius: 4px;
  background: rgba(99,102,241,0.15);
  color: var(--accent-light);
}
.meta-source {
  font-size: 12px;
  padding: 2px 10px;
  border-radius: 4px;
  background: rgba(16,185,129,0.15);
  color: #10b981;
}
.meta-draft {
  font-size: 12px;
  padding: 2px 10px;
  border-radius: 4px;
  background: rgba(245,158,11,0.15);
  color: #f59e0b;
}
.meta-visibility {
  font-size: 13px;
  color: var(--text-muted);
}
.meta-time {
  font-size: 12px;
  color: var(--text-muted);
  margin-left: auto;
}
.note-tags {
  display: flex;
  gap: 6px;
  flex-wrap: wrap;
}
.tag {
  font-size: 12px;
  padding: 2px 10px;
  border-radius: 4px;
  background: rgba(255,255,255,0.06);
  color: var(--text-muted);
}

/* 面试回流关联 */
.guest-notice {
  margin-bottom: 20px;
  padding: 10px 16px;
  background: rgba(16,185,129,0.08);
  border: 1px solid rgba(16,185,129,0.2);
  border-radius: 10px;
  color: #10b981;
  font-size: 13px;
}
.interview-link {
  margin-bottom: 20px;
  padding: 12px 16px;
  background: rgba(99,102,241,0.08);
  border: 1px solid rgba(99,102,241,0.2);
  border-radius: 10px;
}
.link-text {
  color: var(--accent-light);
  text-decoration: none;
  font-size: 14px;
  font-weight: 500;
}
.link-text:hover {
  text-decoration: underline;
}

/* 正文 */
.note-body {
  font-size: 15px;
  line-height: 1.8;
  color: var(--text-secondary);
}
.note-body :deep(h1) {
  font-size: 22px;
  font-weight: 700;
  color: var(--text-primary);
  margin: 24px 0 12px;
}
.note-body :deep(h2) {
  font-size: 18px;
  font-weight: 600;
  color: var(--text-primary);
  margin: 20px 0 10px;
  padding-bottom: 6px;
  border-bottom: 1px solid rgba(255,255,255,0.08);
}
.note-body :deep(h3) {
  font-size: 16px;
  font-weight: 600;
  color: var(--text-primary);
  margin: 16px 0 8px;
}
.note-body :deep(p) {
  margin: 8px 0;
}
.note-body :deep(ul),
.note-body :deep(ol) {
  margin: 8px 0;
  padding-left: 24px;
}
.note-body :deep(li) {
  margin: 4px 0;
}
.note-body :deep(blockquote) {
  margin: 12px 0;
  padding: 8px 16px;
  background: rgba(99,102,241,0.06);
  border-left: 3px solid var(--accent-purple);
  border-radius: 0 8px 8px 0;
  color: var(--text-secondary);
}
.note-body :deep(code) {
  background: rgba(255,255,255,0.08);
  padding: 2px 6px;
  border-radius: 4px;
  font-size: 13px;
  font-family: 'Consolas', 'Monaco', monospace;
}
.note-body :deep(pre) {
  background: rgba(0,0,0,0.3);
  padding: 14px;
  border-radius: 8px;
  overflow-x: auto;
  margin: 12px 0;
}
.note-body :deep(pre code) {
  background: transparent;
  padding: 0;
}
.note-body :deep(strong) {
  font-weight: 600;
  color: var(--text-primary);
}
.note-body :deep(table) {
  width: 100%;
  border-collapse: collapse;
  margin: 12px 0;
}
.note-body :deep(th),
.note-body :deep(td) {
  border: 1px solid rgba(255,255,255,0.1);
  padding: 8px 12px;
  text-align: left;
}
.note-body :deep(th) {
  background: rgba(255,255,255,0.05);
  font-weight: 600;
}

/* 底部 */
.note-footer {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-top: 32px;
  padding-top: 20px;
  border-top: 1px solid rgba(255,255,255,0.08);
}
.footer-stats {
  display: flex;
  gap: 16px;
  font-size: 13px;
  color: var(--text-muted);
}
.footer-actions {
  display: flex;
  gap: 10px;
}
.btn-edit,
.btn-delete {
  padding: 6px 16px;
  background: rgba(255,255,255,0.06);
  border: 1px solid rgba(255,255,255,0.1);
  border-radius: 8px;
  color: var(--text-secondary);
  font-size: 13px;
  cursor: pointer;
  transition: all 0.2s;
}
.btn-edit:hover {
  background: rgba(99,102,241,0.15);
  border-color: rgba(99,102,241,0.3);
  color: var(--accent-light);
}
.btn-delete:hover {
  background: rgba(239,68,68,0.15);
  border-color: rgba(239,68,68,0.3);
  color: #ef4444;
}
</style>
