# Get Stock Data 微服务 - 完整构建镜像
# 第一阶段：基础构建环境
FROM python:3.12-slim as base

# 构建参数
ARG ENABLE_PROXY=true
ARG PROXY_URL=http://192.168.151.18:3128

# 设置工作目录
WORKDIR /app

# 设置时区
ENV TZ=Asia/Shanghai
RUN ln -snf /usr/share/zoneinfo/$TZ /etc/localtime && echo $TZ > /etc/timezone

# 配置apt代理和源
RUN if [ "$ENABLE_PROXY" = "true" ]; then \
        echo 'Acquire::http::Proxy "'$PROXY_URL'";' > /etc/apt/apt.conf.d/00proxy && \
        echo 'Acquire::https::Proxy "'$PROXY_URL'";' >> /etc/apt/apt.conf.d/00proxy && \
        sed -i 's|deb.debian.org|mirrors.aliyun.com|g' /etc/apt/sources.list.d/debian.sources; \
    else \
        rm -f /etc/apt/apt.conf.d/00proxy; \
    fi

# 安装基础依赖
RUN apt-get update && apt-get install -y \
    gcc \
    curl \
    && rm -rf /var/lib/apt/lists/*

# 配置pip国内镜像源
RUN mkdir -p ~/.pip && \
    echo '[global]' > ~/.pip/pip.conf && \
    echo 'index-url = http://mirrors.aliyun.com/pypi/simple/' >> ~/.pip/pip.conf && \
    echo 'trusted-host = mirrors.aliyun.com' >> ~/.pip/pip.conf && \
    echo 'timeout = 120' >> ~/.pip/pip.conf

# 复制并安装核心依赖
COPY requirements.txt .
RUN if [ "$ENABLE_PROXY" = "true" ]; then \
        http_proxy=$PROXY_URL https_proxy=$PROXY_URL pip install --no-cache-dir --upgrade pip && \
        http_proxy=$PROXY_URL https_proxy=$PROXY_URL pip install --no-cache-dir -r requirements.txt; \
    else \
        pip install --no-cache-dir --upgrade pip && \
        pip install --no-cache-dir -r requirements.txt; \
    fi

# 第二阶段：应用打包
FROM base as final

# 设置PYTHONPATH
ENV PYTHONPATH=/app/src

# 复制应用代码和配置
COPY src/ ./src/
COPY config/ ./config/
COPY entrypoint.sh /app/entrypoint.sh
COPY tests/ ./tests/
COPY packages/ /packages/

# 设置权限并安装离线包
USER root
RUN if [ -f /packages/pytdx-1.72.tar.gz ]; then \
        pip install --no-cache-dir /packages/pytdx-1.72.tar.gz; \
    else \
        pip install --no-cache-dir pytdx; \
    fi && \
    rm -rf /packages && \
    chmod +x /app/entrypoint.sh && \
    useradd --create-home --shell /bin/bash app || true && \
    mkdir -p /app/logs && \
    chown -R app:app /app

# 切换到非root用户
USER app

# 暴露端口 (内部端口 8083)
EXPOSE 8083

# 🚀 启动命令
ENTRYPOINT ["/app/entrypoint.sh"]
CMD ["python", "src/main.py"]