<template>
  <StarryBackground />
  <div class="note-edit-page">
    <div class="page-header">
      <button class="back-btn" @click="goBack"><BaseIcon name="chevron-left" :size="16" /> 返回</button>
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
              ><BaseIcon name="lock" :size="13" /> 仅自己</span>
              <span
                class="option-tab"
                :class="{ active: form.visibility === 'public' }"
                @click="form.visibility = 'public'"
              ><BaseIcon name="globe" :size="13" /> 公开</span>
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

        <!-- 笔记模板 -->
        <div class="form-group">
          <label>
            笔记模板
            <span class="hint">选择一个模板快速填充内容结构</span>
          </label>
          <div class="template-selector">
            <button
              type="button"
              class="btn-template"
              @click="showTemplateDialog = true"
              :disabled="templateLoading"
            >
              <BaseIcon name="list" :size="14" /> {{ selectedTemplate ? '更换模板' : '选择模板' }}
            </button>
            <span v-if="selectedTemplate" class="template-applied">
              已应用模板
            </span>
          </div>
        </div>

        <!-- 模板选择弹窗 -->
        <Teleport to="body">
          <div v-if="showTemplateDialog" class="modal-overlay" @click.self="showTemplateDialog = false">
            <div class="modal-panel">
              <div class="modal-header">
                <h3>选择笔记模板</h3>
                <button class="modal-close" aria-label="关闭模板选择" @click="showTemplateDialog = false"><BaseIcon name="x" :size="16" /></button>
              </div>
              <div class="modal-body">
                <div v-if="templateLoading" class="loading-state">加载中...</div>
                <div v-else-if="templates.length === 0" class="empty-state">暂无可用模板</div>
                <div v-else class="template-grid">
                  <div v-for="tpl in templates" :key="tpl.id" class="template-card-wrapper">
                    <button
                      type="button"
                      class="template-card"
                      :class="{ active: selectedTemplate === tpl.id }"
                      @click="applyTemplate(tpl.id)"
                    >
                      <div class="template-card-title">{{ tpl.name }}</div>
                      <div v-if="tpl.description" class="template-card-desc">{{ tpl.description }}</div>
                      <div class="template-card-meta">
                        <span class="template-category">{{ typeLabel(tpl.note_type) }}</span>
                      </div>
                    </button>
                  </div>
                </div>
              </div>
            </div>
          </div>
        </Teleport>

        <!-- 标签（逗号分隔，最多 5 个） -->
        <div class="form-group">
          <label>
            标签（最多 5 个）
            <button
              type="button"
              class="btn-ai-tag"
              @click="loadAiTags"
              :disabled="loadingTags"
            >{{ hasAiRecommendation ? '重新推荐' : 'AI 推荐标签' }}</button>
          </label>
          <div class="tag-input-area">
            <input
              v-model="tagInput"
              type="text"
              placeholder="输入标签后按回车添加"
              maxlength="20"
              class="form-input"
              @keyup.enter="addTag"
            />
          </div>
          <!-- 已选标签 -->
          <div v-if="tagsArray.length" class="tag-list">
            <span v-for="(tag, i) in tagsArray" :key="i" class="tag">
              {{ tag }}
              <span class="tag-remove" @click="removeTag(i)"><BaseIcon name="x" :size="12" /></span>
            </span>
          </div>
          <!-- AI 推荐标签 -->
          <div v-if="aiTags.length" class="ai-tags">
            <span class="ai-tags-label">AI 推荐：</span>
            <span
              v-for="tag in aiTags"
              :key="tag"
              class="tag tag-suggested"
              :class="{ selected: tagsArray.includes(tag) }"
              @click="toggleAiTag(tag)"
            >{{ tag }}</span>
            <span v-if="aiTagsReason" class="ai-tags-reason">{{ aiTagsReason }}</span>
          </div>
          <p v-if="loadingTags" class="hint">AI 正在分析笔记内容...</p>
        </div>

