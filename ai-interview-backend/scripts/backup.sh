#!/usr/bin/env bash
# AI-Interview 每日备份脚本（部署机本地执行，建议由 systemd timer 驱动）
#
# 备份内容：
#   1. PostgreSQL 全库（pg_dump -Fc，可直接 pg_restore）
#   2. Redis 快照（BGSAVE 后的 dump.rdb）
#   3. uploads/ 上传文件（tar.gz）
#   4. .env 配置（含 SECRET_KEY 与各 API Key）
#
# 设计原则：
#   - 失败必须显式失败（非零退出），绝不 `|| echo` 吞掉错误 —— 静默失败的备份
#     比没有备份更危险，因为它会让人误以为数据是安全的。
#   - 每一步产物都做非空校验（test -s）。
#   - 带保留策略，避免磁盘被备份填满（磁盘写满会连带拖垮 PostgreSQL）。
#
# 用法：
#   bash scripts/backup.sh                    # 使用默认值
#   BACKUP_RETENTION_DAYS=30 bash scripts/backup.sh
#   RCLONE_REMOTE=oss:my-bucket/ai-interview bash scripts/backup.sh   # 额外上传异地

set -Eeuo pipefail

# ---------- 配置 ----------
# 定位后端目录（即含 .env 的目录）。
# 注意：本脚本可能被复制到 /usr/local/bin 后由 systemd 调用，那时 dirname 推出的
# 并不是仓库目录，因此必须显式校验「该目录下有没有 .env」，不能想当然。
resolve_backend_dir() {
  if [ -n "${BACKEND_DIR:-}" ] && [ -f "$BACKEND_DIR/.env" ]; then
    printf '%s' "$BACKEND_DIR"
    return 0
  fi
  local script_dir candidate
  script_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
  candidate="$(dirname "$script_dir")"
  if [ -f "$candidate/.env" ]; then
    printf '%s' "$candidate"
    return 0
  fi
  for fallback in \
    "/home/deploy/ai-interview/ai-interview-backend" \
    "$(pwd)"; do
    if [ -f "$fallback/.env" ]; then
      printf '%s' "$fallback"
      return 0
    fi
  done
  return 1
}

BACKEND_DIR="$(resolve_backend_dir)" || {
  echo "FATAL: 无法定位后端目录（未在候选路径下找到 .env）。" >&2
  echo "       请用 BACKEND_DIR=/path/to/ai-interview-backend 显式指定。" >&2
  exit 1
}
cd "$BACKEND_DIR"

BACKUP_DIR="${BACKUP_DIR:-/home/deploy/ai-interview/backups}"
RETENTION_DAYS="${BACKUP_RETENTION_DAYS:-14}"
POSTGRES_CONTAINER="${POSTGRES_CONTAINER:-ai-interview-postgres}"
REDIS_CONTAINER="${REDIS_CONTAINER:-ai-interview-redis}"
RCLONE_REMOTE="${RCLONE_REMOTE:-}"

timestamp="$(date +%Y%m%d%H%M%S)"
log() { echo "[$(date '+%Y-%m-%d %H:%M:%S')] $*"; }

mkdir -p "$BACKUP_DIR"
chmod 700 "$BACKUP_DIR"

# ---------- 读取 .env ----------
if [ ! -f .env ]; then
  log "FATAL: 未找到 $BACKEND_DIR/.env，无法获取数据库凭据"
  exit 1
fi

get_env() {
  # 取指定 key 的值；不存在则返回空。避免 `source .env` 带来的执行风险。
  sed -n "s/^$1=//p" .env | head -1
}

POSTGRES_USER="$(get_env POSTGRES_USER)"; POSTGRES_USER="${POSTGRES_USER:-postgres}"
POSTGRES_DB="$(get_env POSTGRES_DB)";     POSTGRES_DB="${POSTGRES_DB:-postgres}"
REDIS_PASSWORD="$(get_env REDIS_PASSWORD)"

# ---------- 前置检查 ----------
for c in "$POSTGRES_CONTAINER" "$REDIS_CONTAINER"; do
  if ! docker inspect "$c" >/dev/null 2>&1; then
    log "FATAL: 容器 $c 不存在，备份中止"
    exit 1
  fi
done

# 磁盘余量检查：低于 1GB 直接失败，避免写出半截备份并占满磁盘
avail_kb=$(df -Pk "$BACKUP_DIR" | awk 'NR==2 {print $4}')
if [ "${avail_kb:-0}" -lt 1048576 ]; then
  log "FATAL: $BACKUP_DIR 可用空间不足 1GB（当前 ${avail_kb}KB），备份中止"
  exit 1
