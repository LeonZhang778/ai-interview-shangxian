<template>
  <div class="watermark-editor">
    <p class="editor-title">水印设置</p>

    <!-- 水印类型切换 -->
    <div class="type-switch">
      <label class="type-radio">
        <input
          type="radio"
          value="text"
          :checked="local.type === 'text'"
          @change="updateLocal('type', 'text')"
        />
        <span class="radio-label">文字水印</span>
      </label>
      <label class="type-radio">
        <input
          type="radio"
          value="image"
          :checked="local.type === 'image'"
          @change="updateLocal('type', 'image')"
        />
        <span class="radio-label">图片水印</span>
      </label>
    </div>

      <div v-if="local.type === 'image'" class="param-row">
      <label class="param-label">上传水印图片</label>
      <div
        class="image-upload-zone"
        @click="triggerImageInput"
        role="button"
        tabindex="0"
        :aria-label="local.imageFile ? '已选择水印图片，点击重新选择' : '点击选择水印图片'"
        @keydown.enter.prevent="triggerImageInput"
        @keydown.space.prevent="triggerImageInput"
      >
        <input
          ref="imageInput"
          type="file"
          accept="image/png,image/jpeg,image/webp"
          class="file-input-hidden"
          @change="onImageSelected"
          tabindex="-1"
        />
        <div v-if="local.imageFile" class="image-selected">
          <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round">
            <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4" />
            <polyline points="17 8 12 3 7 8" />
            <line x1="12" y1="3" x2="12" y2="15" />
          </svg>
          <span class="image-name">{{ local.imageFile.original_name || '水印图片' }}</span>
        </div>
        <div v-else class="image-empty">
          <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round">
            <rect x="3" y="3" width="18" height="18" rx="2" ry="2" />
            <circle cx="8.5" cy="8.5" r="1.5" />
            <polyline points="21 15 16 10 5 21" />
          </svg>
          <span>点击选择水印图片</span>
        </div>
      </div>
    </div>

    <!-- 文字水印参数 -->
    <template v-if="local.type === 'text'">
      <div class="param-row">
        <label class="param-label">水印文字</label>
        <input
          type="text"
          maxlength="100"
          :value="local.text"
          class="param-input"
          placeholder="请输入水印文字"
          @input="updateLocal('text', $event.target.value)"
        />
        <p class="char-count">{{ (local.text || '').length }}/100</p>
      </div>

      <div class="param-row">
        <label class="param-label">字号</label>
        <input
          type="number"
          min="8"
          max="200"
          :value="local.fontSize"
          class="param-input"
          placeholder="36"
          @input="updateLocal('fontSize', Number($event.target.value) || 36)"
        />
      </div>

      <div class="param-row">
        <label class="param-label">颜色</label>
        <select
          :value="local.fontColor"
          class="param-select"
          @change="updateLocal('fontColor', $event.target.value)"
        >
          <option value="#ffffff">白色</option>
          <option value="#000000">黑色</option>
          <option value="#ef4444">红色</option>
          <option value="#eab308">黄色</option>
          <option value="#6b7280">灰色</option>
        </select>
      </div>
    </template>

    <!-- 共用参数 -->
    <div class="param-row">
      <label class="param-label">位置</label>
      <select
        :value="local.position"
        class="param-select"
        @change="updateLocal('position', $event.target.value)"
      >
        <option value="top-left">左上角</option>
        <option value="top-right">右上角</option>
        <option value="bottom-left">左下角</option>
        <option value="bottom-right">右下角</option>
        <option value="center">居中</option>
      </select>
    </div>

    <div class="param-row">
      <label class="param-label">透明度 ({{ Math.round(local.opacity * 100) }}%)</label>
      <input
        type="range"
        min="0.1"
        max="1.0"
        step="0.1"
        :value="local.opacity"
        class="param-range"
        @input="updateLocal('opacity', Number($event.target.value))"
      />
    </div>

    <div class="param-row">
      <label class="param-label">水印宽度 (px)</label>
      <input
        type="number"
        min="0"
        max="1920"
        :value="local.watermark_width"
        class="param-input"
        placeholder="0（自动）"
        @input="updateLocal('watermark_width', Number($event.target.value) || 0)"
      />
      <p class="input-hint">0 表示自动宽度</p>
    </div>
  </div>
</template>

<script setup>
import { reactive, watch, ref } from 'vue'
import { useMediaStore } from '../../stores/media'

const props = defineProps({
  modelValue: { type: Object, required: true },
  capabilities: { type: Object, default: null }
})

const emit = defineEmits(['update:modelValue'])

