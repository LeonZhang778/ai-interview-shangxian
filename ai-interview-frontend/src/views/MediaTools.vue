<template>
  <div class="media-page">
    <header class="media-header">
      <div>
        <p class="eyebrow">TOOLS / MEDIA</p>
        <h1>视频与音频工具</h1>
        <p class="lead">上传一次，完成格式转换、压缩、截取和音频提取。任务会自动保存，刷新页面也能继续查看。</p>
      </div>
      <router-link to="/dashboard" class="back-link">返回工作台</router-link>
    </header>

    <section class="tool-grid" aria-label="工具选择">
      <button
        v-for="tool in tools"
        :key="tool.code"
        class="tool-card"
        :class="{ active: selectedTool === tool.code }"
        type="button"
        @click="selectTool(tool.code)"
      >
        <span class="tool-icon" aria-hidden="true">{{ tool.icon }}</span>
        <span class="tool-card-body">
          <strong>{{ tool.name }}</strong>
          <small>{{ tool.description }}</small>
        </span>
        <span v-if="selectedTool === tool.code" class="selected-mark" aria-label="已选择">✓</span>
      </button>
    </section>

    <main class="workspace-grid">
      <section class="workspace-card">
        <div class="section-heading">
          <div>
            <p class="section-kicker">STEP 01</p>
            <h2>{{ currentTool.name }}</h2>
          </div>
          <span class="format-hint">支持 {{ allowedExtensionsLabel }}</span>
        </div>

<div
          class="drop-zone"
          :class="{ dragging: dragging, 'has-file': selectedFile || selectedFiles.length > 0 }"
          role="button"
          tabindex="0"
          @click="openFilePicker"
          @keydown.enter.prevent="openFilePicker"
          @keydown.space.prevent="openFilePicker"
          @dragover.prevent="dragging = true"
          @dragleave.prevent="dragging = false"
          @drop.prevent="handleDrop"
        >
          <input ref="fileInput" type="file" class="visually-hidden" :accept="acceptTypes" :multiple="selectedTool === 'merge'" @change="handleFileChange" />
          <template v-if="selectedTool === 'merge' && selectedFiles.length > 0">
            <span class="upload-icon" aria-hidden="true">↑</span>
            <strong>继续添加文件，或点击选择</strong>
            <span>已选择 {{ selectedFiles.length }} 个文件</span>
          </template>
          <template v-else-if="selectedFile">
            <span class="file-icon" aria-hidden="true">{{ selectedFile.media_type === 'audio' ? '♫' : '▣' }}</span>
            <div class="file-info">
              <strong>{{ selectedFile.original_name }}</strong>
              <span>{{ formatBytes(selectedFile.size_bytes) }}<template v-if="selectedFile.duration_ms"> · {{ formatDuration(selectedFile.duration_ms) }}</template></span>
              <span v-if="selectedFile.metadata" class="file-meta">{{ mediaMetaLabel }}</span>
            </div>
            <button class="remove-file" type="button" aria-label="移除文件" @click.stop="removeFile">移除</button>
          </template>
          <template v-else-if="uploading">
            <span class="upload-spinner" aria-hidden="true"></span>
            <strong>正在上传并检测媒体信息</strong>
            <span>{{ uploadProgress }}%</span>
            <div class="progress-track"><span :style="{ width: `${uploadProgress}%` }"></span></div>
          </template>
          <template v-else>
            <span class="upload-icon" aria-hidden="true">↑</span>
            <strong>拖拽文件到这里，或点击选择</strong>
            <span>单个文件最大 {{ maxFileSize }}MB</span>
          </template>
</div>

        <!-- 合并文件列表 -->
        <div v-if="selectedTool === 'merge' && selectedFiles.length > 0" class="merge-file-list">
          <div class="merge-file-header">
            <span class="merge-file-label">已选择文件（共 {{ selectedFiles.length }} 个，拖动可调整顺序）</span>
          </div>
          <div v-for="(file, index) in selectedFiles" :key="file.id" class="merge-file-item">
            <span class="merge-file-index">{{ index + 1 }}</span>
            <div class="merge-file-info">
              <strong>{{ file.original_name }}</strong>
              <span>{{ formatBytes(file.size_bytes) }}<template v-if="file.duration_ms"> · {{ formatDuration(file.duration_ms) }}</template></span>
            </div>
            <div class="merge-file-actions">
              <button type="button" class="move-btn" :disabled="index === 0" @click="moveFileUp(index)" aria-label="上移">↑</button>
              <button type="button" class="move-btn" :disabled="index === selectedFiles.length - 1" @click="moveFileDown(index)" aria-label="下移">↓</button>
              <button type="button" class="remove-file" @click="removeMergeFile(index)" aria-label="移除">移除</button>
            </div>
          </div>
        </div>

        <p v-if="errorMessage" class="message error-message" role="alert">{{ errorMessage }}</p>

<form v-if="selectedFile || (selectedTool === 'merge' && selectedFiles.length >= 2) || (selectedTool === 'watermark' && selectedFile)" class="options-form" @submit.prevent="submitTask">
          <div class="section-heading compact">
            <div>
              <p class="section-kicker">STEP 02</p>
              <h3>处理参数</h3>
            </div>
            <span class="format-hint">可随时重新处理</span>
          </div>

