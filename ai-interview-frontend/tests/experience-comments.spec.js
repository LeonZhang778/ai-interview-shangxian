import { test, expect } from '@playwright/test'

test('删除刚发布且没有 replies 字段的评论不会报错', async ({ page }) => {
  await page.addInitScript(() => {
    localStorage.setItem('token', 'test-token')
    localStorage.setItem('userId', '7')
    localStorage.setItem('userName', '测试用户')
  })

  await page.route('**/api/v1/experiences/30', async route => {
    await route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify({
        code: 200,
        data: {
          id: 30,
          title: '测试面经',
          company: '测试公司',
          position: '后端开发',
          author_name: '作者',
          created_at: '2026-10-05',
          view_count: 1,
          like_count: 0,
          collect_count: 0,
          tags: [],
          content: '测试内容',
          level: '',
          round: ''
        }
      })
    })
  })

  await page.route('**/api/v1/experiences/30/comments*', async route => {
    if (route.request().method() === 'GET') {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          code: 200,
          data: {
            items: [{
              id: 2,
              content: '已有评论',
              user: { id: 7, first_name: '测试用户', avatar: '' },
              parent_id: null,
              like_count: 0,
              created_at: '2026-10-04T00:00:00'
            }],
            total: 1,
            page: 1,
            per_page: 20
          }
        })
      })
      return
    }

    await route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify({
        code: 200,
        data: {
          id: 1,
          content: '刚发布的评论',
          user: { id: 7, first_name: '测试用户', avatar: '' },
          parent_id: null,
          like_count: 0,
          created_at: '2026-10-05T00:00:00'
        }
      })
    })
  })

  await page.route('**/api/v1/experiences/30/interaction-status', async route => {
    await route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify({ code: 200, data: { liked: false, collected: false } })
    })
  })

  await page.route('**/api/v1/experiences/comments/1', async route => {
    await route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify({ code: 200, message: '评论已删除', data: null })
    })
  })

  await page.goto('/experiences/30')
  await expect(page.getByText('测试面经')).toBeVisible()
  await expect(page.getByText('已有评论')).toBeVisible()

  await page.locator('textarea[placeholder="写下你的评论..."]').fill('刚发布的评论')
  await page.getByRole('button', { name: '发表评论' }).click()
  await expect(page.getByText('刚发布的评论')).toBeVisible()

  const dialogs = []
  page.on('dialog', async dialog => {
    dialogs.push(dialog.message())
    await dialog.accept()
  })
  await page.getByRole('button', { name: '删除' }).first().click()
  await expect(page.getByText('刚发布的评论')).not.toBeVisible()
  expect(dialogs).toEqual(['确定删除这条评论？'])
})
