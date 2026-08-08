<template>
  <div class="param-panel">
    <!-- 基础参数 -->
    <div class="param-section">
      <p class="param-section-title">基本参数</p>

      <!-- 输出格式 -->
      <div class="param-row">
        <label class="param-label">输出格式</label>
        <select
          :value="form.target_format"
          class="param-select"
          @change="updateForm('target_format', $event.target.value)"
        >
          <option v-for="fmt in formatOptions" :key="fmt" :value="fmt">
            {{ fmt.toUpperCase() }}
          </option>
        </select>
      </div>

      <!-- 质量（compress 模式） -->
      <div v-if="toolCode === 'compress'" class="param-row">
        <label class="param-label">压缩质量</label>
        <select
          :value="form.quality"
          class="param-select"
          @change="updateForm('quality', $event.target.value)"
        >
          <option value="high">高质量（文件较大）</option>
          <option value="medium">均衡</option>
          <option value="low">小文件（质量较低）</option>
        </select>
      </div>

      <!-- 分辨率 -->
      <div class="param-row">
        <label class="param-label">分辨率</label>
        <select
          :value="form.resolution"
          class="param-select"
          @change="updateForm('resolution', $event.target.value)"
        >
          <option value="">原始分辨率</option>
          <option value="3840x2160">4K (3840×2160)</option>
          <option value="1920x1080">1080p (1920×1080)</option>
          <option value="1280x720">720p (1280×720)</option>
          <option value="854x480">480p (854×480)</option>
          <option value="640x360">360p (640×360)</option>
        </select>
      </div>

      <!-- 帧率（非音频） -->
      <div v-if="!isAudioFile" class="param-row">
        <label class="param-label">帧率 (fps)</label>
        <select
          :value="form.frame_rate"
          class="param-select"
          @change="updateForm('frame_rate', Number($event.target.value))"
        >
          <option :value="0">原始帧率</option>
          <option :value="60">60</option>
          <option :value="30">30</option>
          <option :value="24">24</option>
          <option :value="15">15</option>
          <option :value="10">10</option>
        </select>
      </div>

      <!-- 截取参数（trim 模式） -->
      <template v-if="toolCode === 'trim'">
        <div class="param-row">
          <label class="param-label">开始时间 (秒)</label>
          <input
            type="number"
            min="0"
            :value="form.start_time"
            class="param-input"
            placeholder="0"
            @input="updateForm('start_time', Number($event.target.value) || 0)"
          />
        </div>
        <div class="param-row">
          <label class="param-label">持续时长 (秒)</label>
          <input
            type="number"
            min="1"
            :value="form.duration"
            class="param-input"
            placeholder="0"
            @input="updateForm('duration', Number($event.target.value) || 0)"
          />
        </div>
      </template>

      <!-- 音频码率（非纯音频提取时） -->
      <div class="param-row">
        <label class="param-label">音频码率</label>
        <select
          :value="form.audio_bitrate"
          class="param-select"
          @change="updateForm('audio_bitrate', $event.target.value)"
        >
          <option value="">原始</option>
          <option value="320k">320 kbps</option>
          <option value="256k">256 kbps</option>
          <option value="192k">192 kbps</option>
          <option value="128k">128 kbps</option>
          <option value="96k">96 kbps</option>
          <option value="64k">64 kbps</option>
        </select>
      </div>
    </div>

    <!-- 高级参数 -->
    <div class="param-section">
      <button
        class="param-advanced-toggle"
        type="button"
        @click="showAdvanced = !showAdvanced"
      >
        <span>高级参数</span>
        <svg
          :class="['toggle-arrow', { 'toggle-arrow-open': showAdvanced }]"
          width="12"
          height="12"
          viewBox="0 0 24 24"
          fill="none"
          stroke="currentColor"
          stroke-width="2"
          stroke-linecap="round"
          stroke-linejoin="round"
        >
          <polyline points="6 9 12 15 18 9" />
        </svg>
      </button>

      <div v-if="showAdvanced" class="param-advanced-body">
        <!-- 视频编码器 -->
        <div class="param-row">
          <label class="param-label">视频编码器</label>
          <select
            :value="form.video_codec"
            class="param-select"
            @change="updateForm('video_codec', $event.target.value)"
          >
            <option value="">自动</option>
            <option value="h264">H.264</option>
            <option value="h265">H.265 / HEVC</option>
            <option value="vp9">VP9</option>
            <option value="av1">AV1</option>
          </select>
        </div>

        <!-- 音频编码器 -->
        <div class="param-row">
          <label class="param-label">音频编码器</label>
          <select
            :value="form.audio_codec"
            class="param-select"
            @change="updateForm('audio_codec', $event.target.value)"
          >
            <option value="">自动</option>
            <option value="aac">AAC</option>
            <option value="mp3">MP3</option>
            <option value="opus">Opus</option>
            <option value="vorbis">Vorbis</option>
            <option value="pcm_s16le">PCM S16LE</option>
          </select>
        </div>

        <!-- 采样率 -->
        <div class="param-row">
          <label class="param-label">采样率 (Hz)</label>
          <select
            :value="form.sample_rate"
            class="param-select"
            @change="updateForm('sample_rate', Number($event.target.value))"
          >
            <option :value="0">原始</option>
            <option :value="48000">48000</option>
            <option :value="44100">44100</option>
            <option :value="22050">22050</option>
            <option :value="16000">16000</option>
          </select>
        </div>

        <!-- 声道 -->
        <div class="param-row">
          <label class="param-label">声道</label>
          <select
            :value="form.channels"
            class="param-select"
            @change="updateForm('channels', Number($event.target.value))"
          >
            <option :value="0">原始</option>
            <option :value="2">立体声</option>
            <option :value="1">单声道</option>
          </select>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed } from 'vue'
