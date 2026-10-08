<template>
  <StarryBackground />
  <div class="image-studio">
    <div class="studio-header">
      <h1>AI 画图</h1>
      <p>输入文字描述，AI 为你生成图片</p>
    </div>

    <div class="studio-body">
      <!-- 左侧：生成表单 -->
      <div class="generate-panel">
        <div class="panel-card">
          <h3>生成图片</h3>

          <!-- 生图功能被后台关闭时的提示 -->
          <div v-if="!imageEnabled" class="feature-off-notice">
            <span class="notice-icon">🚫</span>
            <span>该生图功能已关闭请稍后再试~</span>
          </div>

          <div class="form-group">
            <label>提示词 <span class="required">*</span></label>
            <textarea
              v-model="form.prompt"
              placeholder="描述你想生成的图片，例如：一只可爱的猫咪坐在窗台上，阳光洒进来"
              rows="4"
            ></textarea>
          </div>

          <div class="form-group">
            <label>反向提示词</label>
            <textarea
              v-model="form.negative_prompt"
              placeholder="不想出现的内容，例如：模糊, 低质量, 扭曲"
              rows="2"
            ></textarea>
          </div>

          <div class="form-row">
            <div class="form-group">
              <label>宽度</label>
              <select v-model="form.width">
                <option :value="256">256</option>
                <option :value="512">512</option>
                <option :value="768">768</option>
                <option :value="1024">1024</option>
              </select>
            </div>
            <div class="form-group">
              <label>高度</label>
              <select v-model="form.height">
                <option :value="256">256</option>
                <option :value="512">512</option>
                <option :value="768">768</option>
                <option :value="1024">1024</option>
              </select>
            </div>
          </div>

          <div class="form-row">
            <div class="form-group">
              <label>步数</label>
              <input type="number" v-model.number="form.steps" min="1" max="50" />
            </div>
            <div class="form-group">
              <label>CFG Scale</label>
              <input type="number" v-model.number="form.cfg_scale" min="1" max="20" />
            </div>
          </div>

          <button
            class="btn-generate"
            @click="handleGenerate"
            :disabled="generating || !form.prompt.trim()"
          >
            <span v-if="generating" class="spinner"></span>
            {{ generating ? '生成中...' : '开始生成' }}
          </button>
        </div>
      </div>

      <!-- 右侧：历史记录 -->
      <div class="history-panel">
        <div class="panel-card">
          <h3>生成记录</h3>

          <div v-if="loading" class="loading-state">加载中...</div>

          <div v-else-if="tasks.length === 0" class="empty-state">
            <p>暂无生成记录</p>
            <p class="sub">在左侧输入提示词开始创作吧</p>
          </div>

          <div v-else class="task-grid">
            <div v-for="task in tasks" :key="task.id" class="task-card">
              <div class="task-image">
                <img v-if="task.image_url" :src="task.image_url" :alt="task.prompt" @click="previewImage(task)" />
                <div v-else class="task-placeholder">
                  <span v-if="task.status === 'pending'">排队中...</span>
                  <span v-else-if="task.status === 'processing'" class="generating-text">生成中...</span>
                  <span v-else-if="task.status === 'failed'" class="error-text">生成失败</span>
                </div>
              </div>
              <div class="task-info">
                <p class="task-prompt" :title="task.prompt">{{ task.prompt }}</p>
                <p v-if="task.status === 'failed' && task.error_message" class="task-error" :title="task.error_message">
                  {{ task.error_message }}
                </p>
                <div class="task-meta">
                  <span class="task-time">{{ formatTime(task.created_at) }}</span>
                  <span class="task-status" :class="task.status">{{ statusText(task.status) }}</span>
                </div>
                <div class="task-actions">
                  <a v-if="task.image_url" :href="task.image_url" download class="btn-download">下载</a>
                  <button class="btn-delete" @click="handleDelete(task.id)">删除</button>
                </div>
              </div>
            </div>
          </div>

          <!-- 分页 -->
          <div v-if="totalPages > 1" class="pagination">
            <button @click="page--" :disabled="page <= 1">上一页</button>
            <span>{{ page }} / {{ totalPages }}</span>
            <button @click="page++" :disabled="page >= totalPages">下一页</button>
          </div>
        </div>
      </div>
    </div>

    <!-- 图片预览模态框 -->
    <div v-if="previewTask" class="preview-overlay" @click.self="previewTask = null">
      <div class="preview-content">
        <img :src="previewTask.image_url" :alt="previewTask.prompt" />
        <p>{{ previewTask.prompt }}</p>
        <button class="preview-close" @click="previewTask = null">关闭</button>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, reactive, onMounted, onUnmounted, watch } from 'vue'
import { generateImage, getImageTasks, getImageTask, deleteImageTask } from '../api/image'
import { getSiteInfo } from '../api/config'
import StarryBackground from '../components/StarryBackground.vue'

const form = reactive({
  prompt: '',
  negative_prompt: '',
  width: 512,
  height: 512,
  steps: 20,
  cfg_scale: 7,
})

