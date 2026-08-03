# AI-Interview 部署交接日志

更新时间：2026-08-03  
仓库：`git@github.com:LeonZhang778/ai-interview-shangxian.git`  
服务器目录：`/home/deploy/ai-interview`

## 当前代码与部署状态

- 本地 `main` 已推送到 GitHub，最新提交为 `29b05a7 fix: make media task migration idempotent`。
- 服务器代码目录已更新到 `29b05a7`，`git status` 仅显示运行期目录：
  - `ai-interview-backend/uploads/media/`
  - `backups/`
- 服务器容器整体健康：
  - `ai-interview-app`：healthy
  - `ai-interview-postgres`：healthy
  - `ai-interview-redis`：healthy
  - `ai-interview-celery-worker`：healthy
  - `ai-interview-celery-beat`：healthy
  - `ai-interview-nginx`：running

## 已完成改动

### 1. 修复部署最终健康检查误判

提交：

```text
e60faa1 fix: use HTTPS for deployment checks
```

原因：

- 宿主机 Nginx 的 HTTP 80 仅放行 `/api/v1/config/health`。
- `/`、`/admin/`、`/api/v1/config/release` 在 HTTP 下会 301 跳转 HTTPS。
- 旧 workflow 用 `http://localhost:80/...` 检查并要求 200，导致部署最后阶段误判失败。

处理：

- 将最终 frontend/admin/API 检查改为 `https://localhost/...`。
- 使用 `curl -k` 避免 localhost 与正式证书域名不一致导致证书校验失败。
- 增加状态码输出：

```bash
echo "HTTPS status: frontend=$frontend_status admin=$admin_status api=$api_status"
```

结果：

- 部署检查不再因 HTTP 301 重定向误判。

### 2. 修复媒体工具表结构缺列

提交：

```text
456fdd1 fix: add media task error message migration
29b05a7 fix: make media task migration idempotent
```

原因：

- 生产日志报错：

```text
column media_tasks.error_message does not exist
```

- 代码模型 `MediaTask` 已有 `error_message` 字段。
- 初始媒体工具迁移 `i2b3c4d5e6f7_add_media_toolbox_tables.py` 创建 `media_tasks` 时漏掉了该列。
- 访问媒体任务列表和创建转换任务时 SQLAlchemy 会查询该字段，因此触发 500。

处理：

- 新增 Alembic 迁移：

```text
ai-interview-backend/migrations/versions/j3c4d5e6f7g8_add_media_task_error_message.py
```

- 迁移使用幂等 DDL：

```sql
ALTER TABLE media_tasks ADD COLUMN IF NOT EXISTS error_message TEXT;
```

- 服务器上已先做生产止血：
  - 备份表结构到 `/home/deploy/ai-interview/backups/`
  - 手动执行 `ALTER TABLE media_tasks ADD COLUMN IF NOT EXISTS error_message TEXT;`

结果：

- 服务器当前 Alembic 版本：

```text
j3c4d5e6f7g8 (head)
```

- 生产库已确认列存在：

```text
error_message:text
```

- 未登录访问任务列表现在返回预期 401，而不是 500：

```text
GET /api/v1/media-tools/tasks?page=1&size=12 -> 401 Not authenticated
```

## 当前仍存在的问题

### 媒体处理工具创建转换任务仍然 500

人工在页面点击媒体工具转换后，Nginx 仍记录：

```text
POST /api/v1/media-tools/tasks/convert HTTP/1.1" 500
```

最新后端日志根因已经变为：

```text
AttributeError: 'FormatConfig' object has no attribute 'TOOL_CODES'
```

对应代码位置：

```text
ai-interview-backend/app/api/client/v1/media/tasks.py
```

问题代码逻辑：

```python
if tool_code not in format_config.TOOL_CODES:
```

但 `FormatConfig` 实例中没有 `TOOL_CODES` 属性。需要检查：

```text
ai-interview-backend/app/services/media/format_config.py
```

建议下一步：

1. 确认工具码白名单到底定义在哪里。
2. 如果 `FormatConfig` 中已有类似 `get_capabilities()` 或工具配置结构，应改成从该结构读取合法工具码。
3. 如果没有统一定义，应在 `FormatConfig` 增加实例属性或方法，例如 `is_valid_tool_code(tool_code)`。
4. 补一个最小后端单测覆盖：
   - `tool_code=convert` 应通过校验。
   - 非法 `tool_code` 应返回 400。

## 验证记录

已验证：

```text
python -m py_compile ai-interview-backend/migrations/versions/j3c4d5e6f7g8_add_media_task_error_message.py
git diff --check
```

服务器验证：

```text
docker ps -> app/postgres/redis/celery/nginx 均健康或运行中
alembic current -> j3c4d5e6f7g8 (head)
media_tasks.error_message -> exists
GET /api/v1/media-tools/tasks without token -> 401
```

## 注意事项

- 不要把 SSH 密码、GitHub Actions Secrets、数据库密码、API Key 写入仓库或交接日志。
- 服务器上的 `uploads/media/` 和 `backups/` 是运行期目录，不应纳入 Git。
- 现在媒体工具的问题已经从“数据库列缺失”推进到“工具码白名单属性缺失”，下一轮应优先修 `FormatConfig.TOOL_CODES`。