<!-- 内容 -->
        <div class="form-group">
          <label>
            内容 <span class="required">*</span>
            <span class="hint">支持 Markdown 语法</span>
            <button type="button" class="btn-import" @click="fileInput?.click()"><BaseIcon name="file" :size="14" /> 导入 Markdown / 文本</button>
            <input ref="fileInput" type="file" accept=".txt,.md,.text,.markdown" style="display:none" @change="handleFileImport" />
          </label>
          <div class="editor-wrapper" @click="handleEditorClick">
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
import { ref, computed, onMounted, nextTick } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import StarryBackground from '../components/StarryBackground.vue'
import BaseIcon from '../components/BaseIcon.vue'
import { Editor } from '@bytemd/vue-next'
import gfm from '@bytemd/plugin-gfm'
import highlight from '@bytemd/plugin-highlight'
import 'bytemd/dist/index.css'
import 'highlight.js/styles/github-dark.css'
import { createNote, updateNote, getNoteDetail, uploadNoteImage, getNotebooks, suggestTags, getTemplates, getTemplateDetail } from '../api/learningNote'

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

// 模板选择
const templates = ref([])
const templateLoading = ref(false)
const showTemplateDialog = ref(false)
const selectedTemplate = ref(null)

// 标签管理：form.tags 保留为逗号字符串供提交，tagsArray 是前端操作的数组视图
const tagInput = ref('')
const aiTags = ref([])
const aiTagsReason = ref('')
const loadingTags = ref(false)
const hasAiRecommendation = ref(false)

const form = ref({
  title: '',
  content: '',
  note_type: 'note',
  visibility: 'private',
  status: 'draft',
  tags: '',
  notebook_id: null,
})

// tags 字符串 <-> 数组 双向转换，方便前端增删
const tagsArray = computed({
  get: () => form.value.tags
    ? form.value.tags.split(',').map(t => t.trim()).filter(Boolean)
    : [],
  set: (arr) => { form.value.tags = arr.join(',') },
})

function addTag() {
  const t = tagInput.value.trim()
  if (!t) return
  const arr = tagsArray.value
  if (arr.includes(t)) {
    tagInput.value = ''
    return
  }
  if (arr.length >= 5) {
    error.value = '最多 5 个标签'
    return
  }
  error.value = ''
  tagsArray.value = [...arr, t]
  tagInput.value = ''
}

function removeTag(idx) {
  const arr = tagsArray.value
  arr.splice(idx, 1)
  tagsArray.value = arr
}

function toggleAiTag(tag) {
  const arr = tagsArray.value
  if (arr.includes(tag)) {
    // 已选中则取消选中
    const idx = arr.indexOf(tag)
    arr.splice(idx, 1)
    tagsArray.value = arr
    return
  }
  if (arr.length >= 5) {
    error.value = '最多 5 个标签'
    return
  }
  arr.push(tag)
  tagsArray.value = arr
}

async function loadAiTags() {
  if (!isEditMode.value || !route.params.id) {
    error.value = '请先保存笔记后再让 AI 推荐标签'
    return
  }
  loadingTags.value = true
  error.value = ''
  try {
    const res = await suggestTags(route.params.id, hasAiRecommendation.value)
    aiTags.value = res.tags || []
    aiTagsReason.value = res.reason || ''
    hasAiRecommendation.value = true
  } catch (e) {
    error.value = e?.message || 'AI 标签推荐失败'
    console.error(e)
  } finally {
    loadingTags.value = false
  }
}

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

async function loadTemplates() {
  templateLoading.value = true
  try {
    const res = await getTemplates()
    templates.value = res?.templates || []
  } catch (e) {
    console.error('加载模板失败', e)
  } finally {
    templateLoading.value = false
  }
}

async function applyTemplate(templateId) {
  const template = templates.value.find(item => item.id === templateId)
  if (!template) return

  if (form.value.content.trim()) {
    const confirmed = window.confirm('应用模板会覆盖当前内容，确定继续吗？')
    if (!confirmed) return
  }

  showTemplateDialog.value = false
  try {
    const detail = await getTemplateDetail(templateId)
    if (detail?.markdown) {
      form.value.content = detail.markdown
      if (detail.note_type) {
        form.value.note_type = detail.note_type
      }
    }
    selectedTemplate.value = templateId
  } catch (e) {
    error.value = e?.message || '应用模板失败'
    console.error('应用模板失败', e)
  }
}