const tasks = ref([])
const loading = ref(false)
const generating = ref(false)
// AI 生图功能开关（由后台系统设置控制），默认开启
const imageEnabled = ref(true)
const page = ref(1)
const total = ref(0)
const pageSize = 20
const totalPages = ref(0)
const previewTask = ref(null)
let pollTimer = null

async function loadTasks() {
  loading.value = true
  try {
    const res = await getImageTasks({ page: page.value, size: pageSize })
    tasks.value = res.items || []
    total.value = res.total || 0
    totalPages.value = Math.ceil(total.value / pageSize)
  } catch (e) {
    console.error('加载任务列表失败', e)
  } finally {
    loading.value = false
  }
}

async function handleGenerate() {
  if (!imageEnabled.value) {
    alert('该生图功能已关闭请稍后再试~')
    return
  }
  if (!form.prompt.trim()) return
  generating.value = true
  try {
    await generateImage({
      prompt: form.prompt,
      negative_prompt: form.negative_prompt || undefined,
      width: form.width,
      height: form.height,
      steps: form.steps,
      cfg_scale: form.cfg_scale,
    })
    form.prompt = ''
    form.negative_prompt = ''
    page.value = 1
    await loadTasks()
    startPolling()
  } catch (e) {
    console.error('提交生成任务失败', e)
    const msg = e.response?.data?.message || e.message || '未知错误'
    // 后台已关闭生图时，直接展示开关提示，不额外加前缀
    if (msg.includes('生图功能已关闭')) {
      imageEnabled.value = false
      alert(msg)
    } else {
      alert('提交失败：' + msg)
    }
  } finally {
    generating.value = false
  }
}

async function handleDelete(taskId) {
  if (!confirm('确定删除这张图片？')) return
  try {
    await deleteImageTask(taskId)
    await loadTasks()
  } catch (e) {
    console.error('删除失败', e)
  }
}

function previewImage(task) {
  if (task.image_url) {
    previewTask.value = task
  }
}

function startPolling() {
  stopPolling()
  pollTimer = setInterval(async () => {
    const hasPending = tasks.value.some(t => t.status === 'pending' || t.status === 'processing')
    if (!hasPending) {
      stopPolling()
      return
    }
    // 刷新列表
    try {
      const res = await getImageTasks({ page: page.value, size: pageSize })
      tasks.value = res.items || []
    } catch (e) {
      // 忽略轮询错误
    }
  }, 3000)
}

function stopPolling() {
  if (pollTimer) {
    clearInterval(pollTimer)
    pollTimer = null
  }
}

function formatTime(t) {
  if (!t) return ''
  return t.replace('T', ' ').substring(0, 16)
}

function statusText(status) {
  const map = { pending: '排队中', processing: '生成中', success: '已完成', failed: '失败' }
  return map[status] || status
}

watch(page, () => loadTasks())

onMounted(async () => {
  loadTasks()
  // 读取后台系统设置中的生图开关
  try {
    const info = await getSiteInfo()
    if (info && info.image_generation_enabled === false) {
      imageEnabled.value = false
    }
  } catch (e) {
    // 开关读取失败时不阻断功能，保持默认开启（后端仍有二次校验）
    console.error('读取生图功能开关失败', e)
  }
})

onUnmounted(() => {
  stopPolling()
})
</script>

<style scoped>
.image-studio {
  max-width: 1200px;
  margin: 0 auto;
  padding: 24px 20px;
}
.studio-header {
  text-align: center;
  margin-bottom: 32px;
}
.studio-header h1 {
  font-family: Inter, sans-serif;
  font-size: 28px;
  font-weight: 700;
  background:var(--title-gradient);

  margin-bottom: 8px;
}
.studio-header p { color: var(--text-muted); font-size: 15px; }

.studio-body {
  display: grid;
  grid-template-columns: 360px 1fr;
  gap: 24px;
  align-items: start;
}
@media (max-width: 768px) { .studio-body { grid-template-columns: 1fr; } }

/* 生图功能关闭提示 */
.feature-off-notice {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 10px 12px;
  margin-bottom: 16px;
  border-radius: 8px;
  background: rgba(128, 128, 128, 0.1);
  border: 1px solid rgba(128, 128, 128, 0.35);
  color: #A3A3A3;
  font-size: 13px;
  line-height: 1.4;
}
.feature-off-notice .notice-icon { flex-shrink: 0; }

.panel-card {
  background: var(--bg-card);
  border: 1px solid var(--border-default);
  border-radius: 8px;
  padding: 24px;
}
.panel-card h3 {
  font-size: 16px;
  font-weight: 600;
  margin-bottom: 20px;
  color: var(--accent-light);
}

.form-group { margin-bottom: 16px; }
.form-group label {
  display: block;
  font-size: 13px;
  font-weight: 500;
  color: var(--text-secondary);
  margin-bottom: 6px;
}
.required { color: var(--red); }

