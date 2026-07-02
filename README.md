# 🧠 AlgoMaster

> A self-hosted DSA (data structures & algorithms) practice platform with a sandboxed code runner, AI coaching, deep progress analytics, and dedicated interview-readiness tracking — built for engineers who take interview prep seriously.

[![FastAPI](https://img.shields.io/badge/FastAPI-0.115-009688?style=flat-square&logo=fastapi)](https://fastapi.tiangolo.com/)
[![React](https://img.shields.io/badge/React-18-61DAFB?style=flat-square&logo=react)](https://react.dev/)
[![PostgreSQL](https://img.shields.io/badge/TimescaleDB-pg16-336791?style=flat-square&logo=postgresql)](https://www.timescale.com/)
[![Docker](https://img.shields.io/badge/Docker-Compose-2496ED?style=flat-square&logo=docker)](https://docs.docker.com/compose/)
[![License](https://img.shields.io/badge/License-MIT-yellow?style=flat-square)](./LICENSE)

---

## Table of Contents

- [What is AlgoMaster?](#what-is-algomaster)
- [Features](#features)
- [Architecture](#architecture)
- [Tech Stack](#tech-stack)
- [Project Structure](#project-structure)
- [Getting Started](#getting-started)
  - [Prerequisites](#prerequisites)
  - [Environment Variables](#environment-variables)
  - [Docker Setup (recommended)](#docker-setup-recommended)
  - [Database Initialization](#database-initialization)
  - [Local Development (hot reload)](#local-development-hot-reload)
- [Common Development Commands](#common-development-commands)
- [API Overview](#api-overview)
- [Algorithm Categories](#algorithm-categories)
- [Analytics](#analytics)
- [AI Coach](#ai-coach)
- [Interview Readiness](#interview-readiness)
- [Security](#security)
- [Troubleshooting](#troubleshooting)
- [License](#license)

---

## What is AlgoMaster?

AlgoMaster is a self-hosted alternative to commercial DSA interview-prep platforms. You run it on your own machine (or your own server), your solve history and code never leave your infrastructure, and you optionally bring your own OpenAI key for AI-assisted coaching.

It ships with **600 curated problems across 59 algorithm patterns**, a real Python execution sandbox (not a fake "did the output string match" check — your code actually runs, with CPU/memory limits, against hidden test cases), and an analytics layer that goes beyond "problems solved" to track *how* you solve — time-to-pattern-recognition, mistake categories, spaced-repetition review scheduling, and a composite interview-readiness score.

---

## Features

- **600 curated problems** across 59 algorithm patterns — Arrays, DP, Graphs, Trees, Backtracking, and more
- **Sandboxed code runner** — your Python actually executes, isolated in its own container with CPU/memory limits and no network/filesystem access
- **AI coaching** (optional, bring your own OpenAI key) — Socratic hints, "why did I fail?" mistake explanations, and post-accept code reviews
- **Progress analytics** — solve streaks, topic mastery scores ranked by a struggle index, error-pattern breakdowns
- **Interview readiness tracking** — self-assessments, an SM-2 spaced-repetition review queue, a mistake log, a contest log, and a composite readiness score (see [Interview Readiness](#interview-readiness))
- **Monaco editor** (the engine behind VS Code) with syntax highlighting, keyboard shortcuts, and per-problem notes
- **JWT authentication** with per-route rate limiting; the first account to register is auto-promoted to admin
- **Self-hosted** — your data and code stay on your own machine

---

## Architecture

```
┌─────────┐      ┌──────────────┐      ┌─────────────┐      ┌──────────────┐
│  nginx  │─────▶│   frontend   │      │   backend   │─────▶│ TimescaleDB  │
│  :80    │      │ React build  │      │  FastAPI    │      │ (PostgreSQL) │
│(reverse │      │ served by an │      │  + Alembic  │      └──────────────┘
│ proxy)  │─────▶│ internal     │      │  + slowapi  │
└─────────┘      │ nginx (:80)  │      └──────┬──────┘
                  └──────────────┘             │
                                         ┌──────▼──────┐
                                         │ code-runner │
                                         │ (sandboxed, │
                                         │  no network,│
                                         │ read-only)  │
                                         └─────────────┘
```

Five containers, all on one internal Docker network (`algomaster`):

| Service | Role | Reachable from your host at |
|---|---|---|
| `nginx` | Reverse proxy — routes `/api/*` to the backend, everything else to the frontend | `http://localhost` (port 80) |
| `frontend` | React SPA, built to a static bundle and served by its own internal nginx | not published directly — go through the top-level `nginx` |
| `backend` | FastAPI application — auth, problems, attempts, analytics, AI, admin | not published directly — go through `nginx`'s `/api/*` routes |
| `code-runner` | Executes untrusted user Python in an isolated, network-less, read-only container | not published to the host at all (internal only) |
| `db` | TimescaleDB (PostgreSQL 16 + time-series extension) | `127.0.0.1:5432` (loopback only, for local `psql`/admin access) |

Only `nginx` (port 80) and `db` (port 5432, loopback-only) are exposed to your host machine. Everything else talks to everything else over the internal Docker network by service name.

---

## Tech Stack

| Layer | Technology |
|---|---|
| Frontend | React 18, MUI v6, Monaco Editor, Recharts, D3, Vite 5 |
| Backend | FastAPI 0.115, SQLAlchemy 2.0 (async), Alembic, Pydantic v2, slowapi (rate limiting) |
| Database | TimescaleDB 2.17 (PostgreSQL 16) |
| Code Execution | Python 3.12 subprocess inside a locked-down Docker container (Flask + Gunicorn) |
| Auth | JWT (`python-jose`), bcrypt password hashing |
| Secrets | Fernet (AES-128-CBC + HMAC-SHA256) encryption for the stored OpenAI key |
| AI | OpenAI API (`gpt-4o` by default) via the official `openai` SDK |
| Proxy | nginx 1.25 |
| Orchestration | Docker Compose |

---

## Project Structure

```
algomaster/
├── backend/                          # FastAPI application
│   ├── app/
│   │   ├── api/                      # Route handlers: auth, problems, attempts,
│   │   │                             #   analytics, ai, admin, settings, interview
│   │   ├── analytics/                # Topic mastery / streak / readiness-score engine
│   │   ├── core/                     # Auth deps, rate limiter, encryption helpers
│   │   ├── models/                   # SQLAlchemy ORM models
│   │   ├── schemas/                  # Pydantic request/response schemas
│   │   ├── scripts/                  # One-off admin scripts (LeetCode fetch/export)
│   │   ├── seed/                     # Problem seeder (loads data/problems_data.json)
│   │   ├── config.py                 # Settings (env vars) + startup safety checks
│   │   ├── database.py               # SQLAlchemy engine/session setup
│   │   └── main.py                   # App factory, startup lifespan, migrations runner
│   ├── alembic/                      # Database migrations (schema evolution)
│   │   └── versions/
│   ├── alembic.ini
│   ├── data/problems_data.json       # The 600 curated problems
│   ├── requirements.txt
│   └── Dockerfile
├── code-runner/                      # Sandboxed Python executor (Flask + Gunicorn)
│   ├── executor.py
│   ├── requirements.txt
│   └── Dockerfile
├── frontend/                         # React SPA
│   ├── src/
│   │   ├── api/                      # Axios client
│   │   ├── components/               # Layout, Auth, Analytics, Editor, Tracker
│   │   ├── contexts/                 # AuthContext
│   │   ├── hooks/
│   │   └── pages/                    # Tracker, Problem, Analytics, Interview, Settings, Login
│   ├── nginx.static.conf             # Serves the built SPA inside the frontend container
│   ├── vite.config.js
│   ├── package.json
│   └── Dockerfile                    # Multi-stage: Vite build → nginx runtime
├── db/
│   └── init.sql                      # One-time schema bootstrap (extensions + base tables)
├── nginx/
│   └── nginx.conf                    # Top-level reverse-proxy config
├── docker-compose.yml
├── .env.example
└── LICENSE
```

---

## Getting Started

### Prerequisites

- [Docker Desktop](https://www.docker.com/products/docker-desktop/) or Docker Engine + the Compose v2 plugin (`docker compose version` should work)
- For local (non-Docker) frontend/backend development: **Node.js 20+** and **Python 3.12+**
- An OpenAI API key — **optional**. AI coaching features are disabled gracefully without one; everything else works fine.

### Environment Variables

All configuration lives in a single `.env` file at the project root. Start from the template:

```bash
cp .env.example .env
```

| Variable | Default | Required? | Description |
|---|---|---|---|
| `POSTGRES_USER` | `algomaster` | No | Database role name |
| `POSTGRES_PASSWORD` | `algomaster_secret` | **Yes — must be changed** | Database password. The backend refuses to start if this is still the placeholder value (see [Troubleshooting](#troubleshooting)) |
| `POSTGRES_DB` | `algomaster` | No | Database name |
| `DATABASE_URL` | `postgresql+asyncpg://algomaster:algomaster_secret@db:5432/algomaster` | **Yes — must match `POSTGRES_PASSWORD`** | Full async connection string the backend uses |
| `SECRET_KEY` | `dev_secret_change_in_production` | **Yes — must be changed** | JWT signing key. The backend refuses to start with the placeholder value. Generate one with `python -c "import secrets; print(secrets.token_hex(32))"` |
| `CODE_RUNNER_URL` | `http://code-runner:5000` | No | Internal URL the backend uses to reach the sandbox. Only change this for [local hybrid development](#local-development-hot-reload) |
| `OPENAI_API_KEY` | *(unset)* | No | Enables AI coaching (hints, mistake explanations, code review). Can also be set later from the in-app **Settings** page (admin only) — it's stored encrypted in the database either way |
| `OPENAI_MODEL` | `gpt-4o` | No | Override to use a different OpenAI chat model |
| `BACKEND_CORS_ORIGINS` | `["http://localhost","http://localhost:5173","http://localhost:3000"]` | No | JSON array of allowed CORS origins |
| `ENVIRONMENT` | `development` | No | Informational; doesn't currently gate behavior beyond logging |

**Before your first run, at minimum:**

```env
SECRET_KEY=<output of: python -c "import secrets; print(secrets.token_hex(32))">
POSTGRES_PASSWORD=<a different random string>
DATABASE_URL=postgresql+asyncpg://algomaster:<the same random string>@db:5432/algomaster
```

`POSTGRES_PASSWORD` and the password embedded in `DATABASE_URL` **must match** — Postgres itself is initialized from the former, and the backend connects using the latter.

### Docker Setup (recommended)

This is the standard way to run AlgoMaster — it starts all five services with the exact topology described in [Architecture](#architecture).

```bash
git clone <this-repo-url>
cd algomaster
cp .env.example .env
# edit .env — set SECRET_KEY and POSTGRES_PASSWORD as described above
docker compose up --build
```

First run will: build all four custom images, initialize the Postgres volume (`db/init.sql`), run Alembic migrations, and seed the database with all 600 problems. This takes roughly 1–3 minutes depending on your machine and network speed. The backend has a 60-second startup grace period before its health check is considered failed, so don't panic if `backend-1` looks quiet for a bit.

Once `backend` reports healthy, open **[http://localhost](http://localhost)**.

**Register your account** — the first user to register is automatically promoted to admin (admin is required to configure the shared OpenAI key from the Settings page).

To run in the background instead of attached to your terminal:

```bash
docker compose up -d --build
docker compose logs -f backend   # tail logs when you need them
```

### Database Initialization

Schema setup happens in two layers, both automatic:

1. **`db/init.sql`** — runs exactly once, the very first time the `db` container initializes an empty Postgres data volume (this is standard Postgres-image behavior for anything mounted into `/docker-entrypoint-initdb.d/`). It enables the `timescaledb`, `pgcrypto`, and `pg_stat_statements` extensions and creates the base tables (`users`, `problems`, `sessions`, etc.).
2. **Alembic migrations** (`backend/alembic/versions/`) — run automatically on every backend startup (see `run_migrations()` in `backend/app/main.py`), carrying the schema forward from whatever `init.sql` created to the current model definitions. Currently two revisions: `001_initial_column_migrations` (auth/multi-user columns, admin role) and `002_interview_readiness_tables` (self-assessments, review schedule, mistake log, contest log, DS fluency).

You generally never need to touch either of these by hand. If you do:

```bash
# Run migrations manually against a running db (from inside the backend container or a local venv with DATABASE_URL set)
cd backend
alembic upgrade head

# Check current migration state
alembic current
alembic history
```

**Resetting the database entirely** (drops all data — useful in dev when you've changed `POSTGRES_PASSWORD` after the volume was already initialized, or just want a clean slate):

```bash
docker compose down -v   # -v removes the named volume (postgres_data)
docker compose up --build
```

### Local Development (hot reload)

The Docker setup above is the easiest way to run the full stack, but it rebuilds the frontend on every change and doesn't give you Python debugger/hot-reload ergonomics for backend work. Two supported workflows:

**A. Frontend hot reload against the full Dockerized backend (recommended for UI work)**

```bash
docker compose up --build      # full stack, running at http://localhost
```

In a second terminal:

```bash
cd frontend
npm install
VITE_API_BASE_URL=http://localhost/api npm run dev
```

Vite's dev server starts at `http://localhost:5173` with hot module reload, and points API calls at your already-running Dockerized backend through the top-level nginx — no code changes needed. (`vite.config.js`'s built-in proxy target, `http://backend:8000`, only resolves *inside* the Docker network, so it won't work if Vite is running on your bare host — the `VITE_API_BASE_URL` override above sidesteps that.)

**B. Backend hot reload with Dockerized dependencies**

Run just the database and code runner in Docker:

```bash
docker compose up -d db
```

The `code-runner` service isn't published to the host by default (it's only reachable from other containers on the Docker network). To reach it from a backend running on bare metal, add a `docker-compose.override.yml` (Compose automatically merges this — it's already covered by `.gitignore`-style local overrides, keep it out of version control) with:

```yaml
services:
  code-runner:
    ports:
      - "5000:5000"
```

Then:

```bash
docker compose up -d code-runner
```

Now run the backend locally, pointing it at the Dockerized `db` (reachable via the loopback port mapping already in `docker-compose.yml`) and `code-runner`:

```bash
cd backend
python -m venv venv && source venv/bin/activate    # Windows: venv\Scripts\activate
pip install -r requirements.txt

export DATABASE_URL=postgresql+asyncpg://algomaster:<your password>@localhost:5432/algomaster
export CODE_RUNNER_URL=http://localhost:5000
export SECRET_KEY=<your dev secret>

alembic upgrade head
uvicorn app.main:app --reload --port 8000
```

The backend is now at `http://localhost:8000` with auto-reload on file changes. Point the frontend at it with `VITE_API_BASE_URL=http://localhost:8000 npm run dev`, or use `curl`/an API client directly.

---

## Common Development Commands

| Task | Command |
|---|---|
| Start full stack (build if needed) | `docker compose up --build` |
| Start full stack, detached | `docker compose up -d --build` |
| Stop everything | `docker compose down` |
| Stop everything **and wipe the database** | `docker compose down -v` |
| Tail logs for one service | `docker compose logs -f backend` (or `frontend`, `db`, `code-runner`, `nginx`) |
| Rebuild one service after a Dockerfile change | `docker compose up --build backend` |
| Shell into a running container | `docker compose exec backend bash` |
| Run a migration manually | `docker compose exec backend alembic upgrade head` |
| Open a `psql` shell against the DB | `docker compose exec db psql -U algomaster -d algomaster` |
| Frontend: install deps | `cd frontend && npm install` |
| Frontend: dev server (hot reload) | `cd frontend && npm run dev` |
| Frontend: production build | `cd frontend && npm run build` |
| Frontend: preview a production build locally | `cd frontend && npm run preview` |
| Backend: install deps (local venv) | `cd backend && pip install -r requirements.txt` |
| Backend: run with hot reload (local venv) | `cd backend && uvicorn app.main:app --reload --port 8000` |
| Backend: check migration status | `cd backend && alembic current` / `alembic history` |
| Generate a random `SECRET_KEY` / password | `python -c "import secrets; print(secrets.token_hex(32))"` |

> **Note:** there is currently no automated test suite in this repository (no `pytest`/`vitest`/`jest` config). If you're adding one, `backend/tests/` and `frontend/src/**/*.test.jsx` would be the conventional locations.

---

## API Overview

The backend is a single FastAPI app; all routes are proxied under `/api/*` by nginx. Interactive Swagger docs are available at **`http://localhost/api/docs`** whenever the backend is running.

| Router | Prefix | Covers |
|---|---|---|
| Auth | `/api/auth` | Register, login, `/me` (JWT-based; first registrant becomes admin) |
| Problems | `/api/problems` | List/get problems, per-user progress, starring |
| Attempts | `/api/attempts` | Run/submit code against the sandboxed runner, attempt history |
| Analytics | `/api/analytics` | Overview stats, daily activity, topic mastery, error patterns |
| AI | `/api/ai` | Hints, mistake explanations, code review, weekly reports (rate-limited) |
| Interview | `/api/interview` | Self-assessments, spaced-repetition review queue, mistake log, contest log, DS fluency, readiness score |
| Settings | `/api/settings` | OpenAI key status/configuration (admin-only to write) |
| Admin | `/api/admin` | LeetCode metadata fetch/export utilities (admin-only) |

---

## Algorithm Categories

AlgoMaster covers **59 patterns** including:

`Arrays` · `Two Pointers` · `Sliding Window` · `Binary Search` · `Hash Tables` · `Linked Lists` · `Stacks` · `Queues` · `Trees` · `Graphs` · `BFS` · `DFS` · `Backtracking` · `Heaps` · `Tries` · `1-D DP` · `0/1 Knapsack` · `Greedy` · `Bit Manipulation` · `Prefix Sum` · `Union Find` · `Topological Sort` · `Shortest Path` · `Segment Trees` · `Monotonic Stack` · `Divide and Conquer` · and more

---

## Analytics

After solving problems, the Analytics page shows:

- **Daily activity** calendar heatmap
- **Topic mastery** scores ranked by struggle index
- **Error pattern** breakdown (SyntaxError, TypeError, TimeoutError, WrongAnswer, etc.)
- **Solve rate** and streak tracking over time

Topic mastery refreshes in the background with a 5-minute cooldown to avoid unnecessary DB load.

---

## AI Coach

Powered by OpenAI (`gpt-4o` by default). Fully optional — every other feature works without an API key. Three modes available from the problem page:

| Mode | Trigger | What it does |
|---|---|---|
| **AI Hints** | Anytime | Socratic nudges — guides you without giving away the answer |
| **Why did I fail?** | After a wrong answer | Explains which test cases failed and why your logic broke |
| **Review my code** | After an accepted solution | Time/space complexity analysis and style suggestions |

Set the key from **Settings** (admin-only; stored Fernet-encrypted in the database, takes effect immediately, no restart needed) or via `OPENAI_API_KEY` in `.env`. The `/api/ai/insight` endpoint is rate-limited to 20 requests/hour per user.

---

## Interview Readiness

A dedicated **Interview Readiness** page (separate from Analytics) tracks the metacognitive and interview-specific signals that raw solve/fail counts miss:

| Feature | What it captures |
|---|---|
| **Self-assessment** | After each solve, log which pattern you identified (and how fast), time to first idea / algorithm / total solve, bug count and categories, whether you checked edge cases before coding, and a post-solve confidence rating |
| **Spaced repetition review queue** | Problems can be added to a review schedule; due dates are computed with the SM-2 algorithm (the same spaced-repetition scheduler used by Anki), driven by a 1–5 quality score you give each time you re-solve |
| **Mistake log** | Freeform log of recurring mistake categories (e.g. off-by-one, misread constraints, wrong data structure) tied to a problem, so patterns become visible over time |
| **Contest log** | Track rating, rank, and questions solved per contest (LeetCode/Codeforces-style) to correlate practice with real contest performance |
| **Data structure fluency** | Self-rated 1–5 fluency per data structure (arrays, heaps, tries, etc.), independent of any specific problem |
| **Composite readiness score** | Rolls the above into a single score via `GET /api/interview/readiness`, combining solve breadth, pattern recognition speed, mistake frequency, and review consistency |

Backend logic lives in `backend/app/api/interview.py` and `backend/app/analytics/interview.py`; the underlying tables (`self_assessments`, `review_schedule`, `mistake_log`, `contest_log`, `ds_fluency`) are created by Alembic migration `002_interview_readiness_tables.py`.

---

## Security

- Passwords hashed with **bcrypt** (min 8 chars, max 72, must contain both letters and numbers)
- Sessions use **HS256-signed JWTs**
- Auth endpoints rate-limited: **5 req/min** (register) · **10 req/min** (login); AI endpoints: **20 req/hour** per user
- The code runner executes untrusted code with `no-new-privileges`, all Linux capabilities dropped, a read-only root filesystem, a 256 MB memory cap, and a 10-second execution timeout — with no network access
- Admin-only routes (settings write, admin utilities) are protected by a `require_admin` FastAPI dependency; the first user to register is auto-promoted
- The stored OpenAI key is encrypted at rest with Fernet (AES-128-CBC + HMAC-SHA256) using `SECRET_KEY` as the derivation source
- `config.py` refuses to start the app if `SECRET_KEY` or `POSTGRES_PASSWORD` are still set to their placeholder values — see [Troubleshooting](#troubleshooting) if you hit this
- Postgres is bound to `127.0.0.1` only, not published to your network

---

## Troubleshooting

**`RuntimeError: SECRET_KEY is still set to the default placeholder`** or **`POSTGRES_PASSWORD is still set to the default placeholder`**
The backend intentionally refuses to boot with either default value (see [Security](#security)). Generate real values and set them in `.env` — see [Environment Variables](#environment-variables).

**I changed `POSTGRES_PASSWORD` in `.env` but the backend still can't authenticate to Postgres**
Postgres only applies `POSTGRES_PASSWORD` when it initializes a *brand-new, empty* data volume — not on every restart. If `db`'s volume was already initialized (e.g. you'd previously started the stack with the placeholder password), changing `.env` alone won't change the actual database role's password. Either:
- Wipe and reinitialize (fine for a fresh dev setup, **destroys all data**): `docker compose down -v && docker compose up --build`, or
- Change the password in place without losing data: `docker compose exec db psql -U algomaster -c "ALTER ROLE algomaster WITH PASSWORD '<new password>';"`, then update `.env` to match.

**A container shows `Unhealthy` or keeps restarting**
Check its logs first: `docker compose logs <service>`. The backend's health check has a 60-second grace period on first boot (it's running migrations + seeding 600 problems), so a few `starting` cycles are normal — only worry if it's still failing after ~90 seconds.

**Frontend dev server (`npm run dev`) can't reach the API**
`vite.config.js`'s built-in proxy targets `http://backend:8000`, which only resolves inside the Docker network. Running Vite on your bare host needs an explicit override — see [Local Development](#local-development-hot-reload), Workflow A.

**Port 80 already in use**
Something else on your machine (often another local web server) is bound to port 80. Either stop it, or change the published port in `docker-compose.yml`'s `nginx` service (`"80:80"` → e.g. `"8080:80"`) and access the app at `http://localhost:8080` instead.

---

## License

[MIT](./LICENSE)