function handleEditorChange(v) {
  form.value.content = v
}

// 编辑器预览区标题点击跳转（事件委托）
function handleEditorClick(e) {
  const target = e.target.closest('h1, h2, h3, h4, h5, h6')
  if (!target) return
  // 仅处理预览区内的标题
  const preview = document.querySelector('.bytemd-preview')
  if (!preview || !preview.contains(target)) return
  // 点击标题 → 滚动到该标题在预览区的顶部
  nextTick(() => {
    const rect = target.getBoundingClientRect()
    const previewRect = preview.getBoundingClientRect()
    const offsetTop = rect.top - previewRect.top + preview.scrollTop - 10
    preview.scrollTo({ top: offsetTop, behavior: 'smooth' })
  })
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

function typeLabel(value) {
  return typeOptions.find(option => option.value === value)?.label || '通用'
}

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
    // 新建笔记时，先加载笔记本列表和模板
    loadTemplates()
    await loadNotebooks()
    // 如果 URL query 有 notebook_id，自动选中
    if (route.query.notebook_id) {
      form.value.notebook_id = Number(route.query.notebook_id)
    }
    return
  }
  loading.value = true
  // 同时加载模板列表
  loadTemplates()
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
  background: rgba(128, 128, 128,0.1);
  border-color: rgba(128, 128, 128,0.3);
}
.page-header h1 {
  font-size: 24px;
  font-weight: 700;
  color: var(--text-primary);
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
  color: #A3A3A3;
}
.hint {
  font-size: 12px;
  font-weight: 400;
  color: var(--text-muted);
}
.hint.warn {
  color: #A3A3A3;
  margin-top: 4px;
}
.btn-import {
  margin-left: 12px;
  padding: 4px 10px;
  background: rgba(128, 128, 128,0.12);
  border: 1px solid rgba(128, 128, 128,0.25);
  border-radius: 6px;
  color: var(--accent-light);
  font-size: 12px;
  font-weight: 500;
  cursor: pointer;
  transition: all 0.2s;
}
.btn-import:hover {
  background: rgba(128, 128, 128,0.2);
}

.form-input {
  padding: 10px 14px;
  background: rgba(255,255,255,0.05);
  border: 1px solid rgba(255,255,255,0.1);
  border-radius: 8px;
  color: var(--text-primary);
  font-size: 14px;
  outline: none;
  transition: all 0.2s;
}
.form-input:focus {
  border-color: rgba(128, 128, 128,0.4);
  background: rgba(255,255,255,0.07);
}
.form-select {
  padding: 10px 14px;
  background: var(--bg-card);
  border: 1px solid var(--border-default);
  border-radius: 8px;
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
  border-color: var(--border-focus);
  background-color: var(--bg-input-focus);
}
.form-select:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}
/* option 弹出层由全局 style.css 统一适配黑夜/白天模式 */

.form-textarea {
  padding: 14px;
  background: rgba(255,255,255,0.05);
  border: 1px solid rgba(255,255,255,0.1);
  border-radius: 8px;
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
  border-color: rgba(128, 128, 128,0.4);
  background: rgba(255,255,255,0.07);
}