<div class="form-grid">
            <label v-if="selectedTool !== 'merge' && selectedTool !== 'watermark'">
              <span>输出格式</span>
              <select v-model="form.target_format">
                <option v-for="format in targetFormats" :key="format" :value="format">{{ format.toUpperCase() }}</option>
              </select>
            </label>
            <label v-if="selectedTool === 'compress'">
              <span>压缩质量</span>
              <select v-model="form.quality">
                <option value="high">高质量</option>
                <option value="medium">均衡</option>
                <option value="low">小体积</option>
              </select>
            </label>
            <label v-if="isVideoTool && selectedTool !== 'watermark'">
              <span>分辨率</span>
              <select v-model="form.resolution">
                <option value="">保持原尺寸</option>
                <option v-for="resolution in resolutionOptions" :key="resolution" :value="resolution">{{ resolution }}</option>
              </select>
            </label>
            <label v-if="isVideoTool && selectedTool !== 'watermark'">
              <span>帧率</span>
              <select v-model="form.frame_rate">
                <option :value="0">保持原帧率</option>
                <option :value="24">24 fps</option>
                <option :value="30">30 fps</option>
                <option :value="60">60 fps</option>
              </select>
            </label>
            <label v-if="selectedTool === 'trim'">
              <span>开始时间（秒）</span>
              <input v-model.number="form.start_time" type="number" min="0" step="0.1" placeholder="0" />
            </label>
            <label v-if="selectedTool === 'trim'">
              <span>截取时长（秒）</span>
              <input v-model.number="form.duration" type="number" min="0.1" step="0.1" placeholder="例如 30" />
            </label>
            <label v-if="isAudioTool">
              <span>音频码率</span>
              <select v-model="form.audio_bitrate">
                <option value="">默认</option>
                <option value="128k">128 kbps</option>
                <option value="192k">192 kbps</option>
                <option value="320k">320 kbps</option>
              </select>
            </label>
            <!-- 水印参数 -->
            <template v-if="selectedTool === 'watermark'">
              <label class="full-width">
                <span>水印类型</span>
                <div class="radio-group">
                  <label class="radio-label">
                    <input v-model="watermarkType" type="radio" value="image" />
                    <span>图片水印</span>
                  </label>
                  <label class="radio-label">
                    <input v-model="watermarkType" type="radio" value="text" />
                    <span>文字水印</span>
                  </label>
                </div>
              </label>
              <label class="full-width">
                <span>水印位置</span>
                <select v-model="form.position">
                  <option value="top-left">左上角</option>
                  <option value="top-right">右上角</option>
                  <option value="bottom-left">左下角</option>
                  <option value="bottom-right">右下角</option>
                  <option value="center">居中</option>
                </select>
              </label>
              <label>
                <span>透明度</span>
                <input v-model.number="form.opacity" type="number" min="0.1" max="1" step="0.1" placeholder="1.0" />
              </label>
            </template>
          </div>

          <!-- 水印图片上传 -->
          <div v-if="selectedTool === 'watermark' && watermarkType === 'image'" class="watermark-image-section">
            <div
              class="watermark-drop"
              role="button"
              tabindex="0"
              @click="watermarkFileInput?.click()"
              @keydown.enter.prevent="watermarkFileInput?.click()"
              @keydown.space.prevent="watermarkFileInput?.click()"
            >
              <input ref="watermarkFileInput" type="file" class="visually-hidden" accept=".png,.jpg,.jpeg,.webp" @change="handleWatermarkFileChange" />
              <template v-if="watermarkImageFile">
                <span class="file-icon" aria-hidden="true">◇</span>
                <div class="file-info">
                  <strong>{{ watermarkImageFile.original_name }}</strong>
                  <span>{{ formatBytes(watermarkImageFile.size_bytes) }}</span>
                </div>
                <button type="button" class="remove-file" @click.stop="watermarkImageFile = null">移除</button>
              </template>
              <template v-else-if="uploadingWatermark">
                <span class="upload-spinner" aria-hidden="true"></span>
                <strong>正在上传水印图片...</strong>
              </template>
              <template v-else>
                <span class="upload-icon small" aria-hidden="true">◇</span>
                <strong>点击上传水印图片</strong>
                <span>支持 PNG / JPG / WebP</span>
              </template>
            </div>
          </div>

          <!-- 文字水印参数 -->
          <div v-if="selectedTool === 'watermark' && watermarkType === 'text'" class="form-grid">
            <label class="full-width">
              <span>水印文字</span>
              <input v-model="watermarkText" type="text" placeholder="请输入水印文字" maxlength="100" />
            </label>
            <label>
              <span>字号</span>
              <input v-model.number="watermarkFontSize" type="number" min="8" max="200" placeholder="36" />
            </label>
            <label>
              <span>文字颜色</span>
              <select v-model="watermarkFontColor">
                <option value="white">白色</option>
                <option value="black">黑色</option>
                <option value="red">红色</option>
                <option value="yellow">黄色</option>
                <option value="gray">灰色</option>
              </select>
            </label>
          </div>

          <div class="advanced-toggle">
            <button type="button" class="text-button" @click="showAdvanced = !showAdvanced">{{ showAdvanced ? '收起高级参数' : '展开高级参数' }}</button>
          </div>
          <div v-if="showAdvanced" class="advanced-grid">
            <label>
              <span>视频编码器</span>
              <input v-model="form.video_codec" type="text" placeholder="使用默认编码器" />
            </label>
            <label>
              <span>音频编码器</span>
              <input v-model="form.audio_codec" type="text" placeholder="使用默认编码器" />
            </label>
            <label>
              <span>音频采样率</span>
              <select v-model="form.sample_rate">
                <option :value="0">默认</option>
                <option :value="44100">44.1 kHz</option>
                <option :value="48000">48 kHz</option>
              </select>
            </label>
            <label>
              <span>声道</span>
              <select v-model="form.channels">
                <option :value="0">默认</option>
                <option :value="1">单声道</option>
                <option :value="2">立体声</option>
              </select>
            </label>
          </div>

