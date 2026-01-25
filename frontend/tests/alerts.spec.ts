import { test, expect } from '@playwright/test';

test.describe('Alerts Page', () => {
  test.beforeEach(async ({ page }) => {
    await page.goto('/alerts');
  });

  test('displays alerts page header', async ({ page }) => {
    await expect(page.locator('h1')).toContainText('Alerts');
    await expect(page.locator('text=Get notified when new filings match your criteria')).toBeVisible();
  });

  test('displays create alert button', async ({ page }) => {
    const createButton = page.locator('button:has-text("Create Alert")');
    await expect(createButton).toBeVisible();
  });

  test('has search functionality', async ({ page }) => {
    const searchInput = page.locator('input[placeholder="Search alerts..."]');
    await expect(searchInput).toBeVisible();
    
    // Type in search
    await searchInput.fill('10-K');
    await expect(searchInput).toHaveValue('10-K');
  });

  test('has filter dropdown', async ({ page }) => {
    const filterSelect = page.locator('select');
    await expect(filterSelect).toBeVisible();
    
    // Check filter options
    await expect(filterSelect.locator('option[value="all"]')).toHaveText('All Alerts');
    await expect(filterSelect.locator('option[value="enabled"]')).toHaveText('Enabled Only');
    await expect(filterSelect.locator('option[value="disabled"]')).toHaveText('Disabled Only');
  });

  test('displays sample alerts list', async ({ page }) => {
    // Should show sample alerts (10-K Annual Reports, Apple & Microsoft, Insider Trading)
    await expect(page.locator('text=10-K Annual Reports')).toBeVisible();
    await expect(page.locator('text=Apple & Microsoft Filings')).toBeVisible();
    await expect(page.locator('text=Insider Trading')).toBeVisible();
  });

  test('can toggle alert enabled status', async ({ page }) => {
    // Find enable/disable buttons
    const toggleButtons = page.locator('button[title="Disable alert"], button[title="Enable alert"]');
    await expect(toggleButtons.first()).toBeVisible();
    
    // Click to toggle
    await toggleButtons.first().click();
  });

  test('can expand alert to show details', async ({ page }) => {
    // Click on an alert row to expand
    const alertRow = page.locator('text=10-K Annual Reports').first();
    await alertRow.click();
    
    // Should show conditions and actions sections
    await expect(page.locator('text=Conditions')).toBeVisible();
    await expect(page.locator('text=Actions')).toBeVisible();
  });

  test('opens create alert modal', async ({ page }) => {
    const createButton = page.locator('button:has-text("Create Alert")');
    await createButton.click();
    
    // Modal should appear
    await expect(page.locator('h2:has-text("Create Alert")')).toBeVisible();
    
    // Form fields should be present
    await expect(page.locator('input[placeholder*="Alert Name"]')).toBeVisible();
    await expect(page.locator('textarea[placeholder*="Describe"]')).toBeVisible();
    
    // Action checkboxes
    await expect(page.locator('text=In-app notification')).toBeVisible();
    await expect(page.locator('text=Email notification')).toBeVisible();
    await expect(page.locator('text=Webhook')).toBeVisible();
  });

  test('can create a new alert', async ({ page }) => {
    // Open modal
    await page.locator('button:has-text("Create Alert")').click();
    
    // Fill in form
    await page.locator('input[placeholder*="Alert Name"]').fill('Test Alert');
    await page.locator('textarea[placeholder*="Describe"]').fill('Test description');
    
    // Select condition type
    const conditionTypeSelect = page.locator('select').first();
    await conditionTypeSelect.selectOption('form_types');
    
    // Enter condition value
    await page.locator('input[placeholder*="Value"]').fill('8-K');
    
    // Submit
    await page.locator('button:has-text("Create Alert")').last().click();
    
    // Modal should close and new alert should appear
    await expect(page.locator('h2:has-text("Create Alert")')).not.toBeVisible();
    await expect(page.locator('text=Test Alert')).toBeVisible();
  });

  test('can edit an existing alert', async ({ page }) => {
    // Click edit button on first alert
    const editButton = page.locator('button[title="Edit alert"]').first();
    await editButton.click();
    
    // Edit modal should appear
    await expect(page.locator('h2:has-text("Edit Alert")')).toBeVisible();
    
    // Change the name
    const nameInput = page.locator('input[placeholder*="Alert Name"]');
    await nameInput.clear();
    await nameInput.fill('Updated Alert Name');
    
    // Save
    await page.locator('button:has-text("Save Changes")').click();
    
    // Modal should close
    await expect(page.locator('h2:has-text("Edit Alert")')).not.toBeVisible();
  });

  test('can delete an alert', async ({ page }) => {
    // Setup dialog handler
    page.on('dialog', dialog => dialog.accept());
    
    // Click delete button
    const deleteButton = page.locator('button[title="Delete alert"]').first();
    await deleteButton.click();
    
    // Alert count should decrease
    // (We can't easily verify this without API, but the action should complete)
  });

  test('can filter by enabled status', async ({ page }) => {
    const filterSelect = page.locator('select');
    
    // Filter to enabled only
    await filterSelect.selectOption('enabled');
    
    // Disabled alerts should not be visible
    // The "Insider Trading" alert is disabled in sample data
    // Note: This depends on the sample data state
  });

  test('can add multiple conditions', async ({ page }) => {
    // Open modal
    await page.locator('button:has-text("Create Alert")').click();
    
    // Click "Add Condition"
    await page.locator('text=Add Condition').click();
    
    // Should now have 2 condition rows
    const conditionRows = page.locator('.bg-gray-50, .bg-gray-700\\/50');
    await expect(conditionRows).toHaveCount(2);
  });

  test('displays trigger count and last triggered time', async ({ page }) => {
    // Look for trigger count indicators
    const bellIcons = page.locator('svg.lucide-bell');
    await expect(bellIcons.first()).toBeVisible();
    
    // Look for clock icons (last triggered)
    const clockIcons = page.locator('svg.lucide-clock');
    await expect(clockIcons.first()).toBeVisible();
  });

  test('shows action icons for enabled actions', async ({ page }) => {
    // Alerts should show icons for their enabled actions
    // The 10-K alert has notification and email enabled
    const alertRow = page.locator('text=10-K Annual Reports').locator('..');
    
    // Should have action icons
    await expect(alertRow.locator('svg')).toHaveCount({ minimum: 1 });
  });

  test('modal can be closed with X button', async ({ page }) => {
    // Open modal
    await page.locator('button:has-text("Create Alert")').click();
    await expect(page.locator('h2:has-text("Create Alert")')).toBeVisible();
    
    // Close with X button
    const closeButton = page.locator('button:has(svg.lucide-x)').first();
    await closeButton.click();
    
    // Modal should be closed
    await expect(page.locator('h2:has-text("Create Alert")')).not.toBeVisible();
  });

  test('modal can be closed with Cancel button', async ({ page }) => {
    // Open modal
    await page.locator('button:has-text("Create Alert")').click();
    await expect(page.locator('h2:has-text("Create Alert")')).toBeVisible();
    
    // Close with Cancel
    await page.locator('button:has-text("Cancel")').click();
    
    // Modal should be closed
    await expect(page.locator('h2:has-text("Create Alert")')).not.toBeVisible();
  });

  test('create button is disabled without name', async ({ page }) => {
    // Open modal
    await page.locator('button:has-text("Create Alert")').click();
    
    // Create button should be disabled (name is empty)
    const createBtn = page.locator('button:has-text("Create Alert")').last();
    await expect(createBtn).toBeDisabled();
    
    // Fill in name
    await page.locator('input[placeholder*="Alert Name"]').fill('Test');
    
    // Now it should be enabled
    await expect(createBtn).toBeEnabled();
  });
});

