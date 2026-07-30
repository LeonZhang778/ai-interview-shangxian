import api from './request'

// ==================== 学习笔记 ====================

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