fi

# ---------- 1) PostgreSQL ----------
pg_file="$BACKUP_DIR/postgres-$timestamp.dump"
log "备份 PostgreSQL -> $pg_file"
docker exec "$POSTGRES_CONTAINER" pg_dump -U "$POSTGRES_USER" -d "$POSTGRES_DB" -Fc > "$pg_file"
test -s "$pg_file"
chmod 600 "$pg_file"
log "  OK ($(du -h "$pg_file" | cut -f1))"

# ---------- 2) Redis ----------
redis_file="$BACKUP_DIR/redis-$timestamp.rdb"
log "备份 Redis -> $redis_file"
if [ -n "$REDIS_PASSWORD" ]; then
  docker exec "$REDIS_CONTAINER" redis-cli -a "$REDIS_PASSWORD" --no-auth-warning BGSAVE >/dev/null
else
  docker exec "$REDIS_CONTAINER" redis-cli BGSAVE >/dev/null
fi

# 等待 BGSAVE 完成（最多 60s）
redis_ok=false
for _ in $(seq 1 30); do
  if [ -n "$REDIS_PASSWORD" ]; then
    info=$(docker exec "$REDIS_CONTAINER" redis-cli -a "$REDIS_PASSWORD" --no-auth-warning INFO persistence 2>/dev/null || true)
  else
    info=$(docker exec "$REDIS_CONTAINER" redis-cli INFO persistence 2>/dev/null || true)
  fi
  if echo "$info" | grep -q 'rdb_bgsave_in_progress:0'; then
    redis_ok=true
    break
  fi
  sleep 2
done
if [ "$redis_ok" != "true" ]; then
  log "WARN: 未确认 BGSAVE 完成，仍尝试拷贝现有 dump.rdb"
fi

if docker cp "$REDIS_CONTAINER:/data/dump.rdb" "$redis_file" 2>/dev/null; then
  test -s "$redis_file"
  chmod 600 "$redis_file"
  log "  OK ($(du -h "$redis_file" | cut -f1))"
else
  log "WARN: Redis 未生成 dump.rdb（若为纯缓存/队列用途可忽略；如需保留队列请启用 appendonly）"
  rm -f "$redis_file"
fi

# ---------- 3) uploads ----------
uploads_file="$BACKUP_DIR/uploads-$timestamp.tar.gz"
if [ -d uploads ]; then
  log "备份 uploads -> $uploads_file"
  tar -czf "$uploads_file" uploads
  test -s "$uploads_file"
  chmod 600 "$uploads_file"
  log "  OK ($(du -h "$uploads_file" | cut -f1))"
else
  log "跳过 uploads（目录不存在）"
fi

# ---------- 4) .env ----------
env_file="$BACKUP_DIR/env-$timestamp.backup"
log "备份 .env -> $env_file"
cp -p .env "$env_file"
test -s "$env_file"
chmod 600 "$env_file"
log "  OK"

# ---------- 5) 异地副本（可选） ----------
if [ -n "$RCLONE_REMOTE" ]; then
  if ! command -v rclone >/dev/null 2>&1; then
    log "FATAL: 已设置 RCLONE_REMOTE 但未安装 rclone；异地备份未完成"
    exit 1
  fi
  log "上传到异地 $RCLONE_REMOTE"
  rclone copy "$BACKUP_DIR" "$RCLONE_REMOTE" \
    --include "postgres-$timestamp.dump" \
    --include "redis-$timestamp.rdb" \
    --include "uploads-$timestamp.tar.gz" \
    --include "env-$timestamp.backup"
  log "  异地上传完成"
else
  log "提示：未配置 RCLONE_REMOTE，本次仅本机备份。"
  log "      单机部署下，本机备份无法抵御整机/磁盘损毁，建议至少配置一个异地目标。"
fi

# ---------- 6) 保留策略 ----------
log "清理 ${RETENTION_DAYS} 天前的备份"
find "$BACKUP_DIR" -maxdepth 1 -type f \
  \( -name 'postgres-*.dump' -o -name 'redis-*.rdb' -o -name 'uploads-*.tar.gz' -o -name 'env-*.backup' \) \
  -mtime "+$RETENTION_DAYS" -print -delete

log "备份完成。当前备份目录："
ls -lh "$BACKUP_DIR" | tail -20
