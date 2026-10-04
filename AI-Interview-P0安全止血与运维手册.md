# AI-Interview · P0 安全止血与运维手册

> 适用范围：单机部署（1 台服务器 / 约 100 用户规模）。
> 设计原则：**不为这个规模引入不必要的分布式复杂度**（例如放弃 Redis 主从与多副本），
> 只做「单机做到位」的加固，并把每一笔代价都花在真正会被利用的风险上。

---

## 一、本轮改了什么

| 类别 | 改动 | 文件 |
| --- | --- | --- |
| JWT 密钥 | 生产环境 SECRET_KEY 为空 / 占位值 / 长度 < 32 时**拒绝启动**；CI 缺失或弱值时自动生成强随机密钥（已有强值则原样保留，避免每次部署把所有人踢下线） | `app/core/config.py`、`.github/workflows/main.yml` |
| 凭据泄露 | 清除 7 个**被 git 跟踪**文件中的服务器 root 口令与库口令明文，改为读环境变量（缺失即报错） | `create_exp_tables.py`、`deploy_experiences.py`、`deploy_image_files.py`、`insert_seed.py`、`insert_seed2.py`、`scripts/create_first_admin.py`、`scripts/codepus-agent/ssh_check.py` |
| XSS | 面试页 AI 输出改为「先 HTML 转义、再拼 `<br>`」；抽出公共 `escapeHtml` 并让公告页复用 | `frontend/src/utils/html.js`、`views/Interview.vue`、`views/AnnouncementDetail.vue` |
| 存储暴露 | PostgreSQL 端口由 `5434:5432`（全网卡）改为 `127.0.0.1:5434:5432`；Redis 开启 AOF 持久化 | `docker-compose.yml` |
| 资源与日志 | 全部容器加 `mem_limit`（env 可覆盖）与 `json-file` 日志轮转（10m × 3） | `docker-compose.yml` |
| 备份 | 新增每日备份脚本（PG + Redis + uploads + .env，带磁盘余量检查、非空校验、保留策略、可选异地） | `scripts/backup.sh` |
| 回滚 | 新增一键回滚脚本；CI 部署前记录 last-good 镜像、应用起不来时自动回滚、镜像清理改为**保留回滚目标** | `scripts/rollback.sh`、`.github/workflows/main.yml` |

### 顺带修正的两个认知错误

1. `docker-compose.prod.yml` **从未被 CI 加载**（CI 只跑 `docker compose up -d`，不带 `-f`），
   所以它里面的日志轮转、`ports: []`、Redis AOF 一直没生效。加固项已全部下沉到基础文件。
2. 面试页的 XSS 是**自伤型**（只有你自己浏览器会执行），不是跨用户盗号——
   管理端没有任何 `v-html`，面经与公告都做了转义 / 白名单。严重度比初判低，但仍是真实缺陷。

---

## 二、⚠️ 必须由你执行的密钥轮换

git 历史中残留过以下凭据（按你的决定**不改写历史**），因此**轮换是唯一彻底的出路**：
历史里翻出来也没有用，前提是它们已经失效。

| # | 凭据 | 用途 | 去哪儿换 | GitHub Secret 名 | 生效方式 |
| --- | --- | --- | --- | --- | --- |
| 1 | **服务器 root 口令**（`5408854088Ab@`） | SSH 登录部署机 | 服务器上 `passwd` 改 root 口令 | 无（本地脚本改读 `DEPLOY_SSH_PASS` 环境变量） | 改完即刻生效；**优先级最高** |
| 2 | **后台管理员口令**（与 root 口令相同，账号 `1448203623@qq.com`） | 登录管理后台 | 管理端「设置 / 账号」改密码 | 无 | 改完即刻生效；**优先级次高** |
| 3 | `SECRET_KEY` | JWT 签名 | 无需第三方，重新生成即可 | 不需要（CI 自动生成并写入部署机 `.env`） | 下次部署自动生效；**会导致全体用户需重新登录一次** |
| 4 | `POSTGRES_PASSWORD` | 数据库口令 | 生成新的强口令 | `POSTGRES_PASSWORD` | 更新 Secret 后重新部署：CI 会 `ALTER ROLE` 同步 |
| 5 | `REDIS_PASSWORD` | Redis 口令 | 生成新的强口令 | `REDIS_PASSWORD` | 更新 Secret 后重新部署 |
| 6 | `AI_API_KEY` / `XAI_API_KEY` | Grok 中转站 | 中转站后台重置 | `AI_API_KEY` | 更新 Secret 后重新部署 |
| 7 | `AI_QWEN_API_KEY` | 阿里云 DashScope | 阿里云百炼控制台 | `AI_QWEN_API_KEY` | 同上 |
| 8 | `POLLINATIONS_API_KEY` | 生图服务 | 对应服务后台 | `POLLINATIONS_API_KEY` | 同上 |
| 9 | `MAIL_PASSWORD`（QQ 邮箱授权码） | 邮件发送 | QQ 邮箱 → 设置 → 重新生成授权码 | **不在 CI 托管范围内**，需手工改部署机 `.env` | 手工编辑后 `docker compose up -d app` 重启 |

