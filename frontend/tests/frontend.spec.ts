import { test, expect, type Page } from '@playwright/test'
import AxeBuilder from '@axe-core/playwright'
import { mkdir, readFile } from 'node:fs/promises'

const password = 'Browser-test-only-2026!'

test('prediction result has a responsive valuation card without a photo section', async ({ page }) => {
  const auth = await page.request.post('/api/v1/auth/login', { data: { email: 'viewer@example.com', password } })
  const token = (await auth.json()).data.csrf_token
  const created = await page.request.post('/api/v1/predictions', {
    data: JSON.parse(await readFile('../examples/predict-bike.json', 'utf8')),
    headers: { 'X-CSRF-Token': token },
  })
  expect(created.status()).toBe(201)
  const row = (await created.json()).data
  const photoRequests: string[] = []
  page.on('request', request => {
    if (request.url().endsWith('/photo') || request.url().includes('/assets/vehicles/')) photoRequests.push(request.url())
  })
  await page.goto(`/predictions/${row.id}`)
  await expect(page.getByRole('region', { name: 'Estimated resale value' })).toBeVisible()
  await expect(page.locator('.valuation-price')).toContainText('NPR')
  await expect(page.locator('.vehicle-photo,.result-image,.result-grid')).toHaveCount(0)
  await expect(page.getByRole('button', { name: 'Download PDF report' })).toBeVisible()
  for (const width of [1440, 768, 390, 320]) {
    await page.setViewportSize({ width, height: 950 })
    await fits(page)
    if (width === 1440 || width === 390) {
      await accessible(page)
      await capture(page, `result-no-photo-${width}`)
    }
  }
  expect(photoRequests).toEqual([])
})
const reportRoot = () => '../frontend/test-results/artifacts'
const shots = () => `${reportRoot()}/screenshots/${test.info().project.name || 'edge'}`
async function capture(page: Page, name: string) {
  await mkdir(shots(), { recursive: true })
  await page.evaluate(() => { window.scrollTo(0, 0); if (document.activeElement instanceof HTMLElement) document.activeElement.blur() })
  await page.screenshot({ path: `${shots()}/${name}.png`, fullPage: true })
}
async function accessible(page: Page) {
  await page.evaluate(async () => {
    await document.fonts.ready
    await Promise.all(document.getAnimations().filter(a => a.effect?.getTiming().iterations !== Infinity).map(a => a.finished.catch(() => {})))
  })
  const results = await new AxeBuilder({ page }).withTags(['wcag2a', 'wcag2aa', 'wcag21aa']).analyze()
  expect(results.violations.map(v => ({ id: v.id, nodes: v.nodes.map(n => ({ target: n.target, reason: n.failureSummary })) }))).toEqual([])
}
async function login(page: Page, email = 'viewer@example.com', pass = password) {
  await page.goto('/signin')
  await page.getByLabel('Email address').fill(email)
  await page.locator('input[name=password]').fill(pass)
  await page.getByRole('button', { name: 'Sign in', exact: true }).click()
  await expect(page).toHaveURL(/dashboard/)
}
async function fits(page: Page) {
  expect(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth)).toBe(true)
}
async function selectVehicle(page: Page, brand: string, model: string, year: string) {
  await page.getByRole('combobox', { name: 'Brand *', exact: true }).selectOption(brand)
  await page.getByRole('combobox', { name: 'Model *', exact: true }).selectOption(model)
  await page.locator('[name=manufacture_year]').selectOption(year)
}

test('public pages, responsive layout, keyboard navigation and accessibility', async ({ page }) => {
  for (const width of [1440, 768, 390, 320]) {
    await page.setViewportSize({ width, height: 950 })
    await page.goto('/')
    await expect(page.getByRole('heading', { level: 1 })).toContainText('KNOW YOUR')
    await page.locator('.hero-image').evaluate((img: HTMLImageElement) => img.decode())
    await fits(page)
    if (width === 1440 || width === 390) { await accessible(page); await capture(page, `home-${width}`) }
    if (width === 390) {
      await page.getByRole('button', { name: 'Open navigation' }).click()
      await expect(page.getByRole('navigation', { name: 'Main navigation' })).toBeVisible()
      await page.keyboard.press('Escape')
      await expect(page.getByRole('button', { name: 'Open navigation' })).toHaveAttribute('aria-expanded', 'false')
    }
  }
  await page.setViewportSize({ width: 1440, height: 1000 })
  await page.goto('/about')
  await expect(page.getByText('3,316 retained records', { exact: true })).toBeVisible()
  await accessible(page); await capture(page, 'about-desktop')
  await page.goto('/signup'); await accessible(page); await capture(page, 'signup-desktop')
  await page.goto('/does-not-exist'); await expect(page.getByRole('heading', { level: 1 })).toBeVisible()
})

