import { defineConfig } from '@playwright/test'

export default defineConfig({
  testDir: './tests', fullyParallel: false, workers: 1, retries: 0,
  timeout: 60000, expect: { timeout: 10000 },
  reporter: [['list'], ['json', { outputFile: 'test-results/browser-results.json' }]],
  use: { baseURL: 'http://127.0.0.1:5174', channel: 'msedge', viewport: { width: 1440, height: 1000 }, screenshot: 'only-on-failure', trace: 'retain-on-failure' },
  webServer: [
    { command: '"../.venv/Scripts/python.exe" ../scripts/frontend_test_server.py', url: 'http://127.0.0.1:8001/api/v1/health/ready', timeout: 120000, reuseExistingServer: false },
    { command: 'npm run dev -- --port 5174', url: 'http://127.0.0.1:5174', env: { API_PROXY_TARGET: 'http://127.0.0.1:8001' }, timeout: 30000, reuseExistingServer: false },
  ],
})
