import api from './request'

export function getAnnouncements(params) {
  return api.get('/announcements', { params })
}

export function getLatestAnnouncement() {
  return api.get('/announcements/latest')
}

export function getAnnouncementDetail(id) {
  return api.get(`/announcements/${id}`)
}
