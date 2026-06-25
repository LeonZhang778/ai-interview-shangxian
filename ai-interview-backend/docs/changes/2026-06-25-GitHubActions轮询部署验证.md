# GitHub Actions 构建镜像与 SHA 部署

## 1. 功能说明

本次不是业务功能改动，而是把原先依赖阿里云 ACR 自动监听仓库并异步构建的部署链路，改成由 GitHub Actions 直接完成镜像构建、推送和部署。

这样做的目标是解决两个长期稳定性问题：

1. GitHub Actions 无法准确感知 ACR 何时真正完成构建，轮询 digest 时容易出现误判。
2. 即使 ACR 已经构建完成，服务器端如果仍然拉取 `latest`，也不容易确认本次上线到底对应哪一次提交。

改造后，每次 `push main` 时：

1. GitHub Actions 直接构建后端镜像。
2. 同时推送 `latest` 和 `${github.sha}` 两个 tag。
3. 服务器部署时明确使用本次提交对应的 SHA 镜像，而不是仅依赖 `latest`。
4. 部署完成后输出容器镜像与启动状态，并执行健康检查。

## 2. 涉及路由

无。

## 3. 核心实现逻辑

### 3.1 GitHub Actions 侧

1. 登录阿里云 ACR。
2. 基于 `./ai-interview-backend` 目录直接执行 `docker build`。
3. 推送两个标签：
   - `${IMAGE_REPOSITORY}:${GITHUB_SHA}`
   - `${IMAGE_REPOSITORY}:latest`
4. 通过 SSH 登录服务器，执行部署。

### 3.2 服务器部署侧

1. 先 `git pull origin main`，保证部署脚本和 compose 配置同步到最新。
2. 导出 `BACKEND_IMAGE=${IMAGE_REPOSITORY}:${GITHUB_SHA}`。
3. `docker pull` 这次提交对应的精确镜像。
4. `docker compose up -d --force-recreate --no-deps app`，先单独拉起主服务。
5. 等待 `ai-interview-app` 健康检查通过。
6. 再重建 `celery-worker`、`celery-beat` 和 `nginx`。
7. 输出各容器的容器 ID、镜像 ID、启动时间。
8. 最后对 `http://localhost:80/api/v1/config/health` 做健康检查。

### 3.3 Compose 配置调整

为了让服务器可以在不改 compose 结构的前提下切换具体镜像版本，`app`、`celery-worker`、`celery-beat` 三个服务统一改成：

```yaml
image: ${BACKEND_IMAGE:-crpi-yluu2a4ik5gs0met.cn-guangzhou.personal.cr.aliyuncs.com/rwkkyyds-ai-interviews/ai-interviews-shangxian:latest}
```

含义是：

1. 平时手工启动时，如果没有传入 `BACKEND_IMAGE`，仍然默认走 `latest`。
2. GitHub Actions 部署时，可以显式注入 SHA 镜像，实现可追踪部署。

## 4. 为什么比原轮询方案更稳

原轮询方案的问题在于，GitHub Actions 和 ACR 自动构建属于两个异步系统，中间没有强一致的完成信号。即使通过 digest 轮询，也会遇到：

1. 本次提交没有引起镜像层变化，digest 不变，但实际上构建已经成功。
2. ACR 构建完成时间不稳定，轮询窗口过短会误判失败，过长又会拖慢流程。
3. 服务器端如果只拉 `latest`，很难严格验证“本次部署对应哪次代码提交”。

改成 Actions 自己构建后，整条链路只有一个控制面：

1. 构建成功与否由当前 workflow 直接负责。
2. 推送成功后就能立即拿到确定的 SHA tag。
3. 部署时使用精确 tag，容器版本可验证、可追踪、可回滚。

## 5. 涉及文件

```text
.github/workflows/main.yml
ai-interview-backend/docker-compose.yml
ai-interview-backend/docs/changes/2026-06-25-GitHubActions轮询部署验证.md
```

## 6. 验证方式

### 6.1 本地配置验证

执行：

```bash
docker compose -f ai-interview-backend/docker-compose.yml config
```

重点确认：

1. `BACKEND_IMAGE` 变量能正确插值。
2. `app`、`celery-worker`、`celery-beat` 三个服务都引用同一镜像来源。

### 6.2 线上部署验证

1. 提交并推送到 `main`。
2. 观察 GitHub Actions：
   - 构建镜像成功
   - 推送镜像成功
   - SSH 部署成功
   - 健康检查通过
3. 在服务器上核对：
   - `ai-interview-app`
   - `ai-interview-celery-worker`
   - `ai-interview-celery-beat`

这些容器的镜像是否已切换到本次提交对应的 SHA tag。

## 7. 长期建议

当前方案已经比 ACR 自动监听 + 轮询更稳定，适合作为长期主方案。后续如果还要继续提高稳定性，可以考虑：

1. 给后端镜像增加更明确的 `org.opencontainers.image.revision` 标签，便于容器内外核对提交号。
2. 在服务器保留最近若干个 SHA 镜像，配合脚本实现快速回滚。
3. 将部署后的容器检查结果输出为更标准的日志，便于后续排查。
