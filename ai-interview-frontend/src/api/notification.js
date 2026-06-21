import api from './request'

export function getNotifications(params) {
  return api.get('/notifications', { params })
}

export function getUnreadCount() {
  return api.get('/notifications/unread-count')
}

export function markRead(notificationId) {
  return api.put(`/notifications/${notificationId}/read`)
}

export function markAllRead() {
  return api.put('/notifications/read-all')
}

export function deleteNotification(notificationId) {
  return api.delete(`/notifications/${notificationId}`)
}
