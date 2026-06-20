import api from './request'

export const authApi = {
  login: (email, password) => api.post('/auth/login', { email, password }),
  me: () => api.get('/auth/me'),
  refresh: (refreshToken) => api.post('/auth/refresh', { refresh_token: refreshToken }),
  logout: (refreshToken) => api.post('/auth/logout', { refresh_token: refreshToken })
}

export const userApi = {
  list: (params) => api.get('/users', { params }),
  stats: () => api.get('/users/stats'),
  toggleActive: (id) => api.put(`/users/${id}/toggle-active`)
}

export const interviewApi = {
  list: (params) => api.get('/interviews', { params }),
  detail: (id) => api.get(`/interviews/${id}`),
  delete: (id) => api.delete(`/interviews/${id}`)
}

export const adminApi = {
  list: (params) => api.get('/admins', { params }),
  detail: (id) => api.get(`/admins/${id}`),
  create: (data) => api.post('/admins', data),
  update: (id, data) => api.put(`/admins/${id}`, data),
  delete: (id) => api.delete(`/admins/${id}`),
  changePassword: (id, data) => api.post(`/admins/${id}/change-password`, data),
  resetPassword: (id, data) => api.post(`/admins/${id}/reset-password`, data)
}

export const waitingListApi = {
  list: (params) => api.get('/waiting-list', { params })
}

export const announcementApi = {
  list: (params) => api.get('/announcements', { params }),
  create: (data) => api.post('/announcements', null, { params: data }),
  update: (id, data) => api.put(`/announcements/${id}`, null, { params: data }),
  delete: (id) => api.delete(`/announcements/${id}`),
  togglePin: (id) => api.put(`/announcements/${id}/pin`),
  toggleStatus: (id, isActive) => api.put(`/announcements/${id}/status`, null, { params: { is_active: isActive } })
}

export const settingsApi = {
  list: () => api.get('/settings'),
  batchUpdate: (data) => api.put('/settings', data),
  updateSingle: (key, data) => api.put(`/settings/${key}`, data)
}

export const feedbackApi = {
  list: (params) => api.get('/feedbacks', { params }),
  stats: () => api.get('/feedbacks/stats'),
  updateStatus: (id, status) => api.put(`/feedbacks/${id}/status`, null, { params: { status } }),
  reply: (id, adminReply) => api.put(`/feedbacks/${id}/reply`, null, { params: { admin_reply: adminReply } })
}

export const auditLogApi = {
  list: (params) => api.get('/audit-logs', { params }),
  export: (params) => api.get('/audit-logs/export', { params, responseType: 'blob' })
}

export const analyticsApi = {
  overview: () => api.get('/analytics/overview'),
  userTrend: (days) => api.get('/analytics/user-trend', { params: { days } }),
  interviewTrend: (days) => api.get('/analytics/interview-trend', { params: { days } }),
  experienceRanking: () => api.get('/analytics/experience-ranking'),
  activeUsers: () => api.get('/analytics/active-users')
}
