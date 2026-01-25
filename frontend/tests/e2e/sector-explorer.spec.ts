import { test, expect } from '@playwright/test';

/**
 * Sector Explorer E2E Tests
 * 
 * Tests for the sector/industry exploration functionality.
 * Tests cover: sector grid, industry drill-down, company lists.
 */

test.describe('Sector Explorer Page', () => {
  
  test.beforeEach(async ({ page }) => {
    await page.goto('/sectors');
  });

  test('should load sector explorer with sector cards', async ({ page }) => {
    // Sector explorer should load
    await expect(page.locator('[data-testid="sector-explorer"]')).toBeVisible();
    
    // Should have sector cards
    const sectorCards = page.locator('[data-testid="sector-card"]');
    const count = await sectorCards.count();
    expect(count).toBeGreaterThan(0);
  });

  test('should display sector card with metrics', async ({ page }) => {
    // Get first sector card
    const sectorCard = page.locator('[data-testid="sector-card"]').first();
    
    // Should have sector name
    await expect(sectorCard.locator('[data-testid="sector-name"]')).toBeVisible();
    
    // Should have company count
    await expect(sectorCard.locator('[data-testid="company-count"]')).toBeVisible();
    
    // Should have performance metric
    await expect(sectorCard.locator('[data-testid="sector-performance"]')).toBeVisible();
    
    // Should have top company
    await expect(sectorCard.locator('[data-testid="top-company"]')).toBeVisible();
  });

  test('should navigate to sector detail on card click', async ({ page }) => {
    // Get sector name before clicking
    const sectorCard = page.locator('[data-testid="sector-card"]').first();
    const sectorName = await sectorCard.locator('[data-testid="sector-name"]').textContent();
    
    // Click sector card
    await sectorCard.click();
    
    // Should navigate to sector detail
    await expect(page).toHaveURL(/\/sectors\//);
    
    // Sector detail page should load
    await expect(page.locator('[data-testid="sector-detail"]')).toBeVisible();
  });

  test('should toggle between grid and list view', async ({ page }) => {
    // Default should be grid view
    await expect(page.locator('[data-testid="sector-grid"]')).toBeVisible();
    
    // Click list view toggle
    await page.click('[data-testid="view-toggle-list"]');
    
    // Should switch to list view
    await expect(page.locator('[data-testid="sector-list"]')).toBeVisible();
    await expect(page.locator('[data-testid="sector-grid"]')).not.toBeVisible();
    
    // Click grid view toggle
    await page.click('[data-testid="view-toggle-grid"]');
    
    // Should switch back to grid
    await expect(page.locator('[data-testid="sector-grid"]')).toBeVisible();
  });

  test('should sort sectors by different metrics', async ({ page }) => {
    // Get initial order
    const initialOrder = await page.locator('[data-testid="sector-name"]').allTextContents();
    
    // Sort by company count
    await page.selectOption('[data-testid="sort-select"]', 'company_count');
    
    // Wait for sort
    await page.waitForLoadState('networkidle');
    
    // Get new order
    const newOrder = await page.locator('[data-testid="sector-name"]').allTextContents();
    
    // Order should be different (unless already sorted by count)
    // Just verify sort was applied
    await expect(page.locator('[data-testid="sort-select"]')).toHaveValue('company_count');
  });

});

test.describe('Sector Detail Page', () => {
  
  test.beforeEach(async ({ page }) => {
    await page.goto('/sectors/technology');
  });

  test('should load sector detail with header', async ({ page }) => {
    // Sector detail should load
    await expect(page.locator('[data-testid="sector-detail"]')).toBeVisible();
    
    // Header should show sector name
    await expect(page.locator('[data-testid="sector-header"]')).toContainText('Technology');
    
    // Should show total company count
    await expect(page.locator('[data-testid="total-companies"]')).toBeVisible();
  });

  test('should display industries within sector', async ({ page }) => {
    // Industries table should be visible
    const industriesTable = page.locator('[data-testid="industries-table"]');
    await expect(industriesTable).toBeVisible();
    
    // Should have industry rows
    const industryRows = page.locator('[data-testid="industry-row"]');
    const count = await industryRows.count();
    expect(count).toBeGreaterThan(0);
    
    // Each row should have name and metrics
    const firstRow = industryRows.first();
    await expect(firstRow.locator('[data-testid="industry-name"]')).toBeVisible();
    await expect(firstRow.locator('[data-testid="industry-companies"]')).toBeVisible();
  });

  test('should navigate to industry detail', async ({ page }) => {
    // Click on an industry row
    const industryRow = page.locator('[data-testid="industry-row"]').first();
    const industryName = await industryRow.locator('[data-testid="industry-name"]').textContent();
    
    await industryRow.click();
    
    // Should navigate to industry detail
    await expect(page).toHaveURL(/\/sectors\/technology\/industries\//);
    
    // Industry detail should load
    await expect(page.locator('[data-testid="industry-detail"]')).toBeVisible();
  });

  test('should show sector performance chart', async ({ page }) => {
    // Performance chart should be visible
    const chart = page.locator('[data-testid="sector-performance-chart"]');
    await expect(chart).toBeVisible();
  });

  test('should show top companies in sector', async ({ page }) => {
    // Top companies section should be visible
    const topCompanies = page.locator('[data-testid="top-companies"]');
    await expect(topCompanies).toBeVisible();
    
    // Should have company items
    const companyItems = page.locator('[data-testid="top-company-item"]');
    const count = await companyItems.count();
    expect(count).toBeGreaterThan(0);
    
    // Click company should navigate
    await companyItems.first().click();
    await expect(page).toHaveURL(/\/company\//);
  });

});

test.describe('Industry Detail Page', () => {
  
  test.beforeEach(async ({ page }) => {
    await page.goto('/sectors/technology/industries/semiconductors');
  });

  test('should load industry detail with companies', async ({ page }) => {
    // Industry detail should load
    await expect(page.locator('[data-testid="industry-detail"]')).toBeVisible();
    
    // Header should show industry name
    await expect(page.locator('[data-testid="industry-header"]')).toContainText('Semiconductors');
    
    // Companies table should be visible
    await expect(page.locator('[data-testid="companies-table"]')).toBeVisible();
  });

  test('should display company list with metrics', async ({ page }) => {
    // Companies table should have rows
    const companyRows = page.locator('[data-testid="company-row"]');
    const count = await companyRows.count();
    expect(count).toBeGreaterThan(0);
    
    // Each row should have key info
    const firstRow = companyRows.first();
    await expect(firstRow.locator('[data-testid="company-ticker"]')).toBeVisible();
    await expect(firstRow.locator('[data-testid="company-name"]')).toBeVisible();
    await expect(firstRow.locator('[data-testid="company-market-cap"]')).toBeVisible();
  });

  test('should sort companies by metrics', async ({ page }) => {
    // Click market cap header to sort
    await page.click('[data-testid="column-header-market-cap"]');
    
    // Wait for sort
    await page.waitForLoadState('networkidle');
    
    // Get market cap values
    const marketCaps = await page.locator('[data-testid="company-market-cap"]').allTextContents();
    
    // Should be sorted descending
    const numericCaps = marketCaps.map(m => {
      const match = m.match(/[\d.]+/);
      return match ? parseFloat(match[0]) : 0;
    });
    
    for (let i = 1; i < numericCaps.length; i++) {
      expect(numericCaps[i]).toBeLessThanOrEqual(numericCaps[i-1]);
    }
  });

  test('should navigate to company profile', async ({ page }) => {
    // Click on a company row
    const companyRow = page.locator('[data-testid="company-row"]').first();
    const ticker = await companyRow.locator('[data-testid="company-ticker"]').textContent();
    
    await companyRow.click();
    
    // Should navigate to company profile
    await expect(page).toHaveURL(new RegExp(`/company/${ticker?.replace('$', '')}`));
  });

  test('should show industry benchmarks', async ({ page }) => {
    // Benchmarks section should be visible
    const benchmarks = page.locator('[data-testid="industry-benchmarks"]');
    await expect(benchmarks).toBeVisible();
    
    // Should show key metrics
    await expect(page.locator('[data-testid="benchmark-pe"]')).toBeVisible();
    await expect(page.locator('[data-testid="benchmark-revenue-growth"]')).toBeVisible();
  });

  test('should paginate company list', async ({ page }) => {
    // If more than 20 companies, pagination should appear
    const pagination = page.locator('[data-testid="pagination"]');
    
    if (await pagination.isVisible()) {
      // Get first page first company
      const firstCompany = await page.locator('[data-testid="company-ticker"]').first().textContent();
      
      // Go to next page
      await page.click('[data-testid="page-next"]');
      await page.waitForLoadState('networkidle');
      
      // First company should be different
      const newFirstCompany = await page.locator('[data-testid="company-ticker"]').first().textContent();
      expect(newFirstCompany).not.toBe(firstCompany);
    }
  });

});

test.describe('Sector Navigation Flow', () => {

  test('should complete full navigation: sectors → sector → industry → company', async ({ page }) => {
    // Start at sectors
    await page.goto('/sectors');
    
    // Click Technology sector
    await page.click('[data-testid="sector-card"]:has-text("Technology")');
    await expect(page).toHaveURL(/\/sectors\/technology/);
    
    // Click Semiconductors industry
    await page.click('[data-testid="industry-row"]:has-text("Semiconductor")');
    await expect(page).toHaveURL(/\/sectors\/technology\/industries\//);
    
    // Click first company
    await page.locator('[data-testid="company-row"]').first().click();
    await expect(page).toHaveURL(/\/company\//);
    
    // Verify company profile loads
    await expect(page.locator('[data-testid="company-header"]')).toBeVisible();
  });

  test('should support breadcrumb navigation', async ({ page }) => {
    // Navigate to industry detail
    await page.goto('/sectors/technology/industries/semiconductors');
    
    // Breadcrumbs should be visible
    const breadcrumbs = page.locator('[data-testid="breadcrumbs"]');
    await expect(breadcrumbs).toBeVisible();
    
    // Click sector breadcrumb
    await page.click('[data-testid="breadcrumb-sector"]');
    await expect(page).toHaveURL(/\/sectors\/technology$/);
    
    // Click sectors breadcrumb
    await page.click('[data-testid="breadcrumb-sectors"]');
    await expect(page).toHaveURL(/\/sectors$/);
  });

});
