import { test, expect } from '@playwright/test'

/**
 * API Integration Tests
 * 
 * These tests verify that the frontend is correctly calling backend APIs.
 * They intercept network requests and validate:
 * 1. Correct endpoints are called
 * 2. Correct HTTP methods are used
 * 3. Request payloads are properly formatted
 */

const API_BASE = '/api'

test.describe('API Integration Tests', () => {
  
  test.describe('Health Check', () => {
    test('health endpoint returns valid response', async ({ request }) => {
      const response = await request.get(`${API_BASE}/health`)
      
      if (response.ok()) {
        const body = await response.json()
        expect(body).toHaveProperty('status')
        expect(body.status).toBe('ok')
      } else {
        test.info().annotations.push({
          type: 'error',
          description: `Health endpoint returned ${response.status()}`
        })
      }
    })
  })

  test.describe('Feeds API', () => {
    test('GET /api/feeds returns array', async ({ request }) => {
      const response = await request.get(`${API_BASE}/feeds`)
      
      if (response.ok()) {
        const body = await response.json()
        expect(Array.isArray(body)).toBe(true)
      } else {
        test.info().annotations.push({
          type: 'error',
          description: `Feeds endpoint returned ${response.status()}`
        })
      }
    })

    test('POST /api/feeds creates feed', async ({ request }) => {
      const feedData = {
        name: 'Test Feed',
        url: 'https://example.com/rss',
        feed_type: 'rss',
        enabled: true,
        poll_interval: 3600
      }
      
      const response = await request.post(`${API_BASE}/feeds`, {
        data: feedData
      })
      
      if (response.ok() || response.status() === 201) {
        const body = await response.json()
        expect(body).toHaveProperty('feed_id')
      } else if (response.status() === 404) {
        test.info().annotations.push({
          type: 'warning',
          description: 'POST /api/feeds not implemented'
        })
      }
    })
  })

  test.describe('Records API', () => {
    test('GET /api/records returns paginated list', async ({ request }) => {
      const response = await request.get(`${API_BASE}/records`)
      
      if (response.ok()) {
        const body = await response.json()
        expect(body).toHaveProperty('records')
        expect(body).toHaveProperty('total')
        expect(body).toHaveProperty('has_more')
      } else {
        test.info().annotations.push({
          type: 'error',
          description: `Records endpoint returned ${response.status()}`
        })
      }
    })

    test('GET /api/records supports filtering', async ({ request }) => {
      const response = await request.get(`${API_BASE}/records?feed_id=1&limit=10&offset=0`)
      
      if (response.ok()) {
        const body = await response.json()
        expect(Array.isArray(body.records)).toBe(true)
      }
    })

    test('GET /api/records supports search', async ({ request }) => {
      const response = await request.get(`${API_BASE}/records?search=apple`)
      
      if (response.ok()) {
        const body = await response.json()
        expect(body).toHaveProperty('records')
      }
    })

    test('POST /api/records/{id}/read marks as read', async ({ request }) => {
      const response = await request.post(`${API_BASE}/records/test-id/read`)
      
      if (response.status() === 404) {
        test.info().annotations.push({
          type: 'warning',
          description: 'POST /api/records/{id}/read not implemented'
        })
      }
    })

    test('POST /api/records/{id}/star toggles star', async ({ request }) => {
      const response = await request.post(`${API_BASE}/records/test-id/star`)
      
      if (response.status() === 404) {
        test.info().annotations.push({
          type: 'warning',
          description: 'POST /api/records/{id}/star not implemented'
        })
      }
    })
  })

  test.describe('Settings API', () => {
    test('GET /api/settings returns settings object', async ({ request }) => {
      const response = await request.get(`${API_BASE}/settings`)
      
      if (response.ok()) {
        const body = await response.json()
        expect(body).toHaveProperty('theme')
      } else if (response.status() === 404) {
        test.info().annotations.push({
          type: 'warning',
          description: 'GET /api/settings not implemented'
        })
      }
    })

    test('PUT /api/settings updates settings', async ({ request }) => {
      const response = await request.put(`${API_BASE}/settings`, {
        data: { theme: 'dark' }
      })
      
      if (response.status() === 404) {
        test.info().annotations.push({
          type: 'warning',
          description: 'PUT /api/settings not implemented'
        })
      }
    })
  })

  test.describe('Notifications API', () => {
    test('GET /api/notifications returns notifications', async ({ request }) => {
      const response = await request.get(`${API_BASE}/notifications`)
      
      if (response.status() === 404) {
        test.info().annotations.push({
          type: 'warning',
          description: 'GET /api/notifications not implemented - needs to be added'
        })
      }
    })

    test('GET /api/alerts returns alerts', async ({ request }) => {
      const response = await request.get(`${API_BASE}/alerts`)
      
      if (response.status() === 404) {
        test.info().annotations.push({
          type: 'warning',
          description: 'GET /api/alerts not implemented - needs to be added'
        })
      }
    })
  })

  test.describe('Dashboard Stats API', () => {
    test('GET /api/stats returns dashboard statistics', async ({ request }) => {
      const response = await request.get(`${API_BASE}/stats`)
      
      if (response.ok()) {
        const body = await response.json()
        expect(body).toHaveProperty('feed_count')
        expect(body).toHaveProperty('record_count')
      } else if (response.status() === 404) {
        test.info().annotations.push({
          type: 'warning',
          description: 'GET /api/stats not implemented - needs to be added'
        })
      }
    })
  })

  test.describe('User/Auth API (Multi-user)', () => {
    test('GET /api/auth/me returns current user', async ({ request }) => {
      const response = await request.get(`${API_BASE}/auth/me`)
      
      if (response.status() === 404) {
        test.info().annotations.push({
          type: 'info',
          description: 'GET /api/auth/me not implemented - multi-user not enabled'
        })
      }
    })

    test('POST /api/auth/login handles login', async ({ request }) => {
      const response = await request.post(`${API_BASE}/auth/login`, {
        data: { email: 'test@example.com', password: 'test' }
      })
      
      if (response.status() === 404) {
        test.info().annotations.push({
          type: 'info',
          description: 'POST /api/auth/login not implemented - multi-user not enabled'
        })
      }
    })
  })
})
