CREATE TABLE IF NOT EXISTS image_tasks (
    id              SERIAL PRIMARY KEY,
    user_id         INTEGER REFERENCES users(id) ON DELETE CASCADE,
    prompt          TEXT NOT NULL,
    negative_prompt TEXT,
    width           INTEGER DEFAULT 512,
    height          INTEGER DEFAULT 512,
    steps           INTEGER DEFAULT 20,
    cfg_scale       INTEGER DEFAULT 7,
    status          VARCHAR(20) DEFAULT 'pending',
    image_url       VARCHAR(500),
    error_message   TEXT,
    created_at      TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at      TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_image_tasks_user_id ON image_tasks(user_id);
CREATE INDEX IF NOT EXISTS idx_image_tasks_status ON image_tasks(status);
