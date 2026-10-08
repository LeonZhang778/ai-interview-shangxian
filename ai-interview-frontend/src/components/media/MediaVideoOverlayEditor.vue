<template>
  <div class="overlay-editor">
    <div class="overlay-header">
      <div>
        <p class="overlay-kicker">STEP 02</p>
        <h3>{{ mode === 'watermark' ? '编辑预览' : '框选遮挡区域' }}</h3>
      </div>
      <span class="overlay-hint">
        {{ mode === 'watermark' ? '拖动水印到封面任意位置，输出会按同一坐标渲染' : '在封面画面上拖拽选择遮挡区域' }}
      </span>
    </div>

    <div class="video-stage">
      <div v-if="loading" class="stage-placeholder">
        <span>正在生成视频首帧预览...</span>
        <div class="stage-loading-bar" aria-hidden="true"></div>
      </div>
      <div v-else-if="!coverUrl" class="stage-placeholder">暂时无法加载视频封面预览</div>
      <div v-else ref="frameRef" class="video-frame" :style="videoFrameStyle">
        <img
          :src="coverUrl"
          class="preview-cover"
          alt="视频首帧预览"
          draggable="false"
          @load="syncFrameSize"
        />

        <div
          v-if="mode === 'watermark'"
          class="watermark-layer"
          @mousedown.self.prevent
        >
          <div
            ref="watermarkRef"
            class="watermark-preview"
            :style="watermarkStyle"
            @mousedown.prevent="startWatermarkDrag"
            @wheel.prevent.stop="handleWatermarkWheel"
          >
            <img
              v-if="watermarkValue.type === 'image' && imageUrl"
              :src="imageUrl"
              alt="水印图片"
              class="watermark-image"
              draggable="false"
              @load="syncFrameSize"
            />
            <span
              v-else
              class="watermark-text"
              :style="watermarkTextStyle"
            >
              {{ watermarkPreviewText }}
            </span>
          </div>
        </div>

        <div
          v-else
          ref="selectLayerRef"
          class="redact-layer"
          @mousedown="startSelectRegion"
        >
          <div class="redact-box" :style="displayRegionStyle" @mousedown.stop="startMoveRegion">
            <span class="redact-label">{{ redactLabel }}</span>
            <span class="resize-handle" @mousedown.stop.prevent="startResizeRegion"></span>
          </div>
          <div v-if="drawing" class="redact-box drawing" :style="drawingStyle"></div>
        </div>
      </div>
    </div>

    <p v-if="mode === 'redact'" class="coordinate-tip">
      当前区域：X {{ Math.round(regionValue.region_x || 0) }} / Y {{ Math.round(regionValue.region_y || 0) }} / {{ Math.round(regionValue.region_width || 0) }} x {{ Math.round(regionValue.region_height || 0) }} px
    </p>
  </div>
</template>

<script setup>
import { computed, nextTick, onBeforeUnmount, onMounted, ref, watch } from 'vue'

const props = defineProps({
  file: { type: Object, default: null },
  mode: { type: String, default: 'watermark' },
  watermark: { type: Object, default: () => ({}) },
  region: { type: Object, default: () => ({}) },
  redactType: { type: String, default: 'blur' },
})

const emit = defineEmits(['update:watermark', 'update:region'])

const frameRef = ref(null)
const watermarkRef = ref(null)
const selectLayerRef = ref(null)
const sourceVideoUrl = ref('')
const coverUrl = ref('')
const imageUrl = ref('')
const loading = ref(false)
const naturalSize = ref({ width: 0, height: 0 })
const imageNaturalSize = ref({ width: 0, height: 0 })
const displaySize = ref({ width: 0, height: 0 })
const drawing = ref(false)
const drawingRect = ref(null)
let resizeObserver = null

const watermarkValue = computed(() => props.watermark || {})
const regionValue = computed(() => props.region || {})

const redactLabel = computed(() => {
  const labels = { blur: '模糊', pixelate: '像素化', solid: '遮挡' }
  return labels[props.redactType] || '遮挡'
})

const watermarkPreviewText = computed(() => {
  return watermarkValue.value.text || '水印文字'
})

const displayRegion = computed(() => toDisplayRect(regionValue.value))

