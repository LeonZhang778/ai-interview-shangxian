import api from './request'
import axios from 'axios'
import { useAuthStore } from '../stores/auth'

// ==================== 学习笔记 ====================

// 导出单个笔记为 Markdown
export async function exportNote(id) {
  const authStore = useAuthStore()
  const res = await axios.get(`/api/v1/learning-notes/${id}/export`, {
    responseType: 'blob',
    headers: { Authorization: `Bearer ${authStore.token}` }
  })
  triggerDownload(res, `${id}.md`)
  return true
}

// 导出整个笔记本（含子笔记本）为 ZIP
export async function exportNotebook(notebookId) {
  const authStore = useAuthStore()
  const res = await axios.get(`/api/v1/learning-notes/export/notebook/${notebookId}`, {
    responseType: 'blob',
    headers: { Authorization: `Bearer ${authStore.token}` }
  })
  triggerDownload(res, `notebook_${notebookId}.zip`)
  return true
}

// 导出全部笔记为 ZIP
export async function exportAllNotes() {
  const authStore = useAuthStore()
  const res = await axios.get('/api/v1/learning-notes/export/all', {
    responseType: 'blob',
    headers: { Authorization: `Bearer ${authStore.token}` }
  })
  triggerDownload(res, 'all_notes.zip')
  return true
}

// 通用下载触发：从 Content-Disposition 提取文件名，回退用 fallback
function triggerDownload(res, fallbackName) {
  const cd = res.headers['content-disposition'] || ''
  let filename = fallbackName
  const m = cd.match(/filename="?([^"]+)"?/i)
  if (m && m[1]) filename = decodeURIComponent(m[1])
  const url = window.URL.createObjectURL(res.data)
  const a = document.createElement('a')
  a.href = url
  a.download = filename
  document.body.appendChild(a)
  a.click()
  document.body.removeChild(a)
  window.URL.revokeObjectURL(url)
}

// 获取我的笔记列表
export function getMyNotes(params) {
  return api.get('/learning-notes/my', { params })
}

// 获取公开笔记广场
export function getPublicNotes(params) {
  return api.get('/learning-notes/public', { params })
}

// 获取公开笔记的热门标签（供广场下拉筛选）
export function getPublicTags() {
  return api.get('/learning-notes/public/tags')
}

// 获取笔记详情
export function getNoteDetail(id) {
  return api.get(`/learning-notes/${id}`)
}

// 创建笔记
export function createNote(data) {
  return api.post('/learning-notes', data)
}

// 更新笔记
export function updateNote(id, data) {
  return api.put(`/learning-notes/${id}`, data)
}

// 删除笔记
export function deleteNote(id) {
  return api.delete(`/learning-notes/${id}`)
}

// 从 AI 面试结果生成学习笔记草稿
export function generateFromInterview(data) {
  return api.post('/learning-notes/from-interview', data)
}

// 生成或获取笔记的 AI 摘要（含三级要点）
export function generateSummary(id, force = false) {
  return api.post(`/learning-notes/${id}/summary`, null, { params: { force } })
}

// 获取笔记统计
export function getNoteStats(params) {
  return api.get('/learning-notes/stats', { params })
}

// 搜索笔记（全文搜索）
export function searchNotes(params) {
  return api.get('/learning-notes/search', { params })
}

// 上传笔记图片
export function uploadNoteImage(file) {
  const formData = new FormData()
  formData.append('file', file)
  return api.post('/learning-notes/upload-image', formData, {
    headers: { 'Content-Type': 'multipart/form-data' },
  })
}

// ==================== 笔记本 ====================

// 获取笔记本树
export function getNotebooks() {
  return api.get('/notebooks')
}

// 创建笔记本
export function createNotebook(data) {
  return api.post('/notebooks', data)
}

// 更新笔记本
export function updateNotebook(id, data) {
  return api.put(`/notebooks/${id}`, data)
}

// 删除笔记本
export function deleteNotebook(id) {
  return api.delete(`/notebooks/${id}`)
}