<button class="submit-button" type="submit" :disabled="submitting || (selectedTool !== 'merge' && selectedTool !== 'watermark' && !selectedFile) || (selectedTool === 'merge' && selectedFiles.length < 2)">
            <span v-if="submitting" class="button-spinner"></span>
            {{ submitting ? '提交中...' : selectedTool === 'merge' ? `开始合并 (${selectedFiles.length} 个文件)` : selectedTool === 'watermark' ? '添加水印' : '开始处理' }}
          </button>
        </form>

<div v-else-if="selectedTool === 'merge'" class="empty-hint">
          至少上传 2 个视频文件，调整顺序后提交合并。
        </div>
        <div v-else-if="selectedTool === 'watermark'" class="empty-hint">
          先选择一个视频文件，然后设置水印参数。
        </div>
        <div v-else class="empty-hint">
          选择一个文件后，这里会出现格式、质量和时间范围设置。
        </div>
      </section>

      <aside class="history-card">
        <div class="section-heading compact">
          <div>
            <p class="section-kicker">RECENT</p>
            <h2>最近任务</h2>
          </div>
          <button v-if="tasks.length" class="text-button" type="button" @click="loadTasks">刷新</button>
          <button v-if="tasks.length" class="text-button danger-text-button" type="button" :disabled="deletingTasks" @click="deleteAllTasks">
            {{ deletingTasks ? '删除中...' : '清空已完成' }}
          </button>
        </div>

        <div v-if="tasksLoading" class="history-loading">正在加载任务...</div>
        <div v-else-if="!tasks.length" class="history-empty">
          <span aria-hidden="true">◌</span>
          <p>还没有处理任务</p>
          <small>完成第一次转换后，结果会显示在这里</small>
        </div>
        <div v-else class="task-list">
          <article v-for="task in tasks" :key="task.id" class="task-item">
            <div class="task-main">
              <div class="task-title-row">
                <strong>{{ toolName(task.tool_name || task.tool_code) }}</strong>
                <span :class="['task-status', task.status]">{{ statusLabel(task.status) }}</span>
              </div>
              <div class="task-progress" v-if="['queued', 'pending', 'processing'].includes(task.status)">
                <span class="progress-track"><span :style="{ width: `${task.progress || 0}%` }"></span></span>
                <small>{{ task.progress || 0 }}%</small>
              </div>
              <p v-if="task.error_message || task.error_code" class="task-error">{{ task.error_message || task.error_code }}</p>
              <small class="task-date">{{ formatDate(task.created_at) }}</small>
            </div>
            <div class="task-actions">
              <button v-if="task.status === 'completed'" class="task-action success" type="button" @click="downloadTask(task)">下载</button>
              <button v-else-if="['queued', 'pending', 'processing'].includes(task.status)" class="task-action" type="button" @click="cancelTask(task)">取消</button>
              <button v-else-if="task.status === 'failed'" class="task-action" type="button" @click="retryTask(task)">重试</button>
              <button v-if="isDeletableTask(task)" class="task-action danger" type="button" :disabled="deletingTaskId === task.id" @click="deleteTask(task)">
                {{ deletingTaskId === task.id ? '删除中...' : '删除' }}
              </button>
            </div>
          </article>
        </div>
      </aside>
    </main>
  </div>
</template>

<script setup>
import { computed, onMounted, onUnmounted, reactive, ref, watch } from 'vue'
import { useAuthStore } from '../stores/auth'
import {
  cancelMediaTask,
  createConvertTask,
  createGifTask,
  createMergeTask,
  createWatermarkTask,
  getCapabilities,
  getMediaTask,
  getMediaTaskDownload,
  listMediaTasks,
  deleteMediaTask,
  deleteMediaTasks,
  retryMediaTask,
  uploadMediaFile
} from '../api/mediaTool'

