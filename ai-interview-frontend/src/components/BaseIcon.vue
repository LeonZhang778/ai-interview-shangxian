<script setup>
import { computed } from 'vue'

/**
 * BaseIcon —— AI-Interview 统一图标组件（建议方案，2026-10-10）
 *
 * 用法：
 *   <BaseIcon name="eye" :size="14" />
 *   <BaseIcon name="star-fill" :size="16" style="color: var(--state-warning)" />
 *
 * 设计规格：24×24 viewBox / stroke=currentColor / stroke-width=1.8 / 圆角线帽
 * 颜色：跟随当前文字色（语义色用 style 覆盖），深浅主题自动适配
 * 对齐：`vertical-align: -0.125em` 使其与中文基线对齐，可放心内联在文字中
 *
 * 覆盖对照见同目录《图标清单.md》与《图标.png》；替换映射见《图标替换映射.md》
 */
const props = defineProps({
  name: { type: String, required: true },
  size: { type: [Number, String], default: 16 },
  strokeWidth: { type: [Number, String], default: 1.8 },
  /** 填充模式（star-fill / heart-fill 已内置，也可强制） */
  filled: { type: Boolean, default: false },
})

const ICONS = {
  /* ============ 通用界面 ============ */
  x: '<path d="M18 6 6 18M6 6l12 12"/>',
  check: '<path d="m20 6-11 11-5-5"/>',
  'check-circle': '<circle cx="12" cy="12" r="9"/><path d="m8.5 12.5 2.5 2.5 5-5.5"/>',
  'x-circle': '<circle cx="12" cy="12" r="9"/><path d="m9 9 6 6M15 9l-6 6"/>',
  info: '<circle cx="12" cy="12" r="9"/><path d="M12 11v5M12 8v.5"/>',
  'alert-triangle': '<path d="M10.3 4.2 2.8 17.5A2 2 0 0 0 4.5 20.5h15a2 2 0 0 0 1.7-3L13.7 4.2a2 2 0 0 0-3.4 0z"/><path d="M12 9v4M12 16.5v.5"/>',
  'chevron-left': '<path d="m15 18-6-6 6-6"/>',
  'chevron-right': '<path d="m9 18 6-6-6-6"/>',
  'chevron-down': '<path d="m6 9 6 6 6-6"/>',
  'arrow-right': '<path d="M5 12h14"/><path d="m12 5 7 7-7 7"/>',
  'arrow-up': '<path d="M12 19V5"/><path d="m5 12 7-7 7 7"/>',
  'arrow-down': '<path d="M12 5v14"/><path d="m19 12-7 7-7-7"/>',

  /* ============ 内容与数据 ============ */
  list: '<path d="M8 6h13M8 12h13M8 18h13"/><path d="M3 6h.01M3 12h.01M3 18h.01"/>',
  clipboard: '<rect x="8" y="2" width="8" height="4" rx="1"/><path d="M16 4h2a2 2 0 0 1 2 2v14a2 2 0 0 1-2 2H6a2 2 0 0 1-2-2V6a2 2 0 0 1 2-2h2"/>',
  notebook: '<rect x="5" y="3" width="14" height="18" rx="2"/><path d="M9 3v18"/><path d="M13 7h3M13 11h3"/>',
  'book-open': '<path d="M2 4h6a4 4 0 0 1 4 4v13a3 3 0 0 0-3-3H2z"/><path d="M22 4h-6a4 4 0 0 0-4 4v13a3 3 0 0 1 3-3h7z"/>',
  file: '<path d="M14 3H7a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h10a2 2 0 0 0 2-2V8z"/><path d="M14 3v5h5"/>',
  'file-text': '<path d="M14 3H7a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h10a2 2 0 0 0 2-2V8z"/><path d="M14 3v5h5"/><path d="M9 13h6M9 17h4"/>',
  newspaper: '<path d="M4 5a2 2 0 0 1 2-2h12a2 2 0 0 1 2 2v14a2 2 0 0 1-2 2H6a2 2 0 0 1-2-2z"/><path d="M8 7h8M8 11h8M8 15h4"/>',
  target: '<circle cx="12" cy="12" r="9"/><circle cx="12" cy="12" r="5"/><circle cx="12" cy="12" r="1.2" fill="currentColor" stroke="none"/>',
  chart: '<path d="M4 20V10M10 20V4M16 20v-6M2 20h20"/>',
  'trending-up': '<path d="m3 17 6-6 4 4 8-8"/><path d="M17 7h4v4"/>',
  star: '<path d="m12 3 2.9 5.6 6.1.9-4.4 4.3 1 6.1L12 17l-5.6 3 1-6.1L3 9.5l6.1-.9z"/>',
  'star-fill': '<path d="m12 3 2.9 5.6 6.1.9-4.4 4.3 1 6.1L12 17l-5.6 3 1-6.1L3 9.5l6.1-.9z" fill="currentColor"/>',
  heart: '<path d="M12 21C7 16.6 3.5 13 3.5 9.2 3.5 6.4 5.7 4.5 8 4.5c1.6 0 3.1.8 4 2.2.9-1.4 2.4-2.2 4-2.2 2.3 0 4.5 1.9 4.5 4.7 0 3.8-3.5 7.4-8.5 11.8z"/>',
  'heart-fill': '<path d="M12 21C7 16.6 3.5 13 3.5 9.2 3.5 6.4 5.7 4.5 8 4.5c1.6 0 3.1.8 4 2.2.9-1.4 2.4-2.2 4-2.2 2.3 0 4.5 1.9 4.5 4.7 0 3.8-3.5 7.4-8.5 11.8z" fill="currentColor"/>',
  eye: '<path d="M2 12s3.5-6 10-6 10 6 10 6-3.5 6-10 6-10-6-10-6z"/><circle cx="12" cy="12" r="2.6"/>',
  'eye-off': '<path d="M3 3l18 18"/><path d="M10.6 5.1A9.8 9.8 0 0 1 12 5c6.5 0 10 6 10 6a17 17 0 0 1-2.5 3.2M6.6 6.6A16 16 0 0 0 2 11s3.5 6 10 6a9.6 9.6 0 0 0 4.4-1"/>',
  'thumbs-up': '<path d="M7 10v11H4a1 1 0 0 1-1-1v-9a1 1 0 0 1 1-1h3z"/><path d="M7 10l4.2-6.8a2 2 0 0 1 3.5 1.9L13.6 10H19a2 2 0 0 1 2 2.3l-1 6A2 2 0 0 1 18 20H7"/>',
  message: '<path d="M21 11.5a8.5 8.5 0 0 1-8.5 8.5c-1.5 0-2.9-.36-4.1-1L3 20l1-5.4A8.5 8.5 0 1 1 21 11.5z"/>',
  'message-square': '<path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z"/>',
  bell: '<path d="M18 8a6 6 0 1 0-12 0c0 7-3 9-3 9h18s-3-2-3-9"/><path d="M13.7 21a2 2 0 0 1-3.4 0"/>',
  pin: '<path d="M12 17v5"/><path d="M9 10.5V5h6v5.5c0 .8.3 1.5.9 2.1l1.1 1.1H7l1.1-1.1c.6-.6.9-1.3.9-2.1z"/>',
  inbox: '<path d="M22 12h-6l-2 3h-4l-2-3H2"/><path d="M5.5 5.1 2 12v6a2 2 0 0 0 2 2h16a2 2 0 0 0 2-2v-6l-3.5-6.9A2 2 0 0 0 16.7 4H7.3a2 2 0 0 0-1.8 1.1z"/>',

  /* ============ 用户与权限 ============ */
  user: '<circle cx="12" cy="8" r="4"/><path d="M4 21c0-4 3.6-6 8-6s8 2 8 6"/>',
  users: '<circle cx="9" cy="8" r="3.5"/><path d="M2.5 20c0-3.4 3-5.5 6.5-5.5s6.5 2.1 6.5 5.5"/><circle cx="17" cy="9" r="2.6"/><path d="M16.5 14.6c2.9.2 5 2 5 5"/>',
  lock: '<rect x="5" y="11" width="14" height="10" rx="2"/><path d="M8 11V7a4 4 0 0 1 8 0v4"/>',
  globe: '<circle cx="12" cy="12" r="9"/><path d="M3 12h18"/><path d="M12 3c2.5 2.5 4 5.6 4 9s-1.5 6.5-4 9c-2.5-2.5-4-5.6-4-9s1.5-6.5 4-9z"/>',
  shield: '<path d="M12 3l8 3v6c0 5-3.5 8-8 9-4.5-1-8-4-8-9V6z"/>',
  ban: '<circle cx="12" cy="12" r="9"/><path d="M5.6 5.6l12.8 12.8"/>',

  /* ============ 操作 ============ */
  pencil: '<path d="M17 3l4 4L8 20l-5 1 1-5z"/>',
  trash: '<path d="M3 6h18M8 6V4a1 1 0 0 1 1-1h6a1 1 0 0 1 1 1v2M19 6l-1 14a2 2 0 0 1-2 2H8a2 2 0 0 1-2-2L5 6"/><path d="M10 11v6M14 11v6"/>',
  upload: '<path d="M4 17v3h16v-3"/><path d="M12 3v12"/><path d="m7 8 5-5 5 5"/>',
  download: '<path d="M4 17v3h16v-3"/><path d="M12 3v12"/><path d="m7 10 5 5 5-5"/>',
  search: '<circle cx="11" cy="11" r="7"/><path d="m21 21-4-4"/>',
  'user-search': '<circle cx="10" cy="9" r="3.5"/><path d="M3 20c0-3.2 2.8-5.2 6-5.2 1 0 2 .2 2.8.6"/><circle cx="17" cy="17" r="3"/><path d="m22 22-2.2-2.2"/>',
  loader: '<path d="M12 3v3M12 18v3M3 12h3M18 12h3M5.6 5.6l2.1 2.1M16.3 16.3l2.1 2.1M5.6 18.4l2.1-2.1M16.3 7.7l2.1-2.1"/>',
  refresh: '<path d="M21 12a9 9 0 0 0-15-6.7L3 8"/><path d="M3 3v5h5"/><path d="M3 12a9 9 0 0 0 15 6.7L21 16"/><path d="M21 21v-5h-5"/>',
  settings: '<path d="M4 7h16M4 12h16M4 17h16"/><circle cx="15" cy="7" r="2"/><circle cx="9" cy="12" r="2"/><circle cx="14" cy="17" r="2"/>',
  history: '<path d="M3 12a9 9 0 1 0 3-6.7L3 8"/><path d="M3 3v5h5"/><path d="M12 8v4l3 2"/>',
  'list-check': '<path d="M3 6h13M3 12h13M3 18h8"/><path d="m15 16 2 2 4-4"/>',
  dashboard: '<rect x="3" y="3" width="7" height="7" rx="1.5"/><rect x="14" y="3" width="7" height="7" rx="1.5"/><rect x="3" y="14" width="7" height="7" rx="1.5"/><rect x="14" y="14" width="7" height="7" rx="1.5"/>',

  /* ============ 通信与其他 ============ */
  link: '<path d="M10.6 13.4a4 4 0 0 0 5.7 0l2.8-2.8a4 4 0 0 0-5.7-5.7l-1.7 1.7"/><path d="M13.4 10.6a4 4 0 0 0-5.7 0l-2.8 2.8a4 4 0 0 0 5.7 5.7l1.7-1.7"/>',
  share: '<path d="M8 6H5a2 2 0 0 0-2 2v10a2 2 0 0 0 2 2h10a2 2 0 0 0 2-2v-3"/><path d="M13 3h8v8"/><path d="M21 3 11 13"/>',
  mail: '<rect x="3" y="5" width="18" height="14" rx="2"/><path d="m3 7 9 6 9-6"/>',
  camera: '<path d="M4 8h3l1.5-2h7L17 8h3a1 1 0 0 1 1 1v10a1 1 0 0 1-1 1H4a1 1 0 0 1-1-1V9a1 1 0 0 1 1-1z"/><circle cx="12" cy="13" r="3.4"/>',
  paperclip: '<path d="M21.4 11.05 12.25 20.2a6 6 0 0 1-8.49-8.49l8.57-8.57A4 4 0 1 1 18 8.84l-8.59 8.57a2 2 0 0 1-2.83-2.83l8.49-8.48"/>',
  bug: '<path d="M9 7a3 3 0 0 1 6 0v8a3 3 0 0 1-6 0z"/><path d="M12 4V2.5"/><path d="M9 9H5M9 13H4.5M9 17l-2.5 2.5M15 9h4M15 13h4.5M15 17l2.5 2.5"/>',
  snake: '<path d="M3.2 19.6c0-2.7 2.2-4.9 4.9-4.9h7.8c2.7 0 4.9-2.2 4.9-4.9S18.6 4.9 15.9 4.9h-4.2"/><circle cx="9.4" cy="4.9" r="2.4"/><path d="M9.9 4.5h.01"/><path d="M7 4.9H5.2M5.2 4.9 3.9 3.9M5.2 4.9 3.9 5.9"/>',
  lightbulb: '<path d="M9 18h6M10 21h4"/><path d="M12 3a6 6 0 0 1 4 10.6c-.7.6-1 1.5-1 2.4v1H9v-1c0-.9-.3-1.8-1-2.4A6 6 0 0 1 12 3z"/>',
  flame: '<path d="M12 3c2.2 2.6 4.5 5.2 4.5 8.6a4.5 4.5 0 0 1-9 0c0-1 .3-2 .8-2.9.5.9 1.2 1.5 2 1.7-.3-2.7.2-5.3 1.7-7.4z"/>',
  sparkles: '<path d="M12 3l1.9 4.6L18.5 9.5l-4.6 1.9L12 16l-1.9-4.6L5.5 9.5l4.6-1.9z"/><path d="M19 15l.9 2.1L22 18l-2.1.9L19 21l-.9-2.1L16 18l2.1-.9z"/>',
  repeat: '<path d="m17 2 4 4-4 4"/><path d="M3 11V9a4 4 0 0 1 4-4h14"/><path d="m7 22-4-4 4-4"/><path d="M21 13v2a4 4 0 0 1-4 4H3"/>',
  sun: '<circle cx="12" cy="12" r="4"/><path d="M12 2v2M12 20v2M2 12h2M20 12h2M4.9 4.9l1.4 1.4M17.7 17.7l1.4 1.4M4.9 19.1l1.4-1.4M17.7 6.3l1.4-1.4"/>',
  moon: '<path d="M21 12.8A9 9 0 1 1 11.2 3a7 7 0 0 0 9.8 9.8z"/>',

  /* ============ 媒体工具箱 ============ */
  convert: '<path d="M21 12a9 9 0 0 0-15-6.7L3 8"/><path d="M3 3v5h5"/><path d="M3 12a9 9 0 0 0 15 6.7L21 16"/><path d="M21 21v-5h-5"/>',
  compress: '<path d="M15 3h6v6"/><path d="M9 21H3v-6"/><path d="M21 3l-7 7"/><path d="M3 21l7-7"/>',
  scissors: '<circle cx="6" cy="6" r="3"/><circle cx="6" cy="18" r="3"/><path d="M20 4 8.5 15.5M14.5 8.5 20 14M8.5 8.5 12 12"/>',
  music: '<path d="M9 18V5l10-2v13"/><circle cx="6.5" cy="18" r="2.5"/><circle cx="16.5" cy="16" r="2.5"/>',
  volume: '<path d="M11 5 6 9H2v6h4l5 4z"/><path d="M15.5 8.5a5 5 0 0 1 0 7"/><path d="M18.5 5.5a9 9 0 0 1 0 13"/>',
  image: '<rect x="3" y="3" width="18" height="18" rx="2"/><circle cx="9" cy="9" r="2"/><path d="m21 15-4-4L5 21"/>',
  video: '<rect x="3" y="5" width="18" height="14" rx="2"/><path d="m10 9.5 5 2.5-5 2.5z"/><path d="M8 21h8"/>',
  film: '<rect x="3" y="4" width="18" height="16" rx="2"/><path d="M7 4v16M17 4v16M3 9h4M3 15h4M17 9h4M17 15h4"/>',
  merge: '<path d="M3 5h6l6 7h9"/><path d="M3 19h6l6-7"/><path d="M18 9l3 3-3 3"/>',
  droplet: '<path d="M12 3.5s6 6.2 6 10.5a6 6 0 0 1-12 0c0-4.3 6-10.5 6-10.5z"/>',
  redact: '<rect x="3" y="5" width="18" height="14" rx="2"/><path d="M7 9h10M7 13h6"/><path d="m14 17 5 5"/>',
  megaphone: '<path d="m3 11 18-5v12L3 14v-3z"/><path d="M11.6 16.8a3 3 0 1 1-5.8-1.6"/>',
}

const inner = computed(() => ICONS[props.name] || ICONS['info'])
</script>

<template>
  <svg
    class="base-icon"
    :width="size"
    :height="size"
    viewBox="0 0 24 24"
    fill="none"
    stroke="currentColor"
    :stroke-width="strokeWidth"
    stroke-linecap="round"
    stroke-linejoin="round"
    :class="{ 'base-icon--filled': filled }"
    aria-hidden="true"
    focusable="false"
  >
    <g v-html="inner" />
  </svg>
</template>

<style scoped>
.base-icon {
  display: inline-block;
  flex: none;
  vertical-align: -0.125em;
}
.base-icon--filled {
  fill: currentColor;
}
</style>
