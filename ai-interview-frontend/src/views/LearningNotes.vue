<template>
  <StarryBackground />
  <div class="learning-notes-page">
    <div class="page-header">
      <h1>学习笔记</h1>
      <p class="header-desc">沉淀面试知识，记录薄弱点，复盘每一次成长</p>
    </div>

    <div class="main-container">
      <!-- 模式切换 -->
      <div class="mode-tabs">
        <span
          v-if="authStore.isLoggedIn"
          class="mode-tab"
          :class="{ active: mode === 'my' }"
          @click="switchMode('my')"
        >
          我的笔记
        </span>
        <span
          class="mode-tab"
          :class="{ active: mode === 'public' }"
          @click="switchMode('public')"
        >
          公开广场
        </span>
        <span v-if="authStore.isLoggedIn" class="mode-tab mode-add" @click="goCreate">
          + 新建笔记
        </span>
      </div>

      <div class="content-layout" v-if="mode === 'my'">
        <!-- 左侧：笔记本树 -->
        <aside class="sidebar">
          <div class="sidebar-header">
            <h3>📒 笔记本</h3>
            <button class="btn-add-nb" @click="showAddNotebook = true" title="新建笔记本">+</button>
          </div>
          <div class="notebook-tree" v-if="notebookTree.length > 0">
            <div
              class="node-row all-notes"
              :class="{ active: activeNotebookId === null }"
              @click="selectNotebook(null)"
            >
              <span class="node-icon">📋</span>
              <span class="node-name">全部笔记</span>
            </div>
            <NotebookTreeNode
              v-for="nb in notebookTree"
              :key="nb.id"
              :node="nb"
              :active-id="activeNotebookId"
              @select="selectNotebook"
              @add-child="handleAddChild"
              @rename="handleRename"
              @delete="handleDelete"
              @refresh="loadNotebooks"
            />
          </div>
          <div v-else class="sidebar-empty">
            <p>还没有笔记本</p>
          </div>

          <!-- 新建笔记本表单 -->
          <div v-if="showAddNotebook" class="add-notebook-form">
            <input
              v-model="newNotebookName"
              placeholder="笔记本名称"
              @keyup.enter="createNotebook"
              @blur="cancelAddNotebook"
              ref="addNbInput"
              autofocus
            />
          </div>
        </aside>

        <!-- 右侧：笔记列表 -->
        <main class="notes-content">
          <!-- 类型筛选 + 统计 -->
          <div class="filter-bar">
            <div class="type-tabs">
              <span
                class="type-tab"
                :class="{ active: filterType === null }"
                @click="switchType(null)"
              >全部<span class="type-count">{{ stats.total || 0 }}</span></span>
              <span
                v-for="t in typeOptions"
                :key="t.value"
                class="type-tab"
                :class="{ active: filterType === t.value }"
                @click="switchType(t.value)"
              >{{ t.label }}<span class="type-count">{{ stats.by_type?.[t.value] || 0 }}</span></span>
            </div>
            <div class="status-tabs">
              <span
                class="status-tab"
                :class="{ active: filterStatus === null }"
                @click="switchStatus(null)"
              >全部状态</span>
              <span
                class="status-tab"
                :class="{ active: filterStatus === 'draft' }"
                @click="switchStatus('draft')"
              >草稿</span>
              <span
                class="status-tab"
                :class="{ active: filterStatus === 'published' }"
                @click="switchStatus('published')"
              >已发布</span>
            </div>
          </div>

          <!-- 列表 -->
          <div v-if="loading" class="loading-state">加载中...</div>

          <div v-else-if="notes.length === 0" class="empty-state">
            <div class="empty-icon">📝</div>
            <p>还没有学习笔记，去创建第一篇吧</p>
            <router-link to="/learning-notes/edit" class="btn-browse">新建笔记</router-link>
          </div>

          <div v-else class="notes-grid">
            <div
              v-for="note in notes"
              :key="note.id"
              class="note-card"
              @click="goDetail(note.id)"
            >
              <div class="card-top">
                <div class="card-title-row">
                  <span class="card-title">{{ note.title }}</span>
                  <span v-if="note.status === 'draft'" class="card-badge draft">草稿</span>
                  <span v-if="note.source === 'interview'" class="card-badge source">面试回流</span>
                </div>
                <div class="card-meta">
                  <span class="meta-type" :class="`type-${note.note_type}`">
                    {{ typeLabel(note.note_type) }}
                  </span>
                  <span v-if="note.visibility === 'private'" class="meta-private">🔒 私密</span>
                  <span v-if="note.visibility === 'public'" class="meta-public">🌐 公开</span>
                </div>
                <div class="card-tags" v-if="note.tags">
                  <span v-for="(tag, i) in note.tags.split(',').slice(0, 4)" :key="i" class="tag">{{ tag.trim() }}</span>
                </div>
              </div>
              <div class="card-bottom">
                <div class="card-stats">
                  <span>👁 {{ note.view_count || 0 }}</span>
                  <span>👍 {{ note.like_count || 0 }}</span>
                </div>
                <span class="card-time">{{ formatTime(note.updated_at || note.created_at) }}</span>
              </div>
            </div>
          </div>

          <!-- 分页 -->
          <div v-if="totalPages > 1" class="pagination">
            <button
              class="page-btn"
              :disabled="currentPage <= 1"
              @click="changePage(currentPage - 1)"
            >上一页</button>
            <span class="page-info">{{ currentPage }} / {{ totalPages }}</span>
            <button
              class="page-btn"
              :disabled="currentPage >= totalPages"
              @click="changePage(currentPage + 1)"
            >下一页</button>
          </div>
        </main>
      </div>

      <!-- 公开广场（无侧边栏） -->
      <div v-else-if="mode === 'public'" class="content-layout public-only">
        <main class="notes-content">
          <div class="filter-bar">
            <input
              v-model="keyword"
              class="search-input"
              placeholder="搜索笔记标题..."
              @keyup.enter="loadData"
            />
            <div class="status-tabs">
              <span
                class="status-tab"
                :class="{ active: sort === 'latest' }"
                @click="switchSort('latest')"
              >最新</span>
              <span
                class="status-tab"
                :class="{ active: sort === 'popular' }"
                @click="switchSort('popular')"
              >热门</span>
            </div>
          </div>

          <div v-if="loading" class="loading-state">加载中...</div>

          <div v-else-if="notes.length === 0" class="empty-state">
            <div class="empty-icon">🌌</div>
            <p>公开广场还没有笔记</p>
            <router-link v-if="!authStore.isLoggedIn" to="/login" class="btn-browse">登录后创建笔记</router-link>
          </div>

          <div v-else class="notes-grid">
            <div
              v-for="note in notes"
              :key="note.id"
              class="note-card"
              @click="goDetail(note.id)"
            >
              <div class="card-top">
                <div class="card-title-row">
                  <span class="card-title">{{ note.title }}</span>
                </div>
                <div class="card-meta">
                  <span class="meta-type" :class="`type-${note.note_type}`">
                    {{ typeLabel(note.note_type) }}
                  </span>
                </div>
                <div class="card-tags" v-if="note.tags">
                  <span v-for="(tag, i) in note.tags.split(',').slice(0, 4)" :key="i" class="tag">{{ tag.trim() }}</span>
                </div>
              </div>
              <div class="card-bottom">
                <div class="card-stats">
                  <span>👁 {{ note.view_count || 0 }}</span>
                  <span>👍 {{ note.like_count || 0 }}</span>
                </div>
                <span class="card-time">{{ formatTime(note.created_at) }}</span>
              </div>
            </div>
          </div>

          <div v-if="totalPages > 1" class="pagination">
            <button
              class="page-btn"
              :disabled="currentPage <= 1"
              @click="changePage(currentPage - 1)"
            >上一页</button>
            <span class="page-info">{{ currentPage }} / {{ totalPages }}</span>
            <button
              class="page-btn"
              :disabled="currentPage >= totalPages"
              @click="changePage(currentPage + 1)"
            >下一页</button>
          </div>
        </main>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, nextTick } from 'vue'
