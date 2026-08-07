<template>
  <div class="tool-page">
    <div class="tool-header">
      <div>
        <p class="tool-kicker">STEP 01</p>
        <h2>视频合并</h2>
      </div>
      <span class="format-hint">支持 {{ allowedExtensions }}</span>
    </div>

    <MediaFileDropZone
      :accept="acceptTypes"
      :max-size-mb="maxFileSize"
      multiple
      @files-selected="onFilesSelected"
      @error="onError"
    />

    <div v-if="store.files.length > 0" class="file-list-section">
      <p class="file-list-label">已选文件（拖拽调整顺序）</p>
      <div
        v-for="(file, index) in store.files"
        :key="file.id"
        class="file-list-item"
      >
        <span class="file-index">{{ index + 1 }}</span>
        <div class="file-info">
          <span class="file-name">{{ file.name || file.original_name || '未知文件' }}</span>
          <span class="file-size">{{ store.formatBytes(file.size) }}</span>
        </div>
        <div class="file-actions">
          <button
            class="move-btn"
            :disabled="index === 0"
            title="上移"
            @click="moveUp(index)"
          >
            ↑
          </button>
          <button
            class="move-btn"
            :disabled="index === store.files.length - 1"
            title="下移"
            @click="moveDown(index)"
          >
            ↓
          </button>
          <button class="remove-btn" title="移除" @click="removeFile(file.id)">✕</button>
        </div>
      </div>
    </div>

    <div v-if="store.files.length >= 2" class="submit-section">
      <p v-if="store.errorMessage" class="error-message" role="alert">{{ store.errorMessage }}</p>
      <button
        class="submit-button"
        type="button"
        :disabled="store.uploading"
        @click="handleSubmit"
      >
        <span v-if="submitting" class="button-spinner"></span>
        {{ submitting ? '提交中...' : '开始合并' }}
      </button>
    </div>

    <div v-else-if="store.files.length > 0 && store.files.length < 2" class="empty-hint">
      请至少选择 2 个视频文件进行合并。
    </div>

    <div v-else-if="!store.uploading" class="empty-hint">
      选择多个视频文件，按顺序合并为一个。
    </div>

    <div class="history-section">
      <MediaTaskHistory />
    </div>
  </div>
</template>

<script setup>
import { computed, onMounted, ref } from 'vue'
import { useMediaStore } from '../../stores/media'
import MediaFileDropZone from '../../components/media/MediaFileDropZone.vue'
import MediaTaskHistory from '../../components/media/MediaTaskHistory.vue'

const store = useMediaStore()
const submitting = ref(false)

const allowedExtensions = computed(() => {
  const formats = store.capabilities.formats || ['mp4', 'mov', 'mkv', 'webm']
  return formats.slice(0, 8).join('、')
})

const acceptTypes = computed(() => {
  const formats = store.capabilities.formats || []
  return formats.map(f => `.${f}`).join(',') || 'video/*'
})

const maxFileSize = computed(() => store.capabilities.max_file_size_mb || 500)

function onFilesSelected(files) {
  store.setFiles(files)
}

function onError(message) {
  store.errorMessage = message
}

function removeFile(fileId) {
  store.removeFile(fileId)
}

function moveUp(index) {
  if (index > 0) {
    store.reorderFiles(index, index - 1)
  }
}

function moveDown(index) {
  if (index < store.files.length - 1) {
    store.reorderFiles(index, index + 1)
  }
}

async function handleSubmit() {
  if (store.files.length < 2 || submitting.value) return
  submitting.value = true
  try {
    await store.submitTask({
      file_ids: store.files.map(f => f.id),
      target_format: 'mp4',
      tool_code: 'merge'
    }, 'merge')
  } catch {
    // store 已处理 toast
  } finally {
    submitting.value = false
  }
}

onMounted(() => {
  store.startPolling()
  store.bindVisibility()
})
</script>

<style scoped>
.tool-page {
  padding: 0;
}
.tool-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 20px;
}
.tool-kicker {
  color: var(--accent-cyan);
  font-size: 11px;
  font-weight: 700;
  letter-spacing: .16em;
  margin-bottom: 6px;
}
.tool-header h2 {
  color: var(--text-primary);
  font-size: 20px;
}
.format-hint {
  color: var(--text-muted);
  font-size: 12px;
  text-align: right;
}
.file-list-section {
  margin-top: 16px;
}
.file-list-label {
  color: var(--text-secondary);
  font-size: 13px;
  margin-bottom: 10px;
}
.file-list-item {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 10px 12px;
  background: var(--bg-card);
  border: 1px solid var(--border-default);
  border-radius: 9px;
  margin-bottom: 8px;
}
.file-index {
  width: 24px;
  height: 24px;
  display: flex;
  align-items: center;
  justify-content: center;
  border-radius: 50%;
  background: var(--bg-hover);
  color: var(--text-secondary);
  font-size: 12px;
  font-weight: 700;
  flex-shrink: 0;
}
.file-info {
  flex: 1;
  min-width: 0;
}
.file-name {
  display: block;
  color: var(--text-primary);
  font-size: 13px;
  font-weight: 500;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.file-size {
  color: var(--text-muted);
  font-size: 11px;
}
.file-actions {
  display: flex;
  gap: 4px;
  flex-shrink: 0;
}
.move-btn {
  width: 28px;
  height: 28px;
  display: flex;
  align-items: center;
  justify-content: center;
  border: 1px solid var(--border-default);
  border-radius: 6px;
  background: var(--bg-input);
  color: var(--text-secondary);
  font-size: 13px;
  cursor: pointer;
  transition: background .15s;
}
.move-btn:hover:not(:disabled) {
  background: var(--bg-hover);
}
.move-btn:disabled {
  opacity: .35;
  cursor: not-allowed;
}
.remove-btn {
  width: 28px;
  height: 28px;
  display: flex;
  align-items: center;
  justify-content: center;
  border: 1px solid transparent;
  border-radius: 6px;
  background: transparent;
  color: var(--text-muted);
  font-size: 12px;
  cursor: pointer;
  transition: color .15s;
}
.remove-btn:hover {
  color: var(--red);
}
.submit-section {
  margin-top: 22px;
}
.error-message {
  padding: 11px 13px;
  margin-bottom: 12px;
  border-radius: 9px;
  color: var(--red);
  background: var(--red-bg);
  border: 1px solid rgba(239, 68, 68, .2);
  font-size: 13px;
  line-height: 1.5;
}
.submit-button {
  width: 100%;
  padding: 13px 20px;
  color: white;
  background: var(--accent-gradient);
  border: none;
  border-radius: 12px;
  font-weight: 700;
  font-size: 15px;
  cursor: pointer;
  transition: opacity .2s;
}
.submit-button:disabled {
  opacity: .6;
  cursor: not-allowed;
}
.submit-button:hover:not(:disabled) {
  opacity: .9;
}
.button-spinner {
  display: inline-block;
  width: 14px;
  height: 14px;
  margin-right: 7px;
  vertical-align: -2px;
  border: 2px solid rgba(255,255,255,.3);
  border-top-color: white;
  border-radius: 50%;
  animation: spin .8s linear infinite;
}
.empty-hint {
  padding: 21px 0 3px;
  color: var(--text-muted);
  font-size: 13px;
}
.history-section {
  margin-top: 28px;
  padding-top: 24px;
  border-top: 1px solid var(--border-default);
}
@keyframes spin { to { transform: rotate(360deg); } }
</style>