const tools = [
  { code: 'convert', name: '格式转换', icon: '↗', description: '转换视频或音频格式' },
  { code: 'compress', name: '视频压缩', icon: '▤', description: '减小体积，保持清晰度' },
  { code: 'trim', name: '视频截取', icon: '⌁', description: '截取需要的时间片段' },
  { code: 'extract_audio', name: '提取音频', icon: '♫', description: '从视频中提取音频' },
  { code: 'audio_convert', name: '音频转换', icon: '◖', description: '转换音频编码和格式' },
  { code: 'gif', name: '视频转 GIF', icon: '✦', description: '截取视频片段生成 GIF' },
  { code: 'merge', name: '视频合并', icon: '⊕', description: '按顺序合并多个视频' },
{ code: 'watermark', name: '添加水印', icon: '◇', description: '给视频添加图片或文字水印' }
]

const selectedTool = ref('convert')
const authStore = useAuthStore()
const fileInput = ref(null)
const watermarkFileInput = ref(null)
const selectedFile = ref(null)
const capabilities = ref({})
const dragging = ref(false)
const uploading = ref(false)
const uploadProgress = ref(0)
const submitting = ref(false)
const showAdvanced = ref(false)
const errorMessage = ref('')
const tasks = ref([])
const tasksLoading = ref(true)
const deletingTaskId = ref(null)
const deletingTasks = ref(false)
let pollTimer = null

// 合并多文件状态
const selectedFiles = ref([])
const watermarkType = ref('image')
const watermarkImageFile = ref(null)
const watermarkText = ref('')
const watermarkFontSize = ref(36)
const watermarkFontColor = ref('white')
const uploadingWatermark = ref(false)

const form = reactive({
  target_format: 'mp4',
  quality: 'medium',
  resolution: '',
  frame_rate: 0,
  sample_rate: 0,
  channels: 0,
  start_time: 0,
  duration: 0,
  video_codec: '',
  audio_codec: '',
  audio_bitrate: '',
  position: 'bottom-right',
  opacity: 1,
  watermark_width: 0
})

const currentTool = computed(() => tools.find(tool => tool.code === selectedTool.value) || tools[0])
const isAudioTool = computed(() => ['extract_audio', 'audio_convert'].includes(selectedTool.value) || selectedFile.value?.media_type === 'audio')
const isVideoTool = computed(() => !isAudioTool.value && selectedTool.value !== 'audio_convert')
const targetFormats = computed(() => {
  const formats = capabilities.value.formats || ['mp4', 'mov', 'mkv', 'webm', 'mp3', 'wav', 'm4a', 'aac', 'flac', 'ogg']
  if (selectedTool.value === 'extract_audio' || selectedTool.value === 'audio_convert') {
    return formats.filter(format => ['mp3', 'wav', 'm4a', 'aac', 'flac', 'ogg'].includes(format))
  }
  return formats.filter(format => ['mp4', 'mov', 'mkv', 'webm'].includes(format))
})
const resolutionOptions = computed(() => capabilities.value.resolution_presets ? Object.keys(capabilities.value.resolution_presets) : ['1080p', '720p', '480p', '360p'])
const maxFileSize = computed(() => capabilities.value.max_file_size_mb || 500)
const allowedExtensionsLabel = computed(() => (capabilities.value.formats || ['mp4', 'mov', 'mkv', 'webm', 'mp3', 'wav']).slice(0, 8).join('、'))
const acceptTypes = computed(() => (capabilities.value.formats || []).map(format => `.${format}`).join(',') || 'video/*,audio/*')
const mediaMetaLabel = computed(() => {
  const metadata = selectedFile.value?.metadata || {}
  const width = metadata.width || metadata.video?.width
  const height = metadata.height || metadata.video?.height
  return width && height ? `${width} × ${height}` : ''
})

function selectTool(code) {
  selectedTool.value = code
  errorMessage.value = ''
  selectedFiles.value = []
  watermarkImageFile.value = null
  watermarkText.value = ''
  watermarkType.value = 'image'
  if (code === 'extract_audio') form.target_format = 'mp3'
  else if (code === 'audio_convert') form.target_format = 'mp3'
  else if (!['mp4', 'mov', 'mkv', 'webm'].includes(form.target_format)) form.target_format = 'mp4'
}

function openFilePicker() {
  if (!uploading.value) fileInput.value?.click()
}

function handleFileChange(event) {
  const files = event.target.files
  if (!files || files.length === 0) return
  if (selectedTool.value === 'merge') {
    for (const file of files) {
      uploadFile(file)
    }
  } else {
    uploadFile(files[0])
  }
  event.target.value = ''
}

function handleWatermarkFileChange(event) {
  const file = event.target.files?.[0]
  if (file) uploadWatermarkFile(file)
  event.target.value = ''
}

function handleDrop(event) {
  dragging.value = false
  const files = event.dataTransfer.files
  if (!files || files.length === 0) return
  if (selectedTool.value === 'merge') {
    for (const file of files) {
      uploadFile(file)
    }
  } else {
    uploadFile(files[0])
  }
}

async function uploadFile(file) {
  errorMessage.value = ''
  uploading.value = true
  uploadProgress.value = 0
  selectedFile.value = null
  try {
    const result = await uploadMediaFile(file, progress => { uploadProgress.value = progress })
    if (selectedTool.value === 'merge') {
      selectedFiles.value.push(result)
    } else {
      selectedFile.value = result
    }
    if (selectedTool.value === 'extract_audio') form.target_format = 'mp3'
  } catch (error) {
    errorMessage.value = error.message || '上传失败，请检查文件格式后重试'
  } finally {
    uploading.value = false
  }
}

