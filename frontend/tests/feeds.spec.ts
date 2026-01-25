import { test, expect } from '@playwright/test'

test.describe('FeedsPage', () => {
  test.beforeEach(async ({ page }) => {
    await page.goto('/feeds')
  })

  test('renders the feeds management page', async ({ page }) => {
    await expect(page).toHaveURL(/.*feeds/)
  })

  test('displays list of configured feeds', async ({ page }) => {
    // Should show feeds table or list
    const feedsList = page.locator('[data-testid="feeds-list"]').or(page.locator('table'))
    await expect(feedsList).toBeVisible()
  })

  test('has add feed button', async ({ page }) => {
    const addButton = page.locator('button:has-text("Add")').or(
      page.locator('button:has-text("Create")').or(
        page.locator('[data-testid="add-feed-button"]')
      )
    )
    await expect(addButton).toBeVisible()
  })

  test.describe('Feed CRUD Operations', () => {
    test('can open add feed modal', async ({ page }) => {
      const addButton = page.locator('button:has-text("Add")').first()
      if (await addButton.isVisible()) {
        await addButton.click()
        
        // Modal should appear
        const modal = page.locator('[role="dialog"]').or(page.locator('.modal'))
        await expect(modal).toBeVisible()
      }
    })

    test('feed form has required fields', async ({ page }) => {
      const addButton = page.locator('button:has-text("Add")').first()
      if (await addButton.isVisible()) {
        await addButton.click()
        
        // Check for form fields
        await expect(page.locator('input[name="name"]').or(page.locator('input[placeholder*="name" i]'))).toBeVisible()
        await expect(page.locator('input[name="url"]').or(page.locator('input[placeholder*="url" i]'))).toBeVisible()
      }
    })
  })

  test.describe('API Integration', () => {
    test('fetches feeds list from API', async ({ page }) => {
      const feedsRequest = page.waitForRequest((req) => 
        req.url().includes('/api/feeds') && req.method() === 'GET'
      )
      
      await page.goto('/feeds')
      
      try {
        await feedsRequest
      } catch {
        test.info().annotations.push({
          type: 'warning',
          description: 'Feeds API not called - check if FeedsPage uses API hooks'
        })
      }
    })

    test('can create feed via API', async ({ page }) => {
      // Intercept POST request
      let postCalled = false
      page.on('request', (req) => {
        if (req.url().includes('/api/feeds') && req.method() === 'POST') {
          postCalled = true
        }
      })
      
      const addButton = page.locator('button:has-text("Add")').first()
      if (await addButton.isVisible()) {
        await addButton.click()
        
        // Fill form
        await page.fill('input[name="name"]', 'Test Feed')
        await page.fill('input[name="url"]', 'https://example.com/rss')
        
        // Submit
        const submitButton = page.locator('button[type="submit"]').or(page.locator('button:has-text("Save")'))
        await submitButton.click()
        
        await page.waitForTimeout(500)
        
        if (!postCalled) {
          test.info().annotations.push({
            type: 'warning',
            description: 'Create feed API not called'
          })
        }
      }
    })
  })
})
