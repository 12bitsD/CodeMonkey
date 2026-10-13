# Admin Control Room Coding Plan

## Objective

Build a hidden, read-only administrator control room for product analytics, user and learning-session inspection, persistent session traces, AI usage/cost visibility, system health, and audited access. The public application must not expose an admin navigation entry. Authorization is enforced by the backend, never by route secrecy.

Frontend dashboard implementation is intentionally deferred. This plan records its information architecture and visual direction so the backend contracts can be built first.

## Scope

### In scope

- Database-backed administrator roles.
- Short-lived administrator elevation after password re-entry.
- Administrator-only overview, time-series, users, sessions, traces, AI usage, and system-health endpoints.
- Append-only deep-learning session trace events.
- Administrator access audit logs.
- RLS hardening for every new table.
- Backend tests and deployment documentation.
- Dashboard UX specification.

### Deferred

- Admin React pages and charts.
- User deletion, suspension, impersonation, or content mutation.
- Bulk actions and quick actions.
- Automatic production migration or deployment.

## Dashboard design record

Use menu pattern 4 (icon rail with a large page title) as the primary structure and pattern 5 (hover labels) as supporting behavior.

- Hidden route: `/admin`; no link in the public app.
- Narrow left icon rail with a dark rounded active state.
- Hover tooltips reveal menu labels.
- Large page name at the top-left of the content area.
- Date-range selector next to the title.
- Pages: Overview, Users, Sessions, Traces, AI Usage, System.
- Light, low-noise surface; black/white/gray base with a warm orange accent.
- Large rounded cards, subtle borders, compact data tables, timeline/waterfall trace details.
- Desktop-first; collapse the rail on smaller screens.
- No quick actions in v1. Export can be considered later.

## Architecture

Keep four deep modules behind small interfaces:

1. **Admin access module** — administrator elevation, authorization, and revocation.
2. **Admin analytics module** — overview, users, sessions, AI usage, and health queries.
3. **Trace module** — best-effort event recording and session-trace reads.
4. **Admin audit module** — append-only records of sensitive administrator reads.

The frontend will call only `/api/admin/*`. It never decides whether a user is an administrator.

## Database changes

Add an idempotent migration named `backend/sql/2026-10-14_admin_control_room.sql` and keep `backend/schema.sql` aligned.

### `user_roles`

- `user_id`
- `role` (`admin` initially)
- `created_at`
- `granted_by`

No public role-granting endpoint is permitted. Bootstrap administrators through a reviewed SQL statement or server command.

### `session_trace_events`

- Identity: `id`, `session_id`, `user_id`, `request_id`
- Classification: `event_type`, `event_name`, `status`
- Timing: `started_at`, `ended_at`, `duration_ms`, `created_at`
- AI usage: `provider`, `model`, `input_tokens`, `output_tokens`, `estimated_cost_usd`, `retry_count`
- Diagnostics: `error_code`, `attributes`, `redacted_input`, `redacted_output`

### `admin_audit_logs`

- `id`, `admin_user_id`, `action`
- `resource_type`, `resource_id`, `request_id`
- `metadata`, `created_at`

All new tables must enable and force RLS and revoke privileges from `PUBLIC`, `anon`, and `authenticated`.

## Administrator authentication

1. Authenticate through the existing user login.
2. Re-enter the account password at the hidden admin route.
3. Verify the database-backed `admin` role.
4. Issue a 30-minute admin-scoped JWT in an `HttpOnly`, `Secure`, `SameSite=Strict` cookie.
5. Re-check the database role on each admin request so revocation is immediate.
6. Audit sensitive reads.

Configuration:

```dotenv
ADMIN_SESSION_TTL_MINUTES=30
ADMIN_COOKIE_SECURE=true
ADMIN_TRACE_RETENTION_DAYS=30
ADMIN_HTTP_TRACE_SAMPLE_RATE=0.1
```

## Backend endpoints

```text
POST   /api/admin/auth/session
DELETE /api/admin/auth/session
GET    /api/admin/me

GET /api/admin/overview
GET /api/admin/timeseries
GET /api/admin/users
GET /api/admin/users/{user_id}
GET /api/admin/sessions
GET /api/admin/sessions/{session_id}
GET /api/admin/sessions/{session_id}/trace
GET /api/admin/ai-usage
GET /api/admin/system-health
```

Lists use bounded cursor pagination. Email addresses are masked by default. Responses never include password hashes, JWTs, API keys, or database connection details.

## Trace collection

- Record session create/resume, initialization, state changes, messages, commands, tests, completion, abandonment, and failures.
- Record AI provider/model, latency, token usage, retries, error codes, and cost estimates.
- Record image-decision, image-generation, and image-storage stages separately.
- Store only redacted previews and structural metadata by default.
- AI calls and errors are recorded at 100%; successful generic HTTP requests may be sampled at 10%.
- Trace persistence is best effort and must never fail the learner's main request.
- Trace details default to 30-day retention; aggregates may be retained longer.

## Incremental commits

1. **docs: record admin control room contracts and dashboard direction**
2. **feat: add admin schema with RLS hardening**
3. **feat: add administrator elevation and authorization**
4. **feat: add admin overview and user analytics**
5. **feat: add admin session queries**
6. **feat: persist deep-learning session traces**
7. **feat: expose AI usage and system health**
8. **test: harden admin isolation, auditing, and trace failure behavior**

## Verification criteria

- Anonymous requests receive `401` and authenticated non-admin users receive `403`.
- A forged role claim does not grant access.
- Admin elevation expires and can be revoked.
- No secret-bearing columns appear in responses.
- Date filters and bounded pagination are enforced.
- Trace events remain ordered and trace-storage failure does not interrupt learning.
- Every full user/session/trace read creates an audit entry.
- Public `/health` remains available while detailed metrics are admin-only.
- New tables pass RLS/revocation tests.
- Relevant backend tests pass before any migration is proposed for production.

## Deployment order

1. Merge reviewed code.
2. Back up database metadata and apply the idempotent migration.
3. Grant the first administrator role explicitly.
4. Configure admin cookie/session environment values.
5. Deploy the backend only and verify admin endpoints.
6. Implement and deploy the hidden frontend dashboard in a later phase.

