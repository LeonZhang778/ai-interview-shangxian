path = "/home/deploy/ai-interview/ai-interview-backend/docker-compose.yml"
with open(path, "r") as f:
    content = f.read()

old = """  postgres:
    image: postgres:16-alpine
    container_name: ai-interview-postgres
    restart: unless-stopped
    environment:"""

new = """  postgres:
    image: postgres:16-alpine
    container_name: ai-interview-postgres
    restart: unless-stopped
    ports:
      - "5434:5432"
    environment:"""

if old in content:
    content = content.replace(old, new)
    with open(path, "w") as f:
        f.write(content)
    print("Done")
else:
    print("Pattern not found")
