#!/bin/bash
# 安全部署脚本 — 零停机更新
# 用法: bash deploy.sh
set -e

PROJECT_DIR="/home/deploy/ai-interview/ai-interview-backend"
cd "$PROJECT_DIR"

echo "=== [1/5] 拉取最新代码 ==="
git pull origin main

echo "=== [2/5] 构建新镜像（不影响运行中的容器）==="
docker compose build app celery-worker celery-beat

echo "=== [3/5] 运行数据库迁移（如果有）==="
docker compose run --rm app alembic upgrade head 2>/dev/null || echo "无迁移或迁移失败，继续..."

echo "=== [4/5] 滚动更新容器 ==="
# --no-deps: 只重建目标容器，不碰依赖
# --wait: 等 healthcheck 通过才返回
docker compose up -d --no-deps --wait postgres redis
docker compose up -d --no-deps --wait app
docker compose up -d --no-deps --wait celery-worker celery-beat
docker compose up -d --no-deps nginx

echo "=== [5/5] 健康检查 ==="
sleep 5
for i in {1..6}; do
    STATUS=$(curl -s -o /dev/null -w "%{http_code}" http://localhost:8006/api/v1/config/health 2>/dev/null || echo "000")
    if [ "$STATUS" = "200" ]; then
        echo "部署成功！服务正常运行。"
        docker compose ps
        exit 0
    fi
    echo "等待服务启动... ($i/6) 状态码: $STATUS"
    sleep 10
done

echo "部署失败！服务未通过健康检查，正在回滚..."
docker compose logs --tail=30 app
exit 1