test('register, supported estimates, car safety block, PDF, history and profile', async ({ page }) => {
  test.setTimeout(120000)
  const errors: string[] = []; page.on('pageerror', error => errors.push(error.message))
  const email = `browser-${Date.now()}@example.com`
  await page.goto('/predict?type=Bike')
  await expect(page).toHaveURL(/signin\?next=/)
  await page.getByRole('link', { name: 'Create an account' }).click()
  await page.getByLabel('Your name').fill('Browser Rider')
  await page.getByLabel('Email address').fill(email)
  await page.locator('input[name=password]').fill(password)
  await page.getByRole('button', { name: 'Create my account' }).click()
  await expect(page.getByRole('status')).toContainText('Your account is ready')
  await page.getByLabel('Email address').fill(email)
  await page.locator('input[name=password]').fill(password)
  await page.getByRole('button', { name: 'Sign in', exact: true }).click()
  await expect(page).toHaveURL(/predict\?type=Bike/)
  await expect(page.getByRole('combobox', { name: 'Brand *', exact: true })).toBeEnabled()
  await page.getByRole('combobox', { name: 'Brand *', exact: true }).selectOption('Bajaj')
  await expect(page.getByRole('combobox', { name: 'Model *', exact: true })).toBeEnabled()
  await page.getByRole('combobox', { name: 'Model *', exact: true }).selectOption('Pulsar 150')
  await page.locator('[name=manufacture_year]').selectOption('2020')
  await page.locator('[name=km_driven]').fill('30000')
  await page.locator('[name=engine_capacity_cc]').fill('149')
  await accessible(page); await capture(page, 'prediction-desktop')
  await page.getByRole('button', { name: 'Get my estimate' }).click()
  await expect(page).toHaveURL(/\/predictions\/[a-f0-9-]+/)
  const savedUrl = page.url()
  await expect(page.locator('.valuation-price')).toContainText('NPR')
  const originalPrice = await page.locator('.valuation-price').innerText()
  await expect(page.locator('.limitations')).toContainText('unverified provenance')
  await accessible(page); await capture(page, 'result-desktop')
  const download = page.waitForEvent('download')
  await page.getByRole('button', { name: /Download PDF/ }).click()
  const pdf = await download
  expect(pdf.suggestedFilename()).toMatch(/smartsauda-.*\.pdf/)
  await pdf.saveAs(`${reportRoot()}/browser-bike-report-${test.info().project.name || 'edge'}.pdf`)
  await page.reload(); await expect(page.locator('.valuation-price')).toHaveText(originalPrice)
  for (const type of ['Car', 'Scooter']) {
    await page.goto(`/predict?type=${type}`)
    await selectVehicle(page, type === 'Car' ? 'Maruti Suzuki' : 'Honda', type === 'Car' ? 'Swift' : 'Dio', '2020')
    await page.locator('[name=km_driven]').fill('30000')
    if (type === 'Car') {
      await expect(page.getByText('Insufficient verified market data', { exact: true })).toBeVisible()
      await expect(page.getByRole('button', { name: 'Get my estimate' })).toBeDisabled()
      continue
    }
    await page.getByRole('button', { name: 'Get my estimate' }).click()
    await expect(page.locator('.valuation-price')).toContainText('NPR')
  }
  await page.goto('/dashboard'); await expect(page.locator('.stat-card').first()).toContainText('2')
  await accessible(page); await capture(page, 'dashboard-desktop')
  await page.goto('/history'); await expect(page.getByText('2 results', { exact: true })).toBeVisible()
  await page.getByLabel('Search vehicles').fill('Pulsar'); await page.getByRole('button', { name: 'Apply filters' }).click()
  await expect(page.getByText('1 result', { exact: true })).toBeVisible()
  await accessible(page); await capture(page, 'history-desktop')
  await page.getByLabel('Search vehicles').fill('no-matching-vehicle'); await page.getByRole('button', { name: 'Apply filters' }).click()
  await expect(page.getByText('No rides on this stretch.')).toBeVisible()
  await page.goto('/profile'); await page.getByLabel('Display name').fill('Updated Rider')
  await page.getByRole('button', { name: 'Save profile' }).click()
  await expect(page.getByRole('status')).toContainText('profile has been updated')
  await expect(page.getByText('Account management', { exact: true })).toHaveCount(0)
  await accessible(page); await capture(page, 'profile-desktop')
  await page.setViewportSize({ width: 390, height: 844 })
  for (const [path, name] of [[savedUrl, 'result'], ['/predict?type=Scooter', 'prediction'], ['/dashboard', 'dashboard'], ['/history', 'history'], ['/profile', 'profile']]) {
    await page.goto(path); await expect(page.locator('.loading,.page-loading')).toHaveCount(0)
    await fits(page); await accessible(page); await capture(page, `${name}-mobile`)
  }
  await page.locator('[name=current_password]').fill(password)
  await page.locator('[name=new_password]').fill(password + 'changed')
  await page.locator('[name=confirm_password]').fill(password + 'changed')
  await page.getByRole('button', { name: 'Update password' }).click()
  await expect(page).toHaveURL(/signin\?password=changed/)
  // The password change starts a new document. Wait for its session check before
  // the next explicit navigation; WebKit reports prematurely canceled fetches.
  await expect(page.getByRole('button', { name: 'Sign in', exact: true })).toBeEnabled()
  await login(page, email, password + 'changed')
  await page.getByRole('button', { name: 'Open navigation' }).click()
  await page.getByRole('button', { name: 'Sign out', exact: true }).click()
  await expect(page).toHaveURL(/signin/)
  expect(errors).toEqual([])
})

