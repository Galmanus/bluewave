# Routing & Workflows — Bluewave MVP

## 1. REST API Endpoints (FastAPI Backend)

All routes are prefixed with `/api/v1`. Protected routes require `Authorization: Bearer <token>`.

### 1.1 Authentication

| Method | Endpoint | Auth | Description |
|--------|----------|------|-------------|
| `POST` | `/auth/register` | No | Register a new tenant + admin user |
| `POST` | `/auth/login` | No | Returns access + refresh tokens |
| `POST` | `/auth/refresh` | Cookie | Rotates refresh token, returns new access token |
| `POST` | `/auth/logout` | Yes | Invalidates refresh token |

#### Request/Response Examples

**POST /auth/login**
```
Request:  { "email": "...", "password": "..." }
Response: { "access_token": "...", "token_type": "bearer" }
          + Set-Cookie: refresh_token=...; HttpOnly; Secure; SameSite=Strict
```

**POST /auth/register**
```
Request:  { "tenant_name": "Agency X", "email": "...", "password": "...", "full_name": "..." }
Response: { "tenant_id": "uuid", "user_id": "uuid", "message": "Tenant created" }
```

---

### 1.2 Users (Tenant-Scoped)

| Method | Endpoint | Role | Description |
|--------|----------|------|-------------|
| `GET` | `/users/me` | Any | Current user profile |
| `GET` | `/users` | Admin | List users in tenant |
| `POST` | `/users` | Admin | Invite user to tenant |
| `PATCH` | `/users/{id}` | Admin | Update user role |
| `DELETE` | `/users/{id}` | Admin | Remove user from tenant |

---

### 1.3 Media Assets (Tenant-Scoped)

| Method | Endpoint | Role | Description |
|--------|----------|------|-------------|
| `GET` | `/assets` | Any | List assets (filterable: `?status=draft&page=1&size=20`) |
| `GET` | `/assets/{id}` | Any | Single asset with AI-generated metadata |
| `POST` | `/assets` | Editor+ | Upload file (multipart/form-data) |
| `PATCH` | `/assets/{id}` | Editor+ | Update caption, hashtags, or metadata |
| `DELETE` | `/assets/{id}` | Admin | Soft-delete asset |

**POST /assets** flow:
```
Upload file → validate type/size → save to disk → create DB record (status=draft)
           → enqueue background task: generate_caption + generate_hashtags
           → return 202 { "asset_id": "uuid", "status": "processing" }
```

The background task is wrapped with `@retry(max_retries=3, base_delay=1.0)` — if AI generation or the DB commit fails transiently, it retries with exponential backoff (1s → 2s → 4s ± jitter). After 3 failed attempts, `RetryExhausted` is raised and logged.

---

### 1.4 Approval Workflow (Tenant-Scoped)

| Method | Endpoint | Role | Description |
|--------|----------|------|-------------|
| `POST` | `/assets/{id}/submit` | Editor+ | Move from `draft` → `pending_approval` |
| `POST` | `/assets/{id}/approve` | Admin | Move from `pending_approval` → `approved` |
| `POST` | `/assets/{id}/reject` | Admin | Move from `pending_approval` → `draft` (with comment) |

#### State Machine

```
                 submit()            approve()
   ┌───────┐  ──────────►  ┌──────────────┐  ──────────►  ┌──────────┐
   │ DRAFT │                │   PENDING    │                │ APPROVED │
   └───────┘  ◄──────────  │   APPROVAL   │                └──────────┘
                 reject()   └──────────────┘
```

- `reject()` returns the asset to `DRAFT` and attaches an admin comment explaining why.
- Only the asset owner (or admin) can call `submit()`.
- Only admins can call `approve()` or `reject()`.

---

### 1.5 AI Simulation

| Method | Endpoint | Role | Description |
|--------|----------|------|-------------|
| `POST` | `/ai/caption` | Editor+ | Generate caption for a given asset |
| `POST` | `/ai/hashtags` | Editor+ | Generate hashtags for a given asset |

These are also called automatically as background tasks after upload. The manual endpoints allow re-generation.

---

### 1.6 Retry & Error Handling

Both layers implement exponential backoff with ±20% jitter to handle transient failures:

**Frontend (Axios interceptor — `lib/api.ts`):**
- Retries 408, 429, 500, 502, 503, 504 + network errors up to 3 times (500ms → 1s → 2s).
- On 401: automatically refreshes the access token via `/auth/refresh` and retries the original request.
- After all retries exhausted: shows error toast via `react-hot-toast`.

**Backend (`@retry` decorator — `app/core/retry.py`):**
- Configurable decorator for both sync and async callables.
- Parameters: `max_retries`, `base_delay`, `max_delay`, `jitter_factor`, `retryable` exception types.
- Raises `RetryExhausted` (with `.attempts` count and chained `__cause__`) when all attempts fail.
- Currently applied to the `_run_ai_stubs()` background task; ready for use on real AI provider calls.

---

## 2. Frontend Routes (React Router)

| Path | Component | Auth | Description |
|------|-----------|------|-------------|
| `/login` | `LoginPage` | No | Email + password login form |
| `/register` | `RegisterPage` | No | Tenant + admin user registration |
| `/` | `DashboardPage` | Yes | Redirect to `/assets` |
| `/assets` | `AssetListPage` | Yes | Grid/list view of media assets with status filters |
| `/assets/:id` | `AssetDetailPage` | Yes | Preview, metadata, AI captions, approval actions |
| `/assets/upload` | `UploadPage` | Editor+ | Drag-and-drop upload form |
| `/team` | `TeamPage` | Admin | User management within the tenant |
| `/settings` | `SettingsPage` | Admin | Tenant settings (name, logo, etc.) |

### Route Protection

```
<BrowserRouter>
  <Route path="/login" element={<LoginPage />} />
  <Route path="/register" element={<RegisterPage />} />
  <Route element={<AuthGuard />}>          ← redirects to /login if no valid token
    <Route element={<AppLayout />}>        ← sidebar + header shell
      <Route path="/" element={<Navigate to="/assets" />} />
      <Route path="/assets" element={<AssetListPage />} />
      <Route path="/assets/:id" element={<AssetDetailPage />} />
      <Route element={<RoleGuard role="editor" />}>
        <Route path="/assets/upload" element={<UploadPage />} />
      </Route>
      <Route element={<RoleGuard role="admin" />}>
        <Route path="/team" element={<TeamPage />} />
        <Route path="/settings" element={<SettingsPage />} />
      </Route>
    </Route>
  </Route>
</BrowserRouter>
```

---

## 3. Data Flow Summary

```
User Action           Frontend                   Backend                    Database
───────────          ─────────                  ─────────                  ─────────
Login            →   POST /auth/login       →   verify password        →   users table
                 ←   store token in memory   ←   JWT { tenant_id, role }

Upload Asset     →   POST /assets (form)    →   save file              →   INSERT media_assets
                 ←   asset_id + "processing" ←  background: AI stubs   →   UPDATE caption/tags
                                                 (retries 3× on failure)

Submit for       →   POST /assets/:id/submit →  validate owner         →   UPDATE status
Approval         ←   updated asset           ←  "pending_approval"

Approve          →   POST /assets/:id/approve → validate admin role    →   UPDATE status
                 ←   updated asset            ← "approved"
```
