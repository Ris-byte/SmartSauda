import { defineConfig } from '@playwright/test'
import { resolve } from 'node:path'

process.env.PLAYWRIGHT_BROWSERS_PATH ||= resolve('../.playwright-browsers')
export default defineConfig({
  testDir: './tests', fullyParallel: false, workers: 1, retries: 0,
  timeout: 90000, expect: { timeout: 15000 },
  reporter: [['list'], ['json', { outputFile: `test-results/release/${process.env.RELEASE_REPORT || 'browser-results.json'}` }]],
  use: { baseURL: 'http://127.0.0.1:8001', viewport: { width: 1440, height: 1000 }, screenshot: 'only-on-failure', trace: 'retain-on-failure' },
  projects: [
    { name: 'edge', use: { browserName: 'chromium', channel: 'msedge', baseURL: 'http://127.0.0.1:8001' } },
    { name: 'firefox', use: { browserName: 'firefox', baseURL: 'http://127.0.0.1:8002' } },
    { name: 'webkit', use: { browserName: 'webkit', baseURL: 'http://127.0.0.1:8003' } },
  ],
  webServer: [8001, 8002, 8003].map(port => ({ command: '"../.venv/Scripts/python.exe" ../scripts/frontend_test_server.py',
    url: `http://127.0.0.1:${port}/api/v1/health/ready`, timeout: 120000, reuseExistingServer: false,
    env: { TEST_SERVE_BUILD: '1', TEST_PORT: String(port) } })),
})
