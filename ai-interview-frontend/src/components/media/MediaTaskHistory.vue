<template>
  <div class="task-history">
    <div class="task-header">
      <p class="task-title">任务历史</p>
      <div class="task-actions">
        <button
          class="action-btn"
          type="button"
          :disabled="store.tasksLoading"
          @click="handleRefresh"
          :aria-label="store.tasksLoading ? '刷新中' : '刷新任务列表'"
        >
          <svg
            :class="{ 'spinning': store.tasksLoading }"
            width="14"
            height="14"
            viewBox="0 0 24 24"
            fill="none"
            stroke="currentColor"
            stroke-width="2"
            stroke-linecap="round"
            stroke-linejoin="round"
          >
            <polyline points="23 4 23 10 17 10" />
            <polyline points="1 20 1 14 7 14" />
            <path d="M3.51 9a9 9 0 0 1 14.85-3.36L23 10M1 14l4.64 4.36A9 9 0 0 0 20.49 15" />
          </svg>
          <span>刷新</span>
        </button>
        <!-- 批量重试 -->
        <button
          v-if="failedTasks.length > 0"
          class="action-btn action-btn-retry"
          type="button"
          :disabled="!selectedFailedIds.length"
          @click="handleBatchRetry"
          :aria-label="'批量重试失败任务'"
        >
          <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
            <polyline points="23 4 23 10 17 10" />
            <polyline points="1 20 1 14 7 14" />
            <path d="M3.51 9a9 9 0 0 1 14.85-3.36L23 10M1 14l4.64 4.36A9 9 0 0 0 20.49 15" />
          </svg>
          <span>重试 {{ selectedFailedIds.length ? `(${selectedFailedIds.length})` : '' }}</span>
        </button>
        <button
          class="action-btn"
          type="button"
          @click="handleClearAll"
          :disabled="!hasCompletedTasks"
          :aria-label="'清空已完成任务'"
        >
          <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
            <polyline points="3 6 5 6 21 6" />
            <path d="M19 6v14a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V6m3 0V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2" />
          </svg>
          <span>清空已完成</span>
        </button>
      </div>
    </div>

    <!-- 批量选择提示 -->
    <div v-if="failedTasks.length > 1" class="batch-hint">
      <label class="batch-checkbox-label">
        <input
          type="checkbox"
          :checked="allFailedSelected"
          :indeterminate="someFailedSelected && !allFailedSelected"
          @change="toggleAllFailed"
        />
        <span>全选失败任务</span>
      </label>
    </div>

    <!-- 加载态 -->
    <div v-if="store.tasksLoading && !store.tasks.length" class="task-loading">
      <div class="loading-spinner"></div>
      <p class="loading-text">加载中...</p>
    </div>

    <!-- 空态 -->
    <div v-else-if="!store.tasks.length" class="task-empty">
      <svg width="28" height="28" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round">
        <path d="M9 11l3 3L22 4" />
        <path d="M21 12v7a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h11" />
      </svg>
      <p class="empty-text">暂无任务记录</p>
    </div>

    <!-- 任务列表 -->
    <div v-else class="task-list">
      <div
        v-for="task in store.tasks"
        :key="task.id"
        :class="['task-card', `task-${task.status}`]"
      >
        <div class="task-card-top">
          <!-- 批量选择框（仅失败任务） -->
          <label v-if="task.status === 'failed'" class="task-select" @click.stop>
            <input
              type="checkbox"
              :checked="selectedFailedIds.includes(task.id)"
              @change="toggleFailed(task.id)"
            />
          </label>
          <div class="task-card-info">
            <p class="task-card-name">{{ store.toolName(task.tool_code || task.tool_name) }}</p>
            <div class="task-card-meta">
              <span :class="['task-status-badge', `status-${task.status}`]">
                {{ store.statusLabel(task.status) }}
              </span>
              <span class="task-time">{{ store.formatDate(task.created_at) }}</span>
            </div>
          </div>
          <div class="task-card-actions">
            <!-- 预览（已完成且输出文件信息可用） -->
            <button
              v-if="task.status === 'completed' && task.output_file"
              class="task-btn task-btn-preview"
              type="button"
              title="预览"
              :aria-label="'预览任务结果'"
              @click="handlePreview(task)"
            >
              <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                <polygon points="5 3 19 12 5 21 5 3" />
              </svg>
            </button>
            <!-- 下载（已完成） -->
            <button
              v-if="task.status === 'completed'"
              class="task-btn task-btn-download"
              type="button"
              title="下载"
              :aria-label="'下载任务结果'"
              @click="store.downloadTask(task.id)"
            >
              <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4" />
                <polyline points="7 10 12 15 17 10" />
                <line x1="12" y1="15" x2="12" y2="3" />
              </svg>
            </button>
            <!-- 取消（排队/处理中） -->
            <button
              v-if="isActive(task.status)"
              class="task-btn task-btn-cancel"
              type="button"
              title="取消"
              :aria-label="'取消任务'"
              @click="store.cancelTask(task.id)"
            >
              <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                <circle cx="12" cy="12" r="10" />
                <line x1="4.93" y1="4.93" x2="19.07" y2="19.07" />
              </svg>
            </button>
            <!-- 重试（失败） -->
            <button
              v-if="task.status === 'failed'"
              class="task-btn task-btn-retry"
              type="button"
              title="重试"
              :aria-label="'重试任务'"
              @click="store.retryTask(task.id)"
            >
              <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                <polyline points="23 4 23 10 17 10" />
                <polyline points="1 20 1 14 7 14" />
                <path d="M3.51 9a9 9 0 0 1 14.85-3.36L23 10M1 14l4.64 4.36A9 9 0 0 0 20.49 15" />
              </svg>
            </button>
            <!-- 删除（非活跃状态） -->
            <button
              v-if="!isActive(task.status)"
              class="task-btn task-btn-delete"
              type="button"
              title="删除"
              :aria-label="'删除任务记录'"
              @click="store.deleteTask(task.id)"
            >
              <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                <polyline points="3 6 5 6 21 6" />
                <path d="M19 6v14a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V6m3 0V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2" />
              </svg>
            </button>
          </div>
        </div>

        <!-- 进度条 -->
        <div v-if="task.status === 'processing'" class="task-progress">
          <div class="task-progress-bar">
            <div class="task-progress-fill" :style="{ width: (task.progress || 0) + '%' }"></div>
          </div>
          <span class="task-progress-text">{{ task.progress || 0 }}%</span>
        </div>

        <!-- 错误信息 -->
        <p v-if="task.status === 'failed' && task.error_message" class="task-error">
          {{ task.error_message }}
        </p>
      </div>
    </div>

    <!-- 预览弹窗 -->
    <div v-if="previewTask" class="preview-overlay" @click.self="closePreview">
      <div class="preview-modal">
        <div class="preview-header">
          <p class="preview-title">{{ store.toolName(previewTask.tool_code || previewTask.tool_name) }} - 预览</p>
          <button class="preview-close" type="button" @click="closePreview" aria-label="关闭预览">&times;</button>
        </div>
        <div class="preview-body">
          <video
            v-if="previewMediaType === 'video'"
            :src="previewUrl"
            controls
            class="preview-video"
          ></video>
          <audio
            v-else-if="previewMediaType === 'audio'"
            :src="previewUrl"
            controls
            class="preview-audio"
          ></audio>
          <img
            v-else-if="previewMediaType === 'image'"
            :src="previewUrl"
            :alt="previewTask.output_file?.original_name || '任务结果预览'"
            class="preview-image"
          />
          <div v-else class="preview-unavailable">
            <p>无法预览该格式</p>
            <a :href="previewUrl" target="_blank" class="preview-download-link">下载文件</a>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { computed, ref } from 'vue'
