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

    <nav class="tool-switcher" aria-label="工具选择">
      <router-link
        v-for="tool in tools"
        :key="tool.code"
        :to="tool.path"
        :class="['tool-chip', { active: $route.path === tool.path }]"
      >
        <span class="tool-chip-icon" :style="{ background: tool.color }">{{ tool.icon }}</span>
        <span class="tool-chip-body">
          <strong>{{ tool.name }}</strong>
          <small>{{ tool.description }}</small>
        </span>
      </router-link>
    </nav>

<main class="workspace-card">
      <router-view />
    </main>

    <!-- 文件管理面板 -->
    <div class="files-section">
      <MediaFilesPanel />
    </div>

    <MediaToast />
  </div>
</template>

<script setup>
import { useRoute } from 'vue-router'
import { useMediaStore } from '../stores/media'
import MediaToast from '../components/media/MediaToast.vue'
import MediaFilesPanel from '../components/media/MediaFilesPanel.vue'

const store = useMediaStore()
const route = useRoute()

const tools = [
  { code: 'convert', path: '/media-tools/convert', name: '格式转换', icon: '↗', color: '#A3A3A3', description: '转换视频或音频格式' },
  { code: 'compress', path: '/media-tools/compress', name: '视频压缩', icon: '▤', color: '#A3A3A3', description: '减小体积，保持清晰度' },
  { code: 'trim', path: '/media-tools/trim', name: '视频截取', icon: '⌁', color: '#A3A3A3', description: '截取需要的时间片段' },
  { code: 'extract_audio', path: '/media-tools/extract-audio', name: '提取音频', icon: '♫', color: '#A3A3A3', description: '从视频中提取音频' },
  { code: 'audio_convert', path: '/media-tools/audio-convert', name: '音频转换', icon: '◖', color: '#A3A3A3', description: '转换音频编码和格式' },
  { code: 'gif', path: '/media-tools/gif', name: '视频转GIF', icon: '✦', color: '#A3A3A3', description: '截取视频片段生成 GIF' },
  { code: 'merge', path: '/media-tools/merge', name: '视频合并', icon: '⊕', color: '#A3A3A3', description: '按顺序合并多个视频' },
  { code: 'watermark', path: '/media-tools/watermark', name: '添加水印', icon: '◇', color: '#A3A3A3', description: '给视频添加图片或文字水印' },
  { code: 'redact', path: '/media-tools/redact', name: '区域遮挡', icon: '⊡', color: '#A3A3A3', description: '模糊或遮挡视频中的敏感区域' },
]

store.loadCapabilities()
store.loadTasks()
store.startPolling()
store.bindVisibility()
</script>

<style scoped>
.media-page { max-width: 1180px; margin: 0 auto; padding: 46px 24px 72px; }
.media-header { display: flex; justify-content: space-between; gap: 24px; align-items: flex-start; margin-bottom: 30px; }
.eyebrow { color: var(--accent-cyan); font-size: 11px; font-weight: 700; letter-spacing: .16em; margin-bottom: 10px; }
.media-header h1 { color: var(--text-primary); font-size: 40px; letter-spacing: 0; line-height: 1.1; }
.lead { max-width: 640px; margin-top: 14px; color: var(--text-secondary); line-height: 1.7; }
.back-link { white-space: nowrap; color: var(--text-secondary); border: 1px solid var(--border-default); border-radius: 8px; padding: 9px 15px; font-size: 13px; text-decoration: none; transition: color .2s, border-color .2s; }
.back-link:hover { color: var(--text-primary); border-color: var(--border-hover); }
.tool-switcher { display: flex; flex-wrap: wrap; gap: 10px; margin-bottom: 24px; }
.tool-chip { display: flex; align-items: center; gap: 10px; padding: 12px 16px; min-height: 52px; border-radius: 8px; background: var(--bg-card); border: 1px solid var(--border-default); text-decoration: none; color: var(--text-primary); transition: border-color .2s, background .2s, box-shadow .2s; cursor: pointer; flex: 1 1 180px; max-width: 240px; }
.tool-chip:hover { border-color: var(--border-hover); background: var(--bg-hover); }
.tool-chip.active { border-color: var(--accent-primary); background: var(--bg-hover); box-shadow: var(--shadow-sm); }
.tool-chip-icon { display: grid; place-items: center; width: 32px; height: 32px; flex: 0 0 32px; border-radius: 8px; color: white; font-size: 16px; }
.tool-chip-body { display: grid; gap: 2px; min-width: 0; }
.tool-chip-body strong { font-size: 13px; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.tool-chip-body small { color: var(--text-muted); font-size: 10px; line-height: 1.3; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.workspace-card { padding: 28px; background: var(--bg-card); border: 1px solid var(--border-default); border-radius: 8px; box-shadow: var(--shadow-sm); }
.files-section { margin-top: 24px; padding: 24px; background: var(--bg-card); border: 1px solid var(--border-default); border-radius: 8px; box-shadow: var(--shadow-sm); }
@media (max-width: 900px) { .tool-chip { flex: 1 1 140px; max-width: none; } }
@media (max-width: 600px) { .media-page { padding: 30px 16px 52px; } .media-header { display: block; } .back-link { display: inline-block; margin-top: 18px; } .tool-switcher { gap: 8px; } .tool-chip { flex: 1 1 calc(50% - 8px); padding: 10px 12px; min-height: 44px; } .workspace-card { padding: 18px; border-radius: 8px; } }
@media (max-width: 600px) { .media-header h1 { font-size: 30px; } }
</style>