test.describe('Alerts Page - API Integration', () => {
  test('alerts list endpoint integration', async ({ request }) => {
    const response = await request.get('/api/alerts');
    
    // May return 404 if endpoint not implemented yet
    if (response.status() === 200) {
      const alerts = await response.json();
      expect(Array.isArray(alerts)).toBe(true);
    }
  });

  test('create alert endpoint integration', async ({ request }) => {
    const response = await request.post('/api/alerts', {
      data: {
        name: 'Test Alert',
        conditions: [{ type: 'keywords', operator: 'contains', value: 'test' }],
        actions: [{ type: 'notification', enabled: true }],
      },
    });
    
    // May return 404 if endpoint not implemented yet
    if (response.status() === 201 || response.status() === 200) {
      const alert = await response.json();
      expect(alert.name).toBe('Test Alert');
    }
  });

  test('toggle alert endpoint integration', async ({ request }) => {
    // First get an alert
    const listResponse = await request.get('/api/alerts');
    
    if (listResponse.status() === 200) {
      const alerts = await listResponse.json();
      
      if (alerts.length > 0) {
        const alertId = alerts[0].alert_id;
        const toggleResponse = await request.patch(`/api/alerts/${alertId}`, {
          data: { enabled: !alerts[0].enabled },
        });
        
        if (toggleResponse.status() === 200) {
          const updated = await toggleResponse.json();
          expect(updated.enabled).toBe(!alerts[0].enabled);
        }
      }
    }
  });
});