import { useMediaStore } from '../../stores/media'
import { useAuthStore } from '../../stores/auth'
import { getMediaTaskDownload } from '../../api/mediaTool'

const store = useMediaStore()
const authStore = useAuthStore()

const selectedFailedIds = ref([])
const previewTask = ref(null)
const previewUrl = ref('')
const previewMediaType = ref('')

const failedTasks = computed(() => {
  return store.tasks.filter(t => t.status === 'failed')
})

const allFailedSelected = computed(() => {
  return failedTasks.value.length > 0 && selectedFailedIds.value.length === failedTasks.value.length
})

const someFailedSelected = computed(() => {
  return selectedFailedIds.value.length > 0 && selectedFailedIds.value.length < failedTasks.value.length
})

const hasCompletedTasks = computed(() => {
  return store.tasks.some(t => !isActive(t.status))
})

function isActive(status) {
  return ['queued', 'pending', 'processing'].includes(status)
}

function toggleFailed(id) {
  const idx = selectedFailedIds.value.indexOf(id)
  if (idx >= 0) {
    selectedFailedIds.value.splice(idx, 1)
  } else {
    selectedFailedIds.value.push(id)
  }
}

function toggleAllFailed() {
  if (allFailedSelected.value) {
    selectedFailedIds.value = []
  } else {
    selectedFailedIds.value = failedTasks.value.map(t => t.id)
  }
}

function handleRefresh() {
  store.loadTasks()
}

function handleClearAll() {
  store.deleteAllCompleted()
}

