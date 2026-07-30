<template>
  <StarryBackground />
  <div class="note-edit-page">
    <div class="page-header">
      <button class="back-btn" @click="goBack">← 返回</button>
      <h1>{{ isEditMode ? '编辑笔记' : '新建笔记' }}</h1>
    </div>

    <div class="main-container">
      <div v-if="loading" class="loading-state">加载中...</div>

      <div v-else class="note-form">
        <!-- 标题 -->
        <div class="form-group">
          <label>标题 <span class="required">*</span></label>
          <input
            v-model="form.title"
            type="text"
            placeholder="例如：Redis 持久化机制复盘"
            maxlength="200"
            class="form-input"
          />
        </div>

        <!-- 类型 + 可见性 -->
        <div class="form-row">
          <div class="form-group half">
            <label>类型</label>
            <div class="option-tabs">
              <span
                v-for="t in typeOptions"
                :key="t.value"
                class="option-tab"
                :class="{ active: form.note_type === t.value }"
                @click="form.note_type = t.value"
              >{{ t.label }}</span>
            </div>
          </div>
          <div class="form-group half">
            <label>可见性</label>
            <div class="option-tabs">
              <span
                class="option-tab"
                :class="{ active: form.visibility === 'private' }"
                @click="form.visibility = 'private'"
              >🔒 仅自己</span>
              <span
                class="option-tab"
                :class="{ active: form.visibility === 'public' }"
                @click="form.visibility = 'public'"
              >🌐 公开</span>
            </div>
          </div>
        </div>

        <!-- 状态 -->
        <div class="form-group">
          <label>发布状态</label>
          <div class="option-tabs">
            <span
              class="option-tab"
              :class="{ active: form.status === 'draft' }"
              @click="form.status = 'draft'"
            >草稿</span>
            <span
              class="option-tab"
              :class="{ active: form.status === 'published' }"
              @click="form.status = 'published'"
            >发布</span>
          </div>
          <p v-if="form.visibility === 'public' && form.status === 'draft'" class="hint warn">
            当前为“公开但草稿”状态，仅自己可见；选择“发布”后才会进入公开广场。
          </p>
        </div>

        <!-- 笔记本 -->
        <div class="form-group">
          <label>所属笔记本</label>
          <select
            v-model="form.notebook_id"
            class="form-select"
            :disabled="notebookLoading"
          >
            <option :value="null">不指定笔记本</option>
            <option v-for="nb in flatNotebooks" :key="nb.id" :value="nb.id">
              {{ nb.prefix }}{{ nb.name }}
            </option>
          </select>
        </div>

        <!-- 标签（逗号分隔，最多 5 个） -->
        <div class="form-group">
          <label>标签（逗号分隔，最多 5 个）</label>
          <input
            v-model="form.tags"
            type="text"
            placeholder="例如：Redis,缓存,持久化"
            maxlength="500"
            class="form-input"
          />
        </div>

<!-- 内容 -->
        <div class="form-group">
          <label>
            内容 <span class="required">*</span>
            <span class="hint">支持 Markdown 语法</span>
            <button type="button" class="btn-import" @click="fileInput?.click()">📄 导入 Markdown / 文本</button>
            <input ref="fileInput" type="file" accept=".txt,.md,.text,.markdown" style="display:none" @change="handleFileImport" />
          </label>
          <div class="editor-wrapper">
            <Editor
              :value="form.content"
              :plugins="plugins"
              @change="handleEditorChange"
              :uploadImages="handleUploadImages"
            />
          </div>
        </div>

        <!-- 错误提示 -->
        <p v-if="error" class="error-msg">{{ error }}</p>

        <!-- 操作按钮 -->
        <div class="form-actions">
          <button class="btn-save" :disabled="saving" @click="handleSubmit">
            {{ saving ? '保存中...' : (isEditMode ? '保存修改' : '创建笔记') }}
          </button>
          <button class="btn-cancel" @click="goBack">取消</button>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import StarryBackground from '../components/StarryBackground.vue'
import { Editor } from '@bytemd/vue-next'
import gfm from '@bytemd/plugin-gfm'
import highlight from '@bytemd/plugin-highlight'
import 'bytemd/dist/index.css'
import 'highlight.js/styles/github-dark.css'
import { createNote, updateNote, getNoteDetail, uploadNoteImage, getNotebooks } from '../api/learningNote'

const plugins = [
  gfm(),
  highlight(),
]

const route = useRoute()
const router = useRouter()

const loading = ref(false)
const saving = ref(false)
const error = ref('')
const notebookLoading = ref(false)
const notebooks = ref([])
const isEditMode = computed(() => !!route.params.id)
const fileInput = ref(null)

const form = ref({
  title: '',
  content: '',
  note_type: 'note',
  visibility: 'private',
  status: 'draft',
  tags: '',
  notebook_id: null,
})

