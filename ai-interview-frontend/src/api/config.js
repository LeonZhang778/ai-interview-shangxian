import api from './request'

export function getSiteInfo() {
  return api.get('/config/site-info')
}
