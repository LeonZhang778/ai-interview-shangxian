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
export function getNoteStats() {
  return api.get('/learning-notes/stats')
}