test('admin profile can disable and restore an account', async ({ page }) => {
  await login(page, 'admin@example.com')
  await page.goto('/profile')
  await expect(page.getByText('Account management', { exact: true })).toBeVisible()
  const viewer = page.getByRole('row').filter({ hasText: 'viewer@example.com' })
  await viewer.getByRole('button', { name: 'Disable account' }).click()
  await expect(viewer).toContainText('Disabled')
  await viewer.getByRole('button', { name: 'Enable account' }).click()
  await expect(viewer.getByRole('button', { name: 'Disable account' })).toBeEnabled()
  await expect(page.getByRole('row').filter({ hasText: 'admin@example.com' }).getByRole('button')).toBeDisabled()
  await accessible(page); await capture(page, 'admin-desktop')
})

test('catalog outage blocks unsafe input and retry restores the bounded form', async ({ page }) => {
  await login(page)
  await page.route('**/api/v1/catalog/**', route => route.fulfill({ status: 503, json: { error: { message: 'Catalog unavailable.' } } }))
  await page.goto('/predict?type=Bike')
  await expect(page.getByText(/We couldn’t load the catalog/)).toBeVisible()
  await expect(page.locator('[name=manufacture_year]')).toBeDisabled()
  await expect(page.getByRole('button', { name: 'Get my estimate' })).toBeDisabled()
  await page.unroute('**/api/v1/catalog/**')
  await page.getByRole('button', { name: 'Try again', exact: true }).click()
  await selectVehicle(page, 'Honda', 'CB Shine', '2020')
  await page.locator('[name=km_driven]').fill('30000')
  await page.route('**/api/v1/predictions', route => route.fulfill({ status: 503, json: { error: { message: 'Please retry your estimate.' } } }))
  await page.getByRole('button', { name: 'Get my estimate' }).click()
  await expect(page.getByRole('alert')).toContainText('Please retry your estimate.')
  await expect(page.getByRole('combobox', { name: 'Model *', exact: true })).toHaveValue('CB Shine')
  await expect(page.getByRole('button', { name: 'Get my estimate' })).toBeEnabled()
  await accessible(page)
})

