import api from './request'

export function generateImage(data) {
  return api.post('/images/generate', data)
}

export function getImageTasks(params) {
  return api.get('/images/tasks', { params })
}

export function getImageTask(id) {
  return api.get(`/images/tasks/${id}`)
}

export function deleteImageTask(id) {
  return api.delete(`/images/tasks/${id}`)
}
