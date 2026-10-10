<template>
  <StarryBackground />
  <div class="submit-page">
    <div class="page-header">
      <h1>{{ isEditMode ? '编辑面经' : '投稿面经' }}</h1>
      <p>{{ isEditMode ? '修改后的内容会重新进入审核流程，请确认信息准确' : '分享真实面试经历，帮助更多人准备面试' }}</p>
    </div>

    <div class="form-container">
      <form @submit.prevent="handleSubmit">
        <div class="form-row">
          <div class="form-group">
            <label>标题 <span class="required">*</span></label>
            <input v-model="form.title" type="text" placeholder="例如：字节跳动后端开发一面总结" required />
          </div>
        </div>

        <div class="form-row form-row-2">
          <div class="form-group">
            <label>公司 <span class="required">*</span></label>
            <input v-model="form.company" type="text" placeholder="例如：字节跳动" required list="company-list" />
            <datalist id="company-list">
              <option v-for="c in commonCompanies" :key="c" :value="c" />
            </datalist>
          </div>
          <div class="form-group">
            <label>岗位 <span class="required">*</span></label>
            <input v-model="form.position" type="text" placeholder="例如：后端开发" required list="position-list" />
            <datalist id="position-list">
              <option v-for="p in commonPositions" :key="p" :value="p" />
            </datalist>
          </div>
        </div>

        <div class="form-row form-row-2">
          <div class="form-group">
            <label>级别</label>
            <select v-model="form.level">
              <option value="">请选择</option>
              <option v-for="l in levels" :key="l" :value="l">{{ l }}</option>
            </select>
          </div>
          <div class="form-group">
            <label>轮次</label>
            <select v-model="form.round">
              <option value="">请选择</option>
              <option v-for="r in rounds" :key="r" :value="r">{{ r }}</option>
            </select>
          </div>
        </div>

        <div class="form-group">
          <label>摘要</label>
          <textarea v-model="form.summary" rows="2" placeholder="可选；为空时会自动截取正文前 200 字"></textarea>
        </div>

        <div class="form-group">
          <label>面经内容 <span class="required">*</span></label>
          <div class="editor-toolbar">
            <button type="button" @click="insertFormat('**', '**')" title="加粗">B</button>
            <button type="button" @click="insertFormat('*', '*')" title="斜体"><em>I</em></button>
            <button type="button" @click="insertFormat('```\\n', '\\n```')" title="代码块">&lt;/&gt;</button>
            <button type="button" @click="insertFormat('> ', '')" title="引用">"</button>
            <button type="button" @click="insertFormat('- ', '')" title="列表">-</button>
            <button type="button" @click="insertFormat('### ', '')" title="标题">H</button>
            <span class="toolbar-divider"></span>
            <button type="button" @click="fileInput?.click()" title="从文本文件导入">导入</button>
            <input ref="fileInput" type="file" accept=".txt,.md,.text,.markdown" style="display:none" @change="handleFileImport" />
            <span class="toolbar-divider"></span>
            <span class="char-count">{{ form.content.length }} 字</span>
            <button type="button" class="preview-toggle" :class="{ active: showPreview }" @click="showPreview = !showPreview">
              {{ showPreview ? '编辑' : '预览' }}
            </button>
          </div>

          <textarea
            v-if="!showPreview"
            ref="contentRef"
            v-model="form.content"
            rows="14"
            placeholder="请按 Markdown 书写，例如：面试流程、题目、回答思路、复盘建议。系统会清理复杂 HTML 与 SVG，避免详情页样式异常。"
            required
          ></textarea>
          <div v-else class="markdown-preview" v-html="renderedContent"></div>
        </div>

        <div class="form-group">
          <label>标签</label>
          <div class="tags-input">
            <div class="tags-list">
              <span v-for="(tag, i) in form.tags" :key="i" class="tag-item">
                {{ tag }}
                <button type="button" aria-label="移除标签" @click="removeTag(i)"><BaseIcon name="x" :size="12" /></button>
              </span>
            </div>
            <input
              v-model="tagInput"
              type="text"
              placeholder="输入标签后按回车添加"
              @keydown.enter.prevent="addTag"
            />
          </div>
          <div class="suggested-tags">
            <span>常用：</span>
            <button type="button" v-for="t in suggestedTags" :key="t" @click="addSuggestedTag(t)">{{ t }}</button>
          </div>
        </div>

        <div class="form-group anonymous-row">
          <label class="switch-label">
            <input type="checkbox" v-model="form.is_anonymous" />
            <span class="switch-text">匿名发布</span>
          </label>
        </div>

        <div class="form-actions">
          <button v-if="!isEditMode" type="button" class="btn-draft" @click="saveDraft">保存草稿</button>
          <button type="submit" class="btn-submit" :disabled="submitting">
            {{ submitting ? '提交中...' : (isEditMode ? '保存并重新提交审核' : '提交审核') }}
          </button>
        </div>
      </form>
    </div>
  </div>