const store = useMediaStore()

const local = reactive({
  type: props.modelValue?.type || 'text',
  text: props.modelValue?.text || '',
  fontSize: props.modelValue?.fontSize || 36,
  fontColor: props.modelValue?.fontColor || '#ffffff',
  position: props.modelValue?.position || 'bottom-right',
  opacity: props.modelValue?.opacity ?? 0.5,
  watermark_width: props.modelValue?.watermark_width || 0,
  imageFile: props.modelValue?.imageFile || null
})

const imageInput = ref(null)

// 将 modelValue 的变更同步到 local
watch(() => props.modelValue, (val) => {
  if (!val) return
  local.type = val.type || 'text'
  local.text = val.text || ''
  local.fontSize = val.fontSize || 36
  local.fontColor = val.fontColor || '#ffffff'
  local.position = val.position || 'bottom-right'
  local.opacity = val.opacity ?? 0.5
  local.watermark_width = val.watermark_width || 0
  local.imageFile = val.imageFile || null
}, { deep: true })

function emitLocal() {
  emit('update:modelValue', { ...local })
}

function updateLocal(key, value) {
  local[key] = value
  emitLocal()
}

function triggerImageInput() {
  imageInput.value?.click()
}

async function onImageSelected(event) {
  const file = event.target.files?.[0]
  if (!file) return

  try {
    const result = await store.uploadFile(file)
    local.imageFile = result
    emitLocal()
  } catch {
    // store 已处理 toast
  }

  if (imageInput.value) {
    imageInput.value.value = ''
  }
}
</script>

<style scoped>
.watermark-editor {
  border: 1px solid var(--border-default);
  border-radius: 9px;
  padding: 14px 16px;
  background: var(--bg-card);
  margin-top: 16px;
}
.editor-title {
  color: var(--text-secondary);
  font-size: 12px;
  font-weight: 600;
  margin: 0 0 12px;
  letter-spacing: .04em;
}

/* 类型切换 */
.type-switch {
  display: flex;
  gap: 8px;
  margin-bottom: 14px;
}
.type-radio {
  flex: 1;
  cursor: pointer;
}
.type-radio input {
  position: absolute;
  opacity: 0;
  width: 0;
  height: 0;
}
.radio-label {
  display: block;
  text-align: center;
  padding: 8px 12px;
  border: 1px solid var(--border-default);
  border-radius: 7px;
  color: var(--text-secondary);
  font-size: 13px;
  transition: border-color .15s, color .15s, background .15s;
}
.type-radio input:checked + .radio-label {
  border-color: var(--accent-primary);
  color: var(--accent-primary);
  background: var(--bg-hover);
}

/* 参数行 */
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
.param-input,
.param-select {
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
.param-input:focus,
.param-select:focus {
  border-color: var(--accent-primary);
}
.param-input::placeholder {
  color: var(--text-muted);
}
.char-count {
  color: var(--text-muted);
  font-size: 11px;
  text-align: right;
  margin: 2px 0 0;
}
.input-hint {
  color: var(--text-muted);
  font-size: 11px;
  margin: 2px 0 0;
}

/* 滑块 */
.param-range {
  -webkit-appearance: none;
  appearance: none;
  width: 100%;
  height: 5px;
  border-radius: 3px;
  background: var(--border-default);
  outline: none;
  cursor: pointer;
}
.param-range::-webkit-slider-thumb {
  -webkit-appearance: none;
  appearance: none;
  width: 16px;
  height: 16px;
  border-radius: 50%;
  background: var(--accent-primary);
  border: 2px solid var(--bg-card);
  cursor: pointer;
  box-shadow: var(--shadow-sm);
}

/* 图片上传区域 */
.image-upload-zone {
  border: 1px dashed var(--border-hover);
  border-radius: 9px;
  background: var(--bg-input);
  padding: 14px 16px;
  cursor: pointer;
  transition: border-color .2s, background .2s;
  display: flex;
  align-items: center;
  justify-content: center;
}
.image-upload-zone:hover {
  border-color: var(--accent-primary);
  background: var(--bg-hover);
}
.file-input-hidden {
  position: absolute;
  width: 0;
  height: 0;
  opacity: 0;
  overflow: hidden;
  pointer-events: none;
}
.image-selected {
  display: flex;
  align-items: center;
  gap: 8px;
  color: var(--accent-primary);
  font-size: 13px;
}
.image-name {
  color: var(--text-primary);
}
.image-empty {
  display: flex;
  align-items: center;
  gap: 8px;
  color: var(--text-muted);
  font-size: 13px;
}
</style>