import { useRouter } from 'vue-router'
import StarryBackground from '../components/StarryBackground.vue'
import NotebookTreeNode from '../components/NotebookTreeNode.vue'
import { useAuthStore } from '../stores/auth'
import {
  getMyNotes, getPublicNotes, getNoteStats,
  getNotebooks, createNotebook as createNotebookApi, updateNotebook, deleteNotebook,
} from '../api/learningNote'

const router = useRouter()
const authStore = useAuthStore()

const mode = ref(authStore.isLoggedIn ? 'my' : 'public')
const filterType = ref(null)
const filterStatus = ref(null)
const keyword = ref('')
const sort = ref('latest')
const currentPage = ref(1)
const pageSize = 20

const notes = ref([])
const total = ref(0)
const stats = ref({})
const loading = ref(true)

// 笔记本状态
const notebookTree = ref([])
const activeNotebookId = ref(null)
const showAddNotebook = ref(false)
const newNotebookName = ref('')
const addNbInput = ref(null)

const typeOptions = [
  { value: 'note', label: '笔记' },
  { value: 'review', label: '复盘' },
  { value: 'mistake', label: '错题' },
  { value: 'experience', label: '面经' },
  { value: 'material', label: '资料' },
]

const totalPages = computed(() => Math.max(1, Math.ceil(total.value / pageSize)))

