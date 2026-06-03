-- ============================================================
-- Office Task Manager — Supabase Table Setup
-- Run this ONCE in Supabase SQL Editor
-- ============================================================

CREATE TABLE IF NOT EXISTS tasks (
    id             BIGSERIAL PRIMARY KEY,
    title          TEXT NOT NULL,
    description    TEXT,
    department     TEXT,
    assigned_to    TEXT,
    priority       TEXT DEFAULT 'Medium',
    start_date     DATE,
    due_date       DATE,
    follow_up_date DATE,
    status         TEXT DEFAULT 'Not Started',
    remarks        TEXT,
    created_at     TIMESTAMPTZ DEFAULT NOW(),
    updated_at     TIMESTAMPTZ DEFAULT NOW()
);

-- Index for faster filtering
CREATE INDEX IF NOT EXISTS idx_tasks_status       ON tasks(status);
CREATE INDEX IF NOT EXISTS idx_tasks_due_date     ON tasks(due_date);
CREATE INDEX IF NOT EXISTS idx_tasks_assigned_to  ON tasks(assigned_to);
CREATE INDEX IF NOT EXISTS idx_tasks_department   ON tasks(department);
CREATE INDEX IF NOT EXISTS idx_tasks_follow_up    ON tasks(follow_up_date);

-- Allow public read/write (since we use anon key in Streamlit)
ALTER TABLE tasks ENABLE ROW LEVEL SECURITY;

CREATE POLICY "Allow all for anon" ON tasks
    FOR ALL
    TO anon
    USING (true)
    WITH CHECK (true);

-- ============================================================
-- DONE. Your table is ready.
-- ============================================================