const displayRegionStyle = computed(() => ({
  left: `${displayRegion.value.x}px`,
  top: `${displayRegion.value.y}px`,
  width: `${displayRegion.value.width}px`,
  height: `${displayRegion.value.height}px`,
}))

const drawingStyle = computed(() => {
  if (!drawingRect.value) return {}
  return {
    left: `${drawingRect.value.x}px`,
    top: `${drawingRect.value.y}px`,
    width: `${drawingRect.value.width}px`,
    height: `${drawingRect.value.height}px`,
  }
})

const watermarkStyle = computed(() => {
  const style = {
    opacity: watermarkValue.value.opacity ?? 0.8,
    left: `${watermarkDisplayPoint.value.x}px`,
    top: `${watermarkDisplayPoint.value.y}px`,
    transform: `rotate(${Number(watermarkValue.value.rotation || 0)}deg)`,
  }

  if (watermarkValue.value.type === 'image') {
    style.width = `${watermarkDisplaySize.value.width}px`
  }

  return style
})

const watermarkTextStyle = computed(() => ({
  color: watermarkValue.value.fontColor || '#ffffff',
  fontSize: `${watermarkDisplayFontSize.value}px`,
}))

const watermarkDisplayFontSize = computed(() => {
  return Math.max(8, (Number(watermarkValue.value.fontSize) || 36) / scaleY())
})

const watermarkDisplaySize = computed(() => {
  if (watermarkValue.value.type === 'image') {
    const naturalWidth = imageNaturalSize.value.width || 160
    const naturalHeight = imageNaturalSize.value.height || naturalWidth
    const outputWidth = Number(watermarkValue.value.watermark_width || 0) || defaultOutputWatermarkWidth()
    const displayWidth = Math.max(24, outputWidth / scaleX())
    return {
      width: displayWidth,
      height: Math.max(16, displayWidth * (naturalHeight / naturalWidth)),
    }
  }

  const fontSize = watermarkDisplayFontSize.value
  const textWidth = watermarkPreviewText.value.length * fontSize * 0.62
  return {
    width: Math.max(40, textWidth),
    height: Math.max(20, fontSize * 1.25),
  }
})

const watermarkDisplayPoint = computed(() => {
  const frameWidth = displaySize.value.width || 0
  const frameHeight = displaySize.value.height || 0
  if (!frameWidth || !frameHeight) return { x: 12, y: 12 }

  if (watermarkValue.value.position === 'custom') {
    return {
      x: clamp((Number(watermarkValue.value.custom_x) || 0) / scaleX(), 0, Math.max(0, frameWidth - watermarkDisplaySize.value.width)),
      y: clamp((Number(watermarkValue.value.custom_y) || 0) / scaleY(), 0, Math.max(0, frameHeight - watermarkDisplaySize.value.height)),
    }
  }

  return defaultWatermarkPoint(watermarkValue.value.position || 'bottom-right')
})

const videoFrameStyle = computed(() => {
  const width = naturalSize.value.width
  const height = naturalSize.value.height
  if (!width || !height) return {}
  return {
    aspectRatio: `${width} / ${height}`,
    maxWidth: `${Math.round((width / height) * 420)}px`,
  }
})

watch(() => props.file?.id, () => {
  loadVideoCover()
}, { immediate: true })

watch(() => props.watermark?.imageFile?.id, () => {
  loadImagePreview()
}, { immediate: true })

watch(() => [
  props.watermark?.type,
  props.watermark?.text,
  props.watermark?.fontSize,
  props.watermark?.fontColor,
  props.watermark?.opacity,
  props.watermark?.watermark_width,
  props.watermark?.position,
], () => {
  nextTick(syncFrameSize)
}, { deep: true })

watch(() => props.region, () => {
  nextTick(syncFrameSize)
}, { deep: true })

onMounted(() => {
  resizeObserver = new ResizeObserver(syncFrameSize)
  if (frameRef.value) resizeObserver.observe(frameRef.value)
  window.addEventListener('resize', syncFrameSize)
})

onBeforeUnmount(() => {
  resizeObserver?.disconnect()
  window.removeEventListener('resize', syncFrameSize)
  revokeUrl(sourceVideoUrl.value)
  revokeUrl(coverUrl.value)
  revokeUrl(imageUrl.value)
})