function handleFileImport(event) {
  const file = event.target.files?.[0]
  if (!file) return
  const reader = new FileReader()
  reader.onload = (e) => {
    form.value.content = String(e.target?.result || '')
  }
  reader.readAsText(file)
  event.target.value = ''
}

async function loadNotebooks() {
  notebookLoading.value = true
  try {
    const res = await getNotebooks()
    notebooks.value = res.tree || []
  } catch (e) {
    console.error('加载笔记本失败', e)
  } finally {
    notebookLoading.value = false
  }
}

function findNotebookName(notebooks, id) {
  for (const nb of notebooks) {
    if (nb.id === id) return nb.name
    if (nb.children) {
      const found = findNotebookName(nb.children, id)
      if (found) return `${nb.name} / ${found}`
    }
  }
  return null
}

function handleEditorChange(v) {
  form.value.content = v
}

async function handleUploadImages(files) {
  const results = []
  for (const file of files) {
    try {
      const res = await uploadNoteImage(file)
      results.push({
        url: res.url,
        alt: file.name,
        title: file.name,
      })
    } catch (e) {
      console.error('图片上传失败:', e)
    }
  }
  return results
}

const typeOptions = [
  { value: 'note', label: '笔记' },
  { value: 'review', label: '复盘' },
  { value: 'mistake', label: '错题' },
  { value: 'experience', label: '面经' },
  { value: 'material', label: '资料' },
]

// 将嵌套的笔记本树展平，添加路径前缀
function flattenNotebooks(notebooks, prefix = '') {
  const result = []
  for (const nb of notebooks) {
    result.push({
      id: nb.id,
      name: nb.name,
      prefix: prefix ? `${prefix} / ` : '',
    })
    if (nb.children && nb.children.length > 0) {
      result.push(...flattenNotebooks(nb.children, prefix ? `${prefix} / ${nb.name}` : nb.name))
    }
  }
  return result
}

const flatNotebooks = computed(() => flattenNotebooks(notebooks.value))

function goBack() {
  router.push('/learning-notes')
}

async function handleSubmit() {
  error.value = ''
  if (!form.value.title.trim()) {
    error.value = '请输入标题'
    return
  }
  if (!form.value.content.trim()) {
    error.value = '请输入内容'
    return
  }

  saving.value = true
  try {
    const payload = { ...form.value }
    if (isEditMode.value) {
      await updateNote(route.params.id, payload)
    } else {
      await createNote(payload)
    }
    router.push('/learning-notes')
  } catch (e) {
    error.value = e?.message || '保存失败，请重试'
    console.error(e)
  } finally {
    saving.value = false
  }
}

async function loadEditData() {
  if (!isEditMode.value) {
    // 新建笔记时，先加载笔记本列表
    await loadNotebooks()
    // 如果 URL query 有 notebook_id，自动选中
    if (route.query.notebook_id) {
      form.value.notebook_id = Number(route.query.notebook_id)
    }
    return
  }
  loading.value = true
  try {
    const data = await getNoteDetail(route.params.id)
    form.value = {
      title: data.title || '',
      content: data.content || '',
      note_type: data.note_type || 'note',
      visibility: data.visibility || 'private',
      status: data.status || 'draft',
      tags: data.tags || '',
      notebook_id: data.notebook_id || null,
    }
    // 编辑模式也加载笔记本列表以便选择器显示
    await loadNotebooks()
  } catch (e) {
    error.value = '加载笔记失败'
    console.error(e)
  } finally {
    loading.value = false
  }
}

onMounted(loadEditData)
</script>

