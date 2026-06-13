import api from './request'

export function submitWaitingList(data) {
  return api.post('/waiting-list/submit', data)
}

export function verifyWaitingListEmail(token) {
  return api.get('/waiting-list/verify', { params: { token } })
}

export function resendWaitingListVerification(email) {
  return api.post('/waiting-list/resend-verification', { email })
}
