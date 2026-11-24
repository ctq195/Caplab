-- CapLab on AgentArts: 持久化表结构
-- 云端硬约束：禁止本地磁盘状态，全部落 RDS PostgreSQL。
-- user_id + session_id 复合隔离，任何查询必须带两者。

CREATE EXTENSION IF NOT EXISTS vector;

CREATE TABLE IF NOT EXISTS caplab_state (
    user_id     TEXT NOT NULL,
    session_id  TEXT NOT NULL,
    revision    INTEGER NOT NULL,
    state_json  JSONB NOT NULL,
    updated_at  TIMESTAMPTZ NOT NULL DEFAULT now(),
    PRIMARY KEY (user_id, session_id)
);

CREATE TABLE IF NOT EXISTS caplab_revision (
    user_id     TEXT NOT NULL,
    session_id  TEXT NOT NULL,
    revision    INTEGER NOT NULL,
    patch_id    TEXT,
    state_json  JSONB NOT NULL,
    created_at  TIMESTAMPTZ NOT NULL DEFAULT now(),
    PRIMARY KEY (user_id, session_id, revision)
);

CREATE TABLE IF NOT EXISTS caplab_confirmation (
    confirmation_id   TEXT NOT NULL,
    user_id           TEXT NOT NULL,
    session_id        TEXT NOT NULL,
    patch_id          TEXT,
    decision          TEXT NOT NULL CHECK (decision IN ('confirm','partial','revise','reject')),
    scope             JSONB NOT NULL DEFAULT '[]'::jsonb,
    confirmation_text TEXT NOT NULL,
    recorded_at       TIMESTAMPTZ NOT NULL,
    PRIMARY KEY (user_id, session_id, confirmation_id)
);
CREATE INDEX IF NOT EXISTS idx_confirmation_scope ON caplab_confirmation (user_id, session_id, recorded_at);

CREATE TABLE IF NOT EXISTS caplab_invalidation (
    id               BIGSERIAL PRIMARY KEY,
    user_id          TEXT NOT NULL,
    session_id       TEXT NOT NULL,
    section          TEXT NOT NULL,
    caused_by_patch  TEXT,
    caused_by_section TEXT,
    at_revision      INTEGER NOT NULL,
    created_at       TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS idx_invalidation_scope ON caplab_invalidation (user_id, session_id, at_revision);

-- LangGraph checkpoint 与业务表分离：checkpointer 管流程恢复，业务表管事实版本。
CREATE TABLE IF NOT EXISTS caplab_checkpoint (
    thread_id  TEXT NOT NULL,
    checkpoint_id TEXT NOT NULL,
    parent_checkpoint_id TEXT,
    type       TEXT,
    checkpoint JSONB NOT NULL,
    metadata   JSONB,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    PRIMARY KEY (thread_id, checkpoint_id)
);

CREATE TABLE IF NOT EXISTS caplab_entitlement (
    user_id      TEXT PRIMARY KEY,
    knowledge_tier TEXT NOT NULL DEFAULT 'free' CHECK (knowledge_tier IN ('free','paid')),
    granted_by   TEXT,
    granted_at   TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS caplab_knowledge_card (
    card_id      TEXT PRIMARY KEY,
    tier         TEXT NOT NULL CHECK (tier IN ('free','paid')),
    card_type    TEXT NOT NULL,
    source_id    TEXT,
    claim_id     TEXT,
    quality      TEXT,
    content      TEXT NOT NULL,
    metadata     JSONB NOT NULL DEFAULT '{}'::jsonb,
    embedding    vector(512),
    updated_at   TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS idx_card_tier ON caplab_knowledge_card (tier, quality);
CREATE INDEX IF NOT EXISTS idx_card_embedding ON caplab_knowledge_card USING hnsw (embedding vector_cosine_ops);
