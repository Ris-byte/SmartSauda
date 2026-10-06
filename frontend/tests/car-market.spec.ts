import { test, expect } from '@playwright/test'

test('unvalidated cars fail closed in the form and direct API', async ({ page }) => {
  const response = await page.request.post('/api/v1/auth/login', {
    data: { email: 'viewer@example.com', password: 'Browser-test-only-2026!' },
  })
  const token = (await response.json()).data.csrf_token
  await page.goto('/predict?type=Car')
  await expect(page.getByText('Insufficient verified market data', { exact: true })).toBeVisible()
  await expect(page.getByRole('button', { name: 'Get my estimate' })).toBeDisabled()
  const result = await page.request.post('/api/v1/predictions', {
    data: { vehicle_type: 'Car', brand: 'Toyota', model: 'Fortuner', manufacture_year: 2011, km_driven: 130000 },
    headers: { 'X-CSRF-Token': token },
  })
  expect(result.status()).toBe(422)
  expect((await result.json()).error.code).toBe('insufficient_verified_market_data')
  await page.screenshot({ path: 'test-results/car-market-unavailable.png', fullPage: true })
  await page.route('**/api/v1/market-status?*', route => route.fulfill({ status: 503, json: { error: { message: 'Unavailable' } } }))
  await page.reload()
  await expect(page.getByText('Insufficient verified market data', { exact: true })).toBeVisible()
  await expect(page.getByRole('button', { name: 'Get my estimate' })).toBeDisabled()
})
