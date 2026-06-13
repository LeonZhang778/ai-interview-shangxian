import api from './request'

export function getTemporaryCredentials() {
  return api.get('/aws/temporary-credentials')
}
