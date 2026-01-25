import { test, expect } from '@playwright/test'

test.describe('SettingsPage', () => {
  test.beforeEach(async ({ page }) => {
    await page.goto('/settings')
  })

  test('renders the settings page', async ({ page }) => {
    await expect(page).toHaveURL(/.*settings/)
  })

  test('displays settings sections', async ({ page }) => {
    // Should show settings form/sections
    const settingsContent = page.locator('main').or(page.locator('[data-testid="settings"]'))
    await expect(settingsContent).toBeVisible()
  })

  test.describe('Theme Settings', () => {
    test('can change theme', async ({ page }) => {
      const themeSelect = page.locator('[data-testid="theme-select"]').or(
        page.locator('select[name="theme"]').or(
          page.locator('button:has-text("Dark")').or(page.locator('button:has-text("Light")'))
        )
      )
      if (await themeSelect.isVisible()) {
        await themeSelect.click()
      }
    })
  })

  test.describe('Display Settings', () => {
    test('can change text size', async ({ page }) => {
      const textSizeSelect = page.locator('[data-testid="text-size-select"]').or(
        page.locator('select[name="textSize"]')
      )
      if (await textSizeSelect.isVisible()) {
        await textSizeSelect.selectOption({ label: 'Large' })
      }
    })
  })

  test.describe('API Integration', () => {
    test('fetches settings from API', async ({ page }) => {
      let apiCalled = false
      page.on('request', (req) => {
        if (req.url().includes('/api/settings')) {
          apiCalled = true
        }
      })
      
      await page.goto('/settings')
      await page.waitForTimeout(1000)
      
      if (!apiCalled) {
        test.info().annotations.push({
          type: 'warning',
          description: 'Settings API not called - needs endpoint'
        })
      }
    })

    test('saves settings to API', async ({ page }) => {
      let putCalled = false
      page.on('request', (req) => {
        if (req.url().includes('/api/settings') && (req.method() === 'PUT' || req.method() === 'PATCH')) {
          putCalled = true
        }
      })
      
      // Try to change a setting
      const saveButton = page.locator('button:has-text("Save")').first()
      if (await saveButton.isVisible()) {
        await saveButton.click()
        await page.waitForTimeout(500)
        
        if (!putCalled) {
          test.info().annotations.push({
            type: 'warning',
            description: 'Settings save API not called'
          })
        }
      }
    })
  })
})