async function uploadWatermarkFile(file) {
  uploadingWatermark.value = true
  try {
    watermarkImageFile.value = await uploadMediaFile(file)
  } catch (error) {
    errorMessage.value = error.message || '水印图片上传失败'
  } finally {
    uploadingWatermark.value = false
  }
}

function removeFile() {
  selectedFile.value = null
  errorMessage.value = ''
}

function removeMergeFile(index) {
  selectedFiles.value.splice(index, 1)
}

function moveFileUp(index) {
  if (index <= 0) return
  const tmp = selectedFiles.value[index]
  selectedFiles.value[index] = selectedFiles.value[index - 1]
  selectedFiles.value[index - 1] = tmp
}

function moveFileDown(index) {
  if (index >= selectedFiles.value.length - 1) return
  const tmp = selectedFiles.value[index]
  selectedFiles.value[index] = selectedFiles.value[index + 1]
  selectedFiles.value[index + 1] = tmp
}

async function submitTask() {
  if (selectedTool.value === 'merge') {
    if (selectedFiles.value.length < 2) {
      errorMessage.value = '视频合并至少需要上传 2 个文件'
      return
    }
  } else if (selectedTool.value === 'watermark') {
    if (watermarkType.value === 'image' && !watermarkImageFile.value) {
      errorMessage.value = '请上传水印图片'
      return
    }
    if (watermarkType.value === 'text' && !watermarkText.value.trim()) {
      errorMessage.value = '请输入水印文字内容'
      return
    }
  } else if (!selectedFile.value) {
    errorMessage.value = '请先上传文件'
    return
  }
  if (submitting.value) return
  errorMessage.value = ''
  submitting.value = true
  try {
    if (selectedTool.value === 'merge') {
      await createMergeTask({
        file_ids: selectedFiles.value.map(f => f.id),
        target_format: 'mp4',
        tool_code: 'merge'
      })
      selectedFiles.value = []
    } else if (selectedTool.value === 'watermark') {
      const payload = {
        file_id: selectedFile.value.id,
        target_format: form.target_format,
        tool_code: 'watermark',
        watermark_type: watermarkType.value,
        position: form.position || 'bottom-right',
        opacity: form.opacity || 1,
        watermark_width: form.watermark_width || 0
      }
      if (watermarkType.value === 'image') {
        payload.watermark_file_id = watermarkImageFile.value.id
      } else {
        payload.watermark_text = watermarkText.value.trim()
        payload.watermark_font_size = watermarkFontSize.value
        payload.watermark_font_color = watermarkFontColor.value
      }
      await createWatermarkTask(payload)
      selectedFile.value = null
      watermarkImageFile.value = null
      watermarkText.value = ''
    } else if (selectedTool.value === 'gif') {
      const payload = {
        file_id: selectedFile.value.id,
        tool_code: 'gif',
        quality: form.quality,
        start_time: form.start_time || 0,
        duration: form.duration || 0,
        frame_rate: form.frame_rate || 0
      }
      await createGifTask(payload)
      selectedFile.value = null
    } else {
      const payload = {
        file_id: selectedFile.value.id,
        target_format: form.target_format,
        tool_code: selectedTool.value,
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
      }
      await createConvertTask(payload)
      selectedFile.value = null
    }
    await loadTasks()
  } catch (error) {
    errorMessage.value = error.message || '任务提交失败，请稍后重试'
  } finally {
    submitting.value = false
  }
}

async function loadTasks() {
  tasksLoading.value = true
  try {
    const data = await listMediaTasks({ page: 1, size: 12 })
    tasks.value = data.items || []
  } catch (error) {
    if (error.message) errorMessage.value = error.message
  } finally {
    tasksLoading.value = false
  }
}

function startPolling() {
  if (pollTimer) return
  pollTimer = window.setInterval(async () => {
    const activeTasks = tasks.value.filter(task => ['queued', 'pending', 'processing'].includes(task.status))
    if (!activeTasks.length) return
    await Promise.all(activeTasks.map(async task => {
      try {
        const updated = await getMediaTask(task.id)
        const index = tasks.value.findIndex(item => item.id === task.id)
        if (index >= 0) tasks.value[index] = { ...tasks.value[index], ...updated }
      } catch {
        // 单个任务查询失败不影响其他任务轮询
      }
    }))
  }, 2000)
}

async function cancelTask(task) {
  try {
    await cancelMediaTask(task.id)
    task.status = 'cancelled'
  } catch (error) {
    errorMessage.value = error.message || '取消失败'
  }
}

async function retryTask(task) {
  try {
    const result = await retryMediaTask(task.id)
    task.status = result.status || 'queued'
    task.progress = 0
    task.error_message = ''
  } catch (error) {
    errorMessage.value = error.message || '重试失败'
  }
}

