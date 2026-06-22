# 1. 恢复使用官方原生镜像，配合阿里云“海外机器构建”功能，不再需要任何国内加速器
FROM python:3.12-slim

# Set working directory
WORKDIR /app

# Set environment variables
ENV PYTHONPATH=/app
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

# 2. 修改 apt 系统源为阿里云镜像源（保留此项，因为构建后的镜像主要在国内服务器运行，利于后续排查）
RUN sed -i 's/deb.debian.org/mirrors.aliyun.com/g' /etc/apt/sources.list.d/debian.sources \
    && apt-get update && apt-get install -y \
    gcc \
    g++ \
    pkg-config \
    default-libmysqlclient-dev \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements file and install Python dependencies
COPY requirements.txt .

# 3. 恢复使用官方标准的 pip 安装（海外机器拉取官方 PyPI 速度极快）
RUN pip install --no-cache-dir --upgrade pip \
    && pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

# Create logs directory
RUN mkdir -p logs

# Create non-root user to run application
RUN useradd --create-home --shell /bin/bash app \
    && chown -R app:app /app
USER app

# Expose port
EXPOSE 8001

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:${API_PORT:-8001}/api/v1/config/health')" || exit 1

# Start command
CMD ["python", "main.py"]
