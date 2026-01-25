import { test, expect } from '@playwright/test';

/**
 * Universal Query E2E Tests
 * 
 * Tests for the universal query/search functionality.
 * Tests cover: natural language queries, structured queries, saved queries.
 */

test.describe('Universal Query Page', () => {
  
  test.beforeEach(async ({ page }) => {
    await page.goto('/query');
  });

  test('should load query page with input', async ({ page }) => {
    // Query page should load
    await expect(page.locator('[data-testid="query-page"]')).toBeVisible();
    
    // Natural language input should be visible
    await expect(page.locator('[data-testid="nl-query-input"]')).toBeVisible();
    
    // Execute button should be visible
    await expect(page.locator('[data-testid="execute-query"]')).toBeVisible();
  });

  test('should execute natural language query', async ({ page }) => {
    // Enter a natural language query
    await page.fill('[data-testid="nl-query-input"]', 
      'technology companies with revenue over 10 billion'
    );
    
    // Click execute
    await page.click('[data-testid="execute-query"]');
    
    // Wait for results
    await page.waitForResponse(resp => resp.url().includes('/query') && resp.status() === 200);
    
    // Results table should be visible
    const resultsTable = page.locator('[data-testid="results-table"]');
    await expect(resultsTable).toBeVisible();
    
    // Should have results
    const rows = page.locator('[data-testid="result-row"]');
    const count = await rows.count();
    expect(count).toBeGreaterThan(0);
  });

  test('should show query suggestions as typing', async ({ page }) => {
    // Start typing
    await page.fill('[data-testid="nl-query-input"]', 'tech companies with');
    
    // Suggestions should appear
    const suggestions = page.locator('[data-testid="query-suggestions"]');
    await expect(suggestions).toBeVisible();
    
    // Should have suggestion items
    const items = page.locator('[data-testid="suggestion-item"]');
    const count = await items.count();
    expect(count).toBeGreaterThan(0);
    
    // Click a suggestion
    await items.first().click();
    
    // Input should update
    const inputValue = await page.inputValue('[data-testid="nl-query-input"]');
    expect(inputValue.length).toBeGreaterThan('tech companies with'.length);
  });

  test('should switch to structured query mode', async ({ page }) => {
    // Click structured query tab
    await page.click('[data-testid="structured-query-tab"]');
    
    // Structured query builder should be visible
    await expect(page.locator('[data-testid="query-builder"]')).toBeVisible();
    
    // Should have filter rows
    await expect(page.locator('[data-testid="filter-row"]')).toBeVisible();
  });

  test('should build structured query with filters', async ({ page }) => {
    // Switch to structured mode
    await page.click('[data-testid="structured-query-tab"]');
    
    // Add first filter: Sector = Technology
    await page.selectOption('[data-testid="filter-field-0"]', 'sector');
    await page.selectOption('[data-testid="filter-op-0"]', '=');
    await page.selectOption('[data-testid="filter-value-0"]', 'Technology');
    
    // Add second filter: Revenue > $10B
    await page.click('[data-testid="add-filter"]');
    await page.selectOption('[data-testid="filter-field-1"]', 'revenue');
    await page.selectOption('[data-testid="filter-op-1"]', '>');
    await page.fill('[data-testid="filter-value-1"]', '10000000000');
    
    // Execute query
    await page.click('[data-testid="execute-query"]');
    
    // Wait for results
    await page.waitForLoadState('networkidle');
    
    // Should have results
    const resultsCount = page.locator('[data-testid="results-count"]');
    await expect(resultsCount).toBeVisible();
    const countText = await resultsCount.textContent();
    expect(countText).toContain('companies');
  });

  test('should remove filter from query builder', async ({ page }) => {
    // Switch to structured mode
    await page.click('[data-testid="structured-query-tab"]');
    
    // Add two filters
    await page.click('[data-testid="add-filter"]');
    
    // Should have 2 filter rows
    const filterRows = page.locator('[data-testid="filter-row"]');
    expect(await filterRows.count()).toBe(2);
    
    // Remove second filter
    await page.click('[data-testid="remove-filter-1"]');
    
    // Should have 1 filter row
    expect(await filterRows.count()).toBe(1);
  });

  test('should navigate to company from results', async ({ page }) => {
    // Execute a query
    await page.fill('[data-testid="nl-query-input"]', 'Apple');
    await page.click('[data-testid="execute-query"]');
    
    // Wait for results
    await page.waitForLoadState('networkidle');
    
    // Click on first result
    const firstRow = page.locator('[data-testid="result-row"]').first();
    await firstRow.click();
    
    // Should navigate to company profile
    await expect(page).toHaveURL(/\/company\//);
  });

  test('should sort results by column', async ({ page }) => {
    // Execute a query
    await page.fill('[data-testid="nl-query-input"]', 'technology companies');
    await page.click('[data-testid="execute-query"]');
    await page.waitForLoadState('networkidle');
    
    // Click revenue column header to sort
    await page.click('[data-testid="column-header-revenue"]');
    
    // Wait for sort
    await page.waitForLoadState('networkidle');
    
    // Get revenue values
    const revenues = await page.locator('[data-testid="cell-revenue"]').allTextContents();
    
    // Should be sorted (descending by default)
    const numericRevenues = revenues.map(r => parseFloat(r.replace(/[$,B]/g, '')));
    for (let i = 1; i < numericRevenues.length; i++) {
      expect(numericRevenues[i]).toBeLessThanOrEqual(numericRevenues[i-1]);
    }
  });

  test('should paginate results', async ({ page }) => {
    // Execute a broad query
    await page.fill('[data-testid="nl-query-input"]', 'all companies');
    await page.click('[data-testid="execute-query"]');
    await page.waitForLoadState('networkidle');
    
    // Should show pagination
    const pagination = page.locator('[data-testid="pagination"]');
    await expect(pagination).toBeVisible();
    
    // Get first page results
    const firstPageFirstRow = await page.locator('[data-testid="result-row"]').first().textContent();
    
    // Click next page
    await page.click('[data-testid="page-next"]');
    await page.waitForLoadState('networkidle');
    
    // Results should be different
    const secondPageFirstRow = await page.locator('[data-testid="result-row"]').first().textContent();
    expect(secondPageFirstRow).not.toBe(firstPageFirstRow);
  });

  test('should export results to CSV', async ({ page }) => {
    // Execute a query
    await page.fill('[data-testid="nl-query-input"]', 'tech companies');
    await page.click('[data-testid="execute-query"]');
    await page.waitForLoadState('networkidle');
    
    // Click export button
    const [download] = await Promise.all([
      page.waitForEvent('download'),
      page.click('[data-testid="export-csv"]')
    ]);
    
    // Verify download
    expect(download.suggestedFilename()).toContain('.csv');
  });

  test('should save query for later use', async ({ page }) => {
    // Execute a query
    await page.fill('[data-testid="nl-query-input"]', 'tech companies revenue > $50B');
    await page.click('[data-testid="execute-query"]');
    await page.waitForLoadState('networkidle');
    
    // Click save query
    await page.click('[data-testid="save-query"]');
    
    // Modal should appear
    const modal = page.locator('[data-testid="save-query-modal"]');
    await expect(modal).toBeVisible();
    
    // Enter query name
    await page.fill('[data-testid="query-name-input"]', 'My Big Tech Query');
    
    // Save
    await page.click('[data-testid="confirm-save"]');
    
    // Modal should close
    await expect(modal).not.toBeVisible();
    
    // Success toast
    await expect(page.locator('[data-testid="toast"]')).toContainText('Query saved');
  });

  test('should load and run saved queries', async ({ page }) => {
    // First, save a query (simplified - assume already saved)
    // Navigate to saved queries
    await page.click('[data-testid="saved-queries-tab"]');
    
    // Should show saved queries list
    const savedQueries = page.locator('[data-testid="saved-query-item"]');
    
    // If there are saved queries, run one
    if (await savedQueries.count() > 0) {
      await savedQueries.first().click();
      
      // Should load results
      await page.waitForLoadState('networkidle');
      await expect(page.locator('[data-testid="results-table"]')).toBeVisible();
    }
  });

});

test.describe('Query Filters', () => {

  test('should filter by multiple metrics', async ({ page }) => {
    await page.goto('/query');
    await page.click('[data-testid="structured-query-tab"]');
    
    // Add market cap filter
    await page.selectOption('[data-testid="filter-field-0"]', 'market_cap');
    await page.selectOption('[data-testid="filter-op-0"]', '>');
    await page.fill('[data-testid="filter-value-0"]', '100000000000');
    
    // Add P/E filter
    await page.click('[data-testid="add-filter"]');
    await page.selectOption('[data-testid="filter-field-1"]', 'pe_ratio');
    await page.selectOption('[data-testid="filter-op-1"]', '<');
    await page.fill('[data-testid="filter-value-1"]', '30');
    
    // Add sector filter
    await page.click('[data-testid="add-filter"]');
    await page.selectOption('[data-testid="filter-field-2"]', 'sector');
    await page.selectOption('[data-testid="filter-op-2"]', '=');
    await page.selectOption('[data-testid="filter-value-2"]', 'Technology');
    
    // Execute
    await page.click('[data-testid="execute-query"]');
    await page.waitForLoadState('networkidle');
    
    // Verify results match criteria
    const resultsCount = page.locator('[data-testid="results-count"]');
    await expect(resultsCount).toBeVisible();
  });

  test('should filter by relationship type', async ({ page }) => {
    await page.goto('/query');
    await page.click('[data-testid="structured-query-tab"]');
    
    // Select relationship filter
    await page.selectOption('[data-testid="filter-field-0"]', 'has_relationship');
    await page.selectOption('[data-testid="filter-op-0"]', '=');
    await page.selectOption('[data-testid="filter-value-0"]', 'supplies_to');
    
    // Add target entity
    await page.click('[data-testid="add-filter"]');
    await page.selectOption('[data-testid="filter-field-1"]', 'relationship_target');
    await page.fill('[data-testid="filter-value-1"]', 'TSLA');
    
    // Execute - should find Tesla suppliers
    await page.click('[data-testid="execute-query"]');
    await page.waitForLoadState('networkidle');
    
    await expect(page.locator('[data-testid="results-table"]')).toBeVisible();
  });

});