async function handleBatchRetry() {
  if (!selectedFailedIds.value.length) return
  await store.retryMultipleTasks([...selectedFailedIds.value])
  selectedFailedIds.value = []
}

async function handlePreview(task) {
  try {
    if (previewUrl.value?.startsWith('blob:')) {
      URL.revokeObjectURL(previewUrl.value)
    }
    const result = await getMediaTaskDownload(task.id)
    const url = result.download_url.startsWith('http')
      ? result.download_url
      : `${window.location.origin}${result.download_url}`
    const response = await fetch(url, {
      headers: authStore.token ? { Authorization: `Bearer ${authStore.token}` } : {}
    })
    if (!response.ok) throw new Error('预览下载失败')
    previewUrl.value = URL.createObjectURL(await response.blob())
    previewTask.value = task
    const mediaType = task.output_file?.media_type || ''
    const sourceFormat = (task.output_file?.source_format || '').toLowerCase()
    previewMediaType.value = mediaType === 'video' || mediaType === 'audio' || mediaType === 'image'
      ? mediaType
      : sourceFormat === 'gif'
        ? 'image'
        : ''
  } catch {
    store.addToast('获取预览地址失败', 'error')
  }
}

function closePreview() {
  if (previewUrl.value?.startsWith('blob:')) {
    URL.revokeObjectURL(previewUrl.value)
  }
  previewTask.value = null
  previewUrl.value = ''
  previewMediaType.value = ''
}
</script>

<style scoped>
.task-history {
  width: 100%;
}

/* 头部 */
.task-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 14px;
}
.task-title {
  color: var(--text-secondary);
  font-size: 12px;
  font-weight: 600;
  margin: 0;
  letter-spacing: .04em;
}
.task-actions {
  display: flex;
  gap: 6px;
}
.action-btn {
  display: flex;
  align-items: center;
  gap: 4px;
  padding: 5px 10px;
  border: 1px solid var(--border-default);
  border-radius: 7px;
  background: var(--bg-input);
  color: var(--text-secondary);
  font-size: 11px;
  cursor: pointer;
  transition: border-color .15s, color .15s, background .15s;
}
.action-btn:hover:not(:disabled) {
  border-color: var(--accent-primary);
  color: var(--text-primary);
  background: var(--bg-hover);
}
.action-btn:disabled {
  opacity: .5;
  cursor: not-allowed;
}
.action-btn-retry {
  color: var(--accent-primary);
}
.action-btn-retry:hover:not(:disabled) {
  border-color: var(--accent-primary);
}

/* 批量选择提示 */
.batch-hint {
  margin-bottom: 10px;
  padding: 6px 4px;
}
.batch-checkbox-label {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  color: var(--text-muted);
  font-size: 12px;
  cursor: pointer;
}
.batch-checkbox-label input {
  accent-color: var(--accent-primary);
}

/* 加载态 */
.task-loading {
  display: flex;
  flex-direction: column;
  align-items: center;
  padding: 30px 0;
}
.loading-spinner {
  width: 24px;
  height: 24px;
  border: 2px solid var(--border-default);
  border-top-color: var(--accent-cyan);
  border-radius: 50%;
  animation: spin .8s linear infinite;
}
.loading-text {
  color: var(--text-muted);
  font-size: 13px;
  margin: 10px 0 0;
}

/* 空态 */
.task-empty {
  display: flex;
  flex-direction: column;
  align-items: center;
  padding: 30px 0;
  color: var(--text-muted);
}
.empty-text {
  font-size: 13px;
  margin: 8px 0 0;
}

/* 任务列表 */
.task-list {
  display: flex;
  flex-direction: column;
  gap: 8px;
}
.task-card {
  border: 1px solid var(--border-default);
  border-radius: 9px;
  padding: 9px 11px;
  background: var(--bg-card);
}
.task-card-top {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  gap: 8px;
}
.task-select {
  display: flex;
  align-items: center;
  padding-top: 2px;
  flex-shrink: 0;
}
.task-select input {
  accent-color: var(--accent-primary);
}
.task-card-info {
  flex: 1;
  min-width: 0;
}
.task-card-name {
  color: var(--text-primary);
  font-size: 13px;
  font-weight: 600;
  margin: 0 0 4px;
}
.task-card-meta {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 6px;
}
.task-status-badge {
  font-size: 11px;
  padding: 2px 7px;
  border-radius: 4px;
  font-weight: 500;
}
.status-queued,
.status-pending {
  color: var(--accent-cyan);
  background: rgba(6, 182, 212, .12);
}
.status-processing {
  color: #fbbf24;
  background: rgba(251, 191, 36, .12);
}
.status-completed {
  color: var(--green);
  background: var(--green-bg);
}
.status-failed {
  color: var(--red);
  background: var(--red-bg);
}
.status-cancelled {
  color: var(--text-muted);
  background: var(--bg-hover);
}
.task-time {
  color: var(--text-muted);
  font-size: 11px;
}

