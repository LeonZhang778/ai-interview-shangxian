import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import {
  getCapabilities,
  uploadMediaFile,
  createConvertTask,
  createGifTask,
  createMergeTask,
  createWatermarkTask,
  createRedactTask,
  getMediaTask,
  cancelMediaTask,
  deleteMediaTask,
  deleteMediaTasks,
  retryMediaTask,
  retryMediaTasks,
  getMediaTaskDownload,
  listMediaTasks
} from '../api/mediaTool'

// ─── 错误码映射（按后端真实语义：code → 中文提示） ───
const ERROR_MAP = {
  10400: '媒体工具暂未开放',
  10401: '参数有误或该格式不支持',
  10402: '文件超过大小限制，请压缩后再试',
  10403: '文件无法识别，请确认文件未损坏',
  10404: '文件不存在或无权访问',
  10405: '任务不存在或无权访问',
  10406: '相同任务正在处理，请稍后',
  10408: '该功能暂未开放',
  42901: '操作过于频繁，请稍后再试',
}

function mapError(error) {
  if (!error) return '操作失败，请稍后重试'
  if (error.code && ERROR_MAP[error.code]) return ERROR_MAP[error.code]
  if (error.message) return error.message
  return '操作失败，请稍后重试'
}

export const useMediaStore = defineStore('media', () => {
  // ─── 能力配置 ───
  const capabilities = ref({})
  const capabilitiesLoading = ref(false)

  // ─── 文件状态 ───
  const files = ref([])           // 当前工具选定的文件列表（单文件时长度为 1）
  const uploading = ref(false)
  const uploadProgress = ref(0)
  const errorMessage = ref('')
  const filesError = ref('')      // 文件列表加载失败信息（空 = 无错误）

  // ─── 任务状态 ───
  const tasks = ref([])
  const tasksLoading = ref(false)
  const tasksError = ref('')      // 任务列表加载失败信息（空 = 无错误）
  let pollTimer = null
  let polling = false
  let pollRounds = 0
  let pollFailStreak = 0
  const pollTimedOut = ref(false) // 轮询达到上限后置 true，等待用户刷新

  // ─── Toast 消息队列 ───
  const toasts = ref([])
  let toastId = 0

  // ─── 计算属性 ───
  const selectedFile = computed(() => files.value.length === 1 ? files.value[0] : null)
  const hasFiles = computed(() => files.value.length > 0)
  const activeTasks = computed(() => tasks.value.filter(t => ['queued', 'pending', 'processing'].includes(t.status)))

  // ─── Toast ───
  function addToast(message, type = 'success', duration = 3000) {
    const id = ++toastId
    toasts.value.push({ id, message, type })
    if (duration > 0) {
      setTimeout(() => {
        const idx = toasts.value.findIndex(t => t.id === id)
        if (idx >= 0) toasts.value.splice(idx, 1)
      }, duration)
    }
    return id
  }

  function removeToast(id) {
    const idx = toasts.value.findIndex(t => t.id === id)
    if (idx >= 0) toasts.value.splice(idx, 1)
  }

  // ─── 能力加载 ───
  async function loadCapabilities() {
    capabilitiesLoading.value = true
    try {
      capabilities.value = await getCapabilities()
    } catch {
      capabilities.value = {}
    } finally {
      capabilitiesLoading.value = false
    }
  }

  // ─── 文件上传 ───
  async function uploadFile(file) {
    errorMessage.value = ''
    uploading.value = true
    uploadProgress.value = 0
    try {
      const result = await uploadMediaFile(file, progress => {
        uploadProgress.value = progress
      })
      return result
    } catch (error) {
      const msg = mapError(error)
      errorMessage.value = msg
      addToast(msg, 'error')
      throw error
    } finally {
      uploading.value = false
    }
  }

  function setFiles(newFiles) {
    files.value = newFiles
  }

  function addFile(file) {
    files.value.push(file)
  }

  function removeFile(fileId) {
    const idx = files.value.findIndex(f => f.id === fileId)
    if (idx >= 0) files.value.splice(idx, 1)
  }

  function clearFiles() {
    files.value = []
    errorMessage.value = ''
  }

  function reorderFiles(fromIndex, toIndex) {
    if (fromIndex < 0 || fromIndex >= files.value.length) return
    if (toIndex < 0 || toIndex >= files.value.length) return
    const tmp = files.value[fromIndex]
    files.value[fromIndex] = files.value[toIndex]
    files.value[toIndex] = tmp
  }

  // ─── 任务提交 ───
  async function submitTask(payload, toolCode) {
    errorMessage.value = ''
    const resolvedToolCode = toolCode || payload?.tool_code || 'convert'
    try {
      if (resolvedToolCode === 'merge') {
        await createMergeTask(payload)
      } else if (resolvedToolCode === 'watermark') {
        await createWatermarkTask(payload)
      } else if (resolvedToolCode === 'redact') {
        await createRedactTask(payload)
      } else if (resolvedToolCode === 'gif') {
        await createGifTask(payload)
      } else {
        await createConvertTask(payload)
      }
      addToast('任务已提交，正在处理中', 'success')
      await loadTasks()
      clearFiles()
    } catch (error) {
      const msg = mapError(error)
      errorMessage.value = msg
      addToast(msg, 'error')
      throw error
    }
  }

  // ─── 任务查询 ───
  async function loadTasks() {
    tasksLoading.value = true
    try {
      const data = await listMediaTasks({ page: 1, size: 12 })
      tasks.value = data.items || []
      tasksError.value = ''
      // 手动刷新会清掉"轮询超时"标记并恢复轮询
      clearPollTimeout()
      if (activeTasks.value.length) {
        startPolling()
      }
    } catch (error) {
      tasksError.value = mapError(error)
    } finally {
      tasksLoading.value = false
    }
  }

  async function refreshTask(taskId) {
    try {
      const updated = await getMediaTask(taskId)
      const index = tasks.value.findIndex(t => t.id === taskId)
      if (index >= 0) {
        tasks.value[index] = { ...tasks.value[index], ...updated }
      }
      return updated
    } catch {
      return null
    }
  }

  async function cancelTask(taskId) {
    if (!window.confirm('取消后已处理的进度会丢失。确定取消？')) return
    try {
      await cancelMediaTask(taskId)
      const task = tasks.value.find(t => t.id === taskId)
      if (task) task.status = 'cancelled'
      addToast('任务已取消', 'success')
    } catch (error) {
      addToast(mapError(error), 'error')
    }
  }

async function retryTask(taskId) {
    try {
      const result = await retryMediaTask(taskId)
      const task = tasks.value.find(t => t.id === taskId)
      if (task) {
        task.status = result.status || 'queued'
        task.progress = 0
        task.error_message = ''
      }
      addToast('任务已重新提交', 'success')
    } catch (error) {
      addToast(mapError(error), 'error')
    }
  }

  async function retryMultipleTasks(taskIds) {
    try {
      const result = await retryMediaTasks(taskIds)
      const succeeded = result.succeeded || []
      const failed = result.failed || []
      // 更新本地状态
      succeeded.forEach(id => {
        const task = tasks.value.find(t => t.id === id)
        if (task) {
          task.status = 'pending'
          task.progress = 0
          task.error_message = ''
        }
      })
      if (failed.length === 0) {
        addToast(`已重新提交 ${succeeded.length} 个任务`, 'success')
      } else {
        addToast(`成功 ${succeeded.length} 个，失败 ${failed.length} 个`, 'warning')
      }
    } catch (error) {
      addToast(mapError(error), 'error')
    }
  }

  async function deleteTask(taskId) {
    if (!window.confirm('删除后该任务记录不可恢复，已生成的结果文件将无法再下载。确定删除？')) return
    try {
      await deleteMediaTask(taskId)
      tasks.value = tasks.value.filter(t => t.id !== taskId)
      addToast('任务已删除', 'success')
    } catch (error) {
      addToast(mapError(error), 'error')
    }
  }

  async function deleteAllCompleted() {
    const deletable = tasks.value.filter(t => !['queued', 'pending', 'processing'].includes(t.status))
    if (!deletable.length) {
      addToast('没有可删除的任务', 'info')
      return
    }
    if (!window.confirm('将清空全部已完成任务记录（不影响已下载文件）。确定？')) return
    try {
      await deleteMediaTasks(deletable.map(t => t.id))
      const ids = new Set(deletable.map(t => t.id))
      tasks.value = tasks.value.filter(t => !ids.has(t.id))
      addToast(`已清空 ${deletable.length} 条任务记录`, 'success')
    } catch (error) {
      addToast(mapError(error), 'error')
    }
  }

  // ─── 下载 ───
  async function downloadTask(taskId) {
    try {
      const result = await getMediaTaskDownload(taskId)
      const url = result.download_url.startsWith('http')
        ? result.download_url
        : `${window.location.origin}${result.download_url}`
      const response = await fetch(url, {
        headers: { Authorization: `Bearer ${localStorage.getItem('token') || ''}` }
      })
      if (!response.ok) throw new Error('下载失败')
      const blobUrl = URL.createObjectURL(await response.blob())
      const anchor = document.createElement('a')
      anchor.href = blobUrl
      anchor.download = result.file_name || 'media-result'
      document.body.appendChild(anchor)
      anchor.click()
      anchor.remove()
      URL.revokeObjectURL(blobUrl)
      addToast('下载已开始', 'success')
    } catch (error) {
      addToast(error.message || '下载失败，请重试', 'error')
    }
  }

  // ─── 轮询 ───
  // 最多轮询 150 次（2s 间隔约 5 分钟），连续失败 3 次后退避到 5s
  const POLL_INTERVAL_MS = 2000
  const POLL_INTERVAL_BACKOFF_MS = 5000
  const POLL_MAX_ROUNDS = 150
  const POLL_FAIL_BACKOFF_THRESHOLD = 3

  function isActiveStatus(status) {
    return ['queued', 'pending', 'processing'].includes(status)
  }

  function clearPollTimeout() {
    pollTimedOut.value = false
    tasks.value.forEach(t => {
      if (t.poll_timeout) t.poll_timeout = false
    })
  }

  function markPollTimeout() {
    pollTimedOut.value = true
    tasks.value.forEach(t => {
      if (isActiveStatus(t.status)) t.poll_timeout = true
    })
  }

  function currentPollDelay() {
    return pollFailStreak >= POLL_FAIL_BACKOFF_THRESHOLD
      ? POLL_INTERVAL_BACKOFF_MS
      : POLL_INTERVAL_MS
  }

  function startPolling() {
    if (polling) return
    polling = true
    pollRounds = 0
    pollFailStreak = 0
    bindVisibility()
    schedulePoll(POLL_INTERVAL_MS)
  }

  function schedulePoll(delay) {
    pollTimer = window.setTimeout(runPollRound, delay)
  }

  async function runPollRound() {
    pollTimer = null
    if (!polling) return
    // 页面隐藏时不发请求，保持调度
    if (document.hidden) {
      schedulePoll(currentPollDelay())
      return
    }
    const active = [...activeTasks.value]
    if (!active.length) {
      stopPolling()
      return
    }
    pollRounds++
    if (pollRounds > POLL_MAX_ROUNDS) {
      markPollTimeout()
      addToast('轮询超时，请刷新重试', 'warning')
      stopPolling()
      return
    }
    const results = await Promise.all(active.map(task => refreshTask(task.id)))
    // 等待期间被停止（如离开页面）则不再续期
    if (!polling) return
    const failedCount = results.filter(r => !r).length
    pollFailStreak = failedCount > 0 ? pollFailStreak + 1 : 0
    // 任务进入 completed/failed/cancelled 立即停止，不等下一轮
    if (!activeTasks.value.length) {
      stopPolling()
      return
    }
    schedulePoll(currentPollDelay())
  }

  function stopPolling() {
    polling = false
    if (pollTimer) {
      window.clearTimeout(pollTimer)
      pollTimer = null
    }
    pollRounds = 0
    pollFailStreak = 0
    unbindVisibility()
  }

  // ─── 可见性变化监听 ───
  let visibilityHandler = null

  function bindVisibility() {
    if (visibilityHandler) return
    visibilityHandler = () => {
      if (!document.hidden && activeTasks.value.length) {
        // 回到页面时立即刷新一次
        activeTasks.value.forEach(task => refreshTask(task.id))
      }
    }
    document.addEventListener('visibilitychange', visibilityHandler)
  }

  function unbindVisibility() {
    if (visibilityHandler) {
      document.removeEventListener('visibilitychange', visibilityHandler)
      visibilityHandler = null
    }
  }

  // ─── 格式工具 ───
  function formatBytes(bytes) {
    if (!bytes) return '0 B'
    const units = ['B', 'KB', 'MB', 'GB']
    const index = Math.min(Math.floor(Math.log(bytes) / Math.log(1024)), units.length - 1)
    return `${(bytes / (1024 ** index)).toFixed(index ? 1 : 0)} ${units[index]}`
  }

  function formatDuration(milliseconds) {
    if (!milliseconds) return '00:00'
    const seconds = Math.round(milliseconds / 1000)
    const minutes = Math.floor(seconds / 60)
    return `${String(minutes).padStart(2, '0')}:${String(seconds % 60).padStart(2, '0')}`
  }

  function formatDate(value) {
    if (!value) return ''
    return new Date(value).toLocaleString('zh-CN', {
      month: '2-digit', day: '2-digit', hour: '2-digit', minute: '2-digit'
    })
  }

  function statusLabel(status) {
    const map = {
      queued: '排队中',
      pending: '排队中',
      processing: '处理中',
      completed: '已完成',
      failed: '失败',
      cancelled: '已取消'
    }
    return map[status] || status
  }

  function toolName(code) {
    const names = {
      convert: '格式转换',
      compress: '视频压缩',
      trim: '视频截取',
      extract_audio: '提取音频',
      audio_convert: '音频转换',
      gif: '视频转GIF',
      merge: '视频合并',
      watermark: '添加水印',
      redact: '区域遮挡',
    }
    return names[code] || code || '媒体任务'
  }

  return {
    // 状态
    capabilities, capabilitiesLoading,
    files, uploading, uploadProgress, errorMessage, filesError,
    tasks, tasksLoading, tasksError, pollTimedOut,
    toasts,
    // 计算
    selectedFile, hasFiles, activeTasks,
// 动作
    addToast, removeToast,
    loadCapabilities,
    uploadFile, setFiles, addFile, removeFile, clearFiles, reorderFiles,
    submitTask, loadTasks, refreshTask,
    cancelTask, retryTask, retryMultipleTasks, deleteTask, deleteAllCompleted,
    downloadTask,
    startPolling, stopPolling, bindVisibility, unbindVisibility,
    // 工具
    formatBytes, formatDuration, formatDate, statusLabel, toolName,
    mapError,
  }
})