async function fetchObjectUrl(path) {
  const response = await fetch(path, {
    headers: localStorage.getItem('token')
      ? { Authorization: `Bearer ${localStorage.getItem('token')}` }
      : {},
  })
  if (!response.ok) throw new Error('preview load failed')
  return URL.createObjectURL(await response.blob())
}

async function loadVideoCover() {
  revokeUrl(sourceVideoUrl.value)
  revokeUrl(coverUrl.value)
  sourceVideoUrl.value = ''
  coverUrl.value = ''
  naturalSize.value = { width: 0, height: 0 }
  displaySize.value = { width: 0, height: 0 }

  if (!props.file?.id) return
  loading.value = true
  try {
    sourceVideoUrl.value = await fetchObjectUrl(`/api/v1/media-tools/files/${props.file.id}/raw`)
    const cover = await captureFirstFrame(sourceVideoUrl.value)
    coverUrl.value = cover.url
    naturalSize.value = { width: cover.width, height: cover.height }
    await nextTick()
    if (frameRef.value && resizeObserver) resizeObserver.observe(frameRef.value)
    syncFrameSize()
  } catch {
    coverUrl.value = ''
  } finally {
    loading.value = false
  }
}

function captureFirstFrame(src) {
  return new Promise((resolve, reject) => {
    const video = document.createElement('video')
    const cleanup = () => {
      video.pause()
      video.removeAttribute('src')
      video.load()
    }

    const draw = () => {
      const width = video.videoWidth || props.file?.metadata?.video?.width || 0
      const height = video.videoHeight || props.file?.metadata?.video?.height || 0
      if (!width || !height) {
        cleanup()
        reject(new Error('missing video size'))
        return
      }

      const canvas = document.createElement('canvas')
      canvas.width = width
      canvas.height = height
      const ctx = canvas.getContext('2d')
      ctx.drawImage(video, 0, 0, width, height)
      canvas.toBlob((blob) => {
        cleanup()
        if (!blob) {
          reject(new Error('empty cover'))
          return
        }
        resolve({ url: URL.createObjectURL(blob), width, height })
      }, 'image/jpeg', 0.9)
    }

    video.muted = true
    video.playsInline = true
    video.preload = 'auto'
    video.src = src
    video.addEventListener('loadedmetadata', () => {
      if (Number.isFinite(video.duration) && video.duration > 0.1) {
        video.currentTime = 0.05
      } else {
        draw()
      }
    }, { once: true })
    video.addEventListener('seeked', draw, { once: true })
    video.addEventListener('loadeddata', () => {
      if (!Number.isFinite(video.duration) || video.duration <= 0.1) draw()
    }, { once: true })
    video.addEventListener('error', () => {
      cleanup()
      reject(new Error('video cover failed'))
    }, { once: true })
  })
}

async function loadImagePreview() {
  revokeUrl(imageUrl.value)
  imageUrl.value = ''
  imageNaturalSize.value = { width: 0, height: 0 }

  const fileId = props.watermark?.imageFile?.id
  if (!fileId) return

  try {
    imageUrl.value = await fetchObjectUrl(`/api/v1/media-tools/files/${fileId}/raw`)
    await loadImageNaturalSize(imageUrl.value)
    ensureDefaultImageWidth()
    await nextTick()
    syncFrameSize()
  } catch {
    imageUrl.value = ''
    imageNaturalSize.value = { width: 0, height: 0 }
  }
}

function loadImageNaturalSize(src) {
  return new Promise(resolve => {
    const image = new Image()
    image.onload = () => {
      imageNaturalSize.value = {
        width: image.naturalWidth || 0,
        height: image.naturalHeight || 0,
      }
      resolve()
    }
    image.onerror = () => resolve()
    image.src = src
  })
}

function ensureDefaultImageWidth() {
  if (watermarkValue.value.type !== 'image') return
  if (Number(watermarkValue.value.watermark_width || 0) > 0) return
  const width = defaultOutputWatermarkWidth()
  if (!width) return
  emit('update:watermark', {
    ...watermarkValue.value,
    watermark_width: width,
  })
}

