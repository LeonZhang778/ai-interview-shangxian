"""Fix docker-compose.yml on the server with all required overrides."""
path = "/home/deploy/ai-interview/ai-interview-backend/docker-compose.yml"

with open(path, "r") as f:
    content = f.read()

# 1. Add environment section to app service (after env_file)
content = content.replace(
    """  app:
    image: ai-interview-backend-app:latest
    container_name: ai-interview-app
    restart: unless-stopped
    env_file:
      - .env
    volumes:""",
    """  app:
    image: ai-interview-backend-app:latest
    container_name: ai-interview-app
    restart: unless-stopped
    env_file:
      - .env
    environment:
      - POSTGRES_HOST=postgres
      - REDIS_HOST=redis
      - REDIS_PASSWORD=R3d!s_A1_2026_Sec
    volumes:"""
)

# 2. Add environment + uploads volume to celery-worker
content = content.replace(
    """  celery-worker:
    image: ai-interview-backend-celery-worker:latest
    container_name: ai-interview-celery-worker
    restart: unless-stopped
    command: celery -A app.core.celery_app worker --loglevel=info
    env_file:
      - .env
    volumes:
      - ./logs:/app/logs
    depends_on:""",
    """  celery-worker:
    image: ai-interview-backend-celery-worker:latest
    container_name: ai-interview-celery-worker
    restart: unless-stopped
    command: celery -A app.core.celery_app worker --loglevel=info
    env_file:
      - .env
    environment:
      - POSTGRES_HOST=postgres
      - REDIS_HOST=redis
      - REDIS_PASSWORD=R3d!s_A1_2026_Sec
    volumes:
      - ./logs:/app/logs
      - ./uploads:/app/uploads
    depends_on:"""
)

# 3. Add environment to celery-beat
content = content.replace(
    """  celery-beat:
    image: ai-interview-backend-celery-beat:latest
    container_name: ai-interview-celery-beat
    restart: unless-stopped
    command: celery -A app.core.celery_app beat --loglevel=info
    env_file:
      - .env
    volumes:
      - ./logs:/app/logs
    depends_on:
      redis:""",
    """  celery-beat:
    image: ai-interview-backend-celery-beat:latest
    container_name: ai-interview-celery-beat
    restart: unless-stopped
    command: celery -A app.core.celery_app beat --loglevel=info
    env_file:
      - .env
    environment:
      - POSTGRES_HOST=postgres
      - REDIS_HOST=redis
      - REDIS_PASSWORD=R3d!s_A1_2026_Sec
    volumes:
      - ./logs:/app/logs
    depends_on:
      redis:"""
)

# 4. Add Redis password command
content = content.replace(
    """  redis:
    image: redis:7-alpine
    container_name: ai-interview-redis
    restart: unless-stopped
    volumes:""",
    """  redis:
    image: redis:7-alpine
    container_name: ai-interview-redis
    restart: unless-stopped
    command: redis-server --requirepass R3d!s_A1_2026_Sec
    volumes:"""
)

# 5. Fix Redis healthcheck
content = content.replace(
    '      test: ["CMD", "redis-cli", "ping"]',
    '      test: ["CMD", "redis-cli", "-a", "R3d!s_A1_2026_Sec", "ping"]'
)

with open(path, "w") as f:
    f.write(content)

print("Done! Verifying...")

# Verify
with open(path, "r") as f:
    text = f.read()
    checks = [
        "POSTGRES_HOST=postgres",
        "REDIS_HOST=redis",
        "REDIS_PASSWORD=R3d!s_A1_2026_Sec",
        "--requirepass",
        "./uploads:/app/uploads",
    ]
    for c in checks:
        count = text.count(c)
        print(f"  {c}: {count} occurrences")
