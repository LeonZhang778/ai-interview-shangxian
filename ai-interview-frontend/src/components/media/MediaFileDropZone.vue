<template>
  <div class="dropzone-wrapper">
    <!-- 拖拽上传区域 -->
    <div
      :class="['dropzone', { 'dropzone-dragover': isDragover, 'dropzone-disabled': disabled, 'dropzone-has-files': store.hasFiles }]"
      @dragenter.prevent="onDragEnter"
      @dragover.prevent="onDragOver"
      @dragleave.prevent="onDragLeave"
      @drop.prevent="onDrop"
      @click="triggerInput"
      role="button"
      :tabindex="disabled ? -1 : 0"
      :aria-label="uploadLabel"
      @keydown.enter.prevent="triggerInput"
      @keydown.space.prevent="triggerInput"
    >
      <input
        ref="fileInput"
        type="file"
        :accept="accept"
        :multiple="multiple"
        class="file-input"
        @change="onFileChange"
        tabindex="-1"
      />

      <!-- 上传中进度 -->
      <div v-if="store.uploading" class="uploading-state">
        <div class="upload-spinner" aria-hidden="true"></div>
        <p class="upload-text">上传中 {{ store.uploadProgress }}%</p>
        <div class="progress-bar">
          <div class="progress-fill" :style="{ width: store.uploadProgress + '%' }"></div>
        </div>
      </div>

      <!-- 空闲态 -->
      <div v-else-if="!store.hasFiles" class="idle-state">
        <div class="upload-icon" aria-hidden="true">
          <svg width="32" height="32" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round">
            <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4" />
            <polyline points="17 8 12 3 7 8" />
            <line x1="12" y1="3" x2="12" y2="15" />
          </svg>
        </div>
        <p class="idle-text">
          {{ multiple ? '拖拽文件到此处，或点击选择' : '拖拽文件到此处，或点击选择' }}
        </p>
        <p class="idle-hint">支持 {{ accept }} 格式，最大 {{ maxSizeMb }}MB</p>
      </div>

      <!-- 已选文件信息 -->
      <div v-else class="selected-state">
        <p class="selected-count">已选择 {{ store.files.length }} 个文件</p>
        <p class="selected-hint" v-if="!multiple">点击可重新选择文件</p>
      </div>
    </div>

    <!-- 已选文件列表 -->
    <div v-if="store.hasFiles" class="file-list">
      <div
        v-for="file in store.files"
        :key="file.id"
        class="file-list-item"
      >
        <div class="file-item-icon" aria-hidden="true">
          <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round">
            <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z" />
            <polyline points="14 2 14 8 20 8" />
          </svg>
        </div>
        <div class="file-item-info">
          <p class="file-item-name">{{ file.original_name || '未知文件' }}</p>
          <p class="file-item-meta">{{ store.formatBytes(file.size_bytes) }}</p>
        </div>
        <button
          class="file-item-remove"
          type="button"
          :disabled="store.uploading"
          :aria-label="'移除 ' + (file.original_name || '文件')"
          @click.stop="handleRemoveFile(file.id)"
        >
          <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
            <line x1="18" y1="6" x2="6" y2="18" />
            <line x1="6" y1="6" x2="18" y2="18" />
          </svg>
        </button>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed } from 'vue'
import { useMediaStore } from '../../stores/media'

const props = defineProps({
  accept: { type: String, default: 'video/*,audio/*' },
  multiple: { type: Boolean, default: false },
  maxSizeMb: { type: Number, default: 500 }
})

const emit = defineEmits(['file-selected', 'files-selected', 'error'])

const store = useMediaStore()
const fileInput = ref(null)
const isDragover = ref(false)

const disabled = computed(() => store.uploading)

const uploadLabel = computed(() => {
  if (store.uploading) return '上传中...'
  return props.multiple ? '选择文件上传' : '选择文件上传'
})

function triggerInput() {
  if (disabled.value) return
  fileInput.value?.click()
}

function onDragEnter() {
  if (disabled.value) return
  isDragover.value = true
}

function onDragOver() {
  if (disabled.value) return
  isDragover.value = true
}

function onDragLeave() {
  isDragover.value = false
}

function validateFile(file) {
  const maxBytes = props.maxSizeMb * 1024 * 1024
  if (file.size > maxBytes) {
    emit('error', `文件大小超过 ${props.maxSizeMb}MB 限制`)
    return false
  }
  const allowedExtensions = props.accept
    .split(',')
    .map(item => item.trim().toLowerCase())
    .filter(item => item.startsWith('.'))
  if (allowedExtensions.length) {
    const lowerName = file.name.toLowerCase()
    const matched = allowedExtensions.some(ext => lowerName.endsWith(ext))
    if (!matched) {
      emit('error', `文件格式不支持，请选择 ${allowedExtensions.join('、')} 文件`)
      return false
    }
  }
  return true
}

async function onDrop(event) {
  isDragover.value = false
  if (disabled.value) return

  const droppedFiles = Array.from(event.dataTransfer.files)
  if (!droppedFiles.length) return

  if (!props.multiple) {
    if (!validateFile(droppedFiles[0])) return
    await uploadAndEmit(droppedFiles[0])
    return
  }

  const validFiles = droppedFiles.filter(validateFile)
  if (!validFiles.length) return

  if (validFiles.length === 1) {
    await uploadAndEmit(validFiles[0])
  } else {
    await uploadMultipleAndEmit(validFiles)
  }
}

