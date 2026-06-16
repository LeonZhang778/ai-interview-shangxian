-- 面经文章表
CREATE TABLE IF NOT EXISTS experiences (
    id              SERIAL PRIMARY KEY,
    title           VARCHAR(200) NOT NULL,
    company         VARCHAR(50) NOT NULL,
    position        VARCHAR(50) NOT NULL,
    level           VARCHAR(20),
    round           VARCHAR(20),
    content         TEXT NOT NULL,
    summary         VARCHAR(500),
    view_count      INTEGER DEFAULT 0,
    like_count      INTEGER DEFAULT 0,
    collect_count   INTEGER DEFAULT 0,
    author_id       INTEGER REFERENCES users(id),
    is_anonymous    BOOLEAN DEFAULT true,
    status          VARCHAR(20) DEFAULT 'published',
    created_at      TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at      TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- 面经标签关联表
CREATE TABLE IF NOT EXISTS experience_tags (
    experience_id   INTEGER REFERENCES experiences(id) ON DELETE CASCADE,
    tag             VARCHAR(30),
    created_at      TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at      TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    PRIMARY KEY (experience_id, tag)
);

-- 用户收藏表
CREATE TABLE IF NOT EXISTS user_collections (
    user_id         INTEGER REFERENCES users(id) ON DELETE CASCADE,
    experience_id   INTEGER REFERENCES experiences(id) ON DELETE CASCADE,
    created_at      TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at      TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    PRIMARY KEY (user_id, experience_id)
);

-- 索引
CREATE INDEX IF NOT EXISTS idx_experiences_company ON experiences(company);
CREATE INDEX IF NOT EXISTS idx_experiences_position ON experiences(position);
CREATE INDEX IF NOT EXISTS idx_experiences_status ON experiences(status);
CREATE INDEX IF NOT EXISTS idx_experiences_created_at ON experiences(created_at DESC);
