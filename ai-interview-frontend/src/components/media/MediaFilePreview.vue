<template>
  <div class="file-preview" :class="{ 'file-preview-empty': !file }">
    <!-- 空态 -->
    <div v-if="!file" class="preview-empty">
      <div class="empty-icon" aria-hidden="true">
        <svg width="40" height="40" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round">
          <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z" />
          <polyline points="14 2 14 8 20 8" />
        </svg>
      </div>
      <p class="empty-text">暂无文件</p>
    </div>

    <!-- 文件内容 -->
    <div v-else class="preview-content">
      <!-- 缩略图/图标 -->
      <div class="preview-thumb">
        <img
          v-if="previewUrl"
          :src="previewUrl"
          :alt="file.original_name || '预览'"
          class="thumb-image"
        />
        <div v-else class="thumb-icon" :class="`thumb-${file.media_type || 'unknown'}`">
          <!-- 视频图标 -->
          <svg v-if="file.media_type === 'video'" width="28" height="28" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round">
            <polygon points="23 7 16 12 23 17 23 7" />
            <rect x="1" y="5" width="15" height="14" rx="2" ry="2" />
          </svg>
          <!-- 音频图标 -->
          <svg v-else-if="file.media_type === 'audio'" width="28" height="28" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round">
            <path d="M9 18V5l12-2v13" />
            <circle cx="6" cy="18" r="3" />
            <circle cx="18" cy="16" r="3" />
          </svg>
          <!-- 通用文件图标 -->
          <svg v-else width="28" height="28" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round">
            <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z" />
            <polyline points="14 2 14 8 20 8" />
          </svg>
        </div>
      </div>

      <!-- 元数据 -->
      <div class="preview-meta">
        <p class="preview-name">{{ file.original_name || '未知文件' }}</p>
        <div class="preview-details">
          <span class="meta-tag">{{ store.formatBytes(file.size_bytes) }}</span>
          <span v-if="file.duration_ms" class="meta-tag">{{ store.formatDuration(file.duration_ms) }}</span>
          <span v-if="resolution" class="meta-tag">{{ resolution }}</span>
        </div>
      </div>

      <!-- 移除按钮 -->
      <button
        v-if="showRemove"
        class="preview-remove"
        type="button"
        :aria-label="'移除 ' + (file.original_name || '文件')"
        @click="handleRemove"
      >
        <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
          <line x1="18" y1="6" x2="6" y2="18" />
          <line x1="6" y1="6" x2="18" y2="18" />
        </svg>
      </button>
    </div>
  </div>
</template>

<script setup>
import { computed } from 'vue'
import { useMediaStore } from '../../stores/media'

const props = defineProps({
  file: { type: Object, default: null },
  showRemove: { type: Boolean, default: true },
  previewUrl: { type: String, default: '' }
})

const emit = defineEmits(['remove'])

const store = useMediaStore()

const resolution = computed(() => {
  if (!props.file) return ''
  const meta = props.file.metadata
  if (!meta) return ''
  // 优先 video 子字段
  if (meta.video && meta.video.width && meta.video.height) {
    return `${meta.video.width}×${meta.video.height}`
  }
  if (meta.width && meta.height) {
    return `${meta.width}×${meta.height}`
  }
  return ''
})

function handleRemove() {
  emit('remove', props.file.id)
}
</script>

<style scoped>
.file-preview {
  border: 1px solid var(--border-default);
  border-radius: 9px;
  padding: 9px 11px;
  background: var(--bg-card);
  display: flex;
  align-items: center;
  gap: 12px;
}
.file-preview-empty {
  justify-content: center;
  padding: 24px 20px;
}

/* 空态 */
.preview-empty {
  text-align: center;
}
.empty-icon {
  color: var(--text-muted);
  margin-bottom: 6px;
  display: flex;
  justify-content: center;
}
.empty-text {
  color: var(--text-muted);
  font-size: 13px;
  margin: 0;
}

/* 缩略图/图标 */
.preview-thumb {
  flex: 0 0 48px;
  width: 48px;
  height: 48px;
  border-radius: 8px;
  overflow: hidden;
  display: flex;
  align-items: center;
  justify-content: center;
}
.thumb-image {
  width: 100%;
  height: 100%;
  object-fit: cover;
}
.thumb-icon {
  width: 48px;
  height: 48px;
  display: grid;
  place-items: center;
  border-radius: 8px;
}
.thumb-video {
  background: var(--purple-bg);
  color: var(--accent-primary);
}
.thumb-audio {
  background: rgba(128, 128, 128, .15);
  color: var(--accent-cyan);
}
.thumb-unknown {
  background: var(--bg-hover);
  color: var(--text-muted);
}

/* 元数据 */
.preview-meta {
  flex: 1;
  min-width: 0;
}
.preview-name {
  color: var(--text-primary);
  font-size: 13px;
  font-weight: 600;
  margin: 0 0 4px;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}
.preview-details {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
}
.meta-tag {
  color: var(--text-muted);
  font-size: 11px;
  background: var(--bg-hover);
  padding: 2px 7px;
  border-radius: 4px;
  white-space: nowrap;
}

/* 移除按钮 */
.preview-remove {
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
.preview-remove:hover {
  background: var(--red-bg);
  color: var(--red);
}
</style>