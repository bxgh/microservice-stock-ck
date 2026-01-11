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

# 配置pip国内源
RUN mkdir -p ~/.pip && \
    echo '[global]' > ~/.pip/pip.conf && \
    echo 'index-url = http://mirrors.aliyun.com/pypi/simple/' >> ~/.pip/pip.conf && \
    echo 'trusted-host = mirrors.aliyun.com' >> ~/.pip/pip.conf && \
    echo 'timeout = 120' >> ~/.pip/pip.conf
# 复制依赖文件 (假设 context 是项目根目录)
# 1. 服务自身依赖
COPY services/mootdx-source/requirements.txt /app/requirements.txt
# 2. 共享库依赖 (如果有专门的 requirements) - 这里暂无，直接安装 libraries

# 安装 Python 依赖
RUN if [ "$ENABLE_PROXY" = "true" ]; then \
        http_proxy=$PROXY_URL https_proxy=$PROXY_URL pip install --no-cache-dir -r /app/requirements.txt; \
    else \
        pip install --no-cache-dir -r /app/requirements.txt; \
    fi

# 复制共享库
COPY libs/common /app/libs/common
# 将 libs/common 加入 PYTHONPATH
ENV PYTHONPATH=/app/libs/common:$PYTHONPATH

# 复制服务代码
COPY services/mootdx-source/src /app/src

# 环境变量
ENV SERVICE_NAME=mootdx-source
ENV SERVICE_PORT=50051

# 暴露端口
EXPOSE 50051

# 健康检查 (检查gRPC端口是否可用)
HEALTHCHECK --interval=30s --timeout=10s --start-period=30s --retries=3 \
    CMD curl -f http://localhost:50051/ || exit 1

# 启动命令
CMD ["python", "src/main.py"]