<style scoped>
.note-edit-page {
  min-height: 100vh;
  padding-bottom: 60px;
}
.page-header {
  display: flex;
  align-items: center;
  gap: 16px;
  padding: 30px 20px 10px;
  max-width: 800px;
  margin: 0 auto;
}
.back-btn {
  background: none;
  border: 1px solid rgba(255,255,255,0.1);
  border-radius: 8px;
  color: var(--text-secondary);
  font-size: 13px;
  padding: 6px 14px;
  cursor: pointer;
  transition: all 0.2s;
}
.back-btn:hover {
  background: rgba(99,102,241,0.1);
  border-color: rgba(99,102,241,0.3);
}
.page-header h1 {
  font-size: 24px;
  font-weight: 700;
  background: linear-gradient(135deg, #a78bfa, #60a5fa);
  -webkit-background-clip: text;
  -webkit-text-fill-color: transparent;
  background-clip: text;
}
.main-container {
  max-width: 800px;
  margin: 0 auto;
  padding: 0 20px;
}

.loading-state {
  text-align: center;
  padding: 60px;
  color: var(--text-muted);
}

.note-form {
  display: flex;
  flex-direction: column;
  gap: 20px;
}

.form-group {
  display: flex;
  flex-direction: column;
  gap: 8px;
}
.form-row {
  display: flex;
  gap: 16px;
}
.form-group.half {
  flex: 1;
}
label {
  font-size: 14px;
  font-weight: 600;
  color: var(--text-secondary);
}
.required {
  color: #ef4444;
}
.hint {
  font-size: 12px;
  font-weight: 400;
  color: var(--text-muted);
}
.hint.warn {
  color: #f59e0b;
  margin-top: 4px;
}
.btn-import {
  margin-left: 12px;
  padding: 4px 10px;
  background: rgba(99,102,241,0.12);
  border: 1px solid rgba(99,102,241,0.25);
  border-radius: 6px;
  color: var(--accent-light);
  font-size: 12px;
  font-weight: 500;
  cursor: pointer;
  transition: all 0.2s;
}
.btn-import:hover {
  background: rgba(99,102,241,0.2);
}

.form-input {
  padding: 10px 14px;
  background: rgba(255,255,255,0.05);
  border: 1px solid rgba(255,255,255,0.1);
  border-radius: 10px;
  color: var(--text-primary);
  font-size: 14px;
  outline: none;
  transition: all 0.2s;
}
.form-input:focus {
  border-color: rgba(99,102,241,0.4);
  background: rgba(255,255,255,0.07);
}
.form-select {
  padding: 10px 14px;
  background: rgba(255,255,255,0.05);
  border: 1px solid rgba(255,255,255,0.1);
  border-radius: 10px;
  color: var(--text-primary);
  font-size: 14px;
  outline: none;
  transition: all 0.2s;
  appearance: none;
  cursor: pointer;
  background-image: url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' width='12' height='8' viewBox='0 0 12 8'%3E%3Cpath d='M1 1l5 5 5-5' stroke='%239ca3af' stroke-width='2' fill='none'/%3E%3C/svg%3E");
  background-repeat: no-repeat;
  background-position: right 12px center;
  padding-right: 36px;
}
.form-select:focus {
  border-color: rgba(99,102,241,0.4);
  background-color: rgba(255,255,255,0.07);
}
.form-select:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

.form-textarea {
  padding: 14px;
  background: rgba(255,255,255,0.05);
  border: 1px solid rgba(255,255,255,0.1);
  border-radius: 10px;
  color: var(--text-primary);
  font-size: 14px;
  font-family: 'Consolas', 'Monaco', monospace;
  line-height: 1.6;
  outline: none;
  transition: all 0.2s;
  resize: vertical;
  min-height: 400px;
}
.form-textarea:focus {
  border-color: rgba(99,102,241,0.4);
  background: rgba(255,255,255,0.07);
}

.editor-wrapper {
  border: 1px solid rgba(255,255,255,0.1);
  border-radius: 10px;
  overflow: hidden;
}
.editor-wrapper :deep(.bytemd) {
  background: rgba(255,255,255,0.05);
  color: var(--text-primary);
  border: none;
  height: 500px;
}
.editor-wrapper :deep(.bytemd-toolbar) {
  background: rgba(255,255,255,0.08);
  border-bottom: 1px solid rgba(255,255,255,0.1);
}
.editor-wrapper :deep(.bytemd-status) {
  color: var(--text-muted);
}
.editor-wrapper :deep(.bytemd-editor) {
  background: transparent;
}
.editor-wrapper :deep(.bytemd-preview) {
  background: transparent;
}

.option-tabs {
  display: flex;
  gap: 8px;
  flex-wrap: wrap;
}
.option-tab {
  padding: 6px 14px;
  border-radius: 16px;
  font-size: 13px;
  color: var(--text-muted);
  background: rgba(255,255,255,0.04);
  border: 1px solid rgba(255,255,255,0.06);
  cursor: pointer;
  transition: all 0.2s;
}
.option-tab:hover {
  background: rgba(99,102,241,0.1);
}
.option-tab.active {
  background: rgba(99,102,241,0.2);
  border-color: rgba(99,102,241,0.4);
  color: var(--accent-light);
}

.error-msg {
  color: #ef4444;
  font-size: 13px;
  text-align: center;
}

.form-actions {
  display: flex;
  gap: 12px;
  justify-content: center;
  margin-top: 10px;
}
.btn-save {
  padding: 10px 28px;
  background: linear-gradient(135deg, #6366f1, #8b5cf6);
  color: white;
  border: none;
  border-radius: 8px;
  font-size: 14px;
  font-weight: 600;
  cursor: pointer;
  transition: all 0.2s;
}
.btn-save:hover:not(:disabled) {
  opacity: 0.9;
  transform: translateY(-1px);
}
.btn-save:disabled {
  opacity: 0.6;
  cursor: not-allowed;
}
.btn-cancel {
  padding: 10px 28px;
  background: rgba(255,255,255,0.06);
  color: var(--text-secondary);
  border: 1px solid rgba(255,255,255,0.1);
  border-radius: 8px;
  font-size: 14px;
  cursor: pointer;
  transition: all 0.2s;
}
.btn-cancel:hover {
  background: rgba(255,255,255,0.1);
}
</style>