import { useMediaStore } from '../../stores/media'

const props = defineProps({
  form: { type: Object, required: true },
  toolCode: { type: String, required: true },
  capabilities: { type: Object, default: null },
  isAudioFile: { type: Boolean, default: false }
})

const emit = defineEmits(['update:form'])

const store = useMediaStore()
const showAdvanced = ref(false)

const formatOptions = computed(() => {
  if (props.capabilities?.formats) {
    return props.capabilities.formats
  }
  const defaults = ['mp4', 'mov', 'mkv', 'webm', 'avi', 'gif', 'mp3', 'wav', 'aac', 'ogg']
  return defaults
})

function updateForm(key, value) {
  const updated = { ...props.form, [key]: value }
  emit('update:form', updated)
}
</script>

<style scoped>
.param-panel {
  display: flex;
  flex-direction: column;
  gap: 16px;
  margin-top: 16px;
}
.param-section {
  border: 1px solid var(--border-default);
  border-radius: 9px;
  padding: 14px 16px;
  background: var(--bg-card);
}
.param-section-title {
  color: var(--text-secondary);
  font-size: 12px;
  font-weight: 600;
  margin: 0 0 12px;
  letter-spacing: .04em;
}
.param-row {
  display: flex;
  flex-direction: column;
  gap: 5px;
  margin-bottom: 12px;
}
.param-row:last-child {
  margin-bottom: 0;
}
.param-label {
  color: var(--text-secondary);
  font-size: 12px;
}
.param-select,
.param-input {
  width: 100%;
  padding: 8px 10px;
  border: 1px solid var(--border-default);
  border-radius: 7px;
  background: var(--bg-input);
  color: var(--text-primary);
  font-size: 13px;
  outline: none;
  transition: border-color .15s;
  box-sizing: border-box;
}
.param-select:focus,
.param-input:focus {
  border-color: var(--accent-primary);
}
.param-input::placeholder {
  color: var(--text-muted);
}

/* 高级参数折叠 */
.param-advanced-toggle {
  display: flex;
  align-items: center;
  gap: 6px;
  width: 100%;
  padding: 0;
  border: none;
  background: transparent;
  color: var(--text-secondary);
  font-size: 12px;
  font-weight: 600;
  cursor: pointer;
  letter-spacing: .04em;
}
.param-advanced-toggle:hover {
  color: var(--text-primary);
}
.toggle-arrow {
  transition: transform .2s;
}
.toggle-arrow-open {
  transform: rotate(180deg);
}
.param-advanced-body {
  margin-top: 12px;
  padding-top: 12px;
  border-top: 1px solid var(--border-default);
}
</style>