**已完成**：7 个被跟踪文件里的 root 口令 / 库口令明文已清除，所以从现在起仓库里不再有可用凭据。
**未做（需你决定）**：git **历史**中的旧值仍然存在，`git log -p` 能看到。若将来仓库转为公开或增加协作者，
建议再做一次历史重写。

---

## 三、备份

### 自动备份（已由 CI 安装）

CI 每次部署都会注册 systemd timer，**直接以仓库内的脚本路径**执行
（`/home/deploy/ai-interview/ai-interview-backend/scripts/backup.sh`，
并显式设置 `BACKEND_DIR`），时间：**每天 03:30**，`Persistent=true` 时错过的任务开机补跑。

> 注意：不要把脚本 `install` 到 `/usr/local/bin` 再执行 —— 那样脚本会以为自己在仓库里，
> 从而推不出后端目录、找不到 `.env`。脚本已内置目录校验与 `BACKEND_DIR` 兜底，
> 但让 systemd 直接用仓库路径最省事。

```bash
systemctl list-timers 'ai-interview-backup*'      # 查看下次执行时间
systemctl start ai-interview-backup.service       # 立即手动跑一次
journalctl -u ai-interview-backup -n 50           # 看执行日志
```

### 手工执行

```bash
cd /home/deploy/ai-interview/ai-interview-backend
bash scripts/backup.sh
BACKUP_RETENTION_DAYS=30 bash scripts/backup.sh                      # 自定义保留天数
RCLONE_REMOTE=oss:my-bucket/ai-interview bash scripts/backup.sh      # 额外上传异地
```

产物落在 `/home/deploy/ai-interview/backups/`：
`postgres-*.dump`（`pg_dump -Fc`）、`redis-*.rdb`、`uploads-*.tar.gz`、`env-*.backup`。

脚本的行为约定（有意为之，不要改回去）：

- 任何一步失败都**非零退出**，不用 `|| echo` 吞错误——静默失败的备份比没有备份更危险。
- 可用空间不足 1GB 直接中止，避免写半截文件还占满磁盘。
- 每份产物都做 `test -s` 非空校验。

### ⚠️ 单机备份的天花板

只留在同一台机器上，**无法抵御整机损坏 / 磁盘损毁 / 误删整目录**。
要真正兜住这些场景，至少做一件事：配置 `RCLONE_REMOTE` 把备份传到对象存储
（阿里云 OSS / 腾讯云 COS / 任意 rclone 后端都可以）。

### 恢复演练（务必在非高峰期实际跑一遍，别等出事才第一次用）

```bash
cd /home/deploy/ai-interview/ai-interview-backend

# 1) PostgreSQL（--clean 会先删除同名对象，等价于覆盖式恢复）
docker cp backups/postgres-<时间戳>.dump ai-interview-postgres:/tmp/restore.dump
docker exec -i ai-interview-postgres pg_restore -U postgres -d postgres \
  --clean --if-exists --no-owner /tmp/restore.dump

# 2) Redis 快照
docker cp backups/redis-<时间戳>.rdb ai-interview-redis:/data/dump.rdb
docker restart ai-interview-redis

# 3) 上传文件
tar -xzf backups/uploads-<时间戳>.tar.gz
```

---

## 四、回滚

