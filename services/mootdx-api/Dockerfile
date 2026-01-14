FROM python:3.12-slim

# 构建参数
ARG ENABLE_PROXY=true
ARG PROXY_URL=http://192.168.151.18:3128

# 配置apt代理和源
RUN if [ "$ENABLE_PROXY" = "true" ]; then \
        echo 'Acquire::http::Proxy "'$PROXY_URL'";' > /etc/apt/apt.conf.d/00proxy && \
        echo 'Acquire::https::Proxy "'$PROXY_URL'";' >> /etc/apt/apt.conf.d/00proxy && \
        sed -i 's|deb.debian.org|mirrors.aliyun.com|g' /etc/apt/sources.list.d/debian.sources; \
    fi

WORKDIR /app

# 配置pip国内镜像源
RUN mkdir -p ~/.pip && \
    echo '[global]' > ~/.pip/pip.conf && \
    echo 'index-url = http://mirrors.aliyun.com/pypi/simple/' >> ~/.pip/pip.conf && \
    echo 'trusted-host = mirrors.aliyun.com' >> ~/.pip/pip.conf

# 安装 Python 依赖
COPY services/mootdx-api/requirements.txt .
RUN if [ "$ENABLE_PROXY" = "true" ]; then \
        http_proxy=$PROXY_URL https_proxy=$PROXY_URL pip install --no-cache-dir -r requirements.txt; \
    else \
        pip install --no-cache-dir -r requirements.txt; \
    fi

# 清理 apt 代理 (减少层大小，虽然这里没装系统包，但为了规范)
RUN rm -f /etc/apt/apt.conf.d/00proxy

# 复制共享库并安装
COPY libs/gsd-shared/ /app/libs/gsd-shared/
RUN pip install --no-cache-dir -e /app/libs/gsd-shared/

# 复制源代码和诊断工具
COPY services/mootdx-api/src/ ./src/
COPY services/mootdx-api/diagnostics/ ./diagnostics/

# 设置 Python 路径
ENV PYTHONPATH=/app/src

# 健康检查 (使用 Python)
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8003/health')"

# 暴露端口
EXPOSE 8003

# 启动命令
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8003"]