function defaultOutputWatermarkWidth() {
  const videoWidth = naturalSize.value.width || props.file?.metadata?.video?.width || 0
  const imageWidth = imageNaturalSize.value.width || 160
  if (!videoWidth) return Math.min(200, imageWidth)
  return Math.round(Math.min(imageWidth, Math.max(80, videoWidth * 0.22)))
}

function revokeUrl(url) {
  if (url?.startsWith('blob:')) URL.revokeObjectURL(url)
}

function syncFrameSize() {
  const frame = frameRef.value
  if (!frame) return
  const rect = frame.getBoundingClientRect()
  displaySize.value = { width: rect.width, height: rect.height }

  if (props.mode === 'redact' && (!regionValue.value.region_width || !regionValue.value.region_height)) {
    emitRegionFromDisplay({
      x: Math.round(rect.width * 0.58),
      y: Math.round(rect.height * 0.12),
      width: Math.max(80, Math.round(rect.width * 0.25)),
      height: Math.max(50, Math.round(rect.height * 0.16)),
    })
  }
}

function scaleX() {
  return naturalSize.value.width && displaySize.value.width
    ? naturalSize.value.width / displaySize.value.width
    : 1
}

function scaleY() {
  return naturalSize.value.height && displaySize.value.height
    ? naturalSize.value.height / displaySize.value.height
    : 1
}

function toDisplayRect(region) {
  const width = Math.max(20, (Number(region.region_width) || 200) / scaleX())
  const height = Math.max(20, (Number(region.region_height) || 120) / scaleY())
  return {
    x: clamp((Number(region.region_x) || 0) / scaleX(), 0, Math.max(0, displaySize.value.width - width)),
    y: clamp((Number(region.region_y) || 0) / scaleY(), 0, Math.max(0, displaySize.value.height - height)),
    width,
    height,
  }
}

function emitRegionFromDisplay(rect) {
  const maxWidth = displaySize.value.width || rect.width
  const maxHeight = displaySize.value.height || rect.height
  const clean = {
    x: clamp(rect.x, 0, Math.max(0, maxWidth - 20)),
    y: clamp(rect.y, 0, Math.max(0, maxHeight - 20)),
    width: Math.max(20, Math.min(rect.width, maxWidth - rect.x)),
    height: Math.max(20, Math.min(rect.height, maxHeight - rect.y)),
  }

  emit('update:region', {
    ...regionValue.value,
    region_x: Math.round(clean.x * scaleX()),
    region_y: Math.round(clean.y * scaleY()),
    region_width: Math.round(clean.width * scaleX()),
    region_height: Math.round(clean.height * scaleY()),
  })
}

function startSelectRegion(event) {
  if (props.mode !== 'redact' || !selectLayerRef.value) return
  const bounds = selectLayerRef.value.getBoundingClientRect()
  const startX = clamp(event.clientX - bounds.left, 0, bounds.width)
  const startY = clamp(event.clientY - bounds.top, 0, bounds.height)
  drawing.value = true
  drawingRect.value = { x: startX, y: startY, width: 0, height: 0 }

  const onMove = (moveEvent) => {
    const currentX = clamp(moveEvent.clientX - bounds.left, 0, bounds.width)
    const currentY = clamp(moveEvent.clientY - bounds.top, 0, bounds.height)
    drawingRect.value = {
      x: Math.min(startX, currentX),
      y: Math.min(startY, currentY),
      width: Math.abs(currentX - startX),
      height: Math.abs(currentY - startY),
    }
  }

  const onUp = () => {
    const rect = drawingRect.value
    drawing.value = false
    drawingRect.value = null
    document.removeEventListener('mousemove', onMove)
    document.removeEventListener('mouseup', onUp)
    if (rect && rect.width >= 12 && rect.height >= 12) emitRegionFromDisplay(rect)
  }

  document.addEventListener('mousemove', onMove)
  document.addEventListener('mouseup', onUp)
}

