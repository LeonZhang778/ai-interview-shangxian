# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

AI interview simulation platform. Users upload PDF resumes, AI parses them and generates interview questions, multi-turn conversation simulates real interviews with SSE streaming, and a final evaluation report is generated.

## Repo Structure

```
ai-interview/
├── ai-interview-backend/    # FastAPI + Docker (VM deployed)
├── ai-interview-frontend/   # Vue 3 user-facing frontend (port 3000)
├── ai-interview-admin/      # Vue 3 admin panel (port 3001)
└── README.md                # Deployment guide
```

## Backend Commands

All commands run inside the VM or via `docker exec`.

**Docker Compose**: `docker-compose.yml` is a commented-out template. The active service definitions are in `docker-compose.dev.yml`. Dev mode uses `network_mode: host` (the app container shares the host network stack), so Postgres and Redis are reachable at `localhost` from the app.

```bash
# Start all services (dev)
sudo docker-compose -f docker-compose.yml -f docker-compose.dev.yml up -d --build

# View logs
sudo docker logs ai-interview-app --tail 50 -f

# Run database migrations
sudo docker exec -it ai-interview-app alembic upgrade head

# Generate a new migration
sudo docker exec -it ai-interview-app alembic revision --autogenerate -m "description"

# Create first admin
sudo docker exec -it ai-interview-app python scripts/create_first_admin.py

# Check database tables
sudo docker exec -it ai-interview-postgres psql -U demo -d ai_interview -c "\dt"

# Enter database
sudo docker exec -it ai-interview-postgres psql -U demo -d ai_interview

# Health check
curl http://localhost:8006/api/v1/config/health

# Stop all services
sudo docker-compose -f docker-compose.yml -f docker-compose.dev.yml down

# Run tests (inside the app container)
sudo docker exec -it ai-interview-app pytest -m "unit"           # unit tests only
sudo docker exec -it ai-interview-app pytest -m "not slow"       # skip slow tests (CI quick mode)
sudo docker exec -it ai-interview-app pytest -m "smoke"          # smoke tests
sudo docker exec -it ai-interview-app pytest -v                  # all tests, verbose
```

## Backend Architecture

### Docker Setup

- `Dockerfile.dev`: dev image (used by `docker-compose.dev.yml`). Runs `uvicorn` with hot reload.
- Dev mode uses `network_mode: host` — the container shares the host network, so app connects to Postgres at `localhost:5432` and Redis at `localhost:6379`.
- PostgreSQL container exposes `5434` on the host (mapped from container `5432`). Connect via `VM_IP:5434`.

### Entry Point and Request Flow

```
main.py → create_app() (app/route/route.py)
  ├── lifespan: startup/shutdown hooks (log consumer thread, Redis cleanup, DB engine disposal)
  ├── CORS middleware
  ├── Exception handlers (APIException, HTTPException, ValidationError, generic Exception)
  ├── Route registration via RouterRegistry
  ├── Mounted docs apps: /client/docs, /backoffice/docs
  └── Static files: /uploads (avatars, resumes)
```

### Layer Architecture: Router → Service → Model

```
app/api/client/v1/*.py   ← API layer: validate input, call service, return ApiResponse
app/services/client/*.py  ← Service layer: business logic, call external services (AI, Redis, email)
app/models/*.py           ← SQLAlchemy ORM models
app/schemas/client/*.py   ← Pydantic request/response schemas
```

### Dual API Design

- **Client API** (`app/api/client/`): User-facing endpoints, JWT auth with scope `client`
- **Backoffice API** (`app/api/backoffice/`): Admin endpoints, JWT auth with scope `backoffice`
- Both share the same Service layer (`app/services/client/` and `app/services/backoffice/`)

### Route Registry (`app/route/router_registry.py`)

Routes are defined as declarative config lists (`CLIENT_ROUTES`, `BACKOFFICE_ROUTES`, `COMMON_ROUTES`). Each entry is a `RouteConfig(module_path, prefix, tags)`. Adding a new API module requires only adding an entry to the relevant list — no changes to `route.py` needed.

### Unified Response Format