</template>

<script setup>
import { ref, reactive, computed, onMounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { submitExperience, getMyExperienceDetail, updateMyExperience } from '../api/experience'
import StarryBackground from '../components/StarryBackground.vue'
import BaseIcon from '../components/BaseIcon.vue'
import { renderExperienceContent } from '../utils/experienceContent'

const route = useRoute()
const router = useRouter()
const contentRef = ref(null)
const fileInput = ref(null)
const showPreview = ref(false)
const submitting = ref(false)
const tagInput = ref('')
const isEditMode = computed(() => Boolean(route.params.id))

const form = reactive({
  title: '',
  company: '',
  position: '',
  content: '',
  level: '',
  round: '',
  summary: '',
  tags: [],
  is_anonymous: false
})

const levels = ['校招', '1-3年', '3-5年', '5年以上']
const rounds = ['一面', '二面', '三面', 'HR面', '综合']
const commonCompanies = ['字节跳动', '腾讯', '阿里巴巴', '美团', '百度', '京东', '快手', '小红书', '华为', '小米', '网易', '拼多多', '滴滴', '蚂蚁集团']
const commonPositions = ['后端开发', '前端开发', '算法工程师', '测试开发', '产品经理', '数据分析', '运维工程师', '客户端开发', 'Java开发', 'Python开发']
const suggestedTags = ['算法', '系统设计', '数据库', '网络', '操作系统', '项目经验', 'HR面', '手撕代码', '八股文', '场景题']

const renderedContent = computed(() => renderExperienceContent(form.content || ''))

function handleFileImport(event) {
  const file = event.target.files?.[0]
  if (!file) return
  const reader = new FileReader()
  reader.onload = (e) => {
    form.content = String(e.target?.result || '')
  }
  reader.readAsText(file)
  event.target.value = ''
}

function insertFormat(prefix, suffix) {
  const el = contentRef.value
  if (!el) return
  const start = el.selectionStart
  const end = el.selectionEnd
  const selected = form.content.substring(start, end)
  const replacement = prefix + selected + suffix
  form.content = form.content.substring(0, start) + replacement + form.content.substring(end)
}

function addTag() {
  const tag = tagInput.value.trim()
  if (tag && !form.tags.includes(tag) && form.tags.length < 5) {
    form.tags.push(tag)
    tagInput.value = ''
  }
}

function addSuggestedTag(tag) {
  if (!form.tags.includes(tag) && form.tags.length < 5) {
    form.tags.push(tag)
  }
}

function removeTag(index) {
  form.tags.splice(index, 1)
}

function saveDraft() {
  localStorage.setItem('experience-draft', JSON.stringify(form))
  alert('草稿已保存')
}

async function handleSubmit() {
  if (!form.title || !form.company || !form.position || !form.content) {
    alert('请填写必填项')
    return
  }

  submitting.value = true
  try {
    if (isEditMode.value) {
      await updateMyExperience(route.params.id, form)
      alert('面经已更新，并重新进入审核队列')
      router.push('/my/experiences')
    } else {
      await submitExperience(form)
      localStorage.removeItem('experience-draft')
      alert('投稿成功，内容将进入审核队列')
      router.push('/experiences')
    }
  } catch (e) {
    alert(e.response?.data?.message || '提交失败，请重试')
  } finally {
    submitting.value = false
  }
}

async function loadEditData() {
  try {
    const data = await getMyExperienceDetail(route.params.id)
    Object.assign(form, {
      title: data.title || '',
      company: data.company || '',
      position: data.position || '',
      content: data.content || '',
      level: data.level || '',
      round: data.round || '',
      summary: data.summary || '',
      tags: Array.isArray(data.tags) ? [...data.tags] : [],
      is_anonymous: !!data.is_anonymous
    })
  } catch {
    alert('加载投稿失败')
    router.push('/my/experiences')
  }
}

onMounted(() => {
  if (isEditMode.value) {
    loadEditData()
    return
  }

  const draft = localStorage.getItem('experience-draft')
  if (draft) {
    try {
      Object.assign(form, JSON.parse(draft))
    } catch {
      // ignore malformed draft
    }
  }
})
</script>

<style scoped>
.submit-page {
  min-height: 100vh;
  padding-bottom: 60px;
}

.page-header {
  background: var(--bg-surface);
  padding: 48px 20px 40px;
  text-align: center;
  border-bottom: 1px solid var(--border-default);
}

.page-header h1 {
  font-family: Inter, sans-serif;
  font-size: 32px;
  font-weight: 800;
  margin: 0 0 10px;
  color: var(--text-primary);

}

.page-header p {
  font-size: 16px;
  color: var(--text-muted);
  margin: 0;
}

.form-container {
  max-width: 720px;
  margin: 32px auto 0;
  padding: 0 16px;
}

form {
  background: var(--bg-card);
  border: 1px solid var(--border-default);
  border-radius: 8px;
  padding: 28px;
}

.form-row {
  margin-bottom: 20px;
}

.form-row-2 {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 16px;
}

.form-group {
  margin-bottom: 20px;
}

.form-group label {
  display: block;
  font-size: 14px;
  font-weight: 600;
  color: var(--text-secondary);
  margin-bottom: 8px;
}

.required {
  color: #A3A3A3;
}

input[type="text"],
select,
textarea {
  width: 100%;
  padding: 10px 14px;
  background: var(--bg-surface);
  border: 1px solid var(--border-default);
  border-radius: 8px;
  color: var(--text-primary);
  font-size: 14px;
  outline: none;
  transition: border-color 0.2s;
  box-sizing: border-box;
  font-family: inherit;
}

input:focus,
select:focus,
textarea:focus {
  border-color: var(--accent-primary);
}

textarea {
  resize: vertical;
  line-height: 1.6;
}

.editor-toolbar {
  display: flex;
  gap: 4px;
  margin-bottom: 8px;
  padding: 6px;
  background: var(--bg-surface);
  border: 1px solid var(--border-default);
  border-radius: 8px 8px 0 0;
  border-bottom: none;
  flex-wrap: wrap;
}

.editor-toolbar + textarea,
.editor-toolbar + .markdown-preview {
  border-radius: 0 0 8px 8px;
}

.editor-toolbar button {
  padding: 4px 10px;
  background: transparent;
  border: 1px solid transparent;
  border-radius: 4px;
  color: var(--text-secondary);
  cursor: pointer;
  font-size: 13px;
  transition: all 0.2s;
}

.editor-toolbar button:hover {
  background: var(--bg-hover);
  border-color: var(--border-default);
}

.toolbar-divider {
  width: 1px;
  background: var(--border-default);
  margin: 0 4px;
}

.char-count {
  font-size: 12px;
  color: var(--text-dim);
  padding: 0 4px;
  display: inline-flex;
  align-items: center;
}

.preview-toggle.active {
  background: rgba(128, 128, 128,0.15);
  color: var(--accent-purple);
}

.markdown-preview {
  min-height: 300px;
  padding: 16px;
  background: var(--bg-surface);
  border: 1px solid var(--border-default);
  color: var(--text-primary);
  line-height: 1.8;
  font-size: 14px;
}

.markdown-preview :deep(svg) {
  display: none !important;
}

.markdown-preview :deep(*) {
  max-width: 100%;
}

.markdown-preview :deep(pre) {
  background: #141414;
  color: #f3f4f6;
  padding: 12px;
  border-radius: 8px;
  overflow-x: auto;
}

.markdown-preview :deep(code) {
  background: var(--bg-base);
  padding: 2px 6px;
  border-radius: 4px;
  font-size: 13px;
}

.markdown-preview :deep(blockquote) {
  border-left: 3px solid var(--accent-primary);
  padding: 10px 12px;
  margin: 10px 0;
  color: var(--text-secondary);
  background: var(--bg-hover);
}

.markdown-preview :deep(table) {
  width: 100%;
  border-collapse: collapse;
}

.markdown-preview :deep(th),
.markdown-preview :deep(td) {
  border: 1px solid var(--border-default);
  padding: 8px 10px;
}

.tags-input {
  background: var(--bg-surface);
  border: 1px solid var(--border-default);
  border-radius: 8px;
  padding: 8px;
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  align-items: center;
}

.tags-input input {
  border: none;
  background: transparent;
  flex: 1;
  min-width: 120px;
  padding: 4px;
  font-size: 14px;
  color: var(--text-primary);
}

.tags-input input:focus {
  outline: none;
}

.tags-list {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
}

.tag-item {
  display: flex;
  align-items: center;
  gap: 4px;
  padding: 3px 10px;
  background: rgba(128, 128, 128,0.15);
  color: var(--accent-purple);
  border-radius: 8px;
  font-size: 13px;
}

.tag-item button {
  background: none;
  border: none;
  color: var(--accent-purple);
  cursor: pointer;
  font-size: 16px;
  padding: 0;
  line-height: 1;
}

.suggested-tags {
  margin-top: 8px;
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
  align-items: center;
  font-size: 12px;
  color: var(--text-dim);
}

.suggested-tags button {
  padding: 2px 10px;
  background: var(--bg-hover);
  border: 1px solid var(--border-default);
  border-radius: 8px;
  color: var(--text-muted);
  font-size: 12px;
  cursor: pointer;
  transition: all 0.2s;
}

.suggested-tags button:hover {
  border-color: rgba(128, 128, 128,0.3);
  color: var(--accent-purple);
}

.anonymous-row {
  margin-top: 4px;
}

.switch-label {
  display: flex;
  align-items: center;
  gap: 10px;
  cursor: pointer;
  font-size: 14px;
  color: var(--text-secondary);
}

.switch-label input[type="checkbox"] {
  width: 18px;
  height: 18px;
  accent-color: var(--accent-primary);
}

.form-actions {
  display: flex;
  gap: 12px;
  justify-content: flex-end;
  padding-top: 8px;
}

.btn-draft {
  padding: 10px 24px;
  border-radius: 8px;
  font-size: 14px;
  font-weight: 600;
  background: var(--bg-hover);
  color: var(--text-secondary);
  border: 1px solid var(--border-default);
  cursor: pointer;
  transition: all 0.2s;
}

.btn-submit {
  padding: 10px 32px;
  border-radius: 8px;
  font-size: 14px;
  font-weight: 600;
  background: var(--accent-primary); color: var(--bg-base);
  border: none;
  cursor: pointer;
  transition: all 0.2s;
}

.btn-submit:hover {
  box-shadow: var(--shadow-sm);
}

.btn-submit:disabled {
  opacity: 0.6;
  cursor: not-allowed;
}

@media (max-width: 768px) {
  .page-header { padding: 36px 16px 32px; }
  .page-header h1 { font-size: 26px; }
  form { padding: 20px; }
  .form-row-2 { grid-template-columns: 1fr; }
  .form-actions { flex-direction: column; }
  .btn-draft, .btn-submit { text-align: center; }
}
</style>