function startMoveRegion(event) {
  const start = displayRegion.value
  const startX = event.clientX
  const startY = event.clientY

  const onMove = (moveEvent) => {
    emitRegionFromDisplay({
      ...start,
      x: start.x + moveEvent.clientX - startX,
      y: start.y + moveEvent.clientY - startY,
    })
  }

  const onUp = () => {
    document.removeEventListener('mousemove', onMove)
    document.removeEventListener('mouseup', onUp)
  }

  document.addEventListener('mousemove', onMove)
  document.addEventListener('mouseup', onUp)
}

function startResizeRegion(event) {
  const start = displayRegion.value
  const startX = event.clientX
  const startY = event.clientY

  const onMove = (moveEvent) => {
    emitRegionFromDisplay({
      ...start,
      width: start.width + moveEvent.clientX - startX,
      height: start.height + moveEvent.clientY - startY,
    })
  }

  const onUp = () => {
    document.removeEventListener('mousemove', onMove)
    document.removeEventListener('mouseup', onUp)
  }

  document.addEventListener('mousemove', onMove)
  document.addEventListener('mouseup', onUp)
}

function startWatermarkDrag(event) {
  const frame = frameRef.value
  const target = watermarkRef.value
  if (!frame || !target) return

  const bounds = frame.getBoundingClientRect()
  const targetBounds = target.getBoundingClientRect()
  const offsetX = event.clientX - targetBounds.left
  const offsetY = event.clientY - targetBounds.top

  const onMove = (moveEvent) => {
    const liveBounds = target.getBoundingClientRect()
    const targetWidth = liveBounds.width || targetBounds.width || 20
    const targetHeight = liveBounds.height || targetBounds.height || 20
    const x = clamp(moveEvent.clientX - bounds.left - offsetX, 0, Math.max(0, bounds.width - targetWidth))
    const y = clamp(moveEvent.clientY - bounds.top - offsetY, 0, Math.max(0, bounds.height - targetHeight))
    emitCustomWatermark(x, y)
  }

  const onUp = () => {
    document.removeEventListener('mousemove', onMove)
    document.removeEventListener('mouseup', onUp)
  }

  document.addEventListener('mousemove', onMove)
  document.addEventListener('mouseup', onUp)
}

function handleWatermarkWheel(event) {
  if (props.mode !== 'watermark') return
  const zoomIn = event.deltaY < 0

  if (watermarkValue.value.type === 'image') {
    const currentWidth = Number(watermarkValue.value.watermark_width || 0) || defaultOutputWatermarkWidth()
    const factor = zoomIn ? 1.08 : 0.92
    const nextWidth = Math.round(Math.max(16, currentWidth * factor))
    emit('update:watermark', {
      ...watermarkValue.value,
      watermark_width: nextWidth,
    })
    return
  }

  const currentSize = Number(watermarkValue.value.fontSize || 36)
  const step = event.shiftKey ? 1 : 4
  const nextSize = Math.round(Math.max(8, currentSize + (zoomIn ? step : -step)))
  emit('update:watermark', {
    ...watermarkValue.value,
    fontSize: nextSize,
  })
}

function emitCustomWatermark(x, y) {
  emit('update:watermark', {
    ...watermarkValue.value,
    position: 'custom',
    custom_x: Math.round(x * scaleX()),
    custom_y: Math.round(y * scaleY()),
  })
}

function defaultWatermarkPoint(position) {
  const frameWidth = displaySize.value.width || 0
  const frameHeight = displaySize.value.height || 0
  const marginX = 10 / scaleX()
  const marginY = 10 / scaleY()
  const estimatedWidth = watermarkDisplaySize.value.width
  const estimatedHeight = watermarkDisplaySize.value.height
  const points = {
    'top-left': { x: marginX, y: marginY },
    'top-right': { x: frameWidth - estimatedWidth - marginX, y: marginY },
    'bottom-left': { x: marginX, y: frameHeight - estimatedHeight - marginY },
    'bottom-right': { x: frameWidth - estimatedWidth - marginX, y: frameHeight - estimatedHeight - marginY },
    center: { x: (frameWidth - estimatedWidth) / 2, y: (frameHeight - estimatedHeight) / 2 },
  }
  const point = points[position] || points['bottom-right']
  return {
    x: clamp(point.x, 0, Math.max(0, frameWidth - estimatedWidth)),
    y: clamp(point.y, 0, Math.max(0, frameHeight - estimatedHeight)),
  }
}