async function downloadTask(task) {
  try {
    const result = await getMediaTaskDownload(task.id)
    const url = result.download_url.startsWith('http')
      ? result.download_url
      : `${window.location.origin}${result.download_url}`
    const response = await fetch(url, {
      headers: authStore.token ? { Authorization: `Bearer ${authStore.token}` } : {}
    })
    if (!response.ok) throw new Error('下载文件失败')
    const blobUrl = URL.createObjectURL(await response.blob())
    const anchor = document.createElement('a')
    anchor.href = blobUrl
    anchor.download = result.file_name || 'media-result'
    document.body.appendChild(anchor)
    anchor.click()
    anchor.remove()
    URL.revokeObjectURL(blobUrl)
  } catch (error) {
    errorMessage.value = error.message || '获取下载地址失败'
  }
}

async function deleteTask(task) {
  if (!isDeletableTask(task) || deletingTaskId.value) return
  if (!window.confirm('确定删除这条任务记录吗？')) return
  deletingTaskId.value = task.id
  try {
    await deleteMediaTask(task.id)
    tasks.value = tasks.value.filter(item => item.id !== task.id)
  } catch (error) {
    errorMessage.value = error.message || '删除任务失败'
  } finally {
    deletingTaskId.value = null
  }
}

async function deleteAllTasks() {
  const deletableTasks = tasks.value.filter(isDeletableTask)
  if (!deletableTasks.length || deletingTasks.value) return
  if (!window.confirm(`确定清空 ${deletableTasks.length} 条已结束任务吗？`)) return
  deletingTasks.value = true
  try {
    await deleteMediaTasks(deletableTasks.map(task => task.id))
    const deletableIds = new Set(deletableTasks.map(task => task.id))
    tasks.value = tasks.value.filter(task => !deletableIds.has(task.id))
  } catch (error) {
    errorMessage.value = error.message || '批量删除任务失败'
  } finally {
    deletingTasks.value = false
  }
}

function isDeletableTask(task) {
  return !['queued', 'pending', 'processing'].includes(task.status)
}

function formatBytes(bytes) {
  if (!bytes) return '0 B'
  const units = ['B', 'KB', 'MB', 'GB']
  const index = Math.min(Math.floor(Math.log(bytes) / Math.log(1024)), units.length - 1)
  return `${(bytes / (1024 ** index)).toFixed(index ? 1 : 0)} ${units[index]}`
}

function formatDuration(milliseconds) {
  const seconds = Math.round(milliseconds / 1000)
  const minutes = Math.floor(seconds / 60)
  return `${String(minutes).padStart(2, '0')}:${String(seconds % 60).padStart(2, '0')}`
}

function formatDate(value) {
  if (!value) return ''
  return new Date(value).toLocaleString('zh-CN', { month: '2-digit', day: '2-digit', hour: '2-digit', minute: '2-digit' })
}

function toolName(code) {
  return tools.find(tool => tool.code === code)?.name || code || '媒体任务'
}

function statusLabel(status) {
  return { queued: '排队中', pending: '排队中', processing: '处理中', completed: '已完成', failed: '失败', cancelled: '已取消' }[status] || status
}

onMounted(async () => {
  try {
    capabilities.value = await getCapabilities()
  } catch {
    capabilities.value = {}
  }
  await loadTasks()
  startPolling()
})

onUnmounted(() => {
  if (pollTimer) window.clearInterval(pollTimer)
})
</script>

