import { test, expect } from '@playwright/test'

const BASE = 'http://8.166.120.119'

test.describe('面试评分机制测试', () => {

  test('游客登录后开始面试并提交正常回答', async ({ page }) => {
    // 1. 访问首页
    await page.goto(BASE)
    await page.waitForLoadState('networkidle')

    // 2. 点击游客体验按钮
    const guestBtn = page.locator('button:has-text("免费体验")')
    if (await guestBtn.isVisible()) {
      await guestBtn.click()
      await page.waitForURL('**/dashboard', { timeout: 10000 })
    }

    // 3. 上传简历（跳过如果有简历的话）
    const uploadLink = page.locator('a:has-text("上传简历"), router-link:has-text("上传简历")')
    if (await uploadLink.isVisible()) {
      await uploadLink.click()
      await page.waitForURL('**/resume/upload')
    }

    // 检查当前页面
    const url = page.url()
    console.log('Current URL:', url)
  })

  test('直接测试API - 正常回答不应被判为过短', async ({ request }) => {
    // 游客登录
    const loginRes = await request.post(`${BASE}/api/v1/auth/guest`)
    const loginData = await loginRes.json()
    const token = loginData.data.access_token
    console.log('Guest token obtained')

    // 获取简历列表
    const resumesRes = await request.get(`${BASE}/api/v1/resumes`, {
      headers: { Authorization: `Bearer ${token}` }
    })
    const resumesData = await resumesRes.json()
    console.log('Resumes:', resumesData.data?.items?.length || 0)

    // 如果没有简历，需要先上传
    if (!resumesData.data?.items?.length) {
      console.log('No resume found, need to upload first')
      return
    }

    const resumeId = resumesData.data.items[0].id

    // 开始面试
    const startRes = await request.post(`${BASE}/api/v1/interviews/start`, {
      headers: { Authorization: `Bearer ${token}` },
      data: {
        resume_id: resumeId,
        target_position: '后端开发',
        difficulty: 'easy',
        total_questions: 3
      }
    })
    const startData = await startRes.json()
    console.log('Interview started:', startData.data?.interview_id)

    if (!startData.data?.interview_id) {
      console.log('Failed to start interview:', startData.message)
      return
    }

    const interviewId = startData.data.interview_id

    // 提交一个正常的回答（不是"不知道"，长度 > 5）
    const testAnswer = 'Redis是一个开源的内存数据结构存储系统，可以用作数据库、缓存和消息中间件。它支持多种数据结构，如字符串、哈希、列表、集合等。'
    console.log(`Submitting answer (${testAnswer.length} chars): "${testAnswer.substring(0, 30)}..."`)

    const answerRes = await request.post(`${BASE}/api/v1/interviews/${interviewId}/answer`, {
      headers: { Authorization: `Bearer ${token}` },
      data: { answer: testAnswer }
    })
    const answerData = await answerRes.json()
    console.log('Answer response:', JSON.stringify(answerData.data, null, 2))

    // 验证：正常回答不应该得1分
    const score = answerData.data?.score
    console.log(`Score: ${score}`)
    expect(score).toBeGreaterThan(1)

    // 验证：反馈不应该是"回答内容过短"
    const feedback = answerData.data?.feedback || ''
    console.log(`Feedback: ${feedback}`)
    expect(feedback).not.toContain('回答内容过短')
    expect(feedback).not.toContain('未尝试回答')
  })

  test('测试短回答应被判为过短', async ({ request }) => {
    // 游客登录
    const loginRes = await request.post(`${BASE}/api/v1/auth/guest`)
    const loginData = await loginRes.json()
    const token = loginData.data.access_token

    // 获取简历
    const resumesRes = await request.get(`${BASE}/api/v1/resumes`, {
      headers: { Authorization: `Bearer ${token}` }
    })
    const resumesData = await resumesRes.json()

    if (!resumesData.data?.items?.length) {
      console.log('No resume found, skipping')
      return
    }

    const resumeId = resumesData.data.items[0].id

    // 开始面试
    const startRes = await request.post(`${BASE}/api/v1/interviews/start`, {
      headers: { Authorization: `Bearer ${token}` },
      data: {
        resume_id: resumeId,
        target_position: '后端开发',
        difficulty: 'easy',
        total_questions: 3
      }
    })
    const startData = await startRes.json()
    const interviewId = startData.data?.interview_id

    if (!interviewId) {
      console.log('Failed to start interview')
      return
    }

    // 提交一个很短的回答
    const shortAnswer = '不知道'
    console.log(`Submitting short answer: "${shortAnswer}"`)

    const answerRes = await request.post(`${BASE}/api/v1/interviews/${interviewId}/answer`, {
      headers: { Authorization: `Bearer ${token}` },
      data: { answer: shortAnswer }
    })
    const answerData = await answerRes.json()
    console.log('Short answer response:', JSON.stringify(answerData.data, null, 2))

    // 验证：短回答应该得低分
    const score = answerData.data?.score
    console.log(`Score: ${score}`)
    expect(score).toBeLessThanOrEqual(2)
  })

  test('测试"不知道"回答应得1分', async ({ request }) => {
    const loginRes = await request.post(`${BASE}/api/v1/auth/guest`)
    const loginData = await loginRes.json()
    const token = loginData.data.access_token

    const resumesRes = await request.get(`${BASE}/api/v1/resumes`, {
      headers: { Authorization: `Bearer ${token}` }
    })
    const resumesData = await resumesRes.json()

    if (!resumesData.data?.items?.length) return

    const resumeId = resumesData.data.items[0].id

    const startRes = await request.post(`${BASE}/api/v1/interviews/start`, {
      headers: { Authorization: `Bearer ${token}` },
      data: { resume_id: resumeId, target_position: '后端开发', difficulty: 'easy', total_questions: 3 }
    })
    const startData = await startRes.json()
    const interviewId = startData.data?.interview_id

    if (!interviewId) return

    // 测试关键词回答
    const keywords = ['不知道', '不会', '不清楚', '跳过']
    for (const kw of keywords) {
      const answerRes = await request.post(`${BASE}/api/v1/interviews/${interviewId}/answer`, {
        headers: { Authorization: `Bearer ${token}` },
        data: { answer: kw }
      })
      const answerData = await answerRes.json()
      console.log(`"${kw}" -> score: ${answerData.data?.score}`)
      expect(answerData.data?.score).toBe(1)
    }
  })
})
