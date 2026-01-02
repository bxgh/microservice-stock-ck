FROM python:3.12-slim

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

# 升级pip
RUN if [ "$ENABLE_PROXY" = "true" ]; then \
        http_proxy=$PROXY_URL https_proxy=$PROXY_URL pip install --no-cache-dir --upgrade pip; \
    else \
        pip install --no-cache-dir --upgrade pip; \
    fi

# 复制并安装Python依赖
COPY services/gsd-worker/requirements.txt .
RUN if [ "$ENABLE_PROXY" = "true" ]; then \
        http_proxy=$PROXY_URL https_proxy=$PROXY_URL pip install --no-cache-dir -r requirements.txt; \
    else \
        pip install --no-cache-dir -r requirements.txt; \
    fi


# 安装 gsd-shared (从项目根目录复制)
# 注意: 需要从项目根目录构建，使用 docker build -f services/gsd-worker/Dockerfile .
COPY libs/gsd-shared /tmp/gsd-shared
RUN if [ "$ENABLE_PROXY" = "true" ]; then \
        http_proxy=$PROXY_URL https_proxy=$PROXY_URL pip install -e /tmp/gsd-shared; \
    else \
        pip install -e /tmp/gsd-shared; \
    fi

# 复制源代码
COPY services/gsd-worker/src/ ./src/

# 创建非root用户
RUN useradd --create-home --shell /bin/bash app && \
    mkdir -p /app/logs && \
    chown -R app:app /app

# 切换到非root用户
USER app

# 默认执行同步任务
ENTRYPOINT ["python", "-m"]
CMD ["jobs.sync_kline"]
