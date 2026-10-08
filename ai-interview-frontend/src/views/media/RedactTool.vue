<template>
  <div class="tool-page">
    <div class="tool-header">
      <div>
        <p class="tool-kicker">STEP 01</p>
        <h2>区域遮挡</h2>
      </div>
      <span class="format-hint">支持视频格式</span>
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

    <MediaVideoOverlayEditor
      v-if="selectedFile"
      mode="redact"
      :file="selectedFile"
      :region="form"
      :redact-type="form.redact_type"
      @update:region="onRegionPreviewUpdate"
    />

    <!-- 参数面板 -->
    <div v-if="selectedFile" class="param-section">
      <div class="section-heading compact">
        <div>
          <p class="section-kicker">STEP 02</p>
          <h3>遮挡参数</h3>
        </div>
      </div>

      <!-- 遮挡类型 -->
      <div class="param-group">
        <span class="param-label">遮挡类型</span>
        <div class="param-options">
          <button
            v-for="opt in redactTypes"
            :key="opt.value"
            :class="['param-chip', { active: form.redact_type === opt.value }]"
            type="button"
            @click="form.redact_type = opt.value"
          >
            {{ opt.label }}
          </button>
        </div>
      </div>

      <!-- 区域坐标 -->
      <div class="param-grid">
        <label>
          <span>X 坐标</span>
          <input v-model.number="form.region_x" type="number" min="0" placeholder="0" />
        </label>
        <label>
          <span>Y 坐标</span>
          <input v-model.number="form.region_y" type="number" min="0" placeholder="0" />
        </label>
        <label>
          <span>区域宽度</span>
          <input v-model.number="form.region_width" type="number" min="1" placeholder="200" />
        </label>
        <label>
          <span>区域高度</span>
          <input v-model.number="form.region_height" type="number" min="1" placeholder="200" />
        </label>
      </div>

      <!-- 实心颜色（仅 solid 类型） -->
      <div v-if="form.redact_type === 'solid'" class="param-group">
        <span class="param-label">遮挡颜色</span>
        <div class="color-input-row">
          <input
            v-model="form.solid_color"
            type="text"
            class="param-input"
            placeholder="black"
          />
          <input
            v-model="colorPreview"
            type="color"
            class="color-picker"
            :aria-label="'选择遮挡颜色'"
          />
        </div>
        <p class="param-hint">支持颜色名称 (black, red, white) 或十六进制 (#000000)</p>
      </div>

      <!-- 输出文件名 -->
      <div class="param-group">
        <span class="param-label">输出文件名（可选）</span>
        <input
          v-model="form.output_name"
          type="text"
          class="param-input"
          placeholder="留空自动生成"
        />
      </div>
    </div>

    <div v-if="selectedFile" class="submit-section">
      <p v-if="store.errorMessage" class="error-message" role="alert">{{ store.errorMessage }}</p>
      <button
        class="submit-button"
        type="button"
        :disabled="store.uploading || !isValid"
        @click="handleSubmit"
      >
        <span v-if="submitting" class="button-spinner"></span>
        {{ submitting ? '提交中...' : '开始遮挡' }}
      </button>
    </div>

    <div v-else-if="!store.uploading" class="empty-hint">
      选择视频文件，设置遮挡区域后提交任务。
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
import MediaVideoOverlayEditor from '../../components/media/MediaVideoOverlayEditor.vue'
import MediaTaskHistory from '../../components/media/MediaTaskHistory.vue'

const store = useMediaStore()
const submitting = ref(false)
const videoFormats = ['mp4', 'mov', 'mkv', 'webm', 'avi', 'flv']

const form = reactive({
  redact_type: 'blur',
  region_x: 0,
  region_y: 0,
  region_width: 200,
  region_height: 200,
  solid_color: 'black',
  output_name: '',
})

const redactTypes = [
  { value: 'blur', label: '模糊' },
  { value: 'pixelate', label: '像素化' },
  { value: 'solid', label: '实心遮挡' },
]

const selectedFile = computed(() => store.selectedFile)

const isValid = computed(() => {
  return form.region_width > 0 && form.region_height > 0
})

const colorPreview = computed({
  get: () => {
    if (form.solid_color.startsWith('#')) return form.solid_color
    return '#000000'
  },
  set: (val) => {
    form.solid_color = val
  },
})

const allowedExtensions = computed(() => {
  return videoFormats.join('、')
})

const acceptTypes = computed(() => {
  return videoFormats.map(f => `.${f}`).join(',')
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

function onRegionPreviewUpdate(next) {
  Object.assign(form, next)
}

async function handleSubmit() {
  if (!selectedFile.value || submitting.value || !isValid.value) return
  submitting.value = true
  try {
    const payload = {
      file_id: selectedFile.value.id,
      target_format: 'mp4',
      tool_code: 'redact',
      redact_type: form.redact_type,
      region_x: form.region_x || 0,
      region_y: form.region_y || 0,
      region_width: form.region_width,
      region_height: form.region_height,
    }
    if (form.redact_type === 'solid') {
      payload.solid_color = form.solid_color.trim() || 'black'
    }
    if (form.output_name.trim()) {
      payload.output_name = form.output_name.trim()
    }
    await store.submitTask(payload, 'redact')
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
.param-section {
  margin-top: 24px;
  padding-top: 20px;
  border-top: 1px solid var(--border-default);
}
.section-heading {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 16px;
}
.section-kicker {
  color: var(--accent-cyan);
  font-size: 10px;
  font-weight: 700;
  letter-spacing: .16em;
  margin-bottom: 4px;
}
.section-heading h3 {
  color: var(--text-primary);
  font-size: 16px;
  margin: 0;
}
.param-group {
  margin-bottom: 16px;
}
.param-label {
  display: block;
  color: var(--text-secondary);
  font-size: 12px;
  font-weight: 600;
  margin-bottom: 8px;
}
.param-options {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
}
.param-chip {
  padding: 7px 14px;
  border: 1px solid var(--border-default);
  border-radius: 8px;
  background: var(--bg-input);
  color: var(--text-secondary);
  font-size: 13px;
  cursor: pointer;
  transition: border-color .15s, color .15s, background .15s;
}
.param-chip.active {
  border-color: var(--accent-primary);
  color: var(--text-primary);
  background: var(--bg-hover);
}
.param-chip:hover:not(.active) {
  border-color: var(--border-hover);
}
.param-grid {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 12px;
  margin-bottom: 16px;
}
.param-grid label {
  display: grid;
  gap: 5px;
}
.param-grid label span {
  color: var(--text-secondary);
  font-size: 11px;
  font-weight: 600;
}
.param-grid input {
  padding: 9px 11px;
  border: 1px solid var(--border-default);
  border-radius: 8px;
  background: var(--bg-input);
  color: var(--text-primary);
  font-size: 13px;
  outline: none;
  transition: border-color .15s;
}
.param-grid input:focus {
  border-color: var(--accent-primary);
}
.param-input {
  width: 100%;
  padding: 9px 11px;
  border: 1px solid var(--border-default);
  border-radius: 8px;
  background: var(--bg-input);
  color: var(--text-primary);
  font-size: 13px;
  outline: none;
  transition: border-color .15s;
  box-sizing: border-box;
}
.param-input:focus {
  border-color: var(--accent-primary);
}
.color-input-row {
  display: flex;
  gap: 10px;
  align-items: center;
}
.color-input-row .param-input {
  flex: 1;
}
.color-picker {
  width: 38px;
  height: 38px;
  padding: 2px;
  border: 1px solid var(--border-default);
  border-radius: 8px;
  background: var(--bg-input);
  cursor: pointer;
}
.param-hint {
  color: var(--text-muted);
  font-size: 11px;
  margin: 6px 0 0;
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
  border: 1px solid rgba(128, 128, 128, .2);
  font-size: 13px;
  line-height: 1.5;
}
.submit-button {
  width: 100%;
  padding: 13px 20px;
  color: var(--bg-base);
  background: var(--accent-primary);
  border: none;
  border-radius: 8px;
  font-weight: 700;
  font-size: 15px;
  cursor: pointer;
  transition: opacity .2s;
}
.submit-button:disabled {
  opacity: .5;
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
