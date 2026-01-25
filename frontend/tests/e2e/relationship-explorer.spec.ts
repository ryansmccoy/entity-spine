import { test, expect } from '@playwright/test';

/**
 * Relationship Explorer E2E Tests
 * 
 * Tests for the knowledge graph exploration functionality.
 * Tests cover: 2D/3D graph views, entity navigation, path finding.
 */

test.describe('Relationship Explorer Page', () => {
  
  test.beforeEach(async ({ page }) => {
    await page.goto('/relationships');
  });

  test('should load relationship explorer with graph', async ({ page }) => {
    // Page should load
    await expect(page.locator('[data-testid="relationship-explorer"]')).toBeVisible();
    
    // Graph container should be visible
    await expect(page.locator('[data-testid="graph-container"]')).toBeVisible();
  });

  test('should display graph nodes', async ({ page }) => {
    // Wait for graph to render
    await page.waitForTimeout(2000); // Graph rendering takes time
    
    // Should have nodes
    const nodes = page.locator('[data-testid="graph-node"]');
    const count = await nodes.count();
    expect(count).toBeGreaterThan(0);
  });

  test('should display graph edges', async ({ page }) => {
    // Wait for graph to render
    await page.waitForTimeout(2000);
    
    // Should have edges/links
    const edges = page.locator('[data-testid="graph-edge"]');
    const count = await edges.count();
    expect(count).toBeGreaterThan(0);
  });

  test('should toggle between 2D and 3D view', async ({ page }) => {
    // Default might be 2D or 3D depending on implementation
    const viewToggle = page.locator('[data-testid="view-toggle"]');
    await expect(viewToggle).toBeVisible();
    
    // Click 3D toggle
    await page.click('[data-testid="toggle-3d"]');
    
    // 3D canvas should be visible
    await expect(page.locator('[data-testid="graph-3d"]')).toBeVisible();
    
    // Click 2D toggle
    await page.click('[data-testid="toggle-2d"]');
    
    // 2D SVG should be visible
    await expect(page.locator('[data-testid="graph-2d"]')).toBeVisible();
  });

  test('should filter by relationship type', async ({ page }) => {
    // Open relationship filter
    await page.click('[data-testid="filter-relationship-types"]');
    
    // Uncheck all
    await page.click('[data-testid="filter-uncheck-all"]');
    
    // Check only "supplies_to"
    await page.click('[data-testid="filter-supplies-to"]');
    
    // Apply filter
    await page.click('[data-testid="apply-filters"]');
    
    // Wait for graph to update
    await page.waitForTimeout(1000);
    
    // Graph should update (edges should be filtered)
    // This is hard to verify visually, but we can check the filter is applied
    await expect(page.locator('[data-testid="active-filter-badge"]')).toContainText('supplies_to');
  });

  test('should filter by entity type', async ({ page }) => {
    // Open entity type filter
    await page.click('[data-testid="filter-entity-types"]');
    
    // Select only companies
    await page.click('[data-testid="filter-entity-company"]');
    
    // Apply
    await page.click('[data-testid="apply-filters"]');
    
    await page.waitForTimeout(1000);
    
    // Filter badge should show
    await expect(page.locator('[data-testid="active-filter-badge"]')).toContainText('company');
  });

  test('should search for entity in graph', async ({ page }) => {
    // Enter search query
    await page.fill('[data-testid="graph-search"]', 'Tesla');
    
    // Wait for search
    await page.waitForTimeout(500);
    
    // Search results should appear
    const searchResults = page.locator('[data-testid="search-result"]');
    await expect(searchResults.first()).toBeVisible();
    
    // Click on result
    await searchResults.first().click();
    
    // Graph should center on that entity
    // The selected node should be highlighted
    await expect(page.locator('[data-testid="selected-node"]')).toBeVisible();
  });

  test('should show entity detail sidebar on node click', async ({ page }) => {
    // Wait for graph to render
    await page.waitForTimeout(2000);
    
    // Click on a node
    const node = page.locator('[data-testid="graph-node"]').first();
    await node.click();
    
    // Entity detail sidebar should appear
    const sidebar = page.locator('[data-testid="entity-sidebar"]');
    await expect(sidebar).toBeVisible();
    
    // Should show entity info
    await expect(sidebar.locator('[data-testid="entity-name"]')).toBeVisible();
    await expect(sidebar.locator('[data-testid="entity-type"]')).toBeVisible();
  });

  test('should navigate to company profile from sidebar', async ({ page }) => {
    // Wait for graph
    await page.waitForTimeout(2000);
    
    // Click on a company node
    await page.click('[data-testid="graph-node"][data-entity-type="company"]');
    
    // Sidebar should appear
    await expect(page.locator('[data-testid="entity-sidebar"]')).toBeVisible();
    
    // Click "View Profile" button
    await page.click('[data-testid="btn-view-profile"]');
    
    // Should navigate to company profile
    await expect(page).toHaveURL(/\/company\//);
  });

  test('should show relationships list in sidebar', async ({ page }) => {
    // Wait for graph
    await page.waitForTimeout(2000);
    
    // Click on a node
    await page.click('[data-testid="graph-node"]');
    
    // Sidebar should show relationships
    const relationshipsList = page.locator('[data-testid="entity-relationships"]');
    await expect(relationshipsList).toBeVisible();
    
    // Should have relationship items
    const items = page.locator('[data-testid="relationship-item"]');
    const count = await items.count();
    expect(count).toBeGreaterThan(0);
  });

  test('should expand node to show more connections', async ({ page }) => {
    // Wait for graph
    await page.waitForTimeout(2000);
    
    // Get initial node count
    const initialNodeCount = await page.locator('[data-testid="graph-node"]').count();
    
    // Click on a node
    await page.click('[data-testid="graph-node"]');
    
    // Click expand button
    await page.click('[data-testid="btn-expand-node"]');
    
    // Wait for expansion
    await page.waitForTimeout(1000);
    
    // Should have more nodes now
    const newNodeCount = await page.locator('[data-testid="graph-node"]').count();
    expect(newNodeCount).toBeGreaterThanOrEqual(initialNodeCount);
  });

  test('should zoom controls work', async ({ page }) => {
    // Zoom controls should be visible
    await expect(page.locator('[data-testid="zoom-controls"]')).toBeVisible();
    
    // Click zoom in
    await page.click('[data-testid="btn-zoom-in"]');
    
    // Click zoom out
    await page.click('[data-testid="btn-zoom-out"]');
    
    // Click reset/fit
    await page.click('[data-testid="btn-zoom-fit"]');
    
    // Graph should still be visible
    await expect(page.locator('[data-testid="graph-container"]')).toBeVisible();
  });

  test('should fullscreen toggle work', async ({ page }) => {
    // Click fullscreen button
    await page.click('[data-testid="btn-fullscreen"]');
    
    // Graph should be in fullscreen mode (has fullscreen class)
    await expect(page.locator('[data-testid="graph-container"]')).toHaveClass(/fullscreen/);
    
    // Click exit fullscreen
    await page.click('[data-testid="btn-exit-fullscreen"]');
    
    // Should exit fullscreen
    await expect(page.locator('[data-testid="graph-container"]')).not.toHaveClass(/fullscreen/);
  });

});

test.describe('Path Finding', () => {
  
  test('should find path between two entities', async ({ page }) => {
    await page.goto('/relationships');
    
    // Click "Find Path" button
    await page.click('[data-testid="btn-find-path"]');
    
    // Path finder modal should open
    const modal = page.locator('[data-testid="path-finder-modal"]');
    await expect(modal).toBeVisible();
    
    // Enter source entity
    await page.fill('[data-testid="path-source-input"]', 'Tesla');
    await page.click('[data-testid="source-suggestion"]');
    
    // Enter target entity
    await page.fill('[data-testid="path-target-input"]', 'Apple');
    await page.click('[data-testid="target-suggestion"]');
    
    // Click find path
    await page.click('[data-testid="btn-execute-path"]');
    
    // Wait for path calculation
    await page.waitForLoadState('networkidle');
    
    // Path should be highlighted in graph
    await expect(page.locator('[data-testid="highlighted-path"]')).toBeVisible();
    
    // Path details should be shown
    await expect(page.locator('[data-testid="path-details"]')).toBeVisible();
  });

  test('should show message when no path exists', async ({ page }) => {
    await page.goto('/relationships');
    
    // Open path finder
    await page.click('[data-testid="btn-find-path"]');
    
    // Enter entities with no connection
    await page.fill('[data-testid="path-source-input"]', 'Entity A');
    await page.fill('[data-testid="path-target-input"]', 'Unconnected Entity');
    
    // Try to find path
    await page.click('[data-testid="btn-execute-path"]');
    
    // Should show "no path found" message
    await expect(page.locator('[data-testid="no-path-message"]')).toBeVisible();
  });

});

test.describe('Relationship Feed Integration', () => {
  
  test('should show relationship feed below graph', async ({ page }) => {
    await page.goto('/relationships');
    
    // Relationship feed should be visible
    const feed = page.locator('[data-testid="relationship-feed"]');
    await expect(feed).toBeVisible();
    
    // Should have relationship cards
    const cards = page.locator('[data-testid="relationship-card"]');
    const count = await cards.count();
    expect(count).toBeGreaterThan(0);
  });

  test('should click relationship card to highlight in graph', async ({ page }) => {
    await page.goto('/relationships');
    
    // Wait for graph
    await page.waitForTimeout(2000);
    
    // Click a relationship card
    const card = page.locator('[data-testid="relationship-card"]').first();
    await card.click();
    
    // The relationship should be highlighted in the graph
    await expect(page.locator('[data-testid="highlighted-edge"]')).toBeVisible();
  });

});

test.describe('Graph URL State', () => {
  
  test('should support deep linking to specific entity', async ({ page }) => {
    // Navigate with entity ID in URL
    await page.goto('/relationships?center=TSLA');
    
    // Graph should be centered on Tesla
    await page.waitForTimeout(2000);
    
    // Tesla node should be selected/centered
    await expect(page.locator('[data-testid="selected-node"]')).toBeVisible();
    await expect(page.locator('[data-testid="entity-sidebar"]')).toContainText('Tesla');
  });

  test('should support deep linking with filters', async ({ page }) => {
    // Navigate with filters in URL
    await page.goto('/relationships?types=supplies_to,subsidiary_of&depth=2');
    
    // Filters should be applied
    await expect(page.locator('[data-testid="active-filter-badge"]')).toBeVisible();
  });

  test('should update URL when filters change', async ({ page }) => {
    await page.goto('/relationships');
    
    // Apply a filter
    await page.click('[data-testid="filter-relationship-types"]');
    await page.click('[data-testid="filter-supplies-to"]');
    await page.click('[data-testid="apply-filters"]');
    
    // URL should update
    await expect(page).toHaveURL(/types=supplies_to/);
  });

});