async function onFileChange(event) {
  if (disabled.value) return
  const selectedFiles = Array.from(event.target.files || [])
  if (!selectedFiles.length) return

  if (!props.multiple) {
    if (!validateFile(selectedFiles[0])) return
    await uploadAndEmit(selectedFiles[0])
  } else {
    const validFiles = selectedFiles.filter(validateFile)
    if (!validFiles.length) return
    if (validFiles.length === 1) {
      await uploadAndEmit(validFiles[0])
    } else {
      await uploadMultipleAndEmit(validFiles)
    }
  }

  // 重置 input 以允许重复选择同一文件
  if (fileInput.value) {
    fileInput.value.value = ''
  }
}

async function uploadAndEmit(file) {
  try {
    const result = await store.uploadFile(file)
    emit('file-selected', result)
    emit('files-selected', [result])
  } catch {
    // store 已处理 toast 和 errorMessage
  }
}

async function uploadMultipleAndEmit(files) {
  const results = []
  for (const file of files) {
    try {
      const result = await store.uploadFile(file)
      results.push(result)
    } catch {
      // store 已处理 toast
    }
  }
  if (results.length) {
    emit('files-selected', results)
  }
}

function handleRemoveFile(fileId) {
  store.removeFile(fileId)
}
</script>

<style scoped>
.dropzone-wrapper {
  width: 100%;
}
.dropzone {
  border: 1px dashed var(--border-hover);
  border-radius: 13px;
  background: var(--bg-input);
  min-height: 100px;
  display: flex;
  align-items: center;
  justify-content: center;
  cursor: pointer;
  transition: border-color .2s, background .2s;
  position: relative;
  padding: 20px;
}
.dropzone:hover:not(.dropzone-disabled) {
  border-color: var(--accent-primary);
  background: var(--bg-hover);
}
.dropzone-dragover {
  border-color: var(--accent-cyan);
  background: var(--bg-hover);
  border-style: solid;
}
.dropzone-disabled {
  opacity: .6;
  cursor: not-allowed;
}
.dropzone-has-files {
  min-height: 70px;
  padding: 14px 20px;
}
.file-input {
  position: absolute;
  width: 0;
  height: 0;
  opacity: 0;
  overflow: hidden;
  pointer-events: none;
}

/* 空闲态 */
.idle-state {
  text-align: center;
  padding: 10px 0;
}
.upload-icon {
  color: var(--text-muted);
  margin-bottom: 8px;
  display: flex;
  justify-content: center;
}
.idle-text {
  color: var(--text-secondary);
  font-size: 14px;
  margin: 0 0 6px;
}
.idle-hint {
  color: var(--text-muted);
  font-size: 11px;
  margin: 0;
}

/* 上传中 */
.uploading-state {
  text-align: center;
  padding: 10px 0;
  width: 100%;
  max-width: 240px;
}
.upload-spinner {
  width: 24px;
  height: 24px;
  margin: 0 auto 8px;
  border: 2px solid var(--border-default);
  border-top-color: var(--accent-cyan);
  border-radius: 50%;
  animation: spin .8s linear infinite;
}
.upload-text {
  color: var(--text-secondary);
  font-size: 13px;
  margin: 0 0 8px;
}
.progress-bar {
  width: 100%;
  height: 6px;
  border-radius: 999px;
  background: var(--border-default);
  overflow: hidden;
  position: relative;
}
.progress-bar::after {
  content: '';
  position: absolute;
  inset: 0;
  background: linear-gradient(90deg, transparent, rgba(255,255,255,.35), transparent);
  transform: translateX(-100%);
  animation: progress-shimmer 1.35s ease-in-out infinite;
}
.progress-fill {
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

/* 已选态 */
.selected-state {
  text-align: center;
}
.selected-count {
  color: var(--text-primary);
  font-size: 14px;
  margin: 0 0 4px;
}
.selected-hint {
  color: var(--text-muted);
  font-size: 11px;
  margin: 0;
}

/* 文件列表 */
.file-list {
  margin-top: 12px;
  display: flex;
  flex-direction: column;
  gap: 7px;
}
.file-list-item {
  display: flex;
  align-items: center;
  gap: 10px;
  border: 1px solid var(--border-default);
  border-radius: 9px;
  padding: 9px 11px;
  background: var(--bg-card);
}
.file-item-icon {
  flex: 0 0 32px;
  width: 32px;
  height: 32px;
  display: grid;
  place-items: center;
  border-radius: 6px;
  background: var(--purple-bg);
  color: var(--accent-primary);
}
.file-item-info {
  flex: 1;
  min-width: 0;
}
.file-item-name {
  color: var(--text-primary);
  font-size: 13px;
  margin: 0 0 2px;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}
.file-item-meta {
  color: var(--text-muted);
  font-size: 11px;
  margin: 0;
}
.file-item-remove {
  flex: 0 0 28px;
  width: 28px;
  height: 28px;
  display: grid;
  place-items: center;
  border: none;
  background: transparent;
  color: var(--text-muted);
  cursor: pointer;
  border-radius: 6px;
  transition: background .15s, color .15s;
}
.file-item-remove:hover {
  background: var(--red-bg);
  color: var(--red);
}
.file-item-remove:disabled {
  opacity: .4;
  cursor: not-allowed;
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
