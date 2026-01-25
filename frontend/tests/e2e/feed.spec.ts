import { test, expect } from '@playwright/test';

/**
 * Social Feed E2E Tests
 * 
 * Tests for the Instagram-style financial news feed experience.
 * Tests cover: loading, filtering, navigation, interactions.
 */

test.describe('Social Feed Page', () => {
  
  test.beforeEach(async ({ page }) => {
    await page.goto('/feed');
  });

  test('should load feed page with items', async ({ page }) => {
    // Wait for feed items to load
    await expect(page.locator('[data-testid="feed-container"]')).toBeVisible();
    
    // Should have at least some feed cards
    const feedCards = page.locator('[data-testid="feed-card"]');
    await expect(feedCards.first()).toBeVisible({ timeout: 10000 });
    
    // Should have more than 0 items
    const count = await feedCards.count();
    expect(count).toBeGreaterThan(0);
  });

  test('should display filing cards with correct structure', async ({ page }) => {
    // Find a filing card
    const filingCard = page.locator('[data-testid="filing-card"]').first();
    
    // Should have key elements
    await expect(filingCard.locator('[data-testid="ticker-link"]')).toBeVisible();
    await expect(filingCard.locator('[data-testid="form-type"]')).toBeVisible();
    await expect(filingCard.locator('[data-testid="filed-date"]')).toBeVisible();
  });

  test('should filter feed by form type', async ({ page }) => {
    // Click on 10-K filter
    await page.click('[data-testid="filter-10k"]');
    
    // Wait for filter to apply
    await page.waitForResponse(resp => resp.url().includes('/feed') && resp.status() === 200);
    
    // All visible cards should be 10-K
    const formTypes = page.locator('[data-testid="form-type"]');
    const count = await formTypes.count();
    
    for (let i = 0; i < count; i++) {
      await expect(formTypes.nth(i)).toHaveText('10-K');
    }
  });

  test('should filter feed by sector', async ({ page }) => {
    // Open sector filter dropdown
    await page.click('[data-testid="sector-filter-dropdown"]');
    
    // Select Technology
    await page.click('[data-testid="sector-option-technology"]');
    
    // Wait for filter to apply
    await page.waitForLoadState('networkidle');
    
    // Verify technology companies appear
    const sectorLabels = page.locator('[data-testid="company-sector"]');
    const firstSector = await sectorLabels.first().textContent();
    expect(firstSector?.toLowerCase()).toContain('technology');
  });

  test('should navigate to company profile when clicking ticker', async ({ page }) => {
    // Find a ticker link
    const tickerLink = page.locator('[data-testid="ticker-link"]').first();
    const ticker = await tickerLink.textContent();
    
    // Click the ticker
    await tickerLink.click();
    
    // Should navigate to company profile
    await expect(page).toHaveURL(new RegExp(`/company/${ticker?.replace('$', '')}`));
    
    // Company profile should load
    await expect(page.locator('[data-testid="company-header"]')).toBeVisible();
  });

  test('should like a feed item', async ({ page }) => {
    // Find the first like button and its count
    const likeButton = page.locator('[data-testid="like-button"]').first();
    const likeCount = page.locator('[data-testid="like-count"]').first();
    
    // Get initial count
    const initialCount = parseInt(await likeCount.textContent() || '0');
    
    // Click like
    await likeButton.click();
    
    // Count should increase
    await expect(likeCount).toHaveText((initialCount + 1).toString());
    
    // Button should show liked state
    await expect(likeButton).toHaveAttribute('data-liked', 'true');
  });

  test('should save a feed item', async ({ page }) => {
    // Find save button
    const saveButton = page.locator('[data-testid="save-button"]').first();
    
    // Click save
    await saveButton.click();
    
    // Should show saved state
    await expect(saveButton).toHaveAttribute('data-saved', 'true');
    
    // Toast notification should appear
    await expect(page.locator('[data-testid="toast"]')).toContainText('Saved');
  });

  test('should load more items on scroll (infinite scroll)', async ({ page }) => {
    // Get initial card count
    const initialCount = await page.locator('[data-testid="feed-card"]').count();
    
    // Scroll to bottom
    await page.evaluate(() => window.scrollTo(0, document.body.scrollHeight));
    
    // Wait for more items to load
    await page.waitForResponse(resp => resp.url().includes('/feed') && resp.status() === 200);
    await page.waitForLoadState('networkidle');
    
    // Should have more items now
    const newCount = await page.locator('[data-testid="feed-card"]').count();
    expect(newCount).toBeGreaterThan(initialCount);
  });

  test('should show trending sidebar', async ({ page }) => {
    // Trending sidebar should be visible
    await expect(page.locator('[data-testid="trending-sidebar"]')).toBeVisible();
    
    // Should have trending tickers
    const trendingTickers = page.locator('[data-testid="trending-ticker"]');
    await expect(trendingTickers.first()).toBeVisible();
    
    // Click on trending ticker should navigate
    const firstTrending = trendingTickers.first();
    const ticker = await firstTrending.textContent();
    await firstTrending.click();
    
    await expect(page).toHaveURL(new RegExp(`/company/`));
  });

  test('should display relationship cards', async ({ page }) => {
    // Filter to show relationship cards
    await page.click('[data-testid="filter-relationships"]');
    
    // Wait for filter
    await page.waitForLoadState('networkidle');
    
    // Find a relationship card
    const relationshipCard = page.locator('[data-testid="relationship-card"]').first();
    
    if (await relationshipCard.isVisible()) {
      // Should show source and target entities
      await expect(relationshipCard.locator('[data-testid="source-entity"]')).toBeVisible();
      await expect(relationshipCard.locator('[data-testid="target-entity"]')).toBeVisible();
      await expect(relationshipCard.locator('[data-testid="relationship-type"]')).toBeVisible();
    }
  });

  test('should navigate between feed tabs', async ({ page }) => {
    // Should have tab navigation
    await expect(page.locator('[data-testid="feed-tabs"]')).toBeVisible();
    
    // Click "Following" tab
    await page.click('[data-testid="tab-following"]');
    
    // URL should update
    await expect(page).toHaveURL(/\/feed\?tab=following/);
    
    // Click "For You" tab
    await page.click('[data-testid="tab-foryou"]');
    
    await expect(page).toHaveURL(/\/feed\?tab=foryou/);
  });

});

test.describe('Feed Search', () => {
  
  test('should search within feed', async ({ page }) => {
    await page.goto('/feed');
    
    // Type in search box
    await page.fill('[data-testid="feed-search"]', 'NVDA');
    
    // Press enter or wait for debounce
    await page.press('[data-testid="feed-search"]', 'Enter');
    
    // Results should be filtered
    await page.waitForLoadState('networkidle');
    
    const cards = page.locator('[data-testid="feed-card"]');
    const count = await cards.count();
    
    // Each card should relate to NVDA
    for (let i = 0; i < Math.min(count, 5); i++) {
      const cardText = await cards.nth(i).textContent();
      expect(cardText?.toLowerCase()).toContain('nvda');
    }
  });

});