.editor-wrapper {
  border: 1px solid rgba(255,255,255,0.1);
  border-radius: 8px;
  overflow: hidden;
}
/* === bytemd 深色主题覆盖 === */
.editor-wrapper :deep(.bytemd) {
  background: var(--bg-input);
  color: var(--text-primary);
  border: 1px solid var(--border-default);
  border-radius: 8px;
  height: 500px;
  transition: border-color 0.2s;
}
.editor-wrapper :deep(.bytemd:focus-within) {
  border-color: var(--border-focus);
}
/* 全屏模式：修复文字重叠 + 背景遮挡 */
.editor-wrapper :deep(.bytemd.bytemd-fullscreen) {
  position: fixed;
  top: 0;
  left: 0;
  width: 100vw;
  height: 100vh;
  z-index: 9999;
  background: var(--bg-surface);
  height: 100vh !important;
}
.editor-wrapper :deep(.bytemd.bytemd-fullscreen .bytemd-toolbar) {
  background: var(--bg-surface);
  border-bottom: 1px solid var(--border-default);
}
.editor-wrapper :deep(.bytemd.bytemd-fullscreen .bytemd-toolbar-icon) {
  color: var(--text-secondary);
}
.editor-wrapper :deep(.bytemd.bytemd-fullscreen .bytemd-fullscreen-exit) {
  display: inline-flex;
  color: var(--accent-light);
}
.editor-wrapper :deep(.bytemd-toolbar) {
  background: var(--bg-surface);
  border-bottom: 1px solid var(--border-default);
  border-radius: 8px 10px 0 0;
}
.editor-wrapper :deep(.bytemd-toolbar-tab) {
  color: var(--text-muted);
}
.editor-wrapper :deep(.bytemd-toolbar-tab-active) {
  color: var(--accent-light);
}
.editor-wrapper :deep(.bytemd-toolbar-icon) {
  color: var(--text-secondary);
}
.editor-wrapper :deep(.bytemd-toolbar-icon:hover) {
  background: var(--bg-hover);
}
.editor-wrapper :deep(.bytemd-toolbar-icon-active) {
  color: var(--accent-light);
}
.editor-wrapper :deep(.bytemd-status) {
  color: var(--text-muted);
  border-top: 1px solid var(--border-default);
}
.editor-wrapper :deep(.bytemd-sidebar) {
  border-left: 1px solid var(--border-default);
}
.editor-wrapper :deep(.bytemd-split .bytemd-preview) {
  border-left: 1px solid var(--border-default);
}

/* === CodeMirror 编辑区深色覆盖 === */
.editor-wrapper :deep(.bytemd-editor) {
  background: transparent;
}
.editor-wrapper :deep(.CodeMirror) {
  background: transparent !important;
  color: var(--text-primary) !important;
}
.editor-wrapper :deep(.CodeMirror-gutters) {
  background: var(--bg-input) !important;
  border-right: 1px solid var(--border-default) !important;
}
.editor-wrapper :deep(.CodeMirror-linenumber) {
  color: var(--text-muted) !important;
}
.editor-wrapper :deep(.CodeMirror-cursor) {
  border-left-color: var(--accent-light) !important;
}
.editor-wrapper :deep(.CodeMirror-selected) {
  background: var(--gray-a20) !important;
}
.editor-wrapper :deep(.CodeMirror-focused .CodeMirror-selected) {
  background: var(--gray-a30) !important;
}
.editor-wrapper :deep(.CodeMirror-activeline-background) {
  background: var(--bg-hover) !important;
}

/* === 预览区深色覆盖 === */
.editor-wrapper :deep(.bytemd-preview) {
  background: transparent;
}
.editor-wrapper :deep(.bytemd-preview .markdown-body) {
  color: var(--text-primary);
}
.editor-wrapper :deep(.bytemd-preview .markdown-body h1),
.editor-wrapper :deep(.bytemd-preview .markdown-body h2),
.editor-wrapper :deep(.bytemd-preview .markdown-body h3),
.editor-wrapper :deep(.bytemd-preview .markdown-body h4),
.editor-wrapper :deep(.bytemd-preview .markdown-body h5),
.editor-wrapper :deep(.bytemd-preview .markdown-body h6) {
  color: var(--text-primary);
  border-bottom-color: var(--border-default);
  cursor: pointer;
  transition: color 0.15s;
}
.editor-wrapper :deep(.bytemd-preview .markdown-body h1:hover),
.editor-wrapper :deep(.bytemd-preview .markdown-body h2:hover),
.editor-wrapper :deep(.bytemd-preview .markdown-body h3:hover),
.editor-wrapper :deep(.bytemd-preview .markdown-body h4:hover),
.editor-wrapper :deep(.bytemd-preview .markdown-body h5:hover),
.editor-wrapper :deep(.bytemd-preview .markdown-body h6:hover) {
  color: var(--accent-light);
}
.editor-wrapper :deep(.bytemd-preview .markdown-body a) {
  color: var(--accent-light);
}
.editor-wrapper :deep(.bytemd-preview .markdown-body blockquote) {
  color: var(--text-muted);
  border-left-color: var(--accent-purple);
}
.editor-wrapper :deep(.bytemd-preview .markdown-body code) {
  background: var(--code-inline-bg);
  color: var(--text-primary);
}
.editor-wrapper :deep(.bytemd-preview .markdown-body pre) {
  background: var(--code-bg);
  border: 1px solid var(--code-border);
}
.editor-wrapper :deep(.bytemd-preview .markdown-body pre code) {
  color: var(--code-text);
}
.editor-wrapper :deep(.bytemd-preview .markdown-body table th),
.editor-wrapper :deep(.bytemd-preview .markdown-body table td) {
  border-color: var(--border-default);
}
.editor-wrapper :deep(.bytemd-preview .markdown-body table tr:nth-child(2n)) {
  background: var(--bg-hover);
}

