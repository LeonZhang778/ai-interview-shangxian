<template>
  <div class="tool-page">
    <div class="tool-header">
      <div>
        <p class="tool-kicker">STEP 01</p>
        <h2>提取音频</h2>
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

    <MediaParamPanel
      v-if="selectedFile"
      v-model:form="form"
      tool-code="extract_audio"
      :capabilities="store.capabilities"
      :is-audio-file="selectedFile.media_type === 'audio'"
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
        {{ submitting ? '提交中...' : '开始提取' }}
      </button>
    </div>

    <div v-else-if="!store.uploading" class="empty-hint">
      选择视频文件，提取其中的音频轨道。
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
import MediaParamPanel from '../../components/media/MediaParamPanel.vue'
import MediaTaskHistory from '../../components/media/MediaTaskHistory.vue'

const store = useMediaStore()
const submitting = ref(false)
const videoFormats = ['mp4', 'mov', 'mkv', 'webm', 'avi', 'flv']

const form = reactive({
  target_format: 'mp3',
  quality: 'medium',
  resolution: '',
  frame_rate: 0,
  video_codec: '',
  audio_codec: '',
  audio_bitrate: '',
  sample_rate: 0,
  channels: 0,
  start_time: 0,
  duration: 0
})

const selectedFile = computed(() => store.selectedFile)

const allowedExtensions = computed(() => {
  return videoFormats.join('、')
})

const acceptTypes = computed(() => {
  return videoFormats.map(f => `.${f}`).join(',')
})

const maxFileSize = computed(() => store.capabilities.max_file_size_mb || 500)

function onFileSelected(file) {
  store.setFiles([file])
  form.target_format = 'mp3'
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
    await store.submitTask({
      file_id: selectedFile.value.id,
      target_format: form.target_format,
      tool_code: 'extract_audio',
      video_codec: form.video_codec || '',
      audio_codec: form.audio_codec || '',
      audio_bitrate: form.audio_bitrate || '',
      resolution: form.resolution || '',
      frame_rate: form.frame_rate || 0,
      sample_rate: form.sample_rate || 0,
      channels: form.channels || 0,
      start_time: form.start_time || 0,
      duration: form.duration || 0,
      quality: form.quality
    })
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