function typeLabel(t) {
  const opt = typeOptions.find(o => o.value === t)
  return opt ? opt.label : t
}

function switchMode(m) {
  if (mode.value === m) return
  mode.value = m
  currentPage.value = 1
  activeNotebookId.value = null
  loadData()
}

function switchType(t) {
  filterType.value = t
  currentPage.value = 1
  loadData()
}

function switchStatus(s) {
  filterStatus.value = s
  currentPage.value = 1
  loadData()
}

function switchSort(s) {
  sort.value = s
  currentPage.value = 1
  loadData()
}

function changePage(page) {
  currentPage.value = page
  loadData()
}

function goCreate() {
  if (!authStore.isLoggedIn) {
    router.push('/login')
    return
  }
  router.push('/learning-notes/edit')
}

function goDetail(id) {
  router.push(`/learning-notes/${id}`)
}

function formatTime(t) {
  if (!t) return ''
  const d = new Date(t)
  const now = new Date()
  const diff = (now - d) / 1000
  if (diff < 60) return '刚刚'
  if (diff < 3600) return `${Math.floor(diff / 60)}分钟前`
  if (diff < 86400) return `${Math.floor(diff / 3600)}小时前`
  if (diff < 2592000) return `${Math.floor(diff / 86400)}天前`
  return d.toLocaleDateString()
}

// ====== 笔记本操作 ======

function selectNotebook(id) {
  activeNotebookId.value = id
  currentPage.value = 1
  loadData()
}

async function loadNotebooks() {
  try {
    const res = await getNotebooks()
    notebookTree.value = res.tree || []
  } catch (e) {
    console.error('加载笔记本失败', e)
  }
}

async function createNotebook() {
  const name = newNotebookName.value.trim()
  if (!name) {
    showAddNotebook.value = false
    return
  }
  try {
    await createNotebookApi({ name })
    newNotebookName.value = ''
    showAddNotebook.value = false
    await loadNotebooks()
  } catch (e) {
    console.error('创建笔记本失败', e)
  }
}

function cancelAddNotebook() {
  showAddNotebook.value = false
  newNotebookName.value = ''
}

async function handleAddChild({ parentId, name }) {
  try {
    await createNotebookApi({ name, parent_id: parentId })
    await loadNotebooks()
  } catch (e) {
    console.error('创建子笔记本失败', e)
  }
}

async function handleRename({ id, name }) {
  try {
    await updateNotebook(id, { name })
    await loadNotebooks()
  } catch (e) {
    console.error('重命名失败', e)
  }
}

async function handleDelete(id) {
  try {
    await deleteNotebook(id)
    if (activeNotebookId.value === id) {
      activeNotebookId.value = null
    }
    await loadNotebooks()
    await loadData()
  } catch (e) {
    console.error('删除笔记本失败', e)
  }
}

// ====== 数据加载 ======

async function loadData() {
  loading.value = true
  try {
    if (mode.value === 'my') {
      const params = { page: currentPage.value, size: pageSize }
      if (filterType.value) params.note_type = filterType.value
      if (filterStatus.value) params.status = filterStatus.value
      if (activeNotebookId.value !== null) params.notebook_id = activeNotebookId.value
      const res = await getMyNotes(params)
      notes.value = res.items || []
      total.value = res.total || 0
      loadStats()
    } else {
      const params = { page: currentPage.value, size: pageSize, sort: sort.value }
      if (keyword.value.trim()) params.keyword = keyword.value.trim()
      const res = await getPublicNotes(params)
      notes.value = res.items || []
      total.value = res.total || 0
    }
  } catch (e) {
    console.error(e)
  } finally {
    loading.value = false
  }
}

async function loadStats() {
  try {
    stats.value = await getNoteStats()
  } catch (e) {
    console.error(e)
  }
}

onMounted(async () => {
  if (authStore.isLoggedIn) {
    await loadNotebooks()
  }
  await loadData()
})
</script>