.form-group textarea,
.form-group select {
  width: 100%;
  padding: 10px 12px;
  border:1px solid var(--border-default);
  border-radius: 8px;
  font-size: 14px;
  transition: border-color 0.2s;
  box-sizing: border-box;
  background: var(--bg-card);
  color: var(--text-primary);
}
.form-group textarea::placeholder { color: var(--text-dim); }
.form-group textarea:focus,
.form-group select:focus {
  outline: none;
  border-color: rgba(128, 128, 128,0.35);
  box-shadow: var(--shadow-sm);
  background: rgba(128, 128, 128,0.07);
}

.form-row { display: grid; grid-template-columns: 1fr 1fr; gap: 12px; }

.btn-generate {
  width: 100%;
  padding: 12px;
  background: var(--accent-primary); color: var(--bg-base);
  border: none;
  border-radius: 8px;
  font-size: 15px;
  font-weight: 600;
  cursor: pointer;
  transition: all 0.3s;
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 8px;
  box-shadow: var(--shadow-sm);
}
.btn-generate:hover:not(:disabled) { transform: translateY(-1px); box-shadow: var(--shadow-sm); }
.btn-generate:disabled { opacity: 0.5; cursor: not-allowed; transform: none; }

.spinner {
  width: 16px; height: 16px;
  border: 2px solid rgba(255,255,255,0.3);
  border-top-color: white;
  border-radius: 50%;
  animation: spin 0.8s linear infinite;
}
@keyframes spin { to { transform: rotate(360deg); } }

.loading-state, .empty-state { text-align: center; padding: 40px 0; color: var(--text-dim); }
.empty-state .sub { font-size: 13px; margin-top: 4px; }

.task-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(220px, 1fr));
  gap: 16px;
}
.task-card {
  border: 1px solid var(--border-default);
  border-radius: 8px;
  overflow: hidden;
  transition: all 0.3s;
  background: var(--bg-card);
}
.task-card:hover {
  border-color: var(--border-hover);
  box-shadow: var(--shadow-sm);
}

.task-image { width: 100%; height: 180px; background: var(--bg-card); overflow: hidden; }
.task-image img { width: 100%; height: 100%; object-fit: cover; cursor: pointer; transition: transform 0.3s; }
.task-image img:hover { transform: scale(1.05); }
.task-placeholder { width: 100%; height: 100%; display: flex; align-items: center; justify-content: center; color: var(--text-dim); font-size: 14px; }
.generating-text { color: var(--accent-primary); font-weight: 500; }
.error-text { color: var(--red); }

.task-info { padding: 12px; }
.task-prompt { font-size: 13px; color: var(--text-secondary); margin: 0 0 8px; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.task-error {
  font-size: 12px;
  color: var(--red);
  line-height: 1.5;
  margin: -2px 0 8px;
  display: -webkit-box;
  -webkit-line-clamp: 2;
  -webkit-box-orient: vertical;
  overflow: hidden;
}
.task-meta { display: flex; justify-content: space-between; align-items: center; margin-bottom: 8px; }
.task-time { font-size: 12px; color: var(--text-dim); }
.task-status { font-size: 12px; padding: 2px 8px; border-radius: 8px; }
.task-status.pending { background: rgba(128, 128, 128,0.1); color: var(--amber); }
.task-status.processing { background: rgba(128, 128, 128,0.1); color: var(--accent-purple); }
.task-status.success { background: rgba(128, 128, 128,0.1); color: var(--green); }
.task-status.failed { background: rgba(128, 128, 128,0.1); color: var(--red); }

.task-actions { display: flex; gap: 8px; }
.btn-download {
  flex: 1; padding: 6px 0;
  background: var(--accent-primary); color: var(--bg-base); border: none; border-radius: 6px;
  font-size: 12px; text-align: center; text-decoration: none; cursor: pointer;
}
.btn-delete {
  flex: 1; padding: 6px 0;
  background: var(--bg-hover);
  color: var(--text-muted); border: 1px solid var(--border-default);
  border-radius: 6px; font-size: 12px; cursor: pointer;
}
.btn-delete:hover { background: rgba(128, 128, 128,0.1); color: var(--red); border-color: rgba(128, 128, 128,0.15); }

.pagination {
  display: flex; justify-content: center; align-items: center; gap: 16px;
  margin-top: 20px; padding-top: 16px; border-top: 1px solid var(--border-default);
}
.pagination button {
  padding: 6px 16px; border:1px solid var(--border-default);
  background: var(--bg-hover); border-radius: 6px;
  font-size: 13px; cursor: pointer; color: var(--accent-purple);
}
.pagination button:disabled { opacity: 0.4; cursor: not-allowed; }
.pagination span { font-size: 13px; color: var(--text-muted); }

.preview-overlay {
  position: fixed; inset: 0; background: rgba(0,0,0,0.85);
  display: flex; align-items: center; justify-content: center; z-index: 1000;
}
.preview-content { max-width: 90vw; max-height: 90vh; text-align: center; }
.preview-content img { max-width: 100%; max-height: 80vh; border-radius: 8px; }
.preview-content p { color: var(--text-primary); margin: 12px 0; font-size: 14px; }
.preview-close {
  padding: 8px 24px; background: rgba(128, 128, 128,0.15);
  color: var(--text-primary); border: 1px solid rgba(128, 128, 128,0.2);
  border-radius: 6px; cursor: pointer;
}
</style>
