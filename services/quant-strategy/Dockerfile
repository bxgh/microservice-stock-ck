# Quant Strategy 微服务 Dockerfile
# 使用阿里云镜像加速
FROM python:3.12-slim

# 构建参数
ARG ENABLE_PROXY=true
ARG PROXY_URL=http://192.168.151.18:3128

# 设置工作目录
WORKDIR /app

# 设置环境变量
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONPATH=/app/src

# 配置apt代理和源
RUN if [ "$ENABLE_PROXY" = "true" ]; then \
        echo 'Acquire::http::Proxy "'$PROXY_URL'";' > /etc/apt/apt.conf.d/00proxy && \
        echo 'Acquire::https::Proxy "'$PROXY_URL'";' >> /etc/apt/apt.conf.d/00proxy && \
        sed -i 's|deb.debian.org|mirrors.aliyun.com|g' /etc/apt/sources.list.d/debian.sources; \
    fi

# Install system dependencies
RUN apt-get update && apt-get install -y curl proxychains4 netcat-openbsd && rm -rf /var/lib/apt/lists/*

# Configure pip using domestic mirror
RUN mkdir -p ~/.pip && \
    echo '[global]' > ~/.pip/pip.conf && \
    echo 'index-url = http://mirrors.aliyun.com/pypi/simple/' >> ~/.pip/pip.conf && \
    echo 'trusted-host = mirrors.aliyun.com' >> ~/.pip/pip.conf && \
    echo 'timeout = 120' >> ~/.pip/pip.conf

# Upgrade pip
RUN if [ "$ENABLE_PROXY" = "true" ]; then \
        http_proxy=$PROXY_URL https_proxy=$PROXY_URL pip install --no-cache-dir --upgrade pip; \
    else \
        pip install --no-cache-dir --upgrade pip; \
    fi

# Copy dependencies
COPY requirements.txt .

# Install Python dependencies
RUN if [ "$ENABLE_PROXY" = "true" ]; then \
        http_proxy=$PROXY_URL https_proxy=$PROXY_URL pip install --no-cache-dir -r requirements.txt; \
    else \
        pip install --no-cache-dir -r requirements.txt; \
    fi

# Copy application code
COPY src/ ./src/
COPY config/ ./config/
COPY entrypoint.sh /app/entrypoint.sh

# Create non-root user and directories
RUN useradd --create-home --shell /bin/bash app && \
    mkdir -p /app/logs && \
    mkdir -p /app/data && \
    chmod +x /app/entrypoint.sh && \
    chown -R app:app /app

# Switch to non-root user
USER app

# Expose port
EXPOSE 8084

# Set entrypoint
ENTRYPOINT ["/app/entrypoint.sh"]

# Start command
CMD ["python", "src/main.py"]
