# Admin Control Room Deployment

This runbook deploys the administrator backend and the hidden React dashboard.
The dashboard remains available only by directly visiting `/admin`; no public
navigation entry is added.

## Safety boundaries

- Run all Git and Compose commands from `/root/CodeMonkey/ConceptTree` unless a
  command explicitly says otherwise.
- Do not edit nginx, PostgreSQL/Supabase project settings, or unrelated Docker
  services.
- Back up `.env` and tag the currently running backend and frontend images
  before replacement.
- Apply the database migration before starting the new backend image.
- Never paste API keys, passwords, JWTs, or database URLs into logs or chat.

## 1. Preflight

```bash
cd /root/CodeMonkey
git fetch --prune origin
git status --short --branch
git rev-parse HEAD
git rev-parse origin/main

cd /root/CodeMonkey/ConceptTree
docker compose ps
curl -fsS http://127.0.0.1:8000/health
curl -fsS http://127.0.0.1:8000/health/db
```

Stop if tracked server files are modified. Existing untracked backups can stay
in place, but do not add them to Git.

## 2. Create rollback points

```bash
cd /root/CodeMonkey/ConceptTree
DEPLOY_ID="pre-admin-control-room-$(date +%Y%m%d-%H%M%S)"
cp -p .env ".env.backup.$DEPLOY_ID"

CURRENT_BACKEND_IMAGE="$(docker inspect concepttree-backend --format '{{.Image}}')"
docker image tag "$CURRENT_BACKEND_IMAGE" "concepttree-backend:rollback-$DEPLOY_ID"

CURRENT_FRONTEND_IMAGE="$(docker inspect concepttree-frontend --format '{{.Image}}')"
docker image tag "$CURRENT_FRONTEND_IMAGE" "concepttree-frontend:rollback-$DEPLOY_ID"

echo "deploy_id=$DEPLOY_ID"
docker image inspect "concepttree-backend:rollback-$DEPLOY_ID" --format 'rollback_image={{.Id}}'
docker image inspect "concepttree-frontend:rollback-$DEPLOY_ID" --format 'rollback_image={{.Id}}'
```

Keep this shell open so `DEPLOY_ID` remains available for rollback.

## 3. Update source without touching runtime secrets

```bash
cd /root/CodeMonkey
git merge --ff-only origin/main
git status --short --branch
git rev-parse HEAD
```

The checked-in `.env.example` is documentation only. Do not replace the server
`.env` with it.

## 4. Configure administrator runtime values

Add these values once to `/root/CodeMonkey/ConceptTree/.env`:

```dotenv
ADMIN_SESSION_TTL_MINUTES=30
ADMIN_COOKIE_SECURE=true
ADMIN_TRACE_RETENTION_DAYS=30
```

Then validate Compose without printing secrets:

```bash
cd /root/CodeMonkey/ConceptTree
docker compose --env-file .env config --quiet && echo "compose config ok"
```

Use `ADMIN_COOKIE_SECURE=false` only for local HTTP development. Production
HTTPS must keep it `true`.

## 5. Build the new images without replacing running containers

```bash
cd /root/CodeMonkey/ConceptTree
COMPOSE_PARALLEL_LIMIT=1 docker compose --env-file .env build backend
COMPOSE_PARALLEL_LIMIT=1 docker compose --env-file .env build frontend
```

The old containers continue running from their immutable image IDs during the
builds. Building one service at a time limits resource pressure on the server.

## 6. Apply the idempotent migration

The application and Supabase project use the same database, so this migration
must be run exactly once against that shared database before the new container
starts. Re-running it is safe because tables and indexes use `IF NOT EXISTS`.

```bash
cd /root/CodeMonkey/ConceptTree
docker compose run --rm --no-deps -T backend python - <<'PY'
from pathlib import Path
from database import get_db_context

sql = Path('/app/sql/2026-10-14_admin_control_room.sql').read_text(encoding='utf-8')
with get_db_context() as db:
    db.execute(sql)
    db.commit()
print('admin control room migration applied')
PY
```

Alternatively, apply the same checked-in SQL through the Supabase SQL editor.
Do not run both paths concurrently.

Verify only object names and RLS state:

```sql
select relname, relrowsecurity, relforcerowsecurity
from pg_class
where relname in ('user_roles', 'session_trace_events', 'admin_audit_logs')
order by relname;
```

## 7. Grant the first administrator

Replace the email literal with the existing application account that should be
the first administrator. This is the only supported bootstrap path; there is no
public role-grant API.

```sql
insert into user_roles (user_id, role, granted_by)
select id, 'admin', id
from users
where lower(email) = lower('OWNER_EMAIL@example.com')
on conflict (user_id, role) do nothing;
```

Confirm exactly one matching row before continuing:

```sql
select u.id, u.email, r.role, r.created_at
from user_roles r
join users u on u.id = r.user_id
where r.role = 'admin';
```

## 8. Replace and verify only the backend

```bash
cd /root/CodeMonkey/ConceptTree
docker compose --env-file .env up -d --no-deps backend
```

This leaves the frontend, PostgreSQL container, nginx, and other websites
untouched while the new backend is verified.

## 9. Verify the backend

```bash
timeout 60 bash -c 'until curl -fsS http://127.0.0.1:8000/health; do sleep 2; done'
echo
curl -fsS http://127.0.0.1:8000/health/db
echo
docker compose ps backend
docker compose logs --since=10m --tail=200 backend
```

Security checks:

- `/health` and `/health/db` remain public and contain only coarse status.
- `/health/metrics` returns `404`.
- `/api/admin/*` returns `401` without an admin session.
- An authenticated non-admin cannot elevate and receives `403`.
- Admin elevation requires the existing account token plus password re-entry.
- Session, trace, AI-usage, and system-health reads create audit records.

Do not continue to the frontend switch if any backend verification fails.

## 10. Replace and verify only the frontend

```bash
cd /root/CodeMonkey/ConceptTree
docker compose --env-file .env up -d --no-deps frontend

timeout 60 bash -c 'until curl -fsS http://127.0.0.1:18080/ >/dev/null; do sleep 2; done'
curl -fsS -o /dev/null -w 'local_frontend_status=%{http_code}\n' http://127.0.0.1:18080/
curl -fsS -o /dev/null -w 'public_site_status=%{http_code}\n' https://codemonkey666.space/
docker compose ps frontend backend postgres
docker compose logs --since=10m --tail=100 frontend
```

Then sign in with the explicitly granted administrator account and visit:

```text
https://codemonkey666.space/admin
```

Verify password re-entry, overview, users, sessions/traces, AI usage, system
health, mobile layout, and the lock action. Confirm that no administrator link
appears in the public learner navigation.

## 11. Rollback

If only the frontend fails, roll back only the frontend:

```bash
cd /root/CodeMonkey/ConceptTree
docker compose stop frontend
docker tag "concepttree-frontend:rollback-$DEPLOY_ID" concepttree-frontend:latest
docker compose --env-file .env up -d --no-deps --force-recreate frontend
curl -fsS http://127.0.0.1:18080/ >/dev/null && echo "frontend rollback ok"
```

If the backend fails verification, roll back only the backend:

```bash
cd /root/CodeMonkey/ConceptTree
docker compose stop backend
docker tag "concepttree-backend:rollback-$DEPLOY_ID" concepttree-backend:latest
docker compose --env-file .env up -d --no-deps --force-recreate backend
curl -fsS http://127.0.0.1:8000/health
```

The migration is additive. Normally leave its tables in place during an image
rollback; dropping them would destroy trace and audit data and is unnecessary.