```bash
cd /home/deploy/ai-interview/ai-interview-backend
bash scripts/rollback.sh              # 回滚到上一次部署成功的镜像
bash scripts/rollback.sh --list       # 查看本地可用镜像
bash scripts/rollback.sh <image_ref>  # 回滚到指定镜像
```

CI 侧行为：

- 部署前把当前正在运行的镜像写入 `.last_good_image`。
- 若新镜像**应用起不来**（健康检查超时）→ 自动回滚并继续报失败，避免「发布即宕机」。
- 镜像清理步骤已改为**保留当前 + 回滚目标**（此前是把非当前镜像全部删除，等于根本没有回滚目标）。

### 回滚的边界（重要）

- **不回滚数据库迁移**。若新版本已执行过迁移，回退代码可能与 schema 不匹配。
  因此 CI 在**迁移失败时不会自动回滚**，而是明确报错要求人工介入——强行回滚只会造成
  schema 与代码不一致，比停下来更糟。
- **不回滚前端**。前端 `dist/` 是宿主机目录挂载给 nginx 的，不是镜像内容，需要 git 操作。

---

## 五、内存上限调优

基础 compose 已给每个容器设了上限（可用部署机 `.env` 覆盖，无需改代码）：

| 服务 | 默认上限 | 覆盖变量 |
| --- | --- | --- |
| app | 768m | `APP_MEM_LIMIT` |
| celery-worker | 768m | `CELERY_WORKER_MEM_LIMIT` |
| celery-beat | 128m | `CELERY_BEAT_MEM_LIMIT` |
| postgres | 768m | `POSTGRES_MEM_LIMIT` |
| redis | 256m | `REDIS_MEM_LIMIT` |
| nginx | 128m | `NGINX_MEM_LIMIT` |

这些是**上限而非预留**，不会一上来就吃掉内存。CI 现在会在部署日志里打印 `free -h`，
部署后请对照实际内存调一次：内存较小（2G 及以下）就往下调，例如
`APP_MEM_LIMIT=512m`、`POSTGRES_MEM_LIMIT=512m`。

Redis **没有**设置 `maxmemory-policy`：它同时是 Celery broker，一旦启用 LRU 淘汰会
**静默丢弃任务消息**，所以只用容器上限兜底，宁可 OOM 也不要静默丢数据。

---

## 六、验收清单

1. **部署后确认密钥已生效**：CI 日志里应出现
   `SECRET_KEY: preserved (已有强密钥)` 或 `generated (...)`。
2. **验证弱密钥已无法启动**（本地）：
   ```bash
   ENV=production SECRET_KEY=your-secret-key-change-in-production \
     python -c "from app.core.config import Settings; Settings()"
   ```
   预期：抛 `ValidationError`。
3. **验证端口已收敛**：服务器上 `ss -tlnp | grep -E '5434|6379'`，
   应只有 `127.0.0.1` 在监听，不应出现 `0.0.0.0`。
4. **验证日志轮转生效**：`docker inspect ai-interview-app --format '{{json .HostConfig.LogConfig}}'`。
5. **验证备份**：`systemctl start ai-interview-backup.service` 后检查
   `/home/deploy/ai-interview/backups/` 是否生成 4 类文件。
6. **验证 XSS 修复**：面试中让 AI 输出含 `<b>test</b>` 的内容，页面应显示**字面文本**
   而不是加粗。
7. **强制刷新前端**：`Ctrl+F5`，确认加载的是新 chunk。

---

## 七、尚未解决（按建议顺序）

| 项 | 为什么还没做 |
| --- | --- |
| 9 张表缺少 Alembic 迁移 | 需要逐表核对现有生产库结构再补迁移，属于有数据风险的操作，建议单独一轮做 |
| CI 质量门禁只有 5 条样本的关键词脚本 | 需要先让 pytest 全绿（现有 2 个失败测试是历史遗留的 mock 缺陷）再接入 |
| 无监控 / 无告警 / 无 trace_id | 需要选型（如 Sentry + Prometheus），涉及成本决策 |
| 核心链路未异步化（评估/报告仍在请求协程内） | 改动面大，会触及面试流核心逻辑，建议与「Alembic 补齐」分开做 |
| 全站无 i18n / a11y / SSR | 属产品化工作，非止血项 |
