# 🧠 AlgoMaster

> A self-hosted DSA practice platform with a sandboxed code runner, AI coaching, and deep progress analytics — built for engineers who take interview prep seriously.

[![FastAPI](https://img.shields.io/badge/FastAPI-0.115-009688?style=flat-square&logo=fastapi)](https://fastapi.tiangolo.com/)
[![React](https://img.shields.io/badge/React-18-61DAFB?style=flat-square&logo=react)](https://react.dev/)
[![PostgreSQL](https://img.shields.io/badge/TimescaleDB-pg16-336791?style=flat-square&logo=postgresql)](https://www.timescale.com/)
[![Docker](https://img.shields.io/badge/Docker-Compose-2496ED?style=flat-square&logo=docker)](https://docs.docker.com/compose/)
[![License](https://img.shields.io/badge/License-MIT-yellow?style=flat-square)](./LICENSE)

---

## ✨ Features

- **600 curated problems** across 59 algorithm patterns — Arrays, DP, Graphs, Trees, and more
- **Sandboxed code runner** — executes Python in an isolated container with memory and CPU limits
- **AI coaching** powered by GPT-4o — get hints, mistake explanations, and code reviews on demand
- **Progress analytics** — streak tracking, topic mastery scores, error pattern breakdowns
- **Monaco editor** with syntax highlighting, keyboard shortcuts, and per-problem notes
- **JWT authentication** with rate limiting and first-user admin promotion
- **Self-hosted** — your data stays on your machine

---

## 🏗️ Architecture

```
┌─────────┐     ┌──────────┐     ┌─────────────┐     ┌──────────────┐
│  nginx  │────▶│  React   │     │   FastAPI   │────▶│ TimescaleDB  │
│  :80    │     │  Vite    │     │  + Alembic  │     │  PostgreSQL  │
│         │────▶│  MUI v6  │────▶│  + slowapi  │     └──────────────┘
└─────────┘     └──────────┘     └──────┬──────┘
                                         │
                                  ┌──────▼──────┐
                                  │ Code Runner │
                                  │ (sandboxed) │
                                  └─────────────┘
```

| Layer | Technology |
|---|---|
| Frontend | React 18, MUI v6, Monaco Editor, Recharts, Vite |
| Backend | FastAPI, SQLAlchemy (async), Alembic, Pydantic v2, slowapi |
| Database | TimescaleDB 2.17 (PostgreSQL 16) |
| Code Execution | Python subprocess in Docker (no-new-privileges, read-only FS) |
| AI | OpenAI GPT-4o via `openai` SDK |
| Proxy | nginx 1.25 |

---

## 🚀 Quick Start

### Prerequisites

- [Docker Desktop](https://www.docker.com/products/docker-desktop/) (or Docker + Docker Compose v2)
- An OpenAI API key *(optional — AI features are disabled gracefully without one)*

### 1. Clone and configure

```bash
git clone https://github.com/your-username/algomaster.git
cd algomaster
cp .env.example .env
```

Open `.env` and set at minimum:

```env
SECRET_KEY=your_random_32_char_secret_here
OPENAI_API_KEY=sk-...          # optional
```

### 2. Start everything

```bash
docker compose up --build
```

The first run seeds the database with all 600 problems. Once the backend health check passes (~30–60 s), open **[http://localhost](http://localhost)**.

### 3. Register your account

The **first user to register** is automatically promoted to admin.

---

## 🗂️ Project Structure

```
algomaster/
├── backend/                    # FastAPI application
│   ├── app/
│   │   ├── api/                # Route handlers (auth, problems, analytics, ai, admin)
│   │   ├── analytics/          # Topic mastery engine
│   │   ├── core/               # Auth deps, rate limiter
│   │   ├── models/             # SQLAlchemy ORM models
│   │   ├── schemas/            # Pydantic request/response schemas
│   │   └── seed/               # Problem seeder
│   ├── alembic/                # Database migrations
│   └── data/
│       └── problems_data.json  # 600 curated problems
├── code-runner/                # Sandboxed Python executor (Flask)
├── frontend/                   # React SPA
│   └── src/
│       ├── api/                # Axios client
│       ├── contexts/           # AuthContext
│       └── pages/              # Tracker, Problem, Analytics, Settings
├── db/
│   └── init.sql                # Schema bootstrap
├── nginx/
│   └── nginx.conf
└── docker-compose.yml
```

---

## ⚙️ Configuration

All configuration lives in `.env` at the project root.

| Variable | Default | Description |
|---|---|---|
| `POSTGRES_USER` | `algomaster` | Database user |
| `POSTGRES_PASSWORD` | `algomaster_secret` | Database password — **change in production** |
| `POSTGRES_DB` | `algomaster` | Database name |
| `SECRET_KEY` | *(required)* | JWT signing key — must be random and secret |
| `OPENAI_API_KEY` | *(optional)* | GPT-4o key for AI coaching features |
| `OPENAI_MODEL` | `gpt-4o` | Override to use a different model |
| `BACKEND_CORS_ORIGINS` | `["http://localhost"]` | Allowed CORS origins |

---

## 🧩 Algorithm Categories

AlgoMaster covers **59 patterns** including:

`Arrays` · `Two Pointers` · `Sliding Window` · `Binary Search` · `Hash Tables` · `Linked Lists` · `Stacks` · `Queues` · `Trees` · `Graphs` · `BFS` · `DFS` · `Backtracking` · `Heaps` · `Tries` · `1-D DP` · `0/1 Knapsack` · `Greedy` · `Bit Manipulation` · `Prefix Sum` · `Union Find` · `Topological Sort` · `Shortest Path` · `Segment Trees` · `Monotonic Stack` · `Divide and Conquer` · and more

---

## 🔒 Security

- Passwords hashed with **bcrypt** (min 8 chars, max 72, letters + numbers required)
- All tokens signed with **HS256 JWT**
- Auth endpoints rate-limited: **5 req/min** (register) · **10 req/min** (login)
- Code runner runs with `no-new-privileges`, all Linux capabilities dropped, read-only filesystem, 256 MB memory cap, and a 10-second execution timeout
- Admin routes protected by a `require_admin` FastAPI dependency

---

## 🛠️ Development

**Backend only** (hot reload):

```bash
cd backend
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000
```

**Frontend only:**

```bash
cd frontend
npm install
npm run dev        # http://localhost:5173
```

**Run migrations manually:**

```bash
cd backend
alembic upgrade head
```

**Keyboard shortcuts in the editor:**

| Shortcut | Action |
|---|---|
| `Ctrl + Enter` | Run code |
| `Ctrl + Shift + Enter` | Submit solution |

---

## 📊 Analytics

After solving problems, the Analytics page shows:

- **Daily activity** calendar heatmap
- **Topic mastery** scores ranked by struggle index
- **Error pattern** breakdown (SyntaxError, TypeError, TLE, WrongAnswer, etc.)
- **Solve rate** and streak tracking over time

Topic mastery refreshes in the background with a 5-minute cooldown to avoid unnecessary DB load.

---

## 🤖 AI Coach

Powered by OpenAI GPT-4o. Three modes available from the problem page:

| Mode | Trigger | What it does |
|---|---|---|
| **AI Hints** | Anytime | Socratic nudges — guides you without giving away the answer |
| **Why did I fail?** | After a wrong answer | Explains which test cases failed and why your logic broke |
| **Review my code** | After an accepted solution | Time/space complexity analysis and style suggestions |

Set your API key in **Settings** (stored encrypted in the database) or via `OPENAI_API_KEY` in `.env`.

---

## 📄 License

[MIT](./LICENSE)
