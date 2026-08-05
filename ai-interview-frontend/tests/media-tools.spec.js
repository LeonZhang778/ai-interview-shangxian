import { test, expect } from '@playwright/test'

const BASE = process.env.E2E_BASE_URL || 'http://127.0.0.1:8000'

async function guestToken(request) {
  const response = await request.post(`${BASE}/api/v1/auth/guest`)
  expect(response.ok()).toBeTruthy()
  const body = await response.json()
  return body.data.access_token
}

test.describe('媒体工具 GIF、合并和水印 API', () => {
  test('GIF 非法片段被拒绝且不会创建任务', async ({ request }) => {
    const token = await guestToken(request)
    const response = await request.post(`${BASE}/api/v1/media-tools/tasks/gif`, {
      headers: { Authorization: `Bearer ${token}` },
      data: { file_id: 999999, start_time: 5, duration: 0 }
    })
    expect(response.status()).toBe(400)
    const body = await response.json()
    expect(body.message).toContain('GIF 片段时长')
  })

  test('视频合并少于两个文件被拒绝', async ({ request }) => {
    const token = await guestToken(request)
    const response = await request.post(`${BASE}/api/v1/media-tools/tasks/merge`, {
      headers: { Authorization: `Bearer ${token}` },
      data: { file_ids: [999999], target_format: 'mp4' }
    })
    expect(response.status()).toBe(400)
    const body = await response.json()
    expect(body.message).toContain('至少需要 2 个')
  })

  test('水印缺少图片文件被拒绝', async ({ request }) => {
    const token = await guestToken(request)
    const response = await request.post(`${BASE}/api/v1/media-tools/tasks/watermark`, {
      headers: { Authorization: `Bearer ${token}` },
      data: { file_id: 999999, position: 'bottom-right', opacity: 1 }
    })
    expect(response.status()).toBe(400)
    const body = await response.json()
    expect(body.message).toContain('watermark_file_id')
  })
})
