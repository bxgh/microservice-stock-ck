# Stage 1: Builder
FROM python:3.12-slim AS builder

WORKDIR /build

# 构建参数
ARG ENABLE_PROXY=true
ARG PROXY_URL=http://192.168.151.18:3128

# 配置apt代理和源
RUN if [ "$ENABLE_PROXY" = "true" ]; then \
        echo 'Acquire::http::Proxy "'$PROXY_URL'";' > /etc/apt/apt.conf.d/00proxy && \
        echo 'Acquire::https::Proxy "'$PROXY_URL'";' >> /etc/apt/apt.conf.d/00proxy && \
        sed -i 's|deb.debian.org|mirrors.aliyun.com|g' /etc/apt/sources.list.d/debian.sources; \
    fi

# 安装编译依赖
RUN apt-get update && apt-get install -y \
    gcc \
    g++ \
    python3-dev \
    libffi-dev \
    && rm -rf /var/lib/apt/lists/*

# 配置pip国内镜像源
RUN mkdir -p ~/.pip && \
    echo '[global]' > ~/.pip/pip.conf && \
    echo 'index-url = http://mirrors.aliyun.com/pypi/simple/' >> ~/.pip/pip.conf && \
    echo 'trusted-host = mirrors.aliyun.com' >> ~/.pip/pip.conf

# 升级 pip
RUN if [ "$ENABLE_PROXY" = "true" ]; then \
        http_proxy=$PROXY_URL https_proxy=$PROXY_URL pip install --no-cache-dir --upgrade pip; \
    else \
        pip install --no-cache-dir --upgrade pip; \
    fi

# 安装Python依赖到指定目录
COPY services/gsd-worker/requirements.txt .
RUN if [ "$ENABLE_PROXY" = "true" ]; then \
        http_proxy=$PROXY_URL https_proxy=$PROXY_URL pip install --prefix=/install --no-cache-dir -r requirements.txt; \
    else \
        pip install --prefix=/install --no-cache-dir -r requirements.txt; \
    fi

# 安装 gsd-shared
COPY libs/gsd-shared /tmp/gsd-shared
RUN if [ "$ENABLE_PROXY" = "true" ]; then \
        http_proxy=$PROXY_URL https_proxy=$PROXY_URL pip install --prefix=/install /tmp/gsd-shared; \
    else \
        pip install --prefix=/install /tmp/gsd-shared; \
    fi


# Stage 2: Final
FROM python:3.12-slim

WORKDIR /app

# 构建参数 (重申以在 Stage 2 中使用)
ARG ENABLE_PROXY=true
ARG PROXY_URL=http://192.168.151.18:3128

# 设置时区
ENV TZ=Asia/Shanghai
RUN ln -snf /usr/share/zoneinfo/$TZ /etc/localtime && echo $TZ > /etc/timezone

# 配置apt代理和源 (Stage 2 同样需要，用于安装运行时工具)
RUN if [ "$ENABLE_PROXY" = "true" ]; then \
        echo 'Acquire::http::Proxy "'$PROXY_URL'";' > /etc/apt/apt.conf.d/00proxy && \
        echo 'Acquire::https::Proxy "'$PROXY_URL'";' >> /etc/apt/apt.conf.d/00proxy && \
        sed -i 's|deb.debian.org|mirrors.aliyun.com|g' /etc/apt/sources.list.d/debian.sources; \
    fi

# 从构建者阶段复制已安装的包
COPY --from=builder /install /usr/local

# 安装运行时基础工具 (curl 用于连接测试)
RUN apt-get update && apt-get install -y \
    curl \
    && rm -rf /var/lib/apt/lists/* && \
    rm -f /etc/apt/apt.conf.d/00proxy

# 复制源代码和配置
COPY services/gsd-worker/src/ ./src/
COPY services/gsd-worker/config/ ./config/

# 设置PYTHONPATH
ENV PYTHONPATH=/app/src

# 创建并切换到非root用户
RUN useradd --create-home --shell /bin/bash app && \
    mkdir -p /app/logs && \
    chown -R app:app /app

USER app

# 默认执行同步任务
ENTRYPOINT ["python", "-m"]
CMD ["jobs.sync_kline"]