/* === 标签输入区 === */
.btn-ai-tag {
  margin-left: auto;
  padding: 4px 12px;
  background: var(--accent-primary);
  border: 1px solid rgba(128, 128, 128,0.35);
  border-radius: 6px;
  color: var(--accent-light);
  font-size: 12px;
  font-weight: 500;
  cursor: pointer;
  transition: all 0.2s;
}
.btn-ai-tag:hover:not(:disabled) {
  background: var(--accent-primary);
}
.btn-ai-tag:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}
.tag-input-area {
  display: flex;
  gap: 8px;
}
.tag-list {
  display: flex;
  gap: 6px;
  flex-wrap: wrap;
  margin-top: 4px;
}
.tag {
  display: inline-flex;
  align-items: center;
  gap: 4px;
  padding: 4px 10px;
  border-radius: 6px;
  font-size: 12px;
  background: rgba(128, 128, 128,0.15);
  color: var(--accent-light);
}
.tag-remove {
  cursor: pointer;
  opacity: 0.6;
  transition: opacity 0.15s;
}
.tag-remove:hover {
  opacity: 1;
}
.ai-tags {
  display: flex;
  align-items: flex-start;
  gap: 6px;
  flex-wrap: wrap;
  margin-top: 6px;
  padding: 8px 10px;
  background: rgba(128, 128, 128,0.05);
  border: 1px dashed rgba(128, 128, 128,0.2);
  border-radius: 8px;
}
.ai-tags-label {
  font-size: 12px;
  color: var(--text-muted);
  white-space: nowrap;
  padding-top: 4px;
}
.ai-tags-reason {
  flex-basis: 100%;
  font-size: 12px;
  color: var(--text-muted);
  margin-top: 4px;
  line-height: 1.5;
}
.tag-suggested {
  cursor: pointer;
  background: rgba(255,255,255,0.06);
  color: var(--text-muted);
  transition: all 0.2s;
}
.tag-suggested:hover {
  background: rgba(128, 128, 128,0.2);
  color: var(--text-secondary);
}
.tag-suggested.selected {
  background: rgba(128, 128, 128,0.28);
  color: var(--accent-light);
}

.option-tabs {
  display: flex;
  gap: 8px;
  flex-wrap: wrap;
}
.option-tab {
  padding: 6px 14px;
  border-radius: 8px;
  font-size: 13px;
  color: var(--text-muted);
  background: rgba(255,255,255,0.04);
  border: 1px solid rgba(255,255,255,0.06);
  cursor: pointer;
  transition: all 0.2s;
}
.option-tab:hover {
  background: rgba(128, 128, 128,0.1);
}
.option-tab.active {
  background: rgba(128, 128, 128,0.2);
  border-color: rgba(128, 128, 128,0.4);
  color: var(--accent-light);
}

