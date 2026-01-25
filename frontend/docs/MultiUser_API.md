# Multi-User Support - API Requirements

## Overview

Multi-user support enables multiple users to have their own accounts, feeds, read state, and settings.

## Current Status: ❌ Single User Only

The current implementation has no user authentication or user-scoped data.

---

## Authentication Endpoints

### 1. Register

**Endpoint:** `POST /api/auth/register`

**Request Body:**
```json
{
  "email": "user@example.com",
  "password": "securepassword",
  "name": "John Doe"
}
```

**Response:** `201 Created`
```json
{
  "user_id": "uuid",
  "email": "user@example.com",
  "name": "John Doe",
  "created_at": "2026-01-27T12:00:00Z"
}
```

**Validation:**
- Email must be valid and unique
- Password must be at least 8 characters
- Name is optional

---

### 2. Login

**Endpoint:** `POST /api/auth/login`

**Request Body:**
```json
{
  "email": "user@example.com",
  "password": "securepassword"
}
```

**Response:**
```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIs...",
  "token_type": "bearer",
  "expires_in": 3600,
  "refresh_token": "dGhpcyBpcyBhIHJlZnJlc2g...",
  "user": {
    "user_id": "uuid",
    "email": "user@example.com",
    "name": "John Doe"
  }
}
```

**Error Responses:**
- `401 Unauthorized` - Invalid credentials
- `403 Forbidden` - Account disabled

---

### 3. Refresh Token

**Endpoint:** `POST /api/auth/refresh`

**Request Body:**
```json
{
  "refresh_token": "dGhpcyBpcyBhIHJlZnJlc2g..."
}
```

**Response:** Same as login

---

### 4. Logout

**Endpoint:** `POST /api/auth/logout`

**Headers:** `Authorization: Bearer <token>`

**Response:** `204 No Content`

---

### 5. Get Current User

**Endpoint:** `GET /api/auth/me`

**Headers:** `Authorization: Bearer <token>`

**Response:**
```json
{
  "user_id": "uuid",
  "email": "user@example.com",
  "name": "John Doe",
  "role": "user",
  "created_at": "2026-01-27T12:00:00Z",
  "settings": {
    "theme": "dark",
    "email_notifications": true
  }
}
```

---

### 6. Update Profile

**Endpoint:** `PUT /api/auth/me`

**Request Body:**
```json
{
  "name": "John Smith",
  "email": "newemail@example.com"
}
```

**Response:** Updated user object

---

### 7. Change Password

**Endpoint:** `POST /api/auth/change-password`

**Request Body:**
```json
{
  "current_password": "oldpassword",
  "new_password": "newpassword"
}
```

**Response:** `204 No Content`

---

### 8. Forgot Password

**Endpoint:** `POST /api/auth/forgot-password`

**Request Body:**
```json
{
  "email": "user@example.com"
}
```

**Response:** `202 Accepted` (always, to prevent email enumeration)

---

### 9. Reset Password

**Endpoint:** `POST /api/auth/reset-password`

**Request Body:**
```json
{
  "token": "reset-token-from-email",
  "new_password": "newpassword"
}
```

**Response:** `204 No Content`

---

## User Management Endpoints (Admin)

### 10. List Users

**Endpoint:** `GET /api/users`

**Required Role:** `admin`

**Response:**
```json
{
  "users": [
    {
      "user_id": "uuid",
      "email": "user@example.com",
      "name": "John Doe",
      "role": "user",
      "status": "active",
      "created_at": "2026-01-27T12:00:00Z",
      "last_login_at": "2026-01-27T11:00:00Z"
    }
  ],
  "total": 25
}
```

---

### 11. Create User (Admin)

**Endpoint:** `POST /api/users`

**Required Role:** `admin`

**Request Body:**
```json
{
  "email": "newuser@example.com",
  "password": "temppassword",
  "name": "New User",
  "role": "user"
}
```

---

### 12. Update User (Admin)

**Endpoint:** `PUT /api/users/{user_id}`

**Required Role:** `admin`

**Request Body:**
```json
{
  "role": "admin",
  "status": "disabled"
}
```

---

### 13. Delete User (Admin)

**Endpoint:** `DELETE /api/users/{user_id}`

**Required Role:** `admin`

**Response:** `204 No Content`

---

## Database Schema

