-- Enable TimescaleDB extension
CREATE EXTENSION IF NOT EXISTS timescaledb CASCADE;

-- Enable pgcrypto for UUID generation
CREATE EXTENSION IF NOT EXISTS pgcrypto;

-- Enable pg_stat_statements for query analysis
CREATE EXTENSION IF NOT EXISTS pg_stat_statements;

-- ─── ENUM TYPES ───────────────────────────────────────────────────────────────

CREATE TYPE difficulty_enum AS ENUM ('Easy', 'Medium', 'Hard');
-- insight_type_enum kept for reference; ai_insights.insight_type uses VARCHAR(50) for flexibility

-- ─── PROBLEMS TABLE ───────────────────────────────────────────────────────────

CREATE TABLE IF NOT EXISTS users (
    id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    email       VARCHAR(255) UNIQUE NOT NULL,
    username    VARCHAR(100) UNIQUE NOT NULL,
    hashed_pw   VARCHAR(255) NOT NULL,
    is_active   BOOLEAN DEFAULT true,
    is_admin    BOOLEAN DEFAULT false,
    created_at  TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_users_email    ON users(email);
CREATE INDEX idx_users_username ON users(username);

CREATE TABLE IF NOT EXISTS problems (
    id              SERIAL PRIMARY KEY,
    slug            VARCHAR(200) UNIQUE NOT NULL,
    title           VARCHAR(300) NOT NULL,
    difficulty      difficulty_enum NOT NULL,
    category        VARCHAR(100) NOT NULL,
    subcategory     VARCHAR(100),
    leetcode_url    TEXT,
    description     TEXT DEFAULT '',
    starter_code    TEXT DEFAULT 'def solution():\n    pass\n',
    test_cases      JSONB DEFAULT '[]',
    hints           JSONB DEFAULT '[]',
    tags            JSONB DEFAULT '[]',
    constraints     TEXT DEFAULT '',
    input_params    JSONB DEFAULT '[]',
    output_type     TEXT DEFAULT '',
    is_new          BOOLEAN DEFAULT false,
    created_at      TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_problems_category ON problems(category);
CREATE INDEX idx_problems_difficulty ON problems(difficulty);
CREATE INDEX idx_problems_slug ON problems(slug);

-- ─── SESSIONS TABLE (TimescaleDB hypertable) ──────────────────────────────────

CREATE TABLE IF NOT EXISTS sessions (
    id                  UUID DEFAULT gen_random_uuid(),
    started_at          TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    ended_at            TIMESTAMPTZ,
    problems_attempted  INT DEFAULT 0,
    problems_solved     INT DEFAULT 0,
    total_time_secs     INT DEFAULT 0,
    PRIMARY KEY (id, started_at)
);

SELECT create_hypertable('sessions', 'started_at', if_not_exists => TRUE);

-- ─── PROBLEM ATTEMPTS TABLE (TimescaleDB hypertable) ─────────────────────────

CREATE TABLE IF NOT EXISTS problem_attempts (
    id                  UUID DEFAULT gen_random_uuid(),
    user_id             UUID NOT NULL DEFAULT '00000000-0000-0000-0000-000000000001',
    problem_id          INT NOT NULL REFERENCES problems(id) ON DELETE CASCADE,
    session_id          UUID,
    submitted_at        TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    started_at          TIMESTAMPTZ DEFAULT NOW(),
    attempt_number      SMALLINT NOT NULL DEFAULT 1,
    time_spent_secs     INT DEFAULT 0,
    code                TEXT DEFAULT '',
    is_correct          BOOLEAN DEFAULT false,
    is_first_attempt    BOOLEAN DEFAULT false,
    error_type          VARCHAR(50),
    error_message       TEXT,
    stdout              TEXT,
    test_results        JSONB DEFAULT '[]',
    PRIMARY KEY (id, submitted_at)
);

SELECT create_hypertable('problem_attempts', 'submitted_at', if_not_exists => TRUE);

CREATE INDEX idx_attempts_problem_id ON problem_attempts(problem_id, submitted_at DESC);
CREATE INDEX idx_attempts_is_correct ON problem_attempts(is_correct, submitted_at DESC);
CREATE INDEX idx_attempts_error_type ON problem_attempts(error_type, submitted_at DESC);

-- ─── PROBLEM PROGRESS TABLE (one row per problem) ─────────────────────────────

CREATE TABLE IF NOT EXISTS problem_progress (
    problem_id          INT NOT NULL REFERENCES problems(id) ON DELETE CASCADE,
    user_id             UUID NOT NULL DEFAULT '00000000-0000-0000-0000-000000000001',
    first_seen_at       TIMESTAMPTZ DEFAULT NOW(),
    solved_at           TIMESTAMPTZ,
    total_attempts      INT DEFAULT 0,
    total_time_secs     INT DEFAULT 0,
    is_starred          BOOLEAN DEFAULT false,
    confidence          SMALLINT DEFAULT 0 CHECK (confidence BETWEEN 0 AND 5),
    notes               TEXT DEFAULT '',
    best_solution       TEXT DEFAULT '',
    last_attempted_at   TIMESTAMPTZ,
    PRIMARY KEY (problem_id, user_id)
);

CREATE INDEX idx_progress_solved_at ON problem_progress(solved_at);
CREATE INDEX idx_progress_starred ON problem_progress(is_starred);

-- ─── ERROR PATTERNS TABLE (TimescaleDB hypertable) ───────────────────────────

CREATE TABLE IF NOT EXISTS error_patterns (
    id              UUID DEFAULT gen_random_uuid(),
    user_id         UUID NOT NULL DEFAULT '00000000-0000-0000-0000-000000000001',
    attempt_id      UUID,
    problem_id      INT NOT NULL REFERENCES problems(id) ON DELETE CASCADE,
    occurred_at     TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    error_category  VARCHAR(50),
    error_message   TEXT,
    code_snippet    TEXT,
    category        VARCHAR(100),
    difficulty      difficulty_enum,
    ai_diagnosis    TEXT,
    PRIMARY KEY (id, occurred_at)
);

SELECT create_hypertable('error_patterns', 'occurred_at', if_not_exists => TRUE);

CREATE INDEX idx_errors_category ON error_patterns(error_category, occurred_at DESC);
CREATE INDEX idx_errors_problem ON error_patterns(problem_id, occurred_at DESC);

-- ─── AI INSIGHTS TABLE ───────────────────────────────────────────────────────

CREATE TABLE IF NOT EXISTS ai_insights (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id         UUID NOT NULL DEFAULT '00000000-0000-0000-0000-000000000001',
    generated_at    TIMESTAMPTZ DEFAULT NOW(),
    insight_type    VARCHAR(50) NOT NULL,
    content         TEXT NOT NULL,
    input_context   JSONB DEFAULT '{}',
    tokens_used     INT DEFAULT 0,
    model           VARCHAR(50) DEFAULT 'gpt-4o'
);

CREATE INDEX idx_insights_type ON ai_insights(insight_type, generated_at DESC);

-- ─── LEARNING MILESTONES TABLE ───────────────────────────────────────────────

CREATE TABLE IF NOT EXISTS learning_milestones (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id         UUID NOT NULL DEFAULT '00000000-0000-0000-0000-000000000001',
    achieved_at     TIMESTAMPTZ DEFAULT NOW(),
    milestone_type  VARCHAR(100) NOT NULL,
    description     TEXT NOT NULL,
    metadata        JSONB DEFAULT '{}'
);

-- ─── TOPIC MASTERY TABLE (cached, recomputed periodically) ───────────────────

CREATE TABLE IF NOT EXISTS topic_mastery (
    category            VARCHAR(100) NOT NULL,
    user_id             UUID NOT NULL DEFAULT '00000000-0000-0000-0000-000000000001',
    total_problems      INT DEFAULT 0,
    solved              INT DEFAULT 0,
    easy_solved         INT DEFAULT 0,
    medium_solved       INT DEFAULT 0,
    hard_solved         INT DEFAULT 0,
    avg_attempts        FLOAT DEFAULT 0,
    avg_time_secs       INT DEFAULT 0,
    struggle_index      FLOAT DEFAULT 0,
    mastery_score       FLOAT DEFAULT 0,
    last_updated        TIMESTAMPTZ DEFAULT NOW(),
    PRIMARY KEY (category, user_id)
);

-- ─── CONTINUOUS AGGREGATE: daily_stats ───────────────────────────────────────
-- Auto-refreshed by TimescaleDB every hour from problem_attempts hypertable

CREATE MATERIALIZED VIEW IF NOT EXISTS daily_stats
WITH (timescaledb.continuous) AS
SELECT
    time_bucket('1 day', submitted_at)  AS day,
    COUNT(*)                            AS total_attempts,
    COUNT(*) FILTER (WHERE is_correct)  AS solved,
    COUNT(*) FILTER (WHERE is_first_attempt AND is_correct) AS first_attempt_wins,
    COUNT(DISTINCT problem_id)          AS problems_touched,
    SUM(time_spent_secs)                AS total_time_secs,
    COUNT(*) FILTER (WHERE NOT is_correct) AS errors_count
FROM problem_attempts
GROUP BY day
WITH NO DATA;

SELECT add_continuous_aggregate_policy('daily_stats',
    start_offset => INTERVAL '30 days',
    end_offset   => INTERVAL '1 hour',
    schedule_interval => INTERVAL '1 hour',
    if_not_exists => TRUE
);

-- ─── APP SETTINGS TABLE (encrypted key-value store) ─────────────────────────

CREATE TABLE IF NOT EXISTS app_settings (
    key        VARCHAR(100) PRIMARY KEY,
    value      TEXT NOT NULL,            -- Fernet-encrypted ciphertext
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- ─── SEED: default topic mastery rows (populated on first run) ────────────────
-- (Actual data comes from the seed script in the backend)
