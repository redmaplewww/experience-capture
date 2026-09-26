CREATE EXTENSION IF NOT EXISTS vector;
CREATE TABLE IF NOT EXISTS workspaces (id TEXT PRIMARY KEY, name TEXT NOT NULL, auto_approve_threshold REAL NOT NULL DEFAULT 0.92);
CREATE TABLE IF NOT EXISTS agents (id TEXT PRIMARY KEY, workspace_id TEXT NOT NULL REFERENCES workspaces(id));
CREATE TABLE IF NOT EXISTS sessions (id TEXT PRIMARY KEY, workspace_id TEXT NOT NULL REFERENCES workspaces(id), agent_id TEXT, task_context JSONB, created_at TIMESTAMPTZ NOT NULL DEFAULT now());
CREATE TABLE IF NOT EXISTS experience_items (
  id TEXT PRIMARY KEY, workspace_id TEXT NOT NULL REFERENCES workspaces(id), scope_type TEXT NOT NULL, scope_id TEXT,
  title TEXT NOT NULL, statement TEXT NOT NULL, context TEXT, conditions JSONB NOT NULL DEFAULT '[]', procedure JSONB NOT NULL DEFAULT '[]',
  exceptions JSONB NOT NULL DEFAULT '[]', expected_outcome TEXT, counterexamples JSONB NOT NULL DEFAULT '[]',
  confidence REAL NOT NULL, quality_score REAL NOT NULL, freshness REAL NOT NULL DEFAULT 1, status TEXT NOT NULL,
  sensitivity_level TEXT NOT NULL DEFAULT 'normal', source_type TEXT NOT NULL, created_by TEXT NOT NULL,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(), updated_at TIMESTAMPTZ NOT NULL DEFAULT now(), expires_at TIMESTAMPTZ
);
CREATE TABLE IF NOT EXISTS experience_evidence (id TEXT PRIMARY KEY, experience_id TEXT NOT NULL REFERENCES experience_items(id), kind TEXT NOT NULL, content TEXT NOT NULL, source_ref TEXT, created_at TIMESTAMPTZ NOT NULL DEFAULT now());
CREATE TABLE IF NOT EXISTS experience_versions (id TEXT PRIMARY KEY, experience_id TEXT NOT NULL REFERENCES experience_items(id), version INTEGER NOT NULL, snapshot JSONB NOT NULL, changed_by TEXT NOT NULL, reason TEXT, created_at TIMESTAMPTZ NOT NULL DEFAULT now());
CREATE TABLE IF NOT EXISTS experience_relations (from_id TEXT NOT NULL REFERENCES experience_items(id), to_id TEXT NOT NULL REFERENCES experience_items(id), relation TEXT NOT NULL, confidence REAL NOT NULL, PRIMARY KEY(from_id,to_id,relation));
CREATE TABLE IF NOT EXISTS taxonomy_nodes (id TEXT PRIMARY KEY, workspace_id TEXT NOT NULL REFERENCES workspaces(id), parent_id TEXT, name TEXT NOT NULL, path TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS tags (id TEXT PRIMARY KEY, workspace_id TEXT NOT NULL REFERENCES workspaces(id), name TEXT NOT NULL, UNIQUE(workspace_id,name));
CREATE TABLE IF NOT EXISTS experience_tags (experience_id TEXT NOT NULL REFERENCES experience_items(id), tag_id TEXT NOT NULL REFERENCES tags(id), weight REAL NOT NULL, source TEXT NOT NULL, PRIMARY KEY(experience_id,tag_id));
CREATE TABLE IF NOT EXISTS review_tasks (id TEXT PRIMARY KEY, workspace_id TEXT NOT NULL REFERENCES workspaces(id), experience_id TEXT NOT NULL REFERENCES experience_items(id), status TEXT NOT NULL, reason TEXT, created_at TIMESTAMPTZ NOT NULL DEFAULT now());
CREATE TABLE IF NOT EXISTS retrieval_feedback (id TEXT PRIMARY KEY, workspace_id TEXT NOT NULL REFERENCES workspaces(id), experience_id TEXT NOT NULL REFERENCES experience_items(id), useful BOOLEAN, adopted BOOLEAN, correction TEXT, created_at TIMESTAMPTZ NOT NULL DEFAULT now());
CREATE INDEX IF NOT EXISTS experience_scope_idx ON experience_items(workspace_id,scope_type,scope_id,status);
CREATE INDEX IF NOT EXISTS experience_text_idx ON experience_items USING GIN (to_tsvector('simple', title || ' ' || statement || ' ' || coalesce(context,'')));
