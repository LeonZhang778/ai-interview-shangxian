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
        </div>

        <!-- 标签 -->
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
          <label>内容 <span class="required">*</span> <span class="hint">支持 Markdown 语法</span></label>
          <textarea
            v-model="form.content"
            placeholder="用 Markdown 记录你的学习内容..."
            rows="20"
            class="form-textarea"
          ></textarea>
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
import { createNote, updateNote, getNoteDetail } from '../api/learningNote'

const route = useRoute()
const router = useRouter()

const loading = ref(false)
const saving = ref(false)
const error = ref('')
const isEditMode = computed(() => !!route.params.id)

const form = ref({
  title: '',
  content: '',
  note_type: 'note',
  visibility: 'private',
  status: 'draft',
  tags: '',
})

const typeOptions = [
  { value: 'note', label: '笔记' },
  { value: 'review', label: '复盘' },
  { value: 'mistake', label: '错题' },
  { value: 'experience', label: '面经' },
  { value: 'material', label: '资料' },
]

function goBack() {
  router.push('/learning-notes')
}

async function loadEditData() {
  if (!isEditMode.value) return
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
    }
  } catch (e) {
    error.value = '加载笔记失败'
    console.error(e)
  } finally {
    loading.value = false
  }
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
    error.value = e.message || '保存失败，请重试'
    console.error(e)
  } finally {
    saving.value = false
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
