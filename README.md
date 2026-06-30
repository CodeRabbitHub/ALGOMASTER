# AlgoMaster

A self-hosted, full-stack platform for structured DSA practice. Work through 600 LeetCode-style problems organised across 59 algorithm categories, run your code in a sandboxed Python executor, track your progress with time-series analytics, and get personalised coaching from an AI layer powered by GPT-4o.

Everything runs locally via Docker Compose — your data stays on your machine.

---

## Table of Contents

- [Features](#features)
- [Architecture](#architecture)
- [Prerequisites](#prerequisites)
- [Quick Start](#quick-start)
- [Environment Variables](#environment-variables)
- [Frontend Build](#frontend-build)
- [Docker Services](#docker-services)
- [First Run](#first-run)
- [AI Features](#ai-features)
- [Admin Tools](#admin-tools)
- [Local Development](#local-development)
- [API Reference](#api-reference)
- [Database Schema](#database-schema)
- [Code Runner Security](#code-runner-security)
- [Common Commands](#common-commands)
- [Troubleshooting](#troubleshooting)

---

## Features

**Problem Tracker**
- 600 problems across 59 categories (Arrays, DP, Graphs, Trees, etc.) mirroring the AlgoMaster curriculum
- Per-problem progress: solve status, attempt count, time spent, confidence rating (0–5), personal notes, starred flag
- Filter by category, difficulty, and status; full-text search; sort by any column
- Problem descriptions, constraints, examples, and hints fetched from LeetCode's public API on demand

**Code Execution**
- Monaco Editor (same engine as VS Code) with Python syntax highlighting
- Submissions run in a fully isolated Docker container with no network access, read-only filesystem, and a 10-second hard timeout
- Test case results shown inline; failed cases surfaced to the AI explainer

**Analytics**
- GitHub-style activity heatmap and daily solve chart
- Topic mastery radar — computed mastery score per category weighted by difficulty and attempt efficiency
- Error pattern breakdown — classifies runtime errors (SyntaxError, LogicError, WrongAnswer, etc.)
- Streak tracking, solve velocity (7-day and 30-day), first-attempt success rate
- Learning milestone badges at 1, 10, 25, 50, 100, 250, and 600 problems solved

**AI Coaching** *(requires OpenAI API key)*
- **Hints** — three progressive nudges for the current problem, no code spoilers
- **Mistake Explainer** — tells you exactly why your code failed and which concept to fix
- **Code Review** — time/space complexity, what you did right, improvement suggestions
- **Weekly Report** — data-driven performance summary grounded in your actual stats
- **Study Plan** — personalised two-week day-by-day plan targeting your weak areas
- **AI Chat** — ask any DSA question; answers are contextualised with your learning data

**Auth and Multi-user**
- JWT-based authentication (30-day tokens); bcrypt password hashing
- Full per-user data isolation — all progress, attempts, and analytics are scoped to the logged-in user
- First registered account automatically inherits any pre-auth data

**Settings**
- OpenAI API key stored encrypted (AES-256/Fernet) in the database — configure from the UI, no restart needed
- Key is never returned to the frontend; only configured/not-configured status is exposed

---

## Architecture

```
Browser
  └── Nginx :80
        ├── /api/*   → backend:8000   (FastAPI)
        │                  ├── PostgreSQL / TimescaleDB :5432
        │                  └── code-runner:5000          (isolated)
        └── /*       → frontend:5173  (Vite dev server)
```

| Layer | Technology |
|-------|-----------|
| Frontend | React 18, Vite, Material UI, Monaco Editor |
| Backend | Python 3.12, FastAPI, SQLAlchemy 2 (async), asyncpg |
| Database | TimescaleDB (PostgreSQL 16) — time-series hypertables + continuous aggregates |
| Code Runner | Python 3.12, Flask/Gunicorn, fully sandboxed Docker container |
| Auth | JWT (python-jose), bcrypt (passlib), HTTP Bearer scheme |
| AI | OpenAI Python SDK, GPT-4o |
| Proxy | Nginx 1.25 |

---

## Prerequisites

| Tool | Version | Notes |
|------|---------|-------|
| Docker Desktop | 4.x+ | Engine 24+ |
| Node.js + npm | 18 LTS+ | Required to build the frontend |
| Git | any | |

Python is **not** required on the host — the backend runs entirely inside Docker. Node is only needed for the one-time frontend build step.

---

## Quick Start

```bash
# 1. Clone the repository
git clone <your-repo-url> ALGOMASTER
cd ALGOMASTER

# 2. Create your local environment file
cp .env.example .env
```

Open `.env` and set a strong `SECRET_KEY` before doing anything else:

```bash
# Generate a secure key (run this in any terminal with Python)
python -c "import secrets; print(secrets.token_hex(32))"
```

Paste the output as `SECRET_KEY` in `.env`. Leave `OPENAI_API_KEY` blank for now — you can add it from the Settings page later.

```bash
# 3. Build the frontend (one-time; repeat after UI changes)
cd frontend
npm install
npx vite build
xcopy /E /Y dist ..\backend\static\   # Windows
# cp -r dist/* ../backend/static/     # macOS / Linux
cd ..

# 4. Start all services
docker compose up -d --build

# 5. Open the app
# http://localhost
```

First boot seeds all 600 problems automatically. Allow ~60 seconds for TimescaleDB to initialise on the very first run.

---

## Environment Variables

All variables are read from `.env` at the repository root. Copy `.env.example` and fill in the values below.

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `POSTGRES_USER` | Yes | `algomaster` | PostgreSQL username |
| `POSTGRES_PASSWORD` | Yes | `algomaster_secret` | PostgreSQL password |
| `POSTGRES_DB` | Yes | `algomaster` | PostgreSQL database name |
| `DATABASE_URL` | Yes | *(derived)* | Full asyncpg connection string |
| `SECRET_KEY` | **Yes** | — | 32+ char random hex. Used for JWT signing and API key encryption. **Must be changed from the default.** |
| `OPENAI_API_KEY` | No | *(empty)* | OpenAI key. If left blank, set it via the Settings page instead — no restart needed. |
| `OPENAI_MODEL` | No | `gpt-4o` | OpenAI model name |
| `CODE_RUNNER_URL` | No | `http://code-runner:5000` | Internal URL of the sandboxed executor |
| `BACKEND_CORS_ORIGINS` | No | `["http://localhost","http://localhost:5173"]` | JSON array of allowed origins |
| `ENVIRONMENT` | No | `development` | `development` or `production` |

> **Security note:** `.env` is gitignored. Never commit it. The app will refuse to start if `SECRET_KEY` is still set to the placeholder value from `.env.example`.

---

## Frontend Build

The frontend is a Vite + React SPA. In the default Docker setup, nginx proxies all non-API traffic to the Vite dev server running inside the `frontend` container, giving you hot-module replacement (HMR) during development.

For a cleaner setup — or before sharing/deploying — build the static bundle and serve it directly from the backend's `static/` directory:

**Windows (PowerShell):**
```powershell
cd frontend

# If a previous Docker build created a root-owned dist/, clear it first
Remove-Item -Recurse -Force dist -ErrorAction SilentlyContinue

npm install
npx vite build
xcopy /E /Y dist ..\backend\static\
cd ..
docker compose up -d --build
```

**macOS / Linux:**
```bash
cd frontend
rm -rf dist
npm install
npx vite build
cp -r dist/* ../backend/static/
cd ..
docker compose up -d --build
```

After copying the build, nginx can serve it from the backend container. You can remove the `frontend` service from `docker-compose.yml` if you no longer need HMR.

---

## Docker Services

```
docker compose up -d --build
```

| Service | Internal Port | Purpose |
|---------|--------------|---------|
| `nginx` | 80 (host) | Reverse proxy — routes `/api/*` to backend, everything else to frontend |
| `frontend` | 5173 | Vite dev server with HMR |
| `backend` | 8000 | FastAPI application with `--reload` for hot-restart on code changes |
| `code-runner` | 5000 | Isolated Python executor (no external network access) |
| `db` | 5432 (host) | TimescaleDB (PostgreSQL 16) — data persisted to `postgres_data` Docker volume |

The `backend` service mounts `./backend` into `/app` so code changes reload automatically without rebuilding the image.

---

## First Run

### Register an Account

Navigate to `http://localhost`. You will be redirected to the login page. Click **Create Account** and register with an email, username, and password.

> **Important:** The first account registered automatically inherits all pre-existing data (problems attempted before auth was set up). Subsequent accounts start fresh.

### Configure the OpenAI API Key

Go to **Settings** (sidebar, bottom) and paste your key into the OpenAI API Key field. Click **Save Key**. The key is encrypted with AES-256 before being stored in the database — it activates immediately with no container restart required.

If you prefer to set it via `.env`, add:
```
OPENAI_API_KEY=sk-proj-...
```
...then run `docker compose restart backend`. The Settings page will show it as configured from the environment.

### Problem Descriptions

Problems are seeded with titles, categories, and difficulty on first boot. Full descriptions (examples, constraints, hints) are fetched from LeetCode's GraphQL API the first time you open a problem. This happens automatically in the background.

To bulk-fetch all descriptions at once:
```bash
curl -X POST http://localhost/api/admin/fetch-leetcode \
  -H "Authorization: Bearer <your-jwt-token>"
```
Poll `/api/admin/fetch-progress` to watch status.

---

## AI Features

AI features are available in two places:

**On the Problem Page**
- **Hints** — opens a collapsible panel with three progressive hints for the current problem
- **Why did I fail?** — appears on the verdict screen after a wrong answer; explains the specific bug
- **Review my code** — appears after a passing submission; gives time/space complexity and improvement suggestions

**On the Analytics Page (AI Insights tab)**
- **Weekly Report** — summarises this week's performance with three actionable recommendations
- **Study Plan** — generates a personalised two-week schedule targeting your weakest categories
- **Mistake Analysis** — identifies root causes behind your most frequent error types
- **AI Chat** — freeform coaching chat grounded in your actual solve data

All prompts send only your performance statistics to OpenAI — no code is sent unless you explicitly trigger a code-specific feature (mistake explainer, code review).

---

## Admin Tools

Admin endpoints require authentication (valid JWT). They are primarily used for managing problem content.

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/admin/fetch-leetcode` | POST | Start bulk description fetch (runs in background) |
| `/api/admin/fetch-progress` | GET | Poll the status of a running bulk fetch |
| `/api/admin/fetch-leetcode/{problem_id}` | POST | Fetch a single problem's description on demand |
| `/api/admin/problems/no-description` | GET | List all problems with missing or placeholder descriptions |
| `/api/admin/problems/{slug}/manual` | PATCH | Manually set description for a premium/blocked problem |
| `/api/admin/export-problems` | POST | Export all problems to `/app/data/problems_data.json` |
| `/api/admin/export-status` | GET | Check whether the local JSON cache exists |

The export file (`backend/data/problems_data.json`) is the seed source on subsequent Docker restarts — once problems have been fetched and exported, a fresh container won't need to hit LeetCode again.

---

## Local Development

### Backend

The backend reloads automatically when Python files change — the `--reload` flag is passed via the `docker-compose.yml` command override.

```bash
# Start only the services the backend depends on
docker compose up -d db code-runner

# Run the backend outside Docker (optional — requires Python 3.12 + pip install)
cd backend
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000
```

Interactive API docs are available at `http://localhost:8000/docs` (Swagger UI) or `http://localhost:8000/redoc` (ReDoc).

### Frontend

The Vite dev server runs inside the `frontend` Docker container, proxied through nginx. If you prefer to run it on the host:

```bash
cd frontend
npm install
npm run dev   # http://localhost:5173
```

When running outside Docker, update `vite.config.js` to proxy `/api` to `http://localhost:8000` instead of the nginx host.

### Database Access

```bash
# psql shell
docker compose exec db psql -U algomaster -d algomaster

# Check TimescaleDB hypertables
SELECT hypertable_name FROM timescaledb_information.hypertables;

# Inspect continuous aggregate
SELECT * FROM daily_stats ORDER BY day DESC LIMIT 10;
```

---

## API Reference

All endpoints are prefixed `/api/` by nginx. Full interactive docs are at `/api/docs`.

### Auth — `/api/auth`
| Endpoint | Method | Auth | Description |
|----------|--------|------|-------------|
| `/auth/register` | POST | — | Create account; first account claims legacy data |
| `/auth/login` | POST | — | Returns JWT token |
| `/auth/me` | GET | ✓ | Returns current user info |

### Problems — `/api/problems`
| Endpoint | Method | Auth | Description |
|----------|--------|------|-------------|
| `/problems` | GET | ✓ | List all problems (supports `?category=&difficulty=&search=` filters) |
| `/problems/{id}` | GET | ✓ | Problem detail with description, test cases, hints |
| `/problems/{id}/progress` | GET | ✓ | Fetch solve status for this problem |
| `/problems/{id}/progress` | PATCH | ✓ | Update notes, confidence, status |
| `/problems/{id}/star` | POST | ✓ | Toggle star |
| `/problems/progress/all` | GET | ✓ | All progress records for the current user |

### Attempts — `/api/attempts`
| Endpoint | Method | Auth | Description |
|----------|--------|------|-------------|
| `/attempts/run` | POST | ✓ | Submit or run code (`mode: "run"` or `"submit"`) |
| `/attempts/problem/{id}` | GET | ✓ | Attempt history for a problem |

### Analytics — `/api/analytics`
| Endpoint | Method | Auth | Description |
|----------|--------|------|-------------|
| `/analytics/overview` | GET | ✓ | Aggregate stats (solved counts, streak, velocity) |
| `/analytics/daily` | GET | ✓ | Daily time-series (`?days=90`) |
| `/analytics/topic-mastery` | GET | ✓ | Per-category mastery scores |
| `/analytics/error-patterns` | GET | ✓ | Top error categories |
| `/analytics/milestones` | GET | ✓ | Achieved learning milestones |

### AI — `/api/ai`
| Endpoint | Method | Auth | Description |
|----------|--------|------|-------------|
| `/ai/insight` | POST | ✓ | Generate AI insight (`insight_type`: `weekly_report`, `study_plan`, `mistake_analysis`, `hint`, `mistake_explain`, `code_review`, `chat`) |
| `/ai/history` | GET | ✓ | Recent AI responses |

### Settings — `/api/settings`
| Endpoint | Method | Auth | Description |
|----------|--------|------|-------------|
| `/settings/openai-key` | GET | ✓ | Returns `{ configured: bool, source: "database"\|"environment"\|"none" }` |
| `/settings/openai-key` | POST | ✓ | Encrypt and store a new key; activates immediately |
| `/settings/openai-key` | DELETE | ✓ | Remove stored key from database |

### Health — `/api/health`
```json
{ "status": "ok", "version": "1.0.0" }
```

---

## Database Schema

| Table | Type | Description |
|-------|------|-------------|
| `users` | Regular | User accounts (email, username, bcrypt password hash) |
| `problems` | Regular | All 600 problems — title, category, difficulty, description, test cases, hints |
| `problem_progress` | Regular | One row per (user, problem) — solve status, attempts, time, confidence, notes |
| `problem_attempts` | Hypertable | Every code submission, partitioned by `submitted_at` |
| `error_patterns` | Hypertable | Classified runtime errors, partitioned by `occurred_at` |
| `sessions` | Hypertable | Practice sessions (currently unused — reserved for future session tracking) |
| `ai_insights` | Regular | Saved AI-generated responses |
| `learning_milestones` | Regular | Milestone achievements per user |
| `topic_mastery` | Regular | Cached per-category mastery scores, recomputed on each submission |
| `app_settings` | Regular | Encrypted application configuration (`openai_api_key`) |
| `daily_stats` | Continuous Aggregate | Auto-refreshed hourly from `problem_attempts` |

TimescaleDB automatically manages retention and partitioning for the three hypertables. The `daily_stats` aggregate refreshes on a one-hour schedule, covering a 30-day rolling window.

### Schema Migrations

There is no Alembic migration runner. All schema changes are applied at startup in `backend/app/main.py` using idempotent `ALTER TABLE ... ADD COLUMN IF NOT EXISTS` and `ALTER TYPE ... ADD VALUE IF NOT EXISTS` statements. This means the database upgrades safely on every `docker compose up` without manual intervention.

---

## Code Runner Security

Code submitted by users runs in a separate `code-runner` container that is:

- **Network-isolated** — not connected to any external network; cannot reach the internet or the database
- **Read-only filesystem** — only `/tmp` is writable (64 MB RAM disk via `tmpfs`)
- **Non-root** — processes run as user `runner` with no privileges
- **Capability-dropped** — `cap_drop: ALL` removes all Linux capabilities
- **Resource-limited** — 256 MB memory hard limit, 0.5 CPU, 10-second execution timeout (enforced by Gunicorn)
- **No new privileges** — `no-new-privileges: true` prevents privilege escalation via setuid

The backend sends the submitted code and test cases to `code-runner:5000` over the internal Docker network, receives results (stdout, pass/fail per test case, error type/message), and stores the attempt in the database. The code never touches the backend process directly.

---

## Common Commands

```bash
# Start everything
docker compose up -d --build

# Stop containers (data preserved)
docker compose down

# Stop and delete all data (full reset)
docker compose down -v

# View backend logs (live)
docker compose logs -f backend

# View all service logs
docker compose logs -f

# Rebuild a single service after code changes
docker compose up -d --build backend

# Open a Python shell in the backend container
docker compose exec backend python

# Run a DB migration or one-off script
docker compose exec backend python -m app.scripts.export_problems

# Bulk-fetch problem descriptions (requires auth token)
curl -X POST http://localhost/api/admin/fetch-leetcode \
  -H "Authorization: Bearer <token>"

# Check fetch progress
curl http://localhost/api/admin/fetch-progress \
  -H "Authorization: Bearer <token>"

# Reset a specific user's password (via psql)
docker compose exec db psql -U algomaster -d algomaster -c \
  "UPDATE users SET hashed_pw = '<bcrypt-hash>' WHERE email = '<email>'"
```

---

## Troubleshooting

### App won't start — `SECRET_KEY is still set to the default placeholder`

The backend detects the placeholder key and refuses to boot. Generate a real key:

```bash
python -c "import secrets; print(secrets.token_hex(32))"
```

Paste the output as `SECRET_KEY` in `.env`, then `docker compose up -d --build`.

---

### Frontend build fails with `EPERM: operation not permitted, unlink` (Windows)

Docker runs as root inside the container. When it writes the `dist/` folder, Windows marks it as root-owned and your user can't overwrite it.

```powershell
cd frontend
Remove-Item -Recurse -Force dist
npx vite build
xcopy /E /Y dist ..\backend\static\
```

---

### AI features show "API key not configured"

Either the key was never set, or it was encrypted with a different `SECRET_KEY` than the one currently in `.env` (happens if you regenerate `SECRET_KEY` after storing a key).

Fix: go to **Settings**, delete the old key if shown, and enter the key again. It will be re-encrypted with the current `SECRET_KEY`.

---

### Problem descriptions show placeholder text

Descriptions are fetched lazily from LeetCode on first open. If the network fetch fails (rate-limit, timeout, or the problem is premium/paywalled), the placeholder remains. Options:

1. Open the problem again — it retries automatically.
2. Bulk-fetch: `POST /api/admin/fetch-leetcode` (runs in background, polls `/api/admin/fetch-progress`).
3. For premium problems: `PATCH /api/admin/problems/{slug}/manual` with `{ "description": "..." }`.

---

### TimescaleDB takes too long to start / backend exits on first boot

TimescaleDB needs ~30–60 seconds to initialise its extension on a brand-new volume. The backend has a `depends_on: db: condition: service_healthy` with a 10-retry healthcheck. If it still fails:

```bash
docker compose logs db        # check for init errors
docker compose restart backend
```

---

### Port 80 or 5432 already in use

Edit `docker-compose.yml` to change the host-side port:

```yaml
ports:
  - "8080:80"   # nginx on 8080 instead of 80
```

Then access the app at `http://localhost:8080`.

---

### All data is lost after `docker compose down -v`

The `-v` flag deletes the `postgres_data` volume. Without `-v`, data persists across restarts. Before any destructive operation, export your problem data:

```bash
curl -X POST http://localhost/api/admin/export-problems \
  -H "Authorization: Bearer <token>"
```

This writes `backend/data/problems_data.json` which is used as the seed source on the next fresh start — you won't need to re-fetch from LeetCode.