/* 操作按钮 */
.task-card-actions {
  display: flex;
  gap: 4px;
  flex-shrink: 0;
}
.task-btn {
  width: 28px;
  height: 28px;
  display: grid;
  place-items: center;
  border: none;
  background: transparent;
  border-radius: 6px;
  cursor: pointer;
  transition: background .15s, color .15s;
}
.task-btn-preview {
  color: var(--accent-primary);
}
.task-btn-preview:hover {
  background: var(--bg-hover);
}
.task-btn-download {
  color: var(--accent-cyan);
}
.task-btn-download:hover {
  background: rgba(6, 182, 212, .12);
}
.task-btn-cancel {
  color: #fbbf24;
}
.task-btn-cancel:hover {
  background: rgba(251, 191, 36, .12);
}
.task-btn-retry {
  color: var(--accent-primary);
}
.task-btn-retry:hover {
  background: var(--bg-hover);
}
.task-btn-delete {
  color: var(--text-muted);
}
.task-btn-delete:hover {
  color: var(--red);
  background: var(--red-bg);
}

/* 进度条 */
.task-progress {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-top: 8px;
}
.task-progress-bar {
  flex: 1;
  height: 6px;
  border-radius: 999px;
  background: var(--border-default);
  overflow: hidden;
  position: relative;
}
.task-progress-bar::after {
  content: '';
  position: absolute;
  inset: 0;
  background: linear-gradient(90deg, transparent, rgba(255,255,255,.35), transparent);
  transform: translateX(-100%);
  animation: progress-shimmer 1.35s ease-in-out infinite;
}
.task-progress-fill {
  height: 100%;
  min-width: 10px;
  background:
    linear-gradient(90deg, rgba(255,255,255,.25), transparent 35%, rgba(255,255,255,.25) 70%, transparent),
    var(--accent-gradient);
  background-size: 42px 100%, 100% 100%;
  border-radius: 999px;
  transition: width .3s ease;
  animation: progress-flow .85s linear infinite;
}
.task-progress-text {
  color: var(--text-muted);
  font-size: 11px;
  flex-shrink: 0;
}

/* 错误信息 */
.task-error {
  color: var(--red);
  font-size: 11px;
  margin: 6px 0 0;
  padding: 6px 8px;
  border-radius: 5px;
  background: var(--red-bg);
  line-height: 1.4;
}

/* 预览弹窗 */
.preview-overlay {
  position: fixed;
  inset: 0;
  z-index: 1000;
  background: rgba(0,0,0,.6);
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 24px;
}
.preview-modal {
  background: var(--bg-card);
  border: 1px solid var(--border-default);
  border-radius: 14px;
  max-width: 800px;
  width: 100%;
  max-height: 90vh;
  display: flex;
  flex-direction: column;
  overflow: hidden;
}
.preview-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 14px 18px;
  border-bottom: 1px solid var(--border-default);
}
.preview-title {
  color: var(--text-primary);
  font-size: 14px;
  font-weight: 600;
  margin: 0;
}
.preview-close {
  width: 32px;
  height: 32px;
  display: grid;
  place-items: center;
  border: none;
  background: transparent;
  color: var(--text-muted);
  font-size: 20px;
  cursor: pointer;
  border-radius: 8px;
  transition: background .15s;
}
.preview-close:hover {
  background: var(--bg-hover);
  color: var(--text-primary);
}
.preview-body {
  padding: 18px;
  display: flex;
  justify-content: center;
  align-items: center;
}
.preview-video {
  max-width: 100%;
  max-height: 60vh;
  border-radius: 8px;
}
.preview-audio {
  width: 100%;
  max-width: 400px;
}
.preview-image {
  display: block;
  max-width: 100%;
  max-height: 60vh;
  object-fit: contain;
  border-radius: 8px;
}
.preview-unavailable {
  text-align: center;
  color: var(--text-muted);
  font-size: 13px;
  padding: 30px 0;
}
.preview-download-link {
  display: inline-block;
  margin-top: 12px;
  color: var(--accent-primary);
  text-decoration: underline;
}

/* 动画 */
.spinning {
  animation: spin .8s linear infinite;
}
@keyframes spin { to { transform: rotate(360deg); } }
@keyframes progress-flow {
  from { background-position: 0 0, 0 0; }
  to { background-position: 42px 0, 0 0; }
}
@keyframes progress-shimmer {
  0% { transform: translateX(-100%); }
  55%, 100% { transform: translateX(100%); }
}
</style>
