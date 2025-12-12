# Quant Strategy 微服务 Dockerfile
# 使用阿里云镜像加速
FROM python:3.12-slim

# 设置代理环境变量
ENV http_proxy=http://192.168.151.18:3128 \
    https_proxy=http://192.168.151.18:3128 \
    HTTP_PROXY=http://192.168.151.18:3128 \
    HTTPS_PROXY=http://192.168.151.18:3128

# 设置工作目录
WORKDIR /app

# 设置环境变量
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONPATH=/app/src

# 配置apt使用国内源和代理
RUN echo 'Acquire::http::Proxy "http://192.168.151.18:3128";' > /etc/apt/apt.conf.d/00proxy && \
    echo 'Acquire::https::Proxy "http://192.168.151.18:3128";' >> /etc/apt/apt.conf.d/00proxy && \
    sed -i 's|deb.debian.org|mirrors.aliyun.com|g' /etc/apt/sources.list.d/debian.sources

# Install system dependencies
RUN apt-get update && apt-get install -y curl proxychains4 netcat-openbsd && rm -rf /var/lib/apt/lists/*

# Configure pip using domestic mirror
RUN mkdir -p ~/.pip && \
    echo '[global]' > ~/.pip/pip.conf && \
    echo 'index-url = https://pypi.tuna.tsinghua.edu.cn/simple/' >> ~/.pip/pip.conf && \
    echo 'trusted-host = pypi.tuna.tsinghua.edu.cn' >> ~/.pip/pip.conf && \
    echo 'timeout = 120' >> ~/.pip/pip.conf

# Upgrade pip
RUN pip install --no-cache-dir --upgrade pip -i https://pypi.tuna.tsinghua.edu.cn/simple

# Copy dependencies
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt -i https://pypi.tuna.tsinghua.edu.cn/simple || \
    pip install --no-cache-dir -r requirements.txt -i https://mirrors.aliyun.com/pypi/simple || \
    pip install --no-cache-dir -r requirements.txt -i https://pypi.douban.com/simple/ || \
    pip install --no-cache-dir -r requirements.txt

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