function clamp(value, min, max) {
  return Math.max(min, Math.min(max, value))
}
</script>

<style scoped>
.overlay-editor {
  margin-top: 18px;
  border: 1px solid var(--border-default);
  border-radius: 8px;
  background: var(--bg-card);
  padding: 14px;
}
.overlay-header {
  display: flex;
  justify-content: space-between;
  gap: 12px;
  align-items: flex-start;
  margin-bottom: 12px;
}
.overlay-kicker {
  color: var(--accent-cyan);
  font-size: 10px;
  font-weight: 700;
  letter-spacing: .16em;
  margin: 0 0 4px;
}
.overlay-header h3 {
  color: var(--text-primary);
  font-size: 16px;
  margin: 0;
}
.overlay-hint {
  color: var(--text-muted);
  font-size: 12px;
  text-align: right;
  line-height: 1.5;
}
.video-stage {
  position: relative;
  min-height: 220px;
  display: flex;
  align-items: center;
  justify-content: center;
  overflow: hidden;
  border-radius: 8px;
  background: #111111;
  border: 1px solid rgba(255,255,255,.06);
}
.stage-placeholder {
  min-width: 220px;
  color: var(--text-muted);
  font-size: 13px;
  padding: 44px 16px;
  text-align: center;
}
.stage-loading-bar {
  height: 6px;
  margin-top: 14px;
  border-radius: 8px;
  background: var(--accent-primary);
  background-size: 70px 100%, 100% 100%;
  overflow: hidden;
  position: relative;
}
.stage-loading-bar::before {
  content: '';
  position: absolute;
  inset: 0;
  width: 45%;
  border-radius: inherit;
  background: var(--accent-primary);
  animation: indeterminate-progress 1.1s ease-in-out infinite;
}
.video-frame {
  position: relative;
  width: 100%;
  max-height: 420px;
  aspect-ratio: 16 / 9;
  background: #000;
  overflow: hidden;
}
.preview-cover {
  width: 100%;
  height: 100%;
  object-fit: contain;
  display: block;
  user-select: none;
  pointer-events: none;
}
.watermark-layer,
.redact-layer {
  position: absolute;
  inset: 0;
  overflow: hidden;
}
.watermark-layer {
  pointer-events: auto;
}
.watermark-preview {
  position: absolute;
  z-index: 2;
  cursor: move;
  pointer-events: auto;
  outline: 1px dashed var(--accent-cyan);
  border-radius: 6px;
  transform-origin: center center;
  text-shadow: 0 2px 8px rgba(0,0,0,.65);
  user-select: none;
  touch-action: none;
}
.watermark-image {
  display: block;
  width: 100%;
  height: auto;
  pointer-events: none;
}
.watermark-text {
  display: block;
  white-space: nowrap;
  font-weight: 700;
  line-height: 1.2;
  pointer-events: none;
}
.redact-layer {
  cursor: crosshair;
}
.redact-box {
  position: absolute;
  border: 2px solid var(--red);
  background: rgba(128, 128, 128, .2);
  cursor: move;
  box-sizing: border-box;
  touch-action: none;
}
.redact-box.drawing {
  border-style: dashed;
  border-color: var(--accent-cyan);
  background: rgba(128, 128, 128, .18);
  pointer-events: none;
}
.redact-label {
  position: absolute;
  left: -2px;
  top: -24px;
  padding: 2px 7px;
  border-radius: 5px;
  color: white;
  background: rgba(0,0,0,.68);
  font-size: 11px;
  white-space: nowrap;
}
.resize-handle {
  position: absolute;
  right: -6px;
  bottom: -6px;
  width: 12px;
  height: 12px;
  border-radius: 3px;
  border: 2px solid var(--accent-cyan);
  background: white;
  cursor: se-resize;
}
.coordinate-tip {
  color: var(--text-muted);
  font-size: 12px;
  margin: 10px 0 0;
}
@media (max-width: 640px) {
  .overlay-header {
    flex-direction: column;
  }
  .overlay-hint {
    text-align: left;
  }
}
@keyframes indeterminate-progress {
  0% { transform: translateX(-120%); }
  55%, 100% { transform: translateX(240%); }
}
</style>
