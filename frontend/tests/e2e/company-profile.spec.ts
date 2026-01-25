import { test, expect } from '@playwright/test';

/**
 * Company Profile E2E Tests
 * 
 * Tests for Bloomberg/FactSet-style company profile pages.
 * Tests cover: overview, financials, filings, relationships, navigation.
 */

test.describe('Company Profile Page', () => {
  
  test.beforeEach(async ({ page }) => {
    // Navigate to a specific company profile
    await page.goto('/company/TSLA');
  });

  test('should load company profile with header', async ({ page }) => {
    // Company header should be visible
    await expect(page.locator('[data-testid="company-header"]')).toBeVisible();
    
    // Should show company name and ticker
    await expect(page.locator('[data-testid="company-name"]')).toContainText('Tesla');
    await expect(page.locator('[data-testid="company-ticker"]')).toContainText('TSLA');
  });

  test('should display key metrics', async ({ page }) => {
    // Metrics grid should be visible
    const metricsGrid = page.locator('[data-testid="metrics-grid"]');
    await expect(metricsGrid).toBeVisible();
    
    // Should have key metrics
    await expect(page.locator('[data-testid="metric-market-cap"]')).toBeVisible();
    await expect(page.locator('[data-testid="metric-revenue"]')).toBeVisible();
    await expect(page.locator('[data-testid="metric-pe-ratio"]')).toBeVisible();
  });

  test('should show sector and industry', async ({ page }) => {
    // Sector should be visible and clickable
    const sectorLink = page.locator('[data-testid="company-sector"]');
    await expect(sectorLink).toBeVisible();
    
    // Click sector should navigate
    await sectorLink.click();
    await expect(page).toHaveURL(/\/sectors\//);
  });

  test('should navigate between profile tabs', async ({ page }) => {
    // Tabs should be visible
    const tabs = page.locator('[data-testid="profile-tabs"]');
    await expect(tabs).toBeVisible();
    
    // Click Financials tab
    await page.click('[data-testid="tab-financials"]');
    await expect(page.locator('[data-testid="financial-statements"]')).toBeVisible();
    
    // Click Filings tab
    await page.click('[data-testid="tab-filings"]');
    await expect(page.locator('[data-testid="filings-list"]')).toBeVisible();
    
    // Click Relationships tab
    await page.click('[data-testid="tab-relationships"]');
    await expect(page.locator('[data-testid="relationship-graph"]')).toBeVisible();
  });

  test('should display recent filings', async ({ page }) => {
    // Click on Filings tab
    await page.click('[data-testid="tab-filings"]');
    
    // Filings list should be visible
    const filingsList = page.locator('[data-testid="filings-list"]');
    await expect(filingsList).toBeVisible();
    
    // Should have filing items
    const filingItems = page.locator('[data-testid="filing-item"]');
    const count = await filingItems.count();
    expect(count).toBeGreaterThan(0);
    
    // Each filing should have form type and date
    const firstFiling = filingItems.first();
    await expect(firstFiling.locator('[data-testid="filing-form-type"]')).toBeVisible();
    await expect(firstFiling.locator('[data-testid="filing-date"]')).toBeVisible();
  });

  test('should navigate to filing detail', async ({ page }) => {
    // Click on Filings tab
    await page.click('[data-testid="tab-filings"]');
    
    // Click on a filing
    const firstFiling = page.locator('[data-testid="filing-item"]').first();
    await firstFiling.click();
    
    // Should navigate to filing detail page
    await expect(page).toHaveURL(/\/filings\//);
  });

  test('should display financial statements', async ({ page }) => {
    // Click on Financials tab
    await page.click('[data-testid="tab-financials"]');
    
    // Income statement should be visible by default
    await expect(page.locator('[data-testid="income-statement"]')).toBeVisible();
    
    // Should have revenue line item
    await expect(page.locator('[data-testid="line-revenue"]')).toBeVisible();
    
    // Switch to balance sheet
    await page.click('[data-testid="btn-balance-sheet"]');
    await expect(page.locator('[data-testid="balance-sheet"]')).toBeVisible();
    
    // Switch to cash flow
    await page.click('[data-testid="btn-cash-flow"]');
    await expect(page.locator('[data-testid="cash-flow"]')).toBeVisible();
  });

  test('should display revenue segments', async ({ page }) => {
    // Click on Segments tab or section
    await page.click('[data-testid="tab-segments"]');
    
    // Segment chart should be visible
    const segmentChart = page.locator('[data-testid="segment-chart"]');
    await expect(segmentChart).toBeVisible();
    
    // Should have segment breakdown
    const segments = page.locator('[data-testid="segment-item"]');
    const count = await segments.count();
    expect(count).toBeGreaterThan(0);
  });

  test('should display entity relationships mini-graph', async ({ page }) => {
    // Click on Relationships tab
    await page.click('[data-testid="tab-relationships"]');
    
    // Relationship graph should be visible
    const graph = page.locator('[data-testid="relationship-graph"]');
    await expect(graph).toBeVisible();
    
    // Should have nodes
    const nodes = page.locator('[data-testid="graph-node"]');
    const count = await nodes.count();
    expect(count).toBeGreaterThan(0);
    
    // "Explore Full Graph" button should exist
    await expect(page.locator('[data-testid="btn-explore-graph"]')).toBeVisible();
  });

  test('should navigate to full graph explorer', async ({ page }) => {
    // Click on Relationships tab
    await page.click('[data-testid="tab-relationships"]');
    
    // Click explore full graph
    await page.click('[data-testid="btn-explore-graph"]');
    
    // Should navigate to relationship explorer with company context
    await expect(page).toHaveURL(/\/relationships.*TSLA/);
  });

  test('should display competitor table', async ({ page }) => {
    // Competitors section should be visible
    const competitors = page.locator('[data-testid="competitors-table"]');
    await expect(competitors).toBeVisible();
    
    // Should have competitor rows
    const rows = page.locator('[data-testid="competitor-row"]');
    const count = await rows.count();
    expect(count).toBeGreaterThan(0);
    
    // Click competitor should navigate
    const firstCompetitor = rows.first();
    const ticker = await firstCompetitor.locator('[data-testid="competitor-ticker"]').textContent();
    await firstCompetitor.click();
    
    await expect(page).toHaveURL(new RegExp(`/company/${ticker?.replace('$', '')}`));
  });

  test('should follow/unfollow company', async ({ page }) => {
    const followButton = page.locator('[data-testid="follow-button"]');
    
    // Get initial state
    const isFollowing = await followButton.getAttribute('data-following') === 'true';
    const initialText = await followButton.textContent();
    
    // Click to toggle
    await followButton.click();
    
    // Wait for API response
    await page.waitForLoadState('networkidle');
    
    // State should change
    if (isFollowing) {
      await expect(followButton).toHaveText('Follow');
    } else {
      await expect(followButton).toHaveText('Following');
    }
  });

  test('should set price alert', async ({ page }) => {
    // Click alert button
    await page.click('[data-testid="alert-button"]');
    
    // Alert modal should open
    const modal = page.locator('[data-testid="alert-modal"]');
    await expect(modal).toBeVisible();
    
    // Fill in alert details
    await page.selectOption('[data-testid="alert-type"]', 'price_change');
    await page.fill('[data-testid="alert-threshold"]', '5');
    
    // Save alert
    await page.click('[data-testid="save-alert"]');
    
    // Modal should close
    await expect(modal).not.toBeVisible();
    
    // Success toast
    await expect(page.locator('[data-testid="toast"]')).toContainText('Alert created');
  });

  test('should display industry news feed', async ({ page }) => {
    // Industry news section should be visible
    const industryNews = page.locator('[data-testid="industry-news"]');
    await expect(industryNews).toBeVisible();
    
    // Should have news items
    const newsItems = page.locator('[data-testid="news-item"]');
    const count = await newsItems.count();
    expect(count).toBeGreaterThan(0);
  });

});

test.describe('Company Profile Navigation', () => {

  test('should handle invalid ticker gracefully', async ({ page }) => {
    await page.goto('/company/INVALIDTICKER123');
    
    // Should show error or not found state
    await expect(page.locator('[data-testid="company-not-found"]')).toBeVisible();
  });

  test('should support deep linking to tabs', async ({ page }) => {
    // Navigate directly to financials tab
    await page.goto('/company/TSLA?tab=financials');
    
    // Financials should be visible
    await expect(page.locator('[data-testid="financial-statements"]')).toBeVisible();
    
    // Navigate directly to filings tab
    await page.goto('/company/TSLA?tab=filings');
    
    // Filings should be visible
    await expect(page.locator('[data-testid="filings-list"]')).toBeVisible();
  });

  test('should preserve filters when navigating back', async ({ page }) => {
    // Start on company profile
    await page.goto('/company/TSLA');
    
    // Click on Financials tab
    await page.click('[data-testid="tab-financials"]');
    
    // Click on a competitor to navigate away
    await page.click('[data-testid="competitor-row"]');
    await page.waitForURL(/\/company\//);
    
    // Go back
    await page.goBack();
    
    // Should return to TSLA with financials tab still selected
    await expect(page).toHaveURL(/\/company\/TSLA/);
    await expect(page.locator('[data-testid="financial-statements"]')).toBeVisible();
  });

});