<style scoped>
.media-page {
  max-width: 1180px;
  margin: 0 auto;
  padding: 46px 24px 72px;
}
.media-header {
  display: flex;
  justify-content: space-between;
  gap: 24px;
  align-items: flex-start;
  margin-bottom: 30px;
}
.eyebrow, .section-kicker {
  color: var(--accent-cyan);
  font-size: 11px;
  font-weight: 700;
  letter-spacing: .16em;
  margin-bottom: 10px;
}
.media-header h1 {
  color: var(--text-primary);
  font-size: clamp(30px, 5vw, 48px);
  letter-spacing: -.04em;
  line-height: 1.1;
}
.lead {
  max-width: 640px;
  margin-top: 14px;
  color: var(--text-secondary);
  line-height: 1.7;
}
.back-link {
  white-space: nowrap;
  color: var(--text-secondary);
  border: 1px solid var(--border-default);
  border-radius: 999px;
  padding: 9px 15px;
  font-size: 13px;
}
.back-link:hover { color: var(--text-primary); border-color: var(--border-hover); }
.tool-grid {
  display: grid;
  grid-template-columns: repeat(5, 1fr);
  gap: 12px;
  margin-bottom: 22px;
}
.tool-card {
  position: relative;
  display: flex;
  align-items: flex-start;
  gap: 12px;
  min-height: 108px;
  padding: 17px;
  text-align: left;
  color: var(--text-primary);
  background: var(--bg-card);
  border: 1px solid var(--border-default);
  box-shadow: var(--shadow-sm);
}
.tool-card:hover, .tool-card.active { border-color: var(--accent-primary); background: var(--bg-hover); }
.tool-icon {
  display: grid;
  place-items: center;
  width: 34px;
  height: 34px;
  flex: 0 0 34px;
  border-radius: 10px;
  color: var(--accent-light);
  background: var(--purple-bg);
  font-size: 21px;
}
.tool-card-body { display: grid; gap: 7px; }
.tool-card-body strong { font-size: 14px; }
.tool-card-body small { color: var(--text-muted); line-height: 1.45; }
.selected-mark { position: absolute; right: 10px; top: 10px; color: var(--green); font-size: 12px; }
.workspace-grid { display: grid; grid-template-columns: minmax(0, 1.6fr) minmax(300px, .8fr); gap: 22px; align-items: start; }
.workspace-card, .history-card { padding: 24px; background: var(--bg-card); border: 1px solid var(--border-default); border-radius: 16px; box-shadow: var(--shadow-sm); }
.section-heading { display: flex; justify-content: space-between; gap: 16px; align-items: center; margin-bottom: 20px; }
.section-heading.compact { margin-bottom: 16px; }
.history-card .section-heading.compact { align-items: flex-start; }
.history-card .section-heading.compact > div:last-child { display: flex; gap: 12px; align-items: center; }
.danger-text-button { color: var(--red); }
.danger-text-button:disabled { opacity: .55; cursor: not-allowed; }
.section-heading h2, .section-heading h3 { color: var(--text-primary); font-size: 20px; }
.section-heading h3 { font-size: 17px; }
.section-kicker { margin-bottom: 6px; font-size: 10px; }
.format-hint { color: var(--text-muted); font-size: 12px; text-align: right; }
.drop-zone {
  display: grid;
  place-items: center;
  gap: 9px;
  min-height: 218px;
  padding: 28px;
  text-align: center;
  border: 1px dashed var(--border-hover);
  border-radius: 13px;
  color: var(--text-secondary);
  background: var(--bg-input);
  transition: border-color .2s, background .2s;
}
.drop-zone:hover, .drop-zone.dragging { border-color: var(--accent-primary); background: var(--bg-hover); }
.drop-zone.has-file { display: flex; justify-content: flex-start; text-align: left; min-height: 104px; padding: 19px; }
.upload-icon { display: grid; place-items: center; width: 48px; height: 48px; border-radius: 14px; color: var(--accent-light); background: var(--purple-bg); font-size: 28px; }
.file-icon { display: grid; place-items: center; width: 44px; height: 44px; flex: 0 0 44px; border-radius: 12px; color: var(--accent-cyan); background: rgba(6, 182, 212, .1); font-size: 24px; }
.file-info { display: grid; gap: 4px; min-width: 0; flex: 1; }
.file-info strong { overflow: hidden; color: var(--text-primary); text-overflow: ellipsis; white-space: nowrap; }
.file-info span { color: var(--text-muted); font-size: 12px; }
.file-meta { color: var(--accent-cyan) !important; }
.remove-file { padding: 6px 10px; color: var(--text-muted); background: transparent; font-size: 12px; }
.remove-file:hover { color: var(--red); }
.upload-spinner, .button-spinner { width: 18px; height: 18px; border: 2px solid var(--border-hover); border-top-color: var(--accent-primary); border-radius: 50%; animation: spin .8s linear infinite; }
.button-spinner { display: inline-block; width: 14px; height: 14px; margin-right: 7px; vertical-align: -2px; }
.progress-track { display: inline-block; width: 100%; height: 5px; overflow: hidden; border-radius: 999px; background: var(--bg-hover); }
.progress-track span { display: block; height: 100%; border-radius: inherit; background: var(--accent-gradient); transition: width .25s ease; }
.drop-zone > .progress-track { max-width: 280px; margin-top: 3px; }
.message { margin-top: 14px; padding: 11px 13px; border-radius: 9px; font-size: 13px; line-height: 1.5; }
.error-message { color: var(--red); background: var(--red-bg); border: 1px solid rgba(239, 68, 68, .2); }
.options-form { margin-top: 28px; padding-top: 25px; border-top: 1px solid var(--border-default); }
.form-grid, .advanced-grid { display: grid; grid-template-columns: repeat(2, minmax(0, 1fr)); gap: 14px; }
.form-grid label, .advanced-grid label { display: grid; gap: 7px; }
.form-grid label > span, .advanced-grid label > span { color: var(--text-secondary); font-size: 12px; }
.advanced-toggle { margin: 13px 0 4px; }
.text-button { padding: 4px 0; color: var(--accent-light); background: transparent; font-size: 12px; }
.text-button:hover { color: var(--accent-cyan); }
.advanced-grid { padding: 14px; margin: 9px 0 18px; border: 1px solid var(--border-default); border-radius: 10px; background: var(--bg-input); }
.submit-button { width: 100%; margin-top: 22px; padding: 13px 20px; color: white; background: var(--accent-gradient); font-weight: 700; }
.submit-button:disabled { opacity: .6; cursor: not-allowed; }
.empty-hint { padding: 21px 0 3px; color: var(--text-muted); font-size: 13px; }