<style scoped>
.learning-notes-page {
  min-height: 100vh;
  padding-bottom: 60px;
}
.page-header {
  text-align: center;
  padding: 40px 20px 20px;
}
.page-header h1 {
  font-size: 28px;
  font-weight: 700;
  background: linear-gradient(135deg, #a78bfa, #60a5fa);
  -webkit-background-clip: text;
  -webkit-text-fill-color: transparent;
  background-clip: text;
  margin-bottom: 8px;
}
.header-desc {
  font-size: 14px;
  color: var(--text-muted);
}
.main-container {
  max-width: 1100px;
  margin: 0 auto;
  padding: 0 20px;
}

/* 模式切换 */
.mode-tabs {
  display: flex;
  gap: 8px;
  margin-bottom: 20px;
  flex-wrap: wrap;
}
.mode-tab {
  padding: 8px 18px;
  border-radius: 20px;
  font-size: 14px;
  color: var(--text-muted);
  background: rgba(255,255,255,0.05);
  border: 1px solid rgba(255,255,255,0.08);
  cursor: pointer;
  transition: all 0.2s;
}
.mode-tab:hover {
  background: rgba(99,102,241,0.1);
  border-color: rgba(99,102,241,0.3);
}
.mode-tab.active {
  background: linear-gradient(135deg, rgba(99,102,241,0.2), rgba(139,92,246,0.2));
  border-color: rgba(99,102,241,0.5);
  color: var(--accent-light);
}
.mode-add {
  border-style: dashed;
  margin-left: auto;
}

/* 双栏布局 */
.content-layout {
  display: flex;
  gap: 24px;
  align-items: flex-start;
}
.content-layout.public-only {
  display: block;
  max-width: 800px;
  margin: 0 auto;
}

/* 侧边栏 */
.sidebar {
  width: 240px;
  flex-shrink: 0;
  background: rgba(255,255,255,0.03);
  border: 1px solid rgba(255,255,255,0.06);
  border-radius: 12px;
  padding: 12px;
  position: sticky;
  top: 20px;
}
.sidebar-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 8px;
  padding-bottom: 8px;
  border-bottom: 1px solid rgba(255,255,255,0.06);
}
.sidebar-header h3 {
  font-size: 14px;
  font-weight: 600;
  color: var(--text-primary);
}
.btn-add-nb {
  width: 24px;
  height: 24px;
  display: flex;
  align-items: center;
  justify-content: center;
  background: rgba(99,102,241,0.12);
  border: 1px solid rgba(99,102,241,0.25);
  border-radius: 6px;
  color: var(--accent-light);
  font-size: 16px;
  cursor: pointer;
  transition: all 0.2s;
}
.btn-add-nb:hover {
  background: rgba(99,102,241,0.2);
}
.sidebar-empty {
  padding: 20px 0;
  text-align: center;
  color: var(--text-muted);
  font-size: 13px;
}
.notebook-tree {
  max-height: calc(100vh - 280px);
  overflow-y: auto;
}
.node-row.all-notes {
  display: flex;
  align-items: center;
  gap: 4px;
  padding: 6px 8px;
  border-radius: 6px;
  cursor: pointer;
  font-size: 13px;
  color: var(--text-secondary);
  margin-bottom: 4px;
  transition: all 0.15s;
}
.node-row.all-notes:hover {
  background: rgba(255,255,255,0.06);
}
.node-row.all-notes.active {
  background: rgba(99,102,241,0.15);
  color: var(--accent-light);
}
.node-icon {
  font-size: 14px;
  flex-shrink: 0;
}
.node-name {
  flex: 1;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

/* 新建笔记本表单 */
.add-notebook-form {
  padding: 8px 0 0;
}
.add-notebook-form input {
  width: 100%;
  padding: 6px 10px;
  background: rgba(255,255,255,0.08);
  border: 1px solid rgba(99,102,241,0.4);
  border-radius: 6px;
  color: var(--text-primary);
  font-size: 13px;
  outline: none;
}

/* 右侧笔记内容 */
.notes-content {
  flex: 1;
  min-width: 0;
}

/* 筛选栏 */
.filter-bar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 20px;
  gap: 12px;
  flex-wrap: wrap;
}
.type-tabs {
  display: flex;
  gap: 6px;
  flex-wrap: wrap;
}
.type-tab {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  padding: 6px 14px;
  border-radius: 16px;
  font-size: 13px;
  color: var(--text-muted);
  background: rgba(255,255,255,0.04);
  border: 1px solid rgba(255,255,255,0.06);
  cursor: pointer;
  transition: all 0.2s;
}
.type-tab:hover {
  background: rgba(99,102,241,0.1);
}
.type-tab.active {
  background: rgba(99,102,241,0.2);
  border-color: rgba(99,102,241,0.4);
  color: var(--accent-light);
}
.type-count {
  font-size: 11px;
  padding: 1px 6px;
  border-radius: 10px;
  background: rgba(255,255,255,0.1);
}
.status-tabs {
  display: flex;
  gap: 6px;
}
.status-tab {
  padding: 6px 12px;
  border-radius: 14px;
  font-size: 12px;
  color: var(--text-muted);
  cursor: pointer;
  transition: all 0.2s;
}
.status-tab:hover {
  background: rgba(255,255,255,0.06);
}
.status-tab.active {
  background: rgba(139,92,246,0.15);
  color: var(--accent-light);
}
.search-input {
  flex: 1;
  max-width: 240px;
  padding: 8px 14px;
  background: rgba(255,255,255,0.05);
  border: 1px solid rgba(255,255,255,0.1);
  border-radius: 10px;
  color: var(--text-primary);
  font-size: 13px;
  outline: none;
  transition: all 0.2s;
}
.search-input:focus {
  border-color: rgba(99,102,241,0.4);
}

