import api from './request'
import { downloadBinary } from './download'

// ==================== 学习笔记 ====================

// 导出单个笔记为 Markdown
export async function exportNote(id) {
  return downloadBinary(`/api/v1/learning-notes/${id}/export`, `${id}.md`)
}

// 导出单个笔记为 Word
export async function exportNoteDocx(id) {
  return downloadBinary(`/api/v1/learning-notes/${id}/export-docx`, `${id}.docx`)
}

// 导出整个笔记本（含子笔记本）为 ZIP
export async function exportNotebook(notebookId) {
  return downloadBinary(`/api/v1/learning-notes/export/notebook/${notebookId}`, `notebook_${notebookId}.zip`)
}

// 导出整个笔记本（含子笔记本）为 Word ZIP
export async function exportNotebookDocx(notebookId) {
  return downloadBinary(`/api/v1/learning-notes/export-docx/notebook/${notebookId}`, `notebook_${notebookId}_docx.zip`)
}

// 导出全部笔记为 ZIP
export async function exportAllNotes() {
  return downloadBinary('/api/v1/learning-notes/export/all', 'all_notes.zip')
}

// 导出全部笔记为 Word ZIP
export async function exportAllNotesDocx() {
  return downloadBinary('/api/v1/learning-notes/export-docx/all', 'all_notes_docx.zip')
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

// 获取 AI 推荐的标签（不写入笔记，仅返回建议）
export function suggestTags(id, force = false) {
  return api.post(`/learning-notes/${id}/suggest-tags`, null, { params: { force } })
}

// 应用 AI 推荐的标签（用户确认后写入笔记）
export function applyTags(id, tags) {
  return api.post(`/learning-notes/${id}/apply-tags`, { tags })
}

// 点赞/取消点赞公开笔记
export function likeNote(id) {
  return api.post(`/learning-notes/${id}/like`)
}

// 收藏/取消收藏公开笔记
export function collectNote(id) {
  return api.post(`/learning-notes/${id}/collect`)
}

// 获取当前用户对公开笔记的互动状态
export function getNoteInteractionStatus(id) {
  return api.get(`/learning-notes/${id}/interaction-status`)
}

// 获取公开笔记评论
export function getNoteComments(id, params) {
  return api.get(`/learning-notes/${id}/comments`, { params })
}

// 创建公开笔记评论
export function createNoteComment(id, data) {
  return api.post(`/learning-notes/${id}/comments`, data)
}

// 删除自己的公开笔记评论
export function deleteNoteComment(commentId) {
  return api.delete(`/learning-notes/comments/${commentId}`)
}

// 获取相关笔记推荐
export function getRelatedNotes(id, limit = 5) {
  return api.get(`/learning-notes/${id}/related`, { params: { limit } })
}

// 基于面试报告关键词推荐我的相关笔记
export function recommendForInterview(keywords, limit = 5) {
  return api.post('/learning-notes/recommend/interview', { keywords, limit })
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

// ==================== 闪卡复习 ====================

export function getFlashcards(params) {
  return api.get('/flashcards', { params })
}

export function getDueCards(limit = 20) {
  return api.get('/flashcards/due', { params: { limit } })
}

export function reviewCard(cardId, quality) {
  return api.post(`/flashcards/${cardId}/review`, { quality })
}

export function getFlashcardStats() {
  return api.get('/flashcards/stats')
}

export function generateFlashcards(noteId) {
  return api.post(`/flashcards/generate/${noteId}`)
}

// ==================== 错题本仪表盘 ====================

export function getMistakeDashboard() {
  return api.get('/weakness/dashboard')
}

export function getWeaknessHeatmap(limit = 30) {
  return api.get('/weakness/heatmap', { params: { limit } })
}

export function getWeaknessRecommendations(limit = 5) {
  return api.get('/weakness/recommendations', { params: { limit } })
}

// ==================== 笔记模板 ====================

// 获取所有笔记模板列表
export function getTemplates() {
  return api.get('/note-templates/templates')
}

// 获取模板详情（含 Markdown 正文）
export function getTemplateDetail(id) {
  return api.get(`/note-templates/templates/${id}`)
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