/* 合并文件列表 */
.merge-file-list { margin-top: 14px; }
.merge-file-header { margin-bottom: 10px; }
.merge-file-label { color: var(--text-secondary); font-size: 12px; }
.merge-file-item { display: flex; align-items: center; gap: 10px; padding: 9px 11px; margin-bottom: 6px; border: 1px solid var(--border-default); border-radius: 9px; background: var(--bg-input); }
.merge-file-index { width: 22px; height: 22px; display: grid; place-items: center; border-radius: 50%; background: var(--accent-primary); color: #fff; font-size: 11px; font-weight: 700; flex: 0 0 22px; }
.merge-file-info { flex: 1; min-width: 0; }
.merge-file-info strong { display: block; overflow: hidden; color: var(--text-primary); text-overflow: ellipsis; white-space: nowrap; font-size: 13px; }
.merge-file-info span { color: var(--text-muted); font-size: 11px; }
.merge-file-actions { display: flex; gap: 4px; flex: 0 0 auto; align-items: center; }
.move-btn { padding: 3px 6px; color: var(--text-secondary); background: transparent; font-size: 13px; }
.move-btn:hover { color: var(--text-primary); }
.move-btn:disabled { opacity: .3; cursor: not-allowed; }

/* 水印图片上传 */
.watermark-image-section { margin-top: 16px; }
.watermark-drop { display: flex; align-items: center; gap: 11px; padding: 14px; border: 1px dashed var(--border-hover); border-radius: 11px; background: var(--bg-input); cursor: pointer; }
.watermark-drop:hover { border-color: var(--accent-primary); background: var(--bg-hover); }
.watermark-drop strong { font-size: 13px; }
.watermark-drop span { color: var(--text-muted); font-size: 11px; }
.upload-icon.small { width: 36px; height: 36px; font-size: 20px; }

/* 单选按钮组 */
.radio-group { display: flex; gap: 16px; }
.radio-label { display: flex !important; flex-direction: row !important; align-items: center; gap: 6px; cursor: pointer; }
.radio-label input[type="radio"] { cursor: pointer; }
.radio-label span { color: var(--text-primary); font-size: 14px; }

/* 全宽表单字段 */
.full-width { grid-column: 1 / -1; }
.history-card { min-height: 300px; }
.history-loading, .history-empty { padding: 42px 12px; color: var(--text-muted); text-align: center; }
.history-empty span { display: block; margin-bottom: 12px; color: var(--accent-purple); font-size: 34px; }
.history-empty small { display: block; margin-top: 7px; line-height: 1.5; }
.task-list { display: grid; gap: 2px; }
.task-item { display: flex; justify-content: space-between; gap: 10px; padding: 14px 0; border-top: 1px solid var(--border-default); }
.task-main { min-width: 0; flex: 1; }
.task-title-row { display: flex; justify-content: space-between; gap: 8px; align-items: center; }
.task-title-row strong { overflow: hidden; color: var(--text-primary); font-size: 13px; text-overflow: ellipsis; white-space: nowrap; }
.task-status { padding: 3px 6px; border-radius: 5px; background: var(--bg-hover); color: var(--text-muted); font-size: 10px; white-space: nowrap; }
.task-status.completed { color: var(--green); background: var(--green-bg); }
.task-status.failed { color: var(--red); background: var(--red-bg); }
.task-status.processing { color: var(--accent-cyan); background: rgba(6, 182, 212, .1); }
.task-progress { display: flex; gap: 8px; align-items: center; margin-top: 10px; }
.task-progress .progress-track { flex: 1; }
.task-progress small { color: var(--text-muted); font-size: 10px; }
.task-error { margin-top: 7px; color: var(--red); font-size: 11px; line-height: 1.4; }
.task-date { display: block; margin-top: 7px; color: var(--text-muted); font-size: 10px; }
.task-actions { flex: 0 0 auto; align-self: center; }
.task-action { padding: 5px 8px; color: var(--text-secondary); background: var(--bg-hover); font-size: 11px; }
.task-action:hover { color: var(--text-primary); }
.task-action.success { color: var(--green); }
.visually-hidden { position: absolute; width: 1px; height: 1px; overflow: hidden; clip: rect(0 0 0 0); white-space: nowrap; clip-path: inset(50%); }
@keyframes spin { to { transform: rotate(360deg); } }
@media (max-width: 900px) {
  .tool-grid { grid-template-columns: repeat(3, 1fr); }
  .workspace-grid { grid-template-columns: 1fr; }
  .history-card { min-height: 0; }
}
@media (max-width: 600px) {
  .media-page { padding: 30px 16px 52px; }
  .media-header { display: block; }
  .back-link { display: inline-block; margin-top: 18px; }
  .tool-grid { grid-template-columns: repeat(2, 1fr); }
  .tool-card { min-height: 92px; padding: 13px; }
  .workspace-card, .history-card { padding: 18px; border-radius: 13px; }
  .section-heading { align-items: flex-start; }
  .format-hint { max-width: 120px; }
  .drop-zone.has-file { align-items: flex-start; }
  .form-grid, .advanced-grid { grid-template-columns: 1fr; }
  .remove-file { padding: 4px; }
}
@media (max-width: 375px) {
  .tool-grid { gap: 8px; }
  .tool-card { gap: 8px; }
  .tool-icon { width: 29px; height: 29px; flex-basis: 29px; font-size: 17px; }
  .tool-card-body small { font-size: 10px; }
}
</style>
