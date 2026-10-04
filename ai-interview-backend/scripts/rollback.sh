#!/usr/bin/env bash
# AI-Interview 一键回滚脚本（部署机本地执行）
#
# 作用：把 app / celery-worker / celery-beat 三个容器切回上一次部署成功
#       且验证过健康的镜像（由 CI 在每次部署前写入 .last_good_image）。
#
# ⚠️ 边界与限制（务必知悉）：
#   1. 本脚本只回滚「应用镜像」，不会回滚数据库迁移。若新版本已执行了迁移，
#      回退代码可能因 schema 不匹配而报错 —— 这类情况需要人工处理迁移。
#   2. 回滚目标依赖本地镜像仓库中仍保留该镜像。CI 的清理步骤已改为
#      「保留当前 + 回滚目标」，因此正常情况下回滚目标一定还在。
#   3. 前端 dist 由宿主机 nginx 直接挂载（不是镜像内容），所以回滚镜像
#      不会回滚前端。前端如需回退请用 git 操作 dist 目录。
#
# 用法：
#   bash scripts/rollback.sh                 # 回滚到 .last_good_image
#   bash scripts/rollback.sh --list          # 列出本地可用的后端镜像
#   bash scripts/rollback.sh <image_ref>     # 回滚到指定镜像

set -Eeuo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
BACKEND_DIR="$(dirname "$SCRIPT_DIR")"
cd "$BACKEND_DIR"

LAST_GOOD_FILE=".last_good_image"
HEALTH_URL="http://localhost:8006/api/v1/config/health"
SERVICES=(app celery-worker celery-beat)

log() { echo "[$(date '+%Y-%m-%d %H:%M:%S')] $*"; }

current_image() {
  docker inspect --format='{{.Config.Image}}' ai-interview-app 2>/dev/null || true
}

repo_of() {
  # 去掉 tag，得到镜像仓库名，用于 docker image ls 过滤
  echo "${1%:*}"
}

list_images() {
  local repo
  repo="$(repo_of "$(current_image)")"
  if [ -z "$repo" ]; then
    log "无法识别当前镜像仓库；列出全部本地镜像（前 30 行）"
    docker image ls | head -30
    return 0
  fi
  log "仓库 $repo 下的本地镜像（按创建时间倒序）："
  docker image ls "$repo" --format '{{.Repository}}:{{.Tag}}\t{{.CreatedSince}}\t{{.Size}}'
}

# ---------- 解析参数 ----------
target=""
case "${1:-}" in
  --list|-l)
    list_images
    exit 0
    ;;
  "" )
    if [ ! -s "$LAST_GOOD_FILE" ]; then
      log "FATAL: 未找到 $LAST_GOOD_FILE，无法确定回滚目标。"
      log "       请用 'bash scripts/rollback.sh --list' 查看可用镜像，再显式指定。"
      exit 1
    fi
    target="$(cat "$LAST_GOOD_FILE")"
    ;;
  *)
    target="$1"
    ;;
esac

# ---------- 校验目标 ----------
if ! docker image inspect "$target" >/dev/null 2>&1; then
  log "FATAL: 本地不存在镜像 $target"
  list_images
  exit 1
fi

current="$(current_image)"
log "当前镜像: ${current:-未知}"
log "回滚目标: $target"

if [ "$current" = "$target" ]; then
  log "当前已运行该镜像，无需回滚。"
  exit 0
fi

log "开始回滚（仅 app / celery-worker / celery-beat）..."
export BACKEND_IMAGE="$target"

for svc in "${SERVICES[@]}"; do
  log "  重建容器: $svc"
  docker compose up -d --force-recreate --no-deps "$svc"
done

# ---------- 健康检查 ----------
log "等待应用恢复健康（最多 120s）..."
healthy=false
for i in $(seq 1 24); do
  code=$(docker exec ai-interview-app python -c \
    "import urllib.request; print(urllib.request.urlopen('$HEALTH_URL', timeout=5).status)" 2>/dev/null || true)
  if [ "$code" = "200" ]; then
    healthy=true
    break
  fi
  log "  等待中 ($i/24)，health=$code"
  sleep 5
done

if [ "$healthy" != "true" ]; then
  log "❌ 回滚后应用仍未通过健康检查，需要人工介入。最近日志："
  docker logs ai-interview-app --tail 80 || true
  exit 1
fi

# 回滚成功后，把「上个目标」记为新的回滚目标会丢信息，因此这里保留文件不动，
# 由下一次 CI 部署时重新写入。
log "✅ 回滚完成，应用健康。当前镜像: $target"
log "提示：若本次回滚涉及数据库 schema 变更，请人工确认数据库状态。"
docker compose ps