/* 空状态 */
.empty-state {
  text-align: center;
  padding: 80px 20px;
  color: var(--text-muted);
}
.empty-icon {
  font-size: 48px;
  margin-bottom: 16px;
}
.btn-browse {
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
.loading-state {
  text-align: center;
  padding: 60px;
  color: var(--text-muted);
}

/* 笔记卡片 */
.notes-grid {
  display: grid;
  grid-template-columns: 1fr;
  gap: 12px;
}
.note-card {
  background: rgba(255,255,255,0.04);
  border: 1px solid rgba(255,255,255,0.08);
  border-radius: 12px;
  padding: 16px;
  transition: all 0.2s;
  cursor: pointer;
}
.note-card:hover {
  border-color: rgba(99,102,241,0.3);
  background: rgba(255,255,255,0.06);
  transform: translateY(-1px);
}
.card-title-row {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-bottom: 8px;
}
.card-title {
  font-size: 16px;
  font-weight: 600;
  color: var(--text-primary);
  flex: 1;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.card-badge {
  font-size: 11px;
  padding: 2px 8px;
  border-radius: 4px;
  white-space: nowrap;
}
.card-badge.draft {
  background: rgba(245,158,11,0.15);
  color: #f59e0b;
}
.card-badge.source {
  background: rgba(16,185,129,0.15);
  color: #10b981;
}
.card-meta {
  display: flex;
  gap: 8px;
  margin-bottom: 8px;
}
.meta-type {
  font-size: 12px;
  padding: 2px 8px;
  border-radius: 4px;
  background: rgba(99,102,241,0.1);
  color: var(--accent-purple);
}
.meta-private {
  font-size: 12px;
  color: var(--text-muted);
}
.meta-public {
  font-size: 12px;
  color: #10b981;
}
.card-tags {
  display: flex;
  gap: 6px;
  flex-wrap: wrap;
  margin-bottom: 8px;
}
.tag {
  font-size: 11px;
  padding: 2px 8px;
  border-radius: 4px;
  background: rgba(255,255,255,0.06);
  color: var(--text-muted);
}
.card-bottom {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding-top: 10px;
  border-top: 1px solid rgba(255,255,255,0.06);
}
.card-stats {
  display: flex;
  gap: 12px;
  font-size: 12px;
  color: var(--text-muted);
}
.card-time {
  font-size: 12px;
  color: var(--text-muted);
}

/* 分页 */
.pagination {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 16px;
  margin-top: 24px;
}
.page-btn {
  padding: 8px 20px;
  background: rgba(255,255,255,0.06);
  border: 1px solid rgba(255,255,255,0.1);
  border-radius: 8px;
  color: var(--text-secondary);
  font-size: 13px;
  cursor: pointer;
  transition: all 0.2s;
}
.page-btn:hover:not(:disabled) {
  background: rgba(99,102,241,0.15);
  border-color: rgba(99,102,241,0.3);
}
.page-btn:disabled {
  opacity: 0.4;
  cursor: not-allowed;
}
.page-info {
  font-size: 13px;
  color: var(--text-muted);
}
</style>