```sql
-- Users table
CREATE TABLE users (
    user_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    email TEXT NOT NULL UNIQUE,
    password_hash TEXT NOT NULL,
    name TEXT,
    role TEXT NOT NULL DEFAULT 'user',  -- 'user', 'admin'
    status TEXT NOT NULL DEFAULT 'active',  -- 'active', 'disabled', 'pending'
    email_verified BOOLEAN DEFAULT false,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    last_login_at TIMESTAMPTZ
);

-- Sessions table (for refresh tokens)
CREATE TABLE sessions (
    session_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID REFERENCES users(user_id) ON DELETE CASCADE,
    refresh_token_hash TEXT NOT NULL,
    user_agent TEXT,
    ip_address INET,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    expires_at TIMESTAMPTZ NOT NULL,
    revoked_at TIMESTAMPTZ
);

-- Password reset tokens
CREATE TABLE password_resets (
    token_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID REFERENCES users(user_id) ON DELETE CASCADE,
    token_hash TEXT NOT NULL,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    expires_at TIMESTAMPTZ NOT NULL,
    used_at TIMESTAMPTZ
);

-- Indexes
CREATE INDEX idx_sessions_user ON sessions(user_id);
CREATE INDEX idx_sessions_token ON sessions(refresh_token_hash);
CREATE INDEX idx_password_resets_token ON password_resets(token_hash);
```

---

## User-Scoped Data Changes

All existing tables need a `user_id` column:

```sql
-- Add user_id to feeds (shared feeds possible with NULL user_id)
ALTER TABLE feeds ADD COLUMN user_id UUID REFERENCES users(user_id);
ALTER TABLE feeds ADD COLUMN is_shared BOOLEAN DEFAULT false;

-- read_state is user-specific
ALTER TABLE read_state ADD COLUMN user_id UUID REFERENCES users(user_id);
ALTER TABLE read_state DROP CONSTRAINT read_state_pkey;
ALTER TABLE read_state ADD PRIMARY KEY (user_id, record_id);

-- settings are user-specific
ALTER TABLE settings ADD COLUMN user_id UUID REFERENCES users(user_id);
ALTER TABLE settings DROP CONSTRAINT settings_pkey;
ALTER TABLE settings ADD PRIMARY KEY (user_id, key);

-- notifications are user-specific
ALTER TABLE notifications ADD COLUMN user_id UUID REFERENCES users(user_id);

-- alerts are user-specific
ALTER TABLE alerts ADD COLUMN user_id UUID REFERENCES users(user_id);
```

---

## API Changes for User Scope

All existing endpoints need to filter by user:

```python
# Before (single user)
@app.get("/api/feeds")
async def list_feeds():
    return db.query(Feed).all()

# After (multi-user)
@app.get("/api/feeds")
async def list_feeds(current_user: User = Depends(get_current_user)):
    return db.query(Feed).filter(
        (Feed.user_id == current_user.user_id) | 
        (Feed.is_shared == True)
    ).all()
```

---

## Frontend Changes

### Authentication Context

```typescript
// src/contexts/AuthContext.tsx
interface AuthContextType {
  user: User | null
  isAuthenticated: boolean
  isLoading: boolean
  login: (email: string, password: string) => Promise<void>
  logout: () => void
  register: (email: string, password: string, name: string) => Promise<void>
}
```

### Protected Routes

```typescript
// src/App.tsx
<Routes>
  <Route path="/login" element={<LoginPage />} />
  <Route path="/register" element={<RegisterPage />} />
  <Route path="/" element={
    <ProtectedRoute>
      <AdminLayout />
    </ProtectedRoute>
  }>
    <Route path="dashboard" element={<DashboardPage />} />
    {/* ... */}
  </Route>
</Routes>
```

### API Client Token Handling

```typescript
// src/api/index.ts - Already implemented!
api.interceptors.request.use((config) => {
  const token = localStorage.getItem('token')
  if (token) {
    config.headers.Authorization = `Bearer ${token}`
  }
  return config
})
```

---

## Implementation Checklist

### Backend

- [ ] Add users table
- [ ] Add sessions table
- [ ] Add password_resets table
- [ ] Implement password hashing (bcrypt/argon2)
- [ ] Implement JWT token generation
- [ ] Implement all auth endpoints
- [ ] Add authentication middleware
- [ ] Add authorization (role checking)
- [ ] Add user_id to all relevant tables
- [ ] Update all queries to filter by user
- [ ] Add admin endpoints

### Frontend

- [ ] Create AuthContext provider
- [ ] Create LoginPage
- [ ] Create RegisterPage
- [ ] Create ForgotPasswordPage
- [ ] Create ProtectedRoute component
- [ ] Update API client for token handling
- [ ] Add logout button to header
- [ ] Add user profile dropdown
- [ ] Create ProfilePage
- [ ] Create admin UsersPage (if admin)

---

## Roles & Permissions

| Permission | User | Admin |
|------------|------|-------|
| View own feeds | ✅ | ✅ |
| Create feeds | ✅ | ✅ |
| View shared feeds | ✅ | ✅ |
| Create shared feeds | ❌ | ✅ |
| View all users | ❌ | ✅ |
| Create users | ❌ | ✅ |
| Disable users | ❌ | ✅ |
| View system stats | ❌ | ✅ |
