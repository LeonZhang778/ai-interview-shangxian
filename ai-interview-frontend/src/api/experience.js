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
