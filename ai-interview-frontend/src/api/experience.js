import api from './request'

export function getExperiences(params) {
  return api.get('/experiences', { params })
}

export function getExperienceDetail(id) {
  return api.get(`/experiences/${id}`)
}

export function likeExperience(id) {
  return api.post(`/experiences/${id}/like`)
}

export function collectExperience(id) {
  return api.post(`/experiences/${id}/collect`)
}

export function getInteractionStatus(id) {
  return api.get(`/experiences/${id}/interaction-status`)
}

export function getComments(experienceId, params) {
  return api.get(`/experiences/${experienceId}/comments`, { params })
}

export function createComment(experienceId, data) {
  return api.post(`/experiences/${experienceId}/comments`, data)
}

export function deleteComment(commentId) {
  return api.delete(`/experiences/comments/${commentId}`)
}

export function getFilterOptions() {
  return api.get('/experiences/filters')
}

export function submitExperience(data) {
  return api.post('/experiences/submit', data)
}

export function getMyExperiences(params) {
  return api.get('/experiences/my/submissions', { params })
}

// ==================== 收藏夹分组 ====================

export function getMyCollections(params) {
  return api.get('/experiences/collections/my', { params })
}

export function getCollectionGroups() {
  return api.get('/experiences/collections/groups')
}

export function createCollectionGroup(name) {
  return api.post('/experiences/collections/groups', { name })
}

export function updateCollectionGroup(groupId, data) {
  return api.put(`/experiences/collections/groups/${groupId}`, data)
}

export function deleteCollectionGroup(groupId) {
  return api.delete(`/experiences/collections/groups/${groupId}`)
}

export function moveCollection(experienceId, groupId) {
  return api.put(`/experiences/collections/${experienceId}/move`, { group_id: groupId })
}
