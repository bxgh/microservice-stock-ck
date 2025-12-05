# Get Stock Data 微服务 Dockerfile
FROM python:3.12-slim

# 设置代理环境变量（可选，通过build args控制）
ARG ENABLE_PROXY=false
ARG PROXY_URL=http://192.168.151.18:3128

# 根据build args设置代理环境变量
ENV http_proxy=${ENABLE_PROXY:+$PROXY_URL} \
    https_proxy=${ENABLE_PROXY:+$PROXY_URL} \
    HTTP_PROXY=${ENABLE_PROXY:+$PROXY_URL} \
    HTTPS_PROXY=${ENABLE_PROXY:+$PROXY_URL}

# 设置工作目录
WORKDIR /app

# 设置环境变量
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONPATH=/app/src

# 配置apt使用源和代理（可选）
RUN if [ "$ENABLE_PROXY" = "true" ]; then \
        echo 'Acquire::http::Proxy "'$PROXY_URL'";' > /etc/apt/apt.conf.d/00proxy && \
        echo 'Acquire::https::Proxy "'$PROXY_URL'";' >> /etc/apt/apt.conf.d/00proxy && \
        export http_proxy=$PROXY_URL && export https_proxy=$PROXY_URL && \
        sed -i 's|deb.debian.org|mirrors.aliyun.com|g' /etc/apt/sources.list.d/debian.sources; \
    else \
        rm -f /etc/apt/apt.conf.d/00proxy && \
        unset http_proxy && unset https_proxy && \
        sed -i 's|mirrors.aliyun.com|deb.debian.org|g' /etc/apt/sources.list.d/debian.sources || true; \
    fi

# 安装系统依赖
RUN if [ "$ENABLE_PROXY" = "true" ]; then \
        http_proxy=$PROXY_URL https_proxy=$PROXY_URL apt-get update && \
        http_proxy=$PROXY_URL https_proxy=$PROXY_URL apt-get install -y curl && \
        rm -rf /var/lib/apt/lists/*; \
    else \
        unset http_proxy && unset https_proxy && \
        apt-get update && \
        apt-get install -y curl && \
        rm -rf /var/lib/apt/lists/*; \
    fi

# 配置pip使用国内源和代理
RUN mkdir -p ~/.pip && \
    echo '[global]' > ~/.pip/pip.conf && \
    echo 'index-url = https://pypi.tuna.tsinghua.edu.cn/simple/' >> ~/.pip/pip.conf && \
    echo 'trusted-host = pypi.tuna.tsinghua.edu.cn' >> ~/.pip/pip.conf && \
    echo 'timeout = 120' >> ~/.pip/pip.conf

# 升级pip (使用国内源)
RUN pip install --no-cache-dir --upgrade pip -i https://pypi.tuna.tsinghua.edu.cn/simple

# 复制完整依赖文件
COPY requirements.txt .

# 安装Python依赖 (优先使用国内源)
RUN pip install --no-cache-dir -r requirements.txt -i https://pypi.tuna.tsinghua.edu.cn/simple || \
    pip install --no-cache-dir -r requirements.txt -i https://mirrors.aliyun.com/pypi/simple || \
    pip install --no-cache-dir -r requirements.txt -i https://pypi.douban.com/simple/ || \
    pip install --no-cache-dir -r requirements.txt

# 复制FastAPI应用代码
COPY src/ ./src/
COPY config/ ./config/

# 创建非root用户和日志目录
RUN useradd --create-home --shell /bin/bash app && \
    mkdir -p /app/logs && \
    chown -R app:app /app

# 切换到非root用户
USER app

# 暴露端口
EXPOSE 8086

# 启动命令
CMD ["python", "src/main.py"]