.error-msg {
  color: #A3A3A3;
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
  background: var(--accent-primary); color: var(--bg-base);
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

/* === 模板选择器 === */
.template-selector {
  display: flex;
  align-items: center;
  gap: 12px;
}
.btn-template {
  padding: 8px 16px;
  background: rgba(128, 128, 128,0.12);
  border: 1px solid rgba(128, 128, 128,0.25);
  border-radius: 8px;
  color: var(--accent-light);
  font-size: 13px;
  font-weight: 500;
  cursor: pointer;
  transition: all 0.2s;
}
.btn-template:hover:not(:disabled) {
  background: rgba(128, 128, 128,0.2);
}
.btn-template:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}
.template-applied {
  font-size: 12px;
  color: #A3A3A3;
}

/* 模板选择弹窗 */
.modal-overlay {
  position: fixed;
  inset: 0;
  z-index: 10000;
  background: rgba(0,0,0,0.55);
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 20px;
}
.modal-panel {
  background: var(--bg-surface);
  border: 1px solid var(--border-default);
  border-radius: 8px;
  width: 100%;
  max-width: 520px;
  max-height: 80vh;
  display: flex;
  flex-direction: column;
  box-shadow: var(--shadow-sm);
}
.modal-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 18px 20px;
  border-bottom: 1px solid var(--border-default);
}
.modal-header h3 {
  font-size: 16px;
  font-weight: 700;
  color: var(--text-primary);
  margin: 0;
}
.modal-close {
  background: none;
  border: none;
  color: var(--text-muted);
  font-size: 18px;
  cursor: pointer;
  padding: 4px;
  line-height: 1;
}
.modal-close:hover {
  color: var(--text-primary);
}
.modal-body {
  padding: 16px 20px;
  overflow-y: auto;
  flex: 1;
}
.empty-state {
  text-align: center;
  padding: 40px;
  color: var(--text-muted);
  font-size: 14px;
}
.template-grid {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 12px;
}
.template-card {
  width: 100%;
  text-align: left;
  font: inherit;
  padding: 14px;
  border: 1px solid var(--border-default);
  border-radius: 8px;
  cursor: pointer;
  transition: all 0.2s;
  background: rgba(255,255,255,0.03);
}
.template-card:hover {
  border-color: rgba(128, 128, 128,0.4);
  background: rgba(128, 128, 128,0.06);
}
.template-card.active {
  border-color: rgba(128, 128, 128,0.5);
  background: rgba(128, 128, 128,0.1);
}
.template-card-title {
  font-size: 14px;
  font-weight: 600;
  color: var(--text-primary);
  margin-bottom: 4px;
}
.template-card-desc {
  font-size: 12px;
  color: var(--text-muted);
  line-height: 1.4;
  margin-bottom: 8px;
  display: -webkit-box;
  -webkit-line-clamp: 2;
  -webkit-box-orient: vertical;
  overflow: hidden;
}
.template-card-meta {
  display: flex;
  gap: 6px;
}
.template-category {
  font-size: 11px;
  padding: 2px 8px;
  border-radius: 4px;
  background: rgba(128, 128, 128,0.1);
  color: var(--accent-light);
}

/* === 手机端适配 === */
@media (max-width: 640px) {
  .template-grid {
    grid-template-columns: 1fr;
  }

  .page-header {
    padding: 20px 14px 8px;
    gap: 10px;
  }
  .page-header h1 {
    font-size: 18px;
  }
  .main-container {
    padding: 0 14px;
  }
  .note-form {
    gap: 14px;
  }
  .form-row {
    flex-direction: column;
    gap: 14px;
  }
  /* 编辑器在手机上降低高度，改为分屏纵向更舒适 */
  .editor-wrapper :deep(.bytemd) {
    height: 60vh;
  }
  .editor-wrapper :deep(.bytemd-split) {
    flex-direction: column;
  }
  .editor-wrapper :deep(.bytemd-split .bytemd-preview) {
    border-left: none;
    border-top: 1px solid var(--border-default);
  }
  /* 导入按钮不挤占标题行 */
  .btn-import {
    margin-left: 0;
    margin-top: 4px;
    align-self: flex-start;
  }
  .form-actions {
    flex-direction: column;
    gap: 10px;
  }
  .btn-save,
  .btn-cancel {
    width: 100%;
    padding: 12px;
  }
}
</style>
