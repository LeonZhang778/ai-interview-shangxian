<template>
  <div class="my-files">
    <div class="files-header">
      <p class="files-title">我的文件</p>
      <div class="files-actions">
        <button
          class="action-btn"
          type="button"
          :disabled="loading"
          @click="loadFiles"
          :aria-label="'刷新文件列表'"
        >
          <svg
            :class="{ 'spinning': loading }"
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
      </div>
    </div>

    <!-- 类型筛选 -->
    <div class="filter-row">
      <button
        v-for="opt in filterOptions"
        :key="opt.value"
        :class="['filter-chip', { active: filterType === opt.value }]"
        type="button"
        @click="filterType = opt.value; loadFiles()"
      >
        {{ opt.label }}
      </button>
    </div>

    <!-- 错误态 -->
    <div v-if="store.filesError" class="files-error-state">
      <svg width="28" height="28" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round">
        <circle cx="12" cy="12" r="10" />
        <line x1="12" y1="8" x2="12" y2="12" />
        <line x1="12" y1="16" x2="12.01" y2="16" />
      </svg>
      <p class="error-text">{{ store.filesError }}</p>
      <button class="action-btn" type="button" @click="loadFiles">重试</button>
    </div>

    <!-- 加载态 -->
    <div v-else-if="loading && !files.length" class="files-loading">
      <div class="loading-spinner"></div>
      <p class="loading-text">加载中...</p>
    </div>

    <!-- 空态 -->
    <div v-else-if="!files.length" class="files-empty">
      <svg width="28" height="28" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round">
        <path d="M13 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V9z" />
        <polyline points="13 2 13 9 20 9" />
      </svg>
      <p class="empty-text">暂无文件</p>
    </div>

    <!-- 文件列表 -->
    <div v-else class="files-list">
      <div
        v-for="file in files"
        :key="file.id"
        class="file-card"
      >
        <div class="file-card-icon">
          <svg v-if="file.media_type === 'video'" width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round">
            <polygon points="23 7 16 12 23 17 23 7" />
            <rect x="1" y="5" width="15" height="14" rx="2" ry="2" />
          </svg>
          <svg v-else-if="file.media_type === 'audio'" width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round">
            <path d="M9 18V5l12-2v13" />
            <circle cx="6" cy="18" r="3" />
            <circle cx="18" cy="16" r="3" />
          </svg>
          <svg v-else width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round">
            <path d="M13 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V9z" />
            <polyline points="13 2 13 9 20 9" />
          </svg>
        </div>
        <div class="file-card-info">
          <p class="file-card-name" :title="file.original_name">{{ file.original_name }}</p>
          <div class="file-card-meta">
            <span class="file-size-cell">{{ formatBytes(file.size_bytes) }}</span>
            <span v-if="file.duration_ms">{{ formatDuration(file.duration_ms) }}</span>
            <span>{{ file.source_format?.toUpperCase() }}</span>
          </div>
        </div>
        <div class="file-card-actions">
          <button
            class="file-btn file-btn-delete"
            type="button"
            title="删除"
            :aria-label="'删除文件'"
            @click="handleDelete(file)"
          >
            <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
              <polyline points="3 6 5 6 21 6" />
              <path d="M19 6v14a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V6m3 0V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2" />
            </svg>
          </button>
        </div>
      </div>
    </div>

    <!-- 分页 -->
    <div v-if="total > pageSize" class="pagination-row">
      <button
        :disabled="page <= 1"
        class="page-btn"
        type="button"
        @click="page--; loadFiles()"
      >
        上一页
      </button>
      <span class="page-info">{{ page }} / {{ totalPages }}</span>
      <button
        :disabled="page >= totalPages"
        class="page-btn"
        type="button"
        @click="page++; loadFiles()"
      >
        下一页
      </button>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted, computed } from 'vue'
import { listMediaFiles, deleteMediaFile } from '../../api/mediaTool'
import { useMediaStore } from '../../stores/media'

const store = useMediaStore()

const files = ref([])
const loading = ref(false)
const page = ref(1)
const pageSize = 20
const total = ref(0)
const filterType = ref('')

const filterOptions = [
  { value: '', label: '全部' },
  { value: 'video', label: '视频' },
  { value: 'audio', label: '音频' },
  { value: 'image', label: '图片' },
]

const totalPages = computed(() => Math.max(1, Math.ceil(total.value / pageSize)))

function formatBytes(bytes) {
  if (!bytes) return '0 B'
  const units = ['B', 'KB', 'MB', 'GB']
  const index = Math.min(Math.floor(Math.log(bytes) / Math.log(1024)), units.length - 1)
  return `${(bytes / (1024 ** index)).toFixed(index ? 1 : 0)} ${units[index]}`
}

