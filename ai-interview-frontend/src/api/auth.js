import api from './request'

export function register(data) {
  return api.post('/auth/register', data)
}

export function guestLogin() {
  return api.post('/auth/guest')
}

export function login(email, password) {
  return api.post('/auth/login', { email, password })
}

export function sendVerificationCode(email, codeType = 'registration') {
  return api.post('/auth/send-verification-code', { email, code_type: codeType })
}

export function verifyEmail(email, code) {
  return api.post('/auth/verify-email', { email, code })
}

export function refreshToken(refreshTokenValue) {
  return api.post('/auth/refresh', { refresh_token: refreshTokenValue })
}

export function logoutApi(refreshTokenValue) {
  return api.post('/auth/logout', { refresh_token: refreshTokenValue })
}

export function sendPasswordResetCode(email) {
  return api.post('/auth/password-reset/send-code', { email })
}

export function verifyPasswordResetCode(email, code) {
  return api.post('/auth/password-reset/verify-code', { email, code })
}

export function resetPassword(resetToken, newPassword, confirmPassword) {
  return api.post('/auth/password-reset/reset', { reset_token: resetToken, new_password: newPassword, confirm_password: confirmPassword })
}
