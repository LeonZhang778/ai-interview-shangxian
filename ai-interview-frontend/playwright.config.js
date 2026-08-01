import { defineConfig } from '@playwright/test'

const baseURL = process.env.E2E_BASE_URL || 'http://127.0.0.1:8000'

export default defineConfig({
  testDir: './tests',
  timeout: 30_000,
  use: {
    ignoreHTTPSErrors: true,
    baseURL,
    launchOptions: {
      executablePath: process.env.PLAYWRIGHT_CHROME_PATH || 'C:/Program Files/Google/Chrome/Application/chrome.exe'
    }
  }
})
