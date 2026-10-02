FROM python:3.12-slim

WORKDIR /app

ENV PYTHONPATH=/app
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

# APT 镜像源：默认使用 Debian 官方源。CI 构建运行在 GitHub 托管 runner（海外节点），
# 官方源最快；此前硬编码切换为 mirrors.aliyun.com 导致海外 runner 拉包极慢、构建超时。
# 如需在国内本地构建，可显式传参：docker build --build-arg APT_MIRROR=mirrors.aliyun.com
ARG APT_MIRROR=""
RUN if [ -n "$APT_MIRROR" ]; then \
        sed -i "s|deb.debian.org|${APT_MIRROR}|g" /etc/apt/sources.list.d/debian.sources; \
    fi \
    && apt-get update && apt-get install -y \
    gcc \
    g++ \
    pkg-config \
    default-libmysqlclient-dev \
    ffmpeg \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
# pip 源：默认走官方 PyPI。服务器侧（国内）构建时可传
# --build-arg PIP_INDEX_URL=https://mirrors.aliyun.com/pypi/simple/ 走国内镜像加速。
ARG PIP_INDEX_URL=""
RUN pip install --no-cache-dir --upgrade pip \
    && pip install --no-cache-dir ${PIP_INDEX_URL:+-i $PIP_INDEX_URL} -r requirements.txt

COPY . .
RUN mkdir -p logs

RUN useradd --create-home --shell /bin/bash app \
    && chown -R app:app /app
USER app

EXPOSE 8006
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD sh -c "ffmpeg -version >/dev/null 2>&1 && ffprobe -version >/dev/null 2>&1 && python -c \"import urllib.request; urllib.request.urlopen('http://localhost:${API_PORT:-8006}/api/v1/config/health')\"" || exit 1
CMD ["sh", "-c", "exec uvicorn main:app --host 0.0.0.0 --port ${API_PORT:-8006} --workers ${API_WORKERS:-2}"]