test('expired sessions return to sign in and unsafe next URLs stay internal', async ({ page }) => {
  await login(page)
  await page.route('**/api/v1/dashboard', route => route.fulfill({ status: 401, json: { error: { message: 'Session expired.' } } }))
  await page.goto('/dashboard'); await expect(page).toHaveURL(/signin\?next=/)
  await page.context().clearCookies()
  await page.unrouteAll()
  await page.goto('/signin?next=https://example.com')
  await page.getByLabel('Email address').fill('viewer@example.com')
  await page.locator('input[name=password]').fill(password)
  await page.getByRole('button', { name: 'Sign in', exact: true }).click()
  await expect(page).toHaveURL(`${test.info().project.use.baseURL}/dashboard`)
})

test('type changes reset fields, invalid numbers stay local, and PDF failures are recoverable', async ({ page }) => {
  await login(page)
  await page.goto('/predict?type=Car')
  await selectVehicle(page, 'Toyota', 'Corolla', '2020')
  await page.locator('[name=owner_count]').fill('2')
  await page.getByRole('radio', { name: /^Scooter / }).click()
  await expect(page.getByRole('radio', { name: /^Scooter / })).toBeChecked()
  await expect(page.locator('[name=manufacture_year]')).toHaveValue('')
  await expect(page.locator('[name=condition]')).toHaveCount(0)
  await selectVehicle(page, 'Honda', 'Dio', '2020')
  await page.locator('[name=km_driven]').fill('-1')
  await page.getByRole('button', { name: 'Get my estimate' }).click()
  expect(await page.locator('[name=km_driven]').evaluate((input: HTMLInputElement) => input.validity.rangeUnderflow)).toBe(true)
  await page.locator('[name=km_driven]').fill('30000')
  await expect(page.locator('[name=fuel_type]')).toHaveCount(0)
  await expect(page.locator('[name=motor_power_kw]')).toHaveCount(0)
  await page.locator('[name=engine_capacity_cc]').fill('110')
  await page.getByRole('button', { name: 'Get my estimate' }).click()
  await expect(page).toHaveURL(/\/predictions\/[a-f0-9-]+/)
  const saved = page.url()
  const id = saved.split('/').at(-1)
  await page.route(`**/api/v1/predictions/${id}/report.pdf`, route => route.fulfill({ status: 503, json: { error: { message: 'Report temporarily unavailable.' } } }))
  await page.getByRole('button', { name: 'Download PDF report' }).click()
  await expect(page.getByRole('alert')).toContainText('Report temporarily unavailable.')
  await expect(page.getByRole('button', { name: 'Download PDF report' })).toBeEnabled()
})

test('year choices and fuel controls exactly follow each model catalog', async ({ page }) => {
  await login(page)
  for (const [type, brand, model, low, high] of [
    ['Car', 'Toyota', 'Corolla', 2011, 2025], ['Scooter', 'Hero', 'Pleasure', 2004, 2012],
  ] as const) {
    await page.goto(`/predict?type=${type}`)
    await selectVehicle(page, brand, model, String(high))
    const years = await page.locator('[name=manufacture_year] option').evaluateAll(options => options.map(o => (o as HTMLOptionElement).value).filter(Boolean))
    expect(years).toEqual(Array.from({length: high-low+1},(_,i)=>String(high-i)))
    await expect(page.locator('input[name=manufacture_year]')).toHaveCount(0)
  }
  await page.goto('/predict?type=Scooter')
  await selectVehicle(page,'Yadea','C1S','2019')
  await expect(page.locator('[name=motor_power_kw]')).toHaveAttribute('max','3')
  await expect(page.locator('[name=engine_capacity_cc]')).toHaveCount(0)
  await selectVehicle(page,'Honda','Dio','2020')
  await expect(page.locator('[name=motor_power_kw]')).toHaveCount(0)
  await page.goto('/predict?type=Car')
  await selectVehicle(page,'Maruti Suzuki','Alto','2020')
  await expect(page.locator('[name=fuel_type] option')).toHaveText(['Not specified','Petrol'])
  await page.getByRole('combobox',{name:'Brand *',exact:true}).selectOption('BYD')
  await expect(page.locator('[name=manufacture_year]')).toHaveValue('')
  await expect(page.getByRole('button',{name:'Get my estimate'})).toBeDisabled()
})
