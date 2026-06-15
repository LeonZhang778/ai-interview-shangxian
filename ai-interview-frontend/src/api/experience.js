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

export function getFilterOptions() {
  return api.get('/experiences/filters')
}