function formatDuration(ms) {
  if (!ms) return ''
  const seconds = Math.round(ms / 1000)
  const m = Math.floor(seconds / 60)
  const s = seconds % 60
  return `${String(m).padStart(2, '0')}:${String(s).padStart(2, '0')}`
}

async function loadFiles() {
  loading.value = true
  try {
    const params = { page: page.value, size: pageSize }
    if (filterType.value) params.media_type = filterType.value
    const result = await listMediaFiles(params)
    files.value = result.items || []
    total.value = result.total || 0
    store.filesError = ''
  } catch (error) {
    store.filesError = store.mapError(error)
  } finally {
    loading.value = false
  }
}

async function handleDelete(file) {
  if (!window.confirm('删除后该文件不可恢复，引用它的任务将无法重试。确定删除？')) return
  try {
    await deleteMediaFile(file.id)
    files.value = files.value.filter(f => f.id !== file.id)
    total.value = Math.max(0, total.value - 1)
    store.addToast('文件已删除', 'success')
  } catch (error) {
    store.addToast(store.mapError(error), 'error')
  }
}

onMounted(() => {
  loadFiles()
})
</script>

<style scoped>
.my-files {
  width: 100%;
}
.files-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 12px;
}
.files-title {
  color: var(--text-secondary);
  font-size: 12px;
  font-weight: 600;
  margin: 0;
  letter-spacing: .04em;
}
.files-actions {
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

/* 筛选 */
.filter-row {
  display: flex;
  gap: 6px;
  margin-bottom: 12px;
}
.filter-chip {
  padding: 4px 10px;
  border: 1px solid var(--border-default);
  border-radius: 6px;
  background: var(--bg-input);
  color: var(--text-muted);
  font-size: 11px;
  cursor: pointer;
  transition: border-color .15s, color .15s;
}
.filter-chip.active {
  border-color: var(--accent-primary);
  color: var(--text-primary);
}
.filter-chip:hover:not(.active) {
  border-color: var(--border-hover);
}

/* 加载态 */
.files-loading {
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
.files-empty {
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

/* 错误态 */
.files-error-state {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 10px;
  padding: 30px 0;
  color: var(--red);
}
.files-error-state .error-text {
  font-size: 13px;
  margin: 0;
  text-align: center;
  line-height: 1.5;
  overflow-wrap: anywhere;
}

/* 文件列表 */
.files-list {
  display: flex;
  flex-direction: column;
  gap: 6px;
}
.file-card {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 8px 10px;
  border: 1px solid var(--border-default);
  border-radius: 8px;
  background: var(--bg-card);
}
.file-card-icon {
  flex-shrink: 0;
  color: var(--text-muted);
  display: grid;
  place-items: center;
}
.file-card-info {
  flex: 1;
  min-width: 0;
}
.file-card-name {
  color: var(--text-primary);
  font-size: 12px;
  font-weight: 500;
  margin: 0 0 3px;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.file-card-meta {
  display: flex;
  gap: 8px;
  color: var(--text-muted);
  font-size: 10px;
}
.file-card-actions {
  flex-shrink: 0;
}
.file-btn {
  width: 28px;
  height: 28px;
  display: grid;
  place-items: center;
  border: none;
  background: transparent;
  border-radius: 6px;
  cursor: pointer;
  color: var(--text-muted);
  transition: background .15s, color .15s;
}
.file-btn-delete:hover {
  color: var(--red);
  background: var(--red-bg);
}

/* 分页 */
.pagination-row {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 10px;
  margin-top: 14px;
}
.page-btn {
  padding: 5px 12px;
  border: 1px solid var(--border-default);
  border-radius: 6px;
  background: var(--bg-input);
  color: var(--text-secondary);
  font-size: 11px;
  cursor: pointer;
  transition: border-color .15s;
}
.page-btn:hover:not(:disabled) {
  border-color: var(--accent-primary);
}
.page-btn:disabled {
  opacity: .4;
  cursor: not-allowed;
}
.page-info {
  color: var(--text-muted);
  font-size: 11px;
}

/* 移动端断点 */
@media (max-width: 640px) {
  .file-card {
    gap: 8px;
    padding: 8px 10px;
  }
  .file-card-info {
    min-width: 0;
    overflow: hidden;
  }
  .file-card-name {
    min-width: 0;
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
  }
  .file-card-meta {
    flex-wrap: wrap;
    gap: 6px;
  }
  .file-card-meta .file-size-cell {
    width: 72px;
    flex-shrink: 0;
    text-align: right;
  }
  .file-card-actions {
    flex-shrink: 0;
  }
}

@keyframes spin { to { transform: rotate(360deg); } }
</style>