Every endpoint returns via `ApiResponse` ([app/schemas/response.py](ai-interview-backend/app/schemas/response.py)):
```python
{"code": 200, "message": "Success", "data": {...}}
```
Failure: `ApiResponse.failed(message, body_code, http_code, data)`
Success: `ApiResponse.success(data, message, body_code, http_code)`
Paginated: `ApiResponse.paginate(db, query, page, per_page)`

### Exception System

`APIException(code, message, status_code)` ([app/exceptions/http_exceptions.py](ai-interview-backend/app/exceptions/http_exceptions.py)) — all business errors subclass this. Predefined subtypes: `ValidationError(1001)`, `AuthenticationError(1002)`, `AuthorizationError(1003)`, `NotFoundError(1004)`, `ServerError(1005)`, `ForeignKeyViolationError(1006)`. The exception handlers in `route.py` catch them and convert to `ApiResponse.failed()`.

### Database

- PostgreSQL 16 + SQLAlchemy 2.0 async + asyncpg driver
- Connection string: `postgresql+asyncpg://{user}:{password}@{host}:{port}/{db}`
- Pool: `pool_size=20`, `pool_recycle=1800s`, `pool_pre_ping=True`
- Engine/session factory are lazily created via `get_engine()` / `get_session_local()` in [app/db/base.py](ai-interview-backend/app/db/base.py)
- `get_db()` ([app/db/session.py](ai-interview-backend/app/db/session.py)): FastAPI dependency that yields an `AsyncSession`
- `transaction(db)` ([app/db/session.py:L14](ai-interview-backend/app/db/session.py#L14)): async context manager for auto commit/rollback
- All models inherit from `BaseModel` (includes `created_at`, `updated_at` timestamps), which inherits from SQLAlchemy `Base`

### Auth (JWT)

`AuthBase` ([app/core/security.py](ai-interview-backend/app/core/security.py)):
- `create_access_token(subject, scope, expires_delta)` — HS256 JWT with `sub`, `scope`, `exp`, `jti`
- `create_refresh_token(subject)` — same but scope=`refresh`, 7-day expiry
- `verify_token(token, scope)` — decode + optional scope check
- Refresh tokens are hashed with bcrypt before storing in the `tokens` table
- Password hashing: bcrypt via `passlib`

### AI Integration

`AIService` ([app/services/client/ai_service.py](ai-interview-backend/app/services/client/ai_service.py)):
- Uses DeepSeek API via OpenAI SDK (compatible)
- Prompt engineering to force structured JSON output
- SSE streaming via `StreamingResponse` for real-time text output
- Conversation history truncated to last 6 messages to control token usage

### Background Tasks

- **Celery** ([app/core/celery_app.py](ai-interview-backend/app/core/celery_app.py)): Redis as broker and result backend. Tasks: email sending, scheduled demo job. Worker started via `celery_worker.py`.
- **Redis** ([app/services/common/redis.py](ai-interview-backend/app/services/common/redis.py)): Singleton `RedisClient` wrapping `redis.asyncio.Redis`. Methods: `set_with_ttl`, `get`, `delete`, `set_cooldown`, `check_cooldown`, `pipeline`, `brpop`.
- **Log Consumer** ([app/common/log_consumer.py](ai-interview-backend/app/common/log_consumer.py)): Uses `brpop` to consume log queue in a background daemon thread.
- **Thread Pool** ([app/services/common/thread_pool.py](ai-interview-backend/app/services/common/thread_pool.py)): For email sending via SMTP/Brevo.

### Services Directory Convention

```
app/services/
├── client/      # User-facing business logic (auth, resume, interview, AI)
├── backoffice/  # Admin business logic (admin CRUD, waiting list management)
└── common/      # Shared infrastructure (Redis, email, thread pool)
```

Service classes are instantiated at module level (e.g., `client_auth_service = ClientAuthService()`), following a singleton-ish pattern.

## Frontend Projects

Both are Vue 3 + Vite. They proxy `/api` and `/uploads` to the backend VM IP via `vite.config.js`. Start with `npm run dev`.

## Key Config

All configuration via `Settings` ([app/core/config.py](ai-interview-backend/app/core/config.py)) using `pydantic-settings`, loaded from `.env`. `CELERY_BROKER_URL` and `CELERY_RESULT_BACKEND` are auto-constructed in `__init__` from Redis host/port/password.
