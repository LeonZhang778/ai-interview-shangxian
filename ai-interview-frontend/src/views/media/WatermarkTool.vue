<template>
  <div class="tool-page">
    <div class="tool-header">
      <div>
        <p class="tool-kicker">STEP 01</p>
        <h2>添加水印</h2>
      </div>
      <span class="format-hint">支持 {{ allowedExtensions }}</span>
    </div>

    <MediaFileDropZone
      :accept="acceptTypes"
      :max-size-mb="maxFileSize"
      @file-selected="onFileSelected"
      @error="onError"
    />

    <div v-if="selectedFile" class="file-preview-section">
      <MediaFilePreview
        :file="selectedFile"
        @remove="onRemoveFile"
      />
    </div>

    <MediaWatermarkEditor
      v-if="selectedFile"
      v-model="watermark"
      :capabilities="store.capabilities"
    />

    <div v-if="selectedFile" class="submit-section">
      <p v-if="store.errorMessage" class="error-message" role="alert">{{ store.errorMessage }}</p>
      <button
        class="submit-button"
        type="button"
        :disabled="store.uploading"
        @click="handleSubmit"
      >
        <span v-if="submitting" class="button-spinner"></span>
        {{ submitting ? '提交中...' : '开始添加水印' }}
      </button>
    </div>

    <div v-else-if="!store.uploading" class="empty-hint">
      选择视频文件，设置水印参数后提交。
    </div>

    <div class="history-section">
      <MediaTaskHistory />
    </div>
  </div>
</template>

<script setup>
import { computed, onMounted, reactive, ref } from 'vue'
import { useMediaStore } from '../../stores/media'
import MediaFileDropZone from '../../components/media/MediaFileDropZone.vue'
import MediaFilePreview from '../../components/media/MediaFilePreview.vue'
import MediaWatermarkEditor from '../../components/media/MediaWatermarkEditor.vue'
import MediaTaskHistory from '../../components/media/MediaTaskHistory.vue'

const store = useMediaStore()
const submitting = ref(false)

const watermark = reactive({
  type: 'text',
  position: 'bottom-right',
  opacity: 0.8,
  watermark_width: 0,
  text: '',
  fontSize: 36,
  fontColor: '#ffffff',
  imageFile: null
})

const selectedFile = computed(() => store.selectedFile)

const allowedExtensions = computed(() => {
  const formats = store.capabilities.formats || ['mp4', 'mov', 'mkv', 'webm']
  return formats.slice(0, 8).join('、')
})

const acceptTypes = computed(() => {
  const formats = store.capabilities.formats || []
  return formats.map(f => `.${f}`).join(',') || 'video/*'
})

const maxFileSize = computed(() => store.capabilities.max_file_size_mb || 500)

function onFileSelected(file) {
  store.setFiles([file])
}

function onRemoveFile() {
  store.clearFiles()
}

function onError(message) {
  store.errorMessage = message
}

async function handleSubmit() {
  if (!selectedFile.value || submitting.value) return
  submitting.value = true
  try {
    const payload = {
      file_id: selectedFile.value.id,
      target_format: 'mp4',
      tool_code: 'watermark',
      watermark_type: watermark.type,
      position: watermark.position || 'bottom-right',
      opacity: watermark.opacity || 1,
      watermark_width: watermark.watermark_width || 0
    }
    if (watermark.type === 'image') {
      if (!watermark.imageFile) {
        store.errorMessage = '请上传水印图片'
        submitting.value = false
        return
      }
      payload.watermark_file_id = watermark.imageFile.id
    } else {
      if (!watermark.text.trim()) {
        store.errorMessage = '请输入水印文字内容'
        submitting.value = false
        return
      }
      payload.watermark_text = watermark.text.trim()
      payload.watermark_font_size = watermark.fontSize || 36
      payload.watermark_font_color = watermark.fontColor || 'white'
    }
    await store.submitTask(payload, 'watermark')
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
.file-preview-section {
  margin-top: 16px;
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