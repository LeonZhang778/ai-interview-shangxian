path = "/home/deploy/ai-interview/ai-interview-backend/docker-compose.yml"
with open(path, "r") as f:
    lines = f.readlines()

result = []
in_celery_worker = False
in_celery_beat = False

for i, line in enumerate(lines):
    result.append(line)
    stripped = line.strip()

    if "celery-worker:" in line:
        in_celery_worker = True
        in_celery_beat = False
    elif "celery-beat:" in line:
        in_celery_worker = False
        in_celery_beat = True
    elif stripped.endswith(":") and not stripped.startswith("#") and not stripped.startswith("-"):
        if "celery" not in stripped:
            in_celery_worker = False
            in_celery_beat = False

    if (in_celery_worker or in_celery_beat) and stripped == "- REDIS_HOST=redis":
        result.append("      - REDIS_PASSWORD=R3d!s_A1_2026_Sec\n")

with open(path, "w") as f:
    f.writelines(result)
